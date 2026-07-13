"""Curated, chart-aware remedy bundles for life-area sections.

Given the significator planets for a life area (e.g. career -> 10th lord, Sun,
Saturn), assemble a tasteful remedy set per planet from the shared remedy bank
(`remedy_constants`): mantra, gemstone, charity/daan, and a behavioural practice.
Significators that are weak/afflicted (debilitated, retrograde, or in a dusthana
house) are flagged as "priority" so the template can surface them first — this is
the light personalization that keeps the remedies relevant to the actual chart,
without any AI cost.

Only mainstream, respectful remedies are used (mantra, gemstone, daan, lifestyle) —
no extreme folk practices.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sections.dignity import DEBILITATION, EXALTATION, MOOLATRIKONA, OWN_SIGNS
from sections.remedy_constants import (
    BEHAVIORAL_REMEDIES,
    BEHAVIORAL_REMEDIES_HI,
    PLANET_DONATIONS,
    PLANET_DONATIONS_HI,
    PLANET_MANTRAS,
    PLANET_MANTRAS_DEVANAGARI,
    PLANET_MANTRAS_MEANING,
    PLANET_TO_GEMSTONE,
)

if TYPE_CHECKING:
    from models import KundliData

DUSTHANA_HOUSES = {6, 8, 12}

# Planets that have a remedy bundle in remedy_constants.
_REMEDIABLE = set(PLANET_MANTRAS.keys())


def _dignity(name: str, sign: str) -> str:
    if EXALTATION.get(name) == sign:
        return "Exalted"
    if DEBILITATION.get(name) == sign:
        return "Debilitated"
    if MOOLATRIKONA.get(name) == sign:
        return "Moolatrikona"
    if sign in OWN_SIGNS.get(name, []):
        return "Own Sign"
    return "Normal"


def _weakness(name: str, sign: str, house: int, is_retro: str) -> list[str]:
    reasons: list[str] = []
    if DEBILITATION.get(name) == sign:
        reasons.append("Debilitated")
    if str(is_retro).lower() in ("true", "yes", "1"):
        reasons.append("Retrograde")
    if house in DUSTHANA_HOUSES:
        reasons.append(f"House {house}")
    return reasons


def build_area_remedies(
    data: KundliData,
    significators: list[str],
    lang: str = "en",
) -> list[dict]:
    """Return a list of remedy bundles for the given significator planets.

    Duplicates and planets with no remedy bundle (e.g. Ascendant, empty lord) are
    skipped. Weak/afflicted significators are sorted first and flagged.
    """
    planets_by_name = {p.name: p for p in (data.planets or [])}

    bundles: list[dict] = []
    seen: set[str] = set()
    for name in significators:
        if not name or name in seen or name not in _REMEDIABLE:
            continue
        seen.add(name)

        p = planets_by_name.get(name)
        sign = getattr(p, "sign", "") if p else ""
        house = getattr(p, "house", 0) if p else 0
        is_retro = getattr(p, "isRetro", "false") if p else "false"

        reasons = _weakness(name, sign, house, is_retro) if p else []
        gem = PLANET_TO_GEMSTONE.get(name, {})
        donation = (PLANET_DONATIONS_HI if lang == "hi" else PLANET_DONATIONS).get(name, {})

        bundles.append({
            "planet": name,
            "sign": sign,
            "house": house,
            "dignity": _dignity(name, sign) if p else "",
            "priority": bool(reasons),
            "reasons": reasons,
            "mantra": PLANET_MANTRAS_DEVANAGARI.get(name, "") if lang == "hi"
                      else PLANET_MANTRAS.get(name, {}).get("mantra", ""),
            "mantra_meaning": PLANET_MANTRAS_MEANING.get(name, ""),
            "gemstone": gem.get("hindi", "") if lang == "hi" else gem.get("name", ""),
            "donation_item": donation.get("item", ""),
            "donation_day": donation.get("day", ""),
            "behavioral": (BEHAVIORAL_REMEDIES_HI if lang == "hi" else BEHAVIORAL_REMEDIES).get(name, ""),
        })

    # Surface afflicted significators first; preserve input order otherwise.
    bundles.sort(key=lambda b: not b["priority"])
    return bundles
