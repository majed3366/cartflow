# -*- coding: utf-8 -*-
"""
Operational health diagnosis v1 — additive platform diagnosis codes.

Composes scheduler ownership, operational control, lifecycle, purchase, and store backlog.
"""
from __future__ import annotations

from typing import Any

DIAG_OPERATIONAL_CONTROL_UNAVAILABLE = "operational_control_unavailable"
DIAG_LIFECYCLE_TRUTH_DISAGREEMENT = "lifecycle_truth_disagreement"
DIAG_PURCHASE_TRUTH_GAP = "purchase_truth_gap"
DIAG_STORE_BACKLOG_DETECTED = "store_backlog_detected"
DIAG_SCHEDULER_STORE_PRESSURE = "scheduler_store_pressure"

SEVERITY_OK = "ok"
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

_SUMMARY_BY_CODE = {
    DIAG_OPERATIONAL_CONTROL_UNAVAILABLE: "Operational control state could not be loaded; gates fail closed.",
    DIAG_LIFECYCLE_TRUTH_DISAGREEMENT: "Lifecycle state disagrees with dashboard bucket/chip in sampled carts.",
    DIAG_PURCHASE_TRUTH_GAP: "Purchase closures exist without durable purchase truth rows.",
    DIAG_STORE_BACKLOG_DETECTED: "One or more stores have due or running scheduler backlog.",
    DIAG_SCHEDULER_STORE_PRESSURE: "A single store dominates platform due-schedule load.",
}


def build_operational_health_diagnosis(
    *,
    operational_control: dict[str, Any] | None = None,
    scheduler_ownership_diagnosis: dict[str, Any] | None = None,
    lifecycle_reconciliation: dict[str, Any] | None = None,
    purchase_truth_gaps: dict[str, Any] | None = None,
    scheduler_store_visibility: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge section diagnoses into one additive platform diagnosis."""
    oc = operational_control if isinstance(operational_control, dict) else {}
    own = scheduler_ownership_diagnosis if isinstance(scheduler_ownership_diagnosis, dict) else {}
    life = lifecycle_reconciliation if isinstance(lifecycle_reconciliation, dict) else {}
    purchase = purchase_truth_gaps if isinstance(purchase_truth_gaps, dict) else {}
    stores = scheduler_store_visibility if isinstance(scheduler_store_visibility, dict) else {}

    codes: list[str] = list(own.get("codes") or [])
    severity = str(own.get("severity") or SEVERITY_INFO)

    availability = oc.get("availability") if isinstance(oc.get("availability"), dict) else {}
    if availability.get("available") is False or oc.get("healthy") is False:
        if DIAG_OPERATIONAL_CONTROL_UNAVAILABLE not in codes:
            codes.append(DIAG_OPERATIONAL_CONTROL_UNAVAILABLE)
        severity = SEVERITY_CRITICAL

    if life.get("disagreements_present"):
        if DIAG_LIFECYCLE_TRUTH_DISAGREEMENT not in codes:
            codes.append(DIAG_LIFECYCLE_TRUTH_DISAGREEMENT)
        if severity in (SEVERITY_INFO, SEVERITY_OK):
            severity = str(life.get("severity") or SEVERITY_WARNING)

    if purchase.get("gaps_detected"):
        if DIAG_PURCHASE_TRUTH_GAP not in codes:
            codes.append(DIAG_PURCHASE_TRUTH_GAP)
        if severity in (SEVERITY_INFO, SEVERITY_OK):
            severity = str(purchase.get("severity") or SEVERITY_WARNING)

    stores_with_due = int(stores.get("stores_with_due") or 0)
    stores_with_backlog = int(stores.get("stores_with_backlog") or 0)
    if stores_with_due > 0 or stores_with_backlog > 0:
        if DIAG_STORE_BACKLOG_DETECTED not in codes:
            codes.append(DIAG_STORE_BACKLOG_DETECTED)
        if severity in (SEVERITY_INFO, SEVERITY_OK):
            severity = SEVERITY_WARNING

    dominant_share = float(stores.get("dominant_store_due_share") or 0.0)
    if dominant_share >= 0.5 and int(stores.get("total_due") or 0) >= 3:
        if DIAG_SCHEDULER_STORE_PRESSURE not in codes:
            codes.append(DIAG_SCHEDULER_STORE_PRESSURE)
        if severity in (SEVERITY_INFO, SEVERITY_OK):
            severity = SEVERITY_WARNING

    if not codes:
        codes.append("ownership_ok")
        severity = SEVERITY_OK

    primary = codes[0]
    summary = _SUMMARY_BY_CODE.get(primary) or str(own.get("summary") or "Operational health requires review.")
    platform_summaries = [
        _SUMMARY_BY_CODE[c]
        for c in codes
        if c in _SUMMARY_BY_CODE and c != primary
    ]
    if platform_summaries:
        summary = f"{summary} Also: {'; '.join(platform_summaries[:2])}."

    return {
        "codes": codes,
        "severity": severity,
        "summary": summary,
        "operational_control_available": availability.get("available", True),
        "lifecycle_disagreement_count": int(life.get("disagreement_count") or 0),
        "purchase_truth_gap_count": int(purchase.get("non_durable_stop_total") or 0),
        "stores_with_due": stores_with_due,
        "dominant_store_slug": stores.get("dominant_store_slug"),
    }


__all__ = [
    "DIAG_LIFECYCLE_TRUTH_DISAGREEMENT",
    "DIAG_OPERATIONAL_CONTROL_UNAVAILABLE",
    "DIAG_PURCHASE_TRUTH_GAP",
    "DIAG_SCHEDULER_STORE_PRESSURE",
    "DIAG_STORE_BACKLOG_DETECTED",
    "build_operational_health_diagnosis",
]
