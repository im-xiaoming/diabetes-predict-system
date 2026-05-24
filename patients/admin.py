from django.contrib import admin
from django.db.models import Count, Exists, OuterRef, Q

from .models import ClinicalRecord, ClinicalRecordLabel, Patient


class HasLabelFilter(admin.SimpleListFilter):
    title = "Trạng thái nhãn"
    parameter_name = "has_label"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Đã có nhãn"),
            ("no", "Chưa có nhãn"),
        )

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(label__isnull=False)
        if self.value() == "no":
            return queryset.filter(label__isnull=True)
        return queryset


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "sex", "level", "war", "record_count", "labeled_count", "unlabeled_count", "updated_at"]
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _record_count=Count("clinical_records", distinct=True),
            _labeled_count=Count(
                "clinical_records",
                filter=Q(clinical_records__label__isnull=False),
                distinct=True,
            ),
        )

    @admin.display(ordering="_record_count", description="Số bản ghi")
    def record_count(self, obj):
        return obj._record_count

    @admin.display(ordering="_labeled_count", description="Đã có nhãn")
    def labeled_count(self, obj):
        return obj._labeled_count

    @admin.display(description="Chưa có nhãn")
    def unlabeled_count(self, obj):
        return obj._record_count - obj._labeled_count


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ["id", "patient_id", "hba1c", "bmi", "source", "has_label", "created_at"]
    list_filter = [HasLabelFilter, "source"]
    list_per_page = 25

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            _has_label=Exists(
                ClinicalRecordLabel.objects.filter(clinical_record=OuterRef("pk"))
            )
        )

    @admin.display(ordering="patient__id", description="Patient ID")
    def patient_id(self, obj):
        return obj.patient.id

    @admin.display(boolean=True, ordering="_has_label", description="Đã có nhãn")
    def has_label(self, obj):
        return obj._has_label


@admin.register(ClinicalRecordLabel)
class ClinicalRecordLabelAdmin(admin.ModelAdmin):
    list_display = ["id", "clinical_record", "nep", "neu", "ret", "cv", "per_vas", "source", "created_at"]
    list_per_page = 25
