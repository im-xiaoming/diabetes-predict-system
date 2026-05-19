from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    path("", include("dashboard.urls")),
    path("", include("patients.urls")),
    path("", include("mock_his.urls")),
    path("", include("monitor.urls")),
    path("", include("alerts.urls")),
    path("", include("history.urls"))
]
