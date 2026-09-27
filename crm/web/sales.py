"""Views for the sales pipeline: dashboard, deal Kanban board and activities."""

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Max, Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _

from crm.models import Activity, Deal
from crm.services import pipeline_stats

from .sales_forms import ActivityForm, DealForm

ZERO = Decimal("0")


def _safe_redirect(request, target, fallback):
    """Redirect to `target` only if it is a safe, local URL; otherwise `fallback`."""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(fallback)


@login_required
def dashboard(request):
    stats = pipeline_stats()
    now = timezone.now()
    cutoff = now + timedelta(days=7)

    my_tasks = (
        Activity.objects.filter(owner=request.user, done=False, due_at__isnull=False, due_at__lte=cutoff)
        .select_related("deal", "contact", "company")
        .order_by("due_at")[:10]
    )
    recent_activities = Activity.objects.select_related("owner", "contact", "company", "deal").order_by("-created_at")[
        :10
    ]
    top_deals = (
        Deal.objects.filter(stage__in=Deal.OPEN_STAGES).select_related("company", "owner").order_by("-value")[:5]
    )
    max_stage_value = max((row["value"] for row in stats["by_stage"]), default=ZERO)

    context = {
        "stats": stats,
        "max_stage_value": max_stage_value or Decimal("1"),
        "my_tasks": my_tasks,
        "recent_activities": recent_activities,
        "top_deals": top_deals,
        "now": now,
    }
    return render(request, "crm/dashboard.html", context)


@login_required
def deal_board(request):
    owner_filter = request.GET.get("owner", "")
    q = request.GET.get("q", "").strip()

    deals = Deal.objects.select_related("company", "contact", "owner").order_by("stage", "position", "-created_at")
    if owner_filter == "me":
        deals = deals.filter(owner=request.user)
    if q:
        deals = deals.filter(
            Q(title__icontains=q)
            | Q(company__name__icontains=q)
            | Q(contact__first_name__icontains=q)
            | Q(contact__last_name__icontains=q)
        )
    deals = list(deals)

    columns = []
    for stage_key, label in Deal.Stage.choices:
        stage_deals = [d for d in deals if d.stage == stage_key]
        total = sum((d.value for d in stage_deals), ZERO)
        columns.append(
            {"stage": stage_key, "label": label, "deals": stage_deals, "count": len(stage_deals), "total": total}
        )

    context = {"columns": columns, "q": q, "owner_filter": owner_filter}
    return render(request, "crm/deals/board.html", context)


@login_required
def deal_move(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    deal = get_object_or_404(Deal, pk=pk)
    stage = request.POST.get("stage")
    valid_stages = {choice[0] for choice in Deal.Stage.choices}
    if stage not in valid_stages:
        return JsonResponse({"detail": "invalid stage"}, status=400)

    try:
        position = int(request.POST.get("position", 0))
    except (TypeError, ValueError):
        position = 0

    deal.move_to(stage, position)

    siblings = list(Deal.objects.filter(stage=stage).exclude(pk=deal.pk).order_by("position", "id"))
    position = max(0, min(position, len(siblings)))
    siblings.insert(position, deal)
    for idx, sibling in enumerate(siblings):
        if sibling.position != idx:
            sibling.position = idx
            sibling.save(update_fields=["position"])

    total = sum((d.value for d in siblings), ZERO)
    return JsonResponse({"stage": stage, "count": len(siblings), "value": str(total)})


@login_required
def deal_detail(request, pk):
    deal = get_object_or_404(Deal.objects.select_related("company", "contact", "owner"), pk=pk)
    activities = deal.activities.select_related("owner", "contact", "company").order_by("-created_at")

    steps = [(key, label) for key, label in Deal.Stage.choices if key != Deal.Stage.LOST]
    keys = [key for key, _label in steps]
    current_index = keys.index(deal.stage) if deal.stage in keys else -1
    stepper = [
        {"stage": key, "label": label, "reached": idx <= current_index, "current": idx == current_index}
        for idx, (key, label) in enumerate(steps)
    ]

    context = {"deal": deal, "activities": activities, "stepper": stepper}
    return render(request, "crm/deals/detail.html", context)


@login_required
def deal_create(request):
    initial = {}
    for key in ("company", "contact"):
        value = request.GET.get(key)
        if value:
            initial[key] = value

    if request.method == "POST":
        form = DealForm(request.POST)
        if form.is_valid():
            deal = form.save(commit=False)
            deal.owner = request.user
            top_position = Deal.objects.filter(stage=deal.stage).aggregate(m=Max("position"))["m"]
            deal.position = 0 if top_position is None else top_position + 1
            deal.save()
            messages.success(request, _("Fırsat oluşturuldu."))
            return redirect(deal.get_absolute_url())
    else:
        form = DealForm(initial=initial)

    context = {"form": form, "cancel_url": reverse("crm:deal_board"), "title": _("Yeni Fırsat")}
    return render(request, "crm/deals/form.html", context)


@login_required
def deal_update(request, pk):
    deal = get_object_or_404(Deal, pk=pk)
    if request.method == "POST":
        form = DealForm(request.POST, instance=deal)
        if form.is_valid():
            form.save()
            messages.success(request, _("Fırsat güncellendi."))
            return redirect(deal.get_absolute_url())
    else:
        form = DealForm(instance=deal)

    context = {"form": form, "cancel_url": deal.get_absolute_url(), "title": _("Fırsatı Düzenle"), "deal": deal}
    return render(request, "crm/deals/form.html", context)


@login_required
def deal_delete(request, pk):
    deal = get_object_or_404(Deal, pk=pk)
    if request.method == "POST":
        deal.delete()
        messages.success(request, _("Fırsat silindi."))
        return redirect("crm:deal_board")
    return render(request, "crm/deals/confirm_delete.html", {"object": deal, "cancel_url": deal.get_absolute_url()})


@login_required
def activity_list(request):
    filter_key = request.GET.get("filter", "open")
    kind = request.GET.get("kind", "")
    mine = request.GET.get("mine") == "1"
    now = timezone.now()

    qs = Activity.objects.select_related("owner", "contact", "company", "deal")
    qs = qs.order_by("done", "due_at", "-created_at")
    if mine:
        qs = qs.filter(owner=request.user)
    if kind:
        qs = qs.filter(kind=kind)

    if filter_key == "open":
        qs = qs.filter(done=False)
    elif filter_key == "overdue":
        qs = qs.filter(done=False, due_at__isnull=False, due_at__lt=now)
    elif filter_key == "today":
        qs = qs.filter(done=False, due_at__date=now.date())
    elif filter_key == "done":
        qs = qs.filter(done=True)
    # filter_key == "all": no extra filtering

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    tab_choices = [
        ("open", _("Açık")),
        ("overdue", _("Geciken")),
        ("today", _("Bugün")),
        ("done", _("Tamamlanan")),
        ("all", _("Tümü")),
    ]
    context = {
        "page_obj": page_obj,
        "filter_key": filter_key,
        "kind": kind,
        "mine": mine,
        "kinds": Activity.Kind.choices,
        "tab_choices": tab_choices,
        "now": now,
    }
    return render(request, "crm/activities/list.html", context)


@login_required
def activity_create(request):
    next_url = request.GET.get("next", "")
    initial = {}
    for key in ("contact", "company", "deal"):
        value = request.GET.get(key)
        if value:
            initial[key] = value

    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.owner = request.user
            activity.save()
            messages.success(request, _("Aktivite oluşturuldu."))
            return _safe_redirect(request, next_url, reverse("crm:activity_list"))
    else:
        form = ActivityForm(initial=initial)

    context = {
        "form": form,
        "cancel_url": next_url or reverse("crm:activity_list"),
        "title": _("Yeni Aktivite"),
    }
    return render(request, "crm/activities/form.html", context)


@login_required
def activity_update(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    next_url = request.GET.get("next", "")

    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, _("Aktivite güncellendi."))
            return _safe_redirect(request, next_url, reverse("crm:activity_list"))
    else:
        form = ActivityForm(instance=activity)

    context = {
        "form": form,
        "cancel_url": next_url or reverse("crm:activity_list"),
        "title": _("Aktiviteyi Düzenle"),
        "activity": activity,
    }
    return render(request, "crm/activities/form.html", context)


@login_required
def activity_delete(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    activity = get_object_or_404(Activity, pk=pk)
    next_url = request.POST.get("next", "")
    activity.delete()
    messages.success(request, _("Aktivite silindi."))
    return _safe_redirect(request, next_url, reverse("crm:activity_list"))


@login_required
def activity_toggle(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    activity = get_object_or_404(Activity, pk=pk)
    activity.done = not activity.done
    activity.save(update_fields=["done"])

    if request.headers.get("HX-Request") == "true":
        return render(request, "crm/activities/_row.html", {"activity": activity})

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "")
    return _safe_redirect(request, next_url, reverse("crm:activity_list"))
