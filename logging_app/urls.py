from django.urls import path
from . import views

urlpatterns = [
    path("logging/", views.logging_view, name="logging"),
    path("logs/", views.logging_view, name="logs"),
]
