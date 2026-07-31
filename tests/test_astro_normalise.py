"""Tests for app/astro/normalise.py.

The headline test is ``test_defect_7_misspelled_nakshatra_resolves`` — the reference report
printed "Sun Nakshatra: Bharni — details unavailable" because a lookup key missed. Every
spelling this API has been seen to emit must land on a canonical entry.
"""
from __future__ import annotations

import pytest

from app.astro.enums import Graha, Rashi
from app.astro.normalise import (
    NAKSHATRA_SPAN,
    NAKSHATRAS,
    PADA_SPAN,
    NameResolutionError,
    format_degree,
    graha_label,
    is_ascendant,
    nakshatra_at,
    nakshatra_elapsed_fraction,
    normalise_longitude,
    rashi_at,
    resolve_graha,
    resolve_nakshatra,
    resolve_rashi,
    to_devanagari_digits,
    try_resolve_graha,
    try_resolve_nakshatra,
)


# --- the defect this module exists to prevent -------------------------------------------

@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Bharni", "Bharani"),          # the exact reference-report failure
        ("Barani", "Bharani"),
        ("भरणी", "Bharani"),
        ("BHARANI", "Bharani"),
        ("  bharani  ", "Bharani"),
        ("Mrigasira", "Mrigashira"),
        ("Mrigashirsha", "Mrigashira"),
        ("Makayiram", "Mrigashira"),
        ("Poorattathi", "Purva Bhadrapada"),
        ("Uthirattathi", "Uttara Bhadrapada"),
        ("Purvashada", "Purva Ashadha"),
        ("purva-ashadha", "Purva Ashadha"),
        ("Uttarashada", "Uttara Ashadha"),
        ("Kettai", "Jyeshtha"),
        ("Moolam", "Mula"),
        ("Sathayam", "Shatabhisha"),
        ("Thiruvonam", "Shravana"),
        ("Avittam", "Dhanishta"),
        ("Ayilyam", "Ashlesha"),
        ("Karthigai", "Krittika"),
        ("Kṛttikā", "Krittika"),        # academic transliteration with diacritics
        ("Mṛgaśira", "Mrigashira"),
        ("Aśleṣā", "Ashlesha"),
        ("Jyeṣṭhā", "Jyeshtha"),
        ("Revathi", "Revati"),
    ],
)
def test_defect_7_misspelled_nakshatra_resolves(label: str, expected: str) -> None:
    assert resolve_nakshatra(label).en == expected


def test_every_canonical_name_and_alias_resolves_to_itself() -> None:
    """No entry in the master table may be unreachable by any of its own spellings."""
    for nak in NAKSHATRAS:
        for variant in (nak.en, nak.hi, *nak.aliases):
            assert resolve_nakshatra(variant).index == nak.index, variant


def test_nakshatra_table_is_complete_and_ordered() -> None:
    assert len(NAKSHATRAS) == 27
    assert [n.index for n in NAKSHATRAS] == list(range(1, 28))
    assert len({n.en for n in NAKSHATRAS}) == 27
    assert len({n.hi for n in NAKSHATRAS}) == 27


def test_vimshottari_lord_sequence_is_intact() -> None:
    """The lord cycle is what makes the dasha balance computable — it must not be reordered."""
    expected = [
        Graha.KETU, Graha.VENUS, Graha.SUN, Graha.MOON, Graha.MARS,
        Graha.RAHU, Graha.JUPITER, Graha.SATURN, Graha.MERCURY,
    ] * 3
    assert [n.lord for n in NAKSHATRAS] == expected


def test_unknown_nakshatra_raises_rather_than_returning_none() -> None:
    with pytest.raises(NameResolutionError):
        resolve_nakshatra("Definitely Not A Nakshatra")
    with pytest.raises(NameResolutionError):
        resolve_nakshatra("")
    assert try_resolve_nakshatra("Definitely Not A Nakshatra") is None


# --- longitude derivation ---------------------------------------------------------------

def test_nakshatra_at_boundaries() -> None:
    assert nakshatra_at(0.0)[0].en == "Ashwini"
    assert nakshatra_at(0.0)[1] == 1
    assert nakshatra_at(NAKSHATRA_SPAN - 0.001)[0].en == "Ashwini"
    assert nakshatra_at(NAKSHATRA_SPAN)[0].en == "Bharani"
    assert nakshatra_at(359.999)[0].en == "Revati"
    assert nakshatra_at(359.999)[1] == 4


def test_pada_divides_the_nakshatra_into_four() -> None:
    span = NAKSHATRA_SPAN
    assert nakshatra_at(span * 0.1)[1] == 1
    assert nakshatra_at(span * 0.3)[1] == 2
    assert nakshatra_at(span * 0.6)[1] == 3
    assert nakshatra_at(span * 0.9)[1] == 4


def test_pada_never_exceeds_four_at_the_top_of_the_arc() -> None:
    """Floating point at an exact boundary must not produce a pada 5."""
    for index in range(27):
        top = (index + 1) * NAKSHATRA_SPAN - 1e-12
        _, pada = nakshatra_at(top)
        assert 1 <= pada <= 4


def test_elapsed_fraction_spans_zero_to_one() -> None:
    assert nakshatra_elapsed_fraction(0.0) == pytest.approx(0.0)
    assert nakshatra_elapsed_fraction(NAKSHATRA_SPAN / 2) == pytest.approx(0.5)
    assert nakshatra_elapsed_fraction(NAKSHATRA_SPAN * 3.25) == pytest.approx(0.25)


# The nakshatra span is 13.333... — no exact binary representation — so a longitude that lands
# on a round multiple like 40°, 80° or 120° used to floor one nakshatra early and report an
# elapsed fraction of 0.99999999 instead of 0.0. The Vimshottari lord comes from the
# nakshatra, so that error moved the whole dasha timeline by a full Mahadasha.

def test_round_longitudes_land_in_the_nakshatra_they_start() -> None:
    assert nakshatra_at(40.0)[0].en == "Rohini"
    assert nakshatra_at(80.0)[0].en == "Punarvasu"
    assert nakshatra_at(120.0)[0].en == "Magha"
    assert nakshatra_at(160.0)[0].en == "Hasta"


def test_every_nakshatra_boundary_is_exact() -> None:
    """At the start of each of the 27 arcs: the arc's own nakshatra, pada 1, nothing elapsed."""
    for index in range(27):
        boundary = index * NAKSHATRA_SPAN
        nakshatra, pada = nakshatra_at(boundary)
        assert nakshatra.index == index + 1, boundary
        assert pada == 1
        assert nakshatra_elapsed_fraction(boundary) == pytest.approx(0.0, abs=1e-12)


def test_every_pada_boundary_is_exact() -> None:
    """The same float problem exists one level down: 100° is exactly the Pushya pada-2/3
    join, and flooring a division by 3.333... put it in pada 2. Both the nakshatra and the
    pada are derived from one exact 0-107 index, so they cannot disagree."""
    for pada_index in range(108):
        boundary = pada_index * PADA_SPAN
        nakshatra, pada = nakshatra_at(boundary)
        assert nakshatra.index == pada_index // 4 + 1, boundary
        assert pada == pada_index % 4 + 1, boundary

    assert nakshatra_at(100.0) == (NAKSHATRAS[7], 3)


def test_elapsed_fraction_is_never_out_of_range() -> None:
    """It multiplies a lord's period to give the balance at birth, so a value marginally
    outside [0, 1] would produce a negative or over-long first Mahadasha."""
    for index in range(27):
        for offset in (0.0, 1e-13, NAKSHATRA_SPAN / 2, NAKSHATRA_SPAN - 1e-13):
            fraction = nakshatra_elapsed_fraction(index * NAKSHATRA_SPAN + offset)
            assert 0.0 <= fraction <= 1.0


def test_nakshatra_at_and_elapsed_fraction_never_disagree() -> None:
    """Both must read off the same index. If one floors early and the other does not, the
    dasha lord and the balance come from different nakshatras."""
    for index in range(27):
        boundary = index * NAKSHATRA_SPAN
        for delta in (-1e-9, 0.0, 1e-9):
            longitude = (boundary + delta) % 360.0
            nakshatra, _ = nakshatra_at(longitude)
            fraction = nakshatra_elapsed_fraction(longitude)
            # Near the start of an arc the fraction is ~0; near the end it is ~1.
            expected_late = delta < 0
            assert (fraction > 0.5) == expected_late, (nakshatra.en, longitude, fraction)


def test_longitudes_are_folded_into_range() -> None:
    assert normalise_longitude(360.0) == pytest.approx(0.0)
    assert normalise_longitude(370.5) == pytest.approx(10.5)
    assert normalise_longitude(-1.0) == pytest.approx(359.0)


def test_rashi_at_maps_thirty_degree_arcs() -> None:
    assert rashi_at(0.0) == (Rashi.ARIES, pytest.approx(0.0))
    assert rashi_at(29.99)[0] is Rashi.ARIES
    assert rashi_at(30.0)[0] is Rashi.TAURUS
    assert rashi_at(330.0)[0] is Rashi.PISCES
    sign, degree = rashi_at(64.5)
    assert sign is Rashi.GEMINI
    assert degree == pytest.approx(4.5)


# --- signs and planets ------------------------------------------------------------------

@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Aries", Rashi.ARIES), ("मेष", Rashi.ARIES), ("Mesham", Rashi.ARIES),
        ("Kanni", Rashi.VIRGO), ("Kanya", Rashi.VIRGO), ("कन्या", Rashi.VIRGO),
        ("Vrischikam", Rashi.SCORPIO), ("वृश्चिक", Rashi.SCORPIO),
        ("Kumbam", Rashi.AQUARIUS), ("कुम्भ", Rashi.AQUARIUS),
        (5, Rashi.LEO), ("5", Rashi.LEO), (12, Rashi.PISCES),
    ],
)
def test_resolve_rashi(label, expected: Rashi) -> None:
    assert resolve_rashi(label) is expected


def test_resolve_rashi_rejects_out_of_range_ids() -> None:
    with pytest.raises(NameResolutionError):
        resolve_rashi(13)
    with pytest.raises(NameResolutionError):
        resolve_rashi(0)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Sun", Graha.SUN), ("सूर्य", Graha.SUN), ("रवि", Graha.SUN), ("Su", Graha.SUN),
        ("Moon", Graha.MOON), ("चंद्र", Graha.MOON), ("चन्द्र", Graha.MOON),
        ("चंद्रमा", Graha.MOON), ("Chandra", Graha.MOON),
        ("Jupiter", Graha.JUPITER), ("बृहस्पति", Graha.JUPITER), ("गुरु", Graha.JUPITER),
        ("Saturn", Graha.SATURN), ("शनि", Graha.SATURN), ("Shani", Graha.SATURN),
        ("Mangal", Graha.MARS), ("मंगल", Graha.MARS),
        ("Rahu", Graha.RAHU), ("राहु", Graha.RAHU), ("Ketu", Graha.KETU),
    ],
)
def test_resolve_graha(label: str, expected: Graha) -> None:
    assert resolve_graha(label) is expected


def test_ascendant_is_not_a_graha() -> None:
    """It is a point. Letting it into a Graha-keyed dict is how houses get counted twice."""
    for label in ("Ascendant", "लग्न", "Lagna", "Asc"):
        assert is_ascendant(label)
        with pytest.raises(NameResolutionError):
            resolve_graha(label)
        assert try_resolve_graha(label) is None


def test_graha_label_falls_back_to_the_input() -> None:
    assert graha_label("Sun", "hi") == "सूर्य"
    assert graha_label("Sun", "en") == "Sun"
    assert graha_label("लग्न", "hi") == "लग्न"
    assert graha_label("Ascendant", "en") == "Ascendant"
    assert graha_label("Chiron", "en") == "Chiron"  # unknown passes through, does not raise


# --- display helpers --------------------------------------------------------------------

def test_format_degree() -> None:
    assert format_degree(12.5666) == "12°34'"
    assert format_degree(0.0) == "0°00'"
    assert format_degree(29.9999) == "30°00'"   # rounds up cleanly, never 29°60'
    assert format_degree(5.5, "hi") == "५°३०'"


def test_devanagari_digits() -> None:
    assert to_devanagari_digits("2026") == "२०२६"
    assert to_devanagari_digits("12°34'") == "१२°३४'"
    assert to_devanagari_digits("no digits") == "no digits"
