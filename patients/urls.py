from django.urls import path

from . import views


urlpatterns = [
    path("patients/", views.patients_view, name="patients"),
    path("patients/<int:pk>/", views.patient_detail_view, name="patient-detail"),
    path("patient_detail/", views.patient_detail_redirect, name="patient-detail-old"),
]
