from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, translate_keys, make_env

if TYPE_CHECKING:
    from models import KundliData

NAKSHATRA_KEYS_HI: dict[str, str] = {
    "physical": "शारीरिक गुण",
    "character": "चरित्र",
    "education": "शिक्षा",
    "family": "परिवार",
    "health": "स्वास्थ्य",
}

ASCENDANT_KEYS_HI: dict[str, str] = {
    "asc_report": "लग्न रिपोर्ट",
    "ascendant": "लग्न",
    "report": "विवरण",
}


def render_life_reports(data: KundliData, lang: str = "en") -> str | None:
    if not data.general_ascendant_report and not data.general_nakshatra_report:
        return None

    ascendant_report = data.general_ascendant_report
    nakshatra_report = data.general_nakshatra_report
    if lang == "hi":
        ascendant_report = translate_keys(ascendant_report, ASCENDANT_KEYS_HI)
        nakshatra_report = translate_keys(nakshatra_report, NAKSHATRA_KEYS_HI)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("life_reports.html")
    return template.render(
        ascendant_report=ascendant_report,
        nakshatra_report=nakshatra_report,
        locale=locale,
        lang=lang,
    )
