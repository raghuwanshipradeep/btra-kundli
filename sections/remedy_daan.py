from __future__ import annotations

from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from sections import LOCALES
from sections.dignity import DEBILITATION, OWN_SIGNS, EXALTATION, MOOLATRIKONA
from sections.remedy_constants import PLANET_DONATIONS, BEHAVIORAL_REMEDIES

if TYPE_CHECKING:
    from models import KundliData

DUSTHANA_HOUSES = {6, 8, 12}

REASON_LABELS_HI = {
    "Debilitated": "नीच",
    "Retrograde": "वक्री",
    "House 6": "भाव 6",
    "House 8": "भाव 8",
    "House 12": "भाव 12",
    "Manglik Dosha": "मांगलिक दोष",
    "Sadhesati Active": "साढ़ेसाती सक्रिय",
    "Pitra Dosha": "पितृ दोष",
    "Kalsarpa Dosha": "कालसर्प दोष",
    "Functionally Malefic": "कार्यात्मक पापी",
    "Maraka (Killer)": "मारक",
    "Angarak Yoga": "अंगारक योग",
    "Shrapit Dosha": "शापित दोष",
    "Guru-Chandal Dosha": "गुरु-चांडाल दोष",
    "Grahan Dosha (Rahu)": "ग्रहण दोष (राहु)",
    "Grahan Dosha (Ketu)": "ग्रहण दोष (केतु)",
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


DIGNITY_LABELS_HI = {
    "Exalted": "उच्च",
    "Debilitated": "नीच",
    "Moolatrikona": "मूलत्रिकोण",
    "Own Sign": "स्वराशि",
    "Normal": "सामान्य",
}


def _is_weak(name: str, sign: str, house: int, is_retro: str) -> tuple[bool, str]:
    reasons = []
    if DEBILITATION.get(name) == sign:
        reasons.append("Debilitated")
    if str(is_retro).lower() in ("true", "yes", "1"):
        reasons.append("Retrograde")
    if house in DUSTHANA_HOUSES:
        reasons.append(f"House {house}")
    return bool(reasons), ", ".join(reasons)


def _build_dosha_afflictions(data: KundliData) -> dict[str, list[str]]:
    afflictions: dict[str, list[str]] = {}

    manglik = data.manglik or data.simple_manglik
    if manglik and manglik.get("is_manglik"):
        afflictions.setdefault("Mars", []).append("Manglik Dosha")

    if data.sadhesati_current_status and data.sadhesati_current_status.get("is_undergoing_sadhesati"):
        afflictions.setdefault("Saturn", []).append("Sadhesati Active")

    if data.pitra_dosha_report and data.pitra_dosha_report.get("is_pitra_dosha_present"):
        afflictions.setdefault("Sun", []).append("Pitra Dosha")
        afflictions.setdefault("Saturn", []).append("Pitra Dosha")

    if data.kalsarpa_details and data.kalsarpa_details.get("present"):
        afflictions.setdefault("Rahu", []).append("Kalsarpa Dosha")
        afflictions.setdefault("Ketu", []).append("Kalsarpa Dosha")

    if data.planet_nature:
        for planet in (data.planet_nature.BAD or []):
            afflictions.setdefault(planet, []).append("Functionally Malefic")
        for planet in (data.planet_nature.KILLER or []):
            afflictions.setdefault(planet, []).append("Maraka (Killer)")

    if data.planets:
        ph = {p.name: p.house for p in data.planets if p.name != "Ascendant"}
        if ph.get("Mars") is not None and ph.get("Mars") == ph.get("Rahu"):
            afflictions.setdefault("Mars", []).append("Angarak Yoga")
            afflictions.setdefault("Rahu", []).append("Angarak Yoga")
        if ph.get("Saturn") is not None and ph.get("Saturn") == ph.get("Rahu"):
            afflictions.setdefault("Saturn", []).append("Shrapit Dosha")
            afflictions.setdefault("Rahu", []).append("Shrapit Dosha")
        if ph.get("Jupiter") is not None and ph.get("Jupiter") == ph.get("Rahu"):
            afflictions.setdefault("Jupiter", []).append("Guru-Chandal Dosha")
            afflictions.setdefault("Rahu", []).append("Guru-Chandal Dosha")
        for lum in ("Sun", "Moon"):
            for node in ("Rahu", "Ketu"):
                if ph.get(lum) is not None and ph.get(lum) == ph.get(node):
                    afflictions.setdefault(lum, []).append(f"Grahan Dosha ({node})")

    return afflictions


def render_remedy_daan(data: KundliData, lang: str = "en") -> str | None:
    if not data.planets:
        return None

    dosha_map = _build_dosha_afflictions(data)
    weak_planets = []
    for p in data.planets:
        if p.name == "Ascendant" or p.name not in PLANET_DONATIONS:
            continue
        _, dignity_reason = _is_weak(p.name, p.sign, p.house, p.isRetro)
        dosha_reasons = dosha_map.get(p.name, [])

        all_reasons: list[str] = []
        if dignity_reason:
            all_reasons.extend(dignity_reason.split(", "))
        all_reasons.extend(dosha_reasons)

        seen: set[str] = set()
        unique_reasons: list[str] = []
        for r in all_reasons:
            if r not in seen:
                seen.add(r)
                unique_reasons.append(r)

        if not unique_reasons:
            continue

        if lang == "hi":
            unique_reasons = [REASON_LABELS_HI.get(r, r) for r in unique_reasons]

        donation = PLANET_DONATIONS[p.name]
        dignity = _get_dignity(p.name, p.sign)
        weak_planets.append({
            "name": p.name,
            "dignity": DIGNITY_LABELS_HI.get(dignity, dignity) if lang == "hi" else dignity,
            "reason": ", ".join(unique_reasons),
            "house": p.house,
            "sign": p.sign,
            "item": donation["item"],
            "day": donation["day"],
            "metal": donation["metal"],
            "behavioral": BEHAVIORAL_REMEDIES.get(p.name, ""),
        })

    locale = LOCALES.get(lang, LOCALES["en"])
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("remedy_daan.html")
    return template.render(
        weak_planets=weak_planets,
        narrative=data.narratives.get("daan_guidance", ""),
        locale=locale,
        lang=lang,
    )
