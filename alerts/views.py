from django.core.paginator import Paginator
from django.shortcuts import render

from accounts.permissions import doctor_or_admin_required
from predictions.models import RiskScoreDetail


TARGET_NAMES = {
    "NEP": "Thận (NEP)",
    "NEU": "Thần kinh (NEU)",
    "RET": "Võng mạc (RET)",
    "CV": "Tim mạch (CV)",
    "PER VAS": "Mạch ngoại biên",
}


@doctor_or_admin_required
def alerts(request):
    score_qs = (
        RiskScoreDetail.objects.filter(risk_label=1)
        .select_related("prediction", "prediction__patient")
        .order_by("-prediction__created_at")
    )
    paginator = Paginator(score_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    alert_rows = [
        {
            "id": f"AL-{score.id}",
            "patient": score.prediction.patient,
            "prediction": score.prediction,
            "target": TARGET_NAMES.get(score.target, score.target),
            "risk_level": score.risk_level,
            "risk_score": score.risk_score,
            "risk_percent": round(score.risk_score * 100, 1),
            "message": score.prediction.warning_message,
            "created_at": score.prediction.created_at,
        }
        for score in page_obj.object_list
    ]
    return render(
        request,
        "alerts/alerts.html",
        {
            "alerts": alert_rows,
            "high_count": score_qs.filter(risk_level="high").count(),
            "pending_count": score_qs.count(),
            "monitoring_count": score_qs.exclude(risk_level="high").count(),
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )
