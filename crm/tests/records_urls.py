"""Standalone root urlconf for testing crm/web/records.py independently of sales.py.

Provides stub views for the sales-owned names that base.html and records templates
reference (dashboard, deal_board, deal_detail, deal_create, activity_create,
activity_list) plus login/logout/api-docs, so pages render without needing
crm/web/sales.py to exist yet.
"""

from django.contrib.auth import views as auth_views
from django.http import HttpResponse
from django.urls import include, path

from crm.web import records


def _stub(_request, *args, **kwargs):
    return HttpResponse("stub")


_crm_patterns = [
    path("", _stub, name="dashboard"),
    path("deals/", _stub, name="deal_board"),
    path("deals/new/", _stub, name="deal_create"),
    path("deals/<int:pk>/", _stub, name="deal_detail"),
    path("activities/", _stub, name="activity_list"),
    path("activities/new/", _stub, name="activity_create"),
    # records.py (the module under test)
    path("search/", records.global_search, name="search"),
    path("companies/", records.company_list, name="company_list"),
    path("companies/new/", records.company_create, name="company_create"),
    path("companies/<int:pk>/", records.company_detail, name="company_detail"),
    path("companies/<int:pk>/edit/", records.company_update, name="company_update"),
    path("companies/<int:pk>/delete/", records.company_delete, name="company_delete"),
    path("contacts/", records.contact_list, name="contact_list"),
    path("contacts/new/", records.contact_create, name="contact_create"),
    path("contacts/export/", records.contact_export, name="contact_export"),
    path("contacts/import/", records.contact_import, name="contact_import"),
    path("contacts/<int:pk>/", records.contact_detail, name="contact_detail"),
    path("contacts/<int:pk>/edit/", records.contact_update, name="contact_update"),
    path("contacts/<int:pk>/delete/", records.contact_delete, name="contact_delete"),
]

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("api/docs/", _stub, name="api-docs"),
    path("", include((_crm_patterns, "crm"))),
]
