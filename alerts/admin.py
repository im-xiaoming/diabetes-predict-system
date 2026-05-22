from django.contrib import admin

from .models import Alert, WatchlistItem


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "target", "level", "status", "acknowledged_at", "resolved_at", "created_at"]
    list_filter = ["level", "status", "target"]
    search_fields = ["patient__name", "patient__id", "message", "doctor_note"]


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "target", "status", "reviewed_at", "created_at"]
    list_filter = ["status", "target"]
    search_fields = ["patient__name", "patient__id", "message", "doctor_note"]
