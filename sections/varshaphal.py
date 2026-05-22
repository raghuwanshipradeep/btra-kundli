from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData

logger = logging.getLogger(__name__)


def render_varshaphal(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.varshaphal_details
        and not data.varshaphal_planets
        and not data.varshaphal_year_chart
        and not data.varshaphal_month_chart
        and not data.varshaphal_muntha
        and not data.varshaphal_mudda_dasha
        and not data.varshaphal_panchavargeeya_bala
        and not data.varshaphal_harsha_bala
        and not data.varshaphal_saham_points
        and not data.varshaphal_yoga
    ):
        logger.debug("varshaphal: all 10 API fields are empty")
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("varshaphal.html")
    return template.render(
        year_chart=data.varshaphal_year_chart,
        month_chart=data.varshaphal_month_chart,
        details=data.varshaphal_details,
        planets=data.varshaphal_planets,
        muntha=data.varshaphal_muntha,
        mudda_dasha=data.varshaphal_mudda_dasha,
        panchavargeeya_bala=data.varshaphal_panchavargeeya_bala,
        harsha_bala=data.varshaphal_harsha_bala,
        saham_points=data.varshaphal_saham_points,
        yoga=data.varshaphal_yoga,
        locale=locale,
        lang=lang,
    )
