from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient

import main
from config import settings
from main import app
from models import KundliRequest


WEBHOOK_SECRET = "test_webhook_secret_123"
ORDER_ID = "order_TESTwebhook01"
PAYMENT_ID = "pay_TESTwebhook01"


def _sample_request() -> KundliRequest:
    return KundliRequest(
        name="Test User",
        day=15, month=12, year=1986,
        hour=3, min=30,
        lat=22.05795, lon=78.93763, tzone=5.5,
        phone="9999999999", email="test@example.com",
    )


def _payload(event: str = "payment.captured", order_id: str = ORDER_ID) -> bytes:
    body = {
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": PAYMENT_ID,
                    "order_id": order_id,
                    "amount": settings.kundli_price_paise,
                    "status": "captured",
                }
            }
        },
    }
    return json.dumps(body).encode()


def _sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Configure the webhook secret and stub out the heavy background tasks.
    monkeypatch.setattr(settings, "razorpay_webhook_secret", WEBHOOK_SECRET)

    async def _noop_generate(**kwargs):  # _generate_and_archive
        return None

    async def _noop_notify(**kwargs):  # notify_payment_success
        return True

    monkeypatch.setattr(main, "_generate_and_archive", _noop_generate)
    monkeypatch.setattr(main, "notify_payment_success", _noop_notify)

    # Clean module-level state between tests.
    main._ORDER_STORE.clear()
    main._FULFILLED_ORDERS.clear()
    return TestClient(app)


def test_webhook_valid_signature_fulfills(client: TestClient) -> None:
    main._store_order(ORDER_ID, _sample_request())
    body = _payload()
    resp = client.post(
        "/razorpay-webhook",
        content=body,
        headers={"X-Razorpay-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["fulfilled"] is True
    assert ORDER_ID in main._FULFILLED_ORDERS


def test_webhook_invalid_signature_rejected(client: TestClient) -> None:
    main._store_order(ORDER_ID, _sample_request())
    body = _payload()
    resp = client.post(
        "/razorpay-webhook",
        content=body,
        headers={"X-Razorpay-Signature": "deadbeef"},
    )
    assert resp.status_code == 400
    assert ORDER_ID not in main._FULFILLED_ORDERS


def test_webhook_duplicate_delivery_is_idempotent(client: TestClient) -> None:
    main._store_order(ORDER_ID, _sample_request())
    body = _payload()
    headers = {"X-Razorpay-Signature": _sign(body)}

    first = client.post("/razorpay-webhook", content=body, headers=headers)
    second = client.post("/razorpay-webhook", content=body, headers=headers)

    assert first.json()["fulfilled"] is True
    # Second delivery must not re-trigger fulfillment.
    assert second.status_code == 200
    assert second.json()["fulfilled"] is False


def test_webhook_unknown_order_acks_without_fulfilling(client: TestClient) -> None:
    # No order stored for this id.
    body = _payload(order_id="order_DOES_NOT_EXIST")
    resp = client.post(
        "/razorpay-webhook",
        content=body,
        headers={"X-Razorpay-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["fulfilled"] is False


def test_webhook_ignores_unrelated_events(client: TestClient) -> None:
    body = _payload(event="payment.failed")
    resp = client.post(
        "/razorpay-webhook",
        content=body,
        headers={"X-Razorpay-Signature": _sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


# --- inline-generation kill switch ------------------------------------------

def _fulfillment_task_funcs(order_id: str) -> list:
    """Run _start_fulfillment against a real BackgroundTasks and return the scheduled funcs."""
    from fastapi import BackgroundTasks

    main._FULFILLED_ORDERS.clear()
    main._store_order(order_id, _sample_request())
    bg = BackgroundTasks()
    ok = main._start_fulfillment(bg, _sample_request(), order_id, "pay_x")
    assert ok is True
    return [t.func for t in bg.tasks]


def test_inline_generation_disabled_skips_generation(monkeypatch) -> None:
    monkeypatch.setattr(settings, "inline_generation_enabled", False)
    funcs = _fulfillment_task_funcs("order_flag_off")
    # Payment audit + Pabbly notify still scheduled; generation is NOT.
    assert main.notify_payment_success in funcs
    assert main.record_order_paid in funcs
    assert main._generate_and_archive not in funcs


def test_inline_generation_enabled_still_generates(monkeypatch) -> None:
    monkeypatch.setattr(settings, "inline_generation_enabled", True)
    funcs = _fulfillment_task_funcs("order_flag_on")
    assert main._generate_and_archive in funcs
