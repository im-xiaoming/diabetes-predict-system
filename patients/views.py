from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from patients.models import Patient


@login_required(login_url="login")
def patients_view(request):
    patients = Patient.objects.all().order_by("-updated_at")
    return render(request, "patients/patients.html", {"patients": patients})


@login_required(login_url="login")
def patient_detail_view(request, pk):
    patient = get_object_or_404(Patient.objects.prefetch_related("predictions__scores", "clinical_records"), pk=pk)
    pred = patient.predictions.order_by("-created_at").first()
    cr = pred.clinical_record if pred else patient.clinical_records.order_by("-created_at").first()
    hist = patient.predictions.order_by("-created_at")[:10]
    return render(request, "patients/patient_detail.html", {"patient": patient, "prediction": pred, "record": cr, "history": hist})


@login_required(login_url="login")
def patient_detail_redirect(request):
    patient = Patient.objects.order_by("-updated_at").first()
    if patient:
        return redirect("patient-detail", pk=patient.pk)
    return redirect("patients")
