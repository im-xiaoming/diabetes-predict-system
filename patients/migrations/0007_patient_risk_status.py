from django.db import migrations, models
import django.db.models.deletion


def dedupe_patient_target_features(apps, schema_editor):
    PatientTargetFeatures = apps.get_model("patients", "PatientTargetFeatures")

    seen = set()
    for row in PatientTargetFeatures.objects.order_by("-id"):
        if row.patient_id in seen:
            row.delete()
        else:
            seen.add(row.patient_id)


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0006_merge_20260516_0001"),
    ]

    operations = [
        migrations.RunPython(dedupe_patient_target_features, migrations.RunPython.noop),
        migrations.RenameModel(
            old_name="PatientTargetFeatures",
            new_name="PatientRiskStatus",
        ),
        migrations.AlterField(
            model_name="patientriskstatus",
            name="patient",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="risk_status",
                to="patients.patient",
            ),
        ),
        migrations.AddField(
            model_name="patientriskstatus",
            name="source",
            field=models.CharField(default="prediction", max_length=50),
        ),
        migrations.AddField(
            model_name="patientriskstatus",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
