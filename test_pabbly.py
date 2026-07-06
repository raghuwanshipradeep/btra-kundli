"""Standalone self-test for the Pabbly Connect webhook.

Sends the exact payment-success payload the production flow sends to
`PABBLY_WEBHOOK_URL`, and prints Pabbly's HTTP response so you can verify our
side works without waiting for a real Razorpay payment.

    python test_pabbly.py

NOTE: this sends a REAL POST to the live Pabbly webhook (order id = TEST_*),
which may trigger downstream automation (WhatsApp/CRM/sheet).
"""
from __future__ import annotations

import asyncio
import json

import httpx

from config import settings
from demo_data import SAMPLE_KUNDLI_DATA
from pabbly_notifier import build_payload, notify_payment_success


def _mask(url: str) -> str:
    if not url:
        return "(empty)"
    return url if len(url) <= 48 else f"{url[:40]}…{url[-6:]}"


async def main() -> None:
    url = settings.pabbly_webhook_url
    print("PABBLY_WEBHOOK_URL configured:", bool(url))
    print("  url:", _mask(url))
    if not url:
        print("\n-> Not configured. Set PABBLY_WEBHOOK_URL in .env and restart.")
        return

    payload = build_payload(
        SAMPLE_KUNDLI_DATA.request,
        order_id="TEST_order_selfcheck",
        payment_id="TEST_pay_selfcheck",
    )
    print("\nPayload being sent:")
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))

    # 1) Raw POST so we see Pabbly's exact status + body.
    print("\n--- Raw POST ---")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            resp = await client.post(url, json=payload)
        print("HTTP status:", resp.status_code)
        print("Response body:", resp.text[:1000])
    except Exception as exc:  # noqa: BLE001
        print("Raw POST FAILED:", type(exc).__name__, exc)

    # 2) Exercise the real production code path (retries + logging).
    print("\n--- notify_payment_success() (production path) ---")
    ok = await notify_payment_success(
        SAMPLE_KUNDLI_DATA.request,
        order_id="TEST_order_selfcheck",
        payment_id="TEST_pay_selfcheck",
    )
    print("notify_payment_success returned:", ok)
    print(
        "\nInterpretation: 2xx / True => our side works (check Pabbly Task History).\n"
        "                non-2xx / False => URL/network/our-side issue (see status/body above)."
    )


if __name__ == "__main__":
    asyncio.run(main())
