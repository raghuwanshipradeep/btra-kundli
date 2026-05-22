from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_birth_summary(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets and not data.birth_details:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("birth_summary.html")

    ascendant = sun = moon = None
    if data.planets:
        for p in data.planets:
            if p.name == "Ascendant":
                ascendant = p
            elif p.name == "Sun":
                sun = p
            elif p.name == "Moon":
                moon = p

    return template.render(
        birth=data.birth_details,
        ascendant=ascendant,
        sun=sun,
        moon=moon,
        locale=locale,
        lang=lang,
    )
