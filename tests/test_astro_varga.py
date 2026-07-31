"""Tests for app/astro/varga.py.

Two things these pin down. First, that a divisional chart the API failed to return lowers the
*confidence* in the score and not the score itself — a planet must never look weak because a
network call failed. Second, that varga dignity is judged at sign level, so the natal degree
cannot leak into a division where it has no meaning.
"""
from __future__ import annotations

import pytest

from app.astro.chart import build_chart
from app.astro.enums import Dignity, Graha, Rashi
from app.astro.varga import (
    DIGNITY_FACTOR,
    VIMSHOPAKA_TOTAL,
    VIMSHOPAKA_WEIGHTS,
    build_vargas,
    parse_varga_chart,
    varga_dignity,
)
from models import HoroChartSign
from tests.fixtures.synthetic import CORPUS, VARGOTTAMA, horo_chart

CORPUS_IDS = sorted(CORPUS)


@pytest.fixture(scope="module")
def vargottama_set():
    data = VARGOTTAMA
    return build_vargas(build_chart(data), data.horo_charts)


# --- The scheme itself ----------------------------------------------------------------------


def test_weights_are_sixteen_divisions_summing_to_twenty():
    assert len(VIMSHOPAKA_WEIGHTS) == 16
    assert sum(VIMSHOPAKA_WEIGHTS.values()) == pytest.approx(VIMSHOPAKA_TOTAL)


def test_the_heaviest_divisions_are_d60_d1_and_d9():
    """If a future edit reweights the table, this is the sanity line: Shastiamsa, Rashi and
    Navamsa carry more than half the total between them."""
    top = sorted(VIMSHOPAKA_WEIGHTS.items(), key=lambda kv: -kv[1])[:3]
    assert [varga for varga, _ in top] == ["D60", "D1", "D9"]
    assert sum(weight for _, weight in top) > VIMSHOPAKA_TOTAL / 2


def test_dignity_factor_covers_every_dignity_and_is_monotonic():
    assert set(DIGNITY_FACTOR) == set(Dignity)
    assert DIGNITY_FACTOR[Dignity.EXALTED] == 1.0
    assert DIGNITY_FACTOR[Dignity.DEBILITATED] == 0.0
    ordered = sorted(Dignity, key=lambda d: -d.rank)
    factors = [DIGNITY_FACTOR[d] for d in ordered]
    assert factors == sorted(factors, reverse=True)


# --- Sign-level dignity ---------------------------------------------------------------------


def test_varga_dignity_ignores_the_moolatrikona_degree_split():
    """In the natal chart the Moon past 3° Taurus is Moolatrikona. A varga sign has no
    degree, so within a division the Moon in Taurus is simply exalted."""
    signs = {Graha.MOON: Rashi.TAURUS, Graha.VENUS: Rashi.TAURUS}
    assert varga_dignity(Graha.MOON, Rashi.TAURUS, signs) is Dignity.EXALTED
    assert varga_dignity(Graha.MERCURY, Rashi.VIRGO, {Graha.MERCURY: Rashi.VIRGO}) is Dignity.EXALTED
    assert Dignity.MOOLATRIKONA not in {
        varga_dignity(g, s, {g: s}) for g in Graha for s in Rashi
    }


def test_varga_dignity_uses_the_divisions_own_temporal_relations():
    """Panchadha Maitri's temporal half must be computed inside the varga being judged, not
    from the natal positions — otherwise every division returns the same answer."""
    near = {Graha.SATURN: Rashi.GEMINI, Graha.MERCURY: Rashi.CANCER}
    far = {Graha.SATURN: Rashi.GEMINI, Graha.MERCURY: Rashi.SAGITTARIUS}
    assert varga_dignity(Graha.SATURN, Rashi.GEMINI, near) != varga_dignity(
        Graha.SATURN, Rashi.GEMINI, far
    )


def test_nodes_are_neutral_outside_their_declared_signs():
    assert varga_dignity(Graha.RAHU, Rashi.LEO, {Graha.RAHU: Rashi.LEO}) is Dignity.NEUTRAL
    assert varga_dignity(Graha.KETU, Rashi.TAURUS, {Graha.KETU: Rashi.TAURUS}) is Dignity.DEBILITATED


# --- Parsing the API payload -----------------------------------------------------------------


def test_parse_reads_sign_ids_and_separates_the_lagna():
    rows = horo_chart({"Ascendant": 7, "Sun": 5, "Moon": 5, "Saturn": 11})
    chart = parse_varga_chart("D9", rows)

    assert chart is not None
    assert chart.lagna_sign is Rashi.LIBRA
    assert chart.signs[Graha.SUN] is Rashi.LEO
    assert chart.signs[Graha.SATURN] is Rashi.AQUARIUS
    assert Graha.MARS not in chart.signs


def test_parse_accepts_hindi_planet_names():
    """The API returns Devanagari when lang=hi, and the divisional endpoints are no exception."""
    rows = [
        HoroChartSign(sign=5, sign_name="Leo", planet=["सूर्य", "बुध"]),
        HoroChartSign(sign=1, sign_name="Aries", planet=["लग्न"]),
    ]
    chart = parse_varga_chart("D9", rows)

    assert chart is not None
    assert chart.signs[Graha.SUN] is Rashi.LEO
    assert chart.signs[Graha.MERCURY] is Rashi.LEO
    assert chart.lagna_sign is Rashi.ARIES


def test_parse_returns_none_for_an_empty_chart():
    """An empty chart scored as neutral is indistinguishable from a real one — so it must
    not become a chart at all."""
    assert parse_varga_chart("D9", []) is None
    assert parse_varga_chart("D9", None) is None
    assert parse_varga_chart("D9", horo_chart({})) is None


def test_parse_skips_unrecognised_bodies():
    rows = [HoroChartSign(sign=3, sign_name="Gemini", planet=["Sun", "Uranus", ""])]
    chart = parse_varga_chart("D30", rows)

    assert chart is not None
    assert list(chart.signs) == [Graha.SUN]


def test_house_within_a_varga():
    chart = parse_varga_chart("D10", horo_chart({"Ascendant": 10, "Sun": 12, "Mars": 10}))
    assert chart.house_of(Graha.SUN) == 3      # Pisces from a Capricorn varga-Lagna
    assert chart.house_of(Graha.MARS) == 1
    assert chart.house_of(Graha.VENUS) is None


def test_house_is_none_without_a_varga_lagna():
    chart = parse_varga_chart("D10", horo_chart({"Sun": 12}))
    assert chart.lagna_sign is None
    assert chart.house_of(Graha.SUN) is None


# --- Assembly ---------------------------------------------------------------------------------


def test_d1_always_comes_from_the_natal_chart(vargottama_set):
    """Even when horo_charts carries a D1, the longitude-derived natal chart wins — it is the
    single source of truth for Rashi positions and it always has a Lagna."""
    natal = build_chart(VARGOTTAMA)
    data = VARGOTTAMA.model_copy(deep=True)
    data.horo_charts = dict(data.horo_charts or {})
    data.horo_charts["D1"] = horo_chart({"Sun": 1, "Moon": 1, "Ascendant": 1})

    result = build_vargas(natal, data.horo_charts)
    assert result.charts["D1"].signs[Graha.SUN] is Rashi.LEO
    assert result.charts["D1"].lagna_sign is natal.lagna.sign


def test_missing_divisions_are_listed(vargottama_set):
    assert set(vargottama_set.missing) == set(VIMSHOPAKA_WEIGHTS) - {"D1", "D9", "D10", "D12"}
    assert vargottama_set.scored_weight == pytest.approx(3.5 + 3.0 + 0.5 + 0.5)


def test_vargottama_detected(vargottama_set):
    assert vargottama_set.is_vargottama(Graha.SUN) is True
    assert vargottama_set.is_vargottama(Graha.SATURN) is False
    assert vargottama_set.vargottama_grahas() == (Graha.SUN,)


def test_vargottama_is_none_when_d9_is_absent():
    """Not False. Saying "not vargottama" about a planet nobody checked is defect #6 one
    layer down: a computed-looking answer with no computation behind it."""
    result = build_vargas(build_chart(VARGOTTAMA), {})
    assert result.is_vargottama(Graha.SUN) is None
    assert result.vargottama_grahas() == ()


def _uniform_set(natal, sign_for: dict[Graha, int]):
    """A VargaSet where all 15 fetched divisions place the planets identically."""
    charts = {
        varga: horo_chart({g.value: s for g, s in sign_for.items()} | {"Ascendant": 1})
        for varga in VIMSHOPAKA_WEIGHTS
        if varga != "D1"
    }
    return build_vargas(natal, charts)


def _natal_with(**placements: float):
    """A natal chart with the given absolute longitudes, defaults filled in."""
    from tests.fixtures.synthetic import build, deg

    longitudes = {
        "Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": deg(2, 10.0),
        "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Jupiter": deg(5, 10.0),
        "Venus": deg(6, 10.0), "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0),
        "Ketu": deg(2, 10.0),
    }
    longitudes.update(placements)
    return build_chart(build(name="Uniform", longitudes=longitudes))


def test_a_planet_exalted_in_all_sixteen_divisions_scores_the_full_twenty():
    from tests.fixtures.synthetic import deg

    natal = _natal_with(Sun=deg(1, 10.0))          # Sun exalted in Aries natally too
    result = _uniform_set(natal, {Graha.SUN: 1})

    assert result.dignities(Graha.SUN)["D1"] is Dignity.EXALTED
    assert result.missing == ()
    assert result.vimshopaka_bala(Graha.SUN) == pytest.approx(VIMSHOPAKA_TOTAL)


def test_a_planet_debilitated_in_all_sixteen_divisions_scores_zero():
    from tests.fixtures.synthetic import deg

    natal = _natal_with(Moon=deg(8, 14.0))         # Moon debilitated in Scorpio
    result = _uniform_set(natal, {Graha.MOON: 8})

    assert set(result.dignities(Graha.MOON).values()) == {Dignity.DEBILITATED}
    assert result.vimshopaka_bala(Graha.MOON) == 0.0


def test_score_is_scaled_by_covered_weight_not_penalised_for_missing_charts():
    """The same dignities over fewer divisions must give the same score — that is what
    'scaled, not penalised' means."""
    natal = build_chart(VARGOTTAMA)                       # this Sun is in Leo — own sign
    full = _uniform_set(natal, {Graha.SUN: 1})            # exalted in all 15 fetched divisions
    partial = build_vargas(natal, {"D9": horo_chart({"Sun": 1, "Ascendant": 1})})

    # Both sets are "own in D1, exalted everywhere available". Only the denominator differs.
    expected_partial = (3.5 * DIGNITY_FACTOR[Dignity.OWN] + 3.0 * 1.0) / 6.5 * VIMSHOPAKA_TOTAL
    expected_full = (
        (3.5 * DIGNITY_FACTOR[Dignity.OWN] + 16.5 * 1.0) / VIMSHOPAKA_TOTAL * VIMSHOPAKA_TOTAL
    )
    assert partial.vimshopaka_bala(Graha.SUN) == pytest.approx(expected_partial, abs=0.01)
    assert full.vimshopaka_bala(Graha.SUN) == pytest.approx(expected_full, abs=0.01)
    assert partial.scored_weight == pytest.approx(6.5)
    assert full.scored_weight == pytest.approx(VIMSHOPAKA_TOTAL)


def test_a_set_with_only_d1_still_scores():
    result = build_vargas(build_chart(VARGOTTAMA), None)
    assert result.scored_weight == pytest.approx(3.5)
    assert 0.0 <= result.vimshopaka_bala(Graha.SUN) <= VIMSHOPAKA_TOTAL
    assert len(result.missing) == 15


@pytest.mark.parametrize("key", CORPUS_IDS)
def test_every_corpus_chart_yields_scores_in_range(key):
    data = CORPUS[key]
    result = build_vargas(build_chart(data), data.horo_charts)

    assert "D1" in result.charts
    table = result.vimshopaka_table()
    assert set(table) == set(Graha)
    for graha, score in table.items():
        assert 0.0 <= score <= VIMSHOPAKA_TOTAL, graha


def test_vimshopaka_table_omits_grahas_the_chart_lacks():
    from tests.fixtures.synthetic import build, deg

    longitudes = {
        "Ascendant": deg(1, 5.0), "Sun": deg(1, 10.0), "Moon": deg(2, 10.0),
        "Mars": deg(3, 10.0), "Mercury": deg(4, 10.0), "Venus": deg(6, 10.0),
        "Saturn": deg(7, 10.0), "Rahu": deg(8, 10.0), "Ketu": deg(2, 10.0),
    }
    chart = build_chart(build(name="No Jupiter", longitudes=longitudes))
    result = build_vargas(chart, None)

    assert Graha.JUPITER not in result.vimshopaka_table()
    assert result.vimshopaka_bala(Graha.JUPITER) == 0.0
