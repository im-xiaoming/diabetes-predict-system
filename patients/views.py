from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from patients.models import Patient


@login_required(login_url="login")
def patients_view(request):
    patient_list = Patient.objects.all().order_by("-updated_at")
    paginator = Paginator(patient_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "patients/patients.html",
        {
            "patients": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
        },
    )


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
