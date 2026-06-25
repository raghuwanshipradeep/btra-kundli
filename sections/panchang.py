from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from models import KundliData


def _sanitize_nan(obj):
    """Recursively replace NaN-like strings and values with None."""
    if isinstance(obj, dict):
        return {k: _sanitize_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_nan(v) for v in obj]
    if isinstance(obj, float) and math.isnan(obj):
        return None
    if isinstance(obj, str) and "nan" in obj.lower():
        return None
    return obj


def _hours_to_hms(hours):
    """Convert decimal hours (e.g. 6.50) to HH:MM format."""
    if hours is None or not isinstance(hours, (int, float)):
        return "—"
    if isinstance(hours, float) and math.isnan(hours):
        return "—"
    total_minutes = round(hours * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h:02d}:{m:02d}"


def _empty_to_none(obj):
    """Convert empty dicts/lists to None so Jinja truthiness skips them."""
    if isinstance(obj, dict) and len(obj) == 0:
        return None
    if isinstance(obj, list) and len(obj) == 0:
        return None
    return obj


def _sanitize_monthly_panchang(data):
    """Convert decimal-hour time fields in monthly panchang to HH:MM."""
    if not data:
        return data
    if isinstance(data, list):
        return [_sanitize_monthly_panchang(item) for item in data]
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k in ("sunrise", "sunset", "moonrise", "moonset") and isinstance(v, (int, float)):
                result[k] = _hours_to_hms(v)
            else:
                result[k] = _sanitize_monthly_panchang(v)
        return result
    return data


def render_panchang(data: KundliData, lang: str = "en") -> str | None:
    has_any = (
        data.panchang
        or data.basic_panchang
        or data.basic_panchang_sunrise
        or data.advanced_panchang_sunrise
        or data.planet_panchang
        or data.planet_panchang_sunrise
        or data.chaughadiya_muhurta
        or data.hora_muhurta
        or data.panchang_chart
        or data.panchang_festival
        or data.monthly_panchang
    )
    if not has_any:
        return None

    logger.info(
        "Panchang data: chaughadiya=%s hora=%s",
        type(data.chaughadiya_muhurta).__name__ if data.chaughadiya_muhurta else None,
        type(data.hora_muhurta).__name__ if data.hora_muhurta else None,
    )

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("panchang.html")
    birth_ayan = 0.0
    if data.birth_details:
        birth_ayan = data.birth_details.ayanamsha

    return template.render(
        panchang=data.panchang,
        birth_ayanamsha=birth_ayan,
        basic_panchang=_sanitize_nan(data.basic_panchang),
        basic_panchang_sunrise=_sanitize_nan(data.basic_panchang_sunrise),
        advanced_panchang_sunrise=_sanitize_nan(data.advanced_panchang_sunrise),
        planet_panchang=data.planet_panchang,
        planet_panchang_sunrise=data.planet_panchang_sunrise,
        chaughadiya_muhurta=_empty_to_none(_sanitize_nan(data.chaughadiya_muhurta)),
        hora_muhurta=_empty_to_none(_sanitize_nan(data.hora_muhurta)),
        panchang_chart=data.panchang_chart,
        panchang_festival=data.panchang_festival,
        monthly_panchang=_sanitize_monthly_panchang(_sanitize_nan(data.monthly_panchang)),
        locale=locale,
        lang=lang,
    )
