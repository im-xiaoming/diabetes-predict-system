from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required(login_url="login")
def patients_view(request):
    return render(request, 'patients/patients.html')