# -*- coding: utf-8 -*-
"""Recommendation Mapping Registry V1 — recommendations derive only from diagnosis."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.diagnostic_reasoning_v1.cause_registry_v1 import causes_for_family_v1
from services.diagnostic_reasoning_v1.contract_v1 import (
    AR_REC_CONTINUE,
    DIAGNOSIS_STATUS_CONFLICTING,
    DIAGNOSIS_STATUS_INSUFFICIENT,
    DIAGNOSIS_STATUS_SUPPRESSED,
)


def recommendation_for_diagnosis_v1(
    family: str,
    *,
    selected_diagnosis: Optional[str],
    diagnosis_status: str,
) -> dict[str, Any]:
    status = str(diagnosis_status or "")
    if status in {
        DIAGNOSIS_STATUS_INSUFFICIENT,
        DIAGNOSIS_STATUS_CONFLICTING,
        DIAGNOSIS_STATUS_SUPPRESSED,
    }:
        return {
            "cause_key": "insufficient_evidence",
            "text_ar": AR_REC_CONTINUE,
        }
    key = str(selected_diagnosis or "").strip()
    if not key or key == "insufficient_evidence":
        return {
            "cause_key": "insufficient_evidence",
            "text_ar": AR_REC_CONTINUE,
        }
    for cause in causes_for_family_v1(family):
        if str(cause.get("cause_key")) == key:
            return {
                "cause_key": key,
                "text_ar": str(cause.get("safe_recommendation_ar") or AR_REC_CONTINUE),
            }
    # Unknown cause — never invent a recommendation.
    return {
        "cause_key": "insufficient_evidence",
        "text_ar": AR_REC_CONTINUE,
    }


def assert_recommendation_derives_from_diagnosis_v1(
    diagnosis: Mapping[str, Any],
) -> bool:
    status = str(diagnosis.get("diagnosis_status") or "")
    selected = diagnosis.get("selected_diagnosis")
    rec = (
        diagnosis.get("recommendation")
        if isinstance(diagnosis.get("recommendation"), Mapping)
        else {}
    )
    rec_cause = str(rec.get("cause_key") or "")
    if status in {
        DIAGNOSIS_STATUS_INSUFFICIENT,
        DIAGNOSIS_STATUS_CONFLICTING,
        DIAGNOSIS_STATUS_SUPPRESSED,
    }:
        return rec_cause in ("", "insufficient_evidence")
    if not selected:
        return False
    return rec_cause == str(selected)


__all__ = [
    "assert_recommendation_derives_from_diagnosis_v1",
    "recommendation_for_diagnosis_v1",
]
