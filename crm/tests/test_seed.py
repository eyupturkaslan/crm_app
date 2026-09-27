import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from crm.models import Activity, Company, Contact, Deal, Tag

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_expected_data():
    call_command("seed_demo")

    assert Tag.objects.count() == 6
    assert Company.objects.count() == 15
    assert Contact.objects.count() == 40
    assert Deal.objects.count() == 30
    assert Activity.objects.count() == 50

    User = get_user_model()
    demo = User.objects.get(username="demo")
    assert demo.is_superuser
    assert demo.check_password("demo12345")


def test_seed_demo_is_rerunnable_without_duplicating_lookup_data():
    call_command("seed_demo")
    call_command("seed_demo")

    # Tags/companies/contacts are get_or_create'd on stable keys, so a second
    # run without --reset should not duplicate them.
    assert Tag.objects.count() == 6
    assert Company.objects.count() == 15
    assert Contact.objects.count() == 40
    assert get_user_model().objects.filter(username="demo").count() == 1


def test_seed_demo_reset_flag_wipes_before_reseeding():
    call_command("seed_demo")
    call_command("seed_demo", "--reset")

    assert Company.objects.count() == 15
    assert Deal.objects.count() == 30


def test_seed_demo_has_overdue_and_upcoming_activities():
    call_command("seed_demo", "--reset")

    overdue = [a for a in Activity.objects.all() if a.is_overdue]
    upcoming = Activity.objects.filter(done=False, due_at__isnull=False).exclude(id__in=[a.id for a in overdue])

    assert len(overdue) > 0
    assert upcoming.exists()


def test_seed_demo_deals_span_multiple_stages():
    call_command("seed_demo", "--reset")

    stages = set(Deal.objects.values_list("stage", flat=True))
    assert len(stages) >= 3
