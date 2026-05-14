from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from tools import load_csv_with_columns
from .services import calculate_diabetes_risks
from .import services


COLUMNS = ['SL_NO', 'NAME', 'AGE', 'SEX']

@login_required(login_url="login")
def patients_view(request):
    data = load_csv_with_columns(COLUMNS + services.TARGET)
    data['SEX'] = data['SEX'].map(lambda x: 'Nữ' if x == 0 else 'Nam')
    data = calculate_diabetes_risks(data)
    data = data.to_dict(orient='records')
    
    return render(request, 'patients/patients.html', {'patients': data})


@login_required(login_url="login")
def patient_detail_view(request):
    return render(request, 'patients/patient_detail.html')