from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING


from sections import LOCALES, make_env, planet_to_en

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)

JOURNEY_DASHA_COUNT = 3  # current mahadasha + next 2; farther periods are low-value filler


def select_journey_dashas(major_vdasha, current_planet_en, count=JOURNEY_DASHA_COUNT):
    """Current mahadasha + next (count-1). Falls back to first `count` if current not found."""
    if not major_vdasha:
        return []
    start = 0
    if current_planet_en:
        for i, d in enumerate(major_vdasha):
            if planet_to_en(d.planet) == current_planet_en:
                start = i
                break
    return major_vdasha[start:start + count]


def _parse_journey_narrative(raw: str) -> dict:
    """Parse JSON narrative into {experience: [...], avoid: [...]}. Multi-strategy with fallback."""
    if not raw:
        return {}

    text = raw.strip()

    # Strategy 1: direct JSON
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and ("experience" in parsed or "avoid" in parsed):
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 2: extract JSON from markdown fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict) and ("experience" in parsed or "avoid" in parsed):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 3: find outermost {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict) and ("experience" in parsed or "avoid" in parsed):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 4: regex-extract arrays manually
    exp_match = re.search(r'"experience"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    avoid_match = re.search(r'"avoid"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if exp_match or avoid_match:
        def _extract_strings(s: str) -> list[str]:
            return [m.group(1) for m in re.finditer(r'"([^"]+)"', s or "")]
        result = {
            "experience": _extract_strings(exp_match.group(1) if exp_match else ""),
            "avoid": _extract_strings(avoid_match.group(1) if avoid_match else ""),
        }
        if result["experience"] or result["avoid"]:
            return result

    logger.debug("Mahadasha journey narrative was not valid JSON, using fallback")
    if "{" in text and "experience" in text:
        return {"fallback_text": ""}
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
        current_planet = planet_to_en(data.current_vdasha.major.planet)

    journey_entries = []
    for dasha in select_journey_dashas(data.major_vdasha, current_planet):
        # major_vdasha planet names are NOT normalized at fetch time, so in Hindi
        # reports dasha.planet is Devanagari (e.g. "चन्द्र"); normalize to the
        # English canonical so it matches planet_map (English) and the narrative key.
        planet_en = planet_to_en(dasha.planet)
        p = planet_map.get(planet_en)
        narr_key = f"mahadasha_journey_{planet_en}"
        raw_narrative = data.narratives.get(narr_key, "") if data.narratives else ""
        parsed = _parse_journey_narrative(raw_narrative)

        journey_entries.append({
            "planet": planet_en,
            "planet_display": locale.get("planet_names", {}).get(planet_en, dasha.planet),
            "sign": locale.get("sign_names", {}).get(p.sign, p.sign) if p else "—",
            "house": p.house if p else "—",
            "start": dasha.start,
            "end": dasha.end,
            "is_current": planet_en == current_planet,
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
