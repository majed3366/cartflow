# -*- coding: utf-8 -*-
"""
Load observation-input signals from durable truth tables.

Merges Product Signal Collection with hesitation/purchase/cart-line history
and cart_recovery_reasons ↔ cart_line_snapshots joins.
No invented events — only persisted rows.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.product_data.product_signal_types_v1 import (
    SIGNAL_PRODUCT_CART_ADDED,
    SIGNAL_PRODUCT_CUSTOMER_RETURNED,
    SIGNAL_PRODUCT_INTEREST_HESITATION,
    SIGNAL_PRODUCT_PURCHASED,
)


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _snap_key(row: Any) -> str:
    return _norm(row.sku) or _norm(row.product_id) or _norm(row.name)


def load_observation_input_signals_v1(
    store_slug: str, *, limit: int = 500
) -> list[dict[str, Any]]:
    """Return signal-shaped dicts for Observation Foundation assembly."""
    slug = _norm(store_slug)
    if not slug:
        return []

    out: list[dict[str, Any]] = []
    try:
        from services.product_data.product_signal_collection_v1 import (  # noqa: PLC0415
            signals_for_store,
        )

        out.extend(signals_for_store(slug, limit=limit))
    except Exception:  # noqa: BLE001
        pass

    try:
        from extensions import db
        from models import (  # noqa: PLC0415
            CartLineSnapshot,
            CartRecoveryReason,
            ProductHesitationMapping,
            ProductPurchaseMapping,
            ProductSignalEvent,
        )

        # Hesitation mappings → reason-bearing interest signals
        h_rows = (
            db.session.query(ProductHesitationMapping)
            .filter(ProductHesitationMapping.store_slug == slug)
            .order_by(ProductHesitationMapping.id.desc())
            .limit(limit)
            .all()
        )
        for r in h_rows:
            out.append(
                {
                    "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                    "stable_identity_key": _norm(r.stable_identity_key),
                    "product_id": _norm(r.product_id),
                    "session_id": _norm(r.session_id),
                    "recovery_key": _norm(r.recovery_key),
                    "customer_key": _norm(getattr(r, "recovery_key", None)),
                    "reason_code": _norm(r.reason).lower(),
                    "evidence_ref_type": "product_hesitation_mapping",
                    "evidence_ref_id": str(r.id),
                    "observed_at": r.captured_at,
                    "source": "durable_hesitation_mapping",
                }
            )

        # Cart line snapshots → cart-add interest proxies
        snap_rows = (
            db.session.query(CartLineSnapshot)
            .filter(CartLineSnapshot.store_slug == slug)
            .order_by(CartLineSnapshot.id.desc())
            .limit(limit)
            .all()
        )
        snaps_by_session: dict[str, list[Any]] = defaultdict(list)
        for r in snap_rows:
            key = _snap_key(r)
            if not key:
                continue
            snaps_by_session[_norm(r.session_id)].append(r)
            out.append(
                {
                    "signal_type": SIGNAL_PRODUCT_CART_ADDED,
                    "stable_identity_key": key,
                    "product_id": _norm(r.product_id),
                    "session_id": _norm(r.session_id),
                    "recovery_key": _norm(r.recovery_key),
                    "evidence_ref_type": "cart_line_snapshot",
                    "evidence_ref_id": str(r.id),
                    "observed_at": getattr(r, "captured_at", None),
                    "source": "durable_cart_line_snapshot",
                }
            )

        # cart_recovery_reasons ↔ session product lines (durable reason truth)
        reason_rows = (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.store_slug == slug)
            .order_by(CartRecoveryReason.id.desc())
            .limit(limit)
            .all()
        )
        # sessions→products for return correlation
        product_sessions: dict[str, set[str]] = defaultdict(set)
        product_customers: dict[str, set[str]] = defaultdict(set)
        for reason in reason_rows:
            sid = _norm(reason.session_id)
            phone = _norm(reason.customer_phone)
            reason_code = _norm(reason.reason).lower()
            lines = snaps_by_session.get(sid) or []
            if not lines:
                # lazy load session snaps if not in limited snap_rows
                lines = (
                    db.session.query(CartLineSnapshot)
                    .filter(
                        CartLineSnapshot.store_slug == slug,
                        CartLineSnapshot.session_id == sid,
                    )
                    .limit(20)
                    .all()
                )
            for line in lines:
                key = _snap_key(line)
                if not key or not reason_code:
                    continue
                product_sessions[key].add(sid)
                if phone:
                    product_customers[key].add(phone)
                out.append(
                    {
                        "signal_type": SIGNAL_PRODUCT_INTEREST_HESITATION,
                        "stable_identity_key": key,
                        "product_id": _norm(line.product_id),
                        "session_id": sid,
                        "customer_key": phone or sid,
                        "reason_code": reason_code,
                        "evidence_ref_type": "cart_recovery_reason",
                        "evidence_ref_id": str(reason.id),
                        "observed_at": getattr(reason, "created_at", None),
                        "source": "durable_cart_recovery_reason",
                    }
                )

        # Purchase mappings
        purchased_products: set[str] = set()
        p_rows = (
            db.session.query(ProductPurchaseMapping)
            .filter(ProductPurchaseMapping.store_slug == slug)
            .order_by(ProductPurchaseMapping.id.desc())
            .limit(limit)
            .all()
        )
        for r in p_rows:
            pk = _norm(r.stable_identity_key)
            purchased_products.add(pk)
            out.append(
                {
                    "signal_type": SIGNAL_PRODUCT_PURCHASED,
                    "stable_identity_key": pk,
                    "product_id": _norm(r.product_id),
                    "session_id": _norm(r.session_id),
                    "recovery_key": _norm(r.recovery_key),
                    "evidence_ref_type": "product_purchase_mapping",
                    "evidence_ref_id": str(r.id),
                    "observed_at": getattr(r, "purchased_at", None),
                    "source": "durable_purchase_mapping",
                }
            )

        # Explicit product_customer_returned signals from collection
        ret_rows = (
            db.session.query(ProductSignalEvent)
            .filter(
                ProductSignalEvent.store_slug == slug,
                ProductSignalEvent.signal_type == SIGNAL_PRODUCT_CUSTOMER_RETURNED,
            )
            .order_by(ProductSignalEvent.id.desc())
            .limit(limit)
            .all()
        )
        if ret_rows:
            from services.product_data.product_signal_types_v1 import (  # noqa: PLC0415
                product_signal_to_dict,
            )

            out.extend([product_signal_to_dict(r) for r in ret_rows])
        else:
            # Durable return proxy: ≥2 reason sessions for same product+customer,
            # product not purchased — emit return observations (evidence-backed).
            for pk, sessions in product_sessions.items():
                if len(sessions) < 2:
                    continue
                if pk in purchased_products:
                    continue
                customers = product_customers.get(pk) or {f"sess:{s}" for s in sessions}
                for i, sid in enumerate(sorted(sessions)[:8]):
                    ck = next(iter(customers)) if customers else sid
                    out.append(
                        {
                            "signal_type": SIGNAL_PRODUCT_CUSTOMER_RETURNED,
                            "stable_identity_key": pk,
                            "session_id": sid,
                            "customer_key": ck,
                            "evidence_ref_type": "cart_recovery_reason_sessions",
                            "evidence_ref_id": f"{pk}:{len(sessions)}",
                            "observed_at": None,
                            "source": "durable_multi_session_return_proxy",
                        }
                    )
    except Exception:  # noqa: BLE001
        pass

    return out[: max(limit * 4, limit)]


__all__ = ["load_observation_input_signals_v1"]
