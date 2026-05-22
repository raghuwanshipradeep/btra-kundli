from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

GANDMOOL_NAKSHATRAS = {
    "Ashwini", "Ashlesha", "Magha", "Jyeshtha", "Moola", "Revati",
}


def _get_planet_houses(planets: list) -> dict[str, int]:
    return {p.name: p.house for p in planets if p.name != "Ascendant"}


def _check_kemadrum(ph: dict[str, int]) -> dict:
    moon_house = ph.get("Moon")
    if moon_house is None:
        return {"present": False, "description": "Moon data unavailable."}

    h2 = (moon_house % 12) + 1
    h12 = ((moon_house - 2) % 12) + 1

    adjacent_planets = [
        name for name, h in ph.items()
        if name not in ("Moon", "Sun", "Rahu", "Ketu") and h in (h2, h12)
    ]

    if not adjacent_planets:
        return {
            "present": True,
            "description": "No planet in 2nd or 12th from Moon. Moon is isolated, indicating emotional challenges.",
        }
    return {
        "present": False,
        "description": f"Planets near Moon: {', '.join(adjacent_planets)}. Kemadrum cancelled.",
    }


def _check_angarak(ph: dict[str, int]) -> dict:
    mars_h = ph.get("Mars")
    rahu_h = ph.get("Rahu")
    if mars_h is not None and mars_h == rahu_h:
        return {
            "present": True,
            "description": f"Mars and Rahu conjunct in House {mars_h}. Angarak Yoga indicates aggression and conflict.",
        }
    return {"present": False, "description": "Mars and Rahu are not conjunct."}


def _check_shrapit(ph: dict[str, int]) -> dict:
    sat_h = ph.get("Saturn")
    rahu_h = ph.get("Rahu")
    if sat_h is not None and sat_h == rahu_h:
        return {
            "present": True,
            "description": f"Saturn and Rahu conjunct in House {sat_h}. Past-life karmic debts indicated.",
        }
    return {"present": False, "description": "Saturn and Rahu are not conjunct."}


def _check_guru_chandal(ph: dict[str, int]) -> dict:
    jup_h = ph.get("Jupiter")
    rahu_h = ph.get("Rahu")
    if jup_h is not None and jup_h == rahu_h:
        return {
            "present": True,
            "description": f"Jupiter and Rahu conjunct in House {jup_h}. Wisdom may be misguided.",
        }
    return {"present": False, "description": "Jupiter and Rahu are not conjunct."}


def _check_grahan(ph: dict[str, int]) -> dict:
    sun_h = ph.get("Sun")
    moon_h = ph.get("Moon")
    rahu_h = ph.get("Rahu")
    ketu_h = ph.get("Ketu")
    findings = []
    if sun_h is not None and sun_h == rahu_h:
        findings.append(f"Sun-Rahu conjunction in House {sun_h}")
    if sun_h is not None and sun_h == ketu_h:
        findings.append(f"Sun-Ketu conjunction in House {sun_h}")
    if moon_h is not None and moon_h == rahu_h:
        findings.append(f"Moon-Rahu conjunction in House {moon_h}")
    if moon_h is not None and moon_h == ketu_h:
        findings.append(f"Moon-Ketu conjunction in House {moon_h}")

    if findings:
        return {"present": True, "description": "; ".join(findings) + ". Luminaries eclipsed by nodes."}
    return {"present": False, "description": "No Grahan Dosha. Luminaries are free from nodal conjunction."}


def _check_gandmool(planets: list) -> dict:
    moon = next((p for p in planets if p.name == "Moon"), None)
    if not moon:
        return {"present": False, "description": "Moon data unavailable."}

    if moon.nakshatra in GANDMOOL_NAKSHATRAS:
        return {
            "present": True,
            "description": f"Moon in {moon.nakshatra} nakshatra. Gandmool Dosha is present.",
        }
    return {"present": False, "description": f"Moon in {moon.nakshatra}. No Gandmool Dosha."}


def _check_daridra(planets: list, houses: list) -> dict:
    if not houses:
        return {"present": False, "description": "House data unavailable."}

    house_11 = next((h for h in houses if h.house_id == 11), None)
    if not house_11:
        return {"present": False, "description": "House 11 data unavailable."}

    lord = house_11.sign_lord
    lord_planet = next((p for p in planets if p.name == lord), None)
    if not lord_planet:
        return {"present": False, "description": "Lord of 11th house data unavailable."}

    if lord_planet.house in (6, 8, 12):
        return {
            "present": True,
            "description": f"Lord of 11th house ({lord}) is in House {lord_planet.house} (dusthana). Financial obstacles indicated.",
        }
    return {
        "present": False,
        "description": f"Lord of 11th house ({lord}) is in House {lord_planet.house}. No Daridra Yoga.",
    }


def render_extended_dosha(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    ph = _get_planet_houses(data.planets)

    doshas = {
        "kemadrum": _check_kemadrum(ph),
        "angarak": _check_angarak(ph),
        "shrapit": _check_shrapit(ph),
        "guru_chandal": _check_guru_chandal(ph),
        "grahan": _check_grahan(ph),
        "gandmool": _check_gandmool(data.planets),
        "daridra": _check_daridra(data.planets, data.houses or []),
    }

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("extended_dosha.html")
    return template.render(
        doshas=doshas,
        locale=locale,
        lang=lang,
    )
