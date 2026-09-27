"""Aggregate reporting helpers shared by the API and the web dashboard."""

from decimal import Decimal

from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from crm.models import Activity, Company, Contact, Deal


def pipeline_stats():
    """Return a plain dict of pipeline/CRM stats.

    Keys (kept stable so the web dashboard can reuse them):
    companies, contacts, open_deals, pipeline_value, weighted_value,
    won_this_month, win_rate, by_stage, overdue_activities
    """
    now = timezone.now()

    companies = Company.objects.count()
    contacts = Contact.objects.count()

    open_deals_qs = Deal.objects.filter(stage__in=Deal.OPEN_STAGES)
    open_deals = open_deals_qs.count()

    zero = Decimal("0")
    pipeline_value = open_deals_qs.aggregate(
        total=Coalesce(Sum("value"), zero, output_field=DecimalField(max_digits=14, decimal_places=2))
    )["total"]
    weighted_value = sum((deal.weighted_value for deal in open_deals_qs), zero)

    won_this_month = Deal.objects.filter(
        stage=Deal.Stage.WON,
        closed_at__year=now.year,
        closed_at__month=now.month,
    ).aggregate(total=Coalesce(Sum("value"), zero, output_field=DecimalField(max_digits=14, decimal_places=2)))["total"]

    won_count = Deal.objects.filter(stage=Deal.Stage.WON).count()
    lost_count = Deal.objects.filter(stage=Deal.Stage.LOST).count()
    decided = won_count + lost_count
    win_rate = round(won_count / decided, 4) if decided else None

    by_stage = []
    stage_rows = {
        row["stage"]: row
        for row in Deal.objects.values("stage").annotate(
            count=Count("id"),
            value=Coalesce(Sum("value"), zero, output_field=DecimalField(max_digits=14, decimal_places=2)),
        )
    }
    labels = dict(Deal.Stage.choices)
    for stage_key, label in labels.items():
        row = stage_rows.get(stage_key)
        by_stage.append(
            {
                "stage": stage_key,
                "label": str(label),
                "count": row["count"] if row else 0,
                "value": row["value"] if row else zero,
            }
        )

    overdue_activities = Activity.objects.filter(done=False, due_at__isnull=False, due_at__lt=now).count()

    return {
        "companies": companies,
        "contacts": contacts,
        "open_deals": open_deals,
        "pipeline_value": pipeline_value,
        "weighted_value": weighted_value,
        "won_this_month": won_this_month,
        "win_rate": win_rate,
        "by_stage": by_stage,
        "overdue_activities": overdue_activities,
    }
