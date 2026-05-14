from django.urls import path
from .import views

urlpatterns = [
    path('patients/', views.patients_view, name='patients')
]
