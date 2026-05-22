from django.contrib import admin

from .models import ClinicalRecord, ClinicalRecordLabel, Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sex", "level", "war", "updated_at"]
    list_per_page = 25


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "patient_id", "hba1c", "bmi", "source", "created_at"]
    list_per_page = 25

    
    @admin.display(ordering="patient__id", description="Patient ID")
    def patient_id(self, obj):
        return obj.patient.id


@admin.register(ClinicalRecordLabel)
class ClinicalRecordLabelAdmin(admin.ModelAdmin):
    list_display = ["id", "clinical_record", "nep", "neu", "ret", "cv", "per_vas", "source", "created_at"]
    list_per_page = 25
