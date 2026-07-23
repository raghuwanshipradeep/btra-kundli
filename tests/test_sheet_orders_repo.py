from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from tenacity import wait_none

import sheet_orders_repo
from config import settings

SUPA_URL = "https://test.supabase.co"
SERVICE_KEY = "test-service-role-key"
TABLE = "sheet_orders"
ENDPOINT = f"{SUPA_URL}/rest/v1/{TABLE}"


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", SUPA_URL)
    monkeypatch.setattr(settings, "supabase_service_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "sheet_orders_table", TABLE)
    monkeypatch.setattr(settings, "sheet_orders_kundli_max_attempts", 3)
    # Strip tenacity backoff so retry tests run instantly.
    monkeypatch.setattr(sheet_orders_repo._get.retry, "wait", wait_none())
    monkeypatch.setattr(sheet_orders_repo._patch.retry, "wait", wait_none())
    monkeypatch.setattr(sheet_orders_repo._patch_returning.retry, "wait", wait_none())


@pytest.fixture
def unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_service_key", "")


@respx.mock
@pytest.mark.asyncio
async def test_fetch_pending_query_params(configured) -> None:
    route = respx.get(ENDPOINT).mock(return_value=Response(200, json=[{"order_id": "o1"}]))
    rows = await sheet_orders_repo.fetch_pending(50)

    assert rows == [{"order_id": "o1"}]
    params = route.calls.last.request.url.params
    assert params["order_id"] == "not.is.null"
    assert params["payment_status"] == "ilike.success*"
    assert params["or"] == "(kundli_status.is.null,kundli_status.eq.failed)"
    assert params["kundli_attempts"] == "lt.3"
    assert params["order"] == "sheet_row.asc"
    assert params["limit"] == "50"
    # service_role auth is present
    assert route.calls.last.request.headers["apikey"] == SERVICE_KEY


@respx.mock
@pytest.mark.asyncio
async def test_fetch_pending_unconfigured(unconfigured) -> None:
    route = respx.get(ENDPOINT).mock(return_value=Response(200, json=[]))
    rows = await sheet_orders_repo.fetch_pending(50)
    assert rows == []
    assert not route.called


@respx.mock
@pytest.mark.asyncio
async def test_claim_is_conditional_and_bumps_attempts(configured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(200, json=[{"order_id": "order_9"}]))
    ok = await sheet_orders_repo.claim("order_9", attempts=1)

    assert ok is True
    req = route.calls.last.request
    assert req.url.params["order_id"] == "eq.order_9"
    # The claimable-status precondition is what makes the claim atomic across processes.
    assert req.url.params["or"] == "(kundli_status.is.null,kundli_status.eq.failed)"
    assert req.headers["prefer"] == "return=representation"
    body = json.loads(req.content)
    assert body["kundli_status"] == "generating"
    assert body["kundli_attempts"] == 2


@respx.mock
@pytest.mark.asyncio
async def test_claim_lost_when_already_claimed(configured) -> None:
    # Another process set kundli_status='generating' first: the precondition filter
    # matches zero rows, PostgREST returns an empty representation -> claim lost.
    route = respx.patch(ENDPOINT).mock(return_value=Response(200, json=[]))
    ok = await sheet_orders_repo.claim("order_9", attempts=0)
    assert ok is False
    assert route.called


@respx.mock
@pytest.mark.asyncio
async def test_claim_false_on_server_error(configured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(500, text="boom"))
    ok = await sheet_orders_repo.claim("order_9", attempts=0)
    assert ok is False
    assert route.call_count == 3  # retried, then gave up — never raised


@respx.mock
@pytest.mark.asyncio
async def test_claim_unconfigured(unconfigured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(200, json=[]))
    ok = await sheet_orders_repo.claim("order_9", attempts=0)
    assert ok is False
    assert not route.called


@respx.mock
@pytest.mark.asyncio
async def test_mark_done_sets_archived_and_drive(configured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(204))
    ok = await sheet_orders_repo.mark_done("order_9", "file123", "https://drive/x")

    assert ok is True
    body = json.loads(route.calls.last.request.content)
    assert body["kundli_status"] == "archived"
    assert body["kundli_drive_file_id"] == "file123"
    assert body["kundli_drive_link"] == "https://drive/x"
    assert body["kundli_error"] is None
    assert "kundli_generated_at" in body


@respx.mock
@pytest.mark.asyncio
async def test_mark_failed_permanent_vs_retryable(configured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(204))

    await sheet_orders_repo.mark_failed("order_9", "boom", permanent=False)
    assert json.loads(route.calls.last.request.content)["kundli_status"] == "failed"

    await sheet_orders_repo.mark_failed("order_9", "boom", permanent=True)
    assert json.loads(route.calls.last.request.content)["kundli_status"] == "failed_permanent"


@respx.mock
@pytest.mark.asyncio
async def test_mark_never_raises_on_server_error(configured) -> None:
    route = respx.patch(ENDPOINT).mock(return_value=Response(500, text="boom"))
    ok = await sheet_orders_repo.mark_done("order_9", "f", "l")
    assert ok is False
    assert route.call_count == 3  # retried, then gave up — never raised
