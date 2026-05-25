# -*- coding: utf-8 -*-
"""
Read-only diagnostics: widget cart-event → AbandonedCart → merchant dashboard list.

Does not change recovery, widget, or dashboard query behavior.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional

log = logging.getLogger("cartflow")


def _reason_tag_from_row(ac: Any) -> Optional[str]:
    raw = getattr(ac, "raw_payload", None)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            rt = parsed.get("reason_tag")
            return str(rt).strip()[:64] if rt else None
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def log_cf_abandoned_cart_persist(
    row: Any,
    *,
    store_slug: str,
    created: bool,
    event_path: str = "cart_state_sync",
) -> None:
    """Structured persist log for production verification (no PII beyond ids)."""
    if row is None:
        return
    cart_id = (getattr(row, "zid_cart_id", None) or "").strip() or "-"
    session_id = (getattr(row, "recovery_session_id", None) or "").strip() or "-"
    status = (getattr(row, "status", None) or "").strip() or "-"
    reason_tag = _reason_tag_from_row(row) or "-"
    slug = (store_slug or "").strip() or "-"
    mode = "created" if created else "updated"
    line = (
        f"[CF ABANDONED CART PERSIST] path={event_path} mode={mode} "
        f"cart_id={cart_id} session_id={session_id} store_slug={slug} "
        f"status={status} reason_tag={reason_tag}"
    )
    log.info(line)
    try:
        print(line, flush=True)
    except OSError:
        pass


def _iso_dt(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, AttributeError):
        return str(dt)


def _store_slug_for_cart(ac: Any, store_by_id: dict[int, str]) -> Optional[str]:
    sid = getattr(ac, "store_id", None)
    if sid is not None:
        try:
            slug = store_by_id.get(int(sid))
            if slug:
                return slug
        except (TypeError, ValueError):
            pass
    return None


def _cart_row_snapshot(
    ac: Any,
    *,
    dash_store: Optional[Any] = None,
    scope_filter: Any = None,
    store_by_id: Optional[dict[int, str]] = None,
) -> dict[str, Any]:
    from extensions import db
    from models import AbandonedCart

    store_by_id = store_by_id or {}
    store_id = getattr(ac, "store_id", None)
    store_slug = _store_slug_for_cart(ac, store_by_id)
    reason_tag = _reason_tag_from_row(ac)
    excluded: list[str] = []
    status = (getattr(ac, "status", None) or "").strip()
    if status != "abandoned":
        excluded.append(f"status_not_abandoned:{status or 'empty'}")
    if bool(getattr(ac, "vip_mode", False)):
        excluded.append("vip_mode")
    passes_scope = True
    if scope_filter is not None:
        try:
            q = (
                db.session.query(AbandonedCart.id)
                .filter(AbandonedCart.id == int(ac.id))
                .filter(scope_filter)
            )
            passes_scope = q.first() is not None
            if not passes_scope:
                excluded.append("dashboard_store_scope")
        except Exception:  # noqa: BLE001
            passes_scope = False
            excluded.append("scope_check_error")
    dash_slug = (
        (getattr(dash_store, "zid_store_id", None) or "").strip()
        if dash_store is not None
        else None
    )
    return {
        "cart_id": (getattr(ac, "zid_cart_id", None) or "").strip() or None,
        "session_id": (getattr(ac, "recovery_session_id", None) or "").strip() or None,
        "store_id": store_id,
        "store_slug": store_slug,
        "status": status or None,
        "reason_tag": reason_tag,
        "vip_mode": bool(getattr(ac, "vip_mode", False)),
        "cart_value": getattr(ac, "cart_value", None),
        "created_at": _iso_dt(getattr(ac, "first_seen_at", None)),
        "last_seen_at": _iso_dt(getattr(ac, "last_seen_at", None)),
        "passes_dashboard_scope": passes_scope,
        "dashboard_store_slug": dash_slug,
        "excluded_from_normal_carts_reasons": excluded,
    }


def build_merchant_cart_visibility_debug_payload(
    *,
    dash_store: Optional[Any] = None,
    auth_store_slug: Optional[str] = None,
    scope_filter: Any = None,
    normal_carts_row_count: Optional[int] = None,
    normal_carts_error: Optional[str] = None,
) -> dict[str, Any]:
    from extensions import db
    from models import AbandonedCart, Store

    latest_global: list[dict[str, Any]] = []
    try:
        rows = (
            db.session.query(AbandonedCart)
            .order_by(AbandonedCart.last_seen_at.desc())
            .limit(10)
            .all()
        )
        store_ids = {
            int(getattr(r, "store_id"))
            for r in rows
            if getattr(r, "store_id", None) is not None
        }
        store_by_id: dict[int, str] = {}
        if store_ids:
            for st in db.session.query(Store).filter(Store.id.in_(store_ids)).all():
                store_by_id[int(st.id)] = (getattr(st, "zid_store_id", None) or "").strip()
        latest_global = [
            _cart_row_snapshot(
                ac,
                dash_store=dash_store,
                scope_filter=scope_filter,
                store_by_id=store_by_id,
            )
            for ac in rows
        ]
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        latest_global = [{"error": str(exc)[:200]}]

    return {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "dashboard_store": {
            "auth_store_slug": auth_store_slug,
            "resolved_store_id": getattr(dash_store, "id", None) if dash_store else None,
            "resolved_store_slug": (
                (getattr(dash_store, "zid_store_id", None) or "").strip()
                if dash_store
                else None
            ),
            "vip_cart_threshold": getattr(dash_store, "vip_cart_threshold", None)
            if dash_store
            else None,
        },
        "normal_carts_query": {
            "status_filter": "abandoned",
            "lifecycle_default": "active",
            "vip_rows_excluded": True,
            "api_rows_returned": normal_carts_row_count,
            "api_error": normal_carts_error,
        },
        "widget_path_note": (
            "AbandonedCart is upserted on POST /api/cart-event with event=cart_state_sync. "
            "cart_abandoned schedules recovery but does not create the row alone. "
            "normal-carts lists status=abandoned rows matching dashboard store scope."
        ),
        "latest_carts": latest_global,
    }


__all__ = [
    "build_merchant_cart_visibility_debug_payload",
    "log_cf_abandoned_cart_persist",
]
