from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from patients.models import Patient


@login_required(login_url="login")
def patients_view(request):
    return render(request, 'patients/patients.html', {'patients': Patient.objects.all()})


@login_required(login_url="login")
def patient_detail_view(request):
    return render(request, 'patients/patient_detail.html')
