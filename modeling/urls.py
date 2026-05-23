from django.urls import path
from .import views

urlpatterns = [
    path("modeling/", views.modeling, name="modeling"),
    path("modeling/mlflow/", views.open_mlflow_ui, name="open_mlflow_ui"),
    path('model/train/', views.train_model_view, name='train_model')
]
