from __future__ import annotations

import pytest

import credits_repo
import drive_uploader
import main
import sheet_worker
from config import settings


@pytest.fixture(autouse=True)
def _credits_off(monkeypatch: pytest.MonkeyPatch):
    """Keep the pre-existing sweeper tests on the unmetered path.

    Without this they would resolve a real astrologer over HTTP (the dev .env has Supabase
    configured). The credit tests at the bottom of this file opt back in explicitly.
    """
    monkeypatch.setattr(settings, "credit_check_enabled", False)


# --- amount-based Drive folder routing -------------------------------------

def test_folder_for_amount_routes_by_threshold(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_drive_folder_id", "DEFAULT")
    monkeypatch.setattr(settings, "google_drive_folder_id_premium", "PREMIUM")
    monkeypatch.setattr(settings, "drive_premium_amount_threshold", 499)

    # At/below the threshold (and null/unparseable) -> default folder.
    assert drive_uploader.folder_for_amount(499) == "DEFAULT"
    assert drive_uploader.folder_for_amount("499") == "DEFAULT"
    assert drive_uploader.folder_for_amount(299) == "DEFAULT"
    assert drive_uploader.folder_for_amount(None) == "DEFAULT"
    assert drive_uploader.folder_for_amount("abc") == "DEFAULT"
    # Above the threshold -> premium folder.
    assert drive_uploader.folder_for_amount(500) == "PREMIUM"
    assert drive_uploader.folder_for_amount(999) == "PREMIUM"
    assert drive_uploader.folder_for_amount("799.0") == "PREMIUM"


def test_folder_for_amount_default_when_premium_unset(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_drive_folder_id", "DEFAULT")
    monkeypatch.setattr(settings, "google_drive_folder_id_premium", "")
    # Routing disabled: even a big amount stays on the default folder.
    assert drive_uploader.folder_for_amount(9999) == "DEFAULT"


# --- pure helper ------------------------------------------------------------

def test_dedup_by_order_id() -> None:
    rows = [
        {"order_id": "A", "name": "first"},
        {"order_id": "A", "name": "edited"},   # duplicate id -> dropped
        {"order_id": "B", "name": "other"},
        {"order_id": None, "name": "no id"},   # no order_id -> dropped
        {"order_id": "", "name": "blank id"},  # blank -> dropped
    ]
    out = sheet_worker._dedup_by_order_id(rows)
    assert [r["order_id"] for r in out] == ["A", "B"]
    assert out[0]["name"] == "first"  # keeps the first row for an id


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


# --- orchestration ----------------------------------------------------------

@pytest.mark.asyncio
async def test_sweep_dedups_and_is_sequential(monkeypatch) -> None:
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

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_reclaim)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_claim)
    monkeypatch.setattr(sheet_worker.sheet_repo, "mark_done", fake_done)
    monkeypatch.setattr(sheet_worker, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(sheet_worker, "upload_kundli_pdf", fake_upload)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["processed"] == 2
    assert summary["skipped"] == 0
    assert summary["failed"] == 0
    # A generated (once, despite the duplicate row) and fully saved before B starts.
    assert calls == [
        "claim:A", "build:A", "upload:A", "done:A",
        "claim:B", "build:B", "upload:B", "done:B",
    ]


@pytest.mark.asyncio
async def test_sweep_routes_folder_by_amount(monkeypatch) -> None:
    """A >499 order archives to the premium folder; a 499 order to the default folder."""
    monkeypatch.setattr(settings, "google_drive_folder_id", "DEFAULT")
    monkeypatch.setattr(settings, "google_drive_folder_id_premium", "PREMIUM")
    monkeypatch.setattr(settings, "drive_premium_amount_threshold", 499)

    uploads: dict[str, str] = {}

    async def fake_fetch(limit):
        return [
            dict(_row(), order_id="hi", order_total_amount=999),
            dict(_row(), order_id="lo", order_total_amount=499),
        ]

    async def fake_noop(*a, **k):
        return None

    async def fake_ok(*a, **k):
        return True

    async def fake_tzone(*a, **k):
        return 5.5

    async def fake_build(request, order_id):
        return b"%PDF-", f"{order_id}.pdf"

    async def fake_upload(**kwargs):
        uploads[kwargs["order_id"]] = kwargs["folder_id"]
        return {"id": f"file_{kwargs['order_id']}", "webViewLink": "link"}

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_ok)
    monkeypatch.setattr(sheet_worker.sheet_repo, "mark_done", fake_ok)
    monkeypatch.setattr(sheet_worker, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(sheet_worker, "upload_kundli_pdf", fake_upload)

    summary = await sheet_worker.sweep_once(limit=50)
    assert summary["processed"] == 2
    assert uploads == {"hi": "PREMIUM", "lo": "DEFAULT"}


@pytest.mark.asyncio
async def test_sweep_marks_bad_data_permanent_without_spend(monkeypatch) -> None:
    marks: list[tuple] = []
    built: list[str] = []

    async def fake_fetch(limit):
        bad = dict(_row(), order_id="X")
        bad["date_of_birth"] = None  # unparseable -> map_sheet_row error
        return [bad]

    async def fake_noop(*a, **k):
        return None

    async def fake_claim(order_id, attempts):
        return True

    async def fake_failed(order_id, error, *, permanent):
        marks.append((order_id, permanent))
        return True

    async def fake_build(request, order_id):
        built.append(order_id)
        return b"%PDF-", "x.pdf"

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_claim)
    monkeypatch.setattr(sheet_worker.sheet_repo, "mark_failed", fake_failed)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)

    summary = await sheet_worker.sweep_once(limit=50)
    assert summary["skipped"] == 1
    assert marks == [("X", True)]  # bad data -> permanent, never retried
    assert built == []             # zero API spend


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

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_claim_fail)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)

    summary = await sheet_worker.sweep_once(limit=50)
    assert built == []  # generation never ran
    assert summary["processed"] == 0
    assert summary["failed"] == 1
    assert summary["details"][0]["result"] == "claim_failed"


@pytest.mark.asyncio
async def test_mark_done_failure_is_archived_unmarked(monkeypatch) -> None:
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

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_ok)
    monkeypatch.setattr(sheet_worker.sheet_repo, "mark_done", fake_mark_done_fail)
    monkeypatch.setattr(sheet_worker, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(sheet_worker, "upload_kundli_pdf", fake_upload)

    summary = await sheet_worker.sweep_once(limit=50)
    assert summary["processed"] == 0
    assert summary["failed"] == 1
    assert summary["details"][0]["result"] == "archived_unmarked"
    assert summary["details"][0]["drive_link"] == "link/A"


# --- endpoints --------------------------------------------------------------

@pytest.mark.asyncio
async def test_process_endpoint_requires_admin_key(monkeypatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "admin_key", "secret")
    with pytest.raises(HTTPException) as exc:
        await main.process_sheet_orders_endpoint(x_admin_key="wrong", limit=10)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_sheet_jobs_endpoint_requires_admin_key(monkeypatch) -> None:
    from fastapi import HTTPException

    monkeypatch.setattr(settings, "admin_key", "secret")
    with pytest.raises(HTTPException) as exc:
        await main.sheet_jobs_endpoint(x_admin_key="wrong", limit=10)
    assert exc.value.status_code == 401


# --- credit gating ----------------------------------------------------------

def _credit_sweep_stubs(monkeypatch, rows, calls):
    """Wire a sweep whose every step succeeds, recording the call order in `calls`."""
    async def fake_fetch(limit):
        return rows

    async def fake_noop(*a, **k):
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
        return {"id": "file", "webViewLink": "link"}

    async def fake_done(*a, **k):
        return True

    monkeypatch.setattr(sheet_worker.sheet_repo, "fetch_pending", fake_fetch)
    monkeypatch.setattr(sheet_worker.sheet_repo, "reclaim_stale", fake_noop)
    monkeypatch.setattr(sheet_worker.sheet_repo, "claim", fake_claim)
    monkeypatch.setattr(sheet_worker.sheet_repo, "mark_done", fake_done)
    monkeypatch.setattr(sheet_worker, "_lookup_tzone", fake_tzone)
    monkeypatch.setattr(sheet_worker, "_build_kundli_pdf", fake_build)
    monkeypatch.setattr(sheet_worker, "upload_kundli_pdf", fake_upload)


def _enable_credits(monkeypatch, balance, *, consume=(True, 9), spent=None):
    """Turn gating on with a stubbed balance. `spent` collects consume_credit order ids."""
    monkeypatch.setattr(settings, "credit_check_enabled", True)

    async def fake_resolve():
        return "astro-1"

    async def fake_balance(astrologer_id):
        return balance

    async def fake_consume(astrologer_id, order_id):
        if spent is not None:
            spent.append(order_id)
        return consume

    monkeypatch.setattr(credits_repo, "enabled", lambda: True)
    monkeypatch.setattr(credits_repo, "resolve_astrologer_id", fake_resolve)
    monkeypatch.setattr(credits_repo, "get_balance", fake_balance)
    monkeypatch.setattr(credits_repo, "consume_credit", fake_consume)


@pytest.mark.asyncio
async def test_zero_balance_blocks_before_any_spend(monkeypatch) -> None:
    """The whole point of gating before claim(): a blocked row costs nothing and stays pending."""
    calls: list[str] = []
    _credit_sweep_stubs(monkeypatch, [dict(_row(), order_id="A")], calls)
    _enable_credits(monkeypatch, balance=0)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["status"] == "no_credits"
    assert summary["credits_balance"] == 0
    assert summary["processed"] == 0
    # Never claimed and never built: kundli_status stays null, attempts untouched, no API spend.
    assert calls == []


@pytest.mark.asyncio
async def test_unknown_balance_fails_closed(monkeypatch) -> None:
    """A Supabase error (balance None) must block, not wave generation through."""
    calls: list[str] = []
    _credit_sweep_stubs(monkeypatch, [dict(_row(), order_id="A")], calls)
    _enable_credits(monkeypatch, balance=None)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["status"] == "no_credits"
    assert summary["credits_balance"] is None
    assert calls == []


@pytest.mark.asyncio
async def test_unresolvable_astrologer_skips_sweep(monkeypatch) -> None:
    calls: list[str] = []
    _credit_sweep_stubs(monkeypatch, [dict(_row(), order_id="A")], calls)
    monkeypatch.setattr(settings, "credit_check_enabled", True)
    monkeypatch.setattr(credits_repo, "enabled", lambda: True)

    async def no_astrologer():
        return None

    monkeypatch.setattr(credits_repo, "resolve_astrologer_id", no_astrologer)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["status"] == "no_astrologer"
    assert calls == []


@pytest.mark.asyncio
async def test_credit_spent_once_per_generated_order(monkeypatch) -> None:
    spent: list[str] = []
    calls: list[str] = []
    rows = [dict(_row(), order_id="A"), dict(_row(), order_id="B")]
    _credit_sweep_stubs(monkeypatch, rows, calls)
    _enable_credits(monkeypatch, balance=5, consume=(True, 4), spent=spent)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["processed"] == 2
    assert spent == ["A", "B"]  # exactly one credit per delivered PDF


@pytest.mark.asyncio
async def test_failed_deduction_still_archives_the_order(monkeypatch) -> None:
    """PDF is already in Drive — a ledger failure must never fail or refund the order."""
    calls: list[str] = []
    _credit_sweep_stubs(monkeypatch, [dict(_row(), order_id="A")], calls)
    _enable_credits(monkeypatch, balance=5, consume=(False, 0))

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["processed"] == 1
    assert summary["details"][0]["result"] == "archived"
    assert summary["credit_warnings"] == ["A"]


@pytest.mark.asyncio
async def test_disabled_gating_never_touches_credits(monkeypatch) -> None:
    """CREDIT_CHECK_ENABLED=false must behave exactly like the pre-credit sweeper."""
    calls: list[str] = []
    _credit_sweep_stubs(monkeypatch, [dict(_row(), order_id="A")], calls)

    async def boom(*a, **k):
        raise AssertionError("credit gating must not run when disabled")

    monkeypatch.setattr(settings, "credit_check_enabled", False)
    monkeypatch.setattr(credits_repo, "get_balance", boom)
    monkeypatch.setattr(credits_repo, "consume_credit", boom)

    summary = await sheet_worker.sweep_once(limit=50)

    assert summary["processed"] == 1
    assert "status" not in summary or summary["status"] == "ok"
    assert calls == ["claim:A", "build:A"]
