# -*- coding: utf-8 -*-
"""Seed curated merchant-visible demo Decisions for internal flag-ON testing."""
from __future__ import annotations

from typing import Any

from services.cart_workspace.admission_v1 import candidate_from_dict
from services.cart_workspace.shadow_pipeline_v1 import evaluate_candidate
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1


def seed_merchant_comprehension_set(store_slug: str, store: ShadowStoreV1) -> dict[str, Any]:
    """
    Load a small set that answers the 30-second questions:
    - one VIP (Zone A)
    - one normal Decision (Zone B)
    - one Quiet-path event that does not create a card (reply)
    - one completion for Zone D confidence
    """
    slug = (store_slug or "").strip() or "demo"
    steps = [
        {
            "store_slug": slug,
            "recovery_key": f"{slug}-mx-vip",
            "signal_class": "vip_detect",
            "proof_class": "override_eligible",
            "evidence_ids": [f"{slug}-vip"],
            "proof_sufficient": True,
            "override_eligible": True,
            "expected_action": "take_over_conversation",
        },
        {
            "store_slug": slug,
            "recovery_key": f"{slug}-mx-discount",
            "signal_class": "discount_request",
            "proof_class": "approve_deny_required",
            "evidence_ids": [f"{slug}-disc"],
            "proof_sufficient": True,
            "automation_capable": False,
            "human_gain_exceeds_cost": True,
            "expected_action": "approve_discount",
        },
        {
            "store_slug": slug,
            "recovery_key": f"{slug}-mx-reply",
            "signal_class": "customer_reply",
            "proof_class": "automation_can_answer",
            "evidence_ids": [f"{slug}-reply"],
            "proof_sufficient": True,
            "automation_capable": True,
        },
        {
            "store_slug": slug,
            "recovery_key": f"{slug}-mx-done",
            "signal_class": "purchase_completed",
            "proof_class": "terminal_completion",
            "evidence_ids": [f"{slug}-buy"],
            "proof_sufficient": True,
            "journey_completed": True,
        },
    ]
    results = []
    for step in steps:
        results.append(evaluate_candidate(candidate_from_dict(step), store=store))
    from services.cart_workspace.shadow_pipeline_v1 import shadow_snapshot

    snap = shadow_snapshot(slug, store=store)
    return {"ok": True, "seeded": len(steps), "results": results, "snapshot": snap}
