from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.graha_profile import SIGN_LORDS
from sections.life_area_remedies import build_area_remedies

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


def _compute_amatyakaraka(planets: list) -> dict | None:
    candidates = [p for p in planets if p.name in JAIMINI_PLANETS]
    if len(candidates) < 7:
        return None

    for p in candidates:
        if p.name == "Rahu":
            p._adj_deg = 30.0 - p.normDegree
        else:
            p._adj_deg = p.normDegree

    sorted_planets = sorted(candidates, key=lambda p: p._adj_deg, reverse=True)
    if len(sorted_planets) >= 2:
        ak = sorted_planets[1]
        return {"name": ak.name, "sign": ak.sign, "house": ak.house, "degree": round(ak.normDegree, 2)}
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


def render_career_path(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    tenth_sign = _get_house_sign(data.houses, 10)
    tenth_lord = SIGN_LORDS.get(tenth_sign, "")
    tenth_lord_planet = _find_planet(data.planets, tenth_lord)
    planets_in_10th = _planets_in_house(data.planets, 10)

    sixth_sign = _get_house_sign(data.houses, 6)
    sixth_lord = SIGN_LORDS.get(sixth_sign, "")
    sixth_lord_planet = _find_planet(data.planets, sixth_lord)
    planets_in_6th = _planets_in_house(data.planets, 6)

    second_sign = _get_house_sign(data.houses, 2)
    second_lord = SIGN_LORDS.get(second_sign, "")
    second_lord_planet = _find_planet(data.planets, second_lord)

    sun = _find_planet(data.planets, "Sun")
    saturn = _find_planet(data.planets, "Saturn")
    sun_report = _get_report(data.general_house_reports, "Sun")
    saturn_report = _get_report(data.general_house_reports, "Saturn")

    amatyakaraka = _compute_amatyakaraka(data.planets)
    ak_house_report = ""
    ak_rashi_report = ""
    if amatyakaraka:
        ak_house_report = _get_report(data.general_house_reports, amatyakaraka["name"])
        ak_rashi_report = _get_report(data.general_rashi_reports, amatyakaraka["name"])

    tenth_reports = []
    for p in planets_in_10th:
        tenth_reports.append({
            "name": p.name,
            "report": _get_report(data.general_house_reports, p.name),
        })

    env = make_env()
    template = env.get_template("career_path.html")
    return template.render(
        tenth_sign=tenth_sign,
        tenth_lord=tenth_lord,
        tenth_lord_planet=tenth_lord_planet,
        planets_in_10th=planets_in_10th,
        tenth_reports=tenth_reports,
        sixth_sign=sixth_sign,
        sixth_lord=sixth_lord,
        sixth_lord_planet=sixth_lord_planet,
        planets_in_6th=planets_in_6th,
        second_sign=second_sign,
        second_lord=second_lord,
        second_lord_planet=second_lord_planet,
        sun=sun,
        saturn=saturn,
        sun_report=sun_report,
        saturn_report=saturn_report,
        amatyakaraka=amatyakaraka,
        ak_house_report=ak_house_report,
        ak_rashi_report=ak_rashi_report,
        remedies=build_area_remedies(data, [tenth_lord, "Sun", "Saturn"], lang),
        narrative=data.narratives.get("career_path", ""),
        locale=locale,
        lang=lang,
    )
