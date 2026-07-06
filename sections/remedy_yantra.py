from __future__ import annotations

from typing import TYPE_CHECKING


from sections import LOCALES, make_env
from sections.dignity import DEBILITATION, OWN_SIGNS, EXALTATION, MOOLATRIKONA
from sections.remedy_constants import (
    PLANET_YANTRAS, YANTRA_DOS, YANTRA_DONTS,
    PLANET_YANTRAS_HI, YANTRA_DOS_HI, YANTRA_DONTS_HI,
)

if TYPE_CHECKING:
    from models import KundliData

DUSTHANA_HOUSES = {6, 8, 12}

DIGNITY_LABELS_HI = {
    "Exalted": "उच्च", "Debilitated": "नीच", "Moolatrikona": "मूलत्रिकोण",
    "Own Sign": "स्वराशि", "Normal": "सामान्य",
}

# Reason sentence per (reason key, language); {p} is the localized planet name.
REASON_TEMPLATES = {
    "en": {
        "weak": "{p} is debilitated in your chart — this yantra helps strengthen its energy",
        "afflicted": "{p} is afflicted in your chart — this yantra helps balance its influence",
        "strongest": "{p} is your strongest planet — this yantra amplifies its blessings",
    },
    "hi": {
        "weak": "{p} आपकी कुंडली में नीच है — यह यंत्र इसकी ऊर्जा को मजबूत करने में सहायक है",
        "afflicted": "{p} आपकी कुंडली में पीड़ित है — यह यंत्र इसके प्रभाव को संतुलित करने में सहायक है",
        "strongest": "{p} आपका सबसे मजबूत ग्रह है — यह यंत्र इसके आशीर्वाद को बढ़ाता है",
    },
}


def _get_dignity(name: str, sign: str) -> str:
    if EXALTATION.get(name) == sign:
        return "Exalted"
    if DEBILITATION.get(name) == sign:
        return "Debilitated"
    if MOOLATRIKONA.get(name) == sign:
        return "Moolatrikona"
    if sign in OWN_SIGNS.get(name, []):
        return "Own Sign"
    return "Normal"


def _planet_weakness_score(name: str, sign: str, house: int, is_retro: str) -> int:
    score = 0
    if DEBILITATION.get(name) == sign:
        score += 3
    if str(is_retro).lower() in ("true", "yes", "1"):
        score += 1
    if house in DUSTHANA_HOUSES:
        score += 2
    return score


def _planet_strength_score(name: str, sign: str) -> int:
    if EXALTATION.get(name) == sign:
        return 3
    if MOOLATRIKONA.get(name) == sign:
        return 2
    if sign in OWN_SIGNS.get(name, []):
        return 1
    return 0


def render_remedy_yantra(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    candidates = [p for p in data.planets if p.name != "Ascendant" and p.name in PLANET_YANTRAS]
    if not candidates:
        return None

    weakest = max(
        candidates,
        key=lambda p: _planet_weakness_score(p.name, p.sign, p.house, p.isRetro),
    )
    weakness = _planet_weakness_score(weakest.name, weakest.sign, weakest.house, weakest.isRetro)

    if weakness > 0:
        target = weakest
        dignity = _get_dignity(target.name, target.sign)
        reason = "weak" if dignity == "Debilitated" else "afflicted"
    else:
        target = max(candidates, key=lambda p: _planet_strength_score(p.name, p.sign))
        dignity = _get_dignity(target.name, target.sign)
        reason = "strongest"

    locale = LOCALES.get(lang, LOCALES["en"])

    yantra_map = PLANET_YANTRAS_HI if lang == "hi" else PLANET_YANTRAS
    yantra_name = yantra_map.get(target.name, "")

    planet_display = locale.get("planet_names", {}).get(target.name, target.name)
    dignity_label = DIGNITY_LABELS_HI.get(dignity, dignity) if lang == "hi" else dignity
    sign_label = locale.get("sign_names", {}).get(target.sign, target.sign)
    reason_text = REASON_TEMPLATES.get(lang, REASON_TEMPLATES["en"])[reason].format(p=planet_display)

    env = make_env()
    template = env.get_template("remedy_yantra.html")
    return template.render(
        yantra_name=yantra_name,
        planet=target.name,
        dignity=dignity_label,
        house=target.house,
        sign=sign_label,
        reason_text=reason_text,
        dos=YANTRA_DOS_HI if lang == "hi" else YANTRA_DOS,
        donts=YANTRA_DONTS_HI if lang == "hi" else YANTRA_DONTS,
        narrative=data.narratives.get("yantra_guidance", ""),
        locale=locale,
        lang=lang,
    )
