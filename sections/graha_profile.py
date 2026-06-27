from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.drishti import SPECIAL_ASPECTS, DEFAULT_ASPECT
from sections.dignity import _get_dignity

if TYPE_CHECKING:
    from models import KundliData

PLANETS_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

# Top-of-page deity illustration per planet (files live in templates/images/).
PLANET_IMAGES: dict[str, str] = {
    "Sun": "sun.png",
}

KARAKA_NAMES = [
    "Atmakaraka", "Amatyakaraka", "Bhratrikaraka", "Matrikaraka",
    "Putrakaraka", "Gnatikaraka", "Darakaraka",
]

JAIMINI_PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}

SIGN_LORDS: dict[str, str] = {
    "Aries": "Mars", "Taurus": "Venus", "Gemini": "Mercury", "Cancer": "Moon",
    "Leo": "Sun", "Virgo": "Mercury", "Libra": "Venus", "Scorpio": "Mars",
    "Sagittarius": "Jupiter", "Capricorn": "Saturn", "Aquarius": "Saturn", "Pisces": "Jupiter",
}


def _compute_karaka_map(planets: list) -> dict[str, str]:
    candidates = [p for p in planets if p.name in JAIMINI_PLANETS]
    if len(candidates) < 7:
        return {}

    for p in candidates:
        if p.name == "Rahu":
            p._adj_degree = 30.0 - p.normDegree
        else:
            p._adj_degree = p.normDegree

    sorted_planets = sorted(candidates, key=lambda p: p._adj_degree, reverse=True)
    result: dict[str, str] = {}
    for i, karaka in enumerate(KARAKA_NAMES):
        if i < len(sorted_planets):
            result[sorted_planets[i].name] = karaka
    return result


def _compute_aspects_given(planet_name: str, planet_house: int) -> list[int]:
    aspects = SPECIAL_ASPECTS.get(planet_name, DEFAULT_ASPECT)
    return [((planet_house - 1 + a) % 12) + 1 for a in aspects]


def _compute_aspects_received(target_name: str, target_house: int, planets: list) -> list[str]:
    aspecting = []
    for p in planets:
        if p.name == "Ascendant" or p.name == target_name:
            continue
        aspects = SPECIAL_ASPECTS.get(p.name, DEFAULT_ASPECT)
        aspected_houses = [((p.house - 1 + a) % 12) + 1 for a in aspects]
        if target_house in aspected_houses:
            aspecting.append(p.name)
    return aspecting


def _get_nature_label(planet_name: str, planet_nature: list | None) -> str:
    if not planet_nature:
        return ""
    for entry in planet_nature:
        if isinstance(entry, dict):
            name = entry.get("planet") or entry.get("name", "")
            if name == planet_name:
                nature = entry.get("nature") or entry.get("type", "")
                return str(nature)
    return ""


def render_graha_profile(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    karaka_map = _compute_karaka_map(data.planets)

    profiles = []
    for planet_name in PLANETS_ORDER:
        planet_obj = None
        for p in data.planets:
            if p.name == planet_name:
                planet_obj = p
                break
        if not planet_obj:
            continue

        dignity = _get_dignity(planet_name, planet_obj.sign)
        nature = _get_nature_label(planet_name, data.planet_nature)
        sign_lord = SIGN_LORDS.get(planet_obj.sign, "")
        aspects_given = _compute_aspects_given(planet_name, planet_obj.house)
        aspects_received = _compute_aspects_received(planet_name, planet_obj.house, data.planets)
        karaka_role = karaka_map.get(planet_name, "")

        house_report = ""
        rashi_report = ""
        if data.general_house_reports:
            hr = data.general_house_reports.get(planet_name, {})
            if isinstance(hr, dict):
                house_report = hr.get("report", "")
            elif isinstance(hr, str):
                house_report = hr
        if data.general_rashi_reports:
            rr = data.general_rashi_reports.get(planet_name, {})
            if isinstance(rr, dict):
                rashi_report = rr.get("report", "")
            elif isinstance(rr, str):
                rashi_report = rr

        profiles.append({
            "name": planet_name,
            "image": PLANET_IMAGES.get(planet_name, ""),
            "house": planet_obj.house,
            "sign": planet_obj.sign,
            "sign_lord": sign_lord,
            "degree": round(planet_obj.normDegree, 2),
            "nakshatra": getattr(planet_obj, "nakshatra", ""),
            "nakshatra_lord": getattr(planet_obj, "nakshatraLord", ""),
            "is_retro": getattr(planet_obj, "isRetro", "false") == "true",
            "dignity": dignity,
            "nature": nature,
            "karaka_role": karaka_role,
            "aspects_given": aspects_given,
            "aspects_received": aspects_received,
            "house_report": house_report,
            "rashi_report": rashi_report,
        })

    if not profiles:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("graha_profile.html")
    return template.render(
        profiles=profiles,
        locale=locale,
        lang=lang,
    )
