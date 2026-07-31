"""Dignity, Panchadha Maitri, avastha, combustion, and the boundary weaknesses.

Why compound relationships and not the natural friendship table alone: the reference report
said "Mars sits in a neutral sign" using only the Naisargika table. Panchadha Maitri —
natural relationship combined with the temporal (Tatkalika) relationship produced by the
actual chart — is what a practising astrologer will check, and it can move a planet two
bands either way. Getting this right is the difference between a report an astrologer
resells and one they mock.

Everything here is a pure function of longitudes. Nothing reads the API's own dignity or
avastha strings, so a chart cannot end up with two different dignity claims (defect #2).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.astro.enums import (
    SAPTA_GRAHA,
    BaladiAvastha,
    Dignity,
    Graha,
    Rashi,
    Relation,
)
from app.astro.normalise import normalise_longitude, rashi_at

# --- Rulership and the exaltation axis ---------------------------------------------------

EXALTATION_SIGN: dict[Graha, Rashi] = {
    Graha.SUN: Rashi.ARIES,
    Graha.MOON: Rashi.TAURUS,
    Graha.MARS: Rashi.CAPRICORN,
    Graha.MERCURY: Rashi.VIRGO,
    Graha.JUPITER: Rashi.CANCER,
    Graha.VENUS: Rashi.PISCES,
    Graha.SATURN: Rashi.LIBRA,
    # The nodes have no classical rulership and no settled exaltation. This project follows
    # the Taurus/Scorpio convention, which is what the rest of the codebase already used and
    # what the birth-details page declares. Do not "correct" it in one module only.
    Graha.RAHU: Rashi.TAURUS,
    Graha.KETU: Rashi.SCORPIO,
}

DEBILITATION_SIGN: dict[Graha, Rashi] = {
    graha: Rashi(((sign.value + 5) % 12) + 1) for graha, sign in EXALTATION_SIGN.items()
}

# Deep exaltation degree within the exaltation sign. A planet within 1° of this is at
# maximum strength; §10 flags it so the narrative can say so without inventing a number.
EXACT_EXALTATION_DEGREE: dict[Graha, float] = {
    Graha.SUN: 10.0,
    Graha.MOON: 3.0,
    Graha.MARS: 28.0,
    Graha.MERCURY: 15.0,
    Graha.JUPITER: 5.0,
    Graha.VENUS: 27.0,
    Graha.SATURN: 20.0,
}

OWN_SIGNS: dict[Graha, tuple[Rashi, ...]] = {
    Graha.SUN: (Rashi.LEO,),
    Graha.MOON: (Rashi.CANCER,),
    Graha.MARS: (Rashi.ARIES, Rashi.SCORPIO),
    Graha.MERCURY: (Rashi.GEMINI, Rashi.VIRGO),
    Graha.JUPITER: (Rashi.SAGITTARIUS, Rashi.PISCES),
    Graha.VENUS: (Rashi.TAURUS, Rashi.LIBRA),
    Graha.SATURN: (Rashi.CAPRICORN, Rashi.AQUARIUS),
    # Co-lordship convention only; the nodes never displace the real sign lord in any rule.
    Graha.RAHU: (Rashi.AQUARIUS,),
    Graha.KETU: (Rashi.SCORPIO,),
}

# Moolatrikona is a DEGREE RANGE inside the sign, not the whole sign — a planet in its own
# sign outside this arc is "own", not Moolatrikona. Collapsing the two is a common bug and
# inflates the report.
MOOLATRIKONA: dict[Graha, tuple[Rashi, float, float]] = {
    Graha.SUN: (Rashi.LEO, 0.0, 20.0),
    Graha.MOON: (Rashi.TAURUS, 3.0, 30.0),
    Graha.MARS: (Rashi.ARIES, 0.0, 12.0),
    Graha.MERCURY: (Rashi.VIRGO, 15.0, 20.0),
    Graha.JUPITER: (Rashi.SAGITTARIUS, 0.0, 10.0),
    Graha.VENUS: (Rashi.LIBRA, 0.0, 15.0),
    Graha.SATURN: (Rashi.AQUARIUS, 0.0, 20.0),
}

# --- Naisargika (natural) friendship ----------------------------------------------------
# Classical Parashari table. Anything not listed as friend or enemy is neutral.

_NATURAL_FRIENDS: dict[Graha, frozenset[Graha]] = {
    Graha.SUN: frozenset({Graha.MOON, Graha.MARS, Graha.JUPITER}),
    Graha.MOON: frozenset({Graha.SUN, Graha.MERCURY}),
    Graha.MARS: frozenset({Graha.SUN, Graha.MOON, Graha.JUPITER}),
    Graha.MERCURY: frozenset({Graha.SUN, Graha.VENUS}),
    Graha.JUPITER: frozenset({Graha.SUN, Graha.MOON, Graha.MARS}),
    Graha.VENUS: frozenset({Graha.MERCURY, Graha.SATURN}),
    Graha.SATURN: frozenset({Graha.MERCURY, Graha.VENUS}),
}

_NATURAL_ENEMIES: dict[Graha, frozenset[Graha]] = {
    Graha.SUN: frozenset({Graha.VENUS, Graha.SATURN}),
    Graha.MOON: frozenset(),
    Graha.MARS: frozenset({Graha.MERCURY}),
    Graha.MERCURY: frozenset({Graha.MOON}),
    Graha.JUPITER: frozenset({Graha.MERCURY, Graha.VENUS}),
    Graha.VENUS: frozenset({Graha.SUN, Graha.MOON}),
    Graha.SATURN: frozenset({Graha.SUN, Graha.MOON, Graha.MARS}),
}

# Tatkalika: counted from a planet's own sign, occupants of the 2nd, 3rd, 4th, 10th, 11th
# and 12th are temporal friends; the same sign and the 5th-9th are temporal enemies.
_TEMPORAL_FRIEND_OFFSETS = frozenset({2, 3, 4, 10, 11, 12})


def natural_relation(subject: Graha, other: Graha) -> Relation:
    """Naisargika relationship of ``subject`` toward ``other``.

    Not symmetric — Venus counts the Sun an enemy while the Sun counts Venus an enemy too,
    but Mercury/Moon is asymmetric in some texts. This follows the table above as written.
    Nodes are outside the classical table and come back NEUTRAL.
    """
    if subject.is_node or other.is_node or subject == other:
        return Relation.NEUTRAL
    if other in _NATURAL_FRIENDS.get(subject, frozenset()):
        return Relation.FRIEND
    if other in _NATURAL_ENEMIES.get(subject, frozenset()):
        return Relation.ENEMY
    return Relation.NEUTRAL


def temporal_relation(subject_sign: Rashi, other_sign: Rashi) -> Relation:
    """Tatkalika relationship, from the two occupied signs. Only FRIEND or ENEMY exists."""
    offset = ((other_sign.value - subject_sign.value) % 12) + 1
    return Relation.FRIEND if offset in _TEMPORAL_FRIEND_OFFSETS else Relation.ENEMY


# Panchadha Maitri: natural × temporal → compound. This is the whole point of the module.
_COMPOUND: dict[tuple[Relation, Relation], Relation] = {
    (Relation.FRIEND, Relation.FRIEND): Relation.GREAT_FRIEND,
    (Relation.FRIEND, Relation.ENEMY): Relation.NEUTRAL,
    (Relation.NEUTRAL, Relation.FRIEND): Relation.FRIEND,
    (Relation.NEUTRAL, Relation.ENEMY): Relation.ENEMY,
    (Relation.ENEMY, Relation.FRIEND): Relation.NEUTRAL,
    (Relation.ENEMY, Relation.ENEMY): Relation.GREAT_ENEMY,
}


def compound_relation(
    subject: Graha,
    other: Graha,
    signs: dict[Graha, Rashi],
) -> Relation:
    """Panchadha Maitri relationship of ``subject`` toward ``other`` in this chart.

    ``signs`` maps every graha to the sign it occupies. Falls back to the natural relation
    when either planet's sign is unknown, so a partial chart degrades rather than crashes.
    """
    subject_sign = signs.get(subject)
    other_sign = signs.get(other)
    natural = natural_relation(subject, other)
    if subject_sign is None or other_sign is None:
        return natural
    temporal = temporal_relation(subject_sign, other_sign)
    return _COMPOUND[(natural, temporal)]


def dignity_of(
    graha: Graha,
    longitude: float,
    signs: dict[Graha, Rashi],
) -> Dignity:
    """The single dignity string for this planet in this chart.

    Precedence is exaltation, then debilitation, then Moolatrikona, then own sign, then the
    compound relationship with the sign lord. Every section renders this one value — see the
    ``dignity_consistency`` gate check.

    One refinement matters: for the Moon and Mercury the exaltation sign is *also* their
    Moolatrikona sign, and the classical division splits the sign by degree rather than
    handing the whole sign to exaltation. So the Moon is exalted in Taurus only up to 3°
    and Moolatrikona from 3° on; Mercury is exalted in Virgo to 15°, Moolatrikona 15-20°,
    own sign beyond. Treating the whole sign as exaltation would over-report strength — the
    exact narrative inflation the spec's Part 12 warns about.
    """
    sign, degree = rashi_at(longitude)

    if EXALTATION_SIGN.get(graha) == sign:
        moola = MOOLATRIKONA.get(graha)
        shares_sign_with_moolatrikona = moola is not None and moola[0] == sign
        if not shares_sign_with_moolatrikona or degree < moola[1]:
            return Dignity.EXALTED
        # else: fall through to the Moolatrikona / own-sign checks below
    if DEBILITATION_SIGN.get(graha) == sign:
        return Dignity.DEBILITATED

    moola = MOOLATRIKONA.get(graha)
    if moola is not None and moola[0] == sign and moola[1] <= degree < moola[2]:
        return Dignity.MOOLATRIKONA
    if sign in OWN_SIGNS.get(graha, ()):
        return Dignity.OWN

    # Nodes have no friendship table; anything not exalted/debilitated/own is neutral.
    if graha.is_node:
        return Dignity.NEUTRAL

    return compound_relation(graha, sign.lord, signs).to_dignity()


def exaltation_orb(graha: Graha, longitude: float) -> float | None:
    """Degrees from the deep-exaltation point, or None if not in the exaltation sign.

    Used to flag an exactly-exalted planet. Returns a magnitude, never a signed value —
    the narrative has no business inferring direction from it.
    """
    sign, degree = rashi_at(longitude)
    if EXALTATION_SIGN.get(graha) != sign:
        return None
    exact = EXACT_EXALTATION_DEGREE.get(graha)
    if exact is None:
        return None
    return abs(degree - exact)


# --- Avastha ----------------------------------------------------------------------------

_BALADI_ORDER: tuple[BaladiAvastha, ...] = (
    BaladiAvastha.BALA, BaladiAvastha.KUMARA, BaladiAvastha.YUVA,
    BaladiAvastha.VRIDDHA, BaladiAvastha.MRITA,
)


def baladi_avastha(longitude: float) -> BaladiAvastha:
    """Age-state from the degree within the sign — 6° per state.

    Runs forward in odd (masculine) signs and reversed in even ones, which is why a planet
    at 2° Taurus is Mrita (spent) while at 2° Aries it is Bala (infant).
    """
    sign, degree = rashi_at(longitude)
    band = min(int(degree // 6.0), 4)
    if not sign.is_odd:
        band = 4 - band
    return _BALADI_ORDER[band]


def deeptadi_avastha(
    graha: Graha,
    dignity: Dignity,
    is_combust: bool,
) -> str:
    """Deeptadi state, by the precedence this project has settled on.

    The classical nine states (Deepta, Swastha, Pramudita, Shanta, Deena, Dukhita, Vikala,
    Khala, Kopa) are defined inconsistently across texts, and two of them depend on
    planetary war which we do not compute. The convention here — declared rather than
    implied, so an astrologer reviewing the report can agree or disagree with it explicitly:

        combust        -> Kopa
        exalted        -> Deepta
        Moolatrikona   -> Swastha
        own sign       -> Swastha
        great friend   -> Pramudita
        friend         -> Shanta
        neutral        -> Deena
        enemy          -> Dukhita
        great enemy    -> Vikala
        debilitated    -> Khala
    """
    if is_combust:
        return "Kopa"
    return {
        Dignity.EXALTED: "Deepta",
        Dignity.MOOLATRIKONA: "Swastha",
        Dignity.OWN: "Swastha",
        Dignity.GREAT_FRIEND: "Pramudita",
        Dignity.FRIEND: "Shanta",
        Dignity.NEUTRAL: "Deena",
        Dignity.ENEMY: "Dukhita",
        Dignity.GREAT_ENEMY: "Vikala",
        Dignity.DEBILITATED: "Khala",
    }[dignity]


# --- Boundary weaknesses ----------------------------------------------------------------

# Gandanta is the 3°20' either side of the three water/fire junctions: Cancer-Leo,
# Scorpio-Sagittarius, Pisces-Aries. These are also the Ashlesha-Magha, Jyeshtha-Mula and
# Revati-Ashwini nakshatra joins — a planet there is at a structural seam.
GANDANTA_ARC = 3.0 + 20.0 / 60.0
_WATER_SIGNS = (Rashi.CANCER, Rashi.SCORPIO, Rashi.PISCES)
_FIRE_JUNCTION_SIGNS = (Rashi.LEO, Rashi.SAGITTARIUS, Rashi.ARIES)

RASHI_SANDHI_ARC = 1.0


def is_gandanta(longitude: float) -> bool:
    """True in the last 3°20' of a water sign or the first 3°20' of the following fire sign."""
    sign, degree = rashi_at(longitude)
    if sign in _WATER_SIGNS and degree >= 30.0 - GANDANTA_ARC:
        return True
    return sign in _FIRE_JUNCTION_SIGNS and degree <= GANDANTA_ARC


def is_rashi_sandhi(longitude: float) -> bool:
    """True within 1° of a sign boundary.

    The reference chart had Venus at 0.02° Gemini and the report treated it as a normal
    placement. A planet that has just entered a sign has barely acquired its character; §10
    flags this and every promise made through that planet must be hedged.
    """
    _, degree = rashi_at(longitude)
    return degree < RASHI_SANDHI_ARC or degree > 30.0 - RASHI_SANDHI_ARC


# --- Combustion -------------------------------------------------------------------------

# Classical orbs from the Sun, in degrees. Mercury and Venus take a tighter orb when
# retrograde, per the spec's Part 2.2 table.
_COMBUSTION_ORB: dict[Graha, float] = {
    Graha.MOON: 12.0,
    Graha.MARS: 17.0,
    Graha.MERCURY: 14.0,
    Graha.JUPITER: 11.0,
    Graha.VENUS: 10.0,
    Graha.SATURN: 15.0,
}

_COMBUSTION_ORB_RETRO: dict[Graha, float] = {
    Graha.MERCURY: 12.0,
    Graha.VENUS: 8.0,
}


@dataclass(frozen=True, slots=True)
class Combustion:
    is_combust: bool
    orb: float        # angular distance from the Sun, always 0-180
    limit: float      # the orb that applied, so the report can state the rule it used


def combustion(
    graha: Graha,
    longitude: float,
    sun_longitude: float,
    is_retrograde: bool = False,
) -> Combustion:
    """Whether a planet is combust, with the separation and the threshold applied.

    The Sun cannot be combust, and the nodes are shadow points with no disc to be
    overwhelmed — both return ``is_combust=False`` with their true separation, so a caller
    can still show the distance.
    """
    separation = abs(normalise_longitude(longitude) - normalise_longitude(sun_longitude))
    if separation > 180.0:
        separation = 360.0 - separation

    if graha is Graha.SUN or graha.is_node:
        return Combustion(False, separation, 0.0)

    limit = _COMBUSTION_ORB[graha]
    if is_retrograde and graha in _COMBUSTION_ORB_RETRO:
        limit = _COMBUSTION_ORB_RETRO[graha]
    return Combustion(separation <= limit, separation, limit)


def sign_map_from_longitudes(longitudes: dict[Graha, float]) -> dict[Graha, Rashi]:
    """Convenience: build the ``signs`` argument that the relation functions need."""
    return {graha: rashi_at(lon)[0] for graha, lon in longitudes.items()}


def dignity_table(longitudes: dict[Graha, float]) -> dict[Graha, Dignity]:
    """Dignity for every graha in one pass, so callers cannot compute it per-section.

    Only the seven true grahas plus the nodes are considered; ``longitudes`` may contain
    extra bodies (outer planets) and they are ignored rather than forced through a table
    that has no row for them.
    """
    signs = sign_map_from_longitudes(longitudes)
    known = (*SAPTA_GRAHA, Graha.RAHU, Graha.KETU)
    return {
        graha: dignity_of(graha, longitudes[graha], signs)
        for graha in known
        if graha in longitudes
    }
