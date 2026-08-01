"""Tests for sections/varga.py — the divisional-sign formulas used to draw the
North Indian diamond for each varga chart.

The point of these is the D5 (Panchamsa) case. D5 used to be unmodelled, so
`varga_sign` fell through to a generic guess, the self-validation in
`sections/divisional_charts._varga_lagna_sign` rejected it, no diamond was drawn,
and the Hindi report rendered the chart completely blank (the API's inline SVG is
discarded for Hindi because its Devanagari is unshapeable in WeasyPrint).

The expected values below are the AstrologyAPI's own placements for a real
nativity (11-11-1994 02:30, Ambala), so they pin our formula to the convention the
upstream API actually uses rather than to a textbook we picked.
"""
from __future__ import annotations

import pytest

from sections.varga import varga_sign

# longitude -> varga sign, straight from /horo_chart/{D} for one real chart.
API_PLACEMENTS = {
    5: {
        204.45176404313014: 11,   # Sun
        301.87692721468704: 3,    # Moon
        115.18396388596051: 8,    # Mars
        186.67246324714043: 8,    # Mercury
        209.91003202725840: 11,   # Jupiter
        192.01268424919570: 9,    # Venus
        311.89293291807553: 4,    # Saturn
        200.68655491367180: 10,   # Rahu
        20.686554913671785: 4,    # Ketu
    },
    # A division that was already modelled — guards against a regression in the
    # shared part-index maths while D5 was being added.
    7: {
        204.45176404313014: 12,
        301.87692721468704: 11,
        115.18396388596051: 3,
        186.67246324714043: 8,
        209.91003202725840: 1,
        192.01268424919570: 9,
        311.89293291807553: 1,
        200.68655491367180: 11,
        20.686554913671785: 5,
    },
}


@pytest.mark.parametrize("division", sorted(API_PLACEMENTS))
def test_matches_the_api_convention_for_every_planet(division: int) -> None:
    """Every planet must match — that is exactly the bar _varga_lagna_sign() applies
    before it will trust the formula enough to draw a diamond."""
    mismatches = [
        (lon, expected, varga_sign(lon, division))
        for lon, expected in API_PLACEMENTS[division].items()
        if varga_sign(lon, division) != expected
    ]
    assert not mismatches, f"D{division} disagrees with the API: {mismatches}"


def test_panchamsa_uses_trines_from_the_sign() -> None:
    """Movable -> 1st, fixed -> 5th, dual -> 9th. 0° of each modality lands on its
    own trine start, which is what makes the whole D5 mapping hang together."""
    assert varga_sign(0.0, 5) == 1     # 0° Aries, movable -> Aries
    assert varga_sign(120.0, 5) == 9   # 0° Leo, fixed -> Sagittarius (Leo + 4)
    assert varga_sign(150.0, 5) == 2   # 0° Virgo, dual -> Taurus (Virgo + 8)


def test_each_panchamsa_part_advances_one_sign() -> None:
    """Five 6° parts within one sign step forward one sign each."""
    got = [varga_sign(0.0 + 6.0 * i + 1.0, 5) for i in range(5)]
    assert got == [1, 2, 3, 4, 5]


def test_unmodelled_division_still_returns_a_sign() -> None:
    """The generic fallback must stay in range so the self-validation gate can
    reject it cleanly instead of blowing up. D8's upstream data is degenerate, so
    it is expected to keep failing validation and fall back to the data table."""
    for lon in (0.0, 95.5, 359.9):
        assert 1 <= varga_sign(lon, 8) <= 12


def test_invalid_input_returns_none() -> None:
    assert varga_sign(None, 5) is None
    assert varga_sign(10.0, 0) is None
