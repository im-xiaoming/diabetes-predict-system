from django.urls import path
from .import views

urlpatterns = [
    path("modeling/", views.modeling, name="modeling")
]
