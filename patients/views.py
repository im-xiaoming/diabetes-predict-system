import os
import tempfile
import threading

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .import services
from patients.models import Patient


@login_required(login_url="login")
def patients_view(request):
    return render(request, 'patients/patients.html', {'patients': Patient.objects.all()})


@login_required(login_url="login")
def patient_detail_view(request):
    return render(request, 'patients/patient_detail.html')


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