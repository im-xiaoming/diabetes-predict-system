import os
import tempfile
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from alerts.models import Alert, AlertStatus
from patients.models import ClinicalRecord, Patient
from predictions.models import PredictionResult, RiskScoreDetail
from . import services


def dashboard_result():
    total_patient = Patient.objects.count()
    total_war = Alert.objects.exclude(status=AlertStatus.RESOLVED).count()
    total_prediction = PredictionResult.objects.count()
    return {
        "total_patient": total_patient,
        "total_war": total_war,
        "high_patient": Patient.objects.filter(level__in=["high", "very_high"]).count(),
        "nep": RiskScoreDetail.objects.filter(target="NEP", risk_label=1).count(),
        "neu": RiskScoreDetail.objects.filter(target="NEU", risk_label=1).count(),
        "ret": RiskScoreDetail.objects.filter(target="RET", risk_label=1).count(),
        "cv": RiskScoreDetail.objects.filter(target="CV", risk_label=1).count(),
        "per_vas": RiskScoreDetail.objects.filter(target="PER VAS", risk_label=1).count(),
        "processed_profile": ClinicalRecord.objects.count(),
        "total_prediction": total_prediction,
    }


@login_required(login_url="login")
def dashboard(request):
    rows = (
        Alert.objects.exclude(status=AlertStatus.RESOLVED)
        .select_related("patient", "score")
        .order_by("-created_at")[:5]
    )
    return render(request, "dashboard/dashboard.html", {"result": dashboard_result(), "alerts": rows})


@login_required(login_url="login")
def dashboard_stats(request):
    return JsonResponse({"ok": True, "result": dashboard_result()})


@login_required(login_url="login")
@require_POST
def upload_patients_csv_view(request):
    csv_file = request.FILES.get("csv_file")
    if not csv_file:
        return JsonResponse({"error": "Chua chon file CSV"}, status=400)

    if not csv_file.name.lower().endswith(".csv"):
        return JsonResponse({"error": "File phai co dinh dang .csv"}, status=400)

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
            "message": "File dang duoc xu ly trong nen. Tai lai trang sau it phut de xem du lieu.",
        },
        status=202,
    )
