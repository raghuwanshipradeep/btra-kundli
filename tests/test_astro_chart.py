"""Tests for app/astro/chart.py — the KundliData -> Chart adapter.

The theme running through these is LAW 1: the longitude is the fact, and the API's own
sign/nakshatra/house strings are opinions to be cross-checked. Several tests deliberately
feed a *wrong* label and assert that the derived value is unmoved and a warning is recorded.
"""
from __future__ import annotations

import pytest

from app.astro.chart import ChartDataError, build_chart
from app.astro.enums import SAPTA_GRAHA, SAV_TOTAL, Dignity, Graha, Rashi
from app.astro.normalise import NAKSHATRA_SPAN
from models import HouseData, KundliData
from tests.fixtures.synthetic import CORPUS, build, deg

CORPUS_ITEMS = sorted(CORPUS.items())
CORPUS_IDS = [key for key, _ in CORPUS_ITEMS]


@pytest.fixture(scope="module")
def charts():
    return {key: build_chart(data) for key, data in CORPUS_ITEMS}


# --- Invariants that must hold on every chart in the corpus --------------------------------


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_all_nine_grahas_present(charts, key):
    assert set(charts[key].planets) == set(Graha)


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_degrees_and_longitudes_in_range(charts, key):
    """The gate's ``degrees_in_range`` check, asserted at the source rather than on HTML."""
    chart = charts[key]
    for position in chart.planets.values():
        assert 0.0 <= position.longitude < 360.0
        assert 0.0 <= position.degree_in_sign < 30.0
        assert 1 <= position.house <= 12
        assert 1 <= position.pada <= 4
    assert 0.0 <= chart.lagna.longitude < 360.0
    assert 0.0 <= chart.lagna.degree_in_sign < 30.0


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_sav_totals_337(charts, key):
    assert charts[key].ashtakavarga is not None
    assert charts[key].ashtakavarga.sav_total == SAV_TOTAL


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_nakshatra_trio_fully_populated(charts, key):
    """The ``nakshatra_complete`` gate check. 'Details unavailable' must be unreachable."""
    trio = charts[key].nakshatras
    for label, reading in trio.as_dict().items():
        assert reading.nakshatra is not None, label
        assert reading.nakshatra.en
        assert reading.nakshatra.hi
        assert reading.lord in Graha
        assert 1 <= reading.pada <= 4


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_trio_matches_the_bodies_it_claims_to_describe(charts, key):
    chart = charts[key]
    assert chart.nakshatras.janma.longitude == chart.moon.longitude
    assert chart.nakshatras.surya.longitude == chart.sun.longitude
    assert chart.nakshatras.lagna.longitude == chart.lagna.longitude


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_corpus_builds_without_warnings(charts, key):
    """The fixtures are internally consistent, so any warning here is an adapter bug."""
    assert charts[key].warnings == ()


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_houses_are_whole_sign_from_lagna(charts, key):
    chart = charts[key]
    assert len(chart.houses) == 12
    for index, house in enumerate(chart.houses, start=1):
        assert house.number == index
        expected = ((chart.lagna.sign.value - 1 + index - 1) % 12) + 1
        assert house.sign == Rashi(expected)
        assert house.lord == house.sign.lord


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_occupants_partition_the_grahas(charts, key):
    """Every graha appears in exactly one house's occupant list — no drops, no duplicates."""
    chart = charts[key]
    seen = [g for house in chart.houses for g in house.occupants]
    assert sorted(seen, key=lambda g: g.value) == sorted(Graha, key=lambda g: g.value)
    for house in chart.houses:
        for graha in house.occupants:
            assert chart.planets[graha].house == house.number


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_lord_house_agrees_with_the_lord_position(charts, key):
    chart = charts[key]
    for house in chart.houses:
        assert house.lord_house == chart.planets[house.lord].house


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_build_is_deterministic(key):
    """Same input, same output — the premise the golden-file snapshots will rest on."""
    first, second = build_chart(CORPUS[key]), build_chart(CORPUS[key])
    assert first.planets == second.planets
    assert first.houses == second.houses
    assert first.lagna == second.lagna


# --- Derivation from longitude, not from labels --------------------------------------------


def test_sign_and_nakshatra_come_from_longitude(charts):
    chart = charts["rashi_sandhi"]
    venus = chart.planets[Graha.VENUS]
    assert venus.longitude == pytest.approx(60.02)
    assert venus.sign is Rashi.GEMINI
    assert venus.degree_in_sign == pytest.approx(0.02)
    assert venus.nakshatra.en == "Mrigashira"


def test_a_wrong_api_nakshatra_label_warns_but_does_not_win():
    data = build(
        name="Bad Label",
        longitudes={"Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": deg(2, 10.0),
                    "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Jupiter": deg(5, 10.0),
                    "Venus": deg(6, 10.0), "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0),
                    "Ketu": deg(2, 10.0)},
    )
    moon = next(p for p in data.planets if p.name == "Moon")
    moon.nakshatra = "Revati"           # the truth at 40° is Krittika

    chart = build_chart(data)
    assert chart.planets[Graha.MOON].nakshatra.en == "Krittika"
    assert any("API says nakshatra Revati" in w for w in chart.warnings)


def test_an_unresolvable_api_nakshatra_label_warns():
    """Defect #7's own input — a misspelt key — is reported, never rendered."""
    data = build(
        name="Unresolvable",
        longitudes={"Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": deg(2, 10.0),
                    "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Jupiter": deg(5, 10.0),
                    "Venus": deg(6, 10.0), "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0),
                    "Ketu": deg(2, 10.0)},
    )
    next(p for p in data.planets if p.name == "Sun").nakshatra = "Qwerty"

    chart = build_chart(data)
    assert chart.planets[Graha.SUN].nakshatra.en == "Ashwini"
    assert any("did not resolve" in w for w in chart.warnings)


def test_a_wrong_api_house_warns_but_does_not_win():
    data = CORPUS["kaal_sarp"].model_copy(deep=True)
    next(p for p in data.planets if p.name == "Mars").house = 11

    chart = build_chart(data)
    assert chart.planets[Graha.MARS].house == 3      # Cancer from a Taurus Lagna
    assert any("API house 11" in w for w in chart.warnings)


def test_retro_is_read_as_a_string_not_a_truthiness():
    """``isRetro`` is "false", which is a non-empty string. A bare ``if entry.isRetro``
    would make every planet in every chart retrograde."""
    chart = build_chart(CORPUS["gandanta_moon"])
    assert chart.planets[Graha.SUN].is_retrograde is False
    assert chart.planets[Graha.RAHU].is_retrograde is True


# --- Missing data --------------------------------------------------------------------------


def _full(**overrides) -> dict[str, float]:
    longitudes = {
        "Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": deg(2, 10.0),
        "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Jupiter": deg(5, 10.0),
        "Venus": deg(6, 10.0), "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0),
        "Ketu": deg(2, 10.0),
    }
    longitudes.update(overrides)
    return longitudes


def test_ketu_is_derived_from_rahu_when_absent():
    longitudes = _full()
    longitudes.pop("Ketu")
    chart = build_chart(build(name="No Ketu", longitudes=longitudes))

    rahu = chart.planets[Graha.RAHU].longitude
    assert chart.planets[Graha.KETU].longitude == pytest.approx((rahu + 180.0) % 360.0)
    assert any("Ketu absent" in w for w in chart.warnings)


def test_a_present_ketu_is_never_overwritten():
    chart = build_chart(CORPUS["pre_1970"])
    assert chart.planets[Graha.KETU].longitude == pytest.approx(deg(10, 22.0))
    assert not any("Ketu absent" in w for w in chart.warnings)


@pytest.mark.parametrize("missing", ["Ascendant", "Sun", "Moon"])
def test_the_three_load_bearing_bodies_fail_closed(missing):
    """LAW 3. Without a Lagna there are no house numbers; without the Moon there is no dasha;
    without the Sun there is no combustion. A partial report here would be wrong, not thin."""
    longitudes = _full()
    longitudes.pop(missing)
    with pytest.raises(ChartDataError):
        build_chart(build(name=f"No {missing}", longitudes=longitudes))


def test_a_missing_graha_degrades_rather_than_raising():
    longitudes = _full()
    longitudes.pop("Jupiter")
    chart = build_chart(build(name="No Jupiter", longitudes=longitudes))

    assert Graha.JUPITER not in chart.planets
    assert any("Jupiter absent" in w for w in chart.warnings)
    assert chart.ashtakavarga is None
    assert any("Ashtakavarga skipped" in w for w in chart.warnings)
    # The 12 houses still exist; Jupiter's two lordships simply have no placement, which is
    # reported as None rather than silently defaulting to house 1.
    assert len(chart.houses) == 12
    jupiter_houses = [h for h in chart.houses if h.lord is Graha.JUPITER]
    assert len(jupiter_houses) == 2
    assert all(h.lord_house is None for h in jupiter_houses)
    assert all(h.lord_house is not None for h in chart.houses if h.lord is not Graha.JUPITER)


def test_lagna_recovered_from_the_houses_response():
    longitudes = _full()
    longitudes.pop("Ascendant")
    data = build(name="Lagna via houses", longitudes=longitudes)
    data = KundliData(
        request=data.request,
        planets=data.planets,
        houses=[HouseData(house_id=1, sign="Aries", sign_id=1, degree=5.0, sign_lord="Mars")],
    )

    chart = build_chart(data)
    assert chart.lagna.sign is Rashi.ARIES
    assert chart.lagna.degree_in_sign == pytest.approx(5.0)
    assert any("houses response" in w for w in chart.warnings)


def test_outer_bodies_are_skipped_without_noise():
    """``planets_extended`` carries Uranus, Neptune and Pluto. None of the 29 spec sections
    discusses them, and an 'unrecognised body' warning on every chart would be noise."""
    from demo_data import SAMPLE_KUNDLI_DATA

    chart = build_chart(SAMPLE_KUNDLI_DATA)
    assert set(chart.planets) == set(Graha)
    assert not any("Unrecognised body" in w for w in chart.warnings)


# --- Values the report will actually print -------------------------------------------------


def test_gandanta_is_flagged_at_the_water_fire_junction(charts):
    moon = charts["gandanta_moon"].planets[Graha.MOON]
    assert moon.sign is Rashi.PISCES
    assert moon.is_gandanta is True
    assert moon.needs_hedging is True


def test_rashi_sandhi_is_flagged_at_both_edges(charts):
    chart = charts["rashi_sandhi"]
    assert chart.planets[Graha.VENUS].is_rashi_sandhi is True     # 0°01' into Gemini
    assert chart.planets[Graha.JUPITER].is_rashi_sandhi is True   # exactly 0°00' Sagittarius
    assert chart.planets[Graha.MOON].is_rashi_sandhi is False     # 25° Aquarius


def test_combustion_uses_a_per_planet_orb(charts):
    """A single hardcoded orb cannot pass this: the Moon is combust at 9° while Jupiter,
    18° away in the previous sign, is not."""
    chart = charts["combustion_cluster"]
    assert chart.planets[Graha.MOON].is_combust is True
    assert chart.planets[Graha.MOON].combustion.limit == pytest.approx(12.0)
    assert chart.planets[Graha.MERCURY].is_combust is True
    assert chart.planets[Graha.JUPITER].is_combust is False
    assert chart.planets[Graha.SUN].is_combust is False


def test_retrograde_venus_takes_the_tighter_orb(charts):
    venus = charts["combustion_cluster"].planets[Graha.VENUS]
    assert venus.is_retrograde is True
    assert venus.combustion.limit == pytest.approx(8.0)
    assert venus.combustion.orb == pytest.approx(6.0)
    assert venus.is_combust is True


def test_nodes_are_never_combust(charts):
    for key in CORPUS_IDS:
        for node in (Graha.RAHU, Graha.KETU):
            assert charts[key].planets[node].is_combust is False


def test_exaltation_does_not_swallow_the_moolatrikona_arc(charts):
    """Defect #2 in miniature: the Moon past 3° Taurus is Moolatrikona, not exalted. Calling
    the whole sign exalted is the narrative inflation Part 12 warns about."""
    split = charts["exaltation_split"]
    assert split.planets[Graha.MOON].degree_in_sign == pytest.approx(4.0)
    assert split.planets[Graha.MOON].dignity is Dignity.MOOLATRIKONA
    assert split.planets[Graha.MERCURY].dignity is Dignity.MOOLATRIKONA

    heavy = charts["debilitation_heavy"]
    assert heavy.planets[Graha.MOON].degree_in_sign == pytest.approx(2.0)
    assert heavy.planets[Graha.MOON].dignity is Dignity.EXALTED


def test_debilitations_are_named_as_such(charts):
    chart = charts["debilitation_heavy"]
    debilitated = {g for g, p in chart.planets.items() if p.dignity is Dignity.DEBILITATED}
    assert debilitated == {Graha.SUN, Graha.MARS, Graha.JUPITER, Graha.VENUS, Graha.SATURN}
    # Mars's dispositor is the exalted Moon in the 4th — a kendra. This is Neechabhanga
    # condition (a), which the yoga engine will have to name explicitly.
    assert chart.planets[Graha.MARS].sign.lord is Graha.MOON
    assert chart.planets[Graha.MOON].house == 4


def test_exaltation_orb_is_zero_at_the_deep_point(charts):
    chart = charts["gandanta_moon"]
    assert chart.planets[Graha.MARS].exaltation_orb == pytest.approx(0.0)
    assert chart.planets[Graha.JUPITER].exaltation_orb == pytest.approx(0.0)
    assert chart.planets[Graha.MOON].exaltation_orb is None


def test_pada_matches_the_longitude(charts):
    """Pada is a quarter of a 13°20' nakshatra, derived — never read off the API's field."""
    for key in CORPUS_IDS:
        for position in charts[key].planets.values():
            offset = position.longitude % NAKSHATRA_SPAN
            assert position.pada == min(int(offset // (NAKSHATRA_SPAN / 4)) + 1, 4)


def test_helper_accessors(charts):
    chart = charts["vargottama"]
    assert chart.sign_of(Graha.SUN) is Rashi.LEO
    assert chart.house_of(Graha.SUN) == 1
    assert Graha.SUN in chart.occupants_of(1)
    assert set(chart.longitudes()) == set(Graha)
    assert set(chart.signs()) == set(Graha)


def test_ashtakavarga_is_chart_specific(charts):
    """Defect #5: the per-planet totals are constants, so only the house-level matrix can
    distinguish two charts. At least one cell must differ."""
    a = charts["gandanta_moon"].ashtakavarga
    b = charts["kaal_sarp"].ashtakavarga
    assert any(a.bav[g].bindus != b.bav[g].bindus for g in SAPTA_GRAHA)
