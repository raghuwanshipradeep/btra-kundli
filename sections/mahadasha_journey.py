from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def _parse_journey_narrative(raw: str) -> dict:
    """Parse JSON narrative into {experience: [...], avoid: [...]}. Falls back on failure."""
    if not raw:
        return {}
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(text)
        if isinstance(parsed, dict) and ("experience" in parsed or "avoid" in parsed):
            return parsed
    except (json.JSONDecodeError, ValueError):
        logger.debug("Mahadasha journey narrative was not valid JSON, using fallback")
    return {"fallback_text": raw}


def render_mahadasha_journey(data: KundliData, lang: str = "en") -> str | None:
    if not data.major_vdasha:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    planet_map = {}
    if data.planets:
        planet_map = {p.name: p for p in data.planets if p.name != "Ascendant"}

    current_planet = None
    if data.current_vdasha and data.current_vdasha.major:
        current_planet = data.current_vdasha.major.planet

    journey_entries = []
    for dasha in data.major_vdasha:
        p = planet_map.get(dasha.planet)
        narr_key = f"mahadasha_journey_{dasha.planet}"
        raw_narrative = data.narratives.get(narr_key, "") if data.narratives else ""
        parsed = _parse_journey_narrative(raw_narrative)

        journey_entries.append({
            "planet": dasha.planet,
            "planet_display": locale.get("planet_names", {}).get(dasha.planet, dasha.planet),
            "sign": locale.get("sign_names", {}).get(p.sign, p.sign) if p else "—",
            "house": p.house if p else "—",
            "start": dasha.start,
            "end": dasha.end,
            "is_current": dasha.planet == current_planet,
            "experience": parsed.get("experience", []),
            "avoid": parsed.get("avoid", []),
            "fallback_text": parsed.get("fallback_text", ""),
        })

    env = make_env()
    template = env.get_template("mahadasha_journey.html")
    return template.render(
        entries=journey_entries,
        locale=locale,
        lang=lang,
    )
