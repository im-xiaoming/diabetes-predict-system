from django.urls import path

from . import views


urlpatterns = [
    path("mock-his/", views.mock_his_view, name="mock-his"),
    path("mock-his/send/", views.send_one_view, name="mock-his-send"),
    path("mock-his/send-bulk/", views.send_bulk_view, name="mock-his-send-bulk"),
    path("mock-his/health/", views.health_view, name="mock-his-health"),
    path("mock-his/records/", views.records_view, name="mock-his-records"),
    path("mock-his/feed/status/", views.feed_status_view, name="mock-his-feed-status"),
    path("mock-his/feed/start/", views.feed_start_view, name="mock-his-feed-start"),
    path("mock-his/feed/pause/", views.feed_pause_view, name="mock-his-feed-pause"),
    path("mock-his/feed/resume/", views.feed_resume_view, name="mock-his-feed-resume"),
    path("mock-his/feed/stop/", views.feed_stop_view, name="mock-his-feed-stop"),
    path("mock-his/feed/reset/", views.feed_reset_view, name="mock-his-feed-reset"),
    path("his-inference/", views.his_inference_view, name="his-inference"),
    path("his-inference/send/", views.send_unlabeled_one_view, name="his-inference-send"),
    path("his-inference/send-bulk/", views.send_unlabeled_bulk_view, name="his-inference-send-bulk"),
    path("his-inference/records/", views.unlabeled_records_view, name="his-inference-records"),
]
