from __future__ import annotations

import json

import pytest
import respx
from httpx import Response
from tenacity import wait_none

import credits_repo
from config import settings

SUPA_URL = "https://test.supabase.co"
SERVICE_KEY = "test-service-role-key"
ASTRO = f"{SUPA_URL}/rest/v1/astrologers"
CONSUME = f"{SUPA_URL}/rest/v1/rpc/consume_kundli_credit"
AID = "eca21ad2-a7c0-4245-986f-f8e50506c7d8"


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", SUPA_URL)
    monkeypatch.setattr(settings, "supabase_service_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "credit_check_enabled", True)
    # Strip tenacity backoff so retry tests run instantly.
    monkeypatch.setattr(credits_repo._get.retry, "wait", wait_none())
    monkeypatch.setattr(credits_repo._post.retry, "wait", wait_none())


@pytest.fixture
def killswitched(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "supabase_url", SUPA_URL)
    monkeypatch.setattr(settings, "supabase_service_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "credit_check_enabled", False)


# --- enablement -------------------------------------------------------------

def test_enabled_requires_supabase_and_switch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", SUPA_URL)
    monkeypatch.setattr(settings, "supabase_service_key", SERVICE_KEY)
    monkeypatch.setattr(settings, "credit_check_enabled", True)
    assert credits_repo.enabled() is True

    monkeypatch.setattr(settings, "credit_check_enabled", False)
    assert credits_repo.enabled() is False

    monkeypatch.setattr(settings, "credit_check_enabled", True)
    monkeypatch.setattr(settings, "supabase_url", "")
    assert credits_repo.enabled() is False


@respx.mock
@pytest.mark.asyncio
async def test_killswitch_makes_every_call_a_noop(killswitched) -> None:
    """CREDIT_CHECK_ENABLED=false is the rollback path: no HTTP, nothing blocks."""
    astro = respx.get(ASTRO).mock(return_value=Response(200, json=[]))
    rpc = respx.post(CONSUME).mock(return_value=Response(200, json=[]))

    assert await credits_repo.resolve_astrologer_id() is None
    assert await credits_repo.get_balance(AID) is None
    assert await credits_repo.consume_credit(AID, "o1") == (False, None)
    assert not astro.called
    assert not rpc.called


# --- resolving the astrologer ----------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_resolve_astrologer_filters_active(configured) -> None:
    route = respx.get(ASTRO).mock(
        return_value=Response(200, json=[{"id": AID, "name": "satyam", "credits_balance": 1000}])
    )
    assert await credits_repo.resolve_astrologer_id() == AID

    params = route.calls.last.request.url.params
    assert params["is_active"] == "eq.true"
    # created_at ordering is what makes the multi-astrologer fallback deterministic.
    assert params["order"] == "created_at.asc"
    assert params["limit"] == "2"
    assert route.calls.last.request.headers["apikey"] == SERVICE_KEY


@respx.mock
@pytest.mark.asyncio
async def test_resolve_astrologer_none_when_absent(configured) -> None:
    respx.get(ASTRO).mock(return_value=Response(200, json=[]))
    assert await credits_repo.resolve_astrologer_id() is None


@respx.mock
@pytest.mark.asyncio
async def test_resolve_astrologer_picks_oldest_when_several(configured) -> None:
    """Unexpected (system is single-astrologer), but generation must not halt over it."""
    respx.get(ASTRO).mock(
        return_value=Response(200, json=[{"id": "older"}, {"id": "newer"}])
    )
    assert await credits_repo.resolve_astrologer_id() == "older"


@respx.mock
@pytest.mark.asyncio
async def test_resolve_astrologer_none_on_server_error(configured) -> None:
    route = respx.get(ASTRO).mock(return_value=Response(500, text="boom"))
    assert await credits_repo.resolve_astrologer_id() is None
    assert route.call_count == 3  # retried, then gave up — never raised


# --- balance ----------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_get_balance_returns_int(configured) -> None:
    route = respx.get(ASTRO).mock(
        return_value=Response(200, json=[{"credits_balance": 1000, "is_active": True}])
    )
    assert await credits_repo.get_balance(AID) == 1000
    assert route.calls.last.request.url.params["id"] == f"eq.{AID}"


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_zero_is_zero_not_none(configured) -> None:
    """0 and None both block, but they mean different things and must stay distinct."""
    respx.get(ASTRO).mock(return_value=Response(200, json=[{"credits_balance": 0, "is_active": True}]))
    assert await credits_repo.get_balance(AID) == 0


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_none_when_inactive(configured) -> None:
    respx.get(ASTRO).mock(
        return_value=Response(200, json=[{"credits_balance": 500, "is_active": False}])
    )
    assert await credits_repo.get_balance(AID) is None


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_none_when_missing_row(configured) -> None:
    respx.get(ASTRO).mock(return_value=Response(200, json=[]))
    assert await credits_repo.get_balance(AID) is None


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_fails_closed_on_server_error(configured) -> None:
    """A Supabase blip must block generation, never wave it through."""
    route = respx.get(ASTRO).mock(return_value=Response(500, text="boom"))
    assert await credits_repo.get_balance(AID) is None
    assert route.call_count == 3


# --- consuming --------------------------------------------------------------

@respx.mock
@pytest.mark.asyncio
async def test_consume_credit_calls_rpc(configured) -> None:
    route = respx.post(CONSUME).mock(
        return_value=Response(200, json=[{"ok": True, "balance_after": 999}])
    )
    assert await credits_repo.consume_credit(AID, "order_9") == (True, 999)

    body = json.loads(route.calls.last.request.content)
    assert body["p_astrologer_id"] == AID
    assert body["p_order_id"] == "order_9"


@respx.mock
@pytest.mark.asyncio
async def test_consume_credit_false_when_out_of_credits(configured) -> None:
    respx.post(CONSUME).mock(return_value=Response(200, json=[{"ok": False, "balance_after": 0}]))
    assert await credits_repo.consume_credit(AID, "order_9") == (False, 0)


@respx.mock
@pytest.mark.asyncio
async def test_consume_credit_accepts_bare_object(configured) -> None:
    """PostgREST may return a single object rather than a one-row list."""
    respx.post(CONSUME).mock(return_value=Response(200, json={"ok": True, "balance_after": 42}))
    assert await credits_repo.consume_credit(AID, "order_9") == (True, 42)


@respx.mock
@pytest.mark.asyncio
async def test_consume_credit_never_raises(configured) -> None:
    route = respx.post(CONSUME).mock(return_value=Response(500, text="boom"))
    assert await credits_repo.consume_credit(AID, "order_9") == (False, None)
    assert route.call_count == 3
