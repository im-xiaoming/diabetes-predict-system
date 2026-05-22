import os
import tempfile
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_POST

from patients.models import ClinicalRecord, Patient
from predictions.models import PredictionResult, RiskScoreDetail
from . import services


TARGET_FIELDS = {
    "NEP": "nep",
    "NEU": "neu",
    "RET": "ret",
    "CV": "cv",
    "PER VAS": "per_vas",
}

COMPLICATION_NAMES = {
    "NEP": "Thận (NEP)",
    "NEU": "Thần kinh (NEU)",
    "RET": "Võng mạc (RET)",
    "CV": "Tim mạch (CV)",
    "PER VAS": "Mạch ngoại biên",
}


def _micro_f1_for_predictions(predictions):
    tp = fp = fn = 0
    for prediction in predictions:
        label = getattr(prediction.clinical_record, "label", None)
        if not label:
            continue
        scores = {score.target: score for score in prediction.scores.all()}
        for target, field in TARGET_FIELDS.items():
            truth = bool(getattr(label, field))
            predicted = bool(getattr(scores.get(target), "risk_label", 0))
            if predicted and truth:
                tp += 1
            elif predicted and not truth:
                fp += 1
            elif not predicted and truth:
                fn += 1
    denom = (2 * tp) + fp + fn
    return (2 * tp / denom) if denom else None


@login_required(login_url="login")
def dashboard(request):
    now = timezone.now()
    total_patient = Patient.objects.count()
    total_profile = ClinicalRecord.objects.count()
    total_prediction = PredictionResult.objects.count()
    today_profile = ClinicalRecord.objects.filter(created_at__date=now.date()).count()
    patient_30d = Patient.objects.filter(created_at__gte=now - timezone.timedelta(days=30)).count()
    prev_patient_30d = Patient.objects.filter(
        created_at__gte=now - timezone.timedelta(days=60),
        created_at__lt=now - timezone.timedelta(days=30),
    ).count()
    patient_growth = ((patient_30d - prev_patient_30d) / prev_patient_30d * 100) if prev_patient_30d else None

    alert_predictions = (
        PredictionResult.objects.filter(risk_level__in=["high", "very_high"])
        .select_related("patient", "clinical_record")
        .prefetch_related("scores")
        .order_by("-created_at")
    )

    alert_patients = []
    for prediction in alert_predictions[:5]:
        scores = list(prediction.scores.all())
        complications = [COMPLICATION_NAMES.get(score.target, score.target) for score in scores if score.risk_label]
        max_score = max([score.risk_score for score in scores], default=0)
        alert_patients.append(
            {
                "patient": prediction.patient,
                "age": prediction.clinical_record.age,
                "sex": prediction.patient.get_sex_display(),
                "complications": complications or [prediction.risk_level],
                "risk_percent": round(max_score * 100),
            }
        )

    total_positive_scores = RiskScoreDetail.objects.filter(risk_label=1).count()
    complication_stats = []
    for target, name in COMPLICATION_NAMES.items():
        count = RiskScoreDetail.objects.filter(target=target, risk_label=1).count()
        percent = round((count / total_positive_scores * 100), 1) if total_positive_scores else 0
        if percent >= 50:
            color = "error"
            label = "Rất cao"
        elif percent >= 25:
            color = "warning"
            label = "Cao"
        else:
            color = "success"
            label = "Thấp"
        complication_stats.append(
            {
                "target": target,
                "name": name,
                "count": count,
                "percent": percent,
                "width": min(100, max(0, int(percent))),
                "color": color,
                "label": label,
            }
        )

    evaluated_predictions = (
        PredictionResult.objects.filter(clinical_record__label__isnull=False)
        .select_related("clinical_record", "clinical_record__label")
        .prefetch_related("scores")
    )
    model_accuracy = _micro_f1_for_predictions(evaluated_predictions)
    latest_prediction = PredictionResult.objects.order_by("-created_at").first()

    result = {
        "total_patient": total_patient,
        "total_war": alert_predictions.count(),
        "processed_profile": total_profile,
        "total_prediction": total_prediction,
        "today_profile": today_profile,
        "patient_growth": patient_growth,
        "model_accuracy": model_accuracy,
        "model_status": "Active" if latest_prediction else "No data",
    }
    return render(
        request,
        "dashboard/dashboard.html",
        {"result": result, "alert_patients": alert_patients, "complication_stats": complication_stats},
    )


@login_required(login_url="login")
@require_POST
def upload_patients_csv_view(request):
    csv_file = request.FILES.get("csv_file")
    if not csv_file:
        return JsonResponse({"error": "Chưa chọn file CSV"}, status=400)

    if not csv_file.name.lower().endswith(".csv"):
        return JsonResponse({"error": "File phải có định dạng .csv"}, status=400)

    fd, tmp_path = tempfile.mkstemp(suffix=".csv", prefix="patients_upload_")
    try:
        with os.fdopen(fd, "wb") as out:
            for chunk in csv_file.chunks():
                out.write(chunk)
    except Exception:
        os.unlink(tmp_path)
        raise

    def task(path):
        try:
            services.process_csv_to_database(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    threading.Thread(target=task, args=(tmp_path,), daemon=True).start()

    return JsonResponse(
        {
            "status": "processing",
            "message": "File đang được xử lý trong nền. Tải lại trang sau ít phút để xem dữ liệu.",
        },
        status=202,
    )
