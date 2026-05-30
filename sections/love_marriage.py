from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.graha_profile import SIGN_LORDS

if TYPE_CHECKING:
    from models import KundliData

JAIMINI_PLANETS = {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu"}


def _find_planet(planets: list, name: str):
    for p in planets:
        if p.name == name:
            return p
    return None


def _planets_in_house(planets: list, house: int) -> list:
    return [p for p in planets if p.name != "Ascendant" and p.house == house]


def _get_house_sign(houses: list | None, house_num: int) -> str:
    if not houses:
        return ""
    for h in houses:
        hnum = getattr(h, "house_id", 0) or (h.get("house_id", 0) if isinstance(h, dict) else 0)
        if hnum == house_num:
            return getattr(h, "sign", "") or (h.get("sign", "") if isinstance(h, dict) else "")
    return ""


def _compute_darakaraka(planets: list) -> dict | None:
    candidates = [p for p in planets if p.name in JAIMINI_PLANETS]
    if len(candidates) < 7:
        return None

    for p in candidates:
        if p.name == "Rahu":
            p._adj_deg = 30.0 - p.normDegree
        else:
            p._adj_deg = p.normDegree

    sorted_planets = sorted(candidates, key=lambda p: p._adj_deg, reverse=True)
    if len(sorted_planets) >= 7:
        dk = sorted_planets[6]
        return {"name": dk.name, "sign": dk.sign, "house": dk.house, "degree": round(dk.normDegree, 2)}
    return None


def _get_report(reports: dict | None, planet_name: str) -> str:
    if not reports:
        return ""
    entry = reports.get(planet_name, {})
    if isinstance(entry, dict):
        return entry.get("report", "")
    if isinstance(entry, str):
        return entry
    return ""


def render_love_marriage(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    fifth_house_sign = _get_house_sign(data.houses, 5)
    fifth_lord = SIGN_LORDS.get(fifth_house_sign, "")
    fifth_lord_planet = _find_planet(data.planets, fifth_lord)
    planets_in_5th = _planets_in_house(data.planets, 5)

    seventh_house_sign = _get_house_sign(data.houses, 7)
    seventh_lord = SIGN_LORDS.get(seventh_house_sign, "")
    seventh_lord_planet = _find_planet(data.planets, seventh_lord)
    planets_in_7th = _planets_in_house(data.planets, 7)

    venus = _find_planet(data.planets, "Venus")
    venus_report = _get_report(data.general_house_reports, "Venus")
    venus_rashi_report = _get_report(data.general_rashi_reports, "Venus")

    darakaraka = _compute_darakaraka(data.planets)
    dk_house_report = ""
    dk_rashi_report = ""
    if darakaraka:
        dk_house_report = _get_report(data.general_house_reports, darakaraka["name"])
        dk_rashi_report = _get_report(data.general_rashi_reports, darakaraka["name"])

    fifth_reports = []
    for p in planets_in_5th:
        fifth_reports.append({
            "name": p.name,
            "report": _get_report(data.general_house_reports, p.name),
        })

    seventh_reports = []
    for p in planets_in_7th:
        seventh_reports.append({
            "name": p.name,
            "report": _get_report(data.general_house_reports, p.name),
        })

    env = make_env()
    template = env.get_template("love_marriage.html")
    return template.render(
        fifth_house_sign=fifth_house_sign,
        fifth_lord=fifth_lord,
        fifth_lord_planet=fifth_lord_planet,
        planets_in_5th=planets_in_5th,
        fifth_reports=fifth_reports,
        seventh_house_sign=seventh_house_sign,
        seventh_lord=seventh_lord,
        seventh_lord_planet=seventh_lord_planet,
        planets_in_7th=planets_in_7th,
        seventh_reports=seventh_reports,
        venus=venus,
        venus_report=venus_report,
        venus_rashi_report=venus_rashi_report,
        darakaraka=darakaraka,
        dk_house_report=dk_house_report,
        dk_rashi_report=dk_rashi_report,
        narrative=data.narratives.get("love_marriage", ""),
        locale=locale,
        lang=lang,
    )
