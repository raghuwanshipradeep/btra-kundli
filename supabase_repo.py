"""Durable order/payment tracking in Supabase (Postgres via PostgREST).

A best-effort audit layer that records each order and its full lifecycle
(created -> paid -> generating -> archived/failed) alongside the in-memory
order/job stores in main.py. Like pabbly_notifier and drive_uploader, this
module NEVER raises out to its caller: a Supabase outage must not block payment
confirmation or PDF generation. Every function logs and returns False on failure
or when Supabase is not configured.

Talks to Supabase over its PostgREST REST API using httpx (already a dependency)
so no extra package is needed. Writes use the service_role key, which bypasses
Row Level Security and must stay server-side only.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from config import settings
# Reuse the exact DOB/time formatting used for the Pabbly payload so the two
# integrations stay consistent.
from pabbly_notifier import _format_dob, _format_time, _language_label

if TYPE_CHECKING:
    from models import KundliRequest

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0)


def _enabled() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_key)


def _endpoint() -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{settings.supabase_table}"


def _headers(prefer: str) -> dict[str, str]:
    key = settings.supabase_service_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_row(request: KundliRequest) -> dict[str, Any]:
    """Map a KundliRequest's form fields to table columns (shared by all writes)."""
    time_of_birth, am_pm = _format_time(request.hour, request.min)
    return {
        # Customer form fields
        "name": request.name,
        "phone": request.phone,
        "email": request.email,
        "gender": request.gender,
        "place": request.place,
        "state": request.state,
        "pincode": request.pincode,
        # Birth details (raw)
        "dob_day": request.day,
        "dob_month": request.month,
        "dob_year": request.year,
        "birth_hour": request.hour,
        "birth_min": request.min,
        "lat": request.lat,
        "lon": request.lon,
        "tzone": request.tzone,
        # Pre-formatted, human-friendly
        "date_of_birth": _format_dob(request.day, request.month, request.year),
        "time_of_birth": time_of_birth,
        "am_pm": am_pm,
        "lang": request.lang,
        "language": _language_label(request.lang),
        "report_tier": request.report_tier,
    }


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        if exc.response.status_code == 429:
            return True
        return exc.response.status_code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.TimeoutException))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _request(method: str, payload: dict, *, prefer: str, params: dict | None = None) -> httpx.Response:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.request(
            method,
            _endpoint(),
            json=payload,
            headers=_headers(prefer),
            params=params,
        )
        if response.status_code >= 400:
            logger.warning("Supabase %s %s: %s", method, response.status_code, response.text)
        response.raise_for_status()
        return response


async def record_order_created(
    request: KundliRequest,
    order_id: str,
    amount_paise: int,
) -> bool:
    """Insert a fresh 'created' row for a new order.

    Plain INSERT (not upsert): if the row already exists — e.g. a fast payment
    confirmation wrote a 'paid' row before this background task ran — the unique
    order_id raises a 409 conflict, which we swallow so 'created' never clobbers
    a later status.
    """
    if not _enabled():
        logger.debug("Supabase not configured; skip created for order %s", order_id)
        return False

    row = _base_row(request)
    row.update(
        {
            "order_id": order_id,
            "status": "created",
            "amount_paise": amount_paise,
            "amount_rupees": amount_paise // 100,
            "currency": settings.payment_currency,
        }
    )

    try:
        await _request("POST", row, prefer="return=minimal")
        logger.info("Supabase row created: order=%s name=%s", order_id, request.name)
        return True
    except httpx.HTTPStatusError as exc:
        # 409 = order_id already present (paid-write won the race). Not an error.
        if exc.response.status_code == 409:
            logger.info("Supabase row for order=%s already exists; skip created", order_id)
            return True
        logger.exception("Supabase created FAILED for order=%s — payment unaffected", order_id)
        return False
    except Exception:
        logger.exception("Supabase created FAILED for order=%s — payment unaffected", order_id)
        return False


async def record_order_paid(
    request: KundliRequest,
    order_id: str,
    payment_id: str,
) -> bool:
    """Mark an order paid. Upsert on order_id so it self-heals if the 'created'
    write was lost or slow."""
    extra = {
        "order_id": order_id,
        "status": "paid",
        "payment_id": payment_id,
        "paid_at": _now_utc(),
        "amount_paise": settings.kundli_price_paise,
        "amount_rupees": settings.kundli_price_paise // 100,
        "currency": settings.payment_currency,
    }
    return await _upsert(request, order_id, extra, log="paid")


async def record_job_status(
    request: KundliRequest,
    order_id: str,
    status: str,
    *,
    drive_file_id: str | None = None,
    drive_link: str | None = None,
    error_detail: str | None = None,
    elapsed_s: float | None = None,
) -> bool:
    """Advance the report lifecycle status (generating / archived / *_failed).
    Upsert on order_id so a missing row self-heals."""
    extra: dict[str, Any] = {"order_id": order_id, "status": status}
    if drive_file_id is not None:
        extra["drive_file_id"] = drive_file_id
    if drive_link is not None:
        extra["drive_link"] = drive_link
    if error_detail is not None:
        extra["error_detail"] = error_detail
    if elapsed_s is not None:
        extra["elapsed_s"] = elapsed_s
    return await _upsert(request, order_id, extra, log=status)


async def _upsert(
    request: KundliRequest,
    order_id: str,
    extra: dict[str, Any],
    *,
    log: str,
) -> bool:
    if not _enabled():
        logger.debug("Supabase not configured; skip %s for order %s", log, order_id)
        return False

    row = _base_row(request)
    row.update(extra)

    try:
        await _request(
            "POST",
            row,
            prefer="resolution=merge-duplicates,return=minimal",
            params={"on_conflict": "order_id"},
        )
        logger.info("Supabase %s: order=%s", log, order_id)
        return True
    except Exception:
        logger.exception(
            "Supabase %s FAILED for order=%s — payment/PDF unaffected", log, order_id
        )
        return False
