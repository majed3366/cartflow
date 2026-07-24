# -*- coding: utf-8 -*-
"""Compose Waiting Recovery Work — only when merchant intervention is required."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import (
    DECISION_TYPE_WAITING_RECOVERY,
    SUPPRESS_INSUFFICIENT_EVIDENCE,
    SUPPRESS_NORMAL_STATE,
    new_candidate,
)
from services.decision_composition_engine_v1.priority_v1 import calculate_priority_v1
from services.decision_composition_engine_v1.suppress_v1 import mark_suppressed


def _as_int(v: Any) -> int:
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return 0


def compose_waiting_recovery_v1(
    counters: Mapping[str, Any],
) -> dict[str, Any] | None:
    """
    Waiting carts often mean CartFlow is correctly automating.

    Publish only when waiting volume exceeds no-phone blockers and engaged
    attention suggests human work — otherwise suppress as normal automation.
    """
    slug = str(counters.get("store_slug") or "").strip()
    waiting = _as_int(counters.get("waiting_total"))
    no_phone = _as_int(counters.get("no_phone_total"))
    engaged = _as_int(counters.get("engaged_total"))

    if not counters.get("available"):
        return mark_suppressed(
            new_candidate(
                decision_id="dce:waiting_recovery",
                store_slug=slug,
                decision_type=DECISION_TYPE_WAITING_RECOVERY,
                title="Waiting recovery",
            ),
            SUPPRESS_INSUFFICIENT_EVIDENCE,
        )

    # Pure wait with no engagement / no excess over no-phone → automation OK.
    merchant_needed = engaged > 0 or (waiting > no_phone and waiting >= 5)
    if waiting <= 0 or not merchant_needed:
        return mark_suppressed(
            new_candidate(
                decision_id="dce:waiting_recovery",
                store_slug=slug,
                decision_type=DECISION_TYPE_WAITING_RECOVERY,
                title="Waiting recovery",
                source_truth_types=["merchant_store_cart_counts"],
                evidence_summary=f"waiting={waiting}; engaged={engaged}",
            ),
            SUPPRESS_NORMAL_STATE,
        )

    actionable = max(0, waiting - no_phone) if waiting > no_phone else waiting
    if engaged > 0:
        actionable = max(actionable, engaged)

    decision = "راجع الحالات التي تحتاج تدخلك في مسار الاسترجاع."
    why = (
        f"يوجد {waiting} سلة في حالة انتظار، منها حالات تتطلب متابعة التاجر "
        f"(انتباه/تدخل: {engaged})."
    )
    why_now = (
        "التأخير في الحالات التي تحتاج تدخلاً بشرياً يقلل فرصة إتمام الشراء."
    )
    evidence = (
        f"عدّاد الانتظار={waiting}، عدّاد الانتباه={engaged}، "
        f"سلال بلا رقم={no_phone} (عدّاد السلال المعتمد)."
    )
    ignore = "قد تبقى محادثات أو حالات تحتاج قرارك دون تقدم واضح."
    action = "افتح السلال ذات الانتباه وحدد الخطوة التالية لكل حالة."
    first = "ابدأ بسلال الانتباه (رد/تدخل) ثم راجع ما تبقّى من الانتظار."
    outcome = "تقليل الحالات العالقة التي تحتاج تدخلاً بشرياً."

    automation = engaged == 0
    cand = new_candidate(
        decision_id="dce:waiting_recovery",
        store_slug=slug,
        decision_type=DECISION_TYPE_WAITING_RECOVERY,
        decision_subject_type="store",
        decision_subject_id=slug,
        title=decision,
        merchant_decision=decision,
        why=why,
        why_now=why_now,
        evidence_summary=evidence,
        evidence_refs=[
            "merchant_store_cart_counts.waiting_total",
            "merchant_store_cart_counts.engaged_total",
        ],
        ignore_consequence=ignore,
        recommended_action=action,
        first_step=first,
        expected_outcome=outcome,
        confidence="medium" if engaged == 0 else "high",
        source_truth_types=["merchant_store_cart_counts", "operational_truth"],
        affected_count=actionable,
        view_details_href="#carts",
    )
    score, band, factors = calculate_priority_v1(
        cand, affected_count=actionable, automation_can_resolve=automation
    )
    cand["priority"] = score
    cand["priority_band"] = band
    cand["priority_factors"] = factors
    return cand


__all__ = ["compose_waiting_recovery_v1"]
