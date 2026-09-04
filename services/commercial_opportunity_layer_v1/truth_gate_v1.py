# -*- coding: utf-8 -*-
"""Commercial Opportunity Layer V1 — production truth gate."""
from __future__ import annotations

from typing import Any, Mapping

from services.business_findings_families_v1 import (
    MIN_DOMINANT_COUNT,
    MIN_DOMINANT_SHARE,
    MIN_HESITATION_TOTAL,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    TRUTH_INSUFFICIENT,
    TRUTH_PRODUCTION_PARTIAL,
    TRUTH_PRODUCTION_READY,
    TRUTH_SIMULATION_ONLY,
)


def classify_hesitation_truth_v1(
    *,
    total: int,
    top_count: int,
    share: float,
    simulation: bool = False,
) -> str:
    if simulation:
        return TRUTH_SIMULATION_ONLY
    total_i = max(0, int(total))
    top_i = max(0, int(top_count))
    share_f = float(share or 0.0)
    if total_i <= 0 or top_i <= 0:
        return TRUTH_INSUFFICIENT
    if (
        total_i >= MIN_HESITATION_TOTAL
        and top_i >= MIN_DOMINANT_COUNT
        and share_f >= MIN_DOMINANT_SHARE
    ):
        return TRUTH_PRODUCTION_READY
    if total_i >= 3 and top_i >= 2:
        return TRUTH_PRODUCTION_PARTIAL
    return TRUTH_INSUFFICIENT


def classify_communication_truth_v1(
    *,
    no_phone: int,
    simulation: bool = False,
) -> str:
    if simulation:
        return TRUTH_SIMULATION_ONLY
    n = max(0, int(no_phone))
    if n >= 3:
        return TRUTH_PRODUCTION_READY
    if n >= 1:
        return TRUTH_PRODUCTION_PARTIAL
    return TRUTH_INSUFFICIENT


def may_render_on_merchant_home(truth_class: str) -> bool:
    return truth_class in (TRUTH_PRODUCTION_READY, TRUTH_PRODUCTION_PARTIAL)


def summary_marks_simulation(summary: Mapping[str, Any] | None) -> bool:
    if not isinstance(summary, Mapping):
        return False
    for key in ("truth_boundary", "preview_truth", "lab_truth"):
        if str(summary.get(key) or "") == "SIMULATION_TRUTH":
            return True
    if summary.get("simulation") is True:
        return True
    return False


__all__ = [
    "classify_communication_truth_v1",
    "classify_hesitation_truth_v1",
    "may_render_on_merchant_home",
    "summary_marks_simulation",
]
