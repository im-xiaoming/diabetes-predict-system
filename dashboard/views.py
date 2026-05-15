import os
import tempfile
import threading

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from patients.models import Patient, PatientTargetFeatures
from . import services


@login_required(login_url="login")
def dashboard(request):
    total_patient = Patient.objects.count()
    total_war = Patient.objects.filter(level__in=["medium", "high", "very high"]).count()

    nep = PatientTargetFeatures.objects.filter(nep=1).count()
    neu = PatientTargetFeatures.objects.filter(neu=1).count()
    ret = PatientTargetFeatures.objects.filter(ret=1).count()
    cv = PatientTargetFeatures.objects.filter(cv=1).count()
    per_vas = PatientTargetFeatures.objects.filter(per_vas=1).count()
    patient_target_counts = PatientTargetFeatures.objects.count()
    
    result = {
        'total_patient': total_patient,
        'total_war': total_war, # medium,
        'nep': nep,
        'neu': neu,
        'ret': ret,
        'cv': cv,
        'per_vas': per_vas,
        'processed_profile': patient_target_counts,
        'total_prediction': patient_target_counts
    }
    return render(request, "dashboard/dashboard.html", {
        'result': result
    })


@login_required(login_url="login")
@require_POST
def upload_patients_csv_view(request):
    csv_file = request.FILES.get('csv_file')
    if not csv_file:
        return JsonResponse({'error': 'Chưa chọn file CSV'}, status=400)

    if not csv_file.name.lower().endswith('.csv'):
        return JsonResponse({'error': 'File phải có định dạng .csv'}, status=400)

    fd, tmp_path = tempfile.mkstemp(suffix='.csv', prefix='patients_upload_')
    try:
        with os.fdopen(fd, 'wb') as out:
            for chunk in csv_file.chunks():
                out.write(chunk)
    except Exception:
        os.unlink(tmp_path)
        raise

    def _bg_task(path):
        try:
            services.process_csv_to_database(path)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    threading.Thread(target=_bg_task, args=(tmp_path,), daemon=True).start()

    return JsonResponse({
        'status': 'processing',
        'message': 'File đang được xử lý trong nền. Tải lại trang sau ít phút để xem dữ liệu.'
    }, status=202)
