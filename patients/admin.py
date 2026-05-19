from django.contrib import admin

from .models import ClinicalRecord, Patient, PatientRiskStatus


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "age", "sex", "level", "war", "updated_at"]


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "hba1c", "bmi", "source", "created_at"]


@admin.register(PatientRiskStatus)
class PatientRiskStatusAdmin(admin.ModelAdmin):
    list_display = ["id", "patient", "nep", "neu", "ret", "cv", "per_vas", "source", "updated_at"]
