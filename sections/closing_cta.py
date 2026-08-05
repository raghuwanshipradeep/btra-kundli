from __future__ import annotations

from typing import TYPE_CHECKING


from branding import brand_for
from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_closing_cta(data: KundliData, lang: str = "en") -> str | None:
    brand = brand_for(data)
    if not brand.cta_consult_url and not brand.cta_pooja_url \
            and not brand.cta_rudraksha_url:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env(brand)
    template = env.get_template("closing_cta.html")
    return template.render(
        cta_consult_url=brand.cta_consult_url,
        cta_pooja_url=brand.cta_pooja_url,
        cta_rudraksha_url=brand.cta_rudraksha_url,
        name=data.request.name,
        locale=locale,
        lang=lang,
    )
