"""Views for companies, contacts, global search and CSV import/export."""

import csv
import io
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, DecimalField, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from crm.models import Company, Contact, Deal

from .forms import CompanyForm, ContactForm, ContactImportForm

PAGE_SIZE = 25
ZERO = Decimal("0")


def _querystring_without_page(request):
    qs = request.GET.copy()
    qs.pop("page", None)
    return qs.urlencode()


# --------------------------------------------------------------------------
# Companies
# --------------------------------------------------------------------------


@login_required
def company_list(request):
    q = (request.GET.get("q") or "").strip()
    industry = (request.GET.get("industry") or "").strip()

    companies = (
        Company.objects.select_related("owner")
        .annotate(
            contacts_count=Count("contacts", distinct=True),
            deals_count=Count("deals", distinct=True),
        )
        .order_by("name")
    )
    if q:
        companies = companies.filter(Q(name__icontains=q) | Q(domain__icontains=q) | Q(city__icontains=q))
    if industry:
        companies = companies.filter(industry=industry)

    paginator = Paginator(companies, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    industries = Company.objects.exclude(industry="").order_by("industry").values_list("industry", flat=True).distinct()
    context = {
        "page_obj": page_obj,
        "q": q,
        "industry": industry,
        "industries": industries,
        "qs": _querystring_without_page(request),
    }
    template = "crm/companies/_table.html" if request.headers.get("HX-Request") else "crm/companies/list.html"
    return render(request, template, context)


@login_required
def company_detail(request, pk):
    company = get_object_or_404(Company.objects.select_related("owner").prefetch_related("tags"), pk=pk)
    contacts = company.contacts.select_related("owner").order_by("first_name", "last_name")
    deals = company.deals.select_related("contact", "owner")
    open_pipeline_value = deals.filter(stage__in=Deal.OPEN_STAGES).aggregate(
        total=Coalesce(Sum("value"), ZERO, output_field=DecimalField(max_digits=14, decimal_places=2))
    )["total"]
    activities = company.activities.select_related("owner")[:20]
    context = {
        "company": company,
        "contacts": contacts,
        "deals": deals,
        "open_pipeline_value": open_pipeline_value,
        "activities": activities,
    }
    return render(request, "crm/companies/detail.html", context)


@login_required
def company_create(request):
    if request.method == "POST":
        form = CompanyForm(request.POST)
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            form.save_m2m()
            messages.success(request, _("Firma oluşturuldu."))
            return redirect("crm:company_detail", pk=company.pk)
    else:
        form = CompanyForm()
    return render(request, "crm/companies/form.html", {"form": form, "cancel_url": reverse("crm:company_list")})


@login_required
def company_update(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == "POST":
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, _("Firma güncellendi."))
            return redirect("crm:company_detail", pk=company.pk)
    else:
        form = CompanyForm(instance=company)
    context = {
        "form": form,
        "company": company,
        "cancel_url": reverse("crm:company_detail", args=[company.pk]),
    }
    return render(request, "crm/companies/form.html", context)


@login_required
def company_delete(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == "POST":
        company.delete()
        messages.success(request, _("Firma silindi."))
        return redirect("crm:company_list")
    context = {"object": company, "cancel_url": reverse("crm:company_detail", args=[company.pk])}
    return render(request, "crm/_confirm_delete.html", context)


# --------------------------------------------------------------------------
# Contacts
# --------------------------------------------------------------------------


def _filter_contacts(request):
    q = (request.GET.get("q") or "").strip()
    lifecycle_stage = (request.GET.get("lifecycle_stage") or "").strip()
    owner_me = request.GET.get("owner") == "me"

    contacts = Contact.objects.select_related("company", "owner").prefetch_related("tags")
    if q:
        contacts = contacts.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
        )
    if lifecycle_stage:
        contacts = contacts.filter(lifecycle_stage=lifecycle_stage)
    if owner_me and request.user.is_authenticated:
        contacts = contacts.filter(owner=request.user)

    filters = {"q": q, "lifecycle_stage": lifecycle_stage, "owner_me": owner_me}
    return contacts, filters


@login_required
def contact_list(request):
    contacts, filters = _filter_contacts(request)
    paginator = Paginator(contacts, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    context = {
        "page_obj": page_obj,
        "lifecycle_choices": Contact.Lifecycle.choices,
        "qs": _querystring_without_page(request),
        **filters,
    }
    template = "crm/contacts/_table.html" if request.headers.get("HX-Request") else "crm/contacts/list.html"
    return render(request, template, context)


@login_required
def contact_detail(request, pk):
    contact = get_object_or_404(Contact.objects.select_related("company", "owner").prefetch_related("tags"), pk=pk)
    deals = contact.deals.select_related("company", "owner")
    activities = contact.activities.select_related("owner")[:20]
    context = {"contact": contact, "deals": deals, "activities": activities}
    return render(request, "crm/contacts/detail.html", context)


@login_required
def contact_create(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.owner = request.user
            contact.save()
            form.save_m2m()
            messages.success(request, _("Kişi oluşturuldu."))
            return redirect("crm:contact_detail", pk=contact.pk)
    else:
        initial = {}
        company_id = request.GET.get("company")
        if company_id:
            initial["company"] = company_id
        form = ContactForm(initial=initial)
    return render(request, "crm/contacts/form.html", {"form": form, "cancel_url": reverse("crm:contact_list")})


@login_required
def contact_update(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == "POST":
        form = ContactForm(request.POST, instance=contact)
        if form.is_valid():
            form.save()
            messages.success(request, _("Kişi güncellendi."))
            return redirect("crm:contact_detail", pk=contact.pk)
    else:
        form = ContactForm(instance=contact)
    context = {
        "form": form,
        "contact": contact,
        "cancel_url": reverse("crm:contact_detail", args=[contact.pk]),
    }
    return render(request, "crm/contacts/form.html", context)


@login_required
def contact_delete(request, pk):
    contact = get_object_or_404(Contact, pk=pk)
    if request.method == "POST":
        contact.delete()
        messages.success(request, _("Kişi silindi."))
        return redirect("crm:contact_list")
    context = {"object": contact, "cancel_url": reverse("crm:contact_detail", args=[contact.pk])}
    return render(request, "crm/_confirm_delete.html", context)


class _Echo:
    """A file-like object that just returns what it's given (for streaming CSV)."""

    def write(self, value):
        return value


@login_required
def contact_export(request):
    contacts, _filters = _filter_contacts(request)
    contacts = contacts.order_by("first_name", "last_name")

    def rows():
        writer = csv.writer(_Echo())
        yield "﻿"
        yield writer.writerow(
            ["Ad", "Soyad", "E-posta", "Telefon", "Unvan", "Firma", "Yaşam Döngüsü", "Kaynak", "Skor"]
        )
        for contact in contacts:
            yield writer.writerow(
                [
                    contact.first_name,
                    contact.last_name,
                    contact.email,
                    contact.phone,
                    contact.job_title,
                    contact.company.name if contact.company_id else "",
                    contact.get_lifecycle_stage_display(),
                    contact.get_source_display(),
                    contact.score,
                ]
            )

    response = StreamingHttpResponse(rows(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="contacts.csv"'
    return response


@login_required
def contact_import(request):
    if request.method == "POST":
        form = ContactImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data["csv_file"]
            try:
                decoded = csv_file.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                messages.error(request, _("Dosya UTF-8 formatında olmalı."))
                return redirect("crm:contact_import")

            reader = csv.DictReader(io.StringIO(decoded))
            valid_stages = {value for value, _label in Contact.Lifecycle.choices}
            valid_sources = {value for value, _label in Contact.Source.choices}
            created = updated = skipped = 0

            with transaction.atomic():
                for row in reader:
                    first_name = (row.get("first_name") or "").strip()
                    if not first_name:
                        skipped += 1
                        continue

                    company_obj = None
                    company_name = (row.get("company") or "").strip()
                    if company_name:
                        company_obj, _created = Company.objects.get_or_create(
                            name=company_name, defaults={"owner": request.user}
                        )

                    lifecycle_stage = (row.get("lifecycle_stage") or "").strip()
                    if lifecycle_stage not in valid_stages:
                        lifecycle_stage = Contact.Lifecycle.LEAD

                    source = (row.get("source") or "").strip()
                    if source not in valid_sources:
                        source = Contact.Source.OTHER

                    fields = {
                        "first_name": first_name,
                        "last_name": (row.get("last_name") or "").strip(),
                        "phone": (row.get("phone") or "").strip(),
                        "job_title": (row.get("job_title") or "").strip(),
                        "company": company_obj,
                        "lifecycle_stage": lifecycle_stage,
                        "source": source,
                    }
                    email = (row.get("email") or "").strip().lower()

                    existing = Contact.objects.filter(email=email).first() if email else None
                    if existing:
                        for key, value in fields.items():
                            setattr(existing, key, value)
                        existing.save()
                        updated += 1
                    else:
                        Contact.objects.create(email=email, owner=request.user, **fields)
                        created += 1

            messages.success(
                request,
                _("%(created)d oluşturuldu, %(updated)d güncellendi, %(skipped)d atlandı.")
                % {"created": created, "updated": updated, "skipped": skipped},
            )
            return redirect("crm:contact_list")
    else:
        form = ContactImportForm()
    return render(request, "crm/contacts/import.html", {"form": form, "cancel_url": reverse("crm:contact_list")})


# --------------------------------------------------------------------------
# Global search
# --------------------------------------------------------------------------


@login_required
def global_search(request):
    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return HttpResponse("")

    contacts = Contact.objects.filter(
        Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q)
    ).select_related("company")[:5]
    companies = Company.objects.filter(Q(name__icontains=q) | Q(domain__icontains=q))[:5]
    deals = Deal.objects.filter(title__icontains=q).select_related("company")[:5]

    context = {"q": q, "contacts": contacts, "companies": companies, "deals": deals}
    return render(request, "crm/_search_results.html", context)
