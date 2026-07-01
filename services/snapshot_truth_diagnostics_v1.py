# -*- coding: utf-8 -*-
"""Read-only snapshot vs live-builder vs merchant dashboard truth diagnostics."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from extensions import db
from models import AbandonedCart
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


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _iso(dt: Any) -> Optional[str]:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None


def _recovery_keys_from_inputs(
    *,
    store_slug: str,
    cart_id: str,
    recovery_key: str,
) -> tuple[str, list[str], Optional[AbandonedCart], str]:
    slug = canonical_snapshot_store_slug(store_slug=store_slug)
    cid = _norm(cart_id)[:255]
    rk_in = _norm(recovery_key)[:512]
    keys: list[str] = []
    ac_row: Optional[AbandonedCart] = None

    if rk_in:
        keys.append(rk_in)
        rk_slug, rk_part = parse_recovery_key(rk_in)
        if not slug and rk_slug:
            slug = canonical_snapshot_store_slug(store_slug=rk_slug)
        if not cid and rk_part:
            cid = rk_part[:255]

    if slug and cid:
        rk_cart = f"{slug}:{cid}"[:512]
        if rk_cart not in keys:
            keys.append(rk_cart)
        ac_row = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.id.desc())
            .first()
        )
        sid = _norm(getattr(ac_row, "recovery_session_id", None))[:512] if ac_row else ""
        if sid:
            rk_sess = f"{slug}:{sid}"[:512]
            if rk_sess not in keys:
                keys.append(rk_sess)

    primary = ""
    if cid and slug:
        primary = f"{slug}:{cid}"[:512]
    elif keys:
        primary = keys[0]
    return slug, keys, ac_row, cid


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
    for one cart identity.
    """
    import main as _main  # noqa: PLC0415

    from services.recovery_dashboard_inclusion_truth import (  # noqa: PLC0415
        build_recovery_dashboard_inclusion_truth,
    )

    slug, recovery_keys_list, ac_row, cid = _recovery_keys_from_inputs(
        store_slug=store_slug,
        cart_id=cart_id,
        recovery_key=recovery_key,
    )
    recovery_keys = {k for k in recovery_keys_list if k}
    primary_rk = recovery_keys_list[0] if recovery_keys_list else ""
    cid = _norm(cid)[:255]

    db_ok = ac_row is not None
    if ac_row is None and primary_rk:
        _slug, part = parse_recovery_key(primary_rk)
        if part and not part.startswith("cf_cart_"):
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
    inclusion_by_key: dict[str, dict[str, Any]] = {}
    live_builder_visible = False
    live_exclusion_reason: Optional[str] = None
    for rk in recovery_keys_list:
        inc = build_recovery_dashboard_inclusion_truth(
            recovery_key=rk,
            dash_store=dash_store,
            lifecycle=lifecycle,
        )
        inclusion_by_key[rk] = inc
        if inc.get("dashboard_visible"):
            live_builder_visible = True
            primary_rk = rk
            live_exclusion_reason = None
            break
        live_exclusion_reason = _norm(inc.get("dashboard_exclusion_reason")) or live_exclusion_reason

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
        "dashboard_visible": dashboard_visible,
        "checks": checks,
        "reason": reason,
        "live_builder_by_key": inclusion_by_key,
    }


__all__ = ["build_snapshot_truth_diagnostics"]
