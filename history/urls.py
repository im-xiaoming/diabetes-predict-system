from django.urls import path
from .import views

urlpatterns = [
    path("history/", views.history, name='history'),
    path("history/detail/", views.history_detail, name='history_detail'),
]
