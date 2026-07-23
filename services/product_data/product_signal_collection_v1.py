# -*- coding: utf-8 -*-
"""
Product Signal Collection V1 — durable atomic product facts.

Collects governed product signals for future Product Performance foundations.
Never analyzes, scores, ranks, or decides. Insert-only; never raises to callers
when used via try_* / hook delegates.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import CartLineSnapshot, ProductSignalEvent
from schema_product_signal_events_v1 import ensure_product_signal_events_schema
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_signal_collection_flag_v1 import (
    product_signal_collection_v1_enabled,
)
from services.product_data.product_signal_types_v1 import (
    EVIDENCE_REF_CART_LINE_SNAPSHOT,
    EVIDENCE_REF_HESITATION_MAPPING,
    EVIDENCE_REF_PURCHASE_MAPPING,
    EVIDENCE_REF_RECOVERY_TIMELINE,
    EVIDENCE_REF_SESSION,
    ProductSignalPersistResult,
    RECOVERY_START_STATUSES,
    SIGNAL_PRODUCT_CART_ABANDONED,
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CART_REMOVED,
    SIGNAL_PRODUCT_CART_SYNCED,
    SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_EVIDENCE_LINKED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
    SIGNAL_PRODUCT_RECOVERY_PROGRESSED,
    SIGNAL_PRODUCT_RECOVERY_STARTED,
    SOURCE_BEHAVIORAL_RETURN,
    SOURCE_CART_ABANDONED,
    SOURCE_CART_STATE_SYNC,
    SOURCE_PURCHASE_TRUTH,
    SOURCE_REASON_CAPTURE,
    SOURCE_RECOVERY_TIMELINE,
    product_signal_to_dict,
    signal_family_for_type,
)

log = logging.getLogger("cartflow")

MAX_PRODUCTS_PER_EVENT = 20
MAX_SESSION_SNAPSHOTS = 50


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _norm(value: Any, *, max_len: int) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    return s[:max_len]


def _dedup_hash(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    signal_type: str,
    stable_identity_key: str,
    source: str,
    evidence_ref_type: str,
    evidence_ref_id: str,
    observed_at: datetime,
) -> str:
    canonical = {
        "store_slug": store_slug,
        "session_id": session_id,
        "cart_id": cart_id,
        "signal_type": signal_type,
        "stable_identity_key": stable_identity_key,
        "source": source,
        "evidence_ref_type": evidence_ref_type or "",
        "evidence_ref_id": evidence_ref_id or "",
        "observed_at": observed_at.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    raw = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _products_from_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for line in lines:
        if not isinstance(line, dict):
            continue
        product = catalog_input_from_line(line)
        if product is None:
            continue
        resolution = resolve_canonical_identity(product)
        if resolution is None:
            continue
        key = resolution.stable_identity_key
        if key in by_key:
            continue
        by_key[key] = {
            "stable_identity_key": key,
            "identity_tier": getattr(resolution, "identity_tier", "") or "",
            "product_id": (product.product_id or None),
        }
        if len(by_key) >= MAX_PRODUCTS_PER_EVENT:
            break
    return list(by_key.values())


def _products_from_session_snapshots(
    store_slug: str,
    session_id: str,
) -> list[dict[str, Any]]:
    try:
        snaps = (
            db.session.query(CartLineSnapshot)
            .filter(
                CartLineSnapshot.store_slug == store_slug,
                CartLineSnapshot.session_id == session_id,
            )
            .order_by(CartLineSnapshot.captured_at.desc(), CartLineSnapshot.id.desc())
            .limit(MAX_SESSION_SNAPSHOTS)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []

    by_key: dict[str, dict[str, Any]] = {}
    for snap in snaps:
        line = {
            "product_id": snap.product_id,
            "variant_id": snap.variant_id,
            "sku": snap.sku,
            "name": snap.name,
            "unit_price": snap.unit_price,
            "quantity": snap.quantity,
        }
        product = catalog_input_from_line(line)
        if product is None:
            continue
        resolution = resolve_canonical_identity(product)
        if resolution is None:
            continue
        key = resolution.stable_identity_key
        if key in by_key:
            continue
        by_key[key] = {
            "stable_identity_key": key,
            "identity_tier": getattr(resolution, "identity_tier", "") or "",
            "product_id": (product.product_id or None),
            "evidence_ref_type": EVIDENCE_REF_CART_LINE_SNAPSHOT,
            "evidence_ref_id": str(int(snap.id)),
        }
        if len(by_key) >= MAX_PRODUCTS_PER_EVENT:
            break
    return list(by_key.values())


def _resolve_products(
    *,
    store_slug: str,
    session_id: str,
    payload: Optional[dict[str, Any]] = None,
) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        try:
            from services.product_data.product_cart_snapshots_v1 import (  # noqa: PLC0415
                _extract_lines,
            )

            lines = _extract_lines(payload)
            from_lines = _products_from_lines(lines)
            if from_lines:
                return from_lines
        except Exception:  # noqa: BLE001
            pass
    if store_slug and session_id:
        return _products_from_session_snapshots(store_slug, session_id)
    return []


def persist_product_signals(
    *,
    store_slug: str,
    session_id: str,
    signal_type: str,
    source: str,
    cart_id: str = "",
    recovery_key: Optional[str] = None,
    products: Optional[list[dict[str, Any]]] = None,
    observed_at: Optional[datetime] = None,
    evidence_ref_type: Optional[str] = None,
    evidence_ref_id: Optional[str] = None,
    also_evidence_linked: bool = False,
) -> ProductSignalPersistResult:
    """Insert atomic product signals. No interpretation."""
    if not product_signal_collection_v1_enabled():
        return ProductSignalPersistResult(skipped_disabled=1)

    slug = _norm(store_slug, max_len=255)
    sid = _norm(session_id, max_len=512)
    st = _norm(signal_type, max_len=64)
    src = _norm(source, max_len=128)
    family = signal_family_for_type(st)
    if not slug or not st or not src or not family:
        return ProductSignalPersistResult(skipped_invalid=1)

    cid = _norm(cart_id, max_len=255)
    rkey = _norm(recovery_key, max_len=512) or None
    when = _naive(observed_at or _utc_now())
    product_rows = list(products or [])
    if not product_rows:
        return ProductSignalPersistResult(skipped_empty=1)

    ensure_product_signal_events_schema(db)
    inserted = 0
    skipped_duplicate = 0
    skipped_invalid = 0
    default_eref_type = _norm(evidence_ref_type, max_len=64)
    default_eref_id = _norm(evidence_ref_id, max_len=128)

    try:
        with db.session.begin_nested():
            for product in product_rows[:MAX_PRODUCTS_PER_EVENT]:
                if not isinstance(product, dict):
                    skipped_invalid += 1
                    continue
                key = _norm(product.get("stable_identity_key"), max_len=256)
                if not key:
                    skipped_invalid += 1
                    continue
                tier = _norm(product.get("identity_tier"), max_len=8)
                pid = _norm(product.get("product_id"), max_len=128) or None
                eref_type = (
                    _norm(product.get("evidence_ref_type"), max_len=64)
                    or default_eref_type
                )
                eref_id = (
                    _norm(product.get("evidence_ref_id"), max_len=128)
                    or default_eref_id
                )
                if also_evidence_linked and not (eref_type and eref_id):
                    eref_type = eref_type or EVIDENCE_REF_SESSION
                    eref_id = eref_id or sid
                types_to_write = [st]
                if also_evidence_linked and eref_type and eref_id:
                    types_to_write.append(SIGNAL_PRODUCT_EVIDENCE_LINKED)

                for write_type in types_to_write:
                    write_family = signal_family_for_type(write_type)
                    if not write_family:
                        continue
                    dedup = _dedup_hash(
                        store_slug=slug,
                        session_id=sid,
                        cart_id=cid,
                        signal_type=write_type,
                        stable_identity_key=key,
                        source=src,
                        evidence_ref_type=eref_type,
                        evidence_ref_id=eref_id,
                        observed_at=when,
                    )
                    exists = (
                        db.session.query(ProductSignalEvent.id)
                        .filter(ProductSignalEvent.dedup_hash == dedup)
                        .limit(1)
                        .first()
                    )
                    if exists is not None:
                        skipped_duplicate += 1
                        continue
                    row = ProductSignalEvent(
                        store_slug=slug,
                        session_id=sid,
                        cart_id=cid,
                        recovery_key=rkey,
                        stable_identity_key=key,
                        identity_tier=tier,
                        product_id=pid,
                        signal_family=write_family,
                        signal_type=write_type,
                        observed_at=when,
                        source=src,
                        evidence_ref_type=eref_type or None,
                        evidence_ref_id=eref_id or None,
                        dedup_hash=dedup,
                    )
                    db.session.add(row)
                    inserted += 1
        if inserted:
            db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        log.warning("product signal persist failed", exc_info=True)
        return ProductSignalPersistResult(skipped_invalid=1)

    return ProductSignalPersistResult(
        inserted=inserted,
        skipped_duplicate=skipped_duplicate,
        skipped_invalid=skipped_invalid,
    )


def _identity_from_payload(payload: dict[str, Any]) -> tuple[str, str, str, Optional[str]]:
    store = _norm(
        payload.get("store") or payload.get("store_slug"),
        max_len=255,
    )
    session_id = _norm(payload.get("session_id"), max_len=512)
    cart_id = _norm(payload.get("cart_id"), max_len=255)
    recovery_key = _norm(payload.get("recovery_key"), max_len=512) or None
    return store, session_id, cart_id, recovery_key


def collect_from_cart_payload(
    payload: dict[str, Any],
    *,
    event_hint: str | None = None,
) -> ProductSignalPersistResult:
    """Collect cart / checkout activity signals from cart-event payload."""
    if not product_signal_collection_v1_enabled():
        return ProductSignalPersistResult(skipped_disabled=1)
    if not isinstance(payload, dict):
        return ProductSignalPersistResult(skipped_invalid=1)

    store, session_id, cart_id, recovery_key = _identity_from_payload(payload)
    if not store or not session_id:
        return ProductSignalPersistResult(skipped_invalid=1)

    ev = _norm(event_hint or payload.get("event"), max_len=64).lower()
    reason = _norm(payload.get("reason"), max_len=64).lower()
    ctx = _norm(
        payload.get("recovery_return_context") or payload.get("return_context"),
        max_len=64,
    ).lower()

    if ev == "cart_abandoned":
        signal_type = SIGNAL_PRODUCT_CART_ABANDONED
        source = SOURCE_CART_ABANDONED
    elif reason == "checkout" or ctx == "checkout":
        signal_type = SIGNAL_PRODUCT_CHECKOUT_TOUCHED
        source = SOURCE_CART_STATE_SYNC if ev == "cart_state_sync" else SOURCE_CART_STATE_SYNC
    elif reason == "add":
        signal_type = SIGNAL_PRODUCT_CART_ADDED
        source = SOURCE_CART_STATE_SYNC
    elif reason == "remove":
        signal_type = SIGNAL_PRODUCT_CART_REMOVED
        source = SOURCE_CART_STATE_SYNC
    elif ev == "cart_state_sync":
        signal_type = SIGNAL_PRODUCT_CART_SYNCED
        source = SOURCE_CART_STATE_SYNC
    else:
        return ProductSignalPersistResult(skipped_invalid=1)

    products = _resolve_products(
        store_slug=store, session_id=session_id, payload=payload
    )
    return persist_product_signals(
        store_slug=store,
        session_id=session_id,
        cart_id=cart_id,
        recovery_key=recovery_key,
        signal_type=signal_type,
        source=source,
        products=products,
        also_evidence_linked=True,
    )


def collect_from_hesitation(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    mapping_ids: Optional[list[int]] = None,
) -> ProductSignalPersistResult:
    products = _resolve_products(store_slug=store_slug, session_id=session_id)
    if mapping_ids and products:
        # Attach first mapping id as shared evidence when provided
        mid = str(int(mapping_ids[0]))
        for p in products:
            p.setdefault("evidence_ref_type", EVIDENCE_REF_HESITATION_MAPPING)
            p.setdefault("evidence_ref_id", mid)
    return persist_product_signals(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id or "",
        recovery_key=recovery_key,
        signal_type=SIGNAL_PRODUCT_INTEREST_HESITATION,
        source=SOURCE_REASON_CAPTURE,
        products=products,
        also_evidence_linked=True,
    )


def collect_from_purchase(
    store_slug: str,
    session_id: str,
    *,
    cart_id: Optional[str] = None,
    recovery_key: Optional[str] = None,
    order_id: Optional[str] = None,
    purchased_at: Optional[datetime] = None,
) -> ProductSignalPersistResult:
    products = _resolve_products(store_slug=store_slug, session_id=session_id)
    eref_type = EVIDENCE_REF_PURCHASE_MAPPING if order_id or recovery_key else EVIDENCE_REF_SESSION
    eref_id = _norm(order_id or recovery_key or session_id, max_len=128)
    return persist_product_signals(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id or "",
        recovery_key=recovery_key,
        signal_type=SIGNAL_PRODUCT_PURCHASED,
        source=SOURCE_PURCHASE_TRUTH,
        products=products,
        observed_at=purchased_at,
        evidence_ref_type=eref_type,
        evidence_ref_id=eref_id,
        also_evidence_linked=True,
    )


def collect_from_recovery_timeline(
    *,
    store_slug: str,
    session_id: str,
    status: str,
    source: str = SOURCE_RECOVERY_TIMELINE,
    cart_id: str = "",
    recovery_key: Optional[str] = None,
    timeline_event_id: Optional[int] = None,
) -> ProductSignalPersistResult:
    st = _norm(status, max_len=64).lower()
    if not st:
        return ProductSignalPersistResult(skipped_invalid=1)
    signal_type = (
        SIGNAL_PRODUCT_RECOVERY_STARTED
        if st in RECOVERY_START_STATUSES
        else SIGNAL_PRODUCT_RECOVERY_PROGRESSED
    )
    products = _resolve_products(store_slug=store_slug, session_id=session_id)
    eref_id = str(int(timeline_event_id)) if timeline_event_id else _norm(recovery_key or session_id, max_len=128)
    return persist_product_signals(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
        recovery_key=recovery_key,
        signal_type=signal_type,
        source=_norm(source, max_len=128) or SOURCE_RECOVERY_TIMELINE,
        products=products,
        evidence_ref_type=EVIDENCE_REF_RECOVERY_TIMELINE,
        evidence_ref_id=eref_id,
        also_evidence_linked=True,
    )


def collect_from_customer_return(
    payload: dict[str, Any],
) -> ProductSignalPersistResult:
    if not isinstance(payload, dict):
        return ProductSignalPersistResult(skipped_invalid=1)
    store, session_id, cart_id, recovery_key = _identity_from_payload(payload)
    if not store or not session_id:
        return ProductSignalPersistResult(skipped_invalid=1)
    products = _resolve_products(
        store_slug=store, session_id=session_id, payload=payload
    )
    ctx = _norm(
        payload.get("recovery_return_context") or payload.get("return_context"),
        max_len=64,
    ).lower()
    # Return always records customer_return; checkout context also records checkout touch.
    result = persist_product_signals(
        store_slug=store,
        session_id=session_id,
        cart_id=cart_id,
        recovery_key=recovery_key,
        signal_type=SIGNAL_PRODUCT_CUSTOMER_RETURNED,
        source=SOURCE_BEHAVIORAL_RETURN,
        products=products,
        evidence_ref_type=EVIDENCE_REF_SESSION,
        evidence_ref_id=session_id,
        also_evidence_linked=True,
    )
    if ctx == "checkout" and products:
        persist_product_signals(
            store_slug=store,
            session_id=session_id,
            cart_id=cart_id,
            recovery_key=recovery_key,
            signal_type=SIGNAL_PRODUCT_CHECKOUT_TOUCHED,
            source=SOURCE_BEHAVIORAL_RETURN,
            products=products,
            evidence_ref_type=EVIDENCE_REF_SESSION,
            evidence_ref_id=session_id,
        )
    return result


def signal_count_for_store(store_slug: str) -> int:
    slug = _norm(store_slug, max_len=255)
    if not slug:
        return 0
    ensure_product_signal_events_schema(db)
    try:
        return (
            db.session.query(ProductSignalEvent.id)
            .filter(ProductSignalEvent.store_slug == slug)
            .count()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


def signals_for_store(
    store_slug: str,
    *,
    limit: int = 100,
    signal_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    slug = _norm(store_slug, max_len=255)
    if not slug:
        return []
    ensure_product_signal_events_schema(db)
    try:
        q = db.session.query(ProductSignalEvent).filter(
            ProductSignalEvent.store_slug == slug
        )
        if signal_type:
            q = q.filter(ProductSignalEvent.signal_type == _norm(signal_type, max_len=64))
        rows = (
            q.order_by(ProductSignalEvent.observed_at.desc(), ProductSignalEvent.id.desc())
            .limit(max(1, min(int(limit), 500)))
            .all()
        )
        return [product_signal_to_dict(r) for r in rows]
    except SQLAlchemyError:
        db.session.rollback()
        return []


__all__ = [
    "persist_product_signals",
    "collect_from_cart_payload",
    "collect_from_hesitation",
    "collect_from_purchase",
    "collect_from_recovery_timeline",
    "collect_from_customer_return",
    "signal_count_for_store",
    "signals_for_store",
]
