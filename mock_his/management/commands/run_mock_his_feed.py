from time import sleep

from django.core.management.base import BaseCommand

from mock_his.sample_loader import load_record, total_records
from mock_his.views import call_predict


class Command(BaseCommand):
    help = "Run Mock HIS feed from the server side without opening the Mock HIS page."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=5)
        parser.add_argument("--start", type=int, default=0)
        parser.add_argument("--count", type=int, default=None)

    def handle(self, *args, **opts):
        interval = max(0, opts["interval"])
        start = max(0, opts["start"])
        total = total_records()
        count = opts["count"]
        end = total if count is None else min(total, start + max(0, count))

        self.stdout.write(f"Mock HIS feed start={start} end={end} interval={interval}s")
        for idx in range(start, end):
            rec = load_record(idx)
            if not rec:
                self.stdout.write(f"{idx}: not found")
                continue
            if not rec["ready"]:
                self.stdout.write(f"{idx}: skipped missing values")
                continue

            out = call_predict(rec)
            if out.get("already_saved"):
                status = "already"
            else:
                status = "ok" if out.get("ok") else "fail"
            patient_id = out.get("patient_id", rec.get("pid"))
            pred_id = out.get("prediction_id", "")
            self.stdout.write(f"{idx}: {status} patient={patient_id} prediction={pred_id}")
            if idx < end - 1 and interval:
                sleep(interval)

        self.stdout.write("Mock HIS feed finished")
