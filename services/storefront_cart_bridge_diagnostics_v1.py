# -*- coding: utf-8 -*-
"""Read-only Storefront Cart Bridge diagnostics (v1).

Operators can answer: which adapter, was cart normalized, was cart-event posted,
did AbandonedCart exist, was reason saved without cart, is cart orphaned?
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _parse_beacon(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
    return {}


def _empty_storefront_bridge_state() -> Dict[str, Any]:
    return {
        "adapter": None,
        "read_source": None,
        "normalized": None,
        "last_post_key": None,
        "last_post_at": None,
        "last_post_ok": None,
        "last_post_status": None,
        "last_skip_reason": None,
        "last_error": None,
        "cart_persisted": False,
        "reason_orphan_risk": False,
    }


def storefront_cart_bridge_state_from_beacon(
    beacon: Optional[dict[str, Any]],
) -> Dict[str, Any]:
    """Read storefront cart bridge snapshot from runtime-truth beacon."""
    b = _parse_beacon(beacon)
    rt = _as_dict(b.get("runtime_truth"))
    scb = rt.get("storefront_cart_bridge")
    if not isinstance(scb, dict):
        return _empty_storefront_bridge_state()
    base = _empty_storefront_bridge_state()
    for k in base:
        if k in scb:
            base[k] = scb.get(k)
    base["cart_persisted"] = bool(scb.get("cart_persisted"))
    base["reason_orphan_risk"] = bool(scb.get("reason_orphan_risk"))
    return base


def build_storefront_cart_bridge_truth_report(
    *,
    store_slug: str,
    session_id: Optional[str] = None,
    cart_id: Optional[str] = None,
    store_row: Any = None,
    abandoned_cart_row: Any = None,
    beacon: Optional[dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compose operator-facing truth report for a store/session/cart probe."""
    slug = (store_slug or "").strip()
    sid = (session_id or "").strip()
    cid = (cart_id or "").strip()
    bridge = storefront_cart_bridge_state_from_beacon(beacon)

    ac_facts: Dict[str, Any] = {
        "exists": False,
        "abandoned_cart_id": None,
        "cart_id": None,
        "session_id": None,
        "cart_value": None,
        "vip_mode": None,
        "status": None,
    }
    if abandoned_cart_row is not None:
        ac_facts = {
            "exists": True,
            "abandoned_cart_id": getattr(abandoned_cart_row, "id", None),
            "cart_id": (getattr(abandoned_cart_row, "zid_cart_id", None) or ""),
            "session_id": (
                getattr(abandoned_cart_row, "recovery_session_id", None) or ""
            ),
            "cart_value": getattr(abandoned_cart_row, "cart_value", None),
            "vip_mode": bool(getattr(abandoned_cart_row, "vip_mode", False)),
            "status": str(getattr(abandoned_cart_row, "status", "") or "").strip(),
        }

    raw_bridge_meta: Optional[dict[str, Any]] = None
    if abandoned_cart_row is not None and getattr(abandoned_cart_row, "raw_payload", None):
        try:
            prev = json.loads(abandoned_cart_row.raw_payload)
            if isinstance(prev, dict) and isinstance(
                prev.get("cf_storefront_cart_bridge"), dict
            ):
                raw_bridge_meta = prev.get("cf_storefront_cart_bridge")
        except (json.JSONDecodeError, TypeError, ValueError):
            raw_bridge_meta = None

    orphan_risk = bool(
        bridge.get("reason_orphan_risk")
        or (sid and not ac_facts.get("exists") and bridge.get("last_post_ok") is False)
    )

    questions: List[Dict[str, Any]] = [
        {
            "question": "Which adapter was used?",
            "answer": bridge.get("adapter"),
            "source": "beacon.storefront_cart_bridge.adapter",
        },
        {
            "question": "Was cart read from Zid API?",
            "answer": str(bridge.get("read_source") or "").startswith("zid_api"),
            "source": "beacon.storefront_cart_bridge.read_source",
        },
        {
            "question": "Was cart normalized?",
            "answer": bridge.get("normalized") is not None,
            "source": "beacon.storefront_cart_bridge.normalized",
        },
        {
            "question": "Was /api/cart-event posted?",
            "answer": bridge.get("last_post_ok") is True,
            "source": "beacon.storefront_cart_bridge.last_post_ok",
        },
        {
            "question": "Did AbandonedCart get created?",
            "answer": ac_facts.get("exists") is True,
            "source": "db.abandoned_cart",
        },
        {
            "question": "Why was cart skipped?",
            "answer": bridge.get("last_skip_reason"),
            "source": "beacon.storefront_cart_bridge.last_skip_reason",
        },
        {
            "question": "Was reason saved without cart?",
            "answer": orphan_risk,
            "source": "beacon.reason_orphan_risk + db",
        },
        {
            "question": "Is the cart orphaned?",
            "answer": orphan_risk and not ac_facts.get("exists"),
            "source": "composed",
        },
    ]

    return {
        "ok": True,
        "store_slug": slug,
        "session_id": sid or None,
        "cart_id": cid or None,
        "store_id": getattr(store_row, "id", None) if store_row is not None else None,
        "storefront_cart_bridge": bridge,
        "abandoned_cart": ac_facts,
        "persisted_bridge_meta": raw_bridge_meta,
        "operator_questions": questions,
    }


__all__ = [
    "build_storefront_cart_bridge_truth_report",
    "storefront_cart_bridge_state_from_beacon",
]
