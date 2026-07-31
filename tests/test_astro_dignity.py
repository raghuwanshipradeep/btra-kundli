"""Tests for app/astro/dignity.py.

Two defects are pinned here. Defect #2 — one planet described as "exalted" in one section
and "own sign" in another — is prevented by there being exactly one ``dignity_of`` answer
per placement. And the Part 12 note about narrative inflation is why the Moon/Mercury
exaltation arcs are degree-capped rather than swallowing the whole sign.
"""
from __future__ import annotations

import pytest

from app.astro.dignity import (
    DEBILITATION_SIGN,
    EXACT_EXALTATION_DEGREE,
    EXALTATION_SIGN,
    MOOLATRIKONA,
    OWN_SIGNS,
    baladi_avastha,
    combustion,
    compound_relation,
    deeptadi_avastha,
    dignity_of,
    dignity_table,
    exaltation_orb,
    is_gandanta,
    is_rashi_sandhi,
    natural_relation,
    sign_map_from_longitudes,
    temporal_relation,
)
from app.astro.enums import SAPTA_GRAHA, BaladiAvastha, Dignity, Graha, Rashi, Relation


def lon(sign: Rashi, degree: float = 15.0) -> float:
    """Sidereal longitude for a degree within a sign — keeps the tests readable."""
    return (sign.value - 1) * 30.0 + degree


# --- the exaltation axis ----------------------------------------------------------------

def test_debilitation_is_always_opposite_exaltation() -> None:
    for graha, exalt in EXALTATION_SIGN.items():
        debil = DEBILITATION_SIGN[graha]
        assert (debil.value - exalt.value) % 12 == 6, graha


def test_exaltation_and_debilitation() -> None:
    signs = {Graha.SUN: Rashi.ARIES}
    assert dignity_of(Graha.SUN, lon(Rashi.ARIES, 10.0), signs) is Dignity.EXALTED
    assert dignity_of(Graha.SUN, lon(Rashi.LIBRA, 10.0), {}) is Dignity.DEBILITATED
    assert dignity_of(Graha.MARS, lon(Rashi.CAPRICORN, 28.0), {}) is Dignity.EXALTED
    assert dignity_of(Graha.MARS, lon(Rashi.CANCER, 5.0), {}) is Dignity.DEBILITATED
    assert dignity_of(Graha.SATURN, lon(Rashi.LIBRA, 20.0), {}) is Dignity.EXALTED
    assert dignity_of(Graha.JUPITER, lon(Rashi.CANCER, 5.0), {}) is Dignity.EXALTED
    assert dignity_of(Graha.JUPITER, lon(Rashi.CAPRICORN, 5.0), {}) is Dignity.DEBILITATED
    assert dignity_of(Graha.VENUS, lon(Rashi.PISCES, 27.0), {}) is Dignity.EXALTED


def test_moon_exaltation_is_capped_at_three_degrees() -> None:
    """Taurus is both the Moon's exaltation and its Moolatrikona sign. Handing the whole
    sign to exaltation would over-report strength for 27 of its 30 degrees."""
    assert dignity_of(Graha.MOON, lon(Rashi.TAURUS, 1.0), {}) is Dignity.EXALTED
    assert dignity_of(Graha.MOON, lon(Rashi.TAURUS, 2.99), {}) is Dignity.EXALTED
    assert dignity_of(Graha.MOON, lon(Rashi.TAURUS, 3.0), {}) is Dignity.MOOLATRIKONA
    assert dignity_of(Graha.MOON, lon(Rashi.TAURUS, 25.0), {}) is Dignity.MOOLATRIKONA


def test_mercury_virgo_splits_into_three_bands() -> None:
    """0-15 exalted, 15-20 Moolatrikona, 20-30 own sign — the classical division."""
    assert dignity_of(Graha.MERCURY, lon(Rashi.VIRGO, 5.0), {}) is Dignity.EXALTED
    assert dignity_of(Graha.MERCURY, lon(Rashi.VIRGO, 14.99), {}) is Dignity.EXALTED
    assert dignity_of(Graha.MERCURY, lon(Rashi.VIRGO, 17.0), {}) is Dignity.MOOLATRIKONA
    assert dignity_of(Graha.MERCURY, lon(Rashi.VIRGO, 25.0), {}) is Dignity.OWN


def test_moolatrikona_is_a_degree_range_not_a_whole_sign() -> None:
    """Mars owns Aries but is Moolatrikona only in its first 12°."""
    assert dignity_of(Graha.MARS, lon(Rashi.ARIES, 5.0), {}) is Dignity.MOOLATRIKONA
    assert dignity_of(Graha.MARS, lon(Rashi.ARIES, 11.99), {}) is Dignity.MOOLATRIKONA
    assert dignity_of(Graha.MARS, lon(Rashi.ARIES, 12.0), {}) is Dignity.OWN
    assert dignity_of(Graha.MARS, lon(Rashi.ARIES, 29.0), {}) is Dignity.OWN
    # Scorpio is Mars's other own sign but is nobody's Moolatrikona.
    assert dignity_of(Graha.MARS, lon(Rashi.SCORPIO, 5.0), {}) is Dignity.OWN


def test_moolatrikona_table_is_internally_consistent() -> None:
    """A Moolatrikona sign is a sign the planet rules — with one classical exception.

    The Moon's Moolatrikona is Taurus, which it does not rule (Cancer is its own sign);
    Taurus is its exaltation sign instead. Every other graha's Moolatrikona sits inside its
    own rulership. Encoding the exception here rather than "fixing" the table keeps someone
    from later normalising the Moon to Cancer and quietly changing every chart.
    """
    for graha, (sign, start, end) in MOOLATRIKONA.items():
        assert 0.0 <= start < end <= 30.0, graha
        if graha is Graha.MOON:
            assert sign is Rashi.TAURUS
            assert sign is EXALTATION_SIGN[graha]
            assert sign not in OWN_SIGNS[graha]
        else:
            assert sign in OWN_SIGNS[graha], graha


def test_exaltation_orb_measures_distance_from_the_deep_point() -> None:
    assert exaltation_orb(Graha.SUN, lon(Rashi.ARIES, 10.0)) == pytest.approx(0.0)
    assert exaltation_orb(Graha.SUN, lon(Rashi.ARIES, 12.5)) == pytest.approx(2.5)
    assert exaltation_orb(Graha.SUN, lon(Rashi.ARIES, 7.0)) == pytest.approx(3.0)
    # Not in the exaltation sign at all.
    assert exaltation_orb(Graha.SUN, lon(Rashi.LEO, 10.0)) is None


def test_every_graha_has_a_deep_exaltation_degree_except_the_nodes() -> None:
    for graha in SAPTA_GRAHA:
        assert graha in EXACT_EXALTATION_DEGREE
    assert Graha.RAHU not in EXACT_EXALTATION_DEGREE
    assert Graha.KETU not in EXACT_EXALTATION_DEGREE


# --- Panchadha Maitri -------------------------------------------------------------------

def test_natural_relations_follow_the_classical_table() -> None:
    assert natural_relation(Graha.SUN, Graha.MOON) is Relation.FRIEND
    assert natural_relation(Graha.SUN, Graha.SATURN) is Relation.ENEMY
    assert natural_relation(Graha.SUN, Graha.MERCURY) is Relation.NEUTRAL
    assert natural_relation(Graha.SATURN, Graha.VENUS) is Relation.FRIEND
    assert natural_relation(Graha.JUPITER, Graha.VENUS) is Relation.ENEMY
    assert natural_relation(Graha.MOON, Graha.SATURN) is Relation.NEUTRAL


def test_nodes_have_no_natural_relationships() -> None:
    assert natural_relation(Graha.RAHU, Graha.SUN) is Relation.NEUTRAL
    assert natural_relation(Graha.SUN, Graha.RAHU) is Relation.NEUTRAL
    assert natural_relation(Graha.SUN, Graha.SUN) is Relation.NEUTRAL


def test_temporal_relation_uses_the_2_3_4_10_11_12_rule() -> None:
    base = Rashi.ARIES
    for offset, expected in [
        (0, Relation.ENEMY),      # same sign — 1st
        (1, Relation.FRIEND),     # 2nd
        (2, Relation.FRIEND),     # 3rd
        (3, Relation.FRIEND),     # 4th
        (4, Relation.ENEMY),      # 5th
        (5, Relation.ENEMY),      # 6th
        (6, Relation.ENEMY),      # 7th
        (7, Relation.ENEMY),      # 8th
        (8, Relation.ENEMY),      # 9th
        (9, Relation.FRIEND),     # 10th
        (10, Relation.FRIEND),    # 11th
        (11, Relation.FRIEND),    # 12th
    ]:
        other = Rashi(((base.value - 1 + offset) % 12) + 1)
        assert temporal_relation(base, other) is expected, offset


def test_compound_relation_combines_both_tables() -> None:
    # Sun and Moon are natural friends. Put the Moon in the 2nd from the Sun -> temporal
    # friend too -> great friend.
    signs = {Graha.SUN: Rashi.ARIES, Graha.MOON: Rashi.TAURUS}
    assert compound_relation(Graha.SUN, Graha.MOON, signs) is Relation.GREAT_FRIEND

    # Same natural friendship, but the Moon in the 7th -> temporal enemy -> neutral.
    signs = {Graha.SUN: Rashi.ARIES, Graha.MOON: Rashi.LIBRA}
    assert compound_relation(Graha.SUN, Graha.MOON, signs) is Relation.NEUTRAL

    # Natural enemies (Sun/Saturn) that are also temporal enemies -> great enemy.
    signs = {Graha.SUN: Rashi.ARIES, Graha.SATURN: Rashi.LIBRA}
    assert compound_relation(Graha.SUN, Graha.SATURN, signs) is Relation.GREAT_ENEMY

    # Natural enemies that are temporal friends -> softened to neutral.
    signs = {Graha.SUN: Rashi.ARIES, Graha.SATURN: Rashi.TAURUS}
    assert compound_relation(Graha.SUN, Graha.SATURN, signs) is Relation.NEUTRAL


def test_compound_relation_degrades_to_natural_when_a_sign_is_missing() -> None:
    assert compound_relation(Graha.SUN, Graha.MOON, {}) is Relation.FRIEND


def test_compound_dignity_can_differ_from_the_natural_table_alone() -> None:
    """The reference report's failure: Mars called "neutral" from the natural table when the
    compound relationship says otherwise."""
    # Mars in Gemini (Mercury's sign). Naturally Mars counts Mercury an enemy.
    # Mercury in the 3rd from Mars -> temporal friend -> compound neutral.
    signs = {Graha.MARS: Rashi.GEMINI, Graha.MERCURY: Rashi.LEO}
    assert dignity_of(Graha.MARS, lon(Rashi.GEMINI, 10.0), signs) is Dignity.NEUTRAL

    # Move Mercury to the 6th from Mars -> temporal enemy -> compound great enemy.
    signs = {Graha.MARS: Rashi.GEMINI, Graha.MERCURY: Rashi.SCORPIO}
    assert dignity_of(Graha.MARS, lon(Rashi.GEMINI, 10.0), signs) is Dignity.GREAT_ENEMY


def test_nodes_never_get_a_friendship_based_dignity() -> None:
    signs = {Graha.RAHU: Rashi.GEMINI, Graha.MERCURY: Rashi.LEO}
    assert dignity_of(Graha.RAHU, lon(Rashi.GEMINI, 10.0), signs) is Dignity.NEUTRAL
    # But the exaltation convention still applies.
    assert dignity_of(Graha.RAHU, lon(Rashi.TAURUS, 10.0), signs) is Dignity.EXALTED
    assert dignity_of(Graha.KETU, lon(Rashi.TAURUS, 10.0), signs) is Dignity.DEBILITATED


def test_dignity_table_covers_nine_grahas_and_ignores_extras() -> None:
    longitudes = {g: lon(Rashi.ARIES, 10.0) for g in Graha}
    table = dignity_table(longitudes)
    assert set(table) == set(Graha)
    # An outer planet in the input must not raise or appear in the output.
    table2 = dignity_table({**longitudes, "Pluto": 100.0})  # type: ignore[dict-item]
    assert set(table2) == set(Graha)


def test_sign_map_helper() -> None:
    assert sign_map_from_longitudes({Graha.SUN: lon(Rashi.LEO, 3.0)}) == {Graha.SUN: Rashi.LEO}


# --- avastha ----------------------------------------------------------------------------

def test_baladi_runs_forward_in_odd_signs() -> None:
    assert baladi_avastha(lon(Rashi.ARIES, 1.0)) is BaladiAvastha.BALA
    assert baladi_avastha(lon(Rashi.ARIES, 7.0)) is BaladiAvastha.KUMARA
    assert baladi_avastha(lon(Rashi.ARIES, 13.0)) is BaladiAvastha.YUVA
    assert baladi_avastha(lon(Rashi.ARIES, 19.0)) is BaladiAvastha.VRIDDHA
    assert baladi_avastha(lon(Rashi.ARIES, 25.0)) is BaladiAvastha.MRITA


def test_baladi_reverses_in_even_signs() -> None:
    assert baladi_avastha(lon(Rashi.TAURUS, 1.0)) is BaladiAvastha.MRITA
    assert baladi_avastha(lon(Rashi.TAURUS, 25.0)) is BaladiAvastha.BALA
    assert baladi_avastha(lon(Rashi.TAURUS, 13.0)) is BaladiAvastha.YUVA


def test_baladi_never_indexes_past_the_table() -> None:
    for sign in Rashi:
        assert baladi_avastha(lon(sign, 29.999)) in set(BaladiAvastha)


def test_mrita_avastha_has_no_strength() -> None:
    assert BaladiAvastha.MRITA.strength_factor == 0.0
    assert BaladiAvastha.YUVA.strength_factor == 1.0


def test_deeptadi_precedence_puts_combustion_first() -> None:
    assert deeptadi_avastha(Graha.MERCURY, Dignity.EXALTED, is_combust=True) == "Kopa"
    assert deeptadi_avastha(Graha.MERCURY, Dignity.EXALTED, is_combust=False) == "Deepta"
    assert deeptadi_avastha(Graha.SATURN, Dignity.DEBILITATED, is_combust=False) == "Khala"
    assert deeptadi_avastha(Graha.SATURN, Dignity.OWN, is_combust=False) == "Swastha"


def test_every_dignity_maps_to_a_deeptadi_state() -> None:
    for dignity in Dignity:
        assert deeptadi_avastha(Graha.SUN, dignity, is_combust=False)


# --- boundary weaknesses ----------------------------------------------------------------

def test_gandanta_covers_the_three_water_fire_junctions() -> None:
    for water, fire in ((Rashi.CANCER, Rashi.LEO),
                        (Rashi.SCORPIO, Rashi.SAGITTARIUS),
                        (Rashi.PISCES, Rashi.ARIES)):
        assert is_gandanta(lon(water, 29.0))
        assert is_gandanta(lon(water, 27.0))
        assert not is_gandanta(lon(water, 25.0))
        assert is_gandanta(lon(fire, 1.0))
        assert is_gandanta(lon(fire, 3.0))
        assert not is_gandanta(lon(fire, 4.0))


def test_gandanta_does_not_fire_at_other_boundaries() -> None:
    assert not is_gandanta(lon(Rashi.ARIES, 29.5))     # Aries/Taurus is not a junction
    assert not is_gandanta(lon(Rashi.GEMINI, 0.5))
    assert not is_gandanta(lon(Rashi.CANCER, 15.0))


def test_rashi_sandhi_flags_the_reference_chart_venus() -> None:
    """Venus at 0.02° Gemini — barely functional, and the reference report glossed it."""
    assert is_rashi_sandhi(lon(Rashi.GEMINI, 0.02))
    assert is_rashi_sandhi(lon(Rashi.GEMINI, 0.99))
    assert not is_rashi_sandhi(lon(Rashi.GEMINI, 1.5))
    assert is_rashi_sandhi(lon(Rashi.GEMINI, 29.5))
    assert not is_rashi_sandhi(lon(Rashi.GEMINI, 15.0))


# --- combustion -------------------------------------------------------------------------

def test_combustion_uses_the_classical_orbs() -> None:
    sun = lon(Rashi.ARIES, 15.0)
    # Mercury 10° away — inside its 14° orb.
    result = combustion(Graha.MERCURY, lon(Rashi.ARIES, 25.0), sun)
    assert result.is_combust
    assert result.orb == pytest.approx(10.0)
    assert result.limit == pytest.approx(14.0)

    # Mercury 20° away — outside.
    assert not combustion(Graha.MERCURY, lon(Rashi.TAURUS, 5.0), sun).is_combust

    # Jupiter has the tightest orb of the majors at 11°.
    assert combustion(Graha.JUPITER, lon(Rashi.ARIES, 24.0), sun).is_combust
    assert not combustion(Graha.JUPITER, lon(Rashi.ARIES, 27.0), sun).is_combust


def test_retrograde_tightens_mercury_and_venus_orbs() -> None:
    sun = lon(Rashi.ARIES, 15.0)
    thirteen_away = lon(Rashi.ARIES, 28.0)
    assert combustion(Graha.MERCURY, thirteen_away, sun, is_retrograde=False).is_combust
    assert not combustion(Graha.MERCURY, thirteen_away, sun, is_retrograde=True).is_combust

    nine_away = lon(Rashi.ARIES, 24.0)
    assert combustion(Graha.VENUS, nine_away, sun, is_retrograde=False).is_combust
    assert not combustion(Graha.VENUS, nine_away, sun, is_retrograde=True).is_combust


def test_combustion_separation_wraps_the_short_way() -> None:
    """A planet at 355° and the Sun at 5° are 10° apart, not 350°."""
    result = combustion(Graha.MOON, 355.0, 5.0)
    assert result.orb == pytest.approx(10.0)
    assert result.is_combust


def test_sun_and_nodes_are_never_combust() -> None:
    sun = lon(Rashi.ARIES, 15.0)
    assert not combustion(Graha.SUN, sun, sun).is_combust
    assert not combustion(Graha.RAHU, lon(Rashi.ARIES, 16.0), sun).is_combust
    assert not combustion(Graha.KETU, lon(Rashi.ARIES, 16.0), sun).is_combust
    # The separation is still reported so a table can show it.
    assert combustion(Graha.RAHU, lon(Rashi.ARIES, 16.0), sun).orb == pytest.approx(1.0)


# --- the contract the rest of the report depends on -------------------------------------

def test_dignity_labels_exist_in_both_languages_and_are_distinct() -> None:
    """Every section renders these strings and nothing else. Two dignities sharing a label
    would make the dignity_consistency gate check unable to tell them apart."""
    for lang in ("en", "hi"):
        labels = [d.label(lang) for d in Dignity]
        assert all(labels), lang
        assert len(set(labels)) == len(labels), lang


def test_dignity_rank_orders_strongest_to_weakest() -> None:
    assert Dignity.EXALTED.rank > Dignity.OWN.rank > Dignity.NEUTRAL.rank
    assert Dignity.NEUTRAL.rank > Dignity.ENEMY.rank > Dignity.DEBILITATED.rank
    assert Dignity.EXALTED.is_strong and not Dignity.EXALTED.is_weak
    assert Dignity.DEBILITATED.is_weak and not Dignity.DEBILITATED.is_strong
