from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.career_path import _get_house_sign
from sections.life_area_remedies import build_area_remedies
from sections.remedy_constants import SIGN_LORDS

if TYPE_CHECKING:
    from models import KundliData


def _find(planets: list, name: str):
    return next((p for p in planets if p.name == name), None)


def render_material_comforts(data: KundliData, lang: str = "en") -> str | None:
    """Home, Property & Vehicle — material comforts.

    4th house = home, property, land, vehicles and domestic happiness. Venus is
    the karaka of vehicles/luxury; Mars co-signifies land and property.
    """
    if not data.planets:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    fourth_sign = _get_house_sign(data.houses, 4)
    fourth_lord = SIGN_LORDS.get(fourth_sign, "")
    fourth_lord_planet = _find(data.planets, fourth_lord)
    planets_in_4th = [p for p in data.planets if p.name != "Ascendant" and p.house == 4]

    venus = _find(data.planets, "Venus")
    mars = _find(data.planets, "Mars")

    remedies = build_area_remedies(data, [fourth_lord, "Venus", "Mars"], lang)

    env = make_env()
    template = env.get_template("material_comforts.html")
    return template.render(
        fourth_sign=fourth_sign,
        fourth_lord=fourth_lord,
        fourth_lord_planet=fourth_lord_planet,
        planets_in_4th=planets_in_4th,
        venus=venus,
        mars=mars,
        remedies=remedies,
        narrative=data.narratives.get("material_comforts", ""),
        locale=locale,
        lang=lang,
    )
