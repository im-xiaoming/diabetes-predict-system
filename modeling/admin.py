from django.contrib import admin

from .models import AirflowRetrainConfig


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
