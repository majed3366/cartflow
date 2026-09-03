# -*- coding: utf-8 -*-
"""
Commercial Intelligence Preview V1 — flag-gated founder-only surface.

Gate: CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW (default OFF → 404).
Preview route: GET /preview/commercial-intelligence
Simulation truth is labeled SIMULATION_TRUTH throughout — never production merchant data.
No WhatsApp, no Scheduler, no external API calls.
"""
from __future__ import annotations

import os
from typing import Any, Mapping

FLAG = "CARTFLOW_COMMERCIAL_INTELLIGENCE_PREVIEW"
_TRUE = frozenset({"1", "true", "yes", "on"})

SIMULATION_TRUTH_LABEL = "SIMULATION_TRUTH"
PRODUCTION_TRUTH_LABEL = "PRODUCTION_TRUTH"


def commercial_intelligence_preview_enabled(
    *, environ: Mapping[str, str] | None = None
) -> bool:
    """Default OFF — fail closed. Unset / empty → False."""
    env = environ if environ is not None else os.environ
    raw = str(env.get(FLAG, "") or "").strip().lower()
    return raw in _TRUE


def build_preview_payload_v1() -> dict[str, Any]:
    """
    Build the simulation-truth payload for the founder preview.

    All missions carry simulation_only=True and truth_source=SIMULATION_TRUTH.
    This function must NEVER read production DB tables or real merchant stores.
    """
    from services.revenue_reality_validation_v1.review_lab_v1 import (  # noqa: PLC0415
        build_review_lab_payload_v1,
    )

    lab = build_review_lab_payload_v1()
    # Enforce simulation truth provenance on every mission
    for m in lab.get("missions", {}).get("all", []):
        m["truth_source"] = SIMULATION_TRUTH_LABEL
        m["simulation_only"] = True
    primary = (lab.get("home") or {}).get("primary_mission")
    if primary:
        primary["truth_source"] = SIMULATION_TRUTH_LABEL
        primary["simulation_only"] = True
    for s in (lab.get("home") or {}).get("secondary_opportunities") or []:
        s["truth_source"] = SIMULATION_TRUTH_LABEL
        s["simulation_only"] = True
    for m in (lab.get("workspace") or {}).get("cdi_missions") or []:
        m["truth_source"] = SIMULATION_TRUTH_LABEL
        m["simulation_only"] = True
    # Top-level markers
    lab["truth_source"] = SIMULATION_TRUTH_LABEL
    lab["preview_version"] = "commercial_intelligence_preview_v1"
    lab["production_truth_present"] = False
    return lab


def verify_no_production_truth_leak(payload: dict[str, Any]) -> list[str]:
    """Return list of violations if simulation data is missing provenance."""
    violations: list[str] = []
    if payload.get("truth_source") != SIMULATION_TRUTH_LABEL:
        violations.append("top_level_truth_source_missing")
    if payload.get("production_truth_present"):
        violations.append("production_truth_present_must_be_false")
    for m in payload.get("missions", {}).get("all", []):
        if not m.get("simulation_only"):
            violations.append(f"mission_{m.get('mission_id','?')}_not_labeled_simulation")
    return violations


__all__ = [
    "FLAG",
    "PRODUCTION_TRUTH_LABEL",
    "SIMULATION_TRUTH_LABEL",
    "build_preview_payload_v1",
    "commercial_intelligence_preview_enabled",
    "verify_no_production_truth_leak",
]
