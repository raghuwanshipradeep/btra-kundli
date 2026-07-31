"""Ashtakavarga: the real 8x12 Bhinnashtakavarga matrix, Sarvashtakavarga, and shodhana.

Three of the reference report's ten defects live in this one topic, so it is worth being
explicit about what this module does differently.

**Defect #4** — the report printed "Sarva total: 337 / 337 maximum... above 337 indicates
strong" and elsewhere "337 / 365". The SAV grand total is 337 for *every chart that has ever
been cast*: it is the sum of the benefic-point tables below, a property of the technique, not
of the native. There is no maximum to be near and nothing to be above. The only valid claim
is an intra-chart comparison against the 28.08 mean.

**Defect #5** — all seven BAV totals were labelled "exceptionally strong". Those totals
(Sun 48, Moon 49, Mars 39, Mercury 54, Jupiter 56, Venus 52, Saturn 39) are chart-invariant
constants too. What varies, and what the report must publish, is the house-level
distribution.

**Why computed here rather than read from the API.** ``/planet_ashtak/{planet}`` and
``/sarvashtak`` do return bindu data, but the matrix is a pure function of eight natal signs
and a fixed table — so deriving it locally makes the 337 invariant provable in a unit test
rather than something we hope the upstream got right, and it removes eight API calls. The
API's positions remain the input; only the arithmetic moved in-house.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.astro.enums import SAPTA_GRAHA, SAV_TOTAL, Graha, Rashi, TransitGrade

# --- The classical benefic-point tables --------------------------------------------------
# For the Ashtakavarga *of* planet P, each of the eight contributors C donates a bindu to the
# houses listed, counted from the sign C itself occupies. Lagna is the eighth contributor.
#
# These 56 lists are the irreducible data of the technique. The per-planet totals they imply
# (48/49/39/54/56/52/39, summing to 337) are asserted in the tests rather than written down
# anywhere here — that is what makes a typo in a list a test failure instead of a silently
# wrong chart.

_LAGNA = "Lagna"
_Contributor = Graha | str
CONTRIBUTORS: tuple[_Contributor, ...] = (*SAPTA_GRAHA, _LAGNA)

BENEFIC_PLACES: dict[Graha, dict[_Contributor, tuple[int, ...]]] = {
    Graha.SUN: {
        Graha.SUN: (1, 2, 4, 7, 8, 9, 10, 11),
        Graha.MOON: (3, 6, 10, 11),
        Graha.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Graha.MERCURY: (3, 5, 6, 9, 10, 11, 12),
        Graha.JUPITER: (5, 6, 9, 11),
        Graha.VENUS: (6, 7, 12),
        Graha.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        _LAGNA: (3, 4, 6, 10, 11, 12),
    },
    Graha.MOON: {
        Graha.SUN: (3, 6, 7, 8, 10, 11),
        Graha.MOON: (1, 3, 6, 7, 10, 11),
        Graha.MARS: (2, 3, 5, 6, 9, 10, 11),
        Graha.MERCURY: (1, 3, 4, 5, 7, 8, 10, 11),
        Graha.JUPITER: (1, 4, 7, 8, 10, 11, 12),
        Graha.VENUS: (3, 4, 5, 7, 9, 10, 11),
        Graha.SATURN: (3, 5, 6, 11),
        _LAGNA: (3, 6, 10, 11),
    },
    Graha.MARS: {
        Graha.SUN: (3, 5, 6, 10, 11),
        Graha.MOON: (3, 6, 11),
        Graha.MARS: (1, 2, 4, 7, 8, 10, 11),
        Graha.MERCURY: (3, 5, 6, 11),
        Graha.JUPITER: (6, 10, 11, 12),
        Graha.VENUS: (6, 8, 11, 12),
        Graha.SATURN: (1, 4, 7, 8, 9, 10, 11),
        _LAGNA: (1, 3, 6, 10, 11),
    },
    Graha.MERCURY: {
        Graha.SUN: (5, 6, 9, 11, 12),
        Graha.MOON: (2, 4, 6, 8, 10, 11),
        Graha.MARS: (1, 2, 4, 7, 8, 9, 10, 11),
        Graha.MERCURY: (1, 3, 5, 6, 9, 10, 11, 12),
        Graha.JUPITER: (6, 8, 11, 12),
        Graha.VENUS: (1, 2, 3, 4, 5, 8, 9, 11),
        Graha.SATURN: (1, 2, 4, 7, 8, 9, 10, 11),
        _LAGNA: (1, 2, 4, 6, 8, 10, 11),
    },
    Graha.JUPITER: {
        Graha.SUN: (1, 2, 3, 4, 7, 8, 9, 10, 11),
        Graha.MOON: (2, 5, 7, 9, 11),
        Graha.MARS: (1, 2, 4, 7, 8, 10, 11),
        Graha.MERCURY: (1, 2, 4, 5, 6, 9, 10, 11),
        Graha.JUPITER: (1, 2, 3, 4, 7, 8, 10, 11),
        Graha.VENUS: (2, 5, 6, 9, 10, 11),
        Graha.SATURN: (3, 5, 6, 12),
        _LAGNA: (1, 2, 4, 5, 6, 7, 9, 10, 11),
    },
    Graha.VENUS: {
        Graha.SUN: (8, 11, 12),
        Graha.MOON: (1, 2, 3, 4, 5, 8, 9, 11, 12),
        Graha.MARS: (3, 4, 6, 9, 11, 12),
        Graha.MERCURY: (3, 5, 6, 9, 11),
        Graha.JUPITER: (5, 8, 9, 10, 11),
        Graha.VENUS: (1, 2, 3, 4, 5, 8, 9, 10, 11),
        Graha.SATURN: (3, 4, 5, 8, 9, 10, 11),
        _LAGNA: (1, 2, 3, 4, 5, 8, 9, 11),
    },
    Graha.SATURN: {
        Graha.SUN: (1, 2, 4, 7, 8, 10, 11),
        Graha.MOON: (3, 6, 11),
        Graha.MARS: (3, 5, 6, 10, 11, 12),
        Graha.MERCURY: (6, 8, 9, 10, 11, 12),
        Graha.JUPITER: (5, 6, 11, 12),
        Graha.VENUS: (6, 11, 12),
        Graha.SATURN: (3, 5, 6, 11),
        _LAGNA: (1, 3, 4, 6, 10, 11),
    },
}


def _house_offset(from_sign: Rashi, to_sign: Rashi) -> int:
    """Whole-sign house number of ``to_sign`` counted from ``from_sign`` — 1 through 12."""
    return ((to_sign.value - from_sign.value) % 12) + 1


@dataclass(frozen=True, slots=True)
class BhinnaAshtakavarga:
    """One planet's row: bindus in each of the 12 signs, plus who contributed them.

    ``bindus`` is keyed by Rashi so a caller cannot accidentally index it 0-based.
    ``prastara`` is the full spread — contributor x sign — which is what §18 publishes to
    prove the matrix is chart-specific rather than a constant.
    """

    graha: Graha
    bindus: dict[Rashi, int]
    prastara: dict[_Contributor, dict[Rashi, int]]

    @property
    def total(self) -> int:
        """The chart-invariant per-planet total. Never present this as a strength score."""
        return sum(self.bindus.values())

    def in_sign(self, sign: Rashi) -> int:
        return self.bindus[sign]


@dataclass(frozen=True, slots=True)
class AshtakavargaData:
    """Everything the report knows about Ashtakavarga. Assembled once, read many times."""

    bav: dict[Graha, BhinnaAshtakavarga]
    sav: dict[Rashi, int]
    reduced: dict[Graha, dict[Rashi, int]]     # after Trikona + Ekadhipatya shodhana
    shodhya_pinda: dict[Graha, int]
    lagna_sign: Rashi
    house_of_sign: dict[Rashi, int] = field(default_factory=dict)

    @property
    def sav_total(self) -> int:
        return sum(self.sav.values())

    def sav_by_house(self) -> dict[int, int]:
        """SAV keyed by house number rather than sign — how §18 and §11 present it."""
        return {self.house_of_sign[sign]: value for sign, value in self.sav.items()}

    def strongest_houses(self, count: int = 3) -> list[tuple[int, int]]:
        """(house, bindus) for the best-supported houses, descending."""
        pairs = sorted(self.sav_by_house().items(), key=lambda kv: (-kv[1], kv[0]))
        return pairs[:count]

    def weakest_houses(self, count: int = 3) -> list[tuple[int, int]]:
        pairs = sorted(self.sav_by_house().items(), key=lambda kv: (kv[1], kv[0]))
        return pairs[:count]

    def transit_bindu(self, graha: Graha, sign: Rashi) -> int:
        """Bindus the transiting planet has in that sign — the input to the AV transit filter.

        Uses the unreduced BAV: shodhana exists to derive Shodhya Pinda for remedy weighting,
        not to grade transits. Nodes have no Ashtakavarga, so they return 0 and the transit
        section must grade them by house and dasha instead of pretending to a bindu count.
        """
        if graha not in self.bav:
            return 0
        return self.bav[graha].in_sign(sign)

    def transit_grade(self, graha: Graha, sign: Rashi) -> TransitGrade:
        return TransitGrade.from_bindus(self.transit_bindu(graha, sign))


def compute_bav(graha: Graha, positions: dict[_Contributor, Rashi]) -> BhinnaAshtakavarga:
    """Build one planet's Bhinnashtakavarga from the eight contributor signs.

    ``positions`` must contain all seven grahas plus ``"Lagna"``. A missing contributor is a
    programming error rather than a degradation case: an eight-row matrix with seven rows
    filled would look plausible and be wrong, which is precisely the failure mode this
    module exists to close.
    """
    table = BENEFIC_PLACES[graha]
    missing = [c for c in CONTRIBUTORS if c not in positions]
    if missing:
        raise ValueError(f"Ashtakavarga needs all 8 contributors; missing {missing}")

    prastara: dict[_Contributor, dict[Rashi, int]] = {}
    bindus: dict[Rashi, int] = {sign: 0 for sign in Rashi}
    for contributor in CONTRIBUTORS:
        benefic_houses = table[contributor]
        from_sign = positions[contributor]
        row: dict[Rashi, int] = {}
        for sign in Rashi:
            point = 1 if _house_offset(from_sign, sign) in benefic_houses else 0
            row[sign] = point
            bindus[sign] += point
        prastara[contributor] = row
    return BhinnaAshtakavarga(graha=graha, bindus=bindus, prastara=prastara)


# --- Shodhana ---------------------------------------------------------------------------

# The four trines. Trikona Shodhana operates within each.
TRINES: tuple[tuple[Rashi, Rashi, Rashi], ...] = (
    (Rashi.ARIES, Rashi.LEO, Rashi.SAGITTARIUS),
    (Rashi.TAURUS, Rashi.VIRGO, Rashi.CAPRICORN),
    (Rashi.GEMINI, Rashi.LIBRA, Rashi.AQUARIUS),
    (Rashi.CANCER, Rashi.SCORPIO, Rashi.PISCES),
)

# Sign pairs sharing a lord. Cancer (Moon) and Leo (Sun) have single lords and are excluded,
# which is why this tuple has five entries and not six.
EKADHIPATYA_PAIRS: tuple[tuple[Rashi, Rashi], ...] = (
    (Rashi.ARIES, Rashi.SCORPIO),          # Mars
    (Rashi.TAURUS, Rashi.LIBRA),           # Venus
    (Rashi.GEMINI, Rashi.VIRGO),           # Mercury
    (Rashi.SAGITTARIUS, Rashi.PISCES),     # Jupiter
    (Rashi.CAPRICORN, Rashi.AQUARIUS),     # Saturn
)


def trikona_shodhana(bindus: dict[Rashi, int]) -> dict[Rashi, int]:
    """Reduction by trines: within each trine, if all three signs hold bindus, subtract the
    smallest from all three. A zero anywhere in the trine cancels the reduction for it."""
    result = dict(bindus)
    for trine in TRINES:
        values = [result[sign] for sign in trine]
        if min(values) > 0:
            floor = min(values)
            for sign in trine:
                result[sign] -= floor
    return result


def ekadhipatya_shodhana(
    bindus: dict[Rashi, int],
    occupied: frozenset[Rashi],
) -> dict[Rashi, int]:
    """Reduction by same-lord sign pairs.

    The classical rules are stated inconsistently across texts, so the convention this
    project applies is spelled out rather than implied:

    * both signs occupied by a graha -> no reduction
    * neither occupied -> equal values become 0 for both; otherwise both take the lesser
    * one occupied -> the *unoccupied* sign is reduced: to 0 when its count is <= the
      occupied sign's, and down to the occupied sign's count when it is greater

    Because of that ambiguity, Shodhya Pinda derived from this is used only for *relative*
    remedy weighting (which planet needs support most), never printed as an absolute score
    the customer might compare against another astrologer's number.
    """
    result = dict(bindus)
    for first, second in EKADHIPATYA_PAIRS:
        first_occupied = first in occupied
        second_occupied = second in occupied
        if first_occupied and second_occupied:
            continue
        if not first_occupied and not second_occupied:
            if result[first] == result[second]:
                result[first] = result[second] = 0
            else:
                floor = min(result[first], result[second])
                result[first] = result[second] = floor
            continue
        # Exactly one is occupied.
        empty, full = (second, first) if first_occupied else (first, second)
        result[empty] = 0 if result[empty] <= result[full] else result[full]
    return result


# Multipliers for Shodhya Pinda. Rashi Pinda weights each sign; Graha Pinda weights the
# sign each planet occupies.
RASHI_MULTIPLIER: dict[Rashi, int] = {
    Rashi.ARIES: 7, Rashi.TAURUS: 10, Rashi.GEMINI: 8, Rashi.CANCER: 4,
    Rashi.LEO: 10, Rashi.VIRGO: 5, Rashi.LIBRA: 7, Rashi.SCORPIO: 8,
    Rashi.SAGITTARIUS: 9, Rashi.CAPRICORN: 5, Rashi.AQUARIUS: 11, Rashi.PISCES: 12,
}

GRAHA_MULTIPLIER: dict[Graha, int] = {
    Graha.SUN: 5, Graha.MOON: 5, Graha.MARS: 8, Graha.MERCURY: 5,
    Graha.JUPITER: 10, Graha.VENUS: 7, Graha.SATURN: 5,
}


def shodhya_pinda(
    reduced: dict[Rashi, int],
    positions: dict[_Contributor, Rashi],
) -> int:
    """Rashi Pinda + Graha Pinda over the post-shodhana bindus."""
    rashi_pinda = sum(reduced[sign] * RASHI_MULTIPLIER[sign] for sign in Rashi)
    graha_pinda = sum(
        reduced[positions[graha]] * GRAHA_MULTIPLIER[graha]
        for graha in SAPTA_GRAHA
        if graha in positions
    )
    return rashi_pinda + graha_pinda


def compute_ashtakavarga(
    planet_signs: dict[Graha, Rashi],
    lagna_sign: Rashi,
) -> AshtakavargaData:
    """The single entry point. Builds every BAV row, the SAV, shodhana, and Shodhya Pinda.

    ``planet_signs`` needs the seven grahas; Rahu and Ketu are not contributors and are not
    given an Ashtakavarga, by classical convention.
    """
    missing = [g for g in SAPTA_GRAHA if g not in planet_signs]
    if missing:
        raise ValueError(f"Ashtakavarga needs all seven grahas; missing {missing}")

    positions: dict[_Contributor, Rashi] = {g: planet_signs[g] for g in SAPTA_GRAHA}
    positions[_LAGNA] = lagna_sign
    occupied = frozenset(planet_signs[g] for g in SAPTA_GRAHA)

    bav = {graha: compute_bav(graha, positions) for graha in SAPTA_GRAHA}

    # SAV is the column sum across the seven planetary rows. Lagna is a contributor to each
    # row, not a row of its own, so it is not added again here — that double count is how a
    # SAV total drifts off 337.
    sav = {sign: sum(bav[graha].bindus[sign] for graha in SAPTA_GRAHA) for sign in Rashi}

    reduced: dict[Graha, dict[Rashi, int]] = {}
    pinda: dict[Graha, int] = {}
    for graha in SAPTA_GRAHA:
        after_trikona = trikona_shodhana(bav[graha].bindus)
        after_both = ekadhipatya_shodhana(after_trikona, occupied)
        reduced[graha] = after_both
        pinda[graha] = shodhya_pinda(after_both, positions)

    house_of_sign = {sign: _house_offset(lagna_sign, sign) for sign in Rashi}

    return AshtakavargaData(
        bav=bav,
        sav=sav,
        reduced=reduced,
        shodhya_pinda=pinda,
        lagna_sign=lagna_sign,
        house_of_sign=house_of_sign,
    )


def sav_verdict(bindus: int) -> str:
    """The only defensible framing of a single SAV figure.

    Compares against the 28.08 intra-chart mean. Deliberately returns a key, not prose, so
    the wording lives in one template and cannot drift between sections.
    """
    from app.astro.enums import SAV_EFFORT_THRESHOLD, SAV_SUPPORTED_THRESHOLD

    if bindus >= SAV_SUPPORTED_THRESHOLD:
        return "supported"
    if bindus <= SAV_EFFORT_THRESHOLD:
        return "needs_effort"
    return "average"


assert SAV_TOTAL == 337, "The SAV invariant is 337; enums.SAV_TOTAL disagrees"
