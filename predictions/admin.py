from django.contrib import admin

from .models import PredictionResult, RiskScoreDetail


@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "model_name", "model_version", "risk_level", "created_at"]


@admin.register(RiskScoreDetail)
class RiskScoreDetailAdmin(admin.ModelAdmin):
    list_display = ["id", "prediction", "target", "risk_score", "risk_label", "risk_level"]
