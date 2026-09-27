"""Web UI URL contract.

`records` owns companies, contacts, search and CSV; `sales` owns dashboard, deals and activities.
"""

from django.urls import path

from . import records, sales

app_name = "crm"

urlpatterns = [
    # sales.py
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
    # records.py
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
