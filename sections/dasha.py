from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def _parse_dasha_date(date_str: str) -> datetime | None:
    for fmt in ("%d-%m-%Y %H:%M", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def _calc_timeline_pct(start_str: str, end_str: str) -> float | None:
    start = _parse_dasha_date(start_str)
    end = _parse_dasha_date(end_str)
    if not start or not end or end <= start:
        return None
    now = datetime.now()
    if now < start:
        return 0.0
    if now > end:
        return 100.0
    total = (end - start).total_seconds()
    elapsed = (now - start).total_seconds()
    return (elapsed / total) * 100


def _extract_planet_name(val) -> str:
    if isinstance(val, dict):
        return (val.get("planet") or val.get("name") or "").strip()
    if isinstance(val, str):
        return val.strip()
    return ""


def render_dasha(data: KundliData, lang: str = "en") -> str | None:
    if not data.major_vdasha and not data.current_vdasha:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("dasha_timeline.html")

    timeline_pct = None
    if data.current_vdasha and data.current_vdasha.major.start:
        timeline_pct = _calc_timeline_pct(
            data.current_vdasha.major.start,
            data.current_vdasha.major.end,
        )

    return template.render(
        current_dasha=data.current_vdasha,
        major_dasha=data.major_vdasha,
        timeline_pct=timeline_pct,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )
