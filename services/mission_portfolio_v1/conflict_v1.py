# -*- coding: utf-8 -*-
"""Mission Portfolio V1 — conflict evaluation (deterministic, no LLM)."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.mission_portfolio_v1.contract_v1 import (
    CONFLICT_CAPACITY_ONLY,
    CONFLICT_DUPLICATE_INTENT,
    CONFLICT_MEASUREMENT_CONTAMINATION,
    CONFLICT_MUTUALLY_EXCLUSIVE,
    CONFLICT_SAFE_TO_COEXIST,
    MEASUREMENT_CONTAMINATION_PAIRS,
    MUTUALLY_EXCLUSIVE_PAIRS,
    REASON_CAPACITY_OCCUPIED,
    REASON_CONFLICTS_WITH_ACTIVE,
    REASON_DUPLICATE_INTENT,
    REASON_LOWER_PRIORITY_RECHECK,
    REASON_MEASUREMENT_CONTAMINATION,
    REASON_MISSING_CONFLICT_RULE,
    REASON_SAFE_SECONDARY,
    REASON_UNKNOWN_FAMILY,
    SLOT_PHASES,
)


def _fam(card: Mapping[str, Any] | None) -> str:
    if not isinstance(card, Mapping):
        return ""
    return str(card.get("family") or "").strip()


def _phase(card: Mapping[str, Any] | None) -> Optional[str]:
    if not isinstance(card, Mapping):
        return None
    p = card.get("cdc_phase")
    if p:
        return str(p)
    c = card.get("commitment")
    if isinstance(c, Mapping) and c.get("phase"):
        return str(c.get("phase"))
    return None


def evaluate_conflict_v1(
    *,
    active: Mapping[str, Any] | None,
    candidate: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """
    Classify relationship between active slot owner and a candidate.

    Fail-safe: unknown / missing rules → defer (never allow unsafe concurrent exec).
    """
    if not isinstance(candidate, Mapping):
        return {
            "conflict_type": CONFLICT_CAPACITY_ONLY,
            "reason_code": REASON_UNKNOWN_FAMILY,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    cand_fam = _fam(candidate)
    if not cand_fam:
        return {
            "conflict_type": CONFLICT_MUTUALLY_EXCLUSIVE,
            "reason_code": REASON_UNKNOWN_FAMILY,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    if not isinstance(active, Mapping):
        return {
            "conflict_type": CONFLICT_SAFE_TO_COEXIST,
            "reason_code": REASON_SAFE_SECONDARY,
            "may_execute": True,
            "may_surface_secondary": True,
        }

    act_fam = _fam(active)
    act_phase = _phase(active)
    if not act_fam:
        return {
            "conflict_type": CONFLICT_CAPACITY_ONLY,
            "reason_code": REASON_MISSING_CONFLICT_RULE,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    # Same opportunity identity — not a conflict
    a_oid = str(active.get("opportunity_id") or "")
    c_oid = str(candidate.get("opportunity_id") or "")
    if a_oid and c_oid and a_oid == c_oid:
        return {
            "conflict_type": CONFLICT_SAFE_TO_COEXIST,
            "reason_code": REASON_SAFE_SECONDARY,
            "may_execute": True,
            "may_surface_secondary": False,
        }

    if cand_fam == act_fam:
        return {
            "conflict_type": CONFLICT_DUPLICATE_INTENT,
            "reason_code": REASON_DUPLICATE_INTENT,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    pair = (act_fam, cand_fam)
    if pair in MUTUALLY_EXCLUSIVE_PAIRS:
        return {
            "conflict_type": CONFLICT_MUTUALLY_EXCLUSIVE,
            "reason_code": REASON_CONFLICTS_WITH_ACTIVE,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    if act_phase == "UNDER_MEASUREMENT" and pair in MEASUREMENT_CONTAMINATION_PAIRS:
        return {
            "conflict_type": CONFLICT_MEASUREMENT_CONTAMINATION,
            "reason_code": REASON_MEASUREMENT_CONTAMINATION,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    if act_phase in SLOT_PHASES:
        reason = REASON_CAPACITY_OCCUPIED
        if act_phase == "RECHECK_DUE":
            reason = REASON_LOWER_PRIORITY_RECHECK
        return {
            "conflict_type": CONFLICT_CAPACITY_ONLY,
            "reason_code": reason,
            "may_execute": False,
            "may_surface_secondary": False,
        }

    # Active without slot phase (should not happen) — fail-safe defer
    return {
        "conflict_type": CONFLICT_CAPACITY_ONLY,
        "reason_code": REASON_MISSING_CONFLICT_RULE,
        "may_execute": False,
        "may_surface_secondary": False,
    }


__all__ = ["evaluate_conflict_v1"]
