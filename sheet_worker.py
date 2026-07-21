"""Sheet-driven kundli generation worker.

A second producer alongside the paid Razorpay flow: read SUCCESSFUL rows from the Supabase
``sheet_orders`` table (fed by the hourly Apps Script sync), map each to a KundliRequest, and run
the SAME pipeline (``pipeline._build_kundli_pdf`` -> ``upload_kundli_pdf``). Status lives in
sheet_orders' ``kundli_*`` columns; kundli_orders and the paid flow are untouched.

``sweep_once()`` is invoked both by the FastAPI endpoint ``POST /admin/process-sheet-orders`` and
by the standalone loop in ``run_sweeper.py``. It imports ``pipeline`` (not ``main``) so it carries
no FastAPI dependency. The module-level ``_SHEET_WORKER_LOCK`` + the ``kundli_*`` columns are what
prevent double-generation, which is why the sweeper must run as a SINGLE process (no replicas).
"""
from __future__ import annotations

import asyncio
import logging
import time

from api_client import AstrologyAPIClient
from config import settings
from drive_uploader import folder_for_amount, upload_kundli_pdf
from pipeline import _build_kundli_pdf, _get_generation_slots
from sheet_mapper import map_sheet_row
import sheet_orders_repo as sheet_repo

logger = logging.getLogger(__name__)

_SHEET_WORKER_LOCK = asyncio.Lock()


async def _lookup_tzone(day, month, year, hour, minute, lat, lon) -> float:
    """Derive the DST-aware timezone offset the way the web form does — sheet_orders has no
    timezone column. Falls back to IST (5.5) if the lookup is unavailable."""
    payload = {
        "day": day, "month": month, "year": year, "hour": hour, "min": minute,
        "lat": lat, "lon": lon, "tzone": 5.5,
    }
    try:
        async with AstrologyAPIClient() as client:
            result = await client.get_timezone_with_dst(payload)
        if result and result.get("timezone") is not None:
            return float(result["timezone"])
    except Exception:
        logger.exception("tzone lookup failed; defaulting to 5.5 IST")
    return 5.5


def _dedup_by_order_id(rows: list[dict]) -> list[dict]:
    """First row per order_id — an edited sheet row can insert a second row with the same id,
    and requirement is one kundli per order. Rows with no order_id are dropped."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        oid = row.get("order_id")
        if not oid or oid in seen:
            continue
        seen.add(oid)
        out.append(row)
    return out


async def sweep_once(limit: int = 50) -> dict:
    """Sequentially generate + archive a kundli for each pending SUCCESSFUL sheet order.

    One order is fully generated and saved before the next starts. The module lock makes
    overlapping ticks a no-op; the kundli_* columns make it idempotent across runs.
    """
    if _SHEET_WORKER_LOCK.locked():
        logger.info("sheet worker already running; skipping this invocation")
        return {"status": "already_running"}

    cap = settings.sheet_orders_kundli_max_attempts
    summary: dict = {"status": "ok", "processed": 0, "skipped": 0, "failed": 0, "details": []}

    async with _SHEET_WORKER_LOCK:
        await sheet_repo.reclaim_stale(settings.generation_timeout_seconds)
        rows = _dedup_by_order_id(await sheet_repo.fetch_pending(limit))
        logger.info("sheet worker: %d pending order(s)", len(rows))

        for row in rows:
            order_id = row["order_id"]
            attempts = int(row.get("kundli_attempts") or 0)

            # Gate on the claim landing. If we can't even write kundli_status='generating',
            # the DB is unwritable for this row — so mark_done would fail too, and we'd produce
            # a PDF we can't record (guaranteed duplicate next run). Skip before spending any
            # API calls. This is what stops a broken grant from silently piling up orphan PDFs.
            if not await sheet_repo.claim(order_id, attempts):
                summary["failed"] += 1
                summary["details"].append({
                    "order_id": order_id, "result": "claim_failed",
                    "reason": "could not write kundli_status (DB not writable?); skipped to avoid an orphan PDF",
                })
                logger.error("SHEET CLAIM FAILED: order=%s — skipping generation (check UPDATE grant)", order_id)
                continue

            request, err = map_sheet_row(row)
            if err:
                # Bad birth data — park it, don't retry (retrying bad data just burns attempts).
                await sheet_repo.mark_failed(order_id, err, permanent=True)
                summary["skipped"] += 1
                summary["details"].append({"order_id": order_id, "result": "skipped", "reason": err})
                logger.warning("sheet order %s skipped: %s", order_id, err)
                continue

            # sheet_orders has no timezone column; derive it (DST-aware) before generating.
            request.tzone = await _lookup_tzone(
                request.day, request.month, request.year,
                request.hour, request.min, request.lat, request.lon,
            )

            start = time.time()
            logger.info("SHEET BG START: order=%s customer=%s", order_id, request.name)
            try:
                async with _get_generation_slots():
                    pdf_bytes, filename = await asyncio.wait_for(
                        _build_kundli_pdf(request, order_id),
                        timeout=settings.generation_timeout_seconds,
                    )
                # Route by order value: orders above the premium threshold archive to the
                # premium folder, the rest to the default folder (folder_for_amount handles
                # null/unparseable amounts by falling back to the default).
                amount = row.get("order_total_amount")
                target_folder = folder_for_amount(amount)
                logger.info(
                    "SHEET routing: order=%s amount=%s -> folder=%s",
                    order_id, amount, target_folder,
                )
                drive_result = await upload_kundli_pdf(
                    pdf_bytes=pdf_bytes,
                    filename=filename,
                    customer_name=request.name,
                    order_id=order_id,
                    payment_id="",
                    folder_id=target_folder,
                )
                if not drive_result:
                    permanent = attempts + 1 >= cap
                    await sheet_repo.mark_failed(order_id, "drive upload failed", permanent=permanent)
                    summary["failed"] += 1
                    summary["details"].append({"order_id": order_id, "result": "failed", "reason": "drive upload failed"})
                    logger.error("SHEET DRIVE FAILED: order=%s customer=%s", order_id, request.name)
                    continue

                drive_link = drive_result.get("webViewLink", "")
                # The PDF is in Drive now. If recording that fails, do NOT report success —
                # the row stays pending and would regenerate (duplicate). Surface it loudly as
                # a distinct state so the operator knows a real file exists but is unrecorded.
                if not await sheet_repo.mark_done(order_id, drive_result.get("id"), drive_link):
                    summary["failed"] += 1
                    summary["details"].append({
                        "order_id": order_id, "result": "archived_unmarked",
                        "drive_link": drive_link,
                        "reason": "PDF uploaded to Drive but DB write failed; will regenerate unless fixed",
                    })
                    logger.error(
                        "SHEET ARCHIVED BUT UNMARKED: order=%s — PDF at %s but kundli_status not written "
                        "(check UPDATE grant); row will regenerate until fixed",
                        order_id, drive_link,
                    )
                    continue

                summary["processed"] += 1
                summary["details"].append({
                    "order_id": order_id, "result": "archived", "drive_link": drive_link,
                })
                logger.info(
                    "SHEET BG COMPLETE: order=%s customer=%s elapsed=%.1fs",
                    order_id, request.name, time.time() - start,
                )
            except Exception as exc:  # noqa: BLE001 — one bad order must not stop the batch
                permanent = attempts + 1 >= cap
                await sheet_repo.mark_failed(order_id, f"{type(exc).__name__}: {exc}", permanent=permanent)
                summary["failed"] += 1
                summary["details"].append({"order_id": order_id, "result": "failed", "reason": str(exc)})
                logger.exception("SHEET BG FAILED: order=%s customer=%s", order_id, request.name)

    logger.info(
        "sheet worker run done: processed=%d skipped=%d failed=%d",
        summary["processed"], summary["skipped"], summary["failed"],
    )
    return summary
