from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="MockHisFeedConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auto_start", models.BooleanField(default=True, help_text="Tự động chạy luồng Mock HIS khi Django khởi động.")),
                ("interval", models.PositiveIntegerField(default=5, help_text="Số giây giữa mỗi lần gửi bản ghi.")),
                ("delay", models.PositiveIntegerField(default=3, help_text="Số giây chờ trước khi feed bắt đầu sau khi Django sẵn sàng.")),
                ("unlabeled", models.BooleanField(default=True, help_text="Gửi bản ghi không kèm nhãn (ground truth) khi auto-start.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mock HIS feed config",
                "verbose_name_plural": "Mock HIS feed config",
            },
        ),
    ]
