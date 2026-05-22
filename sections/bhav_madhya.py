from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_bhav_madhya(data: KundliData, lang: str = "en") -> str | None:
    if not data.bhav_madhya:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("bhav_madhya.html")
    return template.render(
        bhav=data.bhav_madhya,
        locale=locale,
        lang=lang,
    )
