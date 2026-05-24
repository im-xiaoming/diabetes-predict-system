from django.contrib import admin

from .models import LabeledFeedConfig, UnlabeledFeedConfig


class _BaseFeedConfigAdmin(admin.ModelAdmin):
    list_display = ("auto_start", "interval", "delay", "updated_at")
    readonly_fields = ("updated_at",)
    fieldsets = (
        (
            "Auto-start",
            {
                "fields": ("auto_start", "interval", "delay"),
                "description": (
                    "Khi bấm Save, cấu hình ghi xuống configs/ và áp dụng ngay vào "
                    "luồng feed tương ứng (không cần restart Django)."
                ),
            },
        ),
        ("Audit", {"fields": ("updated_at",)}),
    )
    list_display_links = ("auto_start", "interval", "delay", "updated_at")

    def has_add_permission(self, request):
        return not self.model.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LabeledFeedConfig)
class LabeledFeedConfigAdmin(_BaseFeedConfigAdmin):
    pass


@admin.register(UnlabeledFeedConfig)
class UnlabeledFeedConfigAdmin(_BaseFeedConfigAdmin):
    pass
