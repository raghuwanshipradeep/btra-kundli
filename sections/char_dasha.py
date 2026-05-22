from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_char_dasha(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.current_chardasha
        and not data.major_chardasha
        and not data.sub_chardasha
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("char_dasha.html")
    return template.render(
        current_char=data.current_chardasha,
        major_char=data.major_chardasha,
        sub_char=data.sub_chardasha,
        locale=locale,
        lang=lang,
    )
