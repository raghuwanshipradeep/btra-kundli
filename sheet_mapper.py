"""Pure, synchronous mapping from a sheet_orders row to a KundliRequest.

Kept PURE (no I/O, no async) so it is trivially unit-testable and can never spend API
money: any parse/validation failure returns ``(None, "specific reason")`` and the worker
parks the row BEFORE any AstrologyAPI/Anthropic call.

Parsing behavior is identical to the helpers that previously lived in main.py
(``_parse_dob`` / ``_parse_tob`` / ``_lang_from_report_language``): the typed ``date_of_birth``
(Postgres date) and ``time_of_birth`` columns are already normalized by the sync, so we parse
those, not the ``*_raw`` fallbacks. tzone is NOT set here — sheet_orders has no timezone column
and the accurate value needs an async DST lookup, so sheet_worker fills ``request.tzone`` after a
successful map. It is left at 0.0 as a placeholder that is always overwritten.
"""
from __future__ import annotations

import logging
import re

from models import KundliRequest

logger = logging.getLogger(__name__)

_PLACEHOLDER_TZONE = 0.0  # always overwritten by sheet_worker._lookup_tzone; never used as-is


def _lang_from_report_language(value: str | None) -> str:
    """report_language holds full words (Hindi / English). Map to the PDF lang code."""
    v = (value or "").strip().lower()
    if v.startswith("hin") or "हिन" in v or "देवन" in v:
        return "hi"
    if v.startswith("eng"):
        return "en"
    if v:
        logger.warning("sheet_orders: unrecognized report_language %r -> defaulting to en", value)
    return "en"


def _parse_dob(value) -> tuple[int, int, int]:
    """'YYYY-MM-DD' -> (year, month, day). The column is a Postgres date, so the format is
    fixed; a null means the sync couldn't parse it (kept only in date_of_birth_raw)."""
    m = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})", str(value) if value is not None else "")
    if not m:
        raise ValueError(f"missing/unparseable date_of_birth: {value!r}")
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise ValueError(f"invalid date_of_birth: {value!r}")
    return year, month, day


def _parse_tob(value) -> tuple[int, int]:
    """'HH:MM[:SS]' -> (hour, minute). Birth time drives the whole chart, so a missing value
    is rejected rather than defaulted to noon (which would emit a confidently-wrong kundli)."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2})", str(value) if value is not None else "")
    if not m:
        raise ValueError(f"missing/unparseable time_of_birth: {value!r}")
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"invalid time_of_birth: {value!r}")
    return hour, minute


def _parse_latlon(row: dict) -> tuple[float, float]:
    lat, lon = row.get("latitude"), row.get("longitude")
    if lat is None or lon is None:
        raise ValueError("missing latitude/longitude")
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        raise ValueError(f"unparseable latitude/longitude: {lat!r}, {lon!r}")


def map_sheet_row(row: dict) -> tuple[KundliRequest | None, str | None]:
    """(request_without_tzone, None) on success; (None, specific_error) on any failure.

    The returned request's ``tzone`` is a placeholder — the caller must set it via an async
    DST lookup before generating.
    """
    try:
        year, month, day = _parse_dob(row.get("date_of_birth"))
        hour, minute = _parse_tob(row.get("time_of_birth"))
        lat, lon = _parse_latlon(row)
    except ValueError as exc:
        return None, str(exc)

    request = KundliRequest(
        name=(row.get("name") or "Native").strip() or "Native",
        day=day, month=month, year=year, hour=hour, min=minute,
        lat=lat, lon=lon, tzone=_PLACEHOLDER_TZONE,
        lang=_lang_from_report_language(row.get("report_language")),
        place=row.get("place_of_birth") or "",
        phone=str(row.get("phone") or ""),
        email=row.get("email") or "",
        gender=row.get("gender") or "",
        state=row.get("state") or "",
        pincode=str(row.get("pin_code") or ""),
        report_tier="detailed",
    )
    return request, None
