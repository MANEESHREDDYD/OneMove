"""Dedicated Outbox Dispatcher service claiming and publishing transactional outbox events to Pub/Sub."""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from services.zonepilot.optimization.service import OptimizationService

logger = logging.getLogger("onemove.outbox.dispatcher")


class OutboxDispatcher:
    """Production-grade asynchronous outbox dispatcher with health endpoints, metrics, and batch processing."""

    def __init__(
        self,
        service: OptimizationService | None = None,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 20,
    ) -> None:
        self.service = service or OptimizationService()
        self.poll_interval = float(os.environ.get("DISPATCHER_INTERVAL_SEC", poll_interval_seconds))
        self.batch_size = int(os.environ.get("DISPATCHER_BATCH_SIZE", batch_size))
        self._running = False
        self._start_time = time.time()
        self._total_dispatched = 0
        self._total_cycles = 0
        self._total_errors = 0
        self._last_cycle_time: float | None = None
        self._last_error: str | None = None

    def run_once(self) -> int:
        """Process one batch of pending outbox events with atomic claiming and publishing."""
        count = self.service.dispatch_outbox_events(limit=self.batch_size)
        self._total_dispatched += count
        self._total_cycles += 1
        self._last_cycle_time = time.time()
        return count

    def get_metrics(self) -> dict[str, Any]:
        """Return operational metrics for monitoring and health probes."""
        return {
            "service": "onemove-outbox-dispatcher",
            "running": self._running,
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "total_dispatched": self._total_dispatched,
            "total_cycles": self._total_cycles,
            "total_errors": self._total_errors,
            "last_cycle_time": self._last_cycle_time,
            "last_error": self._last_error,
            "poll_interval_seconds": self.poll_interval,
            "batch_size": self.batch_size,
        }

    def run_forever(self, start_health_server: bool = True) -> None:
        """Run continuous dispatch loop with graceful signal handling and optional HTTP health server."""
        self._running = True
        self._start_time = time.time()
        logger.info(
            f"Starting dedicated Outbox Dispatcher (interval={self.poll_interval}s, batch_size={self.batch_size})"
        )

        httpd: HTTPServer | None = None
        if start_health_server:
            port = int(os.environ.get("PORT", "8080"))
            httpd = self._start_http_health_server(port)

        def handle_signal(sig: int, frame: Any) -> None:
            logger.info(f"Received signal {sig}; shutting down outbox dispatcher...")
            self._running = False
            if httpd:
                try:
                    httpd.shutdown()
                except Exception:
                    pass

        try:
            signal.signal(signal.SIGINT, handle_signal)
            signal.signal(signal.SIGTERM, handle_signal)
        except (ValueError, AttributeError):
            pass

        while self._running:
            try:
                count = self.run_once()
                if count > 0:
                    logger.debug(f"Dispatched {count} outbox event(s)")
                else:
                    time.sleep(self.poll_interval)
            except Exception as exc:
                self._total_errors += 1
                self._last_error = str(exc)
                logger.error(f"Error in outbox dispatch cycle: {exc}", exc_info=True)
                time.sleep(self.poll_interval * 2)

        logger.info("Outbox Dispatcher stopped cleanly.")

    def _start_http_health_server(self, port: int) -> HTTPServer | None:
        """Launch a background HTTP server for Cloud Run health and readiness checks."""
        dispatcher_ref = self

        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path in {"/healthz", "/health", "/readyz", "/ready", "/"}:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    body = json.dumps({"status": "healthy", **dispatcher_ref.get_metrics()})
                    self.wfile.write(body.encode("utf-8"))
                elif self.path == "/metrics":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    body = json.dumps(dispatcher_ref.get_metrics())
                    self.wfile.write(body.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:
                pass  # Suppress excessive access logs for health probes

        try:
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            logger.info(f"Outbox Dispatcher HTTP health probe listening on port {port}")
            return server
        except Exception as err:
            logger.warning(f"Could not bind HTTP health probe on port {port}: {err}")
            return None


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
    )
    dispatcher = OutboxDispatcher()
    dispatcher.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
