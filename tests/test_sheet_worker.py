from __future__ import annotations

import pytest

import main
from config import settings


# --- pure helpers ----------------------------------------------------------

def test_parse_dob_ok() -> None:
    assert main._parse_dob("1990-08-15") == (1990, 8, 15)
    assert main._parse_dob("2001-1-5") == (2001, 1, 5)


@pytest.mark.parametrize("bad", [None, "", "not-a-date", "1990-13-01", "1990-08-40"])
def test_parse_dob_skips(bad) -> None:
    with pytest.raises(main._SkipRow):
        main._parse_dob(bad)


def test_parse_tob_ok() -> None:
    assert main._parse_tob("14:30:00") == (14, 30)
    assert main._parse_tob("2:05") == (2, 5)


@pytest.mark.parametrize("bad", [None, "", "noon", "25:00", "12:99"])
def test_parse_tob_skips(bad) -> None:
    with pytest.raises(main._SkipRow):
        main._parse_tob(bad)


@pytest.mark.parametrize(
    "value,expected",
    [("Hindi", "hi"), ("hindi", "hi"), ("HINDI", "hi"),
     ("English", "en"), ("english", "en"), ("", "en"), (None, "en"),
     ("Marathi", "en")],
)
def test_lang_from_report_language(value, expected) -> None:
    assert main._lang_from_report_language(value) == expected


def test_dedup_by_order_id() -> None:
    rows = [
        {"order_id": "A", "name": "first"},
        {"order_id": "A", "name": "edited"},   # duplicate id -> dropped
        {"order_id": "B", "name": "other"},
        {"order_id": None, "name": "no id"},   # no order_id -> dropped
        {"order_id": "", "name": "blank id"},  # blank -> dropped
    ]
    out = main._dedup_by_order_id(rows)
    assert [r["order_id"] for r in out] == ["A", "B"]
    assert out[0]["name"] == "first"  # keeps the first row for an id


# --- row -> KundliRequest ---------------------------------------------------

def _row() -> dict:
    return {
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
        "payment_status": "SUCCESSFUL",
        "kundli_attempts": 0,
    }


@pytest.mark.asyncio
async def test_sheet_row_to_request_maps_fields(monkeypatch) -> None:
    async def fake_tzone(*a, **k):
        return 5.5
    monkeypatch.setattr(main, "_lookup_tzone", fake_tzone)

    req = await main._sheet_row_to_request(_row())
    assert (req.year, req.month, req.day) == (1990, 8, 15)
    assert (req.hour, req.min) == (14, 30)
    assert req.lat == 23.1765 and req.lon == 75.7885
    assert req.tzone == 5.5
    assert req.lang == "hi"
    assert req.name == "Asha Devi"
    assert req.place == "Ujjain"
    assert req.pincode == "456001"
    assert req.report_tier == "detailed"


@pytest.mark.asyncio
async def test_sheet_row_to_request_skips_missing_time(monkeypatch) -> None:
    async def fake_tzone(*a, **k):
        return 5.5
    monkeypatch.setattr(main, "_lookup_tzone", fake_tzone)

    row = _row()
    row["time_of_birth"] = None
    with pytest.raises(main._SkipRow):
        await main._sheet_row_to_request(row)


@pytest.mark.asyncio
async def test_sheet_row_to_request_skips_missing_latlon(monkeypatch) -> None:
    async def fake_tzone(*a, **k):
        return 5.5
    monkeypatch.setattr(main, "_lookup_tzone", fake_tzone)

    row = _row()
    row["latitude"] = None
    with pytest.raises(main._SkipRow):
        await main._sheet_row_to_request(row)


# --- orchestration ----------------------------------------------------------

@pytest.mark.asyncio
async def test_process_sheet_orders_dedups_and_is_sequential(monkeypatch) -> None:
    calls: list[str] = []

    two_A = [dict(_row(), order_id="A"), dict(_row(), order_id="A", name="edited")]
    one_B = [dict(_row(), order_id="B")]

    async def fake_fetch(limit):
        return two_A + one_B

    async def fake_reclaim(_):
        return None

    async def fake_claim(order_id, attempts):
        calls.append(f"claim:{order_id}")
        return True

    async def fake_tzone(*a, **k):
        return 5.5

    async def fake_build(request, order_id):
        calls.append(f"build:{order_id}")
        return b"%PDF-", f"{order_id}.pdf"

    async def fake_upload(**kwargs):
        calls.append(f"upload:{kwargs['order_id']}")
        return {"id": f"file_{kwargs['order_id']}", "webViewLink": f"link/{kwargs['order_id']}"}

    async def fake_done(order_id, file_id, link):
        calls.append(f"done:{order_id}")
        return True

    monkeypatch.setattr(main.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(main.sheet_repo, "reclaim_stale", fake_reclaim)
    monkeypatch.setattr(main.sheet_repo, "claim", fake_claim)
    monkeypatch.setattr(main.sheet_repo, "mark_done", fake_done)
    monkeypatch.setattr(main, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(main, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(main, "upload_kundli_pdf", fake_upload)

    summary = await main._process_sheet_orders(limit=50)

    assert summary["processed"] == 2
    assert summary["skipped"] == 0
    assert summary["failed"] == 0
    # A generated (once, despite the duplicate row) and fully saved before B starts.
    assert calls == [
        "claim:A", "build:A", "upload:A", "done:A",
        "claim:B", "build:B", "upload:B", "done:B",
    ]


@pytest.mark.asyncio
async def test_process_sheet_orders_marks_skip_permanent(monkeypatch) -> None:
    marks: list[tuple] = []

    async def fake_fetch(limit):
        bad = dict(_row(), order_id="X")
        bad["date_of_birth"] = None  # unparseable -> _SkipRow
        return [bad]

    async def fake_noop(*a, **k):
        return None

    async def fake_claim(order_id, attempts):
        return True

    async def fake_failed(order_id, error, *, permanent):
        marks.append((order_id, permanent))
        return True

    monkeypatch.setattr(main.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(main.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(main.sheet_repo, "claim", fake_claim)
    monkeypatch.setattr(main.sheet_repo, "mark_failed", fake_failed)

    summary = await main._process_sheet_orders(limit=50)
    assert summary["skipped"] == 1
    assert marks == [("X", True)]  # bad data -> permanent, never retried


@pytest.mark.asyncio
async def test_claim_failure_skips_generation(monkeypatch) -> None:
    """If the DB isn't writable (claim fails), we must NOT generate — an unrecorded PDF would
    regenerate next run. Gate generation on the claim landing."""
    built = []

    async def fake_fetch(limit):
        return [dict(_row(), order_id="A")]

    async def fake_noop(*a, **k):
        return None

    async def fake_claim_fail(order_id, attempts):
        return False  # DB write refused (e.g. missing UPDATE grant)

    async def fake_build(request, order_id):
        built.append(order_id)
        return b"%PDF-", f"{order_id}.pdf"

    monkeypatch.setattr(main.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(main.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(main.sheet_repo, "claim", fake_claim_fail)
    monkeypatch.setattr(main, "_build_kundli_pdf", fake_build)

    summary = await main._process_sheet_orders(limit=50)
    assert built == []  # generation never ran
    assert summary["processed"] == 0
    assert summary["failed"] == 1
    assert summary["details"][0]["result"] == "claim_failed"


@pytest.mark.asyncio
async def test_mark_done_failure_is_not_reported_as_processed(monkeypatch) -> None:
    """A PDF that uploads but can't be recorded must surface as archived_unmarked, never as a
    silent success — otherwise the summary lies and the row regenerates."""
    async def fake_fetch(limit):
        return [dict(_row(), order_id="A")]

    async def fake_noop(*a, **k):
        return None

    async def fake_ok(*a, **k):
        return True

    async def fake_tzone(*a, **k):
        return 5.5

    async def fake_build(request, order_id):
        return b"%PDF-", f"{order_id}.pdf"

    async def fake_upload(**kwargs):
        return {"id": "file_A", "webViewLink": "link/A"}

    async def fake_mark_done_fail(order_id, file_id, link):
        return False  # write refused after the upload already succeeded

    monkeypatch.setattr(main.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(main.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(main.sheet_repo, "claim", fake_ok)
    monkeypatch.setattr(main.sheet_repo, "mark_done", fake_mark_done_fail)
    monkeypatch.setattr(main, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(main, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(main, "upload_kundli_pdf", fake_upload)

    summary = await main._process_sheet_orders(limit=50)
    assert summary["processed"] == 0
    assert summary["failed"] == 1
    assert summary["details"][0]["result"] == "archived_unmarked"
    assert summary["details"][0]["drive_link"] == "link/A"


@pytest.mark.asyncio
async def test_endpoint_requires_admin_key(monkeypatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "admin_key", "secret")
    with pytest.raises(HTTPException) as exc:
        await main.process_sheet_orders_endpoint(x_admin_key="wrong", limit=10)
    assert exc.value.status_code == 401
