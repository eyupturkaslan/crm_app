"""Forms for deals and activities (sales pipeline)."""

from django import forms

from crm.models import Activity, Deal


class DealForm(forms.ModelForm):
    class Meta:
        model = Deal
        exclude = ["owner", "closed_at", "position"]  # noqa: DJ006
        widgets = {
            "expected_close": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["expected_close"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned_data = super().clean()
        stage = cleaned_data.get("stage")
        probability = cleaned_data.get("probability")
        default_probability = self._meta.model._meta.get_field("probability").default
        if stage and (probability is None or probability == default_probability):
            cleaned_data["probability"] = Deal.STAGE_PROBABILITY.get(stage, probability)
        return cleaned_data


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        exclude = ["owner"]  # noqa: DJ006
        widgets = {
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["due_at"].input_formats = ["%Y-%m-%dT%H:%M"]
