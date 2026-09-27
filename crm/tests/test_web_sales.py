from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from crm.models import Activity, Deal

pytestmark = [pytest.mark.django_db, pytest.mark.urls("crm.tests.sales_urls")]


# ---------------------------------------------------------------------------
# Login required
# ---------------------------------------------------------------------------


class TestLoginRequired:
    def test_dashboard_requires_login(self, client):
        response = client.get(reverse("crm:dashboard"))
        assert response.status_code == 302
        assert response.url.startswith("/login/")

    def test_deal_board_requires_login(self, client):
        response = client.get(reverse("crm:deal_board"))
        assert response.status_code == 302

    def test_activity_list_requires_login(self, client):
        response = client.get(reverse("crm:activity_list"))
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


class TestDashboard:
    def test_renders_with_data(self, auth_client, deal, user):
        Activity.objects.create(subject="Ara", owner=user, due_at=timezone.now() + timedelta(days=1))
        response = auth_client.get(reverse("crm:dashboard"))
        assert response.status_code == 200
        assert "stats" in response.context
        assert response.context["stats"]["contacts"] >= 1

    def test_dashboard_shows_overdue_and_upcoming_tasks_only_for_owner(self, auth_client, user, django_user_model):
        other = django_user_model.objects.create_user(username="other", password="pass12345")
        mine = Activity.objects.create(subject="Benim görevim", owner=user, due_at=timezone.now() + timedelta(days=1))
        Activity.objects.create(subject="Başkasının görevi", owner=other, due_at=timezone.now() + timedelta(days=1))
        far = Activity.objects.create(subject="Çok uzak", owner=user, due_at=timezone.now() + timedelta(days=30))
        response = auth_client.get(reverse("crm:dashboard"))
        tasks = list(response.context["my_tasks"])
        assert mine in tasks
        assert far not in tasks
        assert all(t.owner_id == user.pk for t in tasks)


# ---------------------------------------------------------------------------
# Deal board
# ---------------------------------------------------------------------------


class TestDealBoard:
    def test_board_renders_with_columns(self, auth_client, deal):
        response = auth_client.get(reverse("crm:deal_board"))
        assert response.status_code == 200
        stages = {col["stage"] for col in response.context["columns"]}
        assert stages == {c[0] for c in Deal.Stage.choices}

    def test_board_filters_by_owner_me(self, auth_client, user, company, contact, django_user_model):
        other = django_user_model.objects.create_user(username="someone", password="pass12345")
        Deal.objects.create(title="Bana ait", company=company, contact=contact, value=1000, owner=user)
        Deal.objects.create(title="Başkasına ait", company=company, contact=contact, value=2000, owner=other)
        response = auth_client.get(reverse("crm:deal_board"), {"owner": "me"})
        all_titles = {d.title for col in response.context["columns"] for d in col["deals"]}
        assert "Bana ait" in all_titles
        assert "Başkasına ait" not in all_titles

    def test_board_search_by_q(self, auth_client, company, contact, user):
        Deal.objects.create(title="Özel Anlaşma", company=company, contact=contact, value=1000, owner=user)
        Deal.objects.create(title="Diğer", company=company, contact=contact, value=1000, owner=user)
        response = auth_client.get(reverse("crm:deal_board"), {"q": "Özel"})
        all_titles = {d.title for col in response.context["columns"] for d in col["deals"]}
        assert all_titles == {"Özel Anlaşma"}


# ---------------------------------------------------------------------------
# Deal move
# ---------------------------------------------------------------------------


class TestDealMove:
    def test_get_not_allowed(self, auth_client, deal):
        response = auth_client.get(reverse("crm:deal_move", args=[deal.pk]))
        assert response.status_code == 405

    def test_invalid_stage_rejected(self, auth_client, deal):
        response = auth_client.post(reverse("crm:deal_move", args=[deal.pk]), {"stage": "bogus", "position": 0})
        assert response.status_code == 400
        deal.refresh_from_db()
        assert deal.stage == Deal.Stage.NEW

    def test_valid_move_updates_probability(self, auth_client, deal):
        response = auth_client.post(reverse("crm:deal_move", args=[deal.pk]), {"stage": "proposal", "position": 0})
        assert response.status_code == 200
        deal.refresh_from_db()
        assert deal.stage == "proposal"
        assert deal.probability == Deal.STAGE_PROBABILITY["proposal"]
        assert deal.closed_at is None

    def test_move_to_won_sets_closed_at(self, auth_client, deal):
        auth_client.post(reverse("crm:deal_move", args=[deal.pk]), {"stage": "won", "position": 0})
        deal.refresh_from_db()
        assert deal.stage == "won"
        assert deal.probability == 100
        assert deal.closed_at is not None

    def test_position_reorder_within_stage(self, auth_client, company, contact, user):
        common = {"company": company, "contact": contact, "value": 1, "owner": user}
        d1 = Deal.objects.create(title="D1", stage="qualified", position=0, **common)
        d2 = Deal.objects.create(title="D2", stage="qualified", position=1, **common)
        d3 = Deal.objects.create(title="D3", stage="new", position=0, **common)

        response = auth_client.post(reverse("crm:deal_move", args=[d3.pk]), {"stage": "qualified", "position": 0})
        assert response.status_code == 200

        d1.refresh_from_db()
        d2.refresh_from_db()
        d3.refresh_from_db()
        ordered = sorted([d1, d2, d3], key=lambda d: d.position)
        assert [d.pk for d in ordered] == [d3.pk, d1.pk, d2.pk]
        assert ordered[0].position == 0 and ordered[1].position == 1 and ordered[2].position == 2


# ---------------------------------------------------------------------------
# Deal CRUD
# ---------------------------------------------------------------------------


class TestDealCrud:
    def test_deal_detail_renders(self, auth_client, deal):
        response = auth_client.get(reverse("crm:deal_detail", args=[deal.pk]))
        assert response.status_code == 200
        assert response.context["deal"] == deal

    def test_deal_create(self, auth_client, company, contact, user):
        response = auth_client.post(
            reverse("crm:deal_create"),
            {
                "title": "Yeni Fırsat",
                "company": company.pk,
                "contact": contact.pk,
                "value": "1000.00",
                "currency": "TRY",
                "stage": "proposal",
                "probability": 10,  # left at model default -> should be derived from stage
                "expected_close": "2026-12-01",
            },
        )
        created = Deal.objects.get(title="Yeni Fırsat")
        assert response.status_code == 302
        assert response.url == created.get_absolute_url()
        assert created.owner == user
        assert created.probability == Deal.STAGE_PROBABILITY["proposal"]

    def test_deal_create_prefills_company_and_contact(self, auth_client, company, contact):
        response = auth_client.get(reverse("crm:deal_create"), {"company": company.pk, "contact": contact.pk})
        assert response.status_code == 200
        assert response.context["form"].initial.get("company") == str(company.pk)

    def test_deal_update(self, auth_client, deal):
        response = auth_client.post(
            reverse("crm:deal_update", args=[deal.pk]),
            {
                "title": "Güncellendi",
                "company": deal.company_id or "",
                "contact": deal.contact_id or "",
                "value": "999.00",
                "currency": "TRY",
                "stage": deal.stage,
                "probability": deal.probability,
                "expected_close": "",
            },
        )
        assert response.status_code == 302
        deal.refresh_from_db()
        assert deal.title == "Güncellendi"
        assert deal.value == Decimal("999.00")

    def test_deal_delete_get_shows_confirm(self, auth_client, deal):
        response = auth_client.get(reverse("crm:deal_delete", args=[deal.pk]))
        assert response.status_code == 200
        assert response.context["object"] == deal

    def test_deal_delete_post_deletes(self, auth_client, deal):
        response = auth_client.post(reverse("crm:deal_delete", args=[deal.pk]))
        assert response.status_code == 302
        assert not Deal.objects.filter(pk=deal.pk).exists()


# ---------------------------------------------------------------------------
# Activity filters
# ---------------------------------------------------------------------------


class TestActivityList:
    def test_open_filter_excludes_done(self, auth_client, user):
        open_act = Activity.objects.create(subject="Açık", owner=user, done=False)
        Activity.objects.create(subject="Bitti", owner=user, done=True)
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "open"})
        subjects = {a.subject for a in response.context["page_obj"]}
        assert subjects == {open_act.subject}

    def test_overdue_filter(self, auth_client, user):
        overdue = Activity.objects.create(
            subject="Geciken", owner=user, done=False, due_at=timezone.now() - timedelta(days=1)
        )
        Activity.objects.create(subject="Zamanında", owner=user, done=False, due_at=timezone.now() + timedelta(days=1))
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "overdue"})
        subjects = {a.subject for a in response.context["page_obj"]}
        assert subjects == {overdue.subject}

    def test_done_filter(self, auth_client, user):
        done = Activity.objects.create(subject="Tamamlandı", owner=user, done=True)
        Activity.objects.create(subject="Açık iş", owner=user, done=False)
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "done"})
        subjects = {a.subject for a in response.context["page_obj"]}
        assert subjects == {done.subject}

    def test_all_filter_returns_everything(self, auth_client, user):
        Activity.objects.create(subject="A", owner=user, done=True)
        Activity.objects.create(subject="B", owner=user, done=False)
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "all"})
        assert response.context["page_obj"].paginator.count == 2

    def test_mine_toggle(self, auth_client, user, django_user_model):
        other = django_user_model.objects.create_user(username="another", password="pass12345")
        Activity.objects.create(subject="Bana ait", owner=user, done=False)
        Activity.objects.create(subject="Ona ait", owner=other, done=False)
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "all", "mine": "1"})
        subjects = {a.subject for a in response.context["page_obj"]}
        assert subjects == {"Bana ait"}

    def test_pagination(self, auth_client, user):
        for i in range(30):
            Activity.objects.create(subject=f"İş {i}", owner=user, done=False)
        response = auth_client.get(reverse("crm:activity_list"), {"filter": "all"})
        assert len(response.context["page_obj"]) == 25
        assert response.context["page_obj"].paginator.num_pages == 2


# ---------------------------------------------------------------------------
# Activity create/update/delete and safe redirects
# ---------------------------------------------------------------------------


class TestActivityCrud:
    def test_activity_create_prefills_from_get(self, auth_client, deal, contact, company):
        response = auth_client.get(
            reverse("crm:activity_create"), {"deal": deal.pk, "contact": contact.pk, "company": company.pk}
        )
        assert response.status_code == 200
        initial = response.context["form"].initial
        assert initial.get("deal") == str(deal.pk)

    def test_activity_create_sets_owner(self, auth_client, user):
        response = auth_client.post(
            reverse("crm:activity_create"), {"kind": "task", "subject": "Yeni görev", "body": "", "due_at": ""}
        )
        assert response.status_code == 302
        created = Activity.objects.get(subject="Yeni görev")
        assert created.owner == user

    def test_activity_create_redirects_to_safe_next(self, auth_client):
        target = reverse("crm:activity_list") + "?filter=all"
        response = auth_client.post(
            reverse("crm:activity_create") + f"?next={target}",
            {"kind": "task", "subject": "Görev", "body": "", "due_at": ""},
        )
        assert response.status_code == 302
        assert response.url == target

    def test_activity_create_rejects_unsafe_next(self, auth_client):
        response = auth_client.post(
            reverse("crm:activity_create") + "?next=https://evil.example.com/steal",
            {"kind": "task", "subject": "Görev 2", "body": "", "due_at": ""},
        )
        assert response.status_code == 302
        assert "evil.example.com" not in response.url

    def test_activity_update(self, auth_client, user):
        activity = Activity.objects.create(subject="Eski", owner=user)
        response = auth_client.post(
            reverse("crm:activity_update", args=[activity.pk]),
            {"kind": "note", "subject": "Yeni", "body": "", "due_at": ""},
        )
        assert response.status_code == 302
        activity.refresh_from_db()
        assert activity.subject == "Yeni"

    def test_activity_delete_requires_post(self, auth_client, user):
        activity = Activity.objects.create(subject="Silinecek", owner=user)
        response = auth_client.get(reverse("crm:activity_delete", args=[activity.pk]))
        assert response.status_code == 405

    def test_activity_delete_post_removes(self, auth_client, user):
        activity = Activity.objects.create(subject="Silinecek", owner=user)
        response = auth_client.post(reverse("crm:activity_delete", args=[activity.pk]))
        assert response.status_code == 302
        assert not Activity.objects.filter(pk=activity.pk).exists()


class TestActivityToggle:
    def test_toggle_get_not_allowed(self, auth_client, user):
        activity = Activity.objects.create(subject="Görev", owner=user, done=False)
        response = auth_client.get(reverse("crm:activity_toggle", args=[activity.pk]))
        assert response.status_code == 405

    def test_toggle_htmx_returns_partial(self, auth_client, user):
        activity = Activity.objects.create(subject="Görev", owner=user, done=False)
        response = auth_client.post(reverse("crm:activity_toggle", args=[activity.pk]), HTTP_HX_REQUEST="true")
        assert response.status_code == 200
        assert f'id="activity-row-{activity.pk}"'.encode() in response.content
        activity.refresh_from_db()
        assert activity.done is True

    def test_toggle_normal_redirects(self, auth_client, user):
        activity = Activity.objects.create(subject="Görev", owner=user, done=False)
        response = auth_client.post(reverse("crm:activity_toggle", args=[activity.pk]))
        assert response.status_code == 302
        activity.refresh_from_db()
        assert activity.done is True
