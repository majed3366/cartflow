# -*- coding: utf-8 -*-
"""
Evidence Gap Contract V1 — internal engineering artifact only.

Never publish to merchants / Home / Workspace UI.
"""
from __future__ import annotations

from typing import Any, Mapping

EVIDENCE_EXPANSION_VERSION_V1 = "evidence_expansion_v1"
EVIDENCE_GAP_SCHEMA_V1 = "evidence_gap_v1"

GAP_STATUS_OPEN = "open"
GAP_STATUS_PARTIALLY_FILLED = "partially_filled"
GAP_STATUS_RESOLVED = "resolved"
GAP_STATUS_SUPERSEDED = "superseded"
GAP_STATUS_SUPPRESSED = "suppressed"

GAP_STATUSES = frozenset(
    {
        GAP_STATUS_OPEN,
        GAP_STATUS_PARTIALLY_FILLED,
        GAP_STATUS_RESOLVED,
        GAP_STATUS_SUPERSEDED,
        GAP_STATUS_SUPPRESSED,
    }
)

# Terminal statuses must not silently reopen to open without reopen_reason.
TERMINAL_GAP_STATUSES = frozenset(
    {
        GAP_STATUS_RESOLVED,
        GAP_STATUS_SUPERSEDED,
        GAP_STATUS_SUPPRESSED,
    }
)

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"
PRIORITIES = frozenset({PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW})


def empty_evidence_gap_v1(
    *,
    gap_id: str,
    store_slug: str,
    diagnostic_family: str,
    diagnostic_id: str = "",
) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_GAP_SCHEMA_V1,
        "gap_id": gap_id,
        "store_slug": store_slug,
        "diagnostic_id": diagnostic_id,
        "diagnostic_family": diagnostic_family,
        "diagnosis_status": "insufficient_evidence",
        "competing_causes": [],
        "evidence_available": [],
        "evidence_missing": [],
        "possible_future_observables": [],
        "priority": PRIORITY_MEDIUM,
        "gap_status": GAP_STATUS_OPEN,
        "observation_ar": "",
        "rationale": (
            "What evidence is missing that would allow this diagnosis "
            "to become confident?"
        ),
        "merchant_safe": False,
        "internal_only": True,
        "generated_at": None,
        "evidence_expansion_version": EVIDENCE_EXPANSION_VERSION_V1,
    }


def validate_evidence_gap_v1(raw: Mapping[str, Any] | None) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(raw, Mapping):
        return False, ["not_a_mapping"]
    if raw.get("schema") != EVIDENCE_GAP_SCHEMA_V1:
        errors.append("schema")
    if not str(raw.get("diagnostic_family") or "").strip():
        errors.append("diagnostic_family")
    if str(raw.get("gap_status") or "") not in GAP_STATUSES:
        errors.append("gap_status")
    if str(raw.get("priority") or "") not in PRIORITIES:
        errors.append("priority")
    if not list(raw.get("evidence_missing") or []):
        errors.append("evidence_missing_required")
    if raw.get("merchant_safe") is True:
        errors.append("must_not_be_merchant_safe")
    if raw.get("internal_only") is not True:
        errors.append("must_be_internal_only")
    return (len(errors) == 0), errors


def resolve_gap_status_transition_v1(
    *,
    existing_status: str,
    incoming_status: str,
    reopen_reason: str = "",
) -> tuple[str, str]:
    """
    Governed lifecycle transition.

    Returns (effective_status, transition_note).
    Terminal → open requires non-empty reopen_reason; otherwise terminal is preserved.
    """
    existing = str(existing_status or "").strip() or GAP_STATUS_OPEN
    incoming = str(incoming_status or "").strip() or GAP_STATUS_OPEN
    reason = str(reopen_reason or "").strip()
    if existing in TERMINAL_GAP_STATUSES and incoming == GAP_STATUS_OPEN and not reason:
        return existing, "terminal_preserved_no_reopen_reason"
    if existing in TERMINAL_GAP_STATUSES and incoming == GAP_STATUS_OPEN and reason:
        return GAP_STATUS_OPEN, "reopened_with_reason"
    if incoming not in GAP_STATUSES:
        return existing if existing in GAP_STATUSES else GAP_STATUS_OPEN, "invalid_incoming_preserved"
    return incoming, "applied"


__all__ = [
    "EVIDENCE_EXPANSION_VERSION_V1",
    "EVIDENCE_GAP_SCHEMA_V1",
    "GAP_STATUS_OPEN",
    "GAP_STATUS_PARTIALLY_FILLED",
    "GAP_STATUS_RESOLVED",
    "GAP_STATUS_SUPERSEDED",
    "GAP_STATUS_SUPPRESSED",
    "GAP_STATUSES",
    "PRIORITIES",
    "PRIORITY_HIGH",
    "PRIORITY_LOW",
    "PRIORITY_MEDIUM",
    "TERMINAL_GAP_STATUSES",
    "empty_evidence_gap_v1",
    "resolve_gap_status_transition_v1",
    "validate_evidence_gap_v1",
]
