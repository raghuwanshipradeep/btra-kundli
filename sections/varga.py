"""Compute the divisional (varga) sign for a sidereal longitude.

The astrologyapi `/horo_chart/{D}` responses give planet placements but NOT the
varga ascendant, so we compute it locally from the D1 ascendant longitude using
classical Parashari (BPHS) rules. Callers self-validate the result against the
API's own planet placements before trusting it (see divisional_charts.py).

Signs are 1-12 (1 = Aries). Internally we work 0-indexed.
"""
from __future__ import annotations

# 0-indexed sign helpers
_MOVABLE, _FIXED, _DUAL = 0, 1, 2  # s % 3


def _mode(s: int) -> int:
    return s % 3


def _is_odd_sign(s: int) -> bool:
    # Aries (s=0) is the 1st / odd sign
    return s % 2 == 0


def _trimsamsa(s: int, x: float) -> int:
    """D30: five unequal segments; sign depends on odd/even rasi."""
    if _is_odd_sign(s):
        # Mars(Aries) Saturn(Aquarius) Jupiter(Sagittarius) Mercury(Gemini) Venus(Libra)
        bounds = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]
    else:
        # Venus(Taurus) Mercury(Virgo) Jupiter(Pisces) Saturn(Capricorn) Mars(Scorpio)
        bounds = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]
    for upper, sign in bounds:
        if x < upper:
            return sign
    return bounds[-1][1]


def varga_sign(full_longitude: float, n: int) -> int | None:
    """Return the varga sign (1-12) for a sidereal longitude and division n.

    Returns None for divisions we don't model (None lets the caller fall back).
    """
    if full_longitude is None or n <= 0:
        return None

    L = full_longitude % 360.0
    s = int(L // 30)          # 0-11
    x = L - s * 30.0          # 0-30 within sign

    if n == 1:
        return s + 1

    if n == 30:
        return _trimsamsa(s, x) + 1

    part = int(x * n / 30.0)  # 0 .. n-1
    if part >= n:
        part = n - 1

    if n == 2:  # Hora
        if _is_odd_sign(s):
            sign = 4 if part == 0 else 3   # Leo, Cancer
        else:
            sign = 3 if part == 0 else 4   # Cancer, Leo
        return sign + 1

    if n == 3:   # Drekkana
        return (s + 4 * part) % 12 + 1
    if n == 4:   # Chaturthamsa
        return (s + 3 * part) % 12 + 1
    if n == 5:   # Panchamsa — trines from the sign: movable 1st, fixed 5th, dual 9th.
        # Derived empirically from the API's own placements (movable +0 and fixed +4
        # both confirmed against a real chart); the dual offset completes the trine
        # and is covered by the caller's self-validation if this API disagrees.
        start = {_MOVABLE: s, _FIXED: (s + 4) % 12, _DUAL: (s + 8) % 12}[_mode(s)]
        return (start + part) % 12 + 1
    if n == 7:   # Saptamsa
        start = s if _is_odd_sign(s) else (s + 6) % 12
        return (start + part) % 12 + 1
    if n == 9:   # Navamsa
        start = {_MOVABLE: s, _FIXED: (s + 8) % 12, _DUAL: (s + 4) % 12}[_mode(s)]
        return (start + part) % 12 + 1
    if n == 10:  # Dasamsa
        start = s if _is_odd_sign(s) else (s + 8) % 12
        return (start + part) % 12 + 1
    if n == 12:  # Dwadasamsa
        return (s + part) % 12 + 1
    if n == 16:  # Shodasamsa
        start = {_MOVABLE: 0, _FIXED: 4, _DUAL: 8}[_mode(s)]
        return (start + part) % 12 + 1
    if n == 20:  # Vimsamsa
        start = {_MOVABLE: 0, _FIXED: 8, _DUAL: 4}[_mode(s)]
        return (start + part) % 12 + 1
    if n == 24:  # Siddhamsa / Chaturvimsamsa
        start = 4 if _is_odd_sign(s) else 3   # Leo / Cancer
        return (start + part) % 12 + 1
    if n == 27:  # Bhamsa / Nakshatramsa — by element (s % 4)
        start = {0: 0, 1: 3, 2: 6, 3: 9}[s % 4]
        return (start + part) % 12 + 1
    if n == 40:  # Khavedamsa
        start = 0 if _is_odd_sign(s) else 6   # Aries / Libra
        return (start + part) % 12 + 1
    if n == 45:  # Akshavedamsa
        start = {_MOVABLE: 0, _FIXED: 4, _DUAL: 8}[_mode(s)]
        return (start + part) % 12 + 1
    if n == 60:  # Shashtiamsa
        return (s + part) % 12 + 1

    # Unmodelled divisions (e.g. D5, D8): generic "from the sign itself".
    # Gated by the caller's self-validation, so a wrong guess just falls back.
    return (s + part) % 12 + 1
