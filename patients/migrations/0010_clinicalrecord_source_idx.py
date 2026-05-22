from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0009_remove_clinicalrecord_sex_remove_patient_age_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinicalrecord',
            name='source_idx',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
