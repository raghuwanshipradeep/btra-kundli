from __future__ import annotations

from typing import TYPE_CHECKING


from config import settings
from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def render_closing_cta(data: KundliData, lang: str = "en") -> str | None:
    if not settings.cta_consult_url and not settings.cta_pooja_url \
            and not settings.cta_rudraksha_url:
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("closing_cta.html")
    return template.render(
        cta_consult_url=settings.cta_consult_url,
        cta_pooja_url=settings.cta_pooja_url,
        cta_rudraksha_url=settings.cta_rudraksha_url,
        name=data.request.name,
        locale=locale,
        lang=lang,
    )
