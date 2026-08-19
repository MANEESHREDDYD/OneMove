"""Dedicated Outbox Dispatcher service claiming and publishing transactional outbox events to Pub/Sub."""

from __future__ import annotations

import logging
import signal
import sys
import time
from typing import Any

from services.zonepilot.optimization.service import OptimizationService

logger = logging.getLogger("onemove.outbox.dispatcher")


class OutboxDispatcher:
    def __init__(
        self,
        service: OptimizationService | None = None,
        poll_interval_seconds: float = 1.0,
        batch_size: int = 20,
    ) -> None:
        self.service = service or OptimizationService()
        self.poll_interval = poll_interval_seconds
        self.batch_size = batch_size
        self._running = False

    def run_once(self) -> int:
        """Process one batch of pending outbox events."""
        return self.service.dispatch_outbox_events(limit=self.batch_size)

    def run_forever(self) -> None:
        """Run continuous dispatch loop with graceful signal handling."""
        self._running = True
        logger.info(
            f"Starting dedicated Outbox Dispatcher (interval={self.poll_interval}s, batch_size={self.batch_size})"
        )

        def handle_signal(sig: int, frame: Any) -> None:
            logger.info(f"Received signal {sig}; shutting down outbox dispatcher...")
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        while self._running:
            try:
                count = self.run_once()
                if count > 0:
                    logger.debug(f"Dispatched {count} outbox event(s)")
                else:
                    time.sleep(self.poll_interval)
            except Exception as exc:
                logger.error(f"Error in outbox dispatch cycle: {exc}", exc_info=True)
                time.sleep(self.poll_interval * 2)

        logger.info("Outbox Dispatcher stopped cleanly.")


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    dispatcher = OutboxDispatcher()
    dispatcher.run_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
