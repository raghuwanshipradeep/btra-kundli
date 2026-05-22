from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def _parse_dasha_date(date_str: str) -> tuple[int, int]:
    parts = date_str.strip().split(" ")[0].split("-")
    if len(parts) >= 3:
        return int(parts[2]), int(parts[1])
    return 0, 0


def render_life_forecast(data: KundliData, lang: str = "en") -> str | None:
    if not data.current_vdasha_all and not data.major_vdasha:
        logger.debug("life_forecast: both current_vdasha_all and major_vdasha are empty")
        return None
    if not data.varshaphal_details:
        logger.debug("life_forecast: varshaphal_details is empty")
        return None

    current_levels = []
    if data.current_vdasha_all:
        for level_name in ("major", "sub", "sub_sub", "sub_sub_sub"):
            level = data.current_vdasha_all.get(level_name)
            if level and isinstance(level, dict):
                current_levels.append({
                    "level": level_name.replace("_", " ").title(),
                    "planet": level.get("planet", ""),
                    "start": level.get("start", ""),
                    "end": level.get("end", ""),
                })

    varshaphal_summary = {}
    if data.varshaphal_details:
        vd = data.varshaphal_details
        varshaphal_summary = {
            "year": vd.get("year", ""),
            "ascendant": vd.get("varshaphal_ascendant", ""),
            "muntha": vd.get("muntha_sign", ""),
            "varshesh": vd.get("varshesh", ""),
        }

    forecast_notes = []
    if current_levels:
        major = current_levels[0] if current_levels else None
        if major:
            planet = major["planet"]
            forecast_notes.append(
                f"Currently running {planet} Mahadasha ({major['start']} to {major['end']}). "
                f"This period's results are shaped by {planet}'s natal placement and dignity."
            )
        if len(current_levels) >= 2:
            sub = current_levels[1]
            forecast_notes.append(
                f"Antardasha of {sub['planet']} is active ({sub['start']} to {sub['end']}), "
                f"modifying the main period's outcomes."
            )

    if data.varshaphal_muntha:
        muntha = data.varshaphal_muntha
        if muntha.get("report"):
            forecast_notes.append(muntha["report"])

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("life_forecast.html")
    return template.render(
        current_levels=current_levels,
        varshaphal_summary=varshaphal_summary,
        forecast_notes=forecast_notes,
        narrative=data.narratives.get("life_forecast", ""),
        locale=locale,
        lang=lang,
    )
