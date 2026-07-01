# -*- coding: utf-8 -*-
"""Read-only snapshot vs live-builder vs merchant dashboard truth diagnostics."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import or_

from extensions import db
from models import AbandonedCart, CartRecoveryLog
from services.cartflow_session_truth import parse_recovery_key
from services.dashboard_snapshot_v1 import (
    SNAPSHOT_TYPE_NORMAL_CARTS,
    canonical_snapshot_store_slug,
    dashboard_snapshot_mode_enabled,
    decode_snapshot_payload,
    fetch_latest_snapshot_row,
    snapshot_row_is_stale,
)
from services.merchant_cart_row_classifier import UI_FILTER_ALL
from services.merchant_dashboard_recovery_resolve_v1 import SENT_LOG_STATUSES


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None


def _is_cart_scoped_part(part: str) -> bool:
    from services.journey_identity_resolver_v1 import has_stable_cart_id  # noqa: PLC0415

    return has_stable_cart_id(part)


@dataclass(frozen=True)
class _AliasKey:
    recovery_key: str
    key_type: str  # cart | session


def _resolve_key_identity(
    recovery_key: str,
    *,
    store_slug: str,
    ac_row: Optional[AbandonedCart],
) -> tuple[str, str, str, Optional[AbandonedCart]]:
    """Return key_type, cart_id, session_id, abandoned_cart row (alias-aware)."""
    rk_slug, rk_part = parse_recovery_key(recovery_key)
    _ = _norm(rk_slug)
    part = _norm(rk_part)

    if _is_cart_scoped_part(part):
        cart_id = part[:255]
        row = ac_row
        if row is None or _norm(getattr(row, "zid_cart_id", None)) != cart_id:
            row = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id == cart_id)
                .order_by(AbandonedCart.id.desc())
                .first()
            )
        session_id = _norm(getattr(row, "recovery_session_id", None))[:512] if row else ""
        return "cart", cart_id, session_id, row

    session_id = part[:512]
    row = ac_row
    if row is None or _norm(getattr(row, "recovery_session_id", None)) != session_id:
        row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == session_id)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
    cart_id = _norm(getattr(row, "zid_cart_id", None))[:255] if row else ""
    return "session", cart_id, session_id, row


def _diagnostic_dash_store(store_slug: str, dash_store: Any) -> Any:
    """Prefer authenticated dash store; fall back to query store_slug for dev diagnostics."""
    from services.merchant_dashboard_recovery_resolve_v1 import store_slug_from_dash  # noqa: PLC0415

    if store_slug_from_dash(dash_store):
        return dash_store
    slug = _norm(store_slug)[:255]
    if not slug:
        return dash_store
    try:
        from models import Store  # noqa: PLC0415

        row = (
            db.session.query(Store)
            .filter(Store.zid_store_id == slug)
            .order_by(Store.id.desc())
            .first()
        )
        if row is not None:
            return row
    except Exception:  # noqa: BLE001
        db.session.rollback()

    class _StoreSlugProxy:
        zid_store_id = slug

    return _StoreSlugProxy()


def _find_sent_log_diagnostic(
    *,
    store_slug: str,
    recovery_key: str,
    cart_id: str = "",
    session_id: str = "",
    abandoned_cart_id: Optional[int] = None,
) -> Optional[CartRecoveryLog]:
    """Diagnostics-only sent log lookup; does not depend on authenticated dash_store."""
    from services.merchant_dashboard_recovery_resolve_v1 import (  # noqa: PLC0415
        find_sent_log_by_recovery_identity,
    )

    slug = _norm(store_slug)[:255]
    rk = _norm(recovery_key)[:512]
    cid = _norm(cart_id)[:255]
    sid = _norm(session_id)[:512]

    if abandoned_cart_id and (not cid or not sid):
        try:
            ac = db.session.get(AbandonedCart, int(abandoned_cart_id))
            if ac is not None:
                if not cid:
                    cid = _norm(getattr(ac, "zid_cart_id", None))[:255]
                if not sid:
                    sid = _norm(getattr(ac, "recovery_session_id", None))[:512]
        except Exception:  # noqa: BLE001
            db.session.rollback()

    if slug:
        try:
            lg = find_sent_log_by_recovery_identity(
                store_slug=slug,
                recovery_key=rk,
                cart_id=cid,
                session_id=sid,
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    if rk:
        try:
            lg = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.recovery_key == rk,
                    CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
                )
                .order_by(CartRecoveryLog.id.desc())
                .first()
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    if slug and (sid or cid):
        try:
            parts: list[Any] = []
            if sid:
                parts.append(CartRecoveryLog.session_id == sid)
            if cid:
                parts.append(CartRecoveryLog.cart_id == cid)
            lg = (
                db.session.query(CartRecoveryLog)
                .filter(
                    CartRecoveryLog.store_slug == slug,
                    or_(*parts),
                    CartRecoveryLog.status.in_(tuple(SENT_LOG_STATUSES)),
                )
                .order_by(CartRecoveryLog.id.desc())
                .first()
            )
            if lg is not None:
                return lg
        except Exception:  # noqa: BLE001
            db.session.rollback()

    return None


def _recovery_keys_from_inputs(
    *,
    store_slug: str,
    cart_id: str,
    recovery_key: str,
) -> tuple[str, list[_AliasKey], Optional[AbandonedCart], str]:
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    cid = _norm(cart_id)[:255]
    rk_in = _norm(recovery_key)[:512]
    alias_keys: list[_AliasKey] = []
    seen: set[str] = set()
    ac_row: Optional[AbandonedCart] = None

    def _add(rk: str, key_type: str) -> None:
        k = _norm(rk)[:512]
        if not k or k in seen:
            return
        seen.add(k)
        alias_keys.append(_AliasKey(recovery_key=k, key_type=key_type))

    if rk_in:
        _rk_slug, rk_part = parse_recovery_key(rk_in)
        if not slug and _rk_slug:
            slug = canonical_snapshot_store_slug(store_slug=_rk_slug)
        if not cid and rk_part and _is_cart_scoped_part(rk_part):
            cid = rk_part[:255]

    if slug and cid:
        _add(f"{slug}:{cid}", "cart")
        ac_row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        sid = _norm(getattr(ac_row, "recovery_session_id", None))[:512] if ac_row else ""
        if sid:
            _add(f"{slug}:{sid}", "session")

    if rk_in:
        _rk_slug, rk_part = parse_recovery_key(rk_in)
        kt = "cart" if _is_cart_scoped_part(rk_part) else "session"
        _add(rk_in, kt)

    primary = f"{slug}:{cid}"[:512] if slug and cid else (alias_keys[0].recovery_key if alias_keys else "")
    return slug, alias_keys, ac_row, cid


def _snapshot_row_collections(payload: dict[str, Any]) -> list[tuple[str, list[dict[str, Any]]]]:
    return [
        ("active", list(payload.get("merchant_carts_page_rows") or [])),
        ("archived", list(payload.get("merchant_archived_carts_page_rows") or [])),
        ("table", list(payload.get("merchant_table_rows") or [])),
    ]


def _row_matches_target(
    row: dict[str, Any],
    *,
    recovery_keys: set[str],
    cart_id: str,
) -> bool:
    rk = _norm(row.get("recovery_key"))
    if rk and rk in recovery_keys:
        return True
    if not cart_id:
        return False
    for field in ("zid_cart_id", "cart_id", "merchant_cart_id"):
        if _norm(row.get(field)) == cart_id:
            return True
    return False


def _find_snapshot_row(
    payload: dict[str, Any],
    *,
    recovery_keys: set[str],
    cart_id: str,
) -> tuple[Optional[dict[str, Any]], str]:
    for collection, rows in _snapshot_row_collections(payload):
        for row in rows:
            if isinstance(row, dict) and _row_matches_target(
                row, recovery_keys=recovery_keys, cart_id=cart_id
            ):
                return row, collection
    return None, ""


def _filter_tabs_for_row(row: dict[str, Any]) -> list[str]:
    tabs = row.get("merchant_cart_visible_tabs") or []
    out: list[str] = []
    if isinstance(tabs, (list, tuple)):
        for tab in tabs:
            t = _norm(tab).lower()
            if t and t not in out:
                out.append(t)
    bucket = _norm(row.get("merchant_cart_bucket") or row.get("merchant_cart_primary_bucket")).lower()
    if bucket and bucket not in out:
        out.append(bucket)
    if UI_FILTER_ALL not in out:
        out.insert(0, UI_FILTER_ALL)
    return out


def _key_result_included(kr: dict[str, Any]) -> bool:
    if kr.get("dashboard_visible"):
        return True
    if not kr.get("sent_log_found"):
        return False
    returned = bool(kr.get("returned_in_api"))
    stage = _norm(kr.get("exclusion_stage"))
    reason = _norm(kr.get("exclusion_reason"))
    return returned and (stage == "included" or reason == "included")


def _aggregate_alias_results(
    key_results: list[dict[str, Any]],
) -> tuple[bool, str, str, Optional[str]]:
    """Prefer first successful alias (cart before session); never let no_sent_log override included."""
    for kr in key_results:
        if not _key_result_included(kr):
            continue
        matched_key = _norm(kr.get("recovery_key"))
        key_type = _norm(kr.get("key_type")) or "cart"
        if _norm(kr.get("exclusion_stage")) == "included":
            matched_by = f"{key_type}_presence_trace"
        elif kr.get("dashboard_visible"):
            matched_by = f"{key_type}_dashboard_row"
        else:
            matched_by = key_type
        return True, matched_key, matched_by, "included"

    live_exclusion_reason: Optional[str] = None
    for kr in key_results:
        reason = _norm(kr.get("exclusion_reason"))
        if reason and reason != "no_sent_log":
            live_exclusion_reason = reason
            break
    if not live_exclusion_reason:
        for kr in key_results:
            reason = _norm(kr.get("exclusion_reason"))
            if reason:
                live_exclusion_reason = reason
                break
    return False, "", "", live_exclusion_reason


def _build_alias_key_diagnostic(
    alias: _AliasKey,
    *,
    store_slug: str,
    ac_row: Optional[AbandonedCart],
    dash_store: Any,
    lifecycle: str,
) -> dict[str, Any]:
    from services.merchant_cart_presence_trace_v1 import trace_merchant_cart_presence  # noqa: PLC0415
    from services.recovery_dashboard_inclusion_truth import (  # noqa: PLC0415
        build_recovery_dashboard_inclusion_truth,
    )

    key_type, cart_id, session_id, ac_resolved = _resolve_key_identity(
        alias.recovery_key,
        store_slug=store_slug,
        ac_row=ac_row,
    )
    diag_store = _diagnostic_dash_store(store_slug, dash_store)
    ac_id = int(getattr(ac_resolved, "id", 0) or 0) or None

    sent_log = _find_sent_log_diagnostic(
        store_slug=store_slug,
        recovery_key=alias.recovery_key,
        cart_id=cart_id,
        session_id=session_id,
        abandoned_cart_id=ac_id,
    )

    trace = trace_merchant_cart_presence(
        alias.recovery_key,
        dash_store=diag_store,
        lifecycle=lifecycle,
    )
    inclusion = build_recovery_dashboard_inclusion_truth(
        recovery_key=alias.recovery_key,
        dash_store=diag_store,
        lifecycle=lifecycle,
    )

    sent_log_found = sent_log is not None or bool(trace.get("log_id"))
    sent_log_id = (
        int(getattr(sent_log, "id", 0) or 0)
        or int(trace.get("log_id") or 0)
        or None
    )
    returned_in_api = bool(trace.get("returned_in_api"))
    exclusion_stage = _norm(trace.get("exclusion_stage")) or None
    dashboard_visible = bool(inclusion.get("dashboard_visible"))
    exclusion_reason = _norm(inclusion.get("dashboard_exclusion_reason")) or None

    trace_included = exclusion_stage == "included" and returned_in_api
    if trace_included or (exclusion_reason == "included" and returned_in_api):
        dashboard_visible = True
        exclusion_reason = "included"
    elif dashboard_visible:
        exclusion_reason = None

    return {
        "recovery_key": alias.recovery_key,
        "key_type": alias.key_type or key_type,
        "sent_log_found": bool(sent_log_found),
        "sent_log_id": sent_log_id,
        "returned_in_api": returned_in_api,
        "dashboard_visible": dashboard_visible,
        "exclusion_reason": exclusion_reason,
        "exclusion_stage": exclusion_stage,
        "resolved_cart_id": cart_id or None,
        "resolved_session_id": session_id or None,
        "abandoned_cart_id": ac_id,
        "presence_trace": trace,
        "inclusion": inclusion,
    }


def _derive_reason(
    *,
    db_ok: bool,
    live_builder_visible: bool,
    snapshot_exists: bool,
    snapshot_row_present: bool,
    snapshot_stale: bool,
    dashboard_visible: bool,
    live_exclusion_reason: Optional[str],
) -> str:
    if not db_ok:
        return "no_abandoned_cart"
    if live_builder_visible and not snapshot_row_present:
        if not snapshot_exists:
            return "snapshot_missing"
        if snapshot_stale:
            return "snapshot_stale"
        return "row_missing"
    if snapshot_row_present and not dashboard_visible:
        return "frontend_filter_render"
    if not live_builder_visible:
        return _norm(live_exclusion_reason) or "live_builder_excluded"
    if live_builder_visible and snapshot_row_present and dashboard_visible:
        return "ok"
    if snapshot_exists and not snapshot_row_present:
        return "row_missing"
    return "unknown"


def build_snapshot_truth_diagnostics(
    *,
    store_slug: str = "",
    cart_id: str = "",
    recovery_key: str = "",
    lifecycle: str = "active",
) -> dict[str, Any]:
    """
    Compare DB, live builder, snapshot payload, and merchant-visible dashboard rows
    for one cart identity (alias-aware).
    """
    import main as _main  # noqa: PLC0415

    slug, alias_keys, ac_row, cid = _recovery_keys_from_inputs(
        store_slug=store_slug,
        cart_id=cart_id,
        recovery_key=recovery_key,
    )
    recovery_keys_list = [a.recovery_key for a in alias_keys]
    recovery_keys = {k for k in recovery_keys_list if k}
    primary_rk = f"{slug}:{cid}"[:512] if slug and cid else (recovery_keys_list[0] if recovery_keys_list else "")
    cid = _norm(cid)[:255]

    db_ok = ac_row is not None
    if ac_row is None and primary_rk:
        _slug, part = parse_recovery_key(primary_rk)
        if part and not _is_cart_scoped_part(part):
            ac_row = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.recovery_session_id == part)
                .order_by(AbandonedCart.id.desc())
                .first()
            )
            db_ok = ac_row is not None
            if ac_row and not cid:
                cid = _norm(getattr(ac_row, "zid_cart_id", None))[:255]

    dash_store = _main._dashboard_recovery_store_row()
    alias_key_results: list[dict[str, Any]] = []
    inclusion_by_key: dict[str, dict[str, Any]] = {}
    for alias in alias_keys:
        key_diag = _build_alias_key_diagnostic(
            alias,
            store_slug=slug,
            ac_row=ac_row,
            dash_store=dash_store,
            lifecycle=lifecycle,
        )
        alias_key_results.append(key_diag)
        inclusion_by_key[alias.recovery_key] = key_diag.get("inclusion") or {}

    live_builder_visible, matched_key, matched_by, live_exclusion_reason = _aggregate_alias_results(
        alias_key_results
    )
    if matched_key:
        primary_rk = matched_key
    live_builder_status = "included" if live_builder_visible else (_norm(live_exclusion_reason) or "excluded")

    snapshot_row = fetch_latest_snapshot_row(
        store_slug=slug,
        snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
    )
    snapshot_exists = snapshot_row is not None
    snapshot_stale = snapshot_row_is_stale(snapshot_row) if snapshot_row is not None else False
    snapshot_generated_at = _iso(getattr(snapshot_row, "generated_at", None)) if snapshot_row else None
    snapshot_payload: dict[str, Any] = (
        decode_snapshot_payload(snapshot_row) if snapshot_row is not None else {}
    )

    matched_row, matched_collection = _find_snapshot_row(
        snapshot_payload,
        recovery_keys=recovery_keys,
        cart_id=cid,
    )
    snapshot_row_present = matched_row is not None
    snapshot_row_recovery_key = _norm(matched_row.get("recovery_key")) if matched_row else ""
    snapshot_bucket = (
        _norm(
            matched_row.get("merchant_cart_bucket")
            or matched_row.get("merchant_cart_primary_bucket")
            or matched_row.get("merchant_coarse_status")
        )
        if matched_row
        else ""
    )
    snapshot_filter_tabs = _filter_tabs_for_row(matched_row) if matched_row else []
    snapshot_filter_counts = dict(snapshot_payload.get("merchant_cart_filter_counts") or {})

    active_rows = list(snapshot_payload.get("merchant_carts_page_rows") or [])
    archived_rows = list(snapshot_payload.get("merchant_archived_carts_page_rows") or [])
    snapshot_rows_count = len(active_rows) + len(archived_rows)

    snapshot_mode = dashboard_snapshot_mode_enabled()
    if snapshot_mode:
        dashboard_visible = any(
            isinstance(row, dict)
            and _row_matches_target(row, recovery_keys=recovery_keys, cart_id=cid)
            for row in active_rows
        )
    else:
        dashboard_visible = live_builder_visible

    reason = _derive_reason(
        db_ok=db_ok,
        live_builder_visible=live_builder_visible,
        snapshot_exists=snapshot_exists,
        snapshot_row_present=snapshot_row_present,
        snapshot_stale=snapshot_stale,
        dashboard_visible=dashboard_visible,
        live_exclusion_reason=live_exclusion_reason,
    )

    checks = {
        "db": bool(db_ok),
        "live_builder": bool(live_builder_visible),
        "snapshot": bool(snapshot_exists and snapshot_row_present),
        "dashboard": bool(dashboard_visible),
    }

    return {
        "ok": True,
        "store_slug": slug or None,
        "cart_id": cid or None,
        "recovery_key": primary_rk or None,
        "recovery_keys_checked": recovery_keys_list,
        "alias_key_results": [
            {
                "recovery_key": kr.get("recovery_key"),
                "key_type": kr.get("key_type"),
                "sent_log_found": kr.get("sent_log_found"),
                "sent_log_id": kr.get("sent_log_id"),
                "returned_in_api": kr.get("returned_in_api"),
                "dashboard_visible": kr.get("dashboard_visible"),
                "exclusion_reason": kr.get("exclusion_reason"),
                "exclusion_stage": kr.get("exclusion_stage"),
            }
            for kr in alias_key_results
        ],
        "matched_key": matched_key or None,
        "matched_by": matched_by or None,
        "snapshot_mode_enabled": snapshot_mode,
        "snapshot_exists": snapshot_exists,
        "snapshot_generated_at": snapshot_generated_at,
        "snapshot_stale": snapshot_stale,
        "snapshot_row_present": snapshot_row_present,
        "snapshot_row_recovery_key": snapshot_row_recovery_key or None,
        "snapshot_row_collection": matched_collection or None,
        "snapshot_bucket": snapshot_bucket or None,
        "snapshot_filter_tabs": snapshot_filter_tabs,
        "snapshot_filter_counts": snapshot_filter_counts,
        "snapshot_rows_count": snapshot_rows_count,
        "live_builder_visible": live_builder_visible,
        "live_builder_status": live_builder_status,
        "dashboard_visible": dashboard_visible,
        "checks": checks,
        "reason": reason,
        "live_builder_by_key": inclusion_by_key,
    }


__all__ = [
    "build_snapshot_truth_diagnostics",
    "_find_sent_log_diagnostic",
    "_resolve_key_identity",
    "_aggregate_alias_results",
    "_diagnostic_dash_store",
]
