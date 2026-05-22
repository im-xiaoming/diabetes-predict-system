from django.urls import path
from .import views

urlpatterns = [
    path('alerts/', views.alerts, name='alerts'),
    path('alerts/watchlist/', views.watchlist, name='watchlist'),
    path('alerts/watchlist/<int:pk>/status/', views.update_watchlist, name='watchlist-status'),
    path('alerts/<int:pk>/status/', views.update_status, name='alert-status'),
]
