from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, translate_keys, make_env

if TYPE_CHECKING:
    from models import KundliData

DOSHA_KEYS_HI: dict[str, str] = {
    # Simple Manglik (real API keys)
    "is_present": "उपस्थित",
    "is_cancelled": "निरस्त",
    "msg": "संदेश",
    # Simple Manglik (demo/alternate keys)
    "is_manglik": "मांगलिक है",
    "is_manglik_pitr": "पितृ मांगलिक",
    "is_manglik_chandra": "चन्द्र मांगलिक",
    "percentage_manglik_present": "मांगलिक प्रतिशत",
    "manglik_report": "मांगलिक रिपोर्ट",
    # Full Manglik
    "manglik_present_rule": "मांगलिक उपस्थित नियम",
    "manglik_cancel_rule": "मांगलिक निरस्त नियम",
    "percentage_manglik_after_cancellation": "निरस्तीकरण के बाद प्रतिशत",
    "based_on_aspen": "लग्न के आधार पर",
    "based_on_house": "भाव के आधार पर",
    # Kalsarpa
    "present": "उपस्थित",
    "type": "प्रकार",
    "one_directional": "एकदिशीय",
    "report": "विवरण",
    # Sadhesati Status
    "is_undergoing_sadhesati": "साढ़ेसाती चल रही है",
    "sadhesati_status": "साढ़ेसाती स्थिति",
    "is_undergoing_small_panoti": "छोटी पनौती चल रही है",
    "small_panoti_status": "छोटी पनौती स्थिति",
    "consideration_status": "विचार स्थिति",
    "is_undergoing": "चल रहा है",
    # Sadhesati Life
    "sadhesati_details": "साढ़ेसाती विवरण",
    "start": "आरंभ",
    "end": "समाप्ति",
    "phase": "चरण",
    "saturn_sign": "शनि राशि",
    "start_date": "आरंभ तिथि",
    "end_date": "समाप्ति तिथि",
    "sign": "राशि",
    # Pitra Dosha
    "is_pitra_dosha_present": "पितृ दोष उपस्थित है",
    "pitra_dosha_report": "पितृ दोष रिपोर्ट",
    "remedies": "उपाय",
}


def render_dosha(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.simple_manglik
        and not data.manglik
        and not data.kalsarpa_details
        and not data.sadhesati_current_status
        and not data.sadhesati_life_details
        and not data.pitra_dosha_report
    ):
        return None

    simple_manglik = data.simple_manglik
    manglik = data.manglik
    kalsarpa = data.kalsarpa_details
    sadhesati_status = data.sadhesati_current_status
    sadhesati_life = data.sadhesati_life_details
    pitra_dosha = data.pitra_dosha_report

    if lang == "hi":
        simple_manglik = translate_keys(simple_manglik, DOSHA_KEYS_HI)
        manglik = translate_keys(manglik, DOSHA_KEYS_HI)
        kalsarpa = translate_keys(kalsarpa, DOSHA_KEYS_HI)
        sadhesati_status = translate_keys(sadhesati_status, DOSHA_KEYS_HI)
        sadhesati_life = translate_keys(sadhesati_life, DOSHA_KEYS_HI)
        pitra_dosha = translate_keys(pitra_dosha, DOSHA_KEYS_HI)

    locale = LOCALES.get(lang, LOCALES["en"])
    env = make_env()
    template = env.get_template("dosha.html")
    return template.render(
        simple_manglik=simple_manglik,
        manglik=manglik,
        kalsarpa=kalsarpa,
        sadhesati_status=sadhesati_status,
        sadhesati_life=sadhesati_life,
        pitra_dosha=pitra_dosha,
        locale=locale,
        lang=lang,
    )
