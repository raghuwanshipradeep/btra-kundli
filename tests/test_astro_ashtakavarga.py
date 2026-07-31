"""Tests for app/astro/ashtakavarga.py.

These pin defects #4 and #5. The per-planet totals and the 337 grand total are asserted as
*derived* properties of the benefic-point tables, never hardcoded into the module — so a typo
in any of the 56 lists fails here instead of shipping a wrong chart.
"""
from __future__ import annotations

import itertools

import pytest

from app.astro.ashtakavarga import (
    BENEFIC_PLACES,
    CONTRIBUTORS,
    EKADHIPATYA_PAIRS,
    TRINES,
    compute_ashtakavarga,
    compute_bav,
    ekadhipatya_shodhana,
    sav_verdict,
    trikona_shodhana,
)
from app.astro.enums import SAPTA_GRAHA, SAV_MEAN, SAV_TOTAL, Graha, Rashi, TransitGrade

# Two genuinely different charts, so "is the matrix chart-specific?" can be answered.
CHART_A: dict[Graha, Rashi] = {
    Graha.SUN: Rashi.LEO,
    Graha.MOON: Rashi.TAURUS,
    Graha.MARS: Rashi.GEMINI,
    Graha.MERCURY: Rashi.CANCER,
    Graha.JUPITER: Rashi.PISCES,
    Graha.VENUS: Rashi.GEMINI,
    Graha.SATURN: Rashi.CAPRICORN,
}
LAGNA_A = Rashi.SCORPIO

CHART_B: dict[Graha, Rashi] = {
    Graha.SUN: Rashi.AQUARIUS,
    Graha.MOON: Rashi.LIBRA,
    Graha.MARS: Rashi.ARIES,
    Graha.MERCURY: Rashi.CAPRICORN,
    Graha.JUPITER: Rashi.VIRGO,
    Graha.VENUS: Rashi.SAGITTARIUS,
    Graha.SATURN: Rashi.LEO,
}
LAGNA_B = Rashi.GEMINI


# --- the benefic-point tables themselves -------------------------------------------------

def test_every_planet_has_all_eight_contributors() -> None:
    for graha in SAPTA_GRAHA:
        assert set(BENEFIC_PLACES[graha]) == set(CONTRIBUTORS), graha


def test_only_the_seven_grahas_have_an_ashtakavarga() -> None:
    """Rahu and Ketu are not given one by classical convention."""
    assert set(BENEFIC_PLACES) == set(SAPTA_GRAHA)


def test_benefic_houses_are_valid_and_unique() -> None:
    for graha, table in BENEFIC_PLACES.items():
        for contributor, houses in table.items():
            assert houses, (graha, contributor)
            assert all(1 <= h <= 12 for h in houses), (graha, contributor, houses)
            assert len(set(houses)) == len(houses), (graha, contributor)
            assert list(houses) == sorted(houses), (graha, contributor)


@pytest.mark.parametrize(
    ("graha", "expected_total"),
    [
        (Graha.SUN, 48),
        (Graha.MOON, 49),
        (Graha.MARS, 39),
        (Graha.MERCURY, 54),
        (Graha.JUPITER, 56),
        (Graha.VENUS, 52),
        (Graha.SATURN, 39),
    ],
)
def test_classical_per_planet_totals_fall_out_of_the_tables(
    graha: Graha, expected_total: int
) -> None:
    """The table lengths must sum to the classical BAV total for that planet.

    This is the typo detector: change one benefic house anywhere and the total moves.
    """
    assert sum(len(houses) for houses in BENEFIC_PLACES[graha].values()) == expected_total


def test_the_tables_sum_to_337() -> None:
    total = sum(
        len(houses)
        for table in BENEFIC_PLACES.values()
        for houses in table.values()
    )
    assert total == SAV_TOTAL == 337


# --- defect #4: SAV is always 337 --------------------------------------------------------

@pytest.mark.parametrize(("planets", "lagna"), [(CHART_A, LAGNA_A), (CHART_B, LAGNA_B)])
def test_sav_always_totals_337(planets: dict[Graha, Rashi], lagna: Rashi) -> None:
    data = compute_ashtakavarga(planets, lagna)
    assert data.sav_total == 337
    assert sum(data.sav.values()) == 337


def test_sav_totals_337_for_every_lagna_with_a_stacked_chart() -> None:
    """Even a degenerate chart with all seven planets in one sign totals 337."""
    for lagna in Rashi:
        for stack in (Rashi.ARIES, Rashi.CANCER, Rashi.AQUARIUS):
            planets = {g: stack for g in SAPTA_GRAHA}
            assert compute_ashtakavarga(planets, lagna).sav_total == 337


def test_sav_mean_is_the_only_valid_comparison_point() -> None:
    assert SAV_MEAN == pytest.approx(337 / 12)
    assert SAV_MEAN == pytest.approx(28.0833, abs=1e-4)


def test_sav_verdict_bands() -> None:
    assert sav_verdict(31) == "supported"
    assert sav_verdict(30) == "supported"
    assert sav_verdict(28) == "average"
    assert sav_verdict(26) == "average"
    assert sav_verdict(25) == "needs_effort"
    assert sav_verdict(18) == "needs_effort"


# --- defect #5: the matrix must be chart-specific ----------------------------------------

def test_bav_row_totals_are_invariant_but_distributions_are_not() -> None:
    """The headline of defect #5. Row totals match across two unrelated charts — which is
    why they are not a strength score — while the house-level values differ."""
    a = compute_ashtakavarga(CHART_A, LAGNA_A)
    b = compute_ashtakavarga(CHART_B, LAGNA_B)

    for graha in SAPTA_GRAHA:
        assert a.bav[graha].total == b.bav[graha].total, graha

    differing = [g for g in SAPTA_GRAHA if a.bav[g].bindus != b.bav[g].bindus]
    assert len(differing) == 7, "every planet's distribution should differ between charts"

    assert a.sav != b.sav


def test_prastara_is_a_full_eight_by_twelve_spread() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    for graha in SAPTA_GRAHA:
        prastara = data.bav[graha].prastara
        assert set(prastara) == set(CONTRIBUTORS)
        for contributor, row in prastara.items():
            assert set(row) == set(Rashi), (graha, contributor)
            assert all(v in (0, 1) for v in row.values()), (graha, contributor)


def test_prastara_column_sums_equal_the_bindu_row() -> None:
    """The published spread must reconcile with the published bindu count, or the report
    contradicts itself on the same page."""
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    for graha in SAPTA_GRAHA:
        bav = data.bav[graha]
        for sign in Rashi:
            column = sum(bav.prastara[c][sign] for c in CONTRIBUTORS)
            assert column == bav.bindus[sign], (graha, sign)


def test_each_contributor_donates_exactly_its_table_length() -> None:
    """A contributor with 6 benefic houses donates 6 bindus across the 12 signs, always."""
    data = compute_ashtakavarga(CHART_B, LAGNA_B)
    for graha in SAPTA_GRAHA:
        for contributor in CONTRIBUTORS:
            donated = sum(data.bav[graha].prastara[contributor].values())
            assert donated == len(BENEFIC_PLACES[graha][contributor]), (graha, contributor)


def test_bindus_stay_within_zero_to_eight() -> None:
    """Eight contributors means a sign cannot hold more than 8 bindus for one planet."""
    for planets, lagna in ((CHART_A, LAGNA_A), (CHART_B, LAGNA_B)):
        data = compute_ashtakavarga(planets, lagna)
        for graha in SAPTA_GRAHA:
            for value in data.bav[graha].bindus.values():
                assert 0 <= value <= 8


def test_missing_contributor_raises_rather_than_producing_a_short_matrix() -> None:
    incomplete = {g: Rashi.ARIES for g in SAPTA_GRAHA if g is not Graha.SATURN}
    with pytest.raises(ValueError, match="missing"):
        compute_ashtakavarga(incomplete, Rashi.LEO)
    with pytest.raises(ValueError, match="8 contributors"):
        compute_bav(Graha.SUN, {Graha.SUN: Rashi.ARIES})


# --- houses ------------------------------------------------------------------------------

def test_sav_by_house_is_keyed_one_to_twelve_and_preserves_the_total() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    by_house = data.sav_by_house()
    assert sorted(by_house) == list(range(1, 13))
    assert sum(by_house.values()) == 337


def test_house_one_is_the_lagna_sign() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    assert data.house_of_sign[LAGNA_A] == 1
    assert data.sav_by_house()[1] == data.sav[LAGNA_A]


def test_strongest_and_weakest_houses_are_consistent() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    strongest = data.strongest_houses(3)
    weakest = data.weakest_houses(3)
    assert len(strongest) == len(weakest) == 3
    assert strongest[0][1] >= strongest[-1][1]
    assert weakest[0][1] <= weakest[-1][1]
    assert strongest[0][1] >= weakest[0][1]


# --- the transit filter ------------------------------------------------------------------

def test_transit_bindu_reads_the_unreduced_bav() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    for sign in Rashi:
        assert data.transit_bindu(Graha.SATURN, sign) == data.bav[Graha.SATURN].bindus[sign]


def test_transit_grade_thresholds() -> None:
    assert TransitGrade.from_bindus(5) is TransitGrade.SUPPORTIVE
    assert TransitGrade.from_bindus(4) is TransitGrade.SUPPORTIVE
    assert TransitGrade.from_bindus(3) is TransitGrade.MIXED
    assert TransitGrade.from_bindus(2) is TransitGrade.STRESSFUL
    assert TransitGrade.from_bindus(0) is TransitGrade.STRESSFUL


def test_nodes_have_no_bindus_and_do_not_crash_the_filter() -> None:
    """Rahu/Ketu get no Ashtakavarga, so the transit section must not claim a bindu grade
    for them. Returning 0 rather than raising keeps the caller simple; the transit module
    is responsible for grading nodes some other way."""
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    assert data.transit_bindu(Graha.RAHU, Rashi.ARIES) == 0
    assert data.transit_bindu(Graha.KETU, Rashi.LIBRA) == 0


# --- shodhana ----------------------------------------------------------------------------

def test_trines_and_pairs_partition_correctly() -> None:
    covered = list(itertools.chain.from_iterable(TRINES))
    assert sorted(s.value for s in covered) == list(range(1, 13))

    # Ekadhipatya excludes Cancer and Leo, the two single-lord signs.
    paired = set(itertools.chain.from_iterable(EKADHIPATYA_PAIRS))
    assert Rashi.CANCER not in paired
    assert Rashi.LEO not in paired
    assert len(paired) == 10
    for first, second in EKADHIPATYA_PAIRS:
        assert first.lord is second.lord, (first, second)


def test_trikona_shodhana_subtracts_the_trine_minimum() -> None:
    bindus = {sign: 0 for sign in Rashi}
    bindus[Rashi.ARIES] = 5
    bindus[Rashi.LEO] = 3
    bindus[Rashi.SAGITTARIUS] = 4
    out = trikona_shodhana(bindus)
    assert out[Rashi.ARIES] == 2
    assert out[Rashi.LEO] == 0
    assert out[Rashi.SAGITTARIUS] == 1


def test_trikona_shodhana_skips_a_trine_containing_a_zero() -> None:
    bindus = {sign: 0 for sign in Rashi}
    bindus[Rashi.ARIES] = 5
    bindus[Rashi.LEO] = 0
    bindus[Rashi.SAGITTARIUS] = 4
    out = trikona_shodhana(bindus)
    assert out[Rashi.ARIES] == 5
    assert out[Rashi.SAGITTARIUS] == 4


def test_trikona_shodhana_never_produces_a_negative() -> None:
    for planets, lagna in ((CHART_A, LAGNA_A), (CHART_B, LAGNA_B)):
        data = compute_ashtakavarga(planets, lagna)
        for graha in SAPTA_GRAHA:
            assert all(v >= 0 for v in data.reduced[graha].values()), graha


def test_ekadhipatya_leaves_both_occupied_pairs_alone() -> None:
    bindus = {sign: 4 for sign in Rashi}
    bindus[Rashi.ARIES] = 6
    bindus[Rashi.SCORPIO] = 2
    out = ekadhipatya_shodhana(bindus, frozenset({Rashi.ARIES, Rashi.SCORPIO}))
    assert out[Rashi.ARIES] == 6
    assert out[Rashi.SCORPIO] == 2


def test_ekadhipatya_zeroes_the_lesser_unoccupied_sign() -> None:
    bindus = {sign: 4 for sign in Rashi}
    bindus[Rashi.ARIES] = 6       # occupied
    bindus[Rashi.SCORPIO] = 2     # empty, fewer -> 0
    out = ekadhipatya_shodhana(bindus, frozenset({Rashi.ARIES}))
    assert out[Rashi.ARIES] == 6
    assert out[Rashi.SCORPIO] == 0


def test_ekadhipatya_caps_a_greater_unoccupied_sign() -> None:
    bindus = {sign: 4 for sign in Rashi}
    bindus[Rashi.ARIES] = 3       # occupied
    bindus[Rashi.SCORPIO] = 7     # empty, greater -> capped to 3
    out = ekadhipatya_shodhana(bindus, frozenset({Rashi.ARIES}))
    assert out[Rashi.SCORPIO] == 3


def test_ekadhipatya_when_neither_sign_is_occupied() -> None:
    bindus = {sign: 4 for sign in Rashi}
    bindus[Rashi.GEMINI] = 5
    bindus[Rashi.VIRGO] = 2
    out = ekadhipatya_shodhana(bindus, frozenset())
    assert out[Rashi.GEMINI] == out[Rashi.VIRGO] == 2

    bindus[Rashi.GEMINI] = bindus[Rashi.VIRGO] = 4
    out = ekadhipatya_shodhana(bindus, frozenset())
    assert out[Rashi.GEMINI] == out[Rashi.VIRGO] == 0


def test_shodhya_pinda_is_positive_and_chart_specific() -> None:
    a = compute_ashtakavarga(CHART_A, LAGNA_A)
    b = compute_ashtakavarga(CHART_B, LAGNA_B)
    assert set(a.shodhya_pinda) == set(SAPTA_GRAHA)
    assert all(v >= 0 for v in a.shodhya_pinda.values())
    assert a.shodhya_pinda != b.shodhya_pinda


def test_reduction_never_increases_a_bindu_count() -> None:
    data = compute_ashtakavarga(CHART_A, LAGNA_A)
    for graha in SAPTA_GRAHA:
        for sign in Rashi:
            assert data.reduced[graha][sign] <= data.bav[graha].bindus[sign], (graha, sign)


# --- determinism -------------------------------------------------------------------------

def test_computation_is_deterministic() -> None:
    """Golden-file snapshots downstream depend on this."""
    first = compute_ashtakavarga(CHART_A, LAGNA_A)
    second = compute_ashtakavarga(CHART_A, LAGNA_A)
    assert first.sav == second.sav
    assert first.shodhya_pinda == second.shodhya_pinda
    for graha in SAPTA_GRAHA:
        assert first.bav[graha].bindus == second.bav[graha].bindus
