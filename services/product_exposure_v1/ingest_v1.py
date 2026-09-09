# -*- coding: utf-8 -*-
"""HTTP allowlist + tenant + catalog + clock + persist orchestration."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from schema_product_exposure_v1 import ensure_product_exposure_schema
from services.product_exposure_v1.constants_v1 import (
    ALLOWED_PAYLOAD_KEYS,
    CLOCK_FUTURE_SECONDS,
    CLOCK_PAST_SECONDS,
    EVENT_ID_RE,
    PAGE_CONTEXT_PDP,
    PAYLOAD_MAX_BYTES,
    PRODUCT_ID_RE,
    REASON_COMMERCIAL_DEDUPE,
    REASON_IDEMPOTENT_REPLAY,
    REASON_PERSISTED,
    REQUIRED_PAYLOAD_KEYS,
    SESSION_ID_RE,
    SOURCE_STOREFRONT_WIDGET_V1,
    STORE_SLUG_RE,
    TRUTH_VERSION_EXPOSURE_V1,
)
from services.product_exposure_v1.metrics_v1 import incr_exposure_metric
from services.product_exposure_v1.origin_adapter_v1 import resolve_tenant_authority
from services.product_exposure_v1.persist_v1 import (
    catalog_owns_product,
    persist_commercial_exposure,
)
from services.product_exposure_v1.rate_limit_v1 import (
    check_exposure_rate_limits,
    origin_host_from_origin,
)

_JWT_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
_UTM_RE = re.compile(r"^[A-Za-z0-9._-]{1,80}$")


class IngestHttpError(Exception):
    def __init__(self, status: int, error: str) -> None:
        super().__init__(error)
        self.status = status
        self.error = error


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_occurred_at(raw: Any) -> datetime:
    if not isinstance(raw, str) or not raw.strip():
        raise IngestHttpError(400, "malformed_occurred_at")
    s = raw.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError as exc:
        raise IngestHttpError(400, "malformed_occurred_at") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def sanitize_referrer_domain(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if "://" in s:
        try:
            host = (urlparse(s).hostname or "").strip().lower()
        except ValueError:
            return None
        return host[:253] or None
    if "/" in s or "?" in s or "#" in s or "@" in s:
        return None
    host = s.lower()[:253]
    if not re.match(r"^[a-z0-9][a-z0-9.-]{0,252}$", host):
        return None
    return host


def sanitize_claimed_utm(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if "@" in s or _JWT_RE.match(s):
        return None
    if not _UTM_RE.match(s):
        return None
    return s[:80]


def _reject(status: int, error: str) -> None:
    incr_exposure_metric("exposure_rejected_total")
    raise IngestHttpError(status, error)


def ingest_product_viewed(
    *,
    raw_body: bytes,
    origin: Optional[str],
    _fail_after: Optional[str] = None,
) -> dict[str, Any]:
    """
    Returns 200 payload dict: {ok, persisted, reason, db_statements?}.
    Raises IngestHttpError for bounded 4xx/429/503.
    """
    incr_exposure_metric("exposure_requests_total")
    ensure_product_exposure_schema(db)

    if len(raw_body) > PAYLOAD_MAX_BYTES:
        _reject(413, "payload_too_large")
    if not raw_body.strip():
        _reject(400, "malformed_json")
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IngestHttpError(400, "malformed_json") from exc
    if not isinstance(payload, dict):
        _reject(400, "malformed_json")

    extra = set(payload.keys()) - ALLOWED_PAYLOAD_KEYS
    if extra:
        _reject(400, "unknown_field")
    missing = [k for k in REQUIRED_PAYLOAD_KEYS if k not in payload]
    if missing:
        _reject(400, "missing_field")

    event_id = str(payload.get("event_id") or "").strip()
    if not EVENT_ID_RE.match(event_id):
        _reject(400, "malformed_event_id")

    store_slug = str(payload.get("store_slug") or "").strip()
    if not STORE_SLUG_RE.match(store_slug):
        _reject(400, "malformed_store_slug")

    product_id = str(payload.get("product_id") or "").strip()
    if not PRODUCT_ID_RE.match(product_id):
        _reject(400, "invalid_product_id")

    session_id = payload.get("session_id")
    if session_id is None or str(session_id).strip() == "":
        _reject(400, "missing_session")
    session_id = str(session_id).strip()
    if not SESSION_ID_RE.match(session_id) or len(session_id) > 80:
        _reject(400, "malformed_session")

    source = str(payload.get("source") or "").strip()
    if source != SOURCE_STOREFRONT_WIDGET_V1:
        _reject(422, "unknown_source")

    page_context = str(payload.get("page_context") or "").strip()
    if page_context != PAGE_CONTEXT_PDP:
        _reject(422, "invalid_page_context")

    truth_version = str(payload.get("truth_version") or "").strip()
    if truth_version != TRUTH_VERSION_EXPOSURE_V1:
        _reject(422, "invalid_truth_version")

    received_at = _utcnow_naive()
    occurred_at = _parse_occurred_at(payload.get("occurred_at"))
    if occurred_at > received_at + timedelta(seconds=CLOCK_FUTURE_SECONDS):
        _reject(422, "clock_future")
    if occurred_at < received_at - timedelta(seconds=CLOCK_PAST_SECONDS):
        _reject(422, "clock_too_old")

    authority, terr = resolve_tenant_authority(
        origin=origin,
        payload_store_slug=store_slug,
    )
    if terr or authority is None:
        _reject(403, terr or "invalid_origin")

    host = origin_host_from_origin(origin)
    if not check_exposure_rate_limits(
        origin_host=host,
        session_id=session_id,
        store_slug=authority.canonical_store_slug,
    ):
        _reject(429, "rate_limited")

    if not catalog_owns_product(authority.canonical_store_slug, product_id):
        _reject(422, "product_not_owned")

    try:
        result = persist_commercial_exposure(
            event_id=event_id,
            store_slug=authority.canonical_store_slug,
            product_id=product_id,
            session_id=session_id,
            occurred_at=occurred_at,
            received_at=received_at,
            source=source,
            page_context=page_context,
            truth_version=truth_version,
            commerce_platform=authority.commerce_platform,
            referrer_domain=sanitize_referrer_domain(payload.get("referrer_domain")),
            claimed_utm_source=sanitize_claimed_utm(payload.get("claimed_utm_source")),
            claimed_utm_medium=sanitize_claimed_utm(payload.get("claimed_utm_medium")),
            claimed_utm_campaign=sanitize_claimed_utm(payload.get("claimed_utm_campaign")),
            _fail_after=_fail_after,
        )
    except RuntimeError:
        if _fail_after == "commit":
            incr_exposure_metric("exposure_persisted_total")
            raise
        incr_exposure_metric("exposure_db_failures_total")
        raise IngestHttpError(503, "unavailable") from None
    except SQLAlchemyError:
        incr_exposure_metric("exposure_db_failures_total")
        raise IngestHttpError(503, "unavailable") from None

    if result.reason == REASON_PERSISTED:
        incr_exposure_metric("exposure_persisted_total")
    elif result.reason == REASON_IDEMPOTENT_REPLAY:
        incr_exposure_metric("exposure_idempotent_replay_total")
    elif result.reason == REASON_COMMERCIAL_DEDUPE:
        incr_exposure_metric("exposure_commercial_dedupe_total")

    return {
        "ok": True,
        "persisted": bool(result.persisted),
        "reason": result.reason,
        "db_statements": result.db_statements,
    }
