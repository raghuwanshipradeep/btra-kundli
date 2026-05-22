from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_yogini_dasha(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.major_yogini_dasha
        and not data.current_yogini_dasha
        and not data.sub_yogini_dasha
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("yogini_dasha.html")
    return template.render(
        major_yogini=data.major_yogini_dasha,
        current_yogini=data.current_yogini_dasha,
        sub_yogini=data.sub_yogini_dasha,
        locale=locale,
        lang=lang,
    )
