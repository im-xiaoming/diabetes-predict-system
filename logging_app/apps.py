from django.apps import AppConfig


class LoggingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "logging_app"
    label = "logging"
    verbose_name = "Logging"
