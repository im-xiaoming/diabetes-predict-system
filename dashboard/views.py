import os
import tempfile
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from patients.models import ClinicalRecord, Patient
from predictions.models import PredictionResult, RiskScoreDetail
from . import services


@login_required(login_url="login")
def dashboard(request):
    total_patient = Patient.objects.count()
    total_profile = ClinicalRecord.objects.count()
    total_prediction = PredictionResult.objects.count()

    alert_predictions = (
        PredictionResult.objects.filter(risk_level__in=["high", "very_high"])
        .select_related("patient", "clinical_record")
        .prefetch_related("scores")
        .order_by("-created_at")
    )

    risk_percent = {
        "medium": 75,
        "high": 88,
        "very_high": 92,
    }
    complication_names = {
        "CV": "Tim mạch (CV)",
        "NEP": "Thận (NEP)",
        "NEU": "Thần kinh (NEU)",
        "RET": "Võng mạc (RET)",
        "PER VAS": "Mạch ngoại biên",
    }

    alert_patients = []
    for prediction in alert_predictions[:5]:
        complications = [
            complication_names.get(score.target, score.target)
            for score in prediction.scores.all()
            if score.risk_label
        ]
        alert_patients.append(
            {
                "patient": prediction.patient,
                "age": prediction.clinical_record.age,
                "sex": prediction.patient.get_sex_display(),
                "complications": complications or [prediction.risk_level],
                "risk_percent": risk_percent.get(prediction.risk_level, 75),
            }
        )

    result = {
        "total_patient": total_patient,
        "total_war": alert_predictions.count(),
        "nep": RiskScoreDetail.objects.filter(target="NEP", risk_label=1).count(),
        "neu": RiskScoreDetail.objects.filter(target="NEU", risk_label=1).count(),
        "ret": RiskScoreDetail.objects.filter(target="RET", risk_label=1).count(),
        "cv": RiskScoreDetail.objects.filter(target="CV", risk_label=1).count(),
        "per_vas": RiskScoreDetail.objects.filter(target="PER VAS", risk_label=1).count(),
        "processed_profile": total_profile,
        "total_prediction": total_prediction,
    }
    return render(request, "dashboard/dashboard.html", {"result": result, "alert_patients": alert_patients})


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
