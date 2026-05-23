from django.contrib import admin

from .models import AirflowRetrainConfig, ModelTrainingConfig


@admin.register(AirflowRetrainConfig)
class AirflowRetrainConfigAdmin(admin.ModelAdmin):
    list_display = ("schedule", "min_new_labels", "min_new_ratio", "force", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        ("Schedule", {"fields": ("schedule",)}),
        (
            "Policy thresholds",
            {
                "fields": (
                    "min_new_labels",
                    "min_new_ratio",
                    "min_new_positives",
                    "min_positive_targets",
                    "min_days",
                    "urgent_new_labels",
                    "max_missing_rate",
                    "max_duplicate_rate",
                )
            },
        ),
        ("Manual override", {"fields": ("force",)}),
        ("Audit", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not AirflowRetrainConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ModelTrainingConfig)
class ModelTrainingConfigAdmin(admin.ModelAdmin):
    list_display = ("n_trials", "timeout", "tune", "register", "promotion_metric", "promotion_min_delta", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Training",
            {
                "fields": (
                    "tune",
                    "enabled_models",
                    "n_trials",
                    "timeout",
                    "log_optuna_trials",
                )
            },
        ),
        (
            "Promotion",
            {
                "fields": (
                    "register",
                    "promotion_metric",
                    "promotion_min_delta",
                    "force_promote",
                )
            },
        ),
        ("Optuna", {"fields": ("optuna", "search_space")}),
        ("Audit", {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not ModelTrainingConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
