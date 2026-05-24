from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mock_his", "0001_initial"),
    ]

    operations = [
        migrations.DeleteModel(name="MockHisFeedConfig"),
        migrations.CreateModel(
            name="LabeledFeedConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auto_start", models.BooleanField(default=True, help_text="Tự động chạy luồng feed CÓ NHÃN khi Django khởi động.")),
                ("interval", models.PositiveIntegerField(default=5, help_text="Số giây giữa mỗi lần gửi bản ghi (luồng có nhãn).")),
                ("delay", models.PositiveIntegerField(default=3, help_text="Số giây chờ trước khi luồng có nhãn bắt đầu.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mock HIS labeled feed config",
                "verbose_name_plural": "Mock HIS labeled feed config",
            },
        ),
        migrations.CreateModel(
            name="UnlabeledFeedConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auto_start", models.BooleanField(default=False, help_text="Tự động chạy luồng feed KHÔNG NHÃN khi Django khởi động.")),
                ("interval", models.PositiveIntegerField(default=5, help_text="Số giây giữa mỗi lần gửi bản ghi (luồng không nhãn).")),
                ("delay", models.PositiveIntegerField(default=3, help_text="Số giây chờ trước khi luồng không nhãn bắt đầu.")),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Mock HIS unlabeled feed config",
                "verbose_name_plural": "Mock HIS unlabeled feed config",
            },
        ),
    ]
