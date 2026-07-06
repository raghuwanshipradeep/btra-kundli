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

# Keys whose values are long-form text / rules — rendered as flowing "life-report"
# paragraphs (label + text) rather than cramped table cells. Any nested dict/list is
# also treated as narrative.
DOSHA_NARRATIVE_KEYS = {
    "msg", "report", "manglik_report", "pitra_dosha_report",
    "manglik_present_rule", "manglik_cancel_rule", "remedies", "one_line",
}

# Explicit display order for the merged Manglik summary so status/percentage surface up top.
_MANGLIK_ORDER = [
    "is_present", "is_cancelled", "manglik_status", "percentage_manglik_present",
    "percentage_manglik_after_cancellation", "is_mars_manglik_cancelled",
    "manglik_report", "manglik_present_rule", "manglik_cancel_rule",
]


def _split_dosha(d: dict | None) -> tuple[dict, dict]:
    """Split a dosha dict into (summary scalars, narrative text/rules), preserving order."""
    summary: dict = {}
    narrative: dict = {}
    if not d:
        return summary, narrative
    for k, v in d.items():
        if k.endswith("_ms") or k.endswith("_id") or k == "planet_small":
            continue
        if k in DOSHA_NARRATIVE_KEYS or isinstance(v, (dict, list)):
            narrative[k] = v
        else:
            summary[k] = v
    return summary, narrative


def _merge_manglik(simple_manglik: dict | None, manglik: dict | None) -> dict:
    """Combine the short simple_manglik and detailed manglik into one ordered dict."""
    src: dict = {**(simple_manglik or {}), **(manglik or {})}
    merged = {k: src[k] for k in _MANGLIK_ORDER if src.get(k) not in (None, "")}
    # Fall back to the simple-manglik message only when no detailed report exists.
    if "manglik_report" not in merged and src.get("msg"):
        merged["msg"] = src["msg"]
    # Carry any remaining meaningful keys not covered above.
    for k, v in src.items():
        if k not in merged and k not in ("msg",) and v not in (None, ""):
            merged[k] = v
    return merged


def render_dosha(data: KundliData, lang: str = "en") -> str | None:
    if (
        not data.simple_manglik
        and not data.manglik
        and not data.kalsarpa_details
        and not data.sadhesati_current_status
        and not data.pitra_dosha_report
    ):
        return None

    locale = LOCALES.get(lang, LOCALES["en"])

    # (title, raw dosha dict) — Manglik is the merged simple + detailed view.
    raw_sections: list[tuple[str, dict | None]] = [
        (locale.get("manglik_title", "Manglik Analysis"),
         _merge_manglik(data.simple_manglik, data.manglik) or None),
        (locale.get("kalsarpa_title", "Kalsarpa Dosha"), data.kalsarpa_details),
        (locale.get("sadhesati_status_title", "Sadhesati Status"), data.sadhesati_current_status),
        (locale.get("pitra_dosha_title", "Pitra Dosha"), data.pitra_dosha_report),
    ]

    sections = []
    for title, raw in raw_sections:
        if not raw:
            continue
        summary, narrative = _split_dosha(raw)
        if lang == "hi":
            summary = translate_keys(summary, DOSHA_KEYS_HI)
            narrative = translate_keys(narrative, DOSHA_KEYS_HI)
        sections.append({"title": title, "summary": summary, "narrative": narrative})

    if not sections:
        return None

    env = make_env()
    template = env.get_template("dosha.html")
    return template.render(
        sections=sections,
        locale=locale,
        lang=lang,
    )
