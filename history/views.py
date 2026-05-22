from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from predictions.models import PredictionResult

TARGET_NAMES = {
    "NEP": "Nephropathy",
    "NEU": "Neuropathy",
    "RET": "Retinopathy",
    "CV": "Cardiovascular",
    "PER VAS": "Peripheral vascular",
}


# Create your views here.
@login_required(login_url="login")
def history(request):
    prediction_list = (
        PredictionResult.objects.select_related("patient")
        .prefetch_related("scores")
        .order_by("-created_at")
    )
    paginator = Paginator(prediction_list, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    rows = []
    for prediction in page_obj.object_list:
        scores = {score.target: score for score in prediction.scores.all()}
        rows.append(
            {
                "prediction": prediction,
                "nep": scores.get("NEP"),
                "neu": scores.get("NEU"),
                "ret": scores.get("RET"),
                "cv": scores.get("CV"),
                "per_vas": scores.get("PER VAS"),
            }
        )

    return render(
        request,
        "history/prediction_history.html",
        {
            "rows": rows,
            "page_obj": page_obj,
            "paginator": paginator,
            "model_versions": list(dict.fromkeys(PredictionResult.objects.order_by("-created_at").values_list("model_version", flat=True))),
        },
    )


@login_required(login_url="login")
def history_detail(request, pk=None):
    if pk is None:
        latest = PredictionResult.objects.order_by("-created_at").first()
        if latest:
            return redirect("history_detail", pk=latest.pk)
        return redirect("history")

    prediction = get_object_or_404(
        PredictionResult.objects.select_related("patient", "clinical_record").prefetch_related("scores", "request_logs"),
        pk=pk,
    )
    score_rows = []
    for score in prediction.scores.all():
        pct = round(float(score.risk_score) * 100, 1)
        if score.risk_level == "high":
            color = "error"
        elif score.risk_level == "medium":
            color = "warning"
        else:
            color = "low"
        score_rows.append(
            {
                "target": score.target,
                "target_name": TARGET_NAMES.get(score.target, score.target),
                "score": score,
                "percent": pct,
                "dash": f"{pct}, 100",
                "color": color,
                "risk_text": "High risk" if score.risk_level == "high" else "Medium risk" if score.risk_level == "medium" else "Low risk",
            }
        )

    record = prediction.clinical_record
    features = [
        ("AGE", record.age, "years", "-"),
        ("BMI", record.bmi, "kg/m2", "18.5 - 24.9"),
        ("SP", record.sp, "mmHg", "< 120"),
        ("BP", record.bp, "mmHg", "< 80"),
        ("HbA1c", record.hba1c, "%", "< 5.7"),
        ("FPS", record.fps, "mg/dL", "70 - 99"),
        ("PPS", record.pps, "mg/dL", "-"),
        ("ONSET AGE", record.on_age, "years", "-"),
        ("DIA LIFE", record.dia_life, "years", "-"),
        ("FAMILY H/O", record.fam_ho, "", "-"),
        ("SMOKING", record.smk, "", "-"),
        ("PHY ACT", record.phy_act, "", "-"),
        ("MED USE", record.med_use, "", "-"),
        ("MED ADH", record.med_adh, "", "-"),
    ]
    request_log = prediction.request_logs.order_by("-created_at").first()
    alert_scores = [row for row in score_rows if row["score"].risk_label]
    return render(
        request,
        "history/prediction_detail.html",
        {
            "prediction": prediction,
            "patient": prediction.patient,
            "record": record,
            "score_rows": score_rows,
            "features": features,
            "request_log": request_log,
            "alert_scores": alert_scores,
        },
    )
