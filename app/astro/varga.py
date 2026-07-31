"""Divisional charts: Vargottama and Vimshopaka Bala from the fetched ``horo_charts``.

``api_client`` already fetches 17 divisional charts. Each comes back as sign-level placements
— which planet sits in which sign of that varga, with no degrees. That is exactly what the
two deliverables here need, so this module adapts rather than recomputes:

- ``is_vargottama`` — the same sign in D1 and D9.
- ``vimshopaka_bala`` — the Shodashvarga weighted score out of 20.

**Sign-level dignity, deliberately.** ``dignity.dignity_of()`` splits Moolatrikona from
exaltation by degree, because in the natal chart the degree is known. A varga sign has no
meaningful degree — it *is* the unit of the division — so ``varga_dignity()`` judges at sign
level and Moolatrikona does not arise. Using the natal degree inside a varga would be a
category error that quietly inflates every score.

**Degradation is reported, never absorbed.** A divisional chart the API failed to return
reduces the divisor and is listed in ``VargaSet.missing``. Scoring a missing chart as zero
would make a planet look weak because our network call failed, which is the worst kind of
wrong: plausible.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.astro.dignity import (
    DEBILITATION_SIGN,
    EXALTATION_SIGN,
    OWN_SIGNS,
    compound_relation,
)
from app.astro.enums import Dignity, Graha, Rashi
from app.astro.normalise import is_ascendant, try_resolve_graha, try_resolve_rashi

logger = logging.getLogger(__name__)

# The sixteen Shodashvarga divisions and their Vimshopaka weights. The weights sum to exactly
# 20 — that is the whole point of the scheme, and the assertion below is what keeps a future
# edit from quietly breaking the denominator.
#
# Classical sources disagree at the margin (some give Drekkana 1.5 and Akshavedamsa 1.0,
# which sums to 20.5). This project uses the set that sums to 20 so the published figure is
# genuinely "out of 20" rather than out of something else rounded.
VIMSHOPAKA_WEIGHTS: dict[str, float] = {
    "D1": 3.5,    # Rashi — the body itself
    "D2": 1.0,    # Hora — wealth
    "D3": 1.0,    # Drekkana — siblings, courage
    "D4": 0.5,    # Chaturthamsa — fortune, property
    "D7": 0.5,    # Saptamsa — children
    "D9": 3.0,    # Navamsa — the spouse and the inner strength of every planet
    "D10": 0.5,   # Dasamsa — career
    "D12": 0.5,   # Dwadasamsa — parents
    "D16": 2.0,   # Shodasamsa — vehicles, comforts
    "D20": 0.5,   # Vimsamsa — spiritual practice
    "D24": 0.5,   # Chaturvimsamsa — learning
    "D27": 0.5,   # Bhamsa — strengths and weaknesses
    "D30": 1.0,   # Trimsamsa — misfortune
    "D40": 0.5,   # Khavedamsa — maternal legacy
    "D45": 0.5,   # Akshavedamsa — paternal legacy
    "D60": 4.0,   # Shastiamsa — the finest division, and the heaviest weight
}

VIMSHOPAKA_TOTAL = 20.0
assert abs(sum(VIMSHOPAKA_WEIGHTS.values()) - VIMSHOPAKA_TOTAL) < 1e-9, (
    "Vimshopaka weights must sum to 20"
)

# D5 and D8 are fetched by api_client for the divisional-chart grid but are not part of
# Shodashvarga, so they are displayed and not scored.
NON_SHODASHVARGA = ("D5", "D8")

#: The share of a varga's weight a planet earns at each dignity.
#:
#: The classical texts describe Vimshopaka in words ("full in own sign, half in a friend's")
#: without a single agreed fraction table. Rather than adopt one source silently, this
#: project uses an evenly-spaced scale across the nine dignities — declared here so an
#: astrologer reviewing the report can agree or disagree with it explicitly, the same way
#: ``dignity.deeptadi_avastha`` declares its precedence.
DIGNITY_FACTOR: dict[Dignity, float] = {
    Dignity.EXALTED: 1.000,
    Dignity.MOOLATRIKONA: 0.875,
    Dignity.OWN: 0.750,
    Dignity.GREAT_FRIEND: 0.625,
    Dignity.FRIEND: 0.500,
    Dignity.NEUTRAL: 0.375,
    Dignity.ENEMY: 0.250,
    Dignity.GREAT_ENEMY: 0.125,
    Dignity.DEBILITATED: 0.000,
}


def varga_dignity(graha: Graha, sign: Rashi, signs: dict[Graha, Rashi]) -> Dignity:
    """Dignity of a planet in a divisional sign, judged without degrees.

    ``signs`` is every planet's sign *in that same varga*, because the temporal half of
    Panchadha Maitri is computed from where the planets sit relative to each other in the
    chart being judged — not from their natal positions.
    """
    if EXALTATION_SIGN.get(graha) == sign:
        return Dignity.EXALTED
    if DEBILITATION_SIGN.get(graha) == sign:
        return Dignity.DEBILITATED
    if sign in OWN_SIGNS.get(graha, ()):
        return Dignity.OWN
    if graha.is_node:
        return Dignity.NEUTRAL
    return compound_relation(graha, sign.lord, signs).to_dignity()


@dataclass(frozen=True, slots=True)
class VargaChart:
    """One divisional chart, reduced to what the scoring and the SVG renderer need."""

    varga: str
    signs: dict[Graha, Rashi]
    lagna_sign: Rashi | None

    def house_of(self, graha: Graha) -> int | None:
        """Whole-sign house within this varga, or None when the varga Lagna is unknown."""
        sign = self.signs.get(graha)
        if sign is None or self.lagna_sign is None:
            return None
        return ((sign.value - self.lagna_sign.value) % 12) + 1

    def occupants(self) -> dict[Rashi, tuple[Graha, ...]]:
        by_sign: dict[Rashi, list[Graha]] = {sign: [] for sign in Rashi}
        for graha in Graha:
            sign = self.signs.get(graha)
            if sign is not None:
                by_sign[sign].append(graha)
        return {sign: tuple(members) for sign, members in by_sign.items()}


@dataclass(frozen=True, slots=True)
class VargaSet:
    """Every divisional chart available for one native, plus the scores derived from them."""

    charts: dict[str, VargaChart]
    missing: tuple[str, ...] = field(default_factory=tuple)

    def has(self, varga: str) -> bool:
        return varga in self.charts

    def sign_in(self, varga: str, graha: Graha) -> Rashi | None:
        chart = self.charts.get(varga)
        return chart.signs.get(graha) if chart else None

    @property
    def scored_weight(self) -> float:
        """Total Vimshopaka weight actually available, out of 20.

        The report prints this next to the score: "14.5 / 20, computed from 13 of 16
        divisions" is honest; silently scaling and printing a bare number is not.
        """
        return sum(
            weight for varga, weight in VIMSHOPAKA_WEIGHTS.items() if varga in self.charts
        )

    def is_vargottama(self, graha: Graha) -> bool | None:
        """Same sign in D1 and D9. ``None`` means undeterminable, not False.

        Returning False for a missing D9 would let the report state "not vargottama" about a
        planet nobody checked — the shape of defect #6, one layer down.
        """
        natal = self.sign_in("D1", graha)
        navamsa = self.sign_in("D9", graha)
        if natal is None or navamsa is None:
            return None
        return natal == navamsa

    def dignities(self, graha: Graha) -> dict[str, Dignity]:
        """This planet's dignity in every available Shodashvarga division."""
        result: dict[str, Dignity] = {}
        for varga in VIMSHOPAKA_WEIGHTS:
            chart = self.charts.get(varga)
            if chart is None:
                continue
            sign = chart.signs.get(graha)
            if sign is None:
                continue
            result[varga] = varga_dignity(graha, sign, chart.signs)
        return result

    def vimshopaka_bala(self, graha: Graha) -> float:
        """Shodashvarga strength on a 0-20 scale.

        Rescaled by the weight actually covered, so a missing D60 lowers confidence rather
        than the planet's score. Returns 0.0 only when no division at all is available.
        """
        earned = 0.0
        covered = 0.0
        for varga, dignity in self.dignities(graha).items():
            weight = VIMSHOPAKA_WEIGHTS[varga]
            earned += weight * DIGNITY_FACTOR[dignity]
            covered += weight
        if covered <= 0.0:
            return 0.0
        return round(earned / covered * VIMSHOPAKA_TOTAL, 2)

    def vimshopaka_table(self) -> dict[Graha, float]:
        """Every graha's score in one pass — §9 renders this beside the Shodashvarga grid.

        Scoped to the grahas the natal chart actually has, so a planet missing from the API
        response is absent from the table rather than present with a 0.0 nobody computed.
        """
        natal = self.charts.get("D1")
        grahas = natal.signs if natal else {}
        return {graha: self.vimshopaka_bala(graha) for graha in Graha if graha in grahas}

    def vargottama_grahas(self) -> tuple[Graha, ...]:
        return tuple(g for g in Graha if self.is_vargottama(g) is True)


def parse_varga_chart(varga: str, rows) -> VargaChart | None:
    """Turn one ``/horo_chart/{id}`` response into a ``VargaChart``.

    Planet names arrive in the request's language, so every one goes through
    ``resolve_graha``. A row whose sign is out of range, or a chart with no recognisable
    planet in it, yields ``None`` — an empty chart scored as neutral would be indistinguishable
    from a real one.
    """
    signs: dict[Graha, Rashi] = {}
    lagna_sign: Rashi | None = None

    for row in rows or []:
        sign = try_resolve_rashi(getattr(row, "sign", 0) or getattr(row, "sign_name", ""))
        if sign is None:
            continue
        for name in getattr(row, "planet", None) or []:
            label = str(name).strip()
            if not label:
                continue
            if is_ascendant(label):
                lagna_sign = lagna_sign or sign
                continue
            graha = try_resolve_graha(label)
            if graha is None:
                logger.debug("varga %s: unrecognised body %r", varga, label)
                continue
            signs.setdefault(graha, sign)

    if not signs:
        return None
    return VargaChart(varga=varga, signs=signs, lagna_sign=lagna_sign)


def build_vargas(chart, horo_charts: dict | None = None) -> VargaSet:
    """Assemble the ``VargaSet`` for a native.

    D1 is always taken from the natal ``Chart`` rather than from ``horo_charts["D1"]``: the
    natal chart is derived from longitudes and is the single source of truth for the Rashi
    positions, and it carries a Lagna the divisional payload sometimes omits.

    ``chart`` is typed loosely for the same reason ``build_chart`` is — this module must not
    import ``app.astro.chart`` and create a cycle.
    """
    charts: dict[str, VargaChart] = {
        "D1": VargaChart(
            varga="D1",
            signs={graha: position.sign for graha, position in chart.planets.items()},
            lagna_sign=chart.lagna.sign,
        )
    }

    for varga, rows in (horo_charts or {}).items():
        if varga == "D1":
            continue
        parsed = parse_varga_chart(varga, rows)
        if parsed is not None:
            charts[varga] = parsed

    missing = tuple(v for v in VIMSHOPAKA_WEIGHTS if v not in charts)
    if missing:
        logger.warning(
            "varga: %d of 16 Shodashvarga divisions unavailable (%s); Vimshopaka is scaled "
            "to the %.1f weight actually covered",
            len(missing),
            ", ".join(missing),
            VIMSHOPAKA_TOTAL - sum(VIMSHOPAKA_WEIGHTS[v] for v in missing),
        )

    return VargaSet(charts=charts, missing=missing)
