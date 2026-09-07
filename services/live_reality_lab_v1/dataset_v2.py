# -*- coding: utf-8 -*-
"""
Live Reality Dataset V2 — R13–R24 manifests (no AI, no lab ranker).

Gap map (reconstruction vs production-line V1):
  Lab tenant / gate / reset-apply-verify / COL→OGL→catalog→CDC→portfolio
      ALREADY PRESENT
  R1–R12 reason+no_phone+CDC seed
      ALREADY PRESENT (kept)
  نور العناية catalog + named products + missing-name fixture
      NEEDS ADDITION
  38 production-shaped carts with product lines
      NEEDS ADDITION
  Recovery logs / timeline / purchase truth
      NEEDS EXTENSION (write through existing models)
  shipping vs delivery reason keys
      ALREADY PRESENT in taxonomy; COL maps both → shipping_friction
  product_viewed storefront ingestion
      UNSUPPORTED (deferred signal; no pixel writer)
  Lab-synthetic ProductSignalEvent visits
      NEEDS ADDITION (explicit LAB-SYNTHETIC class)
  Next.js / frontend fixtures / lab ranker
      DO NOT REUSE
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from services.live_reality_lab_v1.contract_v1 import (
    DATASET_VERSION_V2,
    LAB_STORE_SLUG,
    LAB_VISIT_TRUTH_CLASS,
    SCENARIO_ALLOWLIST_V2,
    SCENARIO_R13,
    SCENARIO_R14,
    SCENARIO_R15,
    SCENARIO_R16,
    SCENARIO_R17,
    SCENARIO_R18,
    SCENARIO_R19,
    SCENARIO_R20,
    SCENARIO_R21,
    SCENARIO_R22,
    SCENARIO_R23,
    SCENARIO_R24,
)


def _manifest(
    *,
    scenario_id: str,
    reason_counts: Optional[Dict[str, int]],
    cart_count: int,
    sent_recovery: int,
    purchased: int,
    synthetic_visits: int,
    expected: Dict[str, Any],
    notes: str = "",
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "dataset_version": DATASET_VERSION_V2,
        "store_slug": LAB_STORE_SLUG,
        "store_display_name": "نور العناية",
        "truth": {
            "reason_counts": dict(reason_counts or {}),
            "no_phone_count": 0,
            "cdc_phase": None,
            "cart_count": int(cart_count),
            "sent_recovery_count": int(sent_recovery),
            "purchased_count": int(purchased),
            "synthetic_visit_count": int(synthetic_visits),
            "visit_truth_class": LAB_VISIT_TRUTH_CLASS
            if int(synthetic_visits) > 0
            else None,
        },
        "expected_operational_lane": expected.get("operational_lane"),
        "expected_commercial_family": expected.get("commercial_family"),
        "expected_catalog_primary": expected.get("catalog_primary"),
        "expected_cdc_state": expected.get("cdc_state"),
        "expected_portfolio_active_count": expected.get("portfolio_active_count"),
        "expected_deferred_families": list(expected.get("deferred_families") or []),
        "expected_unsupported_claims_count": int(
            expected.get("unsupported_claims_count") or 0
        ),
        "expected_cart_count": int(cart_count),
        "expected_named_products": 10,
        "expected_missing_name_fixture": 1,
        "lab_logic_valid": True,
        "real_merchant_visit_capability": False,
        "notes": notes,
    }


def scenario_manifests_v2() -> Dict[str, dict[str, Any]]:
    wait = {
        "operational_lane": "wait_insufficient_evidence",
        "commercial_family": None,
        "catalog_primary": None,
        "cdc_state": None,
        "portfolio_active_count": 0,
        "deferred_families": [],
        "unsupported_claims_count": 0,
    }
    return {
        SCENARIO_R13: _manifest(
            scenario_id=SCENARIO_R13,
            reason_counts={},
            cart_count=38,
            sent_recovery=12,
            purchased=0,
            synthetic_visits=0,
            expected=wait,
            notes="Sent recovery, no purchase completion. Recovery truth on CartRecoveryLog + timeline.",
        ),
        SCENARIO_R14: _manifest(
            scenario_id=SCENARIO_R14,
            reason_counts={},
            cart_count=38,
            sent_recovery=10,
            purchased=8,
            synthetic_visits=0,
            expected=wait,
            notes="Sent recovery then purchase_truth stop. No frontend simulation.",
        ),
        SCENARIO_R15: _manifest(
            scenario_id=SCENARIO_R15,
            reason_counts={},
            cart_count=38,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=0,
            expected=wait,
            notes="Zero visit rows. Carts exist. Do not claim merchant PDP views.",
        ),
        SCENARIO_R16: _manifest(
            scenario_id=SCENARIO_R16,
            reason_counts={},
            cart_count=0,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=24,
            expected=wait,
            notes="Lab-synthetic visits, no carts. REAL MERCHANT CAPABILITY = NO.",
        ),
        SCENARIO_R17: _manifest(
            scenario_id=SCENARIO_R17,
            reason_counts={"shipping": 12, "price": 5, "thinking": 3},
            cart_count=38,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=20,
            expected={
                "operational_lane": "shipping_friction",
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="Taxonomy key shipping → COL/OGL shipping_friction. Visits are lab-synthetic.",
        ),
        SCENARIO_R18: _manifest(
            scenario_id=SCENARIO_R18,
            reason_counts={"delivery": 12, "price": 5, "thinking": 3},
            cart_count=38,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=20,
            expected={
                "operational_lane": "shipping_friction",
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="Taxonomy key delivery (مدة التوصيل). Same COL family as R17 — not a second ranker family.",
        ),
        SCENARIO_R19: _manifest(
            scenario_id=SCENARIO_R19,
            reason_counts={},
            cart_count=38,
            sent_recovery=0,
            purchased=2,
            synthetic_visits=18,
            expected=wait,
            notes="Strong cart interest, weak purchase. COL has no cart_behavior compose path.",
        ),
        SCENARIO_R20: _manifest(
            scenario_id=SCENARIO_R20,
            reason_counts={"quality": 20, "shipping": 3, "thinking": 2},
            cart_count=38,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=0,
            expected={
                "operational_lane": "product_confidence_quality",
                "commercial_family": "product_confidence",
                "catalog_primary": "product_confidence",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="quality taxonomy → product_confidence. warranty is same family if dominant.",
        ),
        SCENARIO_R21: _manifest(
            scenario_id=SCENARIO_R21,
            reason_counts={"price": 12, "shipping": 5, "thinking": 3},
            cart_count=38,
            sent_recovery=0,
            purchased=0,
            synthetic_visits=0,
            expected={
                "operational_lane": "price_hesitation",
                "commercial_family": "price_hesitation",
                "catalog_primary": "price_hesitation",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R22: _manifest(
            scenario_id=SCENARIO_R22,
            reason_counts={},
            cart_count=38,
            sent_recovery=6,
            purchased=10,
            synthetic_visits=16,
            expected=wait,
            notes="Healthy named-product mix. No commercial mission. Visits lab-synthetic.",
        ),
        SCENARIO_R23: _manifest(
            scenario_id=SCENARIO_R23,
            reason_counts={},
            cart_count=38,
            sent_recovery=14,
            purchased=0,
            synthetic_visits=0,
            expected=wait,
            notes="Unresolved recovery: sent, no purchase, no reply.",
        ),
        SCENARIO_R24: _manifest(
            scenario_id=SCENARIO_R24,
            reason_counts={},
            cart_count=38,
            sent_recovery=12,
            purchased=12,
            synthetic_visits=0,
            expected=wait,
            notes="Resolved recovery: sent then purchase_truth + recovered status.",
        ),
    }


def get_scenario_manifest_v2(scenario_id: str) -> dict[str, Any]:
    sid = str(scenario_id or "").strip()
    if sid not in SCENARIO_ALLOWLIST_V2:
        raise ValueError("live_reality_lab_unknown_scenario")
    return dict(scenario_manifests_v2()[sid])


__all__ = [
    "get_scenario_manifest_v2",
    "scenario_manifests_v2",
]
