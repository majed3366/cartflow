# -*- coding: utf-8 -*-
"""Reality Score — internal validation only (never merchant-facing)."""
from __future__ import annotations

from typing import Any, Optional

from services.store_reality_simulator.accounting_v1 import normalize_accounting
from services.store_reality_simulator.planner_v1 import RealityPlan


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, float(v)))


def compute_reality_score(
    plan: RealityPlan,
    *,
    accounting: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    acc = normalize_accounting(accounting or {})
    n = max(1, len(plan.events))
    customers = max(1, len(set(plan.customers)))
    sessions = max(1, len(set(plan.sessions)))
    products = max(1, len(plan.products))
    types = plan.expected_event_counts

    customer_diversity = _clamp(min(100.0, customers / max(1, plan.duration_days) * 40))
    session_realism = _clamp(min(100.0, (sessions / customers) * 55))
    product_realism = _clamp(min(100.0, products * 18))
    traffic_realism = _clamp(
        40.0
        + (15.0 if types.get("page_viewed") else 0)
        + (15.0 if types.get("product_viewed") else 0)
        + (10.0 if types.get("scroll_depth_reached") else 0)
    )
    purchase_realism = _clamp(
        30.0
        + min(50.0, types.get("purchase_created", 0) * 12)
        + (10.0 if types.get("cart_abandoned", 0) > types.get("purchase_created", 0) else 0)
    )
    recovery_realism = _clamp(
        25.0
        + min(40.0, types.get("whatsapp_sent_mock", 0) * 10)
        + min(25.0, types.get("hesitation_reason_selected", 0) * 8)
    )
    behaviour_realism = _clamp(
        35.0
        + (20.0 if types.get("returned_to_site") else 0)
        + (15.0 if types.get("passive_return") else 0)
        + (15.0 if types.get("hesitation_reason_selected") else 0)
    )
    timeline_realism = _clamp(
        50.0 if any(t in types for t in ("whatsapp_scheduled", "purchase_created")) else 30.0
    )
    # Knowledge realism: evidence presence only — never claims KL quality
    knowledge_realism = _clamp(
        20.0
        + min(40.0, types.get("hesitation_reason_selected", 0) * 10)
        + min(20.0, types.get("purchase_created", 0) * 8)
    )

    processed = acc.get("processed", 0) + acc.get("persisted", 0)
    unsupported = acc.get("unsupported", 0)
    failed = acc.get("failed", 0)
    if acc.get("planned", 0) > 0:
        fidelity = _clamp(100.0 * processed / max(1, acc["planned"] - unsupported))
        if failed:
            fidelity = _clamp(fidelity - failed * 5)
    else:
        fidelity = 70.0  # plan-only score

    dims = {
        "customer_diversity": round(customer_diversity, 1),
        "traffic_realism": round(traffic_realism, 1),
        "purchase_realism": round(purchase_realism, 1),
        "product_realism": round(product_realism, 1),
        "recovery_realism": round(recovery_realism, 1),
        "knowledge_realism": round(knowledge_realism, 1),
        "timeline_realism": round(timeline_realism, 1),
        "session_realism": round(session_realism, 1),
        "behaviour_realism": round(behaviour_realism, 1),
        "execution_fidelity": round(fidelity, 1),
    }
    overall = round(sum(dims.values()) / len(dims), 1)
    return {
        "overall": overall,
        "dimensions": dims,
        "internal_only": True,
        "merchant_facing": False,
        "sample": {
            "events": n,
            "customers": customers,
            "sessions": sessions,
            "products": products,
        },
    }
