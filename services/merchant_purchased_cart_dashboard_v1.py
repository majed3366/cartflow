# -*- coding: utf-8 -*-
"""
Keep purchased / recovered recovery carts visible on the merchant dashboard.

After checkout, AbandonedCart.status becomes ``recovered`` while the default
normal-carts API uses lifecycle=active and only queries ``status=abandoned``.
Purchased carts must still appear in the الكل and مكتملة (recovered) tabs.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, or_

from extensions import db
from models import AbandonedCart, PurchaseTruthRecord

# Augment queries may include recovered rows tied to sent logs / purchase truth.
DASHBOARD_AUGMENT_CART_STATUSES = ("abandoned", "recovered")


def _norm(s: Any) -> str:
    return str(s or "").strip()


def group_is_purchased_terminal(
    *,
    ac: Any,
    log_statuses: Optional[Any] = None,
    purchase_truth: bool = False,
    coarse: str = "",
) -> bool:
    """True when a cart group should stay on the active dashboard for completed tabs."""
    if purchase_truth:
        return True
    if _norm(getattr(ac, "status", None)).lower() == "recovered":
        return True
    log_ss: set[str] = set()
    if log_statuses:
        for raw in log_statuses:
            t = _norm(raw).lower()
            if t:
                log_ss.add(t)
    if "stopped_converted" in log_ss:
        return True
    if _norm(coarse).lower() == "converted":
        return True
    return False


def purchased_terminal_visible_on_active_lifecycle_tab(
    *,
    terminal_archived: bool,
    ac: Any,
    log_statuses: Any = None,
    purchase_truth: bool = False,
    coarse: str = "",
) -> bool:
    """Purchased terminals stay in lifecycle=active API rows (all + completed tabs)."""
    if not terminal_archived:
        return False
    return group_is_purchased_terminal(
        ac=ac,
        log_statuses=log_statuses,
        purchase_truth=purchase_truth,
        coarse=coarse,
    )


def augment_abandoned_candidates_with_purchased_recovery_carts(
    primary_rows: list[AbandonedCart],
    *,
    dash_store: Optional[Any],
    scope_filter: Any,
    augment_limit: int = 60,
    nr_session: Optional[str] = None,
    nr_cart: Optional[str] = None,
) -> list[AbandonedCart]:
    """
    Pull recently recovered carts with durable purchase truth into candidate rows.

    Covers checkout when sent-log augment misses (e.g. log cap) but purchase truth exists.
    """
    slug = (
        _norm(getattr(dash_store, "zid_store_id", None)) if dash_store is not None else ""
    )
    if not slug:
        return list(primary_rows)
    seen: set[int] = set()
    out: list[AbandonedCart] = []
    for row in primary_rows:
        aid = int(getattr(row, "id", 0) or 0)
        if aid and aid not in seen:
            seen.add(aid)
            out.append(row)
    lim = max(1, int(augment_limit))
    session_ids: set[str] = set()
    cart_ids: set[str] = set()
    ns = _norm(nr_session)[:512]
    nc = _norm(nr_cart)[:255]
    scoped = bool(ns or nc)
    if ns:
        session_ids.add(ns)
    if nc:
        cart_ids.add(nc)
    if not scoped:
        for row in primary_rows:
            sid = _norm(getattr(row, "recovery_session_id", None))[:512]
            cid = _norm(getattr(row, "zid_cart_id", None))[:255]
            if sid:
                session_ids.add(sid)
            if cid:
                cart_ids.add(cid)
    try:
        from schema_purchase_truth import ensure_purchase_truth_schema  # noqa: PLC0415

        ensure_purchase_truth_schema(db)
        pt_q = db.session.query(PurchaseTruthRecord).filter(
            PurchaseTruthRecord.store_slug == slug,
            PurchaseTruthRecord.purchase_detected.is_(True),
        )
        if scoped:
            pt_filters: list[Any] = []
            if session_ids:
                pt_filters.append(
                    PurchaseTruthRecord.session_id.in_(list(session_ids))
                )
            if cart_ids:
                pt_filters.append(PurchaseTruthRecord.cart_id.in_(list(cart_ids)))
            if pt_filters:
                pt_q = pt_q.filter(or_(*pt_filters))
            else:
                pt_q = pt_q.filter(PurchaseTruthRecord.id == -1)
        for row in pt_q.order_by(PurchaseTruthRecord.purchase_time.desc()).limit(lim).all():
            sid = _norm(getattr(row, "session_id", None))[:512]
            cid = _norm(getattr(row, "cart_id", None))[:255]
            if sid:
                session_ids.add(sid)
            if cid:
                cart_ids.add(cid)
    except Exception:  # noqa: BLE001
        db.session.rollback()
    or_parts: list[Any] = []
    if session_ids:
        or_parts.append(AbandonedCart.recovery_session_id.in_(list(session_ids)))
    if cart_ids:
        or_parts.append(AbandonedCart.zid_cart_id.in_(list(cart_ids)))
    if not or_parts:
        if scoped:
            return out
        # Unscoped dashboard: bounded recent recovered rows for this store.
        try:
            q_fb = db.session.query(AbandonedCart).filter(
                AbandonedCart.status == "recovered"
            )
            if scope_filter is not None:
                q_fb = q_fb.filter(scope_filter)
            try:
                from services.vip_cart import merchant_vip_threshold_int  # noqa: PLC0415

                vip_th = merchant_vip_threshold_int(dash_store)
                if vip_th is not None:
                    q_fb = q_fb.filter(
                        func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th)
                    )
            except Exception:  # noqa: BLE001
                pass
            q_fb = q_fb.order_by(
                AbandonedCart.recovered_at.desc().nullslast(),
                AbandonedCart.last_seen_at.desc(),
            ).limit(lim)
            for ac in q_fb.all():
                aid = int(getattr(ac, "id", 0) or 0)
                if aid and aid not in seen:
                    seen.add(aid)
                    out.append(ac)
        except Exception:  # noqa: BLE001
            db.session.rollback()
        return out
    try:
        q_extra = db.session.query(AbandonedCart).filter(
            AbandonedCart.status == "recovered",
            or_(*or_parts),
        )
        if scope_filter is not None:
            id_parts: list[Any] = []
            if cart_ids:
                id_parts.append(AbandonedCart.zid_cart_id.in_(list(cart_ids)))
            if session_ids:
                id_parts.append(
                    AbandonedCart.recovery_session_id.in_(list(session_ids))
                )
            if id_parts:
                q_extra = q_extra.filter(or_(scope_filter, or_(*id_parts)))
            else:
                q_extra = q_extra.filter(scope_filter)
        try:
            from services.vip_cart import merchant_vip_threshold_int  # noqa: PLC0415

            vip_th = merchant_vip_threshold_int(dash_store)
            if vip_th is not None:
                q_extra = q_extra.filter(
                    func.coalesce(AbandonedCart.cart_value, 0) < float(vip_th)
                )
        except Exception:  # noqa: BLE001
            pass
        for ac in q_extra.limit(lim).all():
            aid = int(getattr(ac, "id", 0) or 0)
            if aid and aid not in seen:
                seen.add(aid)
                out.append(ac)
    except Exception:  # noqa: BLE001
        db.session.rollback()
    return out


__all__ = [
    "DASHBOARD_AUGMENT_CART_STATUSES",
    "augment_abandoned_candidates_with_purchased_recovery_carts",
    "group_is_purchased_terminal",
    "purchased_terminal_visible_on_active_lifecycle_tab",
]
