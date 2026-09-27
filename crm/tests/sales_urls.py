"""Minimal URLconf for sales-view tests, independent from crm.web.records (owned by another agent)."""

from django.http import HttpResponse
from django.urls import include, path

from crm.web import sales


def _stub(request, *args, **kwargs):
    return HttpResponse("stub")


patterns = [
    path("", sales.dashboard, name="dashboard"),
    path("deals/", sales.deal_board, name="deal_board"),
    path("deals/new/", sales.deal_create, name="deal_create"),
    path("deals/<int:pk>/", sales.deal_detail, name="deal_detail"),
    path("deals/<int:pk>/edit/", sales.deal_update, name="deal_update"),
    path("deals/<int:pk>/delete/", sales.deal_delete, name="deal_delete"),
    path("deals/<int:pk>/move/", sales.deal_move, name="deal_move"),
    path("activities/", sales.activity_list, name="activity_list"),
    path("activities/new/", sales.activity_create, name="activity_create"),
    path("activities/<int:pk>/edit/", sales.activity_update, name="activity_update"),
    path("activities/<int:pk>/toggle/", sales.activity_toggle, name="activity_toggle"),
    path("activities/<int:pk>/delete/", sales.activity_delete, name="activity_delete"),
    # Stubs for records.py (owned by another agent), so base.html and reverse() resolve.
    path("search/", _stub, name="search"),
    path("companies/", _stub, name="company_list"),
    path("companies/new/", _stub, name="company_create"),
    path("companies/<int:pk>/", _stub, name="company_detail"),
    path("contacts/", _stub, name="contact_list"),
    path("contacts/new/", _stub, name="contact_create"),
    path("contacts/<int:pk>/", _stub, name="contact_detail"),
]

urlpatterns = [
    path("", include((patterns, "crm"))),
    path("login/", _stub, name="login"),
    path("logout/", _stub, name="logout"),
    path("api/docs/", _stub, name="api-docs"),
]
