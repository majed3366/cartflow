# -*- coding: utf-8 -*-
"""
Live Reality Dataset V2 seeder — production writers only.

No lab ranker, no threshold bypass, no frontend JSON injection, no Scheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Mapping

from extensions import db
from models import (
    AbandonedCart,
    CartRecoveryLog,
    CartRecoveryReason,
    Store,
    WhatsAppDeliveryTruth,
)
from services.live_reality_lab_v1.catalog_v2 import (
    NAMED_PRODUCTS,
    assert_no_generic_named_products,
    cart_product_sequence,
    catalog_inputs_v2,
    line_for_product,
    named_product_count,
    product_by_id,
)
from services.live_reality_lab_v1.contract_v1 import (
    DATASET_VERSION_V2,
    LAB_CART_ID_PREFIX_V2,
    LAB_REASON_SOURCE,
    LAB_STORE_DISPLAY_NAME_V2,
    LAB_STORE_SLUG,
    LAB_SYNTHETIC_VISIT_SOURCE,
    LAB_VISIT_TRUTH_CLASS,
    MISSING_NAME_PRODUCT_ID,
    SCENARIO_ALLOWLIST_V2,
    SCENARIO_R13,
    SCENARIO_R14,
    SCENARIO_R15,
    SCENARIO_R16,
    SCENARIO_R19,
    SCENARIO_R22,
    SCENARIO_R23,
    SCENARIO_R24,
)
from services.live_reality_lab_v1.dataset_v2 import get_scenario_manifest_v2
from services.product_data.product_catalog_normalizer_v1 import (
    catalog_input_from_line,
    resolve_canonical_identity,
)
from services.product_data.product_catalog_types_v1 import CATALOG_SOURCE_PRODUCT_IDENTITY
from services.product_data.product_catalog_v1 import upsert_catalog_product
from services.product_data.product_cart_snapshots_v1 import (
    CAPTURE_SOURCE_CART_ABANDONED,
    persist_cart_line_snapshots_from_payload,
)
from services.product_data.product_hesitation_mapping_v1 import persist_hesitation_mappings
from services.product_data.product_purchase_mapping_v1 import persist_purchase_mappings
from services.product_data.product_signal_collection_v1 import persist_product_signals
from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ABANDONED,
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_PURCHASED,
    SIGNAL_PRODUCT_RECOVERY_STARTED,
    SIGNAL_PRODUCT_VIEWED,
    SOURCE_CART_ABANDONED,
    SOURCE_PURCHASE_TRUTH,
    SOURCE_RECOVERY_TIMELINE,
)
from services.recovery_truth_timeline_v1 import (
    STATUS_CUSTOMER_REPLY,
    STATUS_PROVIDER_SENT,
    STATUS_WEBHOOK_DELIVERED,
    record_recovery_truth_event,
)

log = logging.getLogger("cartflow.live_reality_lab_v2")

CART_TARGET = 38


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def _session_id(idx: int) -> str:
    return f"lrl-v2-session-{idx:02d}"


def _cart_id(idx: int) -> str:
    return f"{LAB_CART_ID_PREFIX_V2}{idx:02d}"


def _recovery_key(idx: int) -> str:
    return f"{LAB_STORE_SLUG}:{_session_id(idx)}"


def _phone(idx: int) -> str:
    return f"+9665{80000000 + idx:08d}"


def _identity_product(product_id: str) -> dict[str, Any]:
    line = line_for_product(product_id)
    parsed = catalog_input_from_line(line)
    if parsed is None:
        raise ValueError("live_reality_lab_v2_identity_unresolved")
    resolution = resolve_canonical_identity(parsed)
    if resolution is None:
        raise ValueError("live_reality_lab_v2_identity_unresolved")
    return {
        "stable_identity_key": resolution.stable_identity_key,
        "identity_tier": resolution.identity_tier,
        "product_id": product_id,
        "mapping_confidence": resolution.capture_confidence,
    }


def _set_store_display(store: Store) -> None:
    store.widget_display_name = LAB_STORE_DISPLAY_NAME_V2[:255]
    db.session.flush()


def _upsert_catalog() -> int:
    assert_no_generic_named_products()
    n = 0
    now = _naive(_utcnow())
    for product in catalog_inputs_v2():
        upsert_catalog_product(
            LAB_STORE_SLUG,
            product,
            catalog_source=CATALOG_SOURCE_PRODUCT_IDENTITY,
            synced_at=now,
        )
        n += 1
    return n


def _base_carts() -> List[dict[str, Any]]:
    seq = cart_product_sequence()
    if len(seq) != CART_TARGET:
        raise ValueError("live_reality_lab_v2_cart_slot_mismatch")
    catalog = product_by_id()
    now = _utcnow()
    carts: List[dict[str, Any]] = []
    for idx, pid in enumerate(seq):
        meta = catalog[pid]
        carts.append(
            {
                "idx": idx,
                "product_id": pid,
                "name": str(meta.get("name") or ""),
                "price": float(meta["price"]),
                "missing_name": bool(meta.get("missing_name")),
                "has_phone": True,
                "status": "abandoned",
                "reason": None,
                "recovery_sent": False,
                "recovery_delivered": False,
                "recovery_reply": False,
                "purchased": False,
                "visit_count": 0,
                "age_hours": 6 + (idx % 40),
                "first_seen_at": now - timedelta(hours=6 + (idx % 40)),
            }
        )
    return carts


def _apply_scenario_overlay(scenario_id: str, carts: List[dict[str, Any]]) -> List[dict[str, Any]]:
    """Mutate the 38-cart board for one scenario. Never invents a second ranker."""
    named = [c for c in carts if not c["missing_name"]]

    def _mark(rows: List[dict[str, Any]], **fields: Any) -> None:
        for row in rows:
            row.update(fields)

    if scenario_id == SCENARIO_R13:
        _mark(named[:12], recovery_sent=True, recovery_delivered=True)
    elif scenario_id == SCENARIO_R14:
        _mark(named[:10], recovery_sent=True, recovery_delivered=True)
        _mark(named[:8], purchased=True, status="recovered", recovery_sent=True, recovery_delivered=True)
    elif scenario_id == SCENARIO_R15:
        for row in carts:
            row["visit_count"] = 0
    elif scenario_id == SCENARIO_R16:
        return []
    elif scenario_id == SCENARIO_R19:
        _mark(named[-2:], purchased=True, status="recovered")
    elif scenario_id == SCENARIO_R22:
        _mark(named[:10], purchased=True, status="recovered")
        _mark(named[:6], recovery_sent=True, recovery_delivered=True, recovery_reply=True)
    elif scenario_id == SCENARIO_R23:
        _mark(named[:14], recovery_sent=True, recovery_delivered=True)
    elif scenario_id == SCENARIO_R24:
        _mark(
            named[:12],
            recovery_sent=True,
            recovery_delivered=True,
            purchased=True,
            status="recovered",
        )
    return carts


def _attach_reasons(carts: List[dict[str, Any]], counts: Mapping[str, int]) -> None:
    named = [c for c in carts if not c["missing_name"]]
    cursor = 0
    for reason, count in sorted((counts or {}).items()):
        n = max(0, int(count))
        slice_rows = named[cursor : cursor + n]
        for row in slice_rows:
            row["reason"] = str(reason)
        cursor += n


def _attach_visits_from_manifest(carts: List[dict[str, Any]], visit_n: int) -> None:
    for row in carts:
        row["visit_count"] = 0
    if visit_n <= 0 or not carts:
        return
    named = [c for c in carts if not c["missing_name"]] or carts
    per = max(1, visit_n // max(len(named), 1))
    leftover = visit_n
    for row in named:
        take = min(per, leftover)
        row["visit_count"] = take
        leftover -= take
        if leftover <= 0:
            break
    i = 0
    while leftover > 0 and named:
        named[i % len(named)]["visit_count"] += 1
        leftover -= 1
        i += 1


def _persist_cart(store_id: int, spec: dict[str, Any]) -> AbandonedCart:
    idx = int(spec["idx"])
    pid = str(spec["product_id"])
    line = line_for_product(pid)
    payload = {
        "store": LAB_STORE_SLUG,
        "session_id": _session_id(idx),
        "cart_id": _cart_id(idx),
        "lines": [line],
        "lab_dataset": DATASET_VERSION_V2,
    }
    first_seen = spec["first_seen_at"]
    phone = _phone(idx) if spec.get("has_phone") else None
    status = str(spec.get("status") or "abandoned")
    recovered_at = None
    if status in {"recovered", "converted"}:
        recovered_at = _naive(_utcnow() - timedelta(hours=1))
    cart = AbandonedCart(
        store_id=int(store_id),
        zid_cart_id=_cart_id(idx),
        customer_name="عميل نور العناية" if not spec.get("missing_name") else "عميل",
        customer_phone=phone,
        cart_value=float(spec["price"]),
        status=status,
        first_seen_at=_naive(first_seen),
        last_seen_at=_naive(_utcnow() - timedelta(minutes=idx + 1)),
        recovered_at=recovered_at,
        vip_mode=False,
        recovery_session_id=_session_id(idx),
    )
    AbandonedCart.set_raw(cart, payload)
    db.session.add(cart)
    db.session.commit()
    persist_cart_line_snapshots_from_payload(
        payload,
        capture_source=CAPTURE_SOURCE_CART_ABANDONED,
        captured_at=_naive(first_seen),
    )
    ident = _identity_product(pid)
    persist_product_signals(
        store_slug=LAB_STORE_SLUG,
        session_id=_session_id(idx),
        signal_type=SIGNAL_PRODUCT_CART_ADDED,
        source=SOURCE_CART_ABANDONED,
        cart_id=_cart_id(idx),
        recovery_key=_recovery_key(idx),
        products=[ident],
        observed_at=_naive(first_seen),
    )
    persist_product_signals(
        store_slug=LAB_STORE_SLUG,
        session_id=_session_id(idx),
        signal_type=SIGNAL_PRODUCT_CART_ABANDONED,
        source=SOURCE_CART_ABANDONED,
        cart_id=_cart_id(idx),
        recovery_key=_recovery_key(idx),
        products=[ident],
        observed_at=_naive(first_seen + timedelta(minutes=8)),
    )
    return cart


def _persist_reason(spec: dict[str, Any]) -> None:
    reason = spec.get("reason")
    if not reason:
        return
    idx = int(spec["idx"])
    when = _naive(spec["first_seen_at"] + timedelta(minutes=12))
    db.session.add(
        CartRecoveryReason(
            store_slug=LAB_STORE_SLUG,
            session_id=_session_id(idx),
            reason=str(reason),
            customer_phone=_phone(idx) if spec.get("has_phone") else None,
            source=LAB_REASON_SOURCE,
            created_at=when,
            updated_at=when,
        )
    )
    db.session.flush()
    persist_hesitation_mappings(
        LAB_STORE_SLUG,
        _session_id(idx),
        cart_id=_cart_id(idx),
        recovery_key=_recovery_key(idx),
        reason=str(reason),
        captured_at=when,
    )


def _persist_recovery(spec: dict[str, Any]) -> None:
    if not spec.get("recovery_sent"):
        return
    idx = int(spec["idx"])
    rk = _recovery_key(idx)
    sid = _session_id(idx)
    cid = _cart_id(idx)
    sent_at = _naive(spec["first_seen_at"] + timedelta(hours=1))
    db.session.add(
        CartRecoveryLog(
            store_slug=LAB_STORE_SLUG,
            session_id=sid,
            cart_id=cid,
            phone=_phone(idx),
            message="متابعة سلة نور العناية",
            status="mock_sent",
            step=1,
            recovery_key=rk,
            reason_tag=str(spec.get("reason") or "") or None,
            source=LAB_REASON_SOURCE,
            provider="lab",
            provider_message_sid=f"lrl-v2-sid-{idx:02d}",
            created_at=sent_at,
            sent_at=sent_at,
        )
    )
    record_recovery_truth_event(
        recovery_key=rk,
        status=STATUS_PROVIDER_SENT,
        source=LAB_REASON_SOURCE,
        store_slug=LAB_STORE_SLUG,
        session_id=sid,
        cart_id=cid,
    )
    ident = _identity_product(str(spec["product_id"]))
    persist_product_signals(
        store_slug=LAB_STORE_SLUG,
        session_id=sid,
        signal_type=SIGNAL_PRODUCT_RECOVERY_STARTED,
        source=SOURCE_RECOVERY_TIMELINE,
        cart_id=cid,
        recovery_key=rk,
        products=[ident],
        observed_at=sent_at,
    )
    if spec.get("recovery_delivered"):
        db.session.add(
            WhatsAppDeliveryTruth(
                provider="lab",
                message_sid=f"lrl-v2-sid-{idx:02d}",
                customer_phone=_phone(idx),
                store_slug=LAB_STORE_SLUG,
                session_id=sid,
                cart_id=cid,
                recovery_key=rk,
                send_status="sent",
                delivery_status="delivered",
                truth_level="lab_mock_delivered",
                last_event_time=sent_at + timedelta(minutes=4),
            )
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_WEBHOOK_DELIVERED,
            source=LAB_REASON_SOURCE,
            store_slug=LAB_STORE_SLUG,
            session_id=sid,
            cart_id=cid,
        )
    if spec.get("recovery_reply"):
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source=LAB_REASON_SOURCE,
            store_slug=LAB_STORE_SLUG,
            session_id=sid,
            cart_id=cid,
        )


def _persist_purchase(spec: dict[str, Any]) -> None:
    if not spec.get("purchased"):
        return
    from services.cartflow_purchase_truth import record_purchase  # noqa: PLC0415

    idx = int(spec["idx"])
    when = _naive(spec["first_seen_at"] + timedelta(hours=5))
    record_purchase(
        recovery_key=_recovery_key(idx),
        purchase_source=SOURCE_PURCHASE_TRUTH,
        store_slug=LAB_STORE_SLUG,
        session_id=_session_id(idx),
        cart_id=_cart_id(idx),
        order_id=f"lrl-v2-order-{idx:02d}",
        customer_phone=_phone(idx),
        evidence_detail="live_reality_dataset_v2",
        purchase_time=when,
        apply_lifecycle=True,
    )
    persist_purchase_mappings(
        LAB_STORE_SLUG,
        _session_id(idx),
        cart_id=_cart_id(idx),
        recovery_key=_recovery_key(idx),
        order_id=f"lrl-v2-order-{idx:02d}",
        purchase_source=SOURCE_PURCHASE_TRUTH,
        purchased_at=when,
    )
    ident = _identity_product(str(spec["product_id"]))
    persist_product_signals(
        store_slug=LAB_STORE_SLUG,
        session_id=_session_id(idx),
        signal_type=SIGNAL_PRODUCT_PURCHASED,
        source=SOURCE_PURCHASE_TRUTH,
        cart_id=_cart_id(idx),
        recovery_key=_recovery_key(idx),
        products=[ident],
        observed_at=when,
    )


def _persist_synthetic_visits(spec: dict[str, Any]) -> int:
    n = int(spec.get("visit_count") or 0)
    if n <= 0:
        return 0
    ident = _identity_product(str(spec["product_id"]))
    inserted = 0
    for hop in range(n):
        result = persist_product_signals(
            store_slug=LAB_STORE_SLUG,
            session_id=_session_id(int(spec["idx"])),
            signal_type=SIGNAL_PRODUCT_VIEWED,
            source=LAB_SYNTHETIC_VISIT_SOURCE,
            cart_id=_cart_id(int(spec["idx"])),
            recovery_key=_recovery_key(int(spec["idx"])),
            products=[
                {
                    **ident,
                    "evidence_ref_type": "lab_synthetic_visit",
                    "evidence_ref_id": f"lrl-v2-visit-{spec['idx']:02d}-{hop}",
                }
            ],
            observed_at=_naive(spec["first_seen_at"] - timedelta(hours=hop + 1)),
        )
        inserted += int(getattr(result, "inserted", 0) or 0)
    return inserted


def _seed_orphan_visits(count: int) -> int:
    """R16: visits without carts. Still lab-synthetic, still named products."""
    named_ids = [p[0] for p in NAMED_PRODUCTS]
    n = max(0, int(count))
    inserted = 0
    now = _utcnow()
    for i in range(n):
        pid = named_ids[i % len(named_ids)]
        ident = _identity_product(pid)
        result = persist_product_signals(
            store_slug=LAB_STORE_SLUG,
            session_id=f"lrl-v2-visit-only-{i:02d}",
            signal_type=SIGNAL_PRODUCT_VIEWED,
            source=LAB_SYNTHETIC_VISIT_SOURCE,
            cart_id="",
            products=[
                {
                    **ident,
                    "evidence_ref_type": "lab_synthetic_visit",
                    "evidence_ref_id": f"lrl-v2-orphan-visit-{i:02d}",
                }
            ],
            observed_at=_naive(now - timedelta(hours=i + 1)),
        )
        inserted += int(getattr(result, "inserted", 0) or 0)
    return inserted


def _ensure_v2_write_schemas() -> None:
    """Warm production schema guards before lab writes hold a SQLite transaction."""
    if str(getattr(db.engine.dialect, "name", "") or "") == "sqlite":
        return
    from schema_cart_line_snapshots_v1 import (  # noqa: PLC0415
        ensure_cart_line_snapshots_schema,
    )
    from schema_product_catalog_v1 import ensure_product_catalog_schema  # noqa: PLC0415
    from schema_product_hesitation_mapping_v1 import (  # noqa: PLC0415
        ensure_product_hesitation_mapping_schema,
    )
    from schema_product_purchase_mapping_v1 import (  # noqa: PLC0415
        ensure_product_purchase_mapping_schema,
    )
    from schema_product_signal_events_v1 import (  # noqa: PLC0415
        ensure_product_signal_events_schema,
    )

    ensure_product_catalog_schema(db)
    ensure_cart_line_snapshots_schema(db)
    ensure_product_signal_events_schema(db)
    ensure_product_hesitation_mapping_schema(db)
    ensure_product_purchase_mapping_schema(db)


def seed_dataset_v2(*, store: Store, scenario_id: str) -> dict[str, Any]:
    sid = str(scenario_id or "").strip()
    if sid not in SCENARIO_ALLOWLIST_V2:
        raise ValueError("live_reality_lab_unknown_scenario")
    manifest = get_scenario_manifest_v2(sid)
    truth = manifest.get("truth") or {}
    store_id = int(store.id)
    _ensure_v2_write_schemas()
    _set_store_display(store)
    catalog_n = _upsert_catalog()
    carts = _base_carts()
    carts = _apply_scenario_overlay(sid, carts)
    _attach_reasons(carts, truth.get("reason_counts") or {})
    if sid != SCENARIO_R16:
        _attach_visits_from_manifest(carts, int(truth.get("synthetic_visit_count") or 0))
    db.session.commit()

    seeded_carts = 0
    seeded_visits = 0
    for spec in carts:
        try:
            _persist_cart(store_id, spec)
            db.session.commit()
            seeded_carts += 1
        except Exception:
            db.session.rollback()
            raise
    for spec in carts:
        try:
            _persist_reason(spec)
            _persist_recovery(spec)
            _persist_purchase(spec)
            seeded_visits += _persist_synthetic_visits(spec)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
    if sid == SCENARIO_R16:
        try:
            seeded_visits += _seed_orphan_visits(int(truth.get("synthetic_visit_count") or 0))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    log.info(
        "live_reality_lab_v2_seed scenario=%s carts=%s catalog=%s visits=%s class=%s",
        sid,
        seeded_carts,
        catalog_n,
        seeded_visits,
        LAB_VISIT_TRUTH_CLASS if seeded_visits else "none",
    )
    return {
        "ok": True,
        "dataset_version": DATASET_VERSION_V2,
        "store_display_name": LAB_STORE_DISPLAY_NAME_V2,
        "named_products": named_product_count(),
        "missing_name_fixture": 1,
        "carts": seeded_carts,
        "synthetic_visits": seeded_visits,
        "visit_truth_class": LAB_VISIT_TRUTH_CLASS if seeded_visits else None,
        "manifest": manifest,
    }


__all__ = ["CART_TARGET", "seed_dataset_v2"]
