from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from crm.models import Activity, Company, Contact, Deal, Tag

pytestmark = [pytest.mark.django_db, pytest.mark.urls("crm.tests.api_urls")]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_anonymous_request_is_rejected(self):
        anon = APIClient()
        response = anon.get("/api/v1/companies/")
        assert response.status_code in (401, 403)

    def test_authenticated_request_succeeds(self, api_client, company):
        response = api_client.get("/api/v1/companies/")
        assert response.status_code == 200

    def test_token_obtain(self, user):
        anon = APIClient()
        response = anon.post("/api/v1/auth/token/", {"username": user.username, "password": "pass12345"})
        assert response.status_code == 200
        assert "token" in response.data
        assert response.data["token"] == Token.objects.get(user=user).key


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


class TestCompanyAPI:
    def test_list(self, api_client, company):
        response = api_client.get("/api/v1/companies/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_create_sets_owner_from_request_when_missing(self, api_client, user):
        response = api_client.post("/api/v1/companies/", {"name": "Yeni Firma A.Ş."})
        assert response.status_code == 201, response.data
        company = Company.objects.get(pk=response.data["id"])
        assert company.owner_id == user.id

    def test_create_with_explicit_owner_is_respected(self, api_client, django_user_model):
        other = django_user_model.objects.create_user(username="other", password="pass12345")
        response = api_client.post("/api/v1/companies/", {"name": "Başka Firma", "owner": other.id})
        assert response.status_code == 201, response.data
        assert response.data["owner"] == other.id

    def test_tags_writable_by_pk_list(self, api_client, company):
        tag1 = Tag.objects.create(name="VIP")
        tag2 = Tag.objects.create(name="Riskli")
        response = api_client.patch(f"/api/v1/companies/{company.pk}/", {"tags": [tag1.id, tag2.id]}, format="json")
        assert response.status_code == 200, response.data
        company.refresh_from_db()
        assert set(company.tags.values_list("id", flat=True)) == {tag1.id, tag2.id}

    def test_search_by_name(self, api_client):
        Company.objects.create(name="Acme Yazılım")
        Company.objects.create(name="Beta Lojistik")
        response = api_client.get("/api/v1/companies/", {"search": "Acme"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["name"] == "Acme Yazılım"

    def test_read_only_fields_are_not_writable(self, api_client, company):
        original_created_at = company.created_at
        response = api_client.patch(
            f"/api/v1/companies/{company.pk}/", {"created_at": "2000-01-01T00:00:00Z"}, format="json"
        )
        assert response.status_code == 200
        company.refresh_from_db()
        assert company.created_at == original_created_at


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


class TestContactAPI:
    def test_full_name_and_company_name_included(self, api_client, contact):
        response = api_client.get(f"/api/v1/contacts/{contact.pk}/")
        assert response.status_code == 200
        assert response.data["full_name"] == contact.full_name
        assert response.data["company_name"] == contact.company.name

    def test_score_and_consent_at_are_read_only(self, api_client, contact):
        response = api_client.patch(
            f"/api/v1/contacts/{contact.pk}/",
            {"score": 999, "consent_at": "2000-01-01T00:00:00Z"},
            format="json",
        )
        assert response.status_code == 200
        contact.refresh_from_db()
        assert contact.score != 999
        assert contact.consent_at is None  # marketing_consent still false

    def test_marketing_consent_sets_consent_at_via_api(self, api_client, contact):
        assert contact.consent_at is None
        response = api_client.patch(f"/api/v1/contacts/{contact.pk}/", {"marketing_consent": True}, format="json")
        assert response.status_code == 200
        assert response.data["consent_at"] is not None

    def test_filter_by_lifecycle_stage(self, api_client, company):
        Contact.objects.create(first_name="Lead", company=company, lifecycle_stage=Contact.Lifecycle.LEAD)
        Contact.objects.create(first_name="Cust", company=company, lifecycle_stage=Contact.Lifecycle.CUSTOMER)
        response = api_client.get("/api/v1/contacts/", {"lifecycle_stage": "customer"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["first_name"] == "Cust"

    def test_search_by_email(self, api_client, contact):
        response = api_client.get("/api/v1/contacts/", {"search": "mehmet@acme.test"})
        assert response.data["count"] == 1

    def test_ordering_by_score(self, api_client, company):
        Contact.objects.create(first_name="Zayıf", company=company)
        Contact.objects.create(first_name="Güçlü", company=company, email="g@example.com", marketing_consent=True)
        response = api_client.get("/api/v1/contacts/", {"ordering": "-score"})
        names = [row["first_name"] for row in response.data["results"]]
        assert names[0] == "Güçlü"


# ---------------------------------------------------------------------------
# Deals
# ---------------------------------------------------------------------------


class TestDealAPI:
    def test_weighted_value_and_is_open_present(self, api_client, deal):
        response = api_client.get(f"/api/v1/deals/{deal.pk}/")
        assert response.status_code == 200
        assert Decimal(response.data["weighted_value"]) == deal.weighted_value
        assert response.data["is_open"] is True

    def test_move_action_changes_stage_and_probability(self, api_client, deal):
        response = api_client.post(f"/api/v1/deals/{deal.pk}/move/", {"stage": "won"}, format="json")
        assert response.status_code == 200, response.data
        deal.refresh_from_db()
        assert deal.stage == "won"
        assert deal.probability == Deal.STAGE_PROBABILITY["won"]
        assert deal.closed_at is not None
        assert response.data["is_open"] is False

    def test_move_action_with_position(self, api_client, deal):
        response = api_client.post(
            f"/api/v1/deals/{deal.pk}/move/", {"stage": "proposal", "position": 5}, format="json"
        )
        assert response.status_code == 200
        deal.refresh_from_db()
        assert deal.position == 5

    def test_move_action_rejects_invalid_stage(self, api_client, deal):
        response = api_client.post(f"/api/v1/deals/{deal.pk}/move/", {"stage": "not-a-stage"}, format="json")
        assert response.status_code == 400

    def test_filter_by_stage(self, api_client, company, contact):
        Deal.objects.create(title="Kazanılan", company=company, contact=contact, value=1000, stage="won")
        Deal.objects.create(title="Yeni fırsat", company=company, contact=contact, value=2000, stage="new")
        response = api_client.get("/api/v1/deals/", {"stage": "won"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["title"] == "Kazanılan"


# ---------------------------------------------------------------------------
# Activities
# ---------------------------------------------------------------------------


class TestActivityAPI:
    def test_is_overdue_present(self, api_client, contact):
        activity = Activity.objects.create(subject="Ara", due_at=timezone.now() - timedelta(days=1), contact=contact)
        response = api_client.get(f"/api/v1/activities/{activity.pk}/")
        assert response.data["is_overdue"] is True

    def test_toggle_action_flips_done(self, api_client, contact):
        activity = Activity.objects.create(subject="Ara", contact=contact, done=False)
        response = api_client.post(f"/api/v1/activities/{activity.pk}/toggle/")
        assert response.status_code == 200
        assert response.data["done"] is True
        response = api_client.post(f"/api/v1/activities/{activity.pk}/toggle/")
        assert response.data["done"] is False

    def test_filter_by_done(self, api_client, contact):
        Activity.objects.create(subject="Yapıldı", contact=contact, done=True)
        Activity.objects.create(subject="Bekliyor", contact=contact, done=False)
        response = api_client.get("/api/v1/activities/", {"done": "true"})
        assert response.data["count"] == 1
        assert response.data["results"][0]["subject"] == "Yapıldı"


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class TestTagAPI:
    def test_crud(self, api_client):
        response = api_client.post("/api/v1/tags/", {"name": "Öncelikli", "color": "#123456"})
        assert response.status_code == 201
        tag_id = response.data["id"]
        response = api_client.get(f"/api/v1/tags/{tag_id}/")
        assert response.data["name"] == "Öncelikli"
        response = api_client.delete(f"/api/v1/tags/{tag_id}/")
        assert response.status_code == 204


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestStatsAPI:
    def test_stats_shape_and_numbers(self, api_client, company, contact):
        Deal.objects.create(title="Açık", company=company, contact=contact, value=1000, stage="new")
        Deal.objects.create(title="Kazanıldı", company=company, contact=contact, value=2000, stage="won")
        Deal.objects.create(title="Kaybedildi", company=company, contact=contact, value=500, stage="lost")

        response = api_client.get("/api/v1/stats/")
        assert response.status_code == 200
        data = response.data

        for key in (
            "companies",
            "contacts",
            "open_deals",
            "pipeline_value",
            "weighted_value",
            "won_this_month",
            "win_rate",
            "by_stage",
            "overdue_activities",
        ):
            assert key in data

        assert data["companies"] == 1
        assert data["contacts"] == 1
        assert data["open_deals"] == 1
        assert Decimal(str(data["pipeline_value"])) == Decimal("1000")
        assert data["win_rate"] == pytest.approx(0.5)
        stage_counts = {row["stage"]: row["count"] for row in data["by_stage"]}
        assert stage_counts["won"] == 1
        assert stage_counts["lost"] == 1

    def test_win_rate_null_when_no_decided_deals(self, api_client):
        response = api_client.get("/api/v1/stats/")
        assert response.data["win_rate"] is None

    def test_requires_authentication(self):
        anon = APIClient()
        response = anon.get("/api/v1/stats/")
        assert response.status_code in (401, 403)
