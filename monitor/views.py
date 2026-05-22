from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Max
from django.shortcuts import render
from django.utils import timezone

from predictions.models import PredictionResult, RequestLog, RiskScoreDetail


@login_required(login_url="login")
def monitor(request):
    since = timezone.now() - timezone.timedelta(hours=24)
    logs = RequestLog.objects.filter(created_at__gte=since)
    total_requests = logs.count()
    error_count = logs.filter(status_code__gte=400).count()
    avg_latency = logs.aggregate(value=Avg("latency_ms"))["value"] or 0
    max_latency = logs.aggregate(value=Max("latency_ms"))["value"] or 0
    error_rate = (error_count / total_requests * 100) if total_requests else 0
    api_status = "Healthy" if error_rate < 5 else "Degraded"

    recent_predictions = PredictionResult.objects.filter(created_at__gte=since).count()
    positive_scores = RiskScoreDetail.objects.filter(prediction__created_at__gte=since, risk_label=1)
    total_scores = RiskScoreDetail.objects.filter(prediction__created_at__gte=since).count()
    positive_rate = (positive_scores.count() / total_scores * 100) if total_scores else 0
    latest_prediction = PredictionResult.objects.order_by("-created_at").first()
    latest_log = RequestLog.objects.order_by("-created_at").first()
    request_rate = round(total_requests / (24 * 60), 2) if total_requests else 0
    latency_width = min(100, int(max_latency or avg_latency or 0))
    model_health = "Stable" if positive_rate < 50 else "Needs review"

    return render(
        request,
        "monitor/monitoring.html",
        {
            "api_status": api_status,
            "total_requests": total_requests,
            "request_rate": request_rate,
            "error_count": error_count,
            "error_rate": error_rate,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "latency_width": latency_width,
            "recent_predictions": recent_predictions,
            "positive_rate": positive_rate,
            "model_health": model_health,
            "latest_prediction": latest_prediction,
            "latest_log": latest_log,
        },
    )
