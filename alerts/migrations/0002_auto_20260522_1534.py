from django.db import migrations, models
import django.db.models.deletion


def move_medium_alerts(apps, schema_editor):
    Alert = apps.get_model("alerts", "Alert")
    WatchlistItem = apps.get_model("alerts", "WatchlistItem")
    for alert in Alert.objects.filter(level="medium").iterator():
        WatchlistItem.objects.get_or_create(
            score_id=alert.score_id,
            defaults={
                "patient_id": alert.patient_id,
                "prediction_id": alert.prediction_id,
                "target": alert.target,
                "message": alert.message,
            },
        )
        alert.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0010_clinicalrecord_source_idx'),
        ('predictions', '0002_requestlog'),
        ('alerts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='alert',
            name='acknowledged_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alert',
            name='doctor_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='alert',
            name='resolved_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='alert',
            name='level',
            field=models.CharField(choices=[('high', 'High')], max_length=20),
        ),
        migrations.AlterField(
            model_name='alert',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('acknowledged', 'Acknowledged'), ('watching', 'Watching'), ('resolved', 'Resolved')], default='new', max_length=20),
        ),
        migrations.CreateModel(
            name='WatchlistItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target', models.CharField(max_length=20)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('open', 'Open'), ('reviewed', 'Reviewed')], default='open', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='watchlist_items', to='patients.patient')),
                ('prediction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='watchlist_items', to='predictions.predictionresult')),
                ('score', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='watchlist_item', to='predictions.riskscoredetail')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(move_medium_alerts, migrations.RunPython.noop),
    ]
