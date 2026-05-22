from django.urls import path

from . import views


urlpatterns = [
    path("mock-his/", views.mock_his_view, name="mock-his"),
    path("mock-his/send/", views.send_one_view, name="mock-his-send"),
    path("mock-his/send-bulk/", views.send_bulk_view, name="mock-his-send-bulk"),
    path("mock-his/health/", views.health_view, name="mock-his-health"),
    path("mock-his/records/", views.records_view, name="mock-his-records"),
    path("his-inference/", views.his_inference_view, name="his-inference"),
    path("his-inference/send/", views.send_unlabeled_one_view, name="his-inference-send"),
    path("his-inference/send-bulk/", views.send_unlabeled_bulk_view, name="his-inference-send-bulk"),
    path("his-inference/records/", views.unlabeled_records_view, name="his-inference-records"),
]
