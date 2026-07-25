# -*- coding: utf-8 -*-
"""Compose Recoverability Gap as a business decision (not a counter report)."""
from __future__ import annotations

from typing import Any, Mapping

from services.decision_composition_engine_v1.contract_v1 import (
    DECISION_TYPE_RECOVERABILITY_GAP,
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


def compose_recoverability_gap_v1(
    counters: Mapping[str, Any],
) -> dict[str, Any] | None:
    slug = str(counters.get("store_slug") or "").strip()
    n = _as_int(counters.get("no_phone_total"))
    if not counters.get("available"):
        return mark_suppressed(
            new_candidate(
                decision_id="dce:recoverability_gap",
                store_slug=slug,
                decision_type=DECISION_TYPE_RECOVERABILITY_GAP,
                title="Recoverability gap",
            ),
            SUPPRESS_INSUFFICIENT_EVIDENCE,
        )
    if n <= 0:
        return mark_suppressed(
            new_candidate(
                decision_id="dce:recoverability_gap",
                store_slug=slug,
                decision_type=DECISION_TYPE_RECOVERABILITY_GAP,
                title="Recoverability gap",
                source_truth_types=["merchant_store_cart_counts"],
            ),
            SUPPRESS_NORMAL_STATE,
        )

    # Gate 2F — merchant morning-briefing language (rewritten again by Store Executive).
    decision = "راجع تجربة إتمام الشراء ومتابعة العملاء."
    why = (
        "فرص استعادة المبيعات محدودة عندما يتعذّر إكمال متابعة العملاء "
        "بعد ترك السلة."
    )
    why_now = (
        "كل يوم دون معالجة هذا العائق يقلل فرصة تحويل الاهتمام الحالي إلى شراء."
    )
    evidence = (
        "حالة سلال العملاء تشير إلى فرص متابعة مقيدة "
        "بسبب غياب وسيلة تواصل صالحة."
    )
    ignore = (
        "إذا تُركت كما هي، ستستمر فرص الاسترجاع في الضياع ولن تصل رسائل المتابعة."
    )
    action = "راجع كيف يُجمع رقم العميل قبل مغادرة المتجر، ثم عالج الحالات المتأثرة."
    first = "افتح حالات بلا تواصل وحدد أين ينقطع التقاط الرقم في مسار الشراء."
    outcome = "زيادة فرص استعادة المبيعات عبر مسار الاسترجاع."

    cand = new_candidate(
        decision_id="dce:recoverability_gap",
        store_slug=slug,
        decision_type=DECISION_TYPE_RECOVERABILITY_GAP,
        decision_subject_type="store",
        decision_subject_id=slug,
        title=decision,
        merchant_decision=decision,
        why=why,
        why_now=why_now,
        evidence_summary=evidence,
        evidence_refs=["merchant_store_cart_counts.no_phone_total"],
        ignore_consequence=ignore,
        recommended_action=action,
        first_step=first,
        expected_outcome=outcome,
        confidence="high",
        source_truth_types=["merchant_store_cart_counts", "operational_truth"],
        affected_count=n,
        business_domain="recovery",
        view_details_href="#carts?tab=nophone",
    )
    score, band, factors = calculate_priority_v1(
        cand, affected_count=n, automation_can_resolve=False
    )
    cand["priority"] = score
    cand["priority_band"] = band
    cand["priority_factors"] = factors
    return cand


__all__ = ["compose_recoverability_gap_v1"]
