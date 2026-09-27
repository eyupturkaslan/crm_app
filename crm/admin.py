from django.contrib import admin

from .models import Activity, Company, Contact, Deal, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "color"]
    search_fields = ["name"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "industry", "city", "owner", "created_at"]
    list_filter = ["industry", "size"]
    search_fields = ["name", "domain"]
    filter_horizontal = ["tags"]


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ["full_name", "email", "company", "lifecycle_stage", "score", "marketing_consent"]
    list_filter = ["lifecycle_stage", "source", "marketing_consent"]
    search_fields = ["first_name", "last_name", "email", "phone"]
    autocomplete_fields = ["company"]
    filter_horizontal = ["tags"]
    readonly_fields = ["score", "consent_at"]


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["title", "company", "stage", "value", "currency", "probability", "expected_close"]
    list_filter = ["stage", "currency"]
    search_fields = ["title"]
    autocomplete_fields = ["company", "contact"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["subject", "kind", "due_at", "done", "owner"]
    list_filter = ["kind", "done"]
    search_fields = ["subject", "body"]
