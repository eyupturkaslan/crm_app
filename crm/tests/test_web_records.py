import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from crm.models import Company, Contact

pytestmark = pytest.mark.urls("crm.tests.records_urls")


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


def test_company_list_requires_login(client):
    resp = client.get(reverse("crm:company_list"))
    assert resp.status_code == 302
    assert reverse("login") in resp["Location"]


def test_contact_list_requires_login(client):
    resp = client.get(reverse("crm:contact_list"))
    assert resp.status_code == 302


# --------------------------------------------------------------------------
# Companies: list / search / HTMX partial / CRUD / delete
# --------------------------------------------------------------------------


def test_company_list_shows_companies(auth_client, company):
    resp = auth_client.get(reverse("crm:company_list"))
    assert resp.status_code == 200
    assert company.name in resp.content.decode()


def test_company_list_search_filters(auth_client, company):
    Company.objects.create(name="Zeta Ltd.", industry="Perakende")
    resp = auth_client.get(reverse("crm:company_list"), {"q": "Acme"})
    content = resp.content.decode()
    assert company.name in content
    assert "Zeta Ltd." not in content


def test_company_list_htmx_returns_partial(auth_client, company):
    resp = auth_client.get(reverse("crm:company_list"), HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "<html" not in content.lower()
    assert company.name in content


def test_company_create(auth_client, user):
    resp = auth_client.post(
        reverse("crm:company_create"),
        {
            "name": "Yeni Firma A.Ş.",
            "domain": "",
            "industry": "",
            "size": "",
            "phone": "",
            "address": "",
            "city": "",
            "country": "Türkiye",
            "tags": [],
        },
    )
    company = Company.objects.get(name="Yeni Firma A.Ş.")
    assert resp.status_code == 302
    assert resp["Location"] == reverse("crm:company_detail", args=[company.pk])
    assert company.owner == user


def test_company_update(auth_client, company):
    resp = auth_client.post(
        reverse("crm:company_update", args=[company.pk]),
        {
            "name": "Acme Güncel",
            "domain": "",
            "industry": "Yazılım",
            "size": "",
            "phone": "",
            "address": "",
            "city": "",
            "country": "Türkiye",
            "tags": [],
        },
    )
    company.refresh_from_db()
    assert resp.status_code == 302
    assert company.name == "Acme Güncel"


def test_company_detail_shows_related(auth_client, company, contact, deal):
    resp = auth_client.get(reverse("crm:company_detail", args=[company.pk]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert contact.full_name in content
    assert deal.title in content


def test_company_delete_get_shows_confirm(auth_client, company):
    resp = auth_client.get(reverse("crm:company_delete", args=[company.pk]))
    assert resp.status_code == 200
    assert "Sil" in resp.content.decode()
    assert Company.objects.filter(pk=company.pk).exists()


def test_company_delete_post_deletes(auth_client, company):
    resp = auth_client.post(reverse("crm:company_delete", args=[company.pk]))
    assert resp.status_code == 302
    assert resp["Location"] == reverse("crm:company_list")
    assert not Company.objects.filter(pk=company.pk).exists()


# --------------------------------------------------------------------------
# Contacts: list / search / HTMX partial / CRUD / delete
# --------------------------------------------------------------------------


def test_contact_list_shows_contacts(auth_client, contact):
    resp = auth_client.get(reverse("crm:contact_list"))
    assert resp.status_code == 200
    assert contact.full_name in resp.content.decode()


def test_contact_list_lifecycle_filter(auth_client, contact):
    Contact.objects.create(first_name="Ayşe", last_name="Kaya", lifecycle_stage=Contact.Lifecycle.CUSTOMER)
    resp = auth_client.get(reverse("crm:contact_list"), {"lifecycle_stage": Contact.Lifecycle.CUSTOMER})
    content = resp.content.decode()
    assert "Ayşe" in content
    assert contact.first_name not in content


def test_contact_list_owner_me_filter(auth_client, contact, user, django_user_model):
    other = django_user_model.objects.create_user(username="other", password="pass12345")
    Contact.objects.create(first_name="Başka", last_name="Kişi", owner=other)
    resp = auth_client.get(reverse("crm:contact_list"), {"owner": "me"})
    content = resp.content.decode()
    assert contact.first_name in content
    assert "Başka" not in content


def test_contact_list_htmx_returns_partial(auth_client, contact):
    resp = auth_client.get(reverse("crm:contact_list"), HTTP_HX_REQUEST="true")
    assert resp.status_code == 200
    content = resp.content.decode()
    assert "<html" not in content.lower()
    assert contact.full_name in content


def test_contact_create(auth_client, user, company):
    resp = auth_client.post(
        reverse("crm:contact_create"),
        {
            "first_name": "Elif",
            "last_name": "Demir",
            "email": "elif@example.com",
            "phone": "",
            "job_title": "",
            "company": company.pk,
            "lifecycle_stage": Contact.Lifecycle.LEAD,
            "source": Contact.Source.OTHER,
            "preferred_channel": Contact.Channel.EMAIL,
            "marketing_consent": "",
            "notes": "",
            "tags": [],
        },
    )
    new_contact = Contact.objects.get(email="elif@example.com")
    assert resp.status_code == 302
    assert resp["Location"] == reverse("crm:contact_detail", args=[new_contact.pk])
    assert new_contact.owner == user


def test_contact_update(auth_client, contact):
    resp = auth_client.post(
        reverse("crm:contact_update", args=[contact.pk]),
        {
            "first_name": "Mehmet",
            "last_name": "Yılmaz Güncel",
            "email": contact.email,
            "phone": "",
            "job_title": "",
            "company": "",
            "lifecycle_stage": Contact.Lifecycle.CUSTOMER,
            "source": Contact.Source.OTHER,
            "preferred_channel": Contact.Channel.EMAIL,
            "marketing_consent": "",
            "notes": "",
            "tags": [],
        },
    )
    contact.refresh_from_db()
    assert resp.status_code == 302
    assert contact.last_name == "Yılmaz Güncel"
    assert contact.lifecycle_stage == Contact.Lifecycle.CUSTOMER


def test_contact_detail_shows_score_bar_and_deals(auth_client, contact, deal):
    resp = auth_client.get(reverse("crm:contact_detail", args=[contact.pk]))
    assert resp.status_code == 200
    content = resp.content.decode()
    assert deal.title in content
    assert str(contact.score) in content


def test_contact_delete_get_shows_confirm(auth_client, contact):
    resp = auth_client.get(reverse("crm:contact_delete", args=[contact.pk]))
    assert resp.status_code == 200
    assert Contact.objects.filter(pk=contact.pk).exists()


def test_contact_delete_post_deletes(auth_client, contact):
    resp = auth_client.post(reverse("crm:contact_delete", args=[contact.pk]))
    assert resp.status_code == 302
    assert resp["Location"] == reverse("crm:contact_list")
    assert not Contact.objects.filter(pk=contact.pk).exists()


# --------------------------------------------------------------------------
# CSV export
# --------------------------------------------------------------------------


def test_contact_export_csv_content(auth_client, contact):
    resp = auth_client.get(reverse("crm:contact_export"))
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/csv")
    body = b"".join(resp.streaming_content).decode("utf-8")
    assert body.startswith("﻿")
    assert contact.first_name in body
    assert contact.email in body


def test_contact_export_respects_filters(auth_client, contact):
    Contact.objects.create(first_name="Filtrelenmemis", last_name="Kisi", lifecycle_stage=Contact.Lifecycle.CUSTOMER)
    resp = auth_client.get(reverse("crm:contact_export"), {"lifecycle_stage": Contact.Lifecycle.CUSTOMER})
    body = b"".join(resp.streaming_content).decode("utf-8")
    assert "Filtrelenmemis" in body
    assert contact.first_name not in body


# --------------------------------------------------------------------------
# CSV import
# --------------------------------------------------------------------------


def _csv_upload(text):
    return SimpleUploadedFile("contacts.csv", text.encode("utf-8"), content_type="text/csv")


def test_contact_import_creates_updates_and_skips(auth_client, contact):
    csv_text = (
        "first_name,last_name,email,phone,job_title,company,lifecycle_stage,source\n"
        # Update existing contact (matched by email).
        f"Mehmet,Guncel,{contact.email},555,CEO,Acme A.Ş.,customer,referral\n"
        # New contact, creates a new company by name.
        "Elif,Demir,elif@new.test,,,Yeni Firma,lead,website\n"
        # No first_name -> skipped.
        ",Soyadsiz,noone@example.com,,,,,\n"
    )
    resp = auth_client.post(reverse("crm:contact_import"), {"csv_file": _csv_upload(csv_text)})
    assert resp.status_code == 302
    assert resp["Location"] == reverse("crm:contact_list")

    contact.refresh_from_db()
    assert contact.last_name == "Guncel"
    assert contact.lifecycle_stage == Contact.Lifecycle.CUSTOMER

    created = Contact.objects.get(email="elif@new.test")
    assert created.company.name == "Yeni Firma"

    assert not Contact.objects.filter(last_name="Soyadsiz").exists()
    assert Contact.objects.count() == 2


def test_contact_import_rejects_non_csv(auth_client):
    bad_file = SimpleUploadedFile("contacts.txt", b"first_name\nAli\n", content_type="text/plain")
    resp = auth_client.post(reverse("crm:contact_import"), {"csv_file": bad_file})
    assert resp.status_code == 200
    assert not Contact.objects.filter(first_name="Ali").exists()


# --------------------------------------------------------------------------
# Global search
# --------------------------------------------------------------------------


def test_global_search_short_query_returns_empty(auth_client):
    resp = auth_client.get(reverse("crm:search"), {"q": "a"})
    assert resp.status_code == 200
    assert resp.content == b""


def test_global_search_finds_contacts_and_companies(auth_client, contact, company, deal):
    resp = auth_client.get(reverse("crm:search"), {"q": "Acme"})
    assert resp.status_code == 200
    content = resp.content.decode()
    assert company.name in content
    assert contact.full_name in content


def test_global_search_no_results(auth_client):
    resp = auth_client.get(reverse("crm:search"), {"q": "hicbirsonuc"})
    assert resp.status_code == 200
    assert "Sonuç bulunamadı" in resp.content.decode()
