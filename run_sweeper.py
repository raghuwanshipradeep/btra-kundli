"""Dedicated 24/7 sweeper process: sheet_orders -> kundli PDF -> Google Drive.

Run as a SINGLE separate process alongside the web app (which stays --workers 4):
    python run_sweeper.py
Exactly one instance — do NOT run replicas/workers, or the no-double-spend guarantee
(the in-process _SHEET_WORKER_LOCK in sheet_worker) breaks.

Each tick calls sheet_worker.sweep_once() (drains up to 50 pending orders), then sleeps
sheet_sweep_interval_seconds. SHEET_SWEEPER_ENABLED=false idles the loop without touching
code — but config.settings is built once at import, so the flag is frozen at process start:
the loop below re-reads an attribute, not the environment. Flipping it requires restarting
this process, and in a container RECREATING it (`docker restart` reuses the old env).
"""
from __future__ import annotations

import asyncio
import logging
import signal

from config import settings
from pipeline import touch_heartbeat
import sheet_worker

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("weasyprint").setLevel(logging.ERROR)
logger = logging.getLogger("sheet_sweeper")

_stop = asyncio.Event()


def _request_stop(*_) -> None:
    logger.info("shutdown signal received; exiting after the current sweep tick")
    _stop.set()


async def main() -> None:
    logger.info(
        "Sheet sweeper started (enabled=%s interval=%ss timeout=%ss)",
        settings.sheet_sweeper_enabled,
        settings.sheet_sweep_interval_seconds,
        settings.generation_timeout_seconds,
    )
    consecutive_failures = 0
    while not _stop.is_set():
        # Touched even when the kill switch idles the loop: an intentionally idle
        # sweeper is alive, and must not trip the container healthcheck.
        touch_heartbeat()
        if settings.sheet_sweeper_enabled:
            try:
                await sheet_worker.sweep_once()
                consecutive_failures = 0
            except Exception:
                consecutive_failures += 1
                logger.exception("sweep tick failed (%d in a row)", consecutive_failures)
        # Exponential backoff on repeated failures (capped at 10x the interval) so a
        # persistently broken dependency doesn't spam an error every single interval.
        delay = settings.sheet_sweep_interval_seconds * min(2 ** consecutive_failures, 10)
        # Interruptible sleep: wakes immediately on shutdown, else after the delay.
        try:
            await asyncio.wait_for(_stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
    logger.info("Sheet sweeper stopped")


if __name__ == "__main__":
    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        if sig is not None:
            try:
                signal.signal(sig, _request_stop)
            except (ValueError, OSError, RuntimeError):
                pass
    asyncio.run(main())
