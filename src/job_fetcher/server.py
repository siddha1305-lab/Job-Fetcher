from __future__ import annotations

import json
import os
import signal
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from typing import Any
from urllib.parse import urlsplit

from .boards import BOARDS
from .fetchers import fetch_all
from .models import Job
from .pipeline import deduplicate

INDEX_HTML = files("job_fetcher").joinpath("static/index.html").read_bytes()


class JobState:
    def __init__(
        self,
        *,
        location: str,
        refresh_interval: int,
        workers: int,
        timeout: float,
    ) -> None:
        self.location = location
        self.refresh_interval = refresh_interval
        self.workers = workers
        self.timeout = timeout
        self._jobs: list[Job] = []
        self._errors: dict[str, str] = {}
        self._last_refreshed: datetime | None = None
        self._refreshing = False
        self._lock = threading.Lock()
        self._stop = threading.Event()

    def is_stale(self) -> bool:
        with self._lock:
            if self._last_refreshed is None:
                return True
            return datetime.now(timezone.utc) - self._last_refreshed >= timedelta(
                seconds=self.refresh_interval
            )

    def refresh(self) -> None:
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True
        try:
            jobs, errors = fetch_all(
                BOARDS,
                self.location,
                workers=self.workers,
                timeout=self.timeout,
            )
            unique_jobs = deduplicate(jobs)
            with self._lock:
                # Keep the previous successful snapshot through a total outage.
                if unique_jobs or not self._jobs:
                    self._jobs = unique_jobs
                self._errors = errors
                self._last_refreshed = datetime.now(timezone.utc)
        except Exception as exc:
            with self._lock:
                self._errors = {"refresh": str(exc)}
                self._last_refreshed = datetime.now(timezone.utc)
        finally:
            with self._lock:
                self._refreshing = False

    def refresh_async(self) -> None:
        with self._lock:
            if self._refreshing:
                return
        threading.Thread(target=self.refresh, daemon=True, name="job-refresh").start()

    def run_scheduler(self) -> None:
        while not self._stop.wait(self.refresh_interval):
            self.refresh()

    def stop(self) -> None:
        self._stop.set()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "location": self.location,
                "job_count": len(self._jobs),
                "board_count": len(BOARDS),
                "successful_board_count": len(BOARDS) - len(self._errors),
                "last_refreshed": (
                    self._last_refreshed.isoformat()
                    if self._last_refreshed
                    else None
                ),
                "refreshing": self._refreshing,
                "errors": dict(self._errors),
                "jobs": [job.to_dict() for job in self._jobs],
            }


class JobRequestHandler(BaseHTTPRequestHandler):
    state: JobState

    def _send_body(
        self, body: bytes, content_type: str, status: int = 200
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        self._send_body(
            json.dumps(payload, ensure_ascii=False).encode(),
            "application/json; charset=utf-8",
            status,
        )

    def do_GET(self) -> None:
        path = urlsplit(self.path).path.rstrip("/") or "/"
        if path == "/health":
            snapshot = self.state.snapshot()
            self._send_json(
                {
                    "status": "ok",
                    "job_count": snapshot["job_count"],
                    "refreshing": snapshot["refreshing"],
                    "last_refreshed": snapshot["last_refreshed"],
                }
            )
            return
        if path == "/jobs":
            if self.state.is_stale():
                self.state.refresh_async()
            self._send_json(self.state.snapshot())
            return
        if path == "/":
            self._send_body(
                INDEX_HTML,
                "text/html; charset=utf-8",
            )
            return
        self._send_json({"error": "not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        print(
            f'{self.address_string()} - [{self.log_date_time_string()}] '
            f'{format % args}',
            flush=True,
        )


def _positive_number(name: str, default: str, cast: type) -> Any:
    value = cast(os.getenv(name, default))
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


def main() -> None:
    port = _positive_number("PORT", "8000", int)
    state = JobState(
        location=os.getenv("JOB_LOCATION", "United Kingdom"),
        refresh_interval=_positive_number(
            "REFRESH_INTERVAL_SECONDS", "43200", int
        ),
        workers=_positive_number("FETCH_WORKERS", "6", int),
        timeout=_positive_number("FETCH_TIMEOUT_SECONDS", "30", float),
    )
    JobRequestHandler.state = state
    server = ThreadingHTTPServer(("0.0.0.0", port), JobRequestHandler)

    def shutdown(_signum: int, _frame: Any) -> None:
        state.stop()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    state.refresh_async()
    threading.Thread(
        target=state.run_scheduler, daemon=True, name="job-scheduler"
    ).start()
    print(f"VC Job Fetcher listening on 0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    finally:
        state.stop()
        server.server_close()


if __name__ == "__main__":
    main()
