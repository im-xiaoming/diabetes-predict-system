from django.urls import path
from .import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/upload/', views.upload_patients_csv_view, name='patient-upload'),
    path('', views.dashboard)
]
