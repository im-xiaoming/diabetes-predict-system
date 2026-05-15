from django.urls import path
from .import views

urlpatterns = [
    path('patients/', views.patients_view, name='patients'),
    path("patient_detail/", views.patient_detail_view, name='patient-detail'),
]
