"""One admitted job, cooperative cancellation, and cursor-addressable logs."""
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import threading
import time
import uuid
from pathlib import Path


class Cancelled(Exception):
    pass


class Jobs:
    def __init__(self, log_dir=None):
        self.lock = threading.RLock()
        self.cancel_event = threading.Event()
        self.worker = None
        self.sequence = 0
        self.logs = deque(maxlen=500)
        self.log_dir = Path(log_dir) if log_dir else None
        self.log_path = None
        self.data = {"status": "idle", "job_id": None, "task_type": "", "phase": "Ready",
                     "total": 0, "current": 0, "succeeded": 0, "failed": 0, "skipped": 0,
                     "current_file": "", "results": None, "device": None}
        self.started = None
        self.finished = None
        self.processing_started = None

    def log(self, message):
        with self.lock:
            self.sequence += 1
            self.logs.append({"id": self.sequence, "message": str(message)})
            if self.log_path:
                try:
                    with self.log_path.open('a', encoding='utf-8') as report:
                        report.write(str(message).replace('\r', ' ').replace('\n', ' ') + '\n')
                except OSError:
                    self.log_path = None
                    self.data['report_error'] = 'Could not write the complete job report.'

    def start(self, kind, target, device_id="cpu"):
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                raise ValueError("A task is still active. Wait for it to finish or cancel.")
            self.cancel_event.clear()
            self.logs.clear()
            self.started = time.monotonic()
            self.finished = self.processing_started = None
            self.data = {"status": "running", "job_id": uuid.uuid4().hex, "task_type": kind,
                         "phase": "Scanning", "total": 0, "current": 0, "succeeded": 0,
                         "failed": 0, "skipped": 0, "current_file": "", "results": None, "device": None,
                         "requested_device_id": device_id,
                         "started_at": datetime.now(timezone.utc).isoformat()}
            self.log_path = None
            if self.log_dir:
                try:
                    self.log_dir.mkdir(parents=True, exist_ok=True)
                    self.log_path = self.log_dir / f"{self.data['job_id']}.log"
                    self.log_path.write_text(f"{kind} job started {self.data['started_at']}\n", encoding='utf-8')
                    self.data['report_path'] = str(self.log_path)
                except OSError:
                    self.log_path = None
                    self.data['report_error'] = 'Could not create a persistent job report.'
            self.worker = threading.Thread(target=self._run, args=(target,), daemon=True)
            self.worker.start()
            return self.data["job_id"]

    def _run(self, target):
        try:
            results = target(self)
            self.check_cancel()
            self.log(f"Finished: {self.data['succeeded']} succeeded, {self.data['skipped']} skipped, {self.data['failed']} failed.")
            self.update(status="completed_with_errors" if self.data["failed"] else "completed",
                        phase="Finished", results=results)
        except Cancelled:
            self.update(status="cancelled", phase="Cancelled")
            self.log("Cancelled. Successfully written outputs were preserved.")
        except Exception as exc:
            self.update(status="failed", phase="Failed", error=str(exc))
            self.log(f"ERROR: {exc}")
        finally:
            with self.lock:
                self.finished = time.monotonic()

    def update(self, **values):
        with self.lock:
            self.data.update(values)
            if values.get("phase") == "Processing" and self.processing_started is None:
                self.processing_started = time.monotonic()

    def check_cancel(self):
        if self.cancel_event.is_set():
            raise Cancelled()

    def cancel(self):
        with self.lock:
            if self.worker is not None and self.worker.is_alive():
                self.cancel_event.set()
                self.data.update(status="cancelling", phase="Finishing current operation")
                return True
            return False

    def complete_file(self, success):
        with self.lock:
            self.data["current"] += 1
            self.data["succeeded" if success else "failed"] += 1

    def skip_file(self):
        with self.lock:
            self.data["current"] += 1
            self.data["skipped"] += 1

    def snapshot(self, after=0):
        with self.lock:
            result = deepcopy(self.data)
            now = self.finished or time.monotonic()
            elapsed = max(0, now - self.started) if self.started else 0
            processing = max(0, now - self.processing_started) if self.processing_started else 0
            done, total = result["current"], result["total"]
            result["progress"] = int(100 * done / total) if total else (100 if result["status"] == "completed" else 0)
            result["elapsed_seconds"] = round(elapsed, 1)
            result["images_per_minute"] = round(60 * done / processing, 1) if processing > 0 and done else None
            result["eta_seconds"] = round((total - done) * processing / done) if done >= 3 and total > done else None
            result["events"] = [dict(entry) for entry in self.logs if entry["id"] > after]
            result["log_cursor"] = self.sequence
            result["active"] = self.worker is not None and self.worker.is_alive()
            return result
