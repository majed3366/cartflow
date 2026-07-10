# -*- coding: utf-8 -*-
"""
Demo Commerce Lab V1 — authoritative Lab Reset (P1).

Demo store only. Idempotent. Deterministic baseline for Scenario 1.
No UI. No scenario runner. No new tables.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import (
    AbandonedCart,
    AbandonmentReasonLog,
    CartRecoveryLog,
    CartRecoveryReason,
    MerchantCartLifecycleArchive,
    MovementSnapshot,
    PurchaseTruthRecord,
    RecoverySchedule,
    RecoveryTruthTimelineEvent,
    Store,
)
from services.cf_test_phone_override import normalize_cf_test_customer_phone
from services.demo_pi_fresh_session import purge_demo_recovery_rows_for_test_phone

log = logging.getLogger("cartflow")

LAB_STORE_SLUG = "demo"
LAB_SESSION_ID = "s_lab_v1_s1"
LAB_CART_ID = "cf_cart_lab_v1_s1"
# Production recovery_key prefers stable cf_cart_* over session_id.
LAB_RECOVERY_KEY = f"{LAB_STORE_SLUG}:{LAB_CART_ID}"
# Dedicated Lab customer line — NOT CARTFLOW_DEMO_TEST_PHONE.
# Production treats the demo test phone as merchant-equal and blocks scheduling.
LAB_CUSTOMER_PHONE = "966511114449"

# Browser keys the Scenario 1 runner must clear (no UI in P1 — returned for clients).
LAB_CLIENT_STORAGE_CLEAR = (
    "demo_cart",
    "cartflow_recovery_session_id",
    "cartflow_cart_event_id",
    "cartflow_converted",
    "cartflow_recovery_return_state_v1",
    "cartflow_test_customer_phone",
)

_ERROR_REJECTED = "lab_reset_rejected"


def _norm_slug(value: Any) -> str:
    return str(value or "").strip()


def _pn_match(db_val: Any, target_norm: str) -> bool:
    if not target_norm:
        return False
    if db_val is None or not str(db_val).strip():
        return False
    return normalize_cf_test_customer_phone(db_val) == target_norm


def _reject(reason: str, **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": False,
        "error": _ERROR_REJECTED,
        "reject_reason": reason,
        "store_slug": LAB_STORE_SLUG,
    }
    out.update(extra)
    return out


def validate_lab_reset_scope(
    *,
    store_slug: str,
    merchant_activation: bool = False,
) -> Optional[dict[str, Any]]:
    """Hard gates — no writes when this returns a reject payload."""
    if bool(merchant_activation):
        return _reject("merchant_activation_forbidden")
    ss = _norm_slug(store_slug)
    if ss != LAB_STORE_SLUG:
        return _reject("store_slug_must_be_demo", requested_store_slug=ss)
    return None


def lab_baseline_identity() -> dict[str, str]:
    return {
        "store_slug": LAB_STORE_SLUG,
        "session_id": LAB_SESSION_ID,
        "cart_id": LAB_CART_ID,
        "recovery_key": LAB_RECOVERY_KEY,
        "customer_phone": LAB_CUSTOMER_PHONE,
    }


def _clear_lab_phone_miss_cooldown(phone: str = "") -> None:
    """Clear in-process no-phone miss cooldown for Lab identity keys."""
    try:
        import main as main_mod  # noqa: PLC0415

        clear_fn = getattr(main_mod, "_normal_recovery_no_phone_miss_clear", None)
        key_fn = getattr(main_mod, "_normal_recovery_no_phone_miss_cache_key", None)
        if not callable(clear_fn) or not callable(key_fn):
            return
        for sid, cid in (
            (LAB_SESSION_ID, LAB_CART_ID),
            (LAB_SESSION_ID, None),
            (LAB_CART_ID, LAB_CART_ID),
        ):
            clear_fn(key_fn(LAB_STORE_SLUG, sid, cid))
        _ = phone
    except Exception:  # noqa: BLE001
        pass


def _clear_lab_memory() -> None:
    """Drop in-process recovery/session/purchase truth for the fixed Lab keys only."""
    rk = LAB_RECOVERY_KEY
    rk_session = f"{LAB_STORE_SLUG}:{LAB_SESSION_ID}"
    lab_keys = (rk, rk_session, LAB_SESSION_ID, LAB_CART_ID)
    try:
        from services.recovery_session_phone import (  # noqa: PLC0415
            recovery_phone_memory_clear,
        )

        recovery_phone_memory_clear()
    except Exception:  # noqa: BLE001
        pass
    try:
        import main as main_mod  # noqa: PLC0415

        for name in (
            "_session_recovery_started",
            "_session_recovery_logged",
            "_session_recovery_sent",
            "_session_recovery_converted",
            "_session_recovery_returned",
            "_session_recovery_flow_armed_at",
            "_session_recovery_delay_wait_started_at",
            "_session_recovery_send_count",
            "_session_recovery_multi_logged",
            "_session_recovery_multi_attempt_cap",
            "_session_recovery_multi_verified_indexes",
            "_session_recovery_seq_logged",
            "_session_recovery_followup_next_due_at",
            "_session_recovery_last_second_skip_reason",
            "_recovery_pending_reason_arm_ctx",
            "_recovery_pending_phone_arm_ctx",
        ):
            bucket = getattr(main_mod, name, None)
            if isinstance(bucket, dict):
                for k in lab_keys:
                    bucket.pop(k, None)
    except Exception:  # noqa: BLE001
        pass
    try:
        from services import cartflow_purchase_truth as cpt  # noqa: PLC0415

        with cpt._lock:
            for k in lab_keys:
                cpt._memory_records.pop(k, None)
    except Exception:  # noqa: BLE001
        pass
    try:
        from services import purchase_lifecycle_closure as plc  # noqa: PLC0415

        with plc._lock:
            for k in lab_keys:
                plc._closed_keys.discard(k)
    except Exception:  # noqa: BLE001
        pass
    _clear_lab_phone_miss_cooldown()


def _delete_count(query) -> int:
    n = query.delete(synchronize_session=False)
    return int(n or 0)


def _purge_lab_key_scoped(store_slug: str, phone_norm: str) -> dict[str, int]:
    """
    Clear schedules / timeline / purchase / archive for Lab identity and phone
    on demo only. Complements purge_demo_recovery_rows_for_test_phone.
    """
    ss = store_slug
    rk = LAB_RECOVERY_KEY
    sid = LAB_SESSION_ID
    cid = LAB_CART_ID
    counts: dict[str, int] = {}

    n = 0
    for row in (
        db.session.query(RecoverySchedule)
        .filter(RecoverySchedule.store_slug == ss)
        .all()
    ):
        row_rk = _norm_slug(getattr(row, "recovery_key", None))
        row_sid = _norm_slug(getattr(row, "session_id", None))
        row_cid = _norm_slug(getattr(row, "cart_id", None))
        if (
            row_rk == rk
            or row_sid == sid
            or (cid and row_cid == cid)
            or _pn_match(getattr(row, "customer_phone", None), phone_norm)
        ):
            db.session.delete(row)
            n += 1
    counts["recovery_schedules"] = n

    n = 0
    for row in (
        db.session.query(RecoveryTruthTimelineEvent)
        .filter(RecoveryTruthTimelineEvent.store_slug == ss)
        .all()
    ):
        if (
            _norm_slug(getattr(row, "recovery_key", None)) == rk
            or _norm_slug(getattr(row, "session_id", None)) == sid
        ):
            db.session.delete(row)
            n += 1
    counts["recovery_truth_timeline_events"] = n

    n = 0
    for row in (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.store_slug == ss)
        .all()
    ):
        if (
            _norm_slug(getattr(row, "recovery_key", None)) == rk
            or _norm_slug(getattr(row, "session_id", None)) == sid
            or _pn_match(getattr(row, "customer_phone", None), phone_norm)
        ):
            db.session.delete(row)
            n += 1
    counts["purchase_truth_records"] = n

    counts["merchant_cart_lifecycle_archives"] = _delete_count(
        db.session.query(MerchantCartLifecycleArchive).filter(
            MerchantCartLifecycleArchive.store_slug == ss,
            MerchantCartLifecycleArchive.recovery_key == rk,
        )
    )

    counts["lab_session_cart_recovery_reasons"] = _delete_count(
        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == ss,
            CartRecoveryReason.session_id == sid,
        )
    )
    counts["lab_session_cart_recovery_logs"] = _delete_count(
        db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == ss,
            CartRecoveryLog.session_id == sid,
        )
    )
    counts["lab_session_abandonment_reason_logs"] = _delete_count(
        db.session.query(AbandonmentReasonLog).filter(
            AbandonmentReasonLog.store_slug == ss,
            AbandonmentReasonLog.session_id == sid,
        )
    )

    # Also clear session-keyed purchase/timeline leftovers (pre-stable-cart identity).
    rk_session = f"{ss}:{sid}"
    counts["purchase_truth_records_session_key"] = _delete_count(
        db.session.query(PurchaseTruthRecord).filter(
            PurchaseTruthRecord.store_slug == ss,
            PurchaseTruthRecord.recovery_key == rk_session,
        )
    )
    counts["movement_snapshots"] = _delete_count(
        db.session.query(MovementSnapshot).filter(
            MovementSnapshot.store_slug == ss,
            MovementSnapshot.recovery_key.in_((rk, rk_session, cid)),
        )
    )

    return counts


def verify_lab_baseline(*, store_slug: str = LAB_STORE_SLUG, cf_test_phone: str = "") -> dict[str, Any]:
    """Post-reset checks — Lab key and Lab phone must be empty on demo."""
    gate = validate_lab_reset_scope(store_slug=store_slug, merchant_activation=False)
    if gate is not None:
        return gate

    phone = (
        normalize_cf_test_customer_phone(cf_test_phone)
        or (cf_test_phone or "").strip()
        or LAB_CUSTOMER_PHONE
    )
    ss = LAB_STORE_SLUG
    rk = LAB_RECOVERY_KEY
    sid = LAB_SESSION_ID

    st = db.session.query(Store).filter(Store.zid_store_id == ss).first()
    store_id = int(st.id) if st is not None else None
    catalog_present = bool(
        st is not None and str(getattr(st, "cf_product_catalog_json", None) or "").strip()
    )

    abandoned = 0
    if store_id is not None:
        for ac in (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.store_id == store_id)
            .all()
        ):
            if _pn_match(getattr(ac, "customer_phone", None), phone):
                abandoned += 1
            elif _norm_slug(getattr(ac, "recovery_session_id", None)) == sid:
                abandoned += 1
            elif _norm_slug(getattr(ac, "zid_cart_id", None)) == LAB_CART_ID:
                abandoned += 1

    purchase_n = (
        db.session.query(PurchaseTruthRecord)
        .filter(
            PurchaseTruthRecord.store_slug == ss,
            PurchaseTruthRecord.recovery_key == rk,
        )
        .count()
    )
    timeline_n = (
        db.session.query(RecoveryTruthTimelineEvent)
        .filter(
            RecoveryTruthTimelineEvent.store_slug == ss,
            RecoveryTruthTimelineEvent.recovery_key == rk,
        )
        .count()
    )
    schedule_n = (
        db.session.query(RecoverySchedule)
        .filter(
            RecoverySchedule.store_slug == ss,
            RecoverySchedule.recovery_key == rk,
        )
        .count()
    )
    reason_n = (
        db.session.query(CartRecoveryReason)
        .filter(
            CartRecoveryReason.store_slug == ss,
            CartRecoveryReason.session_id == sid,
        )
        .count()
    )

    clean = (
        abandoned == 0
        and purchase_n == 0
        and timeline_n == 0
        and schedule_n == 0
        and reason_n == 0
    )
    return {
        "ok": True,
        "clean": clean,
        "store_slug": ss,
        "recovery_key": rk,
        "session_id": sid,
        "cart_id": LAB_CART_ID,
        "lab_phone": phone,
        "counts": {
            "abandoned_carts": abandoned,
            "purchase_truth_records": int(purchase_n),
            "recovery_truth_timeline_events": int(timeline_n),
            "recovery_schedules": int(schedule_n),
            "cart_recovery_reasons": int(reason_n),
        },
        "preserved": {
            "store_row_present": st is not None,
            "catalog_json_present": catalog_present,
        },
        "identity": lab_baseline_identity(),
    }


def lab_reset_v1(
    *,
    store_slug: str = LAB_STORE_SLUG,
    cf_test_phone: str = "",
    merchant_activation: bool = False,
) -> dict[str, Any]:
    """
    Authoritative Demo Lab Reset.

    Clears demo runtime truth for the Lab phone + fixed Lab identity.
    Preserves Store/catalog. Rejects non-demo and merchant_activation.
    """
    gate = validate_lab_reset_scope(
        store_slug=store_slug,
        merchant_activation=merchant_activation,
    )
    if gate is not None:
        return gate

    phone_raw = (cf_test_phone or "").strip() or LAB_CUSTOMER_PHONE
    phone_norm = normalize_cf_test_customer_phone(phone_raw) or phone_raw
    if not phone_norm:
        return _reject("cf_test_phone_required")

    # Ensure demo Store exists for isolation checks — never delete it.
    st = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    if st is None:
        # Soft provision empty demo store row (same as sandbox warm path intent).
        try:
            from services.recovery_store_lookup import (  # noqa: PLC0415
                ensure_recovery_store_row_for_zid,
            )

            ensure_recovery_store_row_for_zid(LAB_STORE_SLUG)
            st = (
                db.session.query(Store)
                .filter(Store.zid_store_id == LAB_STORE_SLUG)
                .first()
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("lab_reset_v1 ensure store: %s", exc)

    catalog_before = ""
    if st is not None:
        catalog_before = str(getattr(st, "cf_product_catalog_json", None) or "")

    counts: dict[str, int] = {}
    try:
        # Phone-scoped legacy purge (carts/logs/reasons/…)
        phone_counts = purge_demo_recovery_rows_for_test_phone(LAB_STORE_SLUG, phone_norm)
        for k, v in (phone_counts or {}).items():
            counts[k] = int(v or 0)

        # Lab key + schedule/timeline/purchase extension
        key_counts = _purge_lab_key_scoped(LAB_STORE_SLUG, phone_norm)
        for k, v in key_counts.items():
            counts[k] = counts.get(k, 0) + int(v or 0)

        db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError) as exc:
        db.session.rollback()
        log.warning("lab_reset_v1 purge failed: %s", exc)
        return {
            "ok": False,
            "error": "lab_reset_purge_failed",
            "detail": str(exc)[:240],
        }

    _clear_lab_memory()

    # Preserve check — catalog must be unchanged
    st_after = db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    catalog_after = ""
    if st_after is not None:
        catalog_after = str(getattr(st_after, "cf_product_catalog_json", None) or "")
    if catalog_before != catalog_after:
        return {
            "ok": False,
            "error": "lab_reset_catalog_mutated",
        }

    baseline = verify_lab_baseline(store_slug=LAB_STORE_SLUG, cf_test_phone=phone_norm)
    identity = lab_baseline_identity()
    fingerprint = {
        "store_slug": identity["store_slug"],
        "session_id": identity["session_id"],
        "cart_id": identity["cart_id"],
        "recovery_key": identity["recovery_key"],
        "lab_phone": phone_norm,
        "clean": bool(baseline.get("clean")),
        "baseline_counts": dict(baseline.get("counts") or {}),
    }

    return {
        "ok": True,
        "error": None,
        "store_slug": LAB_STORE_SLUG,
        "lab_phone": phone_norm,
        "identity": identity,
        "purge_counts": counts,
        "baseline": baseline,
        "fingerprint": fingerprint,
        "client_storage_clear": list(LAB_CLIENT_STORAGE_CLEAR),
        "preserved": {
            "store_row": st_after is not None,
            "catalog_unchanged": catalog_before == catalog_after,
        },
        "reset_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


__all__ = [
    "LAB_CART_ID",
    "LAB_CLIENT_STORAGE_CLEAR",
    "LAB_CUSTOMER_PHONE",
    "LAB_RECOVERY_KEY",
    "LAB_SESSION_ID",
    "LAB_STORE_SLUG",
    "lab_baseline_identity",
    "lab_reset_v1",
    "validate_lab_reset_scope",
    "verify_lab_baseline",
]
