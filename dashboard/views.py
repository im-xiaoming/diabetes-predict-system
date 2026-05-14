from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from patients.models import Patient


@login_required(login_url="login")
def dashboard(request):
    total_patient = len(Patient.objects.all())
    total_war = len(Patient.objects.filter(level__in=["medium", "high", "very high"]))
    result = {
        'total_patient': total_patient,
        'total_war': total_war # medium
    }
    return render(request, "dashboard/dashboard.html", {
        'result': result
    })
