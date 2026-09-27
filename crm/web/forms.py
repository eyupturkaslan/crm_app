"""Forms for companies and contacts (records)."""

from django import forms
from django.utils.translation import gettext_lazy as _

from crm.models import Company, Contact


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        # All Company fields except owner (set from request.user in the view).
        fields = ["name", "domain", "industry", "size", "phone", "address", "city", "country", "tags"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        # All Contact fields except owner/score/consent_at (owner/score/consent_at are set elsewhere).
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "job_title",
            "company",
            "lifecycle_stage",
            "source",
            "preferred_channel",
            "marketing_consent",
            "notes",
            "tags",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ContactImportForm(forms.Form):
    csv_file = forms.FileField(
        label=_("CSV dosyası"),
        help_text=_("Sütunlar: first_name, last_name, email, phone, job_title, company, lifecycle_stage, source"),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data["csv_file"]
        if not csv_file.name.lower().endswith(".csv"):
            raise forms.ValidationError(_("Lütfen bir CSV dosyası yükleyin."))
        max_size = 5 * 1024 * 1024
        if csv_file.size > max_size:
            raise forms.ValidationError(_("Dosya boyutu 5MB'ı aşamaz."))
        return csv_file
