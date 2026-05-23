from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from accounts.permissions import doctor_or_admin_required
from patients.models import Patient


@doctor_or_admin_required
def patients_view(request):
    patient_list = Patient.objects.prefetch_related("clinical_records").all().order_by("-updated_at")
    paginator = Paginator(patient_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    for patient in page_obj.object_list:
        patient.latest_record = patient.clinical_records.order_by("-created_at").first()
    return render(
        request,
        "patients/patients.html",
        {
            "patients": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


@doctor_or_admin_required
def patient_detail_view(request, pk):
    patient = get_object_or_404(Patient.objects.prefetch_related("predictions__scores", "clinical_records"), pk=pk)
    pred = patient.predictions.order_by("-created_at").first()
    cr = pred.clinical_record if pred else patient.clinical_records.order_by("-created_at").first()
    hist = patient.predictions.order_by("-created_at")[:10]
    return render(
        request,
        "patients/patient_detail.html",
        {
            "patient": patient,
            "prediction": pred,
            "record": cr,
            "history": hist,
        },
    )


@doctor_or_admin_required
def patient_detail_redirect(request):
    patient = Patient.objects.order_by("-updated_at").first()
    if patient:
        return redirect("patient-detail", pk=patient.pk)
    return redirect("patients")
