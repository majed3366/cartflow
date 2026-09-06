# -*- coding: utf-8 -*-
"""
Live Reality Dataset V1 — deterministic scenario manifests (no AI).

Truth written via CartRecoveryReason + lab AbandonedCart + CDC only.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from services.live_reality_lab_v1.contract_v1 import (
    DATASET_VERSION,
    LAB_STORE_SLUG,
    SCENARIO_ALLOWLIST,
    SCENARIO_R1,
    SCENARIO_R10,
    SCENARIO_R11,
    SCENARIO_R12,
    SCENARIO_R2,
    SCENARIO_R3,
    SCENARIO_R4,
    SCENARIO_R5,
    SCENARIO_R6,
    SCENARIO_R7,
    SCENARIO_R8,
    SCENARIO_R9,
)


def _manifest(
    *,
    scenario_id: str,
    reason_counts: Optional[Dict[str, int]],
    no_phone_count: int,
    cdc: Optional[str],
    expected: Dict[str, Any],
    notes: str = "",
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "dataset_version": DATASET_VERSION,
        "store_slug": LAB_STORE_SLUG,
        "truth": {
            "reason_counts": dict(reason_counts or {}),
            "no_phone_count": int(no_phone_count),
            "cdc_phase": cdc,
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
        "notes": notes,
    }


def scenario_manifests_v1() -> Dict[str, dict[str, Any]]:
    """All allowlisted scenarios → machine-readable expected outcomes."""
    return {
        SCENARIO_R1: _manifest(
            scenario_id=SCENARIO_R1,
            reason_counts={},
            no_phone_count=12,
            cdc=None,
            expected={
                "operational_lane": "communication_followup",
                "commercial_family": None,
                "catalog_primary": None,
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="Contact obligation only",
        ),
        SCENARIO_R2: _manifest(
            scenario_id=SCENARIO_R2,
            reason_counts={"shipping": 12, "price": 5, "thinking": 3},
            no_phone_count=0,
            cdc=None,
            expected={
                "operational_lane": None,  # hesitation OGL may be shipping
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R3: _manifest(
            scenario_id=SCENARIO_R3,
            reason_counts={"price": 12, "shipping": 5, "thinking": 3},
            no_phone_count=0,
            cdc=None,
            expected={
                "operational_lane": None,
                "commercial_family": "price_hesitation",
                "catalog_primary": "price_hesitation",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R4: _manifest(
            scenario_id=SCENARIO_R4,
            reason_counts={"quality": 20, "shipping": 3, "thinking": 2},
            no_phone_count=0,
            cdc=None,
            expected={
                "operational_lane": None,
                "commercial_family": "product_confidence",
                "catalog_primary": "product_confidence",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R5: _manifest(
            scenario_id=SCENARIO_R5,
            reason_counts={"quality": 12, "warranty": 12, "shipping": 2},
            no_phone_count=0,
            cdc=None,
            expected={
                "operational_lane": None,
                "commercial_family": "product_opportunity_focus",
                "catalog_primary": "product_opportunity_focus",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R6: _manifest(
            scenario_id=SCENARIO_R6,
            reason_counts={},
            no_phone_count=0,
            cdc=None,
            expected={
                "operational_lane": "wait_insufficient",
                "commercial_family": None,
                "catalog_primary": None,
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R7: _manifest(
            scenario_id=SCENARIO_R7,
            reason_counts={"quality": 12, "warranty": 12, "shipping": 2},
            no_phone_count=39,
            cdc=None,
            expected={
                "operational_lane": "communication_followup",
                "commercial_family": "product_opportunity_focus",
                "catalog_primary": "product_opportunity_focus",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="Priority Surface Contract V1 coexistence",
        ),
        SCENARIO_R8: _manifest(
            scenario_id=SCENARIO_R8,
            reason_counts={"shipping": 12, "price": 5, "thinking": 3},
            no_phone_count=0,
            cdc="ACTION_CHOSEN",
            expected={
                "operational_lane": None,
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": "ACTION_CHOSEN",
                "portfolio_active_count": 1,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R9: _manifest(
            scenario_id=SCENARIO_R9,
            reason_counts={"shipping": 12, "price": 5, "thinking": 3},
            no_phone_count=0,
            cdc="UNDER_MEASUREMENT",
            expected={
                "operational_lane": None,
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": "UNDER_MEASUREMENT",
                "portfolio_active_count": 1,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R10: _manifest(
            scenario_id=SCENARIO_R10,
            reason_counts={"shipping": 12, "price": 5, "thinking": 3},
            no_phone_count=0,
            cdc="RECHECK_DUE",
            expected={
                "operational_lane": None,
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": "RECHECK_DUE",
                "portfolio_active_count": 1,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
        ),
        SCENARIO_R11: _manifest(
            scenario_id=SCENARIO_R11,
            reason_counts={"shipping": 12, "price": 12, "thinking": 2},
            no_phone_count=0,
            cdc="UNDER_MEASUREMENT",
            expected={
                "operational_lane": None,
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": "UNDER_MEASUREMENT",
                "portfolio_active_count": 1,
                "deferred_families": ["price_hesitation"],
                "unsupported_claims_count": 0,
            },
            notes="Active shipping measurement; price deferred",
        ),
        SCENARIO_R12: _manifest(
            scenario_id=SCENARIO_R12,
            reason_counts={"shipping": 12, "price": 12, "thinking": 2},
            no_phone_count=0,
            cdc="CLOSED",
            expected={
                "operational_lane": None,
                "commercial_family": "shipping_friction",
                "catalog_primary": "shipping_friction",
                "cdc_state": None,
                "portfolio_active_count": 0,
                "deferred_families": [],
                "unsupported_claims_count": 0,
            },
            notes="Capacity released after close",
        ),
    }


def get_scenario_manifest(scenario_id: str) -> dict[str, Any]:
    sid = str(scenario_id or "").strip()
    if sid not in SCENARIO_ALLOWLIST:
        raise ValueError("live_reality_lab_unknown_scenario")
    return dict(scenario_manifests_v1()[sid])


__all__ = [
    "get_scenario_manifest",
    "scenario_manifests_v1",
]
