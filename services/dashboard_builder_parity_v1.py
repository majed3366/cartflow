# -*- coding: utf-8 -*-
"""
Dashboard builder parity diagnostics — live vs snapshot builder vs persisted payload.

Governance: no dashboard visibility fix without identifying drop_stage via this contract.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from extensions import db
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, RecoverySchedule
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    canonical_snapshot_store_slug,
    dashboard_snapshot_mode_enabled,
    decode_snapshot_payload,
    fetch_latest_snapshot_row,
    snapshot_row_is_stale,
)
from services.merchant_dashboard_recovery_resolve_v1 import SENT_LOG_STATUSES
from services.snapshot_truth_diagnostics_v1 import (
    _aggregate_alias_results,
    _build_alias_key_diagnostic,
    _diagnostic_dash_store,
    _filter_tabs_for_row,
    _find_sent_log_diagnostic,
    _find_snapshot_row,
    _recovery_keys_from_inputs,
    _resolve_key_identity,
)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None


def _row_bucket(row: dict[str, Any]) -> str:
    return _norm(
        row.get("merchant_cart_bucket")
        or row.get("merchant_cart_primary_bucket")
        or row.get("merchant_coarse_status")
    )


def _payload_row_stats(payload: dict[str, Any]) -> dict[str, Any]:
    active = list(payload.get("merchant_carts_page_rows") or [])
    archived = list(payload.get("merchant_archived_carts_page_rows") or [])
    return {
        "merchant_carts_page_rows": len(active),
        "merchant_archived_carts_page_rows": len(archived),
        "merchant_cart_filter_counts": dict(payload.get("merchant_cart_filter_counts") or {}),
        "candidate_rows": int(payload.get("candidate_rows") or 0),
        "visible_rows": int(payload.get("visible_rows") or 0),
    }


def _payload_truncation_drops_row(
    payload: dict[str, Any],
    *,
    recovery_keys: set[str],
    cart_id: str,
) -> bool:
    if not _find_snapshot_row(payload, recovery_keys=recovery_keys, cart_id=cart_id)[0]:
        return False
    serialized = json.dumps(payload, ensure_ascii=False, default=str)[:65000]
    try:
        decoded = json.loads(serialized)
    except (TypeError, ValueError, json.JSONDecodeError):
        return True
    if not isinstance(decoded, dict):
        return True
    return _find_snapshot_row(decoded, recovery_keys=recovery_keys, cart_id=cart_id)[0] is None


def _resolve_store_row_for_slug(store_slug: str) -> tuple[Optional[Any], Optional[int], str]:
    from models import Store  # noqa: PLC0415

    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    if not slug:
        return None, None, ""
    row = (
        db.session.query(Store)
        .filter(Store.zid_store_id == slug)
        .order_by(Store.id.desc())
        .first()
    )
    if row is None:
        return None, None, slug
    return row, int(getattr(row, "id", 0) or 0) or None, slug


def _build_fresh_normal_carts_payload(dash_store: Any) -> dict[str, Any]:
    from services.dashboard_snapshot_normal_carts_parity_v1 import (  # noqa: PLC0415
        build_canonical_normal_carts_payload,
    )

    body, _prof, _perf = build_canonical_normal_carts_payload(dash_store)
    return dict(body)


def _db_truth(ac_row: Optional[AbandonedCart], *, slug: str, cid: str) -> dict[str, Any]:
    session_id = _norm(getattr(ac_row, "recovery_session_id", None)) if ac_row else ""
    return {
        "db_cart_exists": ac_row is not None,
        "abandoned_cart_id": int(getattr(ac_row, "id", 0) or 0) or None,
        "store_slug": slug or None,
        "cart_id": cid or None,
        "session_id": session_id or None,
        "store_id": int(getattr(ac_row, "store_id", 0) or 0) or None,
    }


def _recovery_truth(
    *,
    store_slug: str,
    recovery_key: str,
    cart_id: str,
    session_id: str,
    abandoned_cart_id: Optional[int],
) -> dict[str, Any]:
    reason_exists = False
    if store_slug and session_id:
        try:
            reason_exists = (
                db.session.query(CartRecoveryReason.id)
                .filter(
                    CartRecoveryReason.store_slug == store_slug,
                    CartRecoveryReason.session_id == session_id,
                )
                .limit(1)
                .first()
                is not None
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()

    phone_exists = False
    if abandoned_cart_id:
        try:
            ac = db.session.get(AbandonedCart, int(abandoned_cart_id))
            phone_exists = bool(_norm(getattr(ac, "customer_phone", None)) if ac else "")
        except Exception:  # noqa: BLE001
            db.session.rollback()

    schedule_exists = False
    if recovery_key:
        try:
            schedule_exists = (
                db.session.query(RecoverySchedule.id)
                .filter(RecoverySchedule.recovery_key == recovery_key)
                .limit(1)
                .first()
                is not None
            )
        except Exception:  # noqa: BLE001
            db.session.rollback()

    sent_log = _find_sent_log_diagnostic(
        store_slug=store_slug,
        recovery_key=recovery_key,
        cart_id=cart_id,
        session_id=session_id,
        abandoned_cart_id=abandoned_cart_id,
    )
    sent_log_exists = sent_log is not None
    provider_sent_exists = False
    if sent_log is not None:
        provider_sent_exists = _norm(getattr(sent_log, "status", None)) in SENT_LOG_STATUSES

    return {
        "reason_exists": bool(reason_exists),
        "phone_exists": bool(phone_exists),
        "schedule_exists": bool(schedule_exists),
        "sent_log_exists": bool(sent_log_exists),
        "provider_sent_exists": bool(provider_sent_exists),
        "sent_log_id": int(getattr(sent_log, "id", 0) or 0) or None,
    }


def _builder_row_truth(
    payload: dict[str, Any],
    *,
    recovery_keys: set[str],
    cart_id: str,
    label: str,
) -> dict[str, Any]:
    row, collection = _find_snapshot_row(
        payload,
        recovery_keys=recovery_keys,
        cart_id=cart_id,
    )
    present = row is not None
    return {
        "label": label,
        "row_present": present,
        "collection": collection or None,
        "bucket": _row_bucket(row) if row else None,
        "tabs": _filter_tabs_for_row(row) if row else [],
        "recovery_key": _norm(row.get("recovery_key")) if row else None,
        "row_stats": _payload_row_stats(payload),
        "payload_truncated_would_drop_row": _payload_truncation_drops_row(
            payload,
            recovery_keys=recovery_keys,
            cart_id=cart_id,
        ),
    }


def _derive_drop_stage(
    *,
    db_ok: bool,
    live_row_present: bool,
    snapshot_builder_row_present: bool,
    snapshot_row_present: bool,
    snapshot_exists: bool,
    snapshot_stale: bool,
    pipeline_stage: str,
    payload_truncated: bool,
    alias_live_included: bool,
) -> tuple[str, str]:
    if not db_ok:
        return "candidate_query", "no_abandoned_cart"
    if not alias_live_included and pipeline_stage == "no_sent_log":
        return "candidate_query", "no_sent_log_alias_mismatch"
    if not alias_live_included and pipeline_stage:
        return pipeline_stage, _norm(pipeline_stage) or "live_builder_excluded"
    if not live_row_present and not snapshot_builder_row_present:
        stage = pipeline_stage or "row_build"
        return stage, stage
    if live_row_present and not snapshot_builder_row_present:
        return "row_build", "live_snapshot_builder_mismatch"
    if live_row_present and not snapshot_row_present:
        if payload_truncated:
            return "snapshot_write", "payload_truncated"
        if not snapshot_exists:
            return "snapshot_read", "snapshot_missing"
        if snapshot_stale:
            return "snapshot_read", "snapshot_stale"
        return "snapshot_read", "row_missing"
    if snapshot_row_present and not alias_live_included:
        return "snapshot_read", "snapshot_has_row_live_excluded"
    if live_row_present and snapshot_row_present:
        return "included", "ok"
    return "unknown", "unknown"


def build_dashboard_builder_parity(
    *,
    store_slug: str = "",
    cart_id: str = "",
    recovery_key: str = "",
    abandoned_cart_id: Optional[int] = None,
    lifecycle: str = "active",
    repair: bool = False,
) -> dict[str, Any]:
    """
    Run live and snapshot builders for the same store; compare persisted snapshot payload.
    Optional ``repair=True`` rebuilds store snapshots when drop_stage is snapshot_read.
    """
    slug, alias_keys, ac_row, cid = _recovery_keys_from_inputs(
        store_slug=store_slug,
        cart_id=cart_id,
        recovery_key=recovery_key,
    )
    if abandoned_cart_id and ac_row is None:
        try:
            ac_row = db.session.get(AbandonedCart, int(abandoned_cart_id))
        except Exception:  # noqa: BLE001
            db.session.rollback()
    if ac_row is not None and not cid:
        cid = _norm(getattr(ac_row, "zid_cart_id", None))[:255]

    recovery_keys = {a.recovery_key for a in alias_keys if a.recovery_key}
    primary_rk = f"{slug}:{cid}"[:512] if slug and cid else (alias_keys[0].recovery_key if alias_keys else "")

    store_row, store_id, canonical_slug = _resolve_store_row_for_slug(slug)
    dash_store = _diagnostic_dash_store(slug, store_row or type("P", (), {"zid_store_id": slug})())

    alias_key_results: list[dict[str, Any]] = []
    for alias in alias_keys:
        alias_key_results.append(
            _build_alias_key_diagnostic(
                alias,
                store_slug=slug,
                ac_row=ac_row,
                dash_store=dash_store,
                lifecycle=lifecycle,
            )
        )
    live_builder_visible, matched_key, matched_by, live_exclusion = _aggregate_alias_results(
        alias_key_results
    )
    if matched_key:
        primary_rk = matched_key

    _kt, resolved_cart_id, resolved_session_id, _ac = _resolve_key_identity(
        primary_rk,
        store_slug=slug,
        ac_row=ac_row,
    )
    cid = resolved_cart_id or cid

    db_block = _db_truth(ac_row, slug=slug, cid=cid)
    recovery_block = _recovery_truth(
        store_slug=slug,
        recovery_key=primary_rk,
        cart_id=cid,
        session_id=resolved_session_id,
        abandoned_cart_id=db_block.get("abandoned_cart_id"),
    )

    live_payload = _build_fresh_normal_carts_payload(dash_store)
    snapshot_builder_payload = _build_fresh_normal_carts_payload(dash_store)

    live_builder = _builder_row_truth(
        live_payload,
        recovery_keys=recovery_keys,
        cart_id=cid,
        label="live_builder",
    )
    snapshot_builder = _builder_row_truth(
        snapshot_builder_payload,
        recovery_keys=recovery_keys,
        cart_id=cid,
        label="snapshot_builder",
    )

    snap_row = fetch_latest_snapshot_row(
        store_slug=slug,
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
    )
    snapshot_exists = snap_row is not None
    snapshot_stale = snapshot_row_is_stale(snap_row) if snap_row is not None else False
    snapshot_generated_at = _iso(getattr(snap_row, "generated_at", None)) if snap_row else None
    persisted_payload = decode_snapshot_payload(snap_row) if snap_row is not None else {}
    persisted = _builder_row_truth(
        persisted_payload,
        recovery_keys=recovery_keys,
        cart_id=cid,
        label="persisted_snapshot",
    )

    pipeline_stage = ""
    for kr in alias_key_results:
        if _norm(kr.get("recovery_key")) == primary_rk:
            pipeline_stage = _norm(kr.get("exclusion_stage"))
            break
    if not pipeline_stage and alias_key_results:
        pipeline_stage = _norm(alias_key_results[0].get("exclusion_stage"))

    drop_stage, reason = _derive_drop_stage(
        db_ok=bool(db_block.get("db_cart_exists")),
        live_row_present=bool(live_builder.get("row_present")),
        snapshot_builder_row_present=bool(snapshot_builder.get("row_present")),
        snapshot_row_present=bool(persisted.get("row_present")),
        snapshot_exists=snapshot_exists,
        snapshot_stale=snapshot_stale,
        pipeline_stage=pipeline_stage,
        payload_truncated=bool(snapshot_builder.get("payload_truncated_would_drop_row")),
        alias_live_included=bool(live_builder_visible),
    )

    repair_out: Optional[dict[str, Any]] = None
    if repair and drop_stage in ("snapshot_read", "snapshot_write", "store_selection") and store_id:
        from services.dashboard_snapshot_builder_v1 import build_store_dashboard_snapshots  # noqa: PLC0415

        repair_out = build_store_dashboard_snapshots(
            store_id=int(store_id),
            store_slug=canonical_slug or slug,
        )
        snap_row = fetch_latest_snapshot_row(
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        )
        snapshot_exists = snap_row is not None
        snapshot_stale = snapshot_row_is_stale(snap_row) if snap_row is not None else False
        snapshot_generated_at = _iso(getattr(snap_row, "generated_at", None)) if snap_row else None
        persisted_payload = decode_snapshot_payload(snap_row) if snap_row is not None else {}
        persisted = _builder_row_truth(
            persisted_payload,
            recovery_keys=recovery_keys,
            cart_id=cid,
            label="persisted_snapshot_after_repair",
        )
        drop_stage, reason = _derive_drop_stage(
            db_ok=bool(db_block.get("db_cart_exists")),
            live_row_present=bool(live_builder.get("row_present")),
            snapshot_builder_row_present=bool(snapshot_builder.get("row_present")),
            snapshot_row_present=bool(persisted.get("row_present")),
            snapshot_exists=snapshot_exists,
            snapshot_stale=snapshot_stale,
            pipeline_stage=pipeline_stage,
            payload_truncated=bool(snapshot_builder.get("payload_truncated_would_drop_row")),
            alias_live_included=bool(live_builder_visible),
        )

    snapshot_mode = dashboard_snapshot_mode_enabled()
    dashboard_row_present = bool(persisted.get("row_present")) if snapshot_mode else bool(
        live_builder.get("row_present")
    )
    dashboard_bucket = persisted.get("bucket") if snapshot_mode else live_builder.get("bucket")
    dashboard_tabs = persisted.get("tabs") if snapshot_mode else live_builder.get("tabs")

    parity_pass = (
        bool(live_builder.get("row_present"))
        and bool(snapshot_builder.get("row_present"))
        and bool(persisted.get("row_present"))
        and bool(dashboard_row_present)
        and not snapshot_stale
    )

    return {
        "ok": True,
        "store_slug": slug or None,
        "cart_id": cid or None,
        "recovery_key": primary_rk or None,
        "store_id": store_id,
        "matched_key": matched_key or None,
        "matched_by": matched_by or None,
        "db_truth": db_block,
        "recovery_truth": recovery_block,
        "live_builder_truth": {
            "candidate_present": bool(live_builder.get("row_stats", {}).get("candidate_rows")),
            "grouped_present": bool(live_builder.get("row_present")),
            "live_builder_row_present": bool(live_builder.get("row_present")),
            "live_builder_bucket": live_builder.get("bucket"),
            "live_builder_tabs": live_builder.get("tabs"),
            "row_stats": live_builder.get("row_stats"),
        },
        "snapshot_builder_truth": {
            "selected_store_present": store_row is not None,
            "snapshot_builder_candidate_present": bool(
                snapshot_builder.get("row_stats", {}).get("candidate_rows")
            ),
            "snapshot_builder_row_present": bool(snapshot_builder.get("row_present")),
            "snapshot_builder_bucket": snapshot_builder.get("bucket"),
            "snapshot_builder_tabs": snapshot_builder.get("tabs"),
            "row_stats": snapshot_builder.get("row_stats"),
            "builders_match": live_builder.get("row_present") == snapshot_builder.get("row_present"),
        },
        "snapshot_payload_truth": {
            "snapshot_exists": snapshot_exists,
            "snapshot_generated_at": snapshot_generated_at,
            "snapshot_stale": snapshot_stale,
            "snapshot_row_present": bool(persisted.get("row_present")),
            "snapshot_rows_count": (
                persisted.get("row_stats", {}).get("merchant_carts_page_rows", 0)
                + persisted.get("row_stats", {}).get("merchant_archived_carts_page_rows", 0)
            ),
            "snapshot_filter_counts": persisted.get("row_stats", {}).get("merchant_cart_filter_counts"),
            "payload_truncated_would_drop_row": bool(
                snapshot_builder.get("payload_truncated_would_drop_row")
            ),
        },
        "dashboard_truth": {
            "dashboard_row_present": dashboard_row_present,
            "dashboard_bucket": dashboard_bucket,
            "dashboard_tabs": dashboard_tabs,
            "snapshot_mode_enabled": snapshot_mode,
        },
        "comparison": {
            "live_builder_row_present": bool(live_builder.get("row_present")),
            "snapshot_builder_row_present": bool(snapshot_builder.get("row_present")),
            "snapshot_row_present": bool(persisted.get("row_present")),
            "dashboard_visible": dashboard_row_present,
        },
        "alias_key_results": [
            {
                "recovery_key": kr.get("recovery_key"),
                "key_type": kr.get("key_type"),
                "sent_log_found": kr.get("sent_log_found"),
                "exclusion_stage": kr.get("exclusion_stage"),
                "exclusion_reason": kr.get("exclusion_reason"),
            }
            for kr in alias_key_results
        ],
        "parity_status": "pass" if parity_pass else "fail",
        "drop_stage": drop_stage,
        "reason": reason,
        "repair": repair_out,
    }


__all__ = ["build_dashboard_builder_parity"]
