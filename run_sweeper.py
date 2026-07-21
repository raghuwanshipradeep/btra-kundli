"""Dedicated 24/7 sweeper process: sheet_orders -> kundli PDF -> Google Drive.

Run as a SINGLE separate process alongside the web app (which stays --workers 4):
    python run_sweeper.py
Exactly one instance — do NOT run replicas/workers, or the no-double-spend guarantee
(the in-process _SHEET_WORKER_LOCK in sheet_worker) breaks.

Each tick calls sheet_worker.sweep_once() (drains up to 50 pending orders), then sleeps
sheet_sweep_interval_seconds. SHEET_SWEEPER_ENABLED=false idles the loop without a restart.
"""
from __future__ import annotations

import asyncio
import logging
import signal

from config import settings
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
    while not _stop.is_set():
        if settings.sheet_sweeper_enabled:
            try:
                await sheet_worker.sweep_once()
            except Exception:
                logger.exception("sweep tick failed")
        # Interruptible sleep: wakes immediately on shutdown, else after the interval.
        try:
            await asyncio.wait_for(_stop.wait(), timeout=settings.sheet_sweep_interval_seconds)
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
