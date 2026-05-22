from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

SPECIAL_ASPECTS: dict[str, list[int]] = {
    "Mars": [4, 7, 8],
    "Jupiter": [5, 7, 9],
    "Saturn": [3, 7, 10],
    "Rahu": [5, 7, 9],
    "Ketu": [5, 7, 9],
}

DEFAULT_ASPECT = [7]


def _compute_graha_drishti(planets: list) -> dict[str, list[str]]:
    planet_houses: dict[str, int] = {}
    for p in planets:
        if p.name == "Ascendant":
            continue
        planet_houses[p.name] = p.house

    drishti: dict[str, list[str]] = {}
    for name, house in planet_houses.items():
        aspects = SPECIAL_ASPECTS.get(name, DEFAULT_ASPECT)
        aspected_houses = [((house - 1 + a) % 12) + 1 for a in aspects]
        targets = []
        for target_name, target_house in planet_houses.items():
            if target_name != name and target_house in aspected_houses:
                targets.append(target_name)
        drishti[name] = targets

    return drishti


def _compute_bhava_drishti(planets: list) -> dict[int, list[str]]:
    bhava: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    for p in planets:
        if p.name == "Ascendant":
            continue
        aspects = SPECIAL_ASPECTS.get(p.name, DEFAULT_ASPECT)
        for a in aspects:
            target_house = ((p.house - 1 + a) % 12) + 1
            bhava[target_house].append(p.name)
    return bhava


def render_drishti(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    graha = _compute_graha_drishti(data.planets)
    bhava = _compute_bhava_drishti(data.planets)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("drishti.html")
    return template.render(
        graha_drishti=graha,
        bhava_drishti=bhava,
        locale=locale,
        lang=lang,
    )
