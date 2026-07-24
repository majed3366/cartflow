# -*- coding: utf-8 -*-
"""Compose Recoverability Gap decisions from operational truth (not raw counters)."""
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

    decision = "حسّن قدرة المتجر على جمع أرقام العملاء القابلين للاسترجاع."
    why = (
        f"{n} سلة نشطة لا يمكن بدء استرجاعها لأن رقم العميل غير متوفر، "
        "فيتوقف مسار التواصل قبل أن يبدأ."
    )
    why_now = (
        f"كل يوم تبقى فيه هذه السلال بلا رقم يقلل فرصة استعادتها — "
        f"يوجد الآن {n} سلة محظورة عن المتابعة."
    )
    evidence = (
        f"{n} سلة نشطة بلا رقم تواصل صالح وفق عدّاد السلال المعتمد للمتجر."
    )
    ignore = (
        "إذا تُركت كما هي، ستظل هذه السلال خارج مسار الاسترجاع ولن تصلها رسائل متابعة."
    )
    action = "راجع كيف يُجمع رقم العميل قبل مغادرة المتجر، ثم عالج السلال المتأثرة."
    first = "افتح سلال بلا رقم تواصل وحدد أين ينقطع التقاط الرقم في مسار الشراء."
    outcome = "زيادة عدد السلال القابلة للدخول في مسار الاسترجاع."

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
