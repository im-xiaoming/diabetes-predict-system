from django.core.management.base import BaseCommand

from alerts.services import create_workflow_items
from predictions.models import PredictionResult


class Command(BaseCommand):
    help = "Create missing alerts from existing prediction results."

    def handle(self, *args, **opts):
        alert_total = 0
        watch_total = 0
        preds = PredictionResult.objects.prefetch_related("scores").select_related("patient")
        for pred in preds.iterator():
            rows = create_workflow_items(pred)
            alert_total += len(rows["alerts"])
            watch_total += len(rows["watchlist"])
        self.stdout.write(f"Created {alert_total} alerts and {watch_total} watchlist items")
