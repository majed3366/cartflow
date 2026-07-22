# -*- coding: utf-8 -*-
"""
OTIF V1 — Operational Truth Registry.

Inventory of operational facts CartFlow already produces.
No invented concepts. No page-specific logic. No recommendations.
"""
from __future__ import annotations

from typing import Any

from services.product_data.operational_truth_types_v1 import OT_REGISTRY_VERSION_V1
from services.product_data.surface_composition_types_v1 import (
    CLASS_CRITICAL_ATTENTION,
    CLASS_OPERATIONAL_HEALTH,
    CLASS_RECOVERY_HEALTH,
    SURFACE_CARTS,
    SURFACE_COMMUNICATION,
    SURFACE_DECISION,
    SURFACE_HOME,
)


def _truth(
    *,
    truth_id: str,
    owner: str,
    source: str,
    metric_key: str,
    severity_policy: str,
    freshness_policy: str,
    lifecycle_policy: str,
    visibility_policy: str,
    stability_policy: str,
    confidence_policy: str,
    merchant_relevance: str,
    expiration_policy: str,
    evidence_threshold: int,
    surfaces: tuple[str, ...],
    information_class: str,
    attention_required_when: str,
) -> dict[str, Any]:
    return {
        "id": truth_id,
        "owner": owner,
        "source": source,
        "metric_key": metric_key,
        "severity": severity_policy,
        "freshness": freshness_policy,
        "lifecycle": lifecycle_policy,
        "visibility": visibility_policy,
        "stability": stability_policy,
        "confidence": confidence_policy,
        "merchant_relevance": merchant_relevance,
        "expiration_policy": expiration_policy,
        "evidence_threshold": evidence_threshold,
        "destination_surfaces": list(surfaces),
        "information_class": information_class,
        "attention_required_when": attention_required_when,
        "version": OT_REGISTRY_VERSION_V1,
    }


# Canonical inventory — only facts already durable in CartFlow.
OPERATIONAL_TRUTH_REGISTRY_V1: dict[str, dict[str, Any]] = {
    "ot_waiting_carts": _truth(
        truth_id="ot_waiting_carts",
        owner="operational_truth_foundation_v1",
        source="abandoned_carts.store_id_count",
        metric_key="abandoned_carts",
        severity_policy="bands_waiting_carts",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_count_above_threshold",
        visibility_policy="expose_when_threshold_met",
        stability_policy="hysteresis_waiting_carts",
        confidence_policy="high_when_store_bound",
        merchant_relevance="requires_attention_when_waiting_carts_exist",
        expiration_policy="cleared_when_count_below_exit_band",
        evidence_threshold=1,
        surfaces=(SURFACE_HOME, SURFACE_CARTS, SURFACE_DECISION),
        information_class=CLASS_CRITICAL_ATTENTION,
        attention_required_when="count >= warning_enter",
    ),
    "ot_recovery_backlog": _truth(
        truth_id="ot_recovery_backlog",
        owner="operational_truth_foundation_v1",
        source="recovery_schedules.store_slug_count",
        metric_key="recovery_schedules",
        severity_policy="bands_recovery_backlog",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_count_above_threshold",
        visibility_policy="expose_when_threshold_met",
        stability_policy="hysteresis_recovery_backlog",
        confidence_policy="high_when_schedules_present",
        merchant_relevance="recovery_queue_pressure",
        expiration_policy="cleared_when_count_below_exit_band",
        evidence_threshold=1,
        surfaces=(SURFACE_HOME, SURFACE_CARTS),
        information_class=CLASS_RECOVERY_HEALTH,
        attention_required_when="count >= warning_enter",
    ),
    "ot_communication_health": _truth(
        truth_id="ot_communication_health",
        owner="operational_truth_foundation_v1",
        source="cart_recovery_logs.mock_sent_count",
        metric_key="mock_whatsapp_sent",
        severity_policy="bands_communication_activity",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_activity_present",
        visibility_policy="expose_when_threshold_met",
        stability_policy="threshold_stable",
        confidence_policy="medium_mock_channel",
        merchant_relevance="communication_activity_exists",
        expiration_policy="cleared_when_no_activity",
        evidence_threshold=1,
        surfaces=(SURFACE_COMMUNICATION, SURFACE_HOME),
        information_class=CLASS_OPERATIONAL_HEALTH,
        attention_required_when="count >= 1",
    ),
    "ot_hesitation_coverage": _truth(
        truth_id="ot_hesitation_coverage",
        owner="operational_truth_foundation_v1",
        source="cart_recovery_reasons.store_slug_count",
        metric_key="hesitation_reasons",
        severity_policy="bands_informational_coverage",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_count_above_threshold",
        visibility_policy="expose_when_threshold_met",
        stability_policy="threshold_stable",
        confidence_policy="high_when_reasons_present",
        merchant_relevance="hesitation_evidence_coverage",
        expiration_policy="cleared_when_count_zero",
        evidence_threshold=1,
        surfaces=(SURFACE_HOME, SURFACE_DECISION),
        information_class=CLASS_OPERATIONAL_HEALTH,
        attention_required_when="never_critical",
    ),
    "ot_purchase_truth_coverage": _truth(
        truth_id="ot_purchase_truth_coverage",
        owner="operational_truth_foundation_v1",
        source="purchase_truth_records.store_slug_count",
        metric_key="purchase_truth",
        severity_policy="bands_informational_coverage",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_count_above_threshold",
        visibility_policy="expose_when_threshold_met",
        stability_policy="threshold_stable",
        confidence_policy="high_when_purchases_present",
        merchant_relevance="purchase_truth_coverage",
        expiration_policy="cleared_when_count_zero",
        evidence_threshold=1,
        surfaces=(SURFACE_HOME,),
        information_class=CLASS_OPERATIONAL_HEALTH,
        attention_required_when="never_critical",
    ),
    "ot_recovery_execution_health": _truth(
        truth_id="ot_recovery_execution_health",
        owner="operational_truth_foundation_v1",
        source="recovery_schedules+mock_whatsapp_composite",
        metric_key="recovery_execution_composite",
        severity_policy="bands_recovery_execution",
        freshness_policy="durable_count_as_of_generation",
        lifecycle_policy="active_while_composite_above_threshold",
        visibility_policy="expose_when_threshold_met",
        stability_policy="hysteresis_recovery_execution",
        confidence_policy="medium_composite",
        merchant_relevance="recovery_execution_pressure",
        expiration_policy="cleared_when_composite_below_exit",
        evidence_threshold=1,
        surfaces=(SURFACE_CARTS, SURFACE_HOME),
        information_class=CLASS_RECOVERY_HEALTH,
        attention_required_when="composite >= warning_enter",
    ),
}


# Stability / severity bands (governance — not recommendations).
SEVERITY_BANDS_V1: dict[str, dict[str, int]] = {
    "bands_waiting_carts": {
        "critical_enter": 10,
        "warning_enter": 3,
        "critical_exit": 7,
        "warning_exit": 1,
    },
    "bands_recovery_backlog": {
        "critical_enter": 20,
        "warning_enter": 5,
        "critical_exit": 12,
        "warning_exit": 2,
    },
    "bands_communication_activity": {
        "critical_enter": 9999,  # activity is not critical by itself
        "warning_enter": 10,
        "critical_exit": 9999,
        "warning_exit": 1,
    },
    "bands_informational_coverage": {
        "critical_enter": 9999,
        "warning_enter": 9999,
        "critical_exit": 9999,
        "warning_exit": 9999,
    },
    "bands_recovery_execution": {
        "critical_enter": 25,
        "warning_enter": 8,
        "critical_exit": 15,
        "warning_exit": 3,
    },
}


def operational_truth_registry_v1() -> dict[str, Any]:
    return {
        "version": OT_REGISTRY_VERSION_V1,
        "truths": dict(OPERATIONAL_TRUTH_REGISTRY_V1),
        "severity_bands": dict(SEVERITY_BANDS_V1),
        "count": len(OPERATIONAL_TRUTH_REGISTRY_V1),
    }


def operational_truth_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    required = (
        "id",
        "owner",
        "source",
        "severity",
        "freshness",
        "lifecycle",
        "visibility",
        "stability",
        "confidence",
        "merchant_relevance",
        "expiration_policy",
    )
    for tid, row in OPERATIONAL_TRUTH_REGISTRY_V1.items():
        for key in required:
            if not row.get(key):
                errors.append(f"missing:{tid}:{key}")
        if row.get("id") != tid:
            errors.append(f"id_mismatch:{tid}")
    return (len(errors) == 0, errors)


__all__ = [
    "OPERATIONAL_TRUTH_REGISTRY_V1",
    "SEVERITY_BANDS_V1",
    "operational_truth_registry_v1",
    "operational_truth_registry_valid_v1",
]
