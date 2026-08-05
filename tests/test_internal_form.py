"""Tests for the TEMPORARY /internal staff form and its gated generate endpoint.

Delete this file when the /internal routes are removed from main.py.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
from config import settings
from main import app
from models import KundliRequest


ADMIN_KEY = "test-admin-key-internal"
FAKE_PDF = b"%PDF-1.7 internal fake\n%%EOF"


def _request() -> KundliRequest:
    return KundliRequest(
        name="Asha Verma",
        day=15, month=8, year=1990,
        hour=14, min=30,
        lat=23.1765, lon=75.7885, tzone=5.5,
        phone="9876543210", email="asha@example.com",
    )


@pytest.fixture
def fake_pipeline(monkeypatch):
    """Replace the real pipeline so no AstrologyAPI/Anthropic credit is spent."""
    calls: list[KundliRequest] = []

    async def fake_build(request, order_id=""):
        calls.append(request)
        return FAKE_PDF, "First##Phone##Email.pdf"

    monkeypatch.setattr(main, "_build_kundli_pdf", fake_build)
    return calls


# --- auth gate --------------------------------------------------------------

@pytest.mark.asyncio
async def test_rejects_missing_admin_key(monkeypatch, fake_pipeline) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    with pytest.raises(HTTPException) as exc:
        await main.internal_generate_kundli(_request(), x_admin_key=None)
    assert exc.value.status_code == 401
    assert not fake_pipeline, "generation must not start without a valid key"


@pytest.mark.asyncio
async def test_rejects_wrong_admin_key(monkeypatch, fake_pipeline) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    with pytest.raises(HTTPException) as exc:
        await main.internal_generate_kundli(_request(), x_admin_key="nope")
    assert exc.value.status_code == 401
    assert not fake_pipeline


@pytest.mark.asyncio
async def test_rejects_when_admin_key_unset(monkeypatch, fake_pipeline) -> None:
    """An empty ADMIN_KEY must fail closed, not wave everyone through."""
    monkeypatch.setattr(settings, "admin_key", "")
    with pytest.raises(HTTPException) as exc:
        await main.internal_generate_kundli(_request(), x_admin_key="")
    assert exc.value.status_code == 401
    assert not fake_pipeline


# --- happy path -------------------------------------------------------------

@pytest.mark.asyncio
async def test_generates_pdf_with_valid_key(monkeypatch, fake_pipeline) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    resp = await main.internal_generate_kundli(_request(), x_admin_key=ADMIN_KEY)

    assert resp.media_type == "application/pdf"
    assert len(fake_pipeline) == 1
    body = b"".join([chunk async for chunk in resp.body_iterator])
    assert body == FAKE_PDF


@pytest.mark.asyncio
async def test_filename_leaks_no_contact_details(monkeypatch, fake_pipeline) -> None:
    """_build_kundli_pdf returns First##Phone##Email.pdf; the download must not use it."""
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    resp = await main.internal_generate_kundli(_request(), x_admin_key=ADMIN_KEY)

    disposition = resp.headers["content-disposition"]
    assert "kundli_Asha Verma_1990.pdf" in disposition
    assert "9876543210" not in disposition
    assert "asha@example.com" not in disposition
    assert "##" not in disposition


@pytest.mark.asyncio
async def test_blank_name_still_yields_a_filename(monkeypatch, fake_pipeline) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    req = _request()
    req.name = "!!!"  # sanitizes to empty
    resp = await main.internal_generate_kundli(req, x_admin_key=ADMIN_KEY)
    assert "kundli_report_1990.pdf" in resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_timeout_returns_504(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "generation_timeout_seconds", 0.01)

    async def slow_build(request, order_id=""):
        await asyncio.sleep(5)

    monkeypatch.setattr(main, "_build_kundli_pdf", slow_build)
    with pytest.raises(HTTPException) as exc:
        await main.internal_generate_kundli(_request(), x_admin_key=ADMIN_KEY)
    assert exc.value.status_code == 504


# --- over HTTP --------------------------------------------------------------
# The tests above call the handler directly, which passes x_admin_key by hand and so
# cannot catch a mis-named header parameter. These go through the real request path.

def test_header_wiring_over_http(monkeypatch, fake_pipeline) -> None:
    monkeypatch.setattr(settings, "admin_key", ADMIN_KEY)
    body = _request().model_dump()
    with TestClient(app) as client:
        assert client.post("/internal/generate-kundli", json=body).status_code == 401
        assert client.post(
            "/internal/generate-kundli", json=body, headers={"X-Admin-Key": "wrong"}
        ).status_code == 401

        ok = client.post(
            "/internal/generate-kundli", json=body, headers={"X-Admin-Key": ADMIN_KEY}
        )
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "application/pdf"
    assert ok.content == FAKE_PDF


# --- the /internal page, and the guarantee that "/" is untouched ------------

def test_internal_page_serves_the_form() -> None:
    with TestClient(app) as client:
        resp = client.get("/internal")
    assert resp.status_code == 200
    assert 'id="kundliForm"' in resp.text


def test_internal_page_is_the_same_document_as_root() -> None:
    """One copy of the form: /internal must not drift from /."""
    with TestClient(app) as client:
        assert client.get("/internal").text == client.get("/").text


def test_payment_config_still_enabled_with_razorpay_keys(monkeypatch) -> None:
    """Regression guard: adding /internal must not let "/" fall into free mode."""
    monkeypatch.setattr(settings, "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(settings, "razorpay_key_secret", "secret_x")
    with TestClient(app) as client:
        cfg = client.get("/api/payment-config").json()
    assert cfg["enabled"] is True


def test_public_generate_kundli_still_gated(monkeypatch, fake_pipeline) -> None:
    """The unauthenticated endpoint must stay closed — /internal is not a way in."""
    monkeypatch.setattr(settings, "allow_free_generation", False)
    with TestClient(app) as client:
        resp = client.post("/generate-kundli", json=_request().model_dump())
    assert resp.status_code == 403
    assert not fake_pipeline
