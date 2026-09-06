# -*- coding: utf-8 -*-
"""Mission Catalog V1 — family inventory (no new intelligence)."""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, List

from services.commercial_decision_commitment_v1.contract_v1 import (
    MERCHANT_CONFIRM_FAMILY_ALLOWLIST,
)
from services.commercial_mission_v1.contract_v1 import (
    MISSION_PROFILES,
    get_mission_profile,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    FAMILY_CART_BEHAVIOR,
    FAMILY_COMMUNICATION_FOLLOWUP,
    FAMILY_PRICE_HESITATION,
    FAMILY_PRODUCT_CONFIDENCE,
    FAMILY_PRODUCT_OPPORTUNITY_FOCUS,
    FAMILY_RECOVERY_HESITATION,
    FAMILY_SHIPPING_FRICTION,
)
from services.mission_catalog_v1.contract_v1 import (
    LIFECYCLE_COL_ONLY,
    LIFECYCLE_MISSION_READY,
    LIFECYCLE_UNSUPPORTED,
)


def _entry(
    *,
    family: str,
    opportunity_key_template: str,
    truth_source: str,
    evidence_sufficiency: str,
    actionable_states: str,
    compatible_metric: str,
    execution_proof: str,
    recheck: str,
    lifecycle_support: str,
    notes: str = "",
) -> dict[str, Any]:
    profile = get_mission_profile(family)
    return {
        "family": family,
        "opportunity_key_template": opportunity_key_template,
        "truth_source": truth_source,
        "evidence_sufficiency": evidence_sufficiency,
        "actionable_partial_insufficient": actionable_states,
        "compatible_metric": compatible_metric
        if compatible_metric
        else (profile.metric_key if profile else None),
        "execution_proof_compatibility": execution_proof,
        "recheck_compatibility": recheck,
        "lifecycle_support": lifecycle_support,
        "mission_profile_registered": profile is not None,
        "cdc_merchant_confirm_allowlisted": family in MERCHANT_CONFIRM_FAMILY_ALLOWLIST,
        "notes": notes,
    }


def catalog_inventory_v1() -> List[dict[str, Any]]:
    """
    Static inventory of families CartFlow may consider.

    Does not invent families. product_confidence_quality (task name) maps to
    COL family `product_confidence`.
    """
    return [
        _entry(
            family=FAMILY_SHIPPING_FRICTION,
            opportunity_key_template="col:shipping_friction:shipping:{store_slug}",
            truth_source="merchant_reason_counts (shipping/delivery) via COL",
            evidence_sufficiency="READY total≥8 top≥5 share≥0.40; PARTIAL lower",
            actionable_states="READY→actionable; PARTIAL→watch; INSUFFICIENT→none",
            compatible_metric="hesitation_share",
            execution_proof="merchant_execution_confirm (allowlisted)",
            recheck="shipping_share_material_change_or_sample_ge_8",
            lifecycle_support=LIFECYCLE_MISSION_READY,
        ),
        _entry(
            family=FAMILY_PRICE_HESITATION,
            opportunity_key_template="col:price_hesitation:price:{store_slug}",
            truth_source="merchant_reason_counts (price) via COL",
            evidence_sufficiency="READY total≥8 top≥5 share≥0.40; PARTIAL lower",
            actionable_states="READY→actionable; PARTIAL→watch; INSUFFICIENT→none",
            compatible_metric="hesitation_share",
            execution_proof="merchant_execution_confirm (allowlisted)",
            recheck="price_share_material_change_or_sample_ge_8",
            lifecycle_support=LIFECYCLE_MISSION_READY,
        ),
        _entry(
            family=FAMILY_PRODUCT_CONFIDENCE,
            opportunity_key_template="col:product_confidence:{reason}:{store_slug}",
            truth_source="merchant_reason_counts (quality/warranty) via COL",
            evidence_sufficiency="READY total≥8 top≥5 share≥0.40; PARTIAL lower",
            actionable_states="READY→actionable; PARTIAL→watch; INSUFFICIENT→none",
            compatible_metric="hesitation_share",
            execution_proof="merchant_execution_confirm (allowlisted)",
            recheck="product_confidence_share_material_change_or_sample_ge_8",
            lifecycle_support=LIFECYCLE_MISSION_READY,
            notes="Merchandising Mission Slice V1 — mission-ready",
        ),
        _entry(
            family=FAMILY_PRODUCT_OPPORTUNITY_FOCUS,
            opportunity_key_template="col:product_opportunity_focus:product_trust:{store_slug}",
            truth_source="combined quality+warranty pool via COL (no exposure)",
            evidence_sufficiency="same hesitation gate on trust pool; skipped if top is quality/warranty",
            actionable_states="READY→actionable; PARTIAL→watch; INSUFFICIENT→none",
            compatible_metric="hesitation_share",
            execution_proof="merchant_execution_confirm (allowlisted)",
            recheck="product_trust_pool_share_material_change_or_sample_ge_8",
            lifecycle_support=LIFECYCLE_MISSION_READY,
            notes="No placement/ads/discount claims",
        ),
        _entry(
            family=FAMILY_COMMUNICATION_FOLLOWUP,
            opportunity_key_template="col:communication_followup:no_phone:{store_slug}",
            truth_source="cart health no_phone teaser via COL",
            evidence_sufficiency="READY no_phone≥3; PARTIAL ≥1",
            actionable_states="COL READY/PARTIAL only",
            compatible_metric="no_phone count",
            execution_proof="CDC allowlisted; mission profile NOT registered",
            recheck="COL recheck_ar only",
            lifecycle_support=LIFECYCLE_COL_ONLY,
        ),
        _entry(
            family=FAMILY_RECOVERY_HESITATION,
            opportunity_key_template="col:recovery_hesitation:{reason}:{store_slug}",
            truth_source="merchant_reason_counts (thinking/other) via COL",
            evidence_sufficiency="hesitation gate",
            actionable_states="COL only",
            compatible_metric="hesitation_share",
            execution_proof="not mission-ready",
            recheck="COL only",
            lifecycle_support=LIFECYCLE_COL_ONLY,
        ),
        _entry(
            family=FAMILY_CART_BEHAVIOR,
            opportunity_key_template="n/a",
            truth_source="COL family reserved; not composed as Home primary today",
            evidence_sufficiency="unsupported in current COL compose",
            actionable_states="none",
            compatible_metric="",
            execution_proof="unsupported",
            recheck="unsupported",
            lifecycle_support=LIFECYCLE_UNSUPPORTED,
        ),
    ]


def inventory_by_family() -> Dict[str, dict[str, Any]]:
    return {e["family"]: e for e in catalog_inventory_v1()}


def mission_ready_families() -> FrozenSet[str]:
    return frozenset(MISSION_PROFILES.keys())


__all__ = [
    "catalog_inventory_v1",
    "inventory_by_family",
    "mission_ready_families",
]
