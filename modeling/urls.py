from django.urls import path
from .import views

urlpatterns = [
    path("modeling/", views.modeling, name="modeling"),
    path('model/train/', views.train_model_view, name='train_model')
]
