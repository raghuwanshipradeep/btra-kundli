from __future__ import annotations

import pytest

from sheet_mapper import map_sheet_row


def _row(**over) -> dict:
    base = {
        "order_id": "order_1",
        "name": "Asha Devi",
        "phone": "9999999999",
        "email": "asha@example.com",
        "gender": "Female",
        "state": "MP",
        "pin_code": "456001",
        "place_of_birth": "Ujjain",
        "date_of_birth": "1990-08-15",
        "time_of_birth": "14:30:00",
        "latitude": 23.1765,
        "longitude": 75.7885,
        "report_language": "Hindi",
    }
    base.update(over)
    return base


def _ok(row: dict):
    req, err = map_sheet_row(row)
    assert err is None, err
    assert req is not None
    return req


# --- happy path -------------------------------------------------------------

def test_maps_all_fields() -> None:
    req = _ok(_row())
    assert (req.year, req.month, req.day) == (1990, 8, 15)
    assert (req.hour, req.min) == (14, 30)
    assert req.lat == 23.1765 and req.lon == 75.7885
    assert req.lang == "hi"
    assert req.name == "Asha Devi"
    assert req.place == "Ujjain"
    assert req.pincode == "456001"
    assert req.report_tier == "detailed"
    # tzone is a placeholder the worker overwrites via an async lookup.
    assert req.tzone == 0.0


def test_blank_name_defaults_native() -> None:
    assert _ok(_row(name="   ")).name == "Native"


def test_phone_preserved_as_string() -> None:
    assert _ok(_row(phone="09876543210")).phone == "09876543210"


# --- date -------------------------------------------------------------------

def test_date_ok_variants() -> None:
    assert _ok(_row(date_of_birth="2001-1-5")).day == 5


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "1990-13-01", "1990-08-40"])
def test_bad_date_returns_error(bad) -> None:
    req, err = map_sheet_row(_row(date_of_birth=bad))
    assert req is None and err and "date_of_birth" in err


# --- time -------------------------------------------------------------------

def test_time_ok_variants() -> None:
    assert (_ok(_row(time_of_birth="2:05")).hour, _ok(_row(time_of_birth="2:05")).min) == (2, 5)


@pytest.mark.parametrize("bad", [None, "", "noon", "25:00", "12:99"])
def test_bad_time_returns_error(bad) -> None:
    req, err = map_sheet_row(_row(time_of_birth=bad))
    assert req is None and err and "time_of_birth" in err


# --- lat/lon ----------------------------------------------------------------

def test_missing_lat_returns_error() -> None:
    req, err = map_sheet_row(_row(latitude=None))
    assert req is None and err and "latitude" in err


def test_missing_lon_returns_error() -> None:
    req, err = map_sheet_row(_row(longitude=None))
    assert req is None and err and "longitude" in err


# --- language (current behavior: unknown/blank -> en) -----------------------

@pytest.mark.parametrize(
    "value,expected",
    [("Hindi", "hi"), ("hindi", "hi"), ("HINDI", "hi"),
     ("English", "en"), ("english", "en"), ("", "en"), (None, "en"),
     ("Marathi", "en")],
)
def test_language(value, expected) -> None:
    assert _ok(_row(report_language=value)).lang == expected
