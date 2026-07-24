# -*- coding: utf-8 -*-
"""Publication and suppression registry helpers — no silent suppression."""
from __future__ import annotations

from typing import Any

from services.decision_composition_engine_v1.contract_v1 import (
    validate_publish_contract,
)


def mark_suppressed(candidate: dict[str, Any], reason: str) -> dict[str, Any]:
    candidate["published"] = False
    candidate["suppressed"] = True
    candidate["suppression_reason"] = str(reason or "unknown")
    return candidate


def mark_published(candidate: dict[str, Any]) -> dict[str, Any]:
    candidate["published"] = True
    candidate["suppressed"] = False
    candidate["suppression_reason"] = ""
    return candidate


def apply_contract_gate(candidate: dict[str, Any]) -> dict[str, Any]:
    ok, reason = validate_publish_contract(candidate)
    if not ok:
        return mark_suppressed(candidate, reason)
    return mark_published(candidate)


def dedupe_key(candidate: dict[str, Any]) -> str:
    return "|".join(
        [
            str(candidate.get("decision_type") or ""),
            str(candidate.get("decision_subject_type") or ""),
            str(candidate.get("decision_subject_id") or ""),
            str(candidate.get("store_slug") or ""),
        ]
    )


__all__ = [
    "apply_contract_gate",
    "dedupe_key",
    "mark_published",
    "mark_suppressed",
]
