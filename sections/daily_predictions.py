from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES

if TYPE_CHECKING:
    from models import KundliData


def render_daily_predictions(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.daily_nakshatra_prediction
        and not data.daily_nakshatra_prediction_next
        and not data.daily_nakshatra_prediction_previous
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("daily_predictions.html")
    return template.render(
        today=data.daily_nakshatra_prediction,
        tomorrow=data.daily_nakshatra_prediction_next,
        yesterday=data.daily_nakshatra_prediction_previous,
        locale=locale,
        lang=lang,
    )
