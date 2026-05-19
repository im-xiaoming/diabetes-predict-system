from django.urls import path
from .import views

urlpatterns = [
    path("monitor/", views.monitor, name='monitor')
]
