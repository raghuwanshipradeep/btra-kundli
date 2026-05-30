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


def _compute_atmakaraka(planets: list) -> dict | None:
    candidates = [p for p in planets if p.name in JAIMINI_PLANETS]
    if len(candidates) < 7:
        return None
    for p in candidates:
        if p.name == "Rahu":
            p._adj_deg = 30.0 - p.normDegree
        else:
            p._adj_deg = p.normDegree
    sorted_planets = sorted(candidates, key=lambda p: p._adj_deg, reverse=True)
    if sorted_planets:
        ak = sorted_planets[0]
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


def _check_spiritual_yogas(planets: list) -> list[dict]:
    yogas = []
    jupiter = _find_planet(planets, "Jupiter")
    ketu = _find_planet(planets, "Ketu")
    moon = _find_planet(planets, "Moon")
    saturn = _find_planet(planets, "Saturn")

    if jupiter and jupiter.house in (9, 12):
        yogas.append({"name": "Jupiter in Dharma/Moksha", "planet": "Jupiter", "house": jupiter.house})
    if ketu and ketu.house == 12:
        yogas.append({"name": "Ketu in 12th (Moksha Karaka)", "planet": "Ketu", "house": 12})
    if jupiter and ketu and jupiter.house == ketu.house:
        yogas.append({"name": "Jupiter-Ketu Conjunction (Spiritual Wisdom)", "planet": "Jupiter-Ketu", "house": jupiter.house})
    if moon and moon.house in (4, 9, 12):
        yogas.append({"name": "Moon in Spiritual House", "planet": "Moon", "house": moon.house})
    if saturn and saturn.house == 12:
        yogas.append({"name": "Saturn in 12th (Renunciation)", "planet": "Saturn", "house": 12})

    benefics_in_5_9 = []
    for p in planets:
        if p.name in ("Jupiter", "Venus", "Mercury", "Moon") and p.house in (5, 9):
            benefics_in_5_9.append(p.name)
    if len(benefics_in_5_9) >= 2:
        yogas.append({"name": "Multiple Benefics in Trikona (5th/9th)", "planet": ", ".join(benefics_in_5_9), "house": 0})

    return yogas


def render_spiritual_potential(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    ninth_sign = _get_house_sign(data.houses, 9)
    ninth_lord = SIGN_LORDS.get(ninth_sign, "")
    planets_in_9th = _planets_in_house(data.planets, 9)

    twelfth_sign = _get_house_sign(data.houses, 12)
    twelfth_lord = SIGN_LORDS.get(twelfth_sign, "")
    planets_in_12th = _planets_in_house(data.planets, 12)

    fifth_sign = _get_house_sign(data.houses, 5)
    fifth_lord = SIGN_LORDS.get(fifth_sign, "")
    planets_in_5th = _planets_in_house(data.planets, 5)

    jupiter = _find_planet(data.planets, "Jupiter")
    ketu = _find_planet(data.planets, "Ketu")
    jupiter_report = _get_report(data.general_house_reports, "Jupiter")
    ketu_report = _get_report(data.general_house_reports, "Ketu")

    atmakaraka = _compute_atmakaraka(data.planets)
    ak_report = ""
    if atmakaraka:
        ak_report = _get_report(data.general_house_reports, atmakaraka["name"])

    spiritual_yogas = _check_spiritual_yogas(data.planets)

    d20_chart = None
    d20_image = None
    if data.horo_charts:
        d20_chart = data.horo_charts.get("D20")
    if data.horo_chart_images:
        d20_image = data.horo_chart_images.get("D20")

    env = make_env()
    template = env.get_template("spiritual_potential.html")
    return template.render(
        ninth_sign=ninth_sign,
        ninth_lord=ninth_lord,
        planets_in_9th=planets_in_9th,
        twelfth_sign=twelfth_sign,
        twelfth_lord=twelfth_lord,
        planets_in_12th=planets_in_12th,
        fifth_sign=fifth_sign,
        fifth_lord=fifth_lord,
        planets_in_5th=planets_in_5th,
        jupiter=jupiter,
        ketu=ketu,
        jupiter_report=jupiter_report,
        ketu_report=ketu_report,
        atmakaraka=atmakaraka,
        ak_report=ak_report,
        spiritual_yogas=spiritual_yogas,
        d20_image=d20_image,
        narrative=data.narratives.get("spiritual_potential", ""),
        locale=locale,
        lang=lang,
    )
