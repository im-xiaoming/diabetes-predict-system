import os
import sys

from django.apps import AppConfig
from django.conf import settings


class MockHisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mock_his"

    def ready(self):
        if not getattr(settings, "MOCK_HIS_AUTO_START", False):
            return
        if "runserver" not in sys.argv:
            return
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return

        from .feed_runner import feed_runner

        feed_runner.auto_start(
            interval=getattr(settings, "MOCK_HIS_AUTO_START_INTERVAL", 5),
            delay=getattr(settings, "MOCK_HIS_AUTO_START_DELAY", 3),
            unlabeled=getattr(settings, "MOCK_HIS_AUTO_START_UNLABELED", False),
        )
