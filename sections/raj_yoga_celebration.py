from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES
from sections.yogas import _detect_yogas

if TYPE_CHECKING:
    from models import KundliData

RAJ_EFFECTS = {"Benefic", "Highly Benefic", "Panch Mahapurusha"}


def render_raj_yoga_celebration(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    all_yogas = _detect_yogas(data.planets, data.houses)
    raj_yogas = [y for y in all_yogas
                 if y.get("effect") in RAJ_EFFECTS
                 and y.get("name") != "No Major Yoga Detected"]

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("raj_yoga_celebration.html")
    return template.render(
        raj_yogas=raj_yogas,
        count=len(raj_yogas),
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )
