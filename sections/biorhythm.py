from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_biorhythm(data: KundliData, lang: str = "en") -> str | None:
    if not data.biorhythm and not data.moon_biorhythm:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("biorhythm.html")
    return template.render(
        biorhythm=data.biorhythm,
        moon_biorhythm=data.moon_biorhythm,
        locale=locale,
        lang=lang,
    )
