"""Tests for app/astro/dasha.py.

The point of this suite is the property the spec's Part 10 defect #1 turns on: there is one
timeline, one accessor, and one string for the running period. So most of these assert
structural invariants — no gaps, no overlaps, children tiling their parent exactly — rather
than spot-checking dates, because a report can only contradict itself if one of those breaks.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.astro.chart import build_chart
from app.astro.dasha import (
    EAGER_LEVELS,
    MAX_LEVEL,
    TOTAL_YEARS,
    VIMSHOTTARI_ORDER,
    VIMSHOTTARI_YEARS,
    YEAR_DAYS,
    DashaError,
    birth_datetime,
    build_from_data,
    build_timeline,
    cross_check_against_api,
    parse_api_datetime,
)
from app.astro.enums import Graha
from app.astro.normalise import NAKSHATRAS
from models import DashaPeriod as ApiDashaPeriod
from tests.fixtures.synthetic import CORPUS, build, deg

CORPUS_IDS = sorted(CORPUS)
NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


@pytest.fixture(scope="module")
def timelines():
    return {
        key: build_from_data(build_chart(data), data)
        for key, data in sorted(CORPUS.items())
    }


def _timeline_for(moon_longitude: float, **kwargs):
    """A timeline whose Moon sits exactly where the test needs it."""
    longitudes = {
        "Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": moon_longitude,
        "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Jupiter": deg(5, 10.0),
        "Venus": deg(6, 10.0), "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0),
        "Ketu": deg(2, 10.0),
    }
    data = build(name="Dasha", longitudes=longitudes, **kwargs)
    return build_from_data(build_chart(data), data)


# --- The scheme -------------------------------------------------------------------------------


def test_the_nine_lords_sum_to_one_hundred_and_twenty_years():
    assert len(VIMSHOTTARI_YEARS) == 9
    assert sum(VIMSHOTTARI_YEARS.values()) == TOTAL_YEARS


def test_the_order_matches_the_nakshatra_lord_cycle():
    """The dasha sequence and the 27 nakshatra lords are the same cycle repeated. That is
    what makes the balance computable from the Moon's longitude, so if normalise.py's table
    is ever re-sorted this fails loudly rather than producing plausible wrong dates."""
    assert tuple(nak.lord for nak in NAKSHATRAS[:9]) == VIMSHOTTARI_ORDER
    assert tuple(nak.lord for nak in NAKSHATRAS[9:18]) == VIMSHOTTARI_ORDER
    assert tuple(nak.lord for nak in NAKSHATRAS[18:]) == VIMSHOTTARI_ORDER


def test_year_length_is_the_declared_constant():
    """365.25 is why our dates differ by a day or two from software using 365.2425. The
    number is printed on the birth-details page, so it is pinned here."""
    assert YEAR_DAYS == 365.25


# --- Continuity: the dasha_continuity gate check, at the source --------------------------------


@pytest.mark.parametrize("key", CORPUS_IDS)
@pytest.mark.parametrize("level", [1, 2, 3])
def test_a_level_is_gap_free_end_to_end(timelines, key, level):
    """Each level tiles the whole timeline: every period ends exactly where the next begins,
    across Mahadasha boundaries as well as within them. This is the strongest form of the
    ``dasha_continuity`` check — no instant belongs to two periods or to none."""
    periods = timelines[key].at_level(level)
    for earlier, later in zip(periods, periods[1:], strict=False):
        assert earlier.end == later.start, f"gap or overlap at level {level}"


@pytest.mark.parametrize("key", CORPUS_IDS)
@pytest.mark.parametrize("level", [1, 2, 3])
def test_every_level_spans_the_same_interval(timelines, key, level):
    timeline = timelines[key]
    periods = timeline.at_level(level)
    assert periods[0].start == timeline.at_level(1)[0].start
    assert periods[-1].end == timeline.at_level(1)[-1].end


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_children_tile_their_parent_exactly(timelines, key):
    """Not 'approximately'. A microsecond gap here is a date that renders differently in two
    sections, which is the entire defect this module exists to prevent."""
    timeline = timelines[key]
    for parent in timeline.at_level(1) + timeline.at_level(2):
        children = timeline.children(parent)
        assert len(children) == 9
        assert children[0].start == parent.start
        assert children[-1].end == parent.end
        for earlier, later in zip(children, children[1:], strict=False):
            assert earlier.end == later.start


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_every_period_has_positive_duration(timelines, key):
    for period in timelines[key].periods:
        assert period.start < period.end


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_mahadashas_run_the_full_cycle_in_order(timelines, key):
    timeline = timelines[key]
    mahadashas = timeline.at_level(1)
    assert len(mahadashas) == 18
    assert mahadashas[0].lord is timeline.first_lord

    for period in mahadashas:
        expected = timedelta(days=VIMSHOTTARI_YEARS[period.lord] * YEAR_DAYS)
        assert period.end - period.start == expected


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_period_counts(timelines, key):
    timeline = timelines[key]
    assert len(timeline.at_level(1)) == 18
    assert len(timeline.at_level(2)) == 18 * 9
    assert len(timeline.at_level(3)) == 18 * 9 * 9


def test_sub_period_shares_are_proportional_to_the_lords_years():
    timeline = _timeline_for(0.0)
    maha = timeline.at_level(1)[0]
    for antar in timeline.children(maha):
        share = antar.duration_days / maha.duration_days
        assert share == pytest.approx(VIMSHOTTARI_YEARS[antar.lord] / TOTAL_YEARS, abs=1e-9)


# --- Balance at birth ---------------------------------------------------------------------------


def test_a_moon_at_the_start_of_a_nakshatra_gets_the_whole_period():
    """0° is the first minute of Ashwini, whose lord is Ketu. Nothing has elapsed, so the
    Mahadasha starts exactly at birth with all seven years to run."""
    timeline = _timeline_for(0.0)
    assert timeline.first_lord is Graha.KETU
    assert timeline.balance_years == pytest.approx(7.0)
    assert timeline.at_level(1)[0].start == timeline.birth


def test_a_moon_at_the_midpoint_of_a_nakshatra_gets_half_the_period():
    span = 360.0 / 27.0
    timeline = _timeline_for(span / 2)
    assert timeline.first_lord is Graha.KETU
    assert timeline.balance_years == pytest.approx(3.5)
    # The virtual start sits 3.5 years before birth, so the full seven-year span is preserved
    # and the elapsed Antardashas fall where they belong.
    first = timeline.at_level(1)[0]
    assert first.start == timeline.birth - timedelta(days=3.5 * YEAR_DAYS)
    assert first.end == timeline.birth + timedelta(days=3.5 * YEAR_DAYS)


def test_balance_matches_an_exact_rational_derivation(timelines):
    """Derived with Fraction rather than floats, so this is a genuinely independent check and
    not a restatement of the implementation. Floating-point ``lon % span`` is exactly what
    got the nakshatra boundary wrong in the first place."""
    from fractions import Fraction

    for key in CORPUS_IDS:
        timeline = timelines[key]
        position = Fraction(timeline.moon_longitude) * 27 / 360     # nakshatras from 0°
        index = position.numerator // position.denominator
        elapsed = position - index

        assert NAKSHATRAS[index].lord is timeline.first_lord, key
        expected = float(1 - elapsed) * VIMSHOTTARI_YEARS[timeline.first_lord]
        assert timeline.balance_years == pytest.approx(expected), key


def test_a_moon_exactly_on_a_nakshatra_boundary_starts_the_later_one(timelines):
    """The Kaal Sarp fixture's Moon lands on exactly 80°, the Ardra/Punarvasu join. Before
    the boundary fix in normalise.py this read as the last instant of Ardra with a zero
    balance, which shifted the whole timeline by a Mahadasha — a full 16 years of dasha
    dates, wrong, from a float rounding error."""
    timeline = timelines["kaal_sarp"]
    assert timeline.moon_longitude == 80.0
    assert timeline.first_lord is Graha.JUPITER
    assert timeline.balance_years == pytest.approx(16.0)
    assert timeline.at_level(1)[0].start == timeline.birth
    assert timeline.warnings == ()


def test_the_gandanta_moon_is_late_in_revati(timelines):
    """The Moon at 28.5° Pisces is 88.75% through Revati, so only about a fifth of Mercury's
    seventeen years remains — the case where an off-by-one in the balance is visible."""
    timeline = timelines["gandanta_moon"]
    assert timeline.first_lord is Graha.MERCURY
    assert timeline.balance_years == pytest.approx(1.9125, abs=1e-4)


def test_a_nearly_exhausted_first_mahadasha_is_warned_about():
    span = 360.0 / 27.0
    timeline = _timeline_for(span - 0.001)          # a hair from the end of Ashwini
    assert timeline.balance_years < 0.05
    assert any("Mahadasha balance at birth" in w for w in timeline.warnings)


# --- active_periods: the single accessor -------------------------------------------------------


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_active_periods_resolves_all_five_levels(timelines, key):
    active = timelines[key].active_periods(NOW)
    assert len(active.levels) == MAX_LEVEL
    for level, period in enumerate(active.levels, start=1):
        assert period.level == level
        assert period.contains(NOW)


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_each_level_is_nested_inside_the_one_above(timelines, key):
    active = timelines[key].active_periods(NOW)
    for outer, inner in zip(active.levels, active.levels[1:], strict=False):
        assert outer.start <= inner.start
        assert inner.end <= outer.end
        assert inner.parent_path == outer.path


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_active_periods_is_deterministic(timelines, key):
    timeline = timelines[key]
    assert timeline.active_periods(NOW) == timeline.active_periods(NOW)


def test_two_timelines_from_the_same_data_agree():
    """Defect #1 restated: two consumers that each build a timeline must not disagree."""
    data = CORPUS["rashi_sandhi"]
    a = build_from_data(build_chart(data), data).active_periods(NOW)
    b = build_from_data(build_chart(data), data).active_periods(NOW)
    assert a.label(depth=5) == b.label(depth=5)
    assert a.levels == b.levels


def test_boundaries_are_half_open(timelines):
    """An instant exactly on a boundary belongs to the period starting there, not the one
    ending there. Closed intervals would put it in both, and which one you got would depend
    on iteration order."""
    timeline = timelines["kaal_sarp"]
    boundary = timeline.at_level(1)[3].start
    assert timeline.active_periods(boundary).maha == timeline.at_level(1)[3]
    just_before = boundary - timedelta(microseconds=1)
    assert timeline.active_periods(just_before).maha == timeline.at_level(1)[2]


def test_at_birth_the_running_mahadasha_is_the_moons_nakshatra_lord(timelines):
    for key in CORPUS_IDS:
        timeline = timelines[key]
        active = timeline.active_periods(timeline.birth)
        assert active.maha.lord is timeline.first_lord, key


def test_a_naive_datetime_is_rejected(timelines):
    with pytest.raises(DashaError, match="timezone-aware"):
        timelines["pre_1970"].active_periods(datetime(2026, 7, 31))


def test_an_instant_outside_the_timeline_is_rejected(timelines):
    timeline = timelines["pre_1970"]
    with pytest.raises(DashaError, match="outside the computed timeline"):
        timeline.active_periods(timeline.birth - timedelta(days=365 * 50))


def test_a_non_utc_aware_datetime_is_converted_not_rejected(timelines):
    timeline = timelines["kaal_sarp"]
    ist = timezone(timedelta(hours=5, minutes=30))
    same_instant = NOW.astimezone(ist)
    assert timeline.active_periods(same_instant).levels == timeline.active_periods(NOW).levels


# --- Labels: the one sanctioned rendering --------------------------------------------------------


def test_label_depth_and_language(timelines):
    active = timelines["vargottama"].active_periods(NOW)
    assert active.label(depth=1) == active.maha.lord.value
    assert active.label(depth=3).count("–") == 2
    assert active.label(depth=5).count("–") == 4
    assert active.label("hi", depth=3) == "–".join(g.hi for g in active.lords[:3])


def test_label_rejects_an_out_of_range_depth(timelines):
    active = timelines["vargottama"].active_periods(NOW)
    for depth in (0, 6):
        with pytest.raises(DashaError):
            active.label(depth=depth)


def test_at_level_rejects_unmaterialised_levels(timelines):
    timeline = timelines["vargottama"]
    with pytest.raises(DashaError, match="materialised"):
        timeline.at_level(EAGER_LEVELS + 1)


def test_level_names_are_bilingual(timelines):
    active = timelines["vargottama"].active_periods(NOW)
    assert active.maha.level_name("en") == "Mahadasha"
    assert active.maha.level_name("hi") == "महादशा"
    assert active.prana.level_name("en") == "Prana"


# --- Transitions ------------------------------------------------------------------------------------


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_next_12_transitions_stay_inside_the_window(timelines, key):
    horizon = NOW + timedelta(days=YEAR_DAYS)
    transitions = timelines[key].next_12_transitions(NOW)
    assert transitions
    for period in transitions:
        assert period.level in (2, 3)
        assert NOW <= period.start < horizon


def test_next_12_transitions_rejects_a_naive_datetime(timelines):
    with pytest.raises(DashaError, match="timezone-aware"):
        timelines["kaal_sarp"].next_12_transitions(datetime(2026, 7, 31))


def test_antardashas_are_scoped_by_period_not_by_lord(timelines):
    """The timeline runs two 120-year cycles, so each lord holds two Mahadashas and
    ``parent_path`` alone cannot tell them apart. ``children()`` takes the actual period, so
    it never merges the two."""
    timeline = timelines["kaal_sarp"]
    first_lord = timeline.first_lord
    same_lord = [p for p in timeline.at_level(1) if p.lord is first_lord]
    assert len(same_lord) == 2
    assert same_lord[0].start != same_lord[1].start

    scoped = timeline.children(same_lord[0])
    assert len(scoped) == 9
    assert all(p.start < same_lord[1].start for p in scoped)
    assert len(timeline.antardashas()) == len(timeline.at_level(2))


# --- Birth instant -------------------------------------------------------------------------------------


def test_birth_datetime_applies_the_request_offset():
    data = CORPUS["pre_1970"]
    birth = birth_datetime(data.request)
    assert birth.tzinfo is UTC
    # 1962-03-14 04:55 IST is 1962-03-13 23:25 UTC.
    assert birth == datetime(1962, 3, 13, 23, 25, tzinfo=UTC)


def test_birth_datetime_handles_a_non_indian_offset():
    birth = birth_datetime(CORPUS["polar_birth"].request)
    assert birth == datetime(1985, 12, 21, 10, 0, tzinfo=UTC)


def test_birth_datetime_rejects_impossible_input():
    data = CORPUS["pre_1970"].model_copy(deep=True)
    data.request.month = 13
    with pytest.raises(DashaError, match="Unusable birth"):
        birth_datetime(data.request)


def test_build_timeline_rejects_a_naive_birth():
    chart = build_chart(CORPUS["kaal_sarp"])
    with pytest.raises(DashaError, match="timezone-aware"):
        build_timeline(chart, datetime(1990, 6, 15))


# --- Cross-check against the API -----------------------------------------------------------------------


def test_parse_api_datetime_handles_both_formats():
    assert parse_api_datetime("15-8-1990 14:30", 5.5) == datetime(1990, 8, 15, 9, 0, tzinfo=UTC)
    assert parse_api_datetime("16-8-2012", 5.5) == datetime(2012, 8, 15, 18, 30, tzinfo=UTC)
    assert parse_api_datetime("", 5.5) is None
    assert parse_api_datetime("not a date", 5.5) is None


def _with_api_mahadashas(data, entries):
    copy = data.model_copy(deep=True)
    copy.major_vdasha = entries
    return copy


def test_cross_check_reports_a_different_starting_lord_and_stops():
    """When the sequences are offset, pairing them by position would report a 46-year
    'divergence' for every lord. One accurate finding beats nine misleading ones."""
    data = CORPUS["kaal_sarp"]
    timeline = build_from_data(build_chart(data), data)
    wrong_lord = Graha.KETU if timeline.first_lord is not Graha.KETU else Graha.VENUS
    data = _with_api_mahadashas(
        data, [ApiDashaPeriod(planet=wrong_lord.value, start="15-6-1990", end="15-6-1997")]
    )

    findings = cross_check_against_api(timeline, data)
    assert len(findings) == 1
    assert "first Mahadasha lord" in findings[0]
    assert "not compared" in findings[0]


def test_cross_check_is_silent_when_the_api_agrees():
    data = CORPUS["kaal_sarp"]
    timeline = build_from_data(build_chart(data), data)
    offset = timedelta(hours=data.request.tzone)
    ours = timeline.at_level(1)

    entries = [
        ApiDashaPeriod(
            planet=period.lord.value,
            start=(period.start + offset).strftime("%d-%m-%Y"),
            end=(period.end + offset).strftime("%d-%m-%Y"),
        )
        for period in ours[:9]
    ]
    entries[0].start = timeline.birth.strftime("%d-%m-%Y")   # the API starts at birth

    assert cross_check_against_api(timeline, _with_api_mahadashas(data, entries)) == ()


def test_cross_check_flags_a_diverging_balance():
    data = CORPUS["kaal_sarp"]
    timeline = build_from_data(build_chart(data), data)
    offset = timedelta(hours=data.request.tzone)
    ours = timeline.at_level(1)

    entries = [
        ApiDashaPeriod(
            planet=period.lord.value,
            start=(period.start + offset).strftime("%d-%m-%Y"),
            end=(period.end + offset).strftime("%d-%m-%Y"),
        )
        for period in ours[:9]
    ]
    entries[0].start = timeline.birth.strftime("%d-%m-%Y")
    entries[0].end = (ours[0].end + offset + timedelta(days=40)).strftime("%d-%m-%Y")

    findings = cross_check_against_api(timeline, _with_api_mahadashas(data, entries))
    assert any("Balance of the" in f for f in findings)


def test_cross_check_is_a_no_op_without_api_data():
    data = CORPUS["kaal_sarp"]
    timeline = build_from_data(build_chart(data), data)
    assert cross_check_against_api(timeline, data) == ()


def test_cross_check_catches_the_demo_datas_own_inconsistency():
    """demo_data's hand-written Mahadasha table starts with Ketu, but its hand-written Moon
    is in a Jupiter nakshatra. The two have always disagreed; this is what noticing it looks
    like rather than rendering both."""
    from demo_data import SAMPLE_KUNDLI_DATA

    timeline = build_from_data(build_chart(SAMPLE_KUNDLI_DATA), SAMPLE_KUNDLI_DATA)
    findings = cross_check_against_api(timeline, SAMPLE_KUNDLI_DATA)
    assert len(findings) == 1
    assert "Ketu" in findings[0] and "Jupiter" in findings[0]
