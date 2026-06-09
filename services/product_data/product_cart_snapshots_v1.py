# -*- coding: utf-8 -*-
"""
Cart Line Snapshots v1 — immutable product line persistence from widget ``lines[]``.

Capture sources: ``cart_state_sync``, ``cart_abandoned`` only.
Insert-only; duplicate identical lines are skipped via content_hash unique constraint.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartLineSnapshot
from schema_cart_line_snapshots_v1 import ensure_cart_line_snapshots_schema
from services.product_data.product_data_types_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
)

log = logging.getLogger("cartflow")

CAPTURE_SOURCE_CART_STATE_SYNC = "cart_state_sync"
CAPTURE_SOURCE_CART_ABANDONED = "cart_abandoned"

_ALLOWED_CAPTURE_SOURCES = frozenset(
    {CAPTURE_SOURCE_CART_STATE_SYNC, CAPTURE_SOURCE_CART_ABANDONED}
)

MAX_LINES = 20


@dataclass(frozen=True, slots=True)
class CartLineSnapshotPersistResult:
    inserted: int = 0
    skipped_duplicate: int = 0
    skipped_empty: int = 0
    skipped_invalid: int = 0


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _norm_str(value: Any, *, max_len: int) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    return s[:max_len]


def _norm_price(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        if isinstance(value, (int, float)):
            n = float(value)
        else:
            n = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    if not (n == n):  # NaN
        return None
    return round(n, 4)


def _norm_qty(value: Any) -> int:
    if value is None or value == "":
        return 1
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return 1
    return n if n > 0 else 1


def _line_product_id(line: dict[str, Any]) -> str:
    pid = _norm_str(line.get("product_id"), max_len=128)
    if pid:
        return pid
    prod = line.get("product")
    if isinstance(prod, dict):
        nested = _norm_str(prod.get("id"), max_len=128)
        if nested:
            return nested
    raw_id = _norm_str(line.get("id"), max_len=128)
    variant_id = _norm_str(line.get("variant_id"), max_len=128)
    if raw_id and not variant_id:
        return raw_id
    return ""


def _line_variant_id(line: dict[str, Any]) -> str:
    return _norm_str(line.get("variant_id"), max_len=128)


def _line_sku(line: dict[str, Any]) -> str:
    return _norm_str(line.get("sku") or line.get("product_num"), max_len=128)


def _line_name(line: dict[str, Any]) -> str:
    name = (
        line.get("name")
        or line.get("title")
        or line.get("product_name")
        or (line.get("product") or {}).get("name")
        or ""
    )
    return _norm_str(name, max_len=200)


def _line_has_identity(line: dict[str, Any]) -> bool:
    return bool(
        _line_product_id(line)
        or _line_variant_id(line)
        or _line_sku(line)
        or _line_name(line)
    )


def _line_capture_confidence(line: dict[str, Any]) -> str:
    if _line_product_id(line):
        return CONFIDENCE_HIGH
    if _line_variant_id(line) or _line_sku(line):
        return CONFIDENCE_MEDIUM
    if _line_name(line):
        return CONFIDENCE_LOW
    return CONFIDENCE_LOW


def _line_content_hash(line: dict[str, Any]) -> str:
    canonical = {
        "product_id": _line_product_id(line),
        "variant_id": _line_variant_id(line),
        "sku": _line_sku(line),
        "name": _line_name(line),
        "unit_price": _norm_price(line.get("unit_price")),
        "quantity": _norm_qty(line.get("quantity")),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _identity_from_payload(payload: dict[str, Any]) -> tuple[str, str, str, str]:
    from main import (  # noqa: PLC0415 — align with cart event identity
        _cart_id_str_from_payload,
        _normalize_store_slug,
        _recovery_key_from_payload,
        _session_part_from_payload,
    )

    store_slug = _normalize_store_slug(payload)[:255]
    session_id = _session_part_from_payload(payload)[:512]
    cart_id = (_cart_id_str_from_payload(payload) or "").strip()[:255]
    recovery_key = _recovery_key_from_payload(payload)[:512]
    return store_slug, session_id, cart_id, recovery_key


def _extract_lines(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("lines")
    if not isinstance(raw, list) or not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw[:MAX_LINES]:
        if isinstance(item, dict):
            out.append(item)
    return out


def persist_cart_line_snapshots_from_payload(
    payload: dict[str, Any],
    *,
    capture_source: str,
    captured_at: Optional[datetime] = None,
) -> CartLineSnapshotPersistResult:
    """
    Insert immutable cart line snapshots from Product Identity ``lines[]``.
    Never updates existing rows.
    """
    source = str(capture_source or "").strip().lower()
    if source not in _ALLOWED_CAPTURE_SOURCES:
        return CartLineSnapshotPersistResult(skipped_invalid=1)

    if not isinstance(payload, dict):
        return CartLineSnapshotPersistResult(skipped_invalid=1)

    lines = _extract_lines(payload)
    if not lines:
        return CartLineSnapshotPersistResult(skipped_empty=1)

    store_slug, session_id, cart_id, recovery_key = _identity_from_payload(payload)
    if not store_slug or not session_id:
        return CartLineSnapshotPersistResult(skipped_invalid=len(lines))

    ensure_cart_line_snapshots_schema(db)
    when = _naive(captured_at or _utc_now())

    inserted = 0
    skipped_duplicate = 0
    skipped_invalid = 0

    try:
        with db.session.begin_nested():
            for line in lines:
                if not _line_has_identity(line):
                    skipped_invalid += 1
                    continue

                content_hash = _line_content_hash(line)
                exists = (
                    db.session.query(CartLineSnapshot.id)
                    .filter(
                        CartLineSnapshot.store_slug == store_slug,
                        CartLineSnapshot.session_id == session_id,
                        CartLineSnapshot.cart_id == (cart_id or ""),
                        CartLineSnapshot.capture_source == source,
                        CartLineSnapshot.content_hash == content_hash,
                    )
                    .limit(1)
                    .first()
                )
                if exists is not None:
                    skipped_duplicate += 1
                    continue

                row = CartLineSnapshot(
                    store_slug=store_slug,
                    session_id=session_id,
                    cart_id=cart_id or "",
                    recovery_key=recovery_key or None,
                    product_id=_line_product_id(line) or None,
                    variant_id=_line_variant_id(line) or None,
                    sku=_line_sku(line) or None,
                    name=_line_name(line) or None,
                    unit_price=_norm_price(line.get("unit_price")),
                    quantity=_norm_qty(line.get("quantity")),
                    captured_at=when,
                    capture_source=source,
                    capture_confidence=_line_capture_confidence(line),
                    content_hash=content_hash,
                )
                db.session.add(row)
                inserted += 1
    except SQLAlchemyError:
        log.warning("cart line snapshot persist failed", exc_info=True)
        return CartLineSnapshotPersistResult(
            inserted=0,
            skipped_duplicate=skipped_duplicate,
            skipped_invalid=skipped_invalid + max(0, len(lines) - skipped_duplicate),
        )

    return CartLineSnapshotPersistResult(
        inserted=inserted,
        skipped_duplicate=skipped_duplicate,
        skipped_invalid=skipped_invalid,
    )


def try_persist_cart_line_snapshots_from_payload(
    payload: dict[str, Any],
    *,
    capture_source: str,
) -> None:
    """Non-blocking delegate hook for ``main.py`` — never raises."""
    try:
        persist_cart_line_snapshots_from_payload(payload, capture_source=capture_source)
    except Exception as exc:  # noqa: BLE001
        log.debug("cart line snapshot persist skipped: %s", exc)


def lines_for_cart(
    store_slug: str,
    cart_id: str,
    *,
    limit: int = 100,
) -> list[CartLineSnapshot]:
    """Read-only: snapshots for one cart id within a store."""
    slug = (store_slug or "").strip()[:255]
    cid = (cart_id or "").strip()[:255]
    if not slug or not cid:
        return []
    ensure_cart_line_snapshots_schema(db)
    try:
        return (
            db.session.query(CartLineSnapshot)
            .filter(
                CartLineSnapshot.store_slug == slug,
                CartLineSnapshot.cart_id == cid,
            )
            .order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def lines_for_session(
    store_slug: str,
    session_id: str,
    *,
    limit: int = 100,
) -> list[CartLineSnapshot]:
    """Read-only: snapshots for one session within a store."""
    slug = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not slug or not sid:
        return []
    ensure_cart_line_snapshots_schema(db)
    try:
        return (
            db.session.query(CartLineSnapshot)
            .filter(
                CartLineSnapshot.store_slug == slug,
                CartLineSnapshot.session_id == sid,
            )
            .order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def snapshot_count_for_store(store_slug: str) -> int:
    """Read-only: total snapshot rows for a store."""
    slug = (store_slug or "").strip()[:255]
    if not slug:
        return 0
    ensure_cart_line_snapshots_schema(db)
    try:
        return (
            db.session.query(CartLineSnapshot)
            .filter(CartLineSnapshot.store_slug == slug)
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


__all__ = [
    "CAPTURE_SOURCE_CART_ABANDONED",
    "CAPTURE_SOURCE_CART_STATE_SYNC",
    "CartLineSnapshotPersistResult",
    "lines_for_cart",
    "lines_for_session",
    "persist_cart_line_snapshots_from_payload",
    "snapshot_count_for_store",
    "try_persist_cart_line_snapshots_from_payload",
]
