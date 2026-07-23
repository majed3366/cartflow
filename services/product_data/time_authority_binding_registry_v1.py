# -*- coding: utf-8 -*-
"""
TABF V1 — Time inventory + subsystem binding registry.

Documents every major time interpretation and which canonical clock it must use.
No page-owned chronology. No analytics.
"""
from __future__ import annotations

from typing import Any

from services.product_data.time_authority_binding_types_v1 import (
    BINDING_BOUND,
    BINDING_LEGACY,
    BINDING_PARTIAL,
    CLOCK_DISPLAY,
    CLOCK_EVENT,
    CLOCK_OBSERVATION,
    CLOCK_PROCESSING,
    CLOCK_REPLAY,
    TABF_REGISTRY_VERSION_V1,
)


def _site(
    *,
    site_id: str,
    description: str,
    location: str,
    clock: str,
    legacy_interpretation: str,
    bound_via: str,
    drift_risk: str,
) -> dict[str, Any]:
    return {
        "site_id": site_id,
        "description": description,
        "location": location,
        "canonical_clock": clock,
        "legacy_interpretation": legacy_interpretation,
        "bound_via": bound_via,
        "drift_risk": drift_risk,
        "version": TABF_REGISTRY_VERSION_V1,
    }


# Phase 1 — inventory of time interpretation sites (platform-wide).
TIME_INVENTORY_V1: dict[str, dict[str, Any]] = {
    "event_timestamps": _site(
        site_id="event_timestamps",
        description="Storefront/widget/cart event occurred_at stamps",
        location="ingress / models event fields",
        clock=CLOCK_EVENT,
        legacy_interpretation="provider/wall mix",
        bound_via="event_time_preserved_as_fact",
        drift_risk="low_if_not_reinterpreted",
    ),
    "scheduler_execution": _site(
        site_id="scheduler_execution",
        description="Recovery scanner / job due evaluation",
        location="services/recovery* / worker scopes",
        clock=CLOCK_PROCESSING,
        legacy_interpretation="datetime.utcnow / system",
        bound_via="worker_scope_authority_now",
        drift_risk="medium",
    ),
    "purchase_detection": _site(
        site_id="purchase_detection",
        description="Purchase truth detection windows",
        location="purchase_truth / conversion reconcile",
        clock=CLOCK_EVENT,
        legacy_interpretation="mixed event vs process",
        bound_via="event_time_primary",
        drift_risk="medium",
    ),
    "recovery_eligibility": _site(
        site_id="recovery_eligibility",
        description="Recovery delay / eligibility windows",
        location="recovery schedule materialization",
        clock=CLOCK_PROCESSING,
        legacy_interpretation="wall clock due",
        bound_via="authority_now_in_worker",
        drift_risk="medium",
    ),
    "cooldown_windows": _site(
        site_id="cooldown_windows",
        description="Widget/recovery cooldown intervals",
        location="widget / recovery settings",
        clock=CLOCK_PROCESSING,
        legacy_interpretation="wall deltas",
        bound_via="authority_now",
        drift_risk="low",
    ),
    "waiting_periods": _site(
        site_id="waiting_periods",
        description="Cart waiting / abandon delay",
        location="abandoned cart lifecycle",
        clock=CLOCK_EVENT,
        legacy_interpretation="event + delay",
        bound_via="event_plus_configured_delay",
        drift_risk="low",
    ),
    "freshness": _site(
        site_id="freshness",
        description="SCF freshness_state_v1 vs valid_until",
        location="surface_composition_foundation_v1.freshness_state_v1",
        clock=CLOCK_OBSERVATION,
        legacy_interpretation="as_of or wall",
        bound_via="tabf_resolve_bound_as_of",
        drift_risk="high_if_unbound",
    ),
    "timeline_ordering": _site(
        site_id="timeline_ordering",
        description="Merchant timeline / home ordering",
        location="merchant home / MEIF packages",
        clock=CLOCK_DISPLAY,
        legacy_interpretation="wall brief_date",
        bound_via="scf_priority_and_bound_as_of",
        drift_risk="high_if_page_owned",
    ),
    "replay": _site(
        site_id="replay",
        description="Historical / recovery replay scopes",
        location="time_authority.context_scope.historical_replay_scope",
        clock=CLOCK_REPLAY,
        legacy_interpretation="FixedAsOfProvider",
        bound_via="query_time_context",
        drift_risk="low_when_activated",
    ),
    "historical_simulation": _site(
        site_id="historical_simulation",
        description="Reality Simulator write + read clocks",
        location="store_reality_simulator + reality_attach_v1",
        clock=CLOCK_REPLAY,
        legacy_interpretation="SimulationClock vs Product Performance wall",
        bound_via="reality_attach_bind_time_plus_tabf",
        drift_risk="critical_if_pp_unbound",
    ),
    "dashboard_chronology": _site(
        site_id="dashboard_chronology",
        description="Dashboard KPI / summary chronology",
        location="dashboard_kpi_time_v1 / summary",
        clock=CLOCK_DISPLAY,
        legacy_interpretation="partial WP-5 binding",
        bound_via="dashboard_kpi_time_v1",
        drift_risk="medium",
    ),
    "operational_stability_windows": _site(
        site_id="operational_stability_windows",
        description="OTIF severity/stability as-of snapshots",
        location="operational_truth_foundation_v1",
        clock=CLOCK_OBSERVATION,
        legacy_interpretation="wall as_of default",
        bound_via="tabf_resolve_bound_as_of",
        drift_risk="medium",
    ),
}


def _subsystem(
    *,
    subsystem_id: str,
    owner: str,
    consumes_clock: str,
    binding_status: str,
    canonical_source: str,
    legacy_interpretation: str,
    conflicts: str,
    drift_risk: str,
    resolve_entry: str,
) -> dict[str, Any]:
    return {
        "subsystem_id": subsystem_id,
        "owner": owner,
        "consumes_clock": consumes_clock,
        "binding_status": binding_status,
        "canonical_source": canonical_source,
        "legacy_interpretation": legacy_interpretation,
        "conflicts": conflicts,
        "drift_risk": drift_risk,
        "resolve_entry": resolve_entry,
        "version": TABF_REGISTRY_VERSION_V1,
    }


# Phase 3 — binding audit targets (merchant Product Performance path).
SUBSYSTEM_BINDINGS_V1: dict[str, dict[str, Any]] = {
    "truth": _subsystem(
        subsystem_id="truth",
        owner="purchase/lifecycle truth",
        consumes_clock=CLOCK_EVENT,
        binding_status=BINDING_PARTIAL,
        canonical_source="event timestamps",
        legacy_interpretation="process time for some reconciles",
        conflicts="event vs process when late reconcile",
        drift_risk="medium",
        resolve_entry="preserve_event_time",
    ),
    "evidence": _subsystem(
        subsystem_id="evidence",
        owner="evidence_confidence_foundation_v1",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1",
        legacy_interpretation="wall _utc_naive_now",
        conflicts="none_when_bound",
        drift_risk="low",
        resolve_entry="generate_evidence_* as_of",
    ),
    "commerce_intelligence": _subsystem(
        subsystem_id="commerce_intelligence",
        owner="commerce_intelligence_synthesis_foundation_v1",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1",
        legacy_interpretation="wall _utc_naive_now",
        conflicts="none_when_bound",
        drift_risk="low",
        resolve_entry="generate_commerce_intelligence_syntheses_v1 as_of",
    ),
    "knowledge": _subsystem(
        subsystem_id="knowledge",
        owner="knowledge_foundation_v1",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1",
        legacy_interpretation="wall default as_of (CG-MEH-01)",
        conflicts="wall vs sim without QTC",
        drift_risk="high_if_unbound",
        resolve_entry="generate_knowledge_v1 as_of",
    ),
    "commercial_guidance": _subsystem(
        subsystem_id="commercial_guidance",
        owner="commercial_guidance_foundation_v1 / routing / presentation",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1",
        legacy_interpretation="wall default as_of",
        conflicts="none_when_caller_passes_bound_as_of",
        drift_risk="medium",
        resolve_entry="generate_*_v1 as_of chain",
    ),
    "operational_truth": _subsystem(
        subsystem_id="operational_truth",
        owner="operational_truth_foundation_v1",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1",
        legacy_interpretation="wall _utc_naive_now",
        conflicts="none_when_bound",
        drift_risk="low",
        resolve_entry="generate_operational_truth_v1 as_of",
    ),
    "surface_composition": _subsystem(
        subsystem_id="surface_composition",
        owner="surface_composition_foundation_v1",
        consumes_clock=CLOCK_OBSERVATION,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1 + freshness_state_v1(as_of)",
        legacy_interpretation="wall as_of; page freshness forbidden",
        conflicts="none_when_bound",
        drift_risk="low",
        resolve_entry="generate_surface_compositions_v1 as_of",
    ),
    "merchant_experience": _subsystem(
        subsystem_id="merchant_experience",
        owner="merchant_experience_integration_foundation_v1",
        consumes_clock=CLOCK_DISPLAY,
        binding_status=BINDING_BOUND,
        canonical_source="resolve_bound_as_of_v1 → SCF/KF",
        legacy_interpretation="wall summary chronology",
        conflicts="display vs observation if unbound",
        drift_risk="medium",
        resolve_entry="generate_merchant_experience_integration_v1 as_of",
    ),
}


def time_inventory_v1() -> dict[str, Any]:
    return {
        "version": TABF_REGISTRY_VERSION_V1,
        "sites": dict(TIME_INVENTORY_V1),
        "count": len(TIME_INVENTORY_V1),
    }


def subsystem_bindings_v1() -> dict[str, Any]:
    return {
        "version": TABF_REGISTRY_VERSION_V1,
        "subsystems": dict(SUBSYSTEM_BINDINGS_V1),
        "count": len(SUBSYSTEM_BINDINGS_V1),
    }


def tabf_registry_valid_v1() -> tuple[bool, list[str]]:
    errors: list[str] = []
    for sid, row in TIME_INVENTORY_V1.items():
        if row.get("site_id") != sid:
            errors.append(f"inventory_id_mismatch:{sid}")
        if not row.get("canonical_clock"):
            errors.append(f"inventory_missing_clock:{sid}")
    for sid, row in SUBSYSTEM_BINDINGS_V1.items():
        if row.get("subsystem_id") != sid:
            errors.append(f"subsystem_id_mismatch:{sid}")
        if row.get("binding_status") not in {
            BINDING_BOUND,
            BINDING_PARTIAL,
            BINDING_LEGACY,
        }:
            errors.append(f"bad_binding_status:{sid}")
    return (len(errors) == 0, errors)


__all__ = [
    "TIME_INVENTORY_V1",
    "SUBSYSTEM_BINDINGS_V1",
    "time_inventory_v1",
    "subsystem_bindings_v1",
    "tabf_registry_valid_v1",
]
