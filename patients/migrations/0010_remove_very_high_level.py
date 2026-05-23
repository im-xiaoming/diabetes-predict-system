from django.db import migrations, models


def normalize_levels(apps, schema_editor):
    patient = apps.get_model("patients", "Patient")
    prediction = apps.get_model("predictions", "PredictionResult")
    patient.objects.filter(level="very_high").update(level="high")
    prediction.objects.filter(risk_level="very_high").update(risk_level="high")


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0009_remove_clinicalrecord_sex_remove_patient_age_and_more'),
        ('predictions', '0002_requestlog'),
    ]

    operations = [
        migrations.RunPython(normalize_levels, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='patient',
            name='level',
            field=models.TextField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]),
        ),
    ]
