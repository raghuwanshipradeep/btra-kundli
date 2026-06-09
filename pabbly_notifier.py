"""Post-payment notification to a Pabbly Connect webhook.

On a confirmed Razorpay payment, POST a full payment-success payload (customer +
payment details) to the configured Pabbly webhook. Pabbly then routes it to
downstream automations (WhatsApp confirmation, CRM/sheet logging, etc.).

This module is best-effort: it never raises out to the caller. A notification
failure must never break payment confirmation or PDF generation.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from config import settings

if TYPE_CHECKING:
    from models import KundliRequest

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0)

_IST = timezone(timedelta(hours=5, minutes=30))
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _format_dob(day: int, month: int, year: int) -> str:
    """15, 12, 1987 -> '15 Dec 1987'."""
    mon = _MONTHS[month - 1] if 1 <= month <= 12 else str(month)
    return f"{day} {mon} {year}"


def _format_time(hour: int, minute: int) -> tuple[str, str]:
    """3, 30 -> ('3:30', 'AM'); 15, 5 -> ('3:05', 'PM')."""
    am_pm = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d}", am_pm


def _now_ist() -> str:
    """Current time in IST as 'MM/DD/YYYY h:MM AM/PM' (no leading zero on hour)."""
    now = datetime.now(_IST)
    h12 = now.hour % 12 or 12
    am_pm = "AM" if now.hour < 12 else "PM"
    return f"{now.month:02d}/{now.day:02d}/{now.year} {h12}:{now.minute:02d} {am_pm}"


def _language_label(lang: str) -> str:
    return {"hi": "Hindi", "en": "English"}.get(lang, lang or "")


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
async def _post(payload: dict) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(settings.pabbly_webhook_url, json=payload)
        if response.status_code >= 400:
            # Log Pabbly's error body before raising so retries/diagnostics are useful.
            logger.warning("Pabbly webhook %s: %s", response.status_code, response.text)
        response.raise_for_status()


async def notify_payment_success(
    request: KundliRequest,
    order_id: str = "",
    payment_id: str = "",
) -> bool:
    """POST the payment-success payload to Pabbly. Returns True on success.

    Never raises — logs and returns False on any failure or when not configured.
    """
    if not settings.pabbly_webhook_url:
        logger.info("Pabbly webhook not configured; skipping for order %s", order_id)
        return False

    time_of_birth, am_pm = _format_time(request.hour, request.min)
    language = _language_label(request.lang)

    payload = {
        "event": "payment_success",
        "time_of_order": _now_ist(),
        "order_id": order_id,
        "payment_id": payment_id,
        # Amount in both units — map "Amount" column to amount_rupees for ₹.
        "amount": settings.kundli_price_paise,
        "amount_rupees": settings.kundli_price_paise // 100,
        "currency": settings.payment_currency,
        # Customer details
        "name": request.name,
        "phone": request.phone,
        "email": request.email,
        "gender": request.gender,
        "state": request.state,
        "pincode": request.pincode,
        "place": request.place,
        # Pre-formatted for the sheet
        "date_of_birth": _format_dob(request.day, request.month, request.year),
        "time_of_birth": time_of_birth,
        "am_pm": am_pm,
        "language": language,
        "report_name": f"Kundli ({language})" if language else "Kundli",
        # Raw fields (kept for existing mappings / flexibility)
        "lang": request.lang,
        "day": request.day,
        "month": request.month,
        "year": request.year,
        "hour": request.hour,
        "min": request.min,
        "lat": request.lat,
        "lon": request.lon,
        "tzone": request.tzone,
    }

    try:
        await _post(payload)
        logger.info(
            "Pabbly notified: order=%s payment=%s name=%s",
            order_id, payment_id, request.name,
        )
        return True
    except Exception:
        logger.exception(
            "Pabbly notification FAILED for order=%s payment=%s "
            "— payment/PDF unaffected", order_id, payment_id,
        )
        return False
