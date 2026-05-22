from django.contrib import admin

from .models import PredictionResult, RequestLog, RiskScoreDetail


@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "model_name", "model_version", "risk_level", "created_at"]
    list_per_page = 25


@admin.register(RiskScoreDetail)
class RiskScoreDetailAdmin(admin.ModelAdmin):
    list_display = ["id", "prediction", "target", "risk_score", "risk_label", "risk_level"]
    list_per_page = 25


@admin.register(RequestLog)
class RequestLogAdmin(admin.ModelAdmin):
    list_display = ["id", "prediction", "endpoint", "status_code", "latency_ms", "created_at"]
    list_per_page = 25
