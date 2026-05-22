from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Alert, AlertStatus, WatchlistItem, WatchlistStatus


TARGETS = [
    ("", "Tất cả biến chứng"),
    ("NEP", "NEP"),
    ("NEU", "NEU"),
    ("RET", "RET"),
    ("CV", "CV"),
    ("PER VAS", "PER VAS"),
]


@login_required(login_url="login")
def alerts(request):
    level = request.GET.get("level", "")
    target = request.GET.get("target", "")
    status = request.GET.get("status", "")
    rows = Alert.objects.select_related("patient", "prediction", "score").all()
    if level:
        rows = rows.filter(level=level)
    if target:
        rows = rows.filter(target=target)
    if status:
        rows = rows.filter(status=status)
    page = Paginator(rows, 10).get_page(request.GET.get("page"))
    watch = WatchlistItem.objects.select_related("patient", "score").filter(status=WatchlistStatus.OPEN)[:10]
    ctx = {
        "alerts": page.object_list,
        "page_obj": page,
        "paginator": page.paginator,
        "watchlist": watch,
        "targets": TARGETS,
        "levels": [("", "Tất cả mức độ"), ("high", "high")],
        "statuses": [
            ("", "Tất cả trạng thái"),
            (AlertStatus.NEW, "Chưa xử lý"),
            (AlertStatus.ACKNOWLEDGED, "Đã xác nhận"),
            (AlertStatus.WATCHING, "Đang theo dõi"),
            (AlertStatus.RESOLVED, "Đã xử lý"),
        ],
        "filters": {"level": level, "target": target, "status": status},
        "total_open": Alert.objects.exclude(status=AlertStatus.RESOLVED).count(),
        "total_new": Alert.objects.filter(status=AlertStatus.NEW).count(),
        "total_ack": Alert.objects.filter(status=AlertStatus.ACKNOWLEDGED).count(),
        "total_watching": Alert.objects.filter(status=AlertStatus.WATCHING).count(),
        "total_watchlist": WatchlistItem.objects.filter(status=WatchlistStatus.OPEN).count(),
    }
    return render(request, "alerts/alerts.html", ctx)


@login_required(login_url="login")
def watchlist(request):
    q = request.GET.get("q", "").strip()
    target = request.GET.get("target", "")
    status = request.GET.get("status", "")
    rows = WatchlistItem.objects.select_related("patient", "prediction", "score").all()
    if q:
        rows = rows.filter(Q(patient__name__icontains=q) | Q(patient__id__icontains=q))
    if target:
        rows = rows.filter(target=target)
    if status:
        rows = rows.filter(status=status)
    page = Paginator(rows, 20).get_page(request.GET.get("page"))
    ctx = {
        "watchlist": page.object_list,
        "page_obj": page,
        "paginator": page.paginator,
        "targets": TARGETS,
        "statuses": [
            ("", "Tất cả trạng thái"),
            (WatchlistStatus.OPEN, "open"),
            (WatchlistStatus.REVIEWED, "reviewed"),
        ],
        "filters": {"q": q, "target": target, "status": status},
        "total_open": WatchlistItem.objects.filter(status=WatchlistStatus.OPEN).count(),
        "total_reviewed": WatchlistItem.objects.filter(status=WatchlistStatus.REVIEWED).count(),
    }
    return render(request, "alerts/watchlist.html", ctx)


@login_required(login_url="login")
@require_POST
def update_status(request, pk):
    alert = get_object_or_404(Alert, pk=pk)
    status = request.POST.get("status", AlertStatus.NEW)
    note = request.POST.get("doctor_note", "").strip()
    fields = ["status", "updated_at"]
    if status in AlertStatus.values:
        alert.status = status
        if status in [AlertStatus.ACKNOWLEDGED, AlertStatus.WATCHING, AlertStatus.RESOLVED] and not alert.acknowledged_at:
            alert.acknowledged_at = timezone.now()
            fields.append("acknowledged_at")
        if status == AlertStatus.RESOLVED:
            alert.resolved_at = timezone.now()
            fields.append("resolved_at")
        elif alert.resolved_at:
            alert.resolved_at = None
            fields.append("resolved_at")
    if note != alert.doctor_note:
        alert.doctor_note = note
        fields.append("doctor_note")
    alert.save(update_fields=fields)
    nxt = request.META.get("HTTP_REFERER")
    return redirect(nxt or "alerts")


@login_required(login_url="login")
@require_POST
def update_watchlist(request, pk):
    item = get_object_or_404(WatchlistItem, pk=pk)
    status = request.POST.get("status", WatchlistStatus.OPEN)
    note = request.POST.get("doctor_note", "").strip()
    fields = ["status", "updated_at"]
    if status in WatchlistStatus.values:
        item.status = status
        if status == WatchlistStatus.REVIEWED:
            item.reviewed_at = timezone.now()
            fields.append("reviewed_at")
        elif item.reviewed_at:
            item.reviewed_at = None
            fields.append("reviewed_at")
    if note != item.doctor_note:
        item.doctor_note = note
        fields.append("doctor_note")
    item.save(update_fields=fields)
    nxt = request.META.get("HTTP_REFERER")
    return redirect(nxt or "watchlist")
