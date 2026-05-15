from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from patients.models import Patient


@login_required(login_url="login")
def patients_view(request):
    patient_list = Patient.objects.all().order_by('id')
    paginator = Paginator(patient_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'patients/patients.html', {
        'patients': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
    })


@login_required(login_url="login")
def patient_detail_view(request):
    return render(request, 'patients/patient_detail.html')
