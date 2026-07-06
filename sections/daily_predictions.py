from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env

if TYPE_CHECKING:
    from models import KundliData


def _split_day(d: dict | None) -> tuple[dict, dict]:
    """Split a day's prediction into (summary scalars, narrative), unwrapping the nested
    `prediction` dict so each category flows as its own subheading + full-width paragraph."""
    summary: dict = {}
    narrative: dict = {}
    if not d:
        return summary, narrative
    for k, v in d.items():
        if k.endswith("_ms") or k.endswith("_id") or k == "planet_small":
            continue
        if isinstance(v, dict):      # the `prediction` sub-dict — unwrap its categories
            narrative.update(v)
        elif isinstance(v, list):
            narrative[k] = v
        else:
            summary[k] = v
    return summary, narrative


def render_daily_predictions(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.daily_nakshatra_prediction
        and not data.daily_nakshatra_prediction_next
        and not data.daily_nakshatra_prediction_previous
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    raw_days = [
        (locale.get("previous_prediction", "Yesterday"), data.daily_nakshatra_prediction_previous),
        (locale.get("today_prediction", "Today"), data.daily_nakshatra_prediction),
        (locale.get("next_prediction", "Tomorrow"), data.daily_nakshatra_prediction_next),
    ]

    days = []
    for title, raw in raw_days:
        if not raw:
            continue
        summary, narrative = _split_day(raw)
        days.append({"title": title, "summary": summary, "narrative": narrative})

    if not days:
        return None

    env = make_env()
    template = env.get_template("daily_predictions.html")
    return template.render(
        days=days,
        locale=locale,
        lang=lang,
    )
