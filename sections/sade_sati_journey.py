from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES, translate_keys

if TYPE_CHECKING:
    from models import KundliData

SADHESATI_KEYS_HI: dict[str, str] = {
    "is_undergoing_sadhesati": "साढ़ेसाती चल रही है",
    "sadhesati_status": "साढ़ेसाती स्थिति",
    "is_undergoing_small_panoti": "छोटी पनौती चल रही है",
    "small_panoti_status": "छोटी पनौती स्थिति",
    "consideration_status": "विचार स्थिति",
    "is_undergoing": "चल रहा है",
    "remedies": "उपाय",
}


def _has_data(data: KundliData) -> bool:
    if data.sadhesati_life_details:
        if isinstance(data.sadhesati_life_details, list) and len(data.sadhesati_life_details) > 0:
            return True
        if isinstance(data.sadhesati_life_details, dict) and data.sadhesati_life_details:
            return True
    if data.sadhesati_current_status and isinstance(data.sadhesati_current_status, dict):
        return True
    return False


def render_sade_sati_journey(data: KundliData, lang: str = "en") -> str | None:
    if not _has_data(data):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    current_status = {}
    if data.sadhesati_current_status and isinstance(data.sadhesati_current_status, dict):
        current_status = data.sadhesati_current_status

    life_details = []
    if data.sadhesati_life_details:
        if isinstance(data.sadhesati_life_details, list):
            life_details = data.sadhesati_life_details
        elif isinstance(data.sadhesati_life_details, dict):
            inner = data.sadhesati_life_details.get("sadhesati_details")
            if isinstance(inner, list):
                life_details = inner
            else:
                life_details = [data.sadhesati_life_details]

    remedies_data = None
    if data.sadhesati_remedies:
        remedies_data = data.sadhesati_remedies

    rudraksha = None
    if data.rudraksha_suggestion:
        if isinstance(data.rudraksha_suggestion, dict):
            rudraksha = data.rudraksha_suggestion.get("rudraksha_suggestion", data.rudraksha_suggestion)
        else:
            rudraksha = data.rudraksha_suggestion

    saturn = None
    moon = None
    if data.planets:
        for p in data.planets:
            if p.name == "Saturn":
                saturn = p
            if p.name == "Moon":
                moon = p

    is_active = bool(current_status.get("is_undergoing_sadhesati"))

    if lang == "hi":
        current_status = translate_keys(current_status, SADHESATI_KEYS_HI) or {}

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("sade_sati_journey.html")
    return template.render(
        current_status=current_status,
        life_details=life_details,
        remedies_data=remedies_data,
        rudraksha=rudraksha,
        saturn=saturn,
        moon=moon,
        is_active=is_active,
        narratives=data.narratives,
        locale=locale,
        lang=lang,
    )
