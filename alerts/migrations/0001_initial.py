from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('predictions', '0002_requestlog'),
        ('patients', '0010_clinicalrecord_source_idx'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('target', models.CharField(max_length=20)),
                ('level', models.CharField(choices=[('medium', 'Medium'), ('high', 'High')], max_length=20)),
                ('message', models.TextField()),
                ('status', models.CharField(choices=[('new', 'New'), ('watching', 'Watching'), ('resolved', 'Resolved')], default='new', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='patients.patient')),
                ('prediction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='predictions.predictionresult')),
                ('score', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='alert', to='predictions.riskscoredetail')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
