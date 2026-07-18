from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import pathlib
import re
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
from drive_uploader import folder_for_amount, upload_kundli_pdf
from match_pdf_generator import MatchPDFGenerator
from pabbly_notifier import notify_payment_success
from supabase_repo import record_order_created, record_order_paid, record_job_status
import sheet_orders_repo as sheet_repo

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

# Gate on concurrent PDF generations. A burst of simultaneous paid orders would
# otherwise all start at once, starve the shared AstrologyAPI Semaphore(10), and
# blow past the per-job timeout wall (only a handful finishing). This caps how
# many render concurrently; the rest queue and complete moments later. Lazily
# created on the running loop so tests importing this module don't bind a loop.
_GENERATION_SLOTS: asyncio.Semaphore | None = None


def _get_generation_slots() -> asyncio.Semaphore:
    global _GENERATION_SLOTS
    if _GENERATION_SLOTS is None:
        _GENERATION_SLOTS = asyncio.Semaphore(settings.generation_concurrency)
    return _GENERATION_SLOTS


def _set_job_state(order_id: str, status: str, **details):
    _JOB_STATE[order_id] = {
        "status": status,
        "updated_at": time.time(),
        **details,
    }


def _get_job_state(order_id: str) -> dict | None:
    return _JOB_STATE.get(order_id)


def _save_recovery_pdf(order_id: str, filename: str, pdf_bytes: bytes) -> str | None:
    """Persist a paid PDF to disk when the Drive upload failed, so it's
    recoverable instead of lost. Returns the path written, or None if disabled
    or the write itself failed (already-bad situation — never raise)."""
    if not settings.drive_recovery_dir:
        return None
    try:
        recovery_dir = pathlib.Path(settings.drive_recovery_dir)
        recovery_dir.mkdir(parents=True, exist_ok=True)
        # Prefix with order_id so the file is unambiguous and collision-free.
        dest = recovery_dir / f"{order_id}__{filename}"
        dest.write_bytes(pdf_bytes)
        return str(dest)
    except OSError:
        logger.exception("Failed to write recovery PDF for order=%s", order_id)
        return None


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
# Reusable PDF pipeline
# ---------------------------------------------------------------------------
async def _build_kundli_pdf(request: KundliRequest, order_id: str = "") -> tuple[bytes, str]:
    """Run the full pipeline: fetch astrology data, narrate, translate, render PDF.
    Returns (pdf_bytes, filename). This is where the PAID API calls happen.
    """
    try:
        async with AstrologyAPIClient(lang=request.lang) as client:
            kundli_data = await client.fetch_all(request)
    except Exception:
        logger.exception("API fetch failed")
        raise HTTPException(status_code=502, detail="Failed to fetch astrology data")

    try:
        kundli_data.narratives = await generate_narratives(kundli_data, request.lang)
    except Exception:
        logger.exception("Narrative generation failed, proceeding without narratives")
        kundli_data.narratives = {}

    try:
        await translate_reports(kundli_data, request.lang)
    except Exception:
        logger.exception("Report translation failed, proceeding with English text")

    try:
        pdf_bytes = await asyncio.to_thread(
            pdf_gen.generate, kundli_data, request.lang,
            report_tier=request.report_tier,
        )
    except Exception:
        logger.exception("PDF generation failed")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    filename = _build_filename(request, order_id)
    return pdf_bytes, filename


def _build_filename(request: KundliRequest, order_id: str = "") -> str:
    """Build the archive filename as First##Phone##Email##OrderId.pdf.

    Only the first name word is used (e.g. "Pradeep Raghuwanshi" -> "Pradeep"),
    then phone, email, and the order id are appended with '##'. Empty fields
    are skipped (e.g. the free/dev flow has no order id).
    """
    def _clean(value: str) -> str:
        return "".join(c for c in value if c.isalnum() or c in "@._-").strip()

    name_parts = [_clean(w) for w in request.name.split() if _clean(w)]
    first_name = name_parts[0] if name_parts else ""
    parts = [first_name, _clean(request.phone), _clean(request.email), _clean(order_id)]
    base = "##".join(p for p in parts if p) or "kundli"
    return f"{base}.pdf"


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
# Sheet-driven kundli generation
#
# A second producer alongside the paid Razorpay flow: read SUCCESSFUL rows from the
# Supabase `sheet_orders` table (fed by the hourly Apps Script sync), build a KundliRequest
# from each, and run the SAME pipeline (`_build_kundli_pdf` -> `upload_kundli_pdf`). Status
# lives in sheet_orders' kundli_* columns; kundli_orders and the paid flow are untouched.
# Triggered by POST /admin/process-sheet-orders (point a scheduler at it).
# ---------------------------------------------------------------------------
_SHEET_WORKER_LOCK = asyncio.Lock()


class _SkipRow(Exception):
    """The row can't produce a kundli (missing/invalid birth data). Park it, don't retry —
    retrying bad data just burns attempts."""


def _lang_from_report_language(value: str | None) -> str:
    """report_language holds full words (Hindi / English). Map to the PDF lang code."""
    v = (value or "").strip().lower()
    if v.startswith("hin") or "हिन" in v or "देवन" in v:
        return "hi"
    if v.startswith("eng"):
        return "en"
    if v:
        logger.warning("sheet_orders: unrecognized report_language %r -> defaulting to en", value)
    return "en"


def _parse_dob(value: str | None) -> tuple[int, int, int]:
    """'YYYY-MM-DD' -> (year, month, day). The column is a Postgres date, so the format is
    fixed; a null means the sync couldn't parse it (kept only in date_of_birth_raw)."""
    m = re.match(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})", value or "")
    if not m:
        raise _SkipRow(f"missing/unparseable date_of_birth: {value!r}")
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        raise _SkipRow(f"invalid date_of_birth: {value!r}")
    return year, month, day


def _parse_tob(value: str | None) -> tuple[int, int]:
    """'HH:MM[:SS]' -> (hour, minute). Birth time drives the whole chart, so a missing value
    is skipped rather than defaulted to noon (which would emit a confidently-wrong kundli)."""
    m = re.match(r"^\s*(\d{1,2}):(\d{2})", value or "")
    if not m:
        raise _SkipRow(f"missing/unparseable time_of_birth: {value!r}")
    hour, minute = int(m.group(1)), int(m.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise _SkipRow(f"invalid time_of_birth: {value!r}")
    return hour, minute


async def _lookup_tzone(day, month, year, hour, minute, lat, lon) -> float:
    """Derive the DST-aware timezone offset the way the web form does — sheet_orders has no
    timezone column. Falls back to IST (5.5) if the lookup is unavailable."""
    payload = {
        "day": day, "month": month, "year": year, "hour": hour, "min": minute,
        "lat": lat, "lon": lon, "tzone": 5.5,
    }
    try:
        async with AstrologyAPIClient() as client:
            result = await client.get_timezone_with_dst(payload)
        if result and result.get("timezone") is not None:
            return float(result["timezone"])
    except Exception:
        logger.exception("tzone lookup failed; defaulting to 5.5 IST")
    return 5.5


async def _sheet_row_to_request(row: dict) -> KundliRequest:
    """Map one sheet_orders row onto a KundliRequest — the same shape the paid flow feeds the
    pipeline. Raises _SkipRow when required birth fields are missing or unparseable."""
    year, month, day = _parse_dob(row.get("date_of_birth"))
    hour, minute = _parse_tob(row.get("time_of_birth"))

    lat, lon = row.get("latitude"), row.get("longitude")
    if lat is None or lon is None:
        raise _SkipRow("missing latitude/longitude")
    lat, lon = float(lat), float(lon)

    tzone = await _lookup_tzone(day, month, year, hour, minute, lat, lon)

    return KundliRequest(
        name=(row.get("name") or "Native").strip() or "Native",
        day=day, month=month, year=year, hour=hour, min=minute,
        lat=lat, lon=lon, tzone=tzone,
        lang=_lang_from_report_language(row.get("report_language")),
        place=row.get("place_of_birth") or "",
        phone=str(row.get("phone") or ""),
        email=row.get("email") or "",
        gender=row.get("gender") or "",
        state=row.get("state") or "",
        pincode=str(row.get("pin_code") or ""),
        report_tier="detailed",
    )


def _dedup_by_order_id(rows: list[dict]) -> list[dict]:
    """First row per order_id — an edited sheet row can insert a second row with the same id,
    and requirement is one kundli per order. Rows with no order_id are dropped."""
    seen: set[str] = set()
    out: list[dict] = []
    for row in rows:
        oid = row.get("order_id")
        if not oid or oid in seen:
            continue
        seen.add(oid)
        out.append(row)
    return out


async def _process_sheet_orders(limit: int = 50) -> dict:
    """Sequentially generate + archive a kundli for each pending SUCCESSFUL sheet order.

    One order is fully generated and saved before the next starts. The module lock makes
    overlapping scheduler ticks a no-op; the kundli_* columns make it idempotent across runs.
    """
    if _SHEET_WORKER_LOCK.locked():
        logger.info("sheet worker already running; skipping this invocation")
        return {"status": "already_running"}

    cap = settings.sheet_orders_kundli_max_attempts
    summary: dict = {"status": "ok", "processed": 0, "skipped": 0, "failed": 0, "details": []}

    async with _SHEET_WORKER_LOCK:
        await sheet_repo.reclaim_stale(settings.generation_timeout_seconds)
        rows = _dedup_by_order_id(await sheet_repo.fetch_pending(limit))
        logger.info("sheet worker: %d pending order(s)", len(rows))

        for row in rows:
            order_id = row["order_id"]
            attempts = int(row.get("kundli_attempts") or 0)

            # Gate on the claim landing. If we can't even write kundli_status='generating',
            # the DB is unwritable for this row — so mark_done would fail too, and we'd produce
            # a PDF we can't record (guaranteed duplicate next run). Skip before spending any
            # API calls. This is what stops a broken grant from silently piling up orphan PDFs.
            if not await sheet_repo.claim(order_id, attempts):
                summary["failed"] += 1
                summary["details"].append({
                    "order_id": order_id, "result": "claim_failed",
                    "reason": "could not write kundli_status (DB not writable?); skipped to avoid an orphan PDF",
                })
                logger.error("SHEET CLAIM FAILED: order=%s — skipping generation (check UPDATE grant)", order_id)
                continue

            try:
                request = await _sheet_row_to_request(row)
            except _SkipRow as exc:
                await sheet_repo.mark_failed(order_id, str(exc), permanent=True)
                summary["skipped"] += 1
                summary["details"].append({"order_id": order_id, "result": "skipped", "reason": str(exc)})
                logger.warning("sheet order %s skipped: %s", order_id, exc)
                continue

            start = time.time()
            logger.info("SHEET BG START: order=%s customer=%s", order_id, request.name)
            try:
                async with _get_generation_slots():
                    pdf_bytes, filename = await asyncio.wait_for(
                        _build_kundli_pdf(request, order_id),
                        timeout=settings.generation_timeout_seconds,
                    )
                # Route by order value: orders above the premium threshold archive to the
                # premium folder, the rest to the default folder (folder_for_amount handles
                # null/unparseable amounts by falling back to the default).
                amount = row.get("order_total_amount")
                target_folder = folder_for_amount(amount)
                logger.info(
                    "SHEET routing: order=%s amount=%s -> folder=%s",
                    order_id, amount, target_folder,
                )
                drive_result = await upload_kundli_pdf(
                    pdf_bytes=pdf_bytes,
                    filename=filename,
                    customer_name=request.name,
                    order_id=order_id,
                    payment_id="",
                    folder_id=target_folder,
                )
                if not drive_result:
                    permanent = attempts + 1 >= cap
                    await sheet_repo.mark_failed(order_id, "drive upload failed", permanent=permanent)
                    summary["failed"] += 1
                    summary["details"].append({"order_id": order_id, "result": "failed", "reason": "drive upload failed"})
                    logger.error("SHEET DRIVE FAILED: order=%s customer=%s", order_id, request.name)
                    continue

                drive_link = drive_result.get("webViewLink", "")
                # The PDF is in Drive now. If recording that fails, do NOT report success —
                # the row stays pending and would regenerate (duplicate). Surface it loudly as
                # a distinct state so the operator knows a real file exists but is unrecorded.
                if not await sheet_repo.mark_done(order_id, drive_result.get("id"), drive_link):
                    summary["failed"] += 1
                    summary["details"].append({
                        "order_id": order_id, "result": "archived_unmarked",
                        "drive_link": drive_link,
                        "reason": "PDF uploaded to Drive but DB write failed; will regenerate unless fixed",
                    })
                    logger.error(
                        "SHEET ARCHIVED BUT UNMARKED: order=%s — PDF at %s but kundli_status not written "
                        "(check UPDATE grant); row will regenerate until fixed",
                        order_id, drive_link,
                    )
                    continue

                summary["processed"] += 1
                summary["details"].append({
                    "order_id": order_id, "result": "archived", "drive_link": drive_link,
                })
                logger.info(
                    "SHEET BG COMPLETE: order=%s customer=%s elapsed=%.1fs",
                    order_id, request.name, time.time() - start,
                )
            except Exception as exc:  # noqa: BLE001 — one bad order must not stop the batch
                permanent = attempts + 1 >= cap
                await sheet_repo.mark_failed(order_id, f"{type(exc).__name__}: {exc}", permanent=permanent)
                summary["failed"] += 1
                summary["details"].append({"order_id": order_id, "result": "failed", "reason": str(exc)})
                logger.exception("SHEET BG FAILED: order=%s customer=%s", order_id, request.name)

    logger.info(
        "sheet worker run done: processed=%d skipped=%d failed=%d",
        summary["processed"], summary["skipped"], summary["failed"],
    )
    return summary


@app.post("/admin/process-sheet-orders")
async def process_sheet_orders_endpoint(
    x_admin_key: str | None = Header(None),
    limit: int = 50,
) -> dict:
    """Generate kundli PDFs for pending SUCCESSFUL sheet_orders rows and archive to Drive.
    Point a scheduler (server cron) at this. Gated by X-Admin-Key like /admin/jobs."""
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return await _process_sheet_orders(limit)
