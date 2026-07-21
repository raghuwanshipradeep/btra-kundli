from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import pathlib
import time
from io import BytesIO

import razorpay
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api_client import AstrologyAPIClient
from config import settings
from models import KundliRequest, MatchRequest
from narrative_engine import generate_narratives, translate_reports
from pdf_generator import PDFGenerator
from drive_uploader import upload_kundli_pdf
from match_pdf_generator import MatchPDFGenerator
from pabbly_notifier import notify_payment_success
from supabase_repo import record_order_created, record_order_paid, record_job_status
import sheet_orders_repo as sheet_repo
from pipeline import _build_kundli_pdf, _save_recovery_pdf, _get_generation_slots
import sheet_worker

STATIC_DIR = pathlib.Path(__file__).parent / "static"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logging.getLogger("weasyprint").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Kundli", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
pdf_gen = PDFGenerator()
match_pdf_gen = MatchPDFGenerator()


# ---------------------------------------------------------------------------
# Razorpay client (lazy init so missing keys don't crash startup)
# ---------------------------------------------------------------------------
_razorpay_client: razorpay.Client | None = None


def _get_razorpay_client() -> razorpay.Client:
    global _razorpay_client
    if _razorpay_client is None:
        if not settings.razorpay_key_id or not settings.razorpay_key_secret:
            raise HTTPException(status_code=503, detail="Payment not configured")
        _razorpay_client = razorpay.Client(
            auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
        )
    return _razorpay_client


# ---------------------------------------------------------------------------
# Order store: order_id -> (KundliRequest, created_at)
# Production should use Redis or the existing aiosqlite DB.
# ---------------------------------------------------------------------------
_ORDER_STORE: dict[str, tuple[KundliRequest, float]] = {}
_ORDER_TTL_SECONDS = 30 * 60


def _store_order(order_id: str, request: KundliRequest) -> None:
    _prune_orders()
    _ORDER_STORE[order_id] = (request, time.time())


def _get_order(order_id: str) -> KundliRequest | None:
    entry = _ORDER_STORE.get(order_id)
    if not entry:
        return None
    request, created = entry
    if time.time() - created > _ORDER_TTL_SECONDS:
        _ORDER_STORE.pop(order_id, None)
        return None
    return request


def _prune_orders() -> None:
    now = time.time()
    expired = [k for k, (_, t) in _ORDER_STORE.items() if now - t > _ORDER_TTL_SECONDS]
    for k in expired:
        _ORDER_STORE.pop(k, None)


# ---------------------------------------------------------------------------
# Fulfillment idempotency: a paid order may arrive via BOTH the browser
# /verify-and-generate callback AND the /razorpay-webhook. Whoever claims the
# order first runs generation; the other is a no-op. The check+add is
# synchronous (no await between), so it's atomic within the single worker.
# ---------------------------------------------------------------------------
_FULFILLED_ORDERS: set[str] = set()


def _claim_order(order_id: str) -> bool:
    """Return True if this caller wins the right to fulfill; False if already claimed."""
    if order_id in _FULFILLED_ORDERS:
        return False
    _FULFILLED_ORDERS.add(order_id)
    return True


def _start_fulfillment(
    background_tasks: BackgroundTasks,
    request: KundliRequest,
    order_id: str,
    payment_id: str,
) -> bool:
    """Schedule Pabbly notify + PDF generation/archive for a paid order, once.

    Returns False (and does nothing) if the order was already fulfilled by the
    other payment-confirmation path. Pabbly is registered before the PDF/Drive
    job so downstream automation fires right away (the PDF job takes minutes).
    """
    if not _claim_order(order_id):
        logger.info("Fulfillment already claimed for order=%s — skipping duplicate", order_id)
        return False

    _ORDER_STORE.pop(order_id, None)
    background_tasks.add_task(
        notify_payment_success,
        request=request,
        order_id=order_id,
        payment_id=payment_id,
    )
    background_tasks.add_task(
        record_order_paid,
        request=request,
        order_id=order_id,
        payment_id=payment_id,
    )
    if settings.inline_generation_enabled:
        background_tasks.add_task(
            _generate_and_archive,
            request=request,
            order_id=order_id,
            payment_id=payment_id,
        )
    else:
        # Generation is handled by the sheet_orders DB worker; skip inline generation so the
        # same order isn't produced twice. Payment + Pabbly notify + audit still ran above.
        logger.info(
            "Inline generation disabled (INLINE_GENERATION_ENABLED=false) — order=%s "
            "recorded + notified; PDF deferred to the sheet_orders worker",
            order_id,
        )
    return True


# ---------------------------------------------------------------------------
# Background job state
# ---------------------------------------------------------------------------
_JOB_STATE: dict[str, dict] = {}


def _set_job_state(order_id: str, status: str, **details):
    _JOB_STATE[order_id] = {
        "status": status,
        "updated_at": time.time(),
        **details,
    }


def _get_job_state(order_id: str) -> dict | None:
    return _JOB_STATE.get(order_id)


def _list_recent_jobs(limit: int = 50) -> list[dict]:
    items = [{"order_id": oid, **state} for oid, state in _JOB_STATE.items()]
    items.sort(key=lambda x: x.get("updated_at", 0), reverse=True)
    return items[:limit]


async def _generate_and_archive(
    request: KundliRequest,
    order_id: str,
    payment_id: str,
):
    """Gate concurrent generations, then run the pipeline. Jobs beyond the
    concurrency cap wait here in ``queued`` state; the per-job timeout wall only
    starts once a slot is acquired inside ``_generate_and_archive_inner``."""
    _set_job_state(order_id, "queued", customer=request.name, lang=request.lang)
    async with _get_generation_slots():
        await _generate_and_archive_inner(request, order_id, payment_id)


async def _generate_and_archive_inner(
    request: KundliRequest,
    order_id: str,
    payment_id: str,
):
    start = time.time()
    _set_job_state(order_id, "generating", customer=request.name, lang=request.lang)
    await record_job_status(request, order_id, "generating")
    logger.info("BG START: order=%s customer=%s", order_id, request.name)

    try:
        pdf_bytes, filename = await asyncio.wait_for(
            _build_kundli_pdf(request, order_id),
            timeout=settings.generation_timeout_seconds,
        )
        logger.info(
            "BG PDF generated: order=%s size=%d filename=%s elapsed=%.1fs",
            order_id, len(pdf_bytes), filename, time.time() - start,
        )
    except asyncio.TimeoutError:
        logger.error(
            "BG TIMEOUT (>%ds): order=%s customer=%s",
            settings.generation_timeout_seconds, order_id, request.name,
        )
        _set_job_state(
            order_id, "timeout",
            customer=request.name,
            elapsed_s=round(time.time() - start, 1),
        )
        await record_job_status(
            request, order_id, "timeout",
            error_detail=f"generation timeout (>{settings.generation_timeout_seconds}s)",
            elapsed_s=round(time.time() - start, 1),
        )
        return
    except Exception:
        logger.exception("BG PDF FAILED: order=%s customer=%s", order_id, request.name)
        _set_job_state(
            order_id, "pdf_failed",
            customer=request.name,
            elapsed_s=round(time.time() - start, 1),
        )
        await record_job_status(
            request, order_id, "pdf_failed",
            error_detail="PDF generation failed",
            elapsed_s=round(time.time() - start, 1),
        )
        return

    drive_result = await upload_kundli_pdf(
        pdf_bytes=pdf_bytes,
        filename=filename,
        customer_name=request.name,
        order_id=order_id,
        payment_id=payment_id,
    )

    if drive_result is None and settings.drive_archive_enabled and settings.google_drive_folder_id:
        recovery_path = _save_recovery_pdf(order_id, filename, pdf_bytes)
        logger.error(
            "DRIVE ARCHIVE MISSING — paid order=%s customer=%s — manual recovery required "
            "(local copy: %s)",
            order_id, request.name, recovery_path or "NOT SAVED",
        )
        _set_job_state(
            order_id, "drive_failed",
            customer=request.name,
            pdf_size_bytes=len(pdf_bytes),
            recovery_path=recovery_path,
            elapsed_s=round(time.time() - start, 1),
        )
        await record_job_status(
            request, order_id, "drive_failed",
            error_detail=f"Drive upload failed; local recovery: {recovery_path or 'NOT SAVED'}",
            elapsed_s=round(time.time() - start, 1),
        )
        return

    if drive_result is None:
        _set_job_state(
            order_id, "generated_no_archive",
            customer=request.name,
            filename=filename,
            elapsed_s=round(time.time() - start, 1),
        )
        await record_job_status(
            request, order_id, "generated_no_archive",
            elapsed_s=round(time.time() - start, 1),
        )
        logger.info("BG COMPLETE (no archive): order=%s customer=%s", order_id, request.name)
        return

    _set_job_state(
        order_id, "archived",
        customer=request.name,
        drive_file_id=drive_result.get("id"),
        drive_link=drive_result.get("webViewLink", ""),
        filename=filename,
        elapsed_s=round(time.time() - start, 1),
    )
    await record_job_status(
        request, order_id, "archived",
        drive_file_id=drive_result.get("id"),
        drive_link=drive_result.get("webViewLink", ""),
        elapsed_s=round(time.time() - start, 1),
    )
    logger.info(
        "BG COMPLETE: order=%s customer=%s elapsed=%.1fs drive_link=%s",
        order_id, request.name, time.time() - start, drive_result.get("webViewLink"),
    )


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------
def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    message = f"{order_id}|{payment_id}".encode()
    expected = hmac.new(
        settings.razorpay_key_secret.encode(),
        message,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify a Razorpay webhook: HMAC-SHA256 of the RAW body using the webhook
    secret (distinct from the checkout signature, which uses the key secret)."""
    if not settings.razorpay_webhook_secret:
        return False
    expected = hmac.new(
        settings.razorpay_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class PaymentVerification(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/geo-search")
async def geo_search(place: str = Query(..., min_length=2)):
    async with AstrologyAPIClient() as client:
        results = await client.get_geo_details(place)
    if results is None:
        return {"geonames": []}
    return {"geonames": [r.model_dump() for r in results]}


@app.get("/api/timezone")
async def timezone_lookup(
    day: int = 1,
    month: int = 1,
    year: int = 2000,
    hour: int = 12,
    min: int = 0,
    lat: float = 0.0,
    lon: float = 0.0,
    tzone: float = 5.5,
):
    payload = {
        "day": day, "month": month, "year": year,
        "hour": hour, "min": min,
        "lat": lat, "lon": lon, "tzone": tzone,
    }
    async with AstrologyAPIClient() as client:
        result = await client.get_timezone_with_dst(payload)
    if result is None:
        return {"timezone": tzone}
    return result


@app.get("/api/payment-config")
async def payment_config() -> dict:
    """Return whether payment is enabled and the price, so the frontend can adapt."""
    enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
    return {
        "enabled": enabled,
        "amount": settings.kundli_price_paise,
        "currency": settings.payment_currency,
    }


@app.post("/create-order")
async def create_order(request: KundliRequest, background_tasks: BackgroundTasks) -> dict:
    if not request.lat or not request.lon:
        raise HTTPException(status_code=400, detail="Place not selected")

    client = _get_razorpay_client()
    try:
        order = await asyncio.to_thread(
            client.order.create,
            {
                "amount": settings.kundli_price_paise,
                "currency": settings.payment_currency,
                "receipt": f"kundli_{int(time.time())}",
                "notes": {"name": request.name, "year": str(request.year)},
            },
        )
    except Exception:
        logger.exception("Razorpay order creation failed")
        raise HTTPException(status_code=502, detail="Could not create payment order")

    _store_order(order["id"], request)

    # Durable audit record (best-effort; runs after the response, never blocks checkout).
    background_tasks.add_task(
        record_order_created,
        request=request,
        order_id=order["id"],
        amount_paise=settings.kundli_price_paise,
    )

    return {
        "order_id": order["id"],
        "amount": order["amount"],
        "currency": order["currency"],
        "key_id": settings.razorpay_key_id,
        "name": request.name,
    }


@app.post("/verify-and-generate")
async def verify_and_generate(
    verification: PaymentVerification,
    background_tasks: BackgroundTasks,
) -> dict:
    if not _verify_signature(
        verification.razorpay_order_id,
        verification.razorpay_payment_id,
        verification.razorpay_signature,
    ):
        logger.warning("Invalid payment signature for order %s", verification.razorpay_order_id)
        raise HTTPException(status_code=400, detail="Payment verification failed")

    request = _get_order(verification.razorpay_order_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Order not found or expired")

    try:
        client = _get_razorpay_client()
        payment = await asyncio.to_thread(client.payment.fetch, verification.razorpay_payment_id)
        if payment.get("status") not in ("captured", "authorized"):
            raise HTTPException(status_code=400, detail="Payment not completed")
        if payment.get("amount") != settings.kundli_price_paise:
            logger.warning("Amount mismatch on order %s", verification.razorpay_order_id)
            raise HTTPException(status_code=400, detail="Payment amount mismatch")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Payment fetch failed")
        raise HTTPException(status_code=502, detail="Could not confirm payment")

    _start_fulfillment(
        background_tasks,
        request=request,
        order_id=verification.razorpay_order_id,
        payment_id=verification.razorpay_payment_id,
    )

    return {
        "status": "processing",
        "message": "Your Kundli is being prepared. We will send it to you shortly.",
        "order_id": verification.razorpay_order_id,
        "payment_id": verification.razorpay_payment_id,
    }


@app.post("/razorpay-webhook")
async def razorpay_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_razorpay_signature: str = Header(default=""),
) -> dict:
    """Server-to-server fulfillment: Razorpay calls this on payment.captured,
    independent of the browser. This is the reliable path — the in-page
    callback (/verify-and-generate) is only a best-effort fast path.

    Idempotent: if the browser callback already fulfilled the order, this is a
    no-op (and vice versa), guarded by _claim_order.
    """
    body = await request.body()

    if not settings.razorpay_webhook_secret:
        logger.error("Webhook received but RAZORPAY_WEBHOOK_SECRET is not configured")
        raise HTTPException(status_code=503, detail="Webhook not configured")

    if not _verify_webhook_signature(body, x_razorpay_signature):
        logger.warning("Razorpay webhook signature verification failed")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Razorpay webhook body was not valid JSON")
        raise HTTPException(status_code=400, detail="Invalid payload")

    event = payload.get("event", "")
    # Only payment-confirming events trigger fulfillment; ack everything else.
    if event not in ("payment.captured", "order.paid"):
        logger.info("Razorpay webhook ignored event=%s", event)
        return {"status": "ignored", "event": event}

    payment_entity = (
        payload.get("payload", {}).get("payment", {}).get("entity", {})
    )
    order_id = payment_entity.get("order_id", "")
    payment_id = payment_entity.get("id", "")
    amount = payment_entity.get("amount")

    if not order_id:
        logger.warning("Razorpay webhook %s had no order_id", event)
        return {"status": "ignored", "reason": "no order_id"}

    if amount is not None and amount != settings.kundli_price_paise:
        logger.warning(
            "Webhook amount mismatch on order %s (got %s, expected %s)",
            order_id, amount, settings.kundli_price_paise,
        )

    kundli_request = _get_order(order_id)
    if kundli_request is None:
        # Paid order we can't map back to form data — needs manual recovery.
        logger.error(
            "WEBHOOK paid order not found in store — order=%s payment=%s — manual recovery required",
            order_id, payment_id,
        )
        # 200 so Razorpay stops retrying; there is nothing more we can do here.
        return {"status": "ok", "fulfilled": False, "reason": "order not found"}

    scheduled = _start_fulfillment(
        background_tasks,
        request=kundli_request,
        order_id=order_id,
        payment_id=payment_id,
    )
    logger.info(
        "WEBHOOK %s order=%s payment=%s scheduled=%s",
        event, order_id, payment_id, scheduled,
    )
    return {"status": "ok", "fulfilled": scheduled}


@app.post("/generate-kundli")
async def generate_kundli(request: KundliRequest) -> StreamingResponse:
    if not settings.allow_free_generation:
        raise HTTPException(status_code=403, detail="Payment required. Use /create-order flow.")

    pdf_bytes, filename = await _build_kundli_pdf(request)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.post("/generate-match")
async def generate_match(request: MatchRequest) -> StreamingResponse:
    try:
        async with AstrologyAPIClient(lang=request.lang) as client:
            match_data = await client.fetch_match(request)
    except Exception:
        logger.exception("Match API fetch failed")
        raise HTTPException(status_code=502, detail="Failed to fetch match data")

    try:
        pdf_bytes = await asyncio.to_thread(
            match_pdf_gen.generate, match_data, request.lang
        )
    except Exception:
        logger.exception("Match PDF generation failed")
        raise HTTPException(status_code=500, detail="Match PDF generation failed")

    safe_m = "".join(c for c in request.m_name if c.isalnum() or c in " _-").strip()
    safe_f = "".join(c for c in request.f_name if c.isalnum() or c in " _-").strip()
    filename = f"match_{safe_m}_{safe_f}.pdf"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/demo")
async def demo() -> StreamingResponse:
    from demo_data import SAMPLE_KUNDLI_DATA

    data = SAMPLE_KUNDLI_DATA.model_copy(deep=True)
    try:
        data.narratives = await generate_narratives(data, "en")
    except Exception:
        logger.exception("Demo narrative generation failed")
        data.narratives = {}

    try:
        await translate_reports(data, "en")
    except Exception:
        logger.exception("Demo translation failed")

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_gen.generate, data, "en"
        )
    except Exception:
        logger.exception("Demo PDF generation failed")
        raise HTTPException(status_code=500, detail="Demo PDF generation failed")

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="demo_kundli.pdf"'},
    )


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------
@app.get("/admin/jobs")
async def list_jobs(
    x_admin_key: str | None = Header(None),
    limit: int = 50,
) -> dict:
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"jobs": _list_recent_jobs(limit=limit)}


@app.get("/admin/jobs/{order_id}")
async def get_job(
    order_id: str,
    x_admin_key: str | None = Header(None),
) -> dict:
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    state = _get_job_state(order_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    return state


# ---------------------------------------------------------------------------
# Sheet-driven kundli generation (manual/backfill trigger)
#
# The worker itself lives in sheet_worker.py and normally runs continuously as a separate
# process (run_sweeper.py). This endpoint is a manual/backfill trigger for the same
# sweep_once() — useful for draining on demand or testing a single order (?limit=1).
# ---------------------------------------------------------------------------
@app.post("/admin/process-sheet-orders")
async def process_sheet_orders_endpoint(
    x_admin_key: str | None = Header(None),
    limit: int = 50,
) -> dict:
    """Generate kundli PDFs for pending SUCCESSFUL sheet_orders rows and archive to Drive.
    A manual trigger for the same worker the standalone sweeper runs. Gated by X-Admin-Key."""
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await sheet_worker.sweep_once(limit)


@app.get("/admin/sheet-jobs")
async def sheet_jobs_endpoint(
    x_admin_key: str | None = Header(None),
    limit: int = 100,
) -> dict:
    """Failed/parked sheet_orders rows (kundli_status in failed/failed_permanent), newest first.
    Gated by X-Admin-Key like /admin/jobs. Each row's sheet_row points back to the source cell."""
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"jobs": await sheet_repo.fetch_failed(limit)}
