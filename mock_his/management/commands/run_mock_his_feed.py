import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from mock_his.feed_runner import saved_mock_record_count
from mock_his.sample_loader import load_record, total_records
from mock_his.views import call_predict, without_truth


class Command(BaseCommand):
    help = "Run Mock HIS feed and send patient records to FastAPI."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=5)
        parser.add_argument("--count", type=int, default=None)
        parser.add_argument("--offset", type=int, default=None)
        parser.add_argument("--unlabeled", action="store_true")
        parser.add_argument("--stop-on-error", action="store_true")

    def handle(self, *args, **opts):
        interval = max(0, int(opts["interval"]))
        total = total_records()
        start = opts["offset"]
        if start is None:
            start = min(saved_mock_record_count(), total)
        end = total if opts["count"] is None else min(total, start + max(0, int(opts["count"])))

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock HIS feed started: offset={start}, end={end}, interval={interval}s"
            )
        )

        sent = 0
        ok = 0
        fail = 0

        for idx in range(start, end):
            close_old_connections()
            rec = load_record(idx)
            if not rec:
                fail += 1
                self.stdout.write(self.style.ERROR(f"[{idx}] record not found"))
                if opts["stop_on_error"]:
                    break
                time.sleep(interval)
                continue

            if not rec["ready"]:
                fail += 1
                self.stdout.write(self.style.WARNING(f"[{idx}] skipped: missing values"))
                time.sleep(interval)
                continue

            if opts["unlabeled"]:
                rec = without_truth(rec)

            out = call_predict(rec)
            sent += 1
            if out.get("ok"):
                ok += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[{idx}] ok patient={out.get('patient_id')} prediction={out.get('prediction_id')}"
                    )
                )
            else:
                fail += 1
                self.stdout.write(self.style.ERROR(f"[{idx}] failed: {out.get('error')}"))
                if opts["stop_on_error"]:
                    break

            close_old_connections()
            time.sleep(interval)

        self.stdout.write(
            self.style.SUCCESS(
                f"Mock HIS feed finished: sent={sent}, ok={ok}, fail={fail}"
            )
        )
