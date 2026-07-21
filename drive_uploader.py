import asyncio
import logging
import time
from io import BytesIO
from pathlib import Path

import google_auth_httplib2
import httplib2
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseUpload

from config import settings

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_drive_service = None


def _load_credentials() -> Credentials:
    token_path = Path(settings.google_token_path)

    # token.json is git-ignored, so it is NOT baked into the built image. On hosts that
    # inject the token as an env var instead of a file mount (e.g. compose-based Coolify),
    # materialize the file once from GOOGLE_TOKEN_JSON so Drive auth works after a fresh deploy.
    if not token_path.exists() and settings.google_token_json:
        try:
            token_path.write_text(settings.google_token_json)
            logger.info("Wrote Drive token to %s from GOOGLE_TOKEN_JSON", token_path)
        except OSError:
            logger.exception("Failed to materialize Drive token from GOOGLE_TOKEN_JSON")

    if not token_path.exists():
        raise FileNotFoundError(
            f"Token file not found at {token_path}. Set GOOGLE_TOKEN_JSON (or mount the file), "
            "or run 'python get_drive_token.py' first to authorize."
        )

    creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Persist the refreshed token, but don't let a write failure (e.g. a
        # read-only mount in production) break the upload — the in-memory creds
        # are already valid for this process.
        try:
            token_path.write_text(creds.to_json())
        except OSError as exc:
            logger.warning(
                "Could not persist refreshed token to %s: %s "
                "(continuing with in-memory credentials)",
                token_path, exc,
            )

    return creds


def _get_drive_service():
    global _drive_service
    if _drive_service is not None:
        return _drive_service

    creds = _load_credentials()
    # Build with an explicit socket timeout so a slow-but-working upload isn't
    # killed at httplib2's ~60s default. AuthorizedHttp injects the OAuth creds.
    authed_http = google_auth_httplib2.AuthorizedHttp(
        creds, http=httplib2.Http(timeout=settings.drive_upload_timeout_seconds)
    )
    _drive_service = build("drive", "v3", http=authed_http, cache_discovery=False)
    return _drive_service


def _upload_sync(pdf_bytes: bytes, filename: str, folder_id: str, description: str) -> dict:
    service = _get_drive_service()

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
        "description": description,
    }

    last_exc = None
    for attempt in range(3):
        try:
            # Resumable upload: chunked and individually retriable, far more
            # robust on flaky container egress than a single-shot PUT.
            media = MediaIoBaseUpload(
                BytesIO(pdf_bytes),
                mimetype="application/pdf",
                resumable=True,
            )
            request = service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, createdTime",
                # Required when the parent is inside a Shared Drive (Team Drive); harmless for
                # a My Drive folder. Without it, a Shared Drive parent returns 404.
                supportsAllDrives=True,
            )
            response = None
            while response is None:
                _, response = request.next_chunk()
            return response
        # TimeoutError/ConnectionError are both OSError subclasses; the previous
        # `except ConnectionError` missed the production write timeout entirely.
        # HttpError covers transient 5xx/429 from Drive.
        except (TimeoutError, OSError, HttpError) as exc:
            last_exc = exc
            logger.warning("Drive upload attempt %d failed: %s", attempt + 1, exc)
            time.sleep(2 ** attempt)

    raise last_exc


def folder_for_amount(amount) -> str:
    """Pick the archive folder for an order's rupee total.

    Orders above ``drive_premium_amount_threshold`` go to the premium folder; the default
    folder catches everything else — the threshold value itself, lower amounts, and any
    null/unparseable value. Falls back to the default folder whenever the premium folder
    isn't configured, so the routing can never send a PDF to an empty folder id.
    """
    default = settings.google_drive_folder_id
    premium = settings.google_drive_folder_id_premium
    if not premium:
        return default
    try:
        amt = float(amount)
    except (TypeError, ValueError):
        return default
    return premium if amt > settings.drive_premium_amount_threshold else default


async def upload_kundli_pdf(
    pdf_bytes: bytes,
    filename: str,
    customer_name: str = "",
    order_id: str = "",
    payment_id: str = "",
    folder_id: str | None = None,
) -> dict | None:
    if not settings.drive_archive_enabled:
        logger.info("Drive archive disabled; skipping upload for %s", filename)
        return None

    # Explicit folder_id (e.g. amount-based routing) wins; otherwise the default folder.
    target_folder = folder_id or settings.google_drive_folder_id
    if not target_folder:
        logger.error("No Drive folder configured; cannot archive %s", filename)
        return None

    description = (
        f"Customer: {customer_name}\n"
        f"Order ID: {order_id}\n"
        f"Payment ID: {payment_id}\n"
    )

    try:
        result = await asyncio.to_thread(
            _upload_sync,
            pdf_bytes,
            filename,
            target_folder,
            description,
        )
        logger.info(
            "Drive upload OK: file_id=%s name=%s customer=%s folder=%s",
            result.get("id"), result.get("name"), customer_name, target_folder,
        )
        return result
    except Exception:
        logger.exception(
            "Drive upload FAILED for order_id=%s filename=%s folder=%s "
            "— payment still valid, PDF needs manual recovery",
            order_id, filename, target_folder,
        )
        return None
