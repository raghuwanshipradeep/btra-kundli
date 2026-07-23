"""Read and track ``sheet_orders`` rows for the sheet-driven kundli worker.

Parallel to ``supabase_repo.py`` (which is hard-wired to ``kundli_orders``). Talks to the
``sheet_orders`` table over PostgREST with the ``service_role`` key. Like the rest of the
integration layer, this NEVER raises out to its caller: a Supabase blip returns ``[]`` / ``False``
so the worker degrades gracefully instead of crashing a run. The ``service_role`` key bypasses
RLS and must stay server-side only.

Reuses ``_headers`` and ``_should_retry`` from ``supabase_repo`` (both table-independent) so the
auth and retry policy can't drift between the two modules; only the endpoint differs.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from config import settings
from supabase_repo import _headers, _should_retry

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0)

# Columns the row -> KundliRequest mapping needs, plus the tracking fields the worker reads.
_SELECT = ",".join(
    [
        "order_id",
        "name",
        "phone",
        "email",
        "gender",
        "state",
        "pin_code",
        "place_of_birth",
        "date_of_birth",
        "time_of_birth",
        "latitude",
        "longitude",
        "report_language",
        "report_name",
        "order_total_amount",
        "addons_name",
        "payment_status",
        "sheet_row",
        "kundli_status",
        "kundli_attempts",
    ]
)


def _enabled() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_key)


def _endpoint() -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.sheet_orders_table}"


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _get(params: dict) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _endpoint(), headers=_headers("return=representation"), params=params
        )
        if resp.status_code >= 400:
            logger.warning("sheet_orders GET %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _patch(params: dict, body: dict) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _endpoint(), headers=_headers("return=minimal"), params=params, json=body
        )
        if resp.status_code >= 400:
            logger.warning("sheet_orders PATCH %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _patch_returning(params: dict, body: dict) -> list[dict]:
    """PATCH with ``return=representation`` so the caller can see WHICH rows matched.
    An empty list means the filter matched nothing — the basis of the atomic claim."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _endpoint(), headers=_headers("return=representation"), params=params, json=body
        )
        if resp.status_code >= 400:
            logger.warning("sheet_orders PATCH %s: %s", resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()


async def fetch_pending(limit: int) -> list[dict]:
    """SUCCESSFUL rows with an order_id that still need a kundli, oldest sheet row first.

    Pending = kundli_status is null (never tried) OR 'failed' (retryable), and attempts below
    the cap so a poison row eventually stops. PostgREST wildcard uses ``*`` (not ``%``) to avoid
    URL-encoding the pattern.
    """
    if not _enabled():
        logger.debug("Supabase not configured; sheet_orders fetch_pending -> []")
        return []
    params = {
        "select": _SELECT,
        "order_id": "not.is.null",
        "payment_status": "ilike.success*",
        "or": "(kundli_status.is.null,kundli_status.eq.failed)",
        "kundli_attempts": f"lt.{settings.sheet_orders_kundli_max_attempts}",
        "order": "sheet_row.asc",
        "limit": str(limit),
    }
    try:
        return await _get(params)
    except Exception:
        logger.exception("sheet_orders fetch_pending failed")
        return []


async def fetch_failed(limit: int = 100) -> list[dict]:
    """Rows the worker gave up on or must retry, newest first — for GET /admin/sheet-jobs.

    Includes retryable 'failed' and terminal 'failed_permanent'. ``sheet_row`` lets the
    operator jump straight to the bad cell in the source Google Sheet.
    """
    if not _enabled():
        return []
    params = {
        "select": "order_id,sheet_row,name,phone,kundli_status,kundli_attempts,kundli_error,order_at",
        "kundli_status": "in.(failed,failed_permanent)",
        "order": "order_at.desc.nullslast",
        "limit": str(limit),
    }
    try:
        return await _get(params)
    except Exception:
        logger.exception("sheet_orders fetch_failed failed")
        return []


async def reclaim_stale(timeout_s: int) -> None:
    """Return rows stuck in 'generating' past the timeout to 'failed' so they retry.

    Covers a worker that crashed mid-generation and left a row claimed. ``updated_at`` is
    auto-bumped by the table's trigger on every write, so it marks when the claim was made.
    """
    if not _enabled():
        return
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=timeout_s)).isoformat()
    params = {"kundli_status": "eq.generating", "updated_at": f"lt.{cutoff}"}
    try:
        await _patch(params, {"kundli_status": "failed", "kundli_error": "reclaimed: stale generating claim"})
    except Exception:
        logger.exception("sheet_orders reclaim_stale failed")


async def claim(order_id: str, attempts: int) -> bool:
    """Atomically mark this order 'generating' and bump the attempt counter.

    The PATCH filter requires the row to still be claimable (kundli_status null or
    'failed'), so the status check and the write are one server-side operation: if
    another process claimed the order first, the filter matches zero rows and this
    returns False. That makes the claim race-safe across processes — e.g. the
    sweeper vs a manual POST /admin/process-sheet-orders — not just within one.

    Updating all claimable duplicate rows (a sheet edit can insert a second row with
    the same order_id) keeps their status consistent and is what makes a later
    'archived' cover them too.
    """
    if not _enabled():
        logger.debug("Supabase not configured; skip sheet_orders claim for %s", order_id)
        return False
    params = {
        "order_id": f"eq.{order_id}",
        "or": "(kundli_status.is.null,kundli_status.eq.failed)",
    }
    body = {"kundli_status": "generating", "kundli_attempts": attempts + 1}
    try:
        rows = await _patch_returning(params, body)
    except Exception:
        logger.exception("sheet_orders claim FAILED for order=%s", order_id)
        return False
    if not rows:
        logger.info("sheet_orders claim lost for order=%s (already claimed elsewhere)", order_id)
        return False
    logger.info("sheet_orders claim: order=%s (%d row(s))", order_id, len(rows))
    return True


async def mark_done(order_id: str, drive_file_id: str | None, drive_link: str | None) -> bool:
    return await _update(
        order_id,
        {
            "kundli_status": "archived",
            "kundli_drive_file_id": drive_file_id,
            "kundli_drive_link": drive_link or "",
            "kundli_generated_at": _now_utc(),
            "kundli_error": None,
        },
        log="done",
    )


async def mark_failed(order_id: str, error: str, *, permanent: bool) -> bool:
    return await _update(
        order_id,
        {
            "kundli_status": "failed_permanent" if permanent else "failed",
            "kundli_error": (error or "")[:500],
        },
        log="failed_permanent" if permanent else "failed",
    )


async def _update(order_id: str, body: dict, *, log: str) -> bool:
    if not _enabled():
        logger.debug("Supabase not configured; skip sheet_orders %s for %s", log, order_id)
        return False
    try:
        await _patch({"order_id": f"eq.{order_id}"}, body)
        logger.info("sheet_orders %s: order=%s", log, order_id)
        return True
    except Exception:
        logger.exception("sheet_orders %s FAILED for order=%s", log, order_id)
        return False
