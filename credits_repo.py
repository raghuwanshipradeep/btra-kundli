"""Credit balance gate for sheet-driven kundli generation.

The credit system itself belongs to a separate admin/user web app: an admin assigns credits,
each assignment is appended to ``credit_transactions`` (``type='assign'``), and the balance
lives on ``astrologers.credits_balance``. This module is the spending side — read the balance
before generating, consume one credit after a PDF is delivered.

NOT the balance: ``credit_transactions.total_credits_assigned``. That column is ``text`` on an
append-only ledger and holds a per-row copy of that row's own ``amount`` ('50', '50', '1000') —
there is no "current" row and no running total. ``astrologers`` is authoritative.

FAIL-CLOSED, unlike the rest of the integration layer. ``drive_uploader`` / ``pabbly_notifier`` /
``supabase_repo`` are best-effort and never block generation; this is a *gate*, so an unreadable
balance must mean "do not generate". ``get_balance`` therefore returns ``None`` (not 0, and not
some permissive default) on any failure, and the caller treats ``None`` as blocking. Failing open
would hand out free generations exactly when the accounting is broken. It costs nothing in
practice: the sweeper already needs Supabase for fetch/claim, so an outage stops it regardless.

Reuses ``_headers`` and ``_should_retry`` from ``supabase_repo`` (both table-independent) so auth
and retry policy can't drift across modules.
"""
from __future__ import annotations

import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

from config import settings
from supabase_repo import _headers, _should_retry

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0)

_ASTROLOGERS = "astrologers"
_CONSUME_FN = "rpc/consume_kundli_credit"


def enabled() -> bool:
    """Credit gating is on only when Supabase is configured AND the kill switch is set.

    ``CREDIT_CHECK_ENABLED=false`` restores the pre-credit behaviour (unmetered generation)
    with no rebuild — the rollback path if the gate ever wrongly blocks production. It is read
    from ``settings``, built once at import, so it applies on a sweeper recreate, not live.
    """
    return bool(
        settings.supabase_url
        and settings.supabase_service_key
        and settings.credit_check_enabled
    )


def _url(path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _get(path: str, params: dict) -> list[dict]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(_url(path), headers=_headers("return=representation"), params=params)
        if resp.status_code >= 400:
            logger.warning("credits GET %s -> %s: %s", path, resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20) + wait_random(0, 2),
    retry=retry_if_exception(_should_retry),
    reraise=True,
)
async def _post(path: str, body: dict) -> list[dict] | dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(_url(path), headers=_headers("return=representation"), json=body)
        if resp.status_code >= 400:
            logger.warning("credits POST %s -> %s: %s", path, resp.status_code, resp.text)
        resp.raise_for_status()
        return resp.json()


async def resolve_astrologer_id() -> str | None:
    """The active astrologer whose balance funds generation, or None to block.

    ``sheet_orders`` carries no astrologer link (unlike ``kundli_orders``), and the system is
    single-astrologer by design, so the row is resolved at runtime rather than pinned in config —
    nothing to keep in sync with the database.

    Fetches two rows to detect the unexpected multi-astrologer case. If it happens, this logs
    loudly and charges the oldest rather than halting generation entirely: a deterministic
    (``created_at`` ascending) wrong-ish account beats stopping the business, and the error is
    impossible to miss.
    """
    if not enabled():
        return None
    params = {
        "select": "id,name,credits_balance",
        "is_active": "eq.true",
        "order": "created_at.asc",
        "limit": "2",
    }
    try:
        rows = await _get(_ASTROLOGERS, params)
    except Exception:
        logger.exception("credits: resolving the active astrologer failed; blocking generation")
        return None

    if not rows:
        logger.error("credits: no active astrologer found; blocking generation")
        return None
    if len(rows) > 1:
        logger.error(
            "credits: %d active astrologers found (%s) but this system expects exactly one; "
            "charging the oldest (%s)",
            len(rows), [r.get("id") for r in rows], rows[0].get("id"),
        )
    return rows[0].get("id")


async def get_balance(astrologer_id: str) -> int | None:
    """Current credit balance, or None when it can't be determined.

    None is deliberately distinct from 0: both block generation, but None means "unknown"
    (Supabase error, missing row) while 0 means "genuinely out of credits". The caller logs
    the difference.
    """
    if not enabled():
        return None
    try:
        rows = await _get(
            _ASTROLOGERS,
            {"select": "credits_balance,is_active", "id": f"eq.{astrologer_id}", "limit": "1"},
        )
    except Exception:
        logger.exception("credits: balance lookup failed for %s; blocking generation", astrologer_id)
        return None

    if not rows:
        logger.error("credits: astrologer %s not found; blocking generation", astrologer_id)
        return None
    if not rows[0].get("is_active"):
        logger.error("credits: astrologer %s is inactive; blocking generation", astrologer_id)
        return None

    balance = rows[0].get("credits_balance")
    if balance is None:
        logger.error("credits: astrologer %s has a null balance; blocking generation", astrologer_id)
        return None
    return int(balance)


async def consume_credit(astrologer_id: str, order_id: str) -> tuple[bool, int | None]:
    """Spend one credit atomically. Returns (spent, balance_after).

    Delegates to the ``consume_kundli_credit`` Postgres function (``credits_schema.sql``) because
    PostgREST cannot express ``set credits_balance = credits_balance - 1`` — a read-then-write here
    would let two callers spend the same credit twice. The function does the check, the decrement,
    and the ledger insert in one transaction.

    ``(False, ...)`` means nothing was spent: out of credits, inactive, or the call failed.
    """
    if not enabled():
        return False, None
    body = {
        "p_astrologer_id": astrologer_id,
        "p_order_id": order_id or None,
        "p_note": "Kundli PDF generated",
    }
    try:
        result = await _post(_CONSUME_FN, body)
    except Exception:
        logger.exception("credits: consume failed for order=%s", order_id)
        return False, None

    # A set-returning function comes back as a list of rows; tolerate a bare object too.
    row = result[0] if isinstance(result, list) and result else result
    if not isinstance(row, dict):
        logger.error("credits: unexpected consume response for order=%s: %r", order_id, result)
        return False, None
    balance_after = row.get("balance_after")
    return bool(row.get("ok")), (int(balance_after) if balance_after is not None else None)
