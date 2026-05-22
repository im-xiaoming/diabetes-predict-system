from __future__ import annotations

import threading
import time
from copy import deepcopy

from django.db import close_old_connections

from .sample_loader import load_record, total_records


class FeedRunner:
    def __init__(self):
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread = None
        self._auto_start_thread = None
        self._state = self._initial_state()

    def _initial_state(self):
        return {
            "running": False,
            "paused": False,
            "done": False,
            "mode": "labeled",
            "interval": 5,
            "next_idx": 0,
            "total": total_records(),
            "sent": 0,
            "ok": 0,
            "fail": 0,
            "last_result": None,
            "message": "Feed idle",
            "statuses": {},
        }

    def status(self):
        with self._lock:
            state = deepcopy(self._state)
            thread_alive = bool(self._thread and self._thread.is_alive())
            state["thread_alive"] = thread_alive
            return state

    def start(self, *, interval=5, reset=False, unlabeled=False):
        interval = max(1, int(interval))
        with self._lock:
            alive = bool(self._thread and self._thread.is_alive())
            if alive and not reset:
                self._state["paused"] = False
                self._state["message"] = "Feed resumed"
                return self.status()

            if alive and reset:
                self._stop_event.set()
                self._thread.join(timeout=2)

            self._stop_event = threading.Event()
            self._state = self._initial_state()
            self._state.update(
                {
                    "running": True,
                    "paused": False,
                    "done": False,
                    "mode": "unlabeled" if unlabeled else "labeled",
                    "interval": interval,
                    "message": "Feed running",
                }
            )
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return self.status()

    def auto_start(self, *, interval=5, delay=3, unlabeled=False):
        def delayed_start():
            time.sleep(max(0, int(delay)))
            with self._lock:
                alive = bool(self._thread and self._thread.is_alive())
                should_start = not alive and not self._state["running"] and not self._state["done"]
            if should_start:
                self.start(interval=interval, reset=False, unlabeled=unlabeled)

        with self._lock:
            alive = bool(self._thread and self._thread.is_alive())
            auto_alive = bool(self._auto_start_thread and self._auto_start_thread.is_alive())
            if alive or auto_alive or self._state["running"] or self._state["done"]:
                return self.status()
            self._state["message"] = "Feed scheduled to auto-start"
            self._auto_start_thread = threading.Thread(target=delayed_start, daemon=True)
            self._auto_start_thread.start()
            return self.status()

    def pause(self):
        with self._lock:
            if self._state["running"]:
                self._state["paused"] = True
                self._state["message"] = "Feed paused"
            return self.status()

    def resume(self):
        with self._lock:
            if self._state["running"]:
                self._state["paused"] = False
                self._state["message"] = "Feed running"
            return self.status()

    def stop(self):
        self._stop_event.set()
        with self._lock:
            self._state["running"] = False
            self._state["paused"] = False
            self._state["message"] = "Feed stopped"
            return self.status()

    def reset(self):
        self._stop_event.set()
        with self._lock:
            self._state = self._initial_state()
            return self.status()

    def _set_status(self, idx, text, ok=None):
        with self._lock:
            self._state["statuses"][str(idx)] = {"text": text, "ok": ok}

    def _record_result(self, idx, result):
        ok = bool(result.get("ok"))
        skipped = bool(result.get("skipped"))
        with self._lock:
            self._state["sent"] += 1
            self._state["ok"] += 1 if ok else 0
            self._state["fail"] += 0 if ok else 1
            self._state["last_result"] = result
            self._state["statuses"][str(idx)] = {
                "text": "Bo qua" if skipped else "Thanh cong" if ok else "That bai",
                "ok": ok,
            }

    def _run(self):
        from .views import call_predict, without_truth

        while not self._stop_event.is_set():
            with self._lock:
                if not self._state["running"]:
                    return
                if self._state["paused"]:
                    interval = 0.5
                    idx = None
                else:
                    idx = self._state["next_idx"]
                    interval = self._state["interval"]
                    if idx >= self._state["total"]:
                        self._state["running"] = False
                        self._state["done"] = True
                        self._state["message"] = "Feed completed"
                        return
                    self._state["next_idx"] += 1

            if idx is None:
                time.sleep(interval)
                continue

            close_old_connections()
            try:
                rec = load_record(idx)
                if not rec:
                    result = {"ok": False, "saved": False, "idx": idx, "error": "Record not found"}
                elif not rec["ready"]:
                    result = {
                        "ok": False,
                        "saved": False,
                        "idx": idx,
                        "skipped": True,
                        "error": "Record has missing values",
                    }
                else:
                    self._set_status(idx, "Dang gui", None)
                    if self.status()["mode"] == "unlabeled":
                        rec = without_truth(rec)
                    result = call_predict(rec)
            except Exception as exc:
                result = {"ok": False, "saved": False, "idx": idx, "error": str(exc)}
            finally:
                close_old_connections()

            self._record_result(idx, result)
            if not result.get("ok") and not result.get("skipped"):
                with self._lock:
                    self._state["paused"] = True
                    self._state["message"] = "Feed paused because prediction failed"

            time.sleep(interval)


feed_runner = FeedRunner()
