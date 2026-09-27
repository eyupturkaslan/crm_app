from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from crm.models import Activity, Contact, Deal

pytestmark = pytest.mark.django_db


class TestContactScoreAndConsent:
    def test_score_increases_with_signals(self, company, user):
        bare = Contact.objects.create(first_name="Boş", owner=user)
        rich = Contact.objects.create(
            first_name="Dolu",
            email="dolu@example.com",
            phone="0555 111 22 33",
            company=company,
            job_title="Müdür",
            marketing_consent=True,
            source=Contact.Source.REFERRAL,
            lifecycle_stage=Contact.Lifecycle.CUSTOMER,
            owner=user,
        )
        assert bare.score == 0
        assert rich.score == min(15 + 10 + 10 + 10 + 15 + 20 + 20, 100)

    def test_consent_at_set_when_consent_true(self, user):
        contact = Contact.objects.create(first_name="Ayşe", marketing_consent=True, owner=user)
        assert contact.consent_at is not None

    def test_consent_at_cleared_when_consent_false(self, user):
        contact = Contact.objects.create(first_name="Ayşe", marketing_consent=True, owner=user)
        assert contact.consent_at is not None
        contact.marketing_consent = False
        contact.save()
        assert contact.consent_at is None

    def test_consent_at_not_overwritten_on_resave(self, user):
        contact = Contact.objects.create(first_name="Ayşe", marketing_consent=True, owner=user)
        first_consent_at = contact.consent_at
        contact.notes = "güncellendi"
        contact.save()
        assert contact.consent_at == first_consent_at


class TestDealLifecycle:
    def test_weighted_value(self, deal):
        deal.value = Decimal("1000")
        deal.probability = 25
        assert deal.weighted_value == Decimal("250")

    def test_is_open_for_open_stage(self, deal):
        assert deal.stage == Deal.Stage.NEW
        assert deal.is_open is True

    def test_closed_at_set_when_won(self, deal):
        assert deal.closed_at is None
        deal.move_to(Deal.Stage.WON)
        deal.refresh_from_db()
        assert deal.closed_at is not None
        assert deal.is_open is False

    def test_closed_at_cleared_when_reopened(self, deal):
        deal.move_to(Deal.Stage.WON)
        deal.move_to(Deal.Stage.NEW)
        deal.refresh_from_db()
        assert deal.closed_at is None

    def test_move_to_updates_probability_and_position(self, deal):
        deal.move_to(Deal.Stage.NEGOTIATION, position=3)
        deal.refresh_from_db()
        assert deal.stage == Deal.Stage.NEGOTIATION
        assert deal.probability == Deal.STAGE_PROBABILITY["negotiation"]
        assert deal.position == 3


class TestActivityOverdue:
    def test_overdue_when_past_due_and_not_done(self, contact, user):
        activity = Activity.objects.create(
            subject="Ara", due_at=timezone.now() - timedelta(days=1), done=False, contact=contact, owner=user
        )
        assert activity.is_overdue is True

    def test_not_overdue_when_done(self, contact, user):
        activity = Activity.objects.create(
            subject="Ara", due_at=timezone.now() - timedelta(days=1), done=True, contact=contact, owner=user
        )
        assert activity.is_overdue is False

    def test_not_overdue_when_no_due_date(self, contact, user):
        activity = Activity.objects.create(subject="Not al", contact=contact, owner=user)
        assert activity.is_overdue is False

    def test_not_overdue_when_in_future(self, contact, user):
        activity = Activity.objects.create(
            subject="Ara", due_at=timezone.now() + timedelta(days=1), contact=contact, owner=user
        )
        assert activity.is_overdue is False
