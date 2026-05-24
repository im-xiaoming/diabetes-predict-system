import os
import sys

from django.apps import AppConfig


class MockHisConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mock_his"

    def ready(self):
        if "runserver" not in sys.argv:
            return
        from django.conf import settings
        if settings.DEBUG and os.environ.get("RUN_MAIN") != "true":
            return

        from .models import load_labeled_config, load_unlabeled_config
        from .feed_runner import labeled_runner, unlabeled_runner

        labeled = load_labeled_config()
        if labeled.get("auto_start"):
            labeled_runner.auto_start(
                interval=labeled.get("interval", 5),
                delay=labeled.get("delay", 3),
                unlabeled=False,
            )

        unlabeled = load_unlabeled_config()
        if unlabeled.get("auto_start"):
            unlabeled_runner.auto_start(
                interval=unlabeled.get("interval", 5),
                delay=unlabeled.get("delay", 3),
                unlabeled=True,
            )
