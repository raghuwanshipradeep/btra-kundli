from __future__ import annotations

import logging
from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def render_panchada_maitri(data: KundliData, lang: str = "en") -> str | None:
    if not data.panchada_maitri:
        logger.debug("panchada_maitri: API returned no data")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    planet_names = locale.get("planet_names", {})
    maitri = data.panchada_maitri

    env = make_env()
    template = env.get_template("panchada_maitri.html")
    return template.render(
        maitri=maitri,
        planet_names=planet_names,
        locale=locale,
        lang=lang,
    )
