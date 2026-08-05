from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING


from branding import brand_for
from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_cover(data: KundliData, lang: str = "en") -> str | None:
    locale = LOCALES.get(lang, LOCALES["en"])
    # Brand passed for the logo in partials/brand_signature.html.
    env = make_env(brand_for(data))
    template = env.get_template("cover.html")
    return template.render(
        name=data.request.name,
        request=data.request,
        birth=data.birth_details,
        planets=data.planets,
        locale=locale,
        lang=lang,
        generated_date=date.today().strftime("%d %B %Y"),
    )
