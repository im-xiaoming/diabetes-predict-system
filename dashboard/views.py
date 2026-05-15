from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from patients.models import Patient, PatientTargetFeatures


@login_required(login_url="login")
def dashboard(request):
    total_patient = Patient.objects.count()
    total_war = Patient.objects.filter(level__in=["medium", "high", "very_high"]).count()
    result = {
        "total_patient": total_patient,
        "total_war": total_war,
        "nep": PatientTargetFeatures.objects.filter(nep=1).count(),
        "neu": PatientTargetFeatures.objects.filter(neu=1).count(),
        "ret": PatientTargetFeatures.objects.filter(ret=1).count(),
        "cv": PatientTargetFeatures.objects.filter(cv=1).count(),
        "per_vas": PatientTargetFeatures.objects.filter(per_vas=1).count(),
    }
    return render(request, "dashboard/dashboard.html", {"result": result})
