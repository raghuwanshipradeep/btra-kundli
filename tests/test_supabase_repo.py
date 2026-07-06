from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from tenacity import wait_none

import supabase_repo
from config import settings
from models import KundliRequest

SUPA_URL = "https://test.supabase.co"
SERVICE_KEY = "test-service-role-key"
TABLE = "kundli_orders"
ENDPOINT = f"{SUPA_URL}/rest/v1/{TABLE}"


def _request() -> KundliRequest:
    return KundliRequest(
        name="Test User",
        day=15, month=8, year=1990,
        hour=14, min=30,
        lat=23.1765, lon=75.7885, tzone=5.5,
        lang="en",
        phone="9999999999", email="t@example.com", gender="Male",
        place="Ujjain", state="MP", pincode="456001",
    )


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", SUPA_URL)
    monkeypatch.setattr(settings, "supabase_service_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "supabase_table", TABLE)
    # Strip tenacity backoff so the retry test runs instantly (no real sleeps).
    monkeypatch.setattr(supabase_repo._request.retry, "wait", wait_none())


@pytest.fixture
def unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_key", "")


@respx.mock
@pytest.mark.asyncio
async def test_skips_when_unconfigured(unconfigured) -> None:
    route = respx.post(ENDPOINT).mock(return_value=Response(201))
    ok = await supabase_repo.record_order_created(_request(), "order_1", 9900)
    assert ok is False
    assert not route.called  # never hits the network when unconfigured


@respx.mock
@pytest.mark.asyncio
async def test_record_order_created_inserts(configured) -> None:
    route = respx.post(ENDPOINT).mock(return_value=Response(201))
    ok = await supabase_repo.record_order_created(_request(), "order_1", 9900)

    assert ok is True
    assert route.called
    req = route.calls.last.request
    assert req.headers["apikey"] == SERVICE_KEY
    assert req.headers["Authorization"] == f"Bearer {SERVICE_KEY}"
    body = json.loads(req.content)
    assert body["order_id"] == "order_1"
    assert body["status"] == "created"
    assert body["amount_paise"] == 9900
    assert body["amount_rupees"] == 99
    assert body["name"] == "Test User"
    assert body["phone"] == "9999999999"
    assert body["date_of_birth"] == "15 Aug 1990"


@respx.mock
@pytest.mark.asyncio
async def test_record_order_created_swallows_conflict(configured) -> None:
    # A 409 means the row already exists (a faster paid-write won the race).
    # That is not a failure — created must not clobber a later status.
    route = respx.post(ENDPOINT).mock(
        return_value=Response(409, json={"message": "duplicate key value"})
    )
    ok = await supabase_repo.record_order_created(_request(), "order_1", 9900)
    assert ok is True
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_record_order_paid_upserts(configured) -> None:
    route = respx.post(ENDPOINT).mock(return_value=Response(201))
    ok = await supabase_repo.record_order_paid(_request(), "order_1", "pay_1")

    assert ok is True
    req = route.calls.last.request
    assert "merge-duplicates" in req.headers["Prefer"]
    assert req.url.params["on_conflict"] == "order_id"
    body = json.loads(req.content)
    assert body["status"] == "paid"
    assert body["payment_id"] == "pay_1"
    assert "paid_at" in body


@respx.mock
@pytest.mark.asyncio
async def test_record_job_status_archived(configured) -> None:
    route = respx.post(ENDPOINT).mock(return_value=Response(201))
    ok = await supabase_repo.record_job_status(
        _request(), "order_1", "archived",
        drive_file_id="file123", drive_link="https://drive/x", elapsed_s=12.3,
    )

    assert ok is True
    body = json.loads(route.calls.last.request.content)
    assert body["status"] == "archived"
    assert body["drive_file_id"] == "file123"
    assert body["drive_link"] == "https://drive/x"
    assert body["elapsed_s"] == 12.3


@respx.mock
@pytest.mark.asyncio
async def test_never_raises_on_server_error(configured) -> None:
    route = respx.post(ENDPOINT).mock(return_value=Response(500, text="boom"))
    ok = await supabase_repo.record_order_paid(_request(), "order_1", "pay_1")
    assert ok is False
    assert route.call_count == 3  # retried, then gave up — never raised
