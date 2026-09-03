# -*- coding: utf-8 -*-
"""Explainable opportunity priority — no invented revenue forecasts."""
from __future__ import annotations

from typing import Any

from services.revenue_intelligence_model_v1.contracts_v1 import (
    TIER_COMPLETED,
    TIER_DECIDE_NOW,
    TIER_IMPORTANT,
    TIER_INSUFFICIENT,
    TIER_IN_PROGRESS,
    TIER_LABEL_AR,
    TIER_MEASURING,
    TIER_MONITOR,
)

# Scenario commercial significance weights (relative ordering aid only — not forecasts)
_SCENARIO_SIGNIFICANCE = {
    "A_discovery": 96,  # under-reached + strong convert — classic top commercial attention
    "D_discount_destroys_value": 94,  # active value destruction
    "B_high_interest_low_conversion": 90,
    "C_price_sensitive": 78,
    "F_channel_quality": 74,
    "G_retention": 66,
    "E_bundle_cross_sell": 64,
    "H_insufficient_evidence": 0,
}


def _clone_suffix(oid: str) -> bool:
    return oid.endswith(("_measuring", "_active", "_fail")) or "measurement_won" in oid


def _factor_evidence(m: dict[str, Any]) -> tuple[int, str]:
    if m.get("status") == "insufficient_evidence" or m.get("confidence") == "insufficient":
        return 0, "الدليل غير كافٍ لاتخاذ قرار تجاري."
    if m.get("evidence_ar") or m.get("evidence"):
        conf = str(m.get("confidence") or "")
        if conf == "high":
            return 95, "الدليل واضح وكافٍ للحكم."
        if conf == "medium":
            return 80, "الدليل كافٍ لتجربة محدودة قابلة للقياس."
        return 55, "الدليل موجود لكن بثقة محدودة."
    return 0, "لا يوجد دليل معروض."


def _factor_revenue_exposure(m: dict[str, Any], world: dict[str, Any] | None) -> tuple[int, str]:
    scope = m.get("scope") or {}
    pid = scope.get("id") if scope.get("type") == "product" else None
    if scope.get("type") == "product_pair":
        products = scope.get("products") or []
        pid = products[0] if products else None
    if scope.get("type") == "customer_segment":
        pid = scope.get("first_product")
    aggs = (world or {}).get("aggregates") or {}
    if pid and pid in aggs:
        rev = float(aggs[pid].get("revenue") or 0)
        # Relative band vs max revenue in store (not a forecast)
        max_rev = max((float(a.get("revenue") or 0) for a in aggs.values()), default=1.0) or 1.0
        share = rev / max_rev
        if share >= 0.55:
            return 85, "المنتج/الشريحة تساهم بإيراد ملموس في المتجر حاليًا."
        if share >= 0.25:
            return 70, "هناك إيراد قائم يستحق الحماية أو التوسيع."
        if share >= 0.08:
            return 55, "الإيراد الحالي محدود لكن التحويل عند الوصول يشير إلى إمكانية توسع."
        return 40, "الإيراد الحالي صغير؛ الأولوية تأتي من جودة التحويل لا من الحجم وحده."
    return 50, "نطاق الإيراد غير مربوط بمنتج واحد — تُقدَّر الأهمية من نوع الفرصة."


def _factor_actionability(m: dict[str, Any]) -> tuple[int, str]:
    sid = str(m.get("scenario_id") or "")
    if sid == "H_insufficient_evidence":
        return 0, "لا إجراء قابل للتنفيذ قبل اكتمال الدليل."
    if sid in ("A_discovery", "E_bundle_cross_sell", "G_retention"):
        return 90, "الإجراء واضح ومنخفض التعقيد نسبيًا (إبراز/اقتراح موجّه)."
    if sid in ("B_high_interest_low_conversion", "C_price_sensitive", "F_channel_quality"):
        return 75, "الإجراء محدود بزمن وشروط إيقاف — قابل للتنفيذ كتجربة."
    if sid == "D_discount_destroys_value":
        return 85, "الإجراء مباشر: إيقاف أو إعادة تصميم عرض جارٍ."
    return 60, "إجراء تجاري ممكن ضمن حدود الدليل."


def _factor_urgency(m: dict[str, Any]) -> tuple[int, str]:
    sid = str(m.get("scenario_id") or "")
    st = m.get("status")
    if sid == "D_discount_destroys_value" and st == "proposed":
        return 92, "العرض قد يستمر في إضعاف القيمة طالما لم يُوقف."
    if st == "proposed" and sid == "A_discovery":
        return 80, "كل يوم باكتشاف ضعيف يفوّت مشتريات كان التحويل يدعمها."
    if st in ("measuring", "active"):
        return 40, "القرار التنفيذي بدأ؛ الأولوية الآن للمتابعة لا لقرار جديد."
    if st == "won":
        return 20, "النتيجة قيست — المتابعة فقط."
    return 65, "القرار مطلوب قبل ضياع نافذة التجربة."


def _factor_reversibility(m: dict[str, Any]) -> tuple[int, str]:
    sid = str(m.get("scenario_id") or "")
    if sid in ("A_discovery", "E_bundle_cross_sell", "G_retention"):
        return 90, "التجربة قابلة للعكس بسرعة (إبراز/اقتراح يمكن إيقافه)."
    if sid in ("B_high_interest_low_conversion", "F_channel_quality"):
        return 80, "تغيير محدود وقابل للتراجع دون التزام سعر دائم."
    if sid == "C_price_sensitive":
        return 55, "تجربة عرض لها أثر سعري — محددة بزمن وإيقاف."
    if sid == "D_discount_destroys_value":
        return 70, "إيقاف الخصم يعيد الوضع السابق — مخاطرة منخفضة مقابل الاستمرار."
    return 50, "المخاطر محدودة بشرط القياس والإيقاف."


def _factor_decision_required(m: dict[str, Any]) -> tuple[int, str]:
    st = m.get("status")
    if st == "proposed":
        return 95, "تحتاج قرار التاجر للبدء."
    if st == "insufficient_evidence":
        return 10, "لا قرار تجاري الآن — انتظار دليل."
    if st in ("active", "measuring"):
        return 30, "القرار اتُّخذ؛ المطلوب مراقبة."
    if st == "won":
        return 15, "لا قرار جديد مطلوب."
    return 40, "قرار محدود."


def _factor_measurement_ready(m: dict[str, Any]) -> tuple[int, str]:
    if m.get("measure_ar") or m.get("measurement_plan"):
        if m.get("recheck_ar") or m.get("recheck_condition"):
            return 90, "خطة قياس وشرط إعادة تقييم جاهزان."
        return 60, "يوجد قياس لكن شرط الإعادة غير مكتمل."
    return 0, "لا خطة قياس — لا تُرفع الأولوية."


def explain_priority_ar(m: dict[str, Any], *, factors: dict[str, Any]) -> str:
    """Merchant-readable WHY THIS IS PRIORITIZED — never 'score=N'."""
    sid = str(m.get("scenario_id") or "")
    st = m.get("status")
    if st == "insufficient_evidence" or sid == "H_insufficient_evidence":
        return (
            "هذه الحالة ليست أولوية قرار تجاري: الدليل غير كافٍ. "
            "CartFlow يؤجّل أي حركة حتى تكتمل العتبات."
        )
    if st == "won":
        return (
            "أُنجزت بالقياس. تظهر ضمن المكتمل لأن النتيجة رُصدت على الإيراد والاكتشاف — "
            "وليست فرصة قرار جديدة."
        )
    if st == "measuring":
        return "أولويتها الآن المتابعة: التجربة بدأت والقياس جارٍ بلا ادّعاء نتيجة مبكرة."
    if st == "active":
        return "قيد التنفيذ: القرار اتُّخذ والتجربة نشطة — الأولوية للالتزام بخطة القياس."

    # Proposed — compose from factors (scenario-specific narrative)
    if sid == "A_discovery":
        return (
            "هذه الفرصة أولوية الآن لأن المنتج يحقق شراءً جيدًا عند الوصول إليه، "
            "لكن وصوله أقل بكثير من المنتجات المشابهة داخل متجرك، "
            "والتجربة المقترحة منخفضة المخاطر وقابلة للقياس."
        )
    if sid == "D_discount_destroys_value":
        return (
            "أولوية عاجلة لأن العرض الجاري يرفع التحويل بينما يضعف الاقتصاد المحاكى؛ "
            "الاستمرار يكلّف أكثر من إيقاف قابل للعكس."
        )
    if sid == "B_high_interest_low_conversion":
        return (
            "أولوية لأن الاهتمام مرتفع والتحويل إلى شراء ضعيف مع دليل شحن غالب؛ "
            "التشخيص قبل أي خصم يقلل مخاطرة قرار خاطئ."
        )
    if sid == "C_price_sensitive":
        return (
            "مهمة لأن تردد السعر متكرر بحجم كافٍ لتجربة عرض محدودة بزمن وإيقاف — "
            "بدون اختراع رفع إيراد مسبق."
        )
    if sid == "F_channel_quality":
        return (
            "مهمة لأن جودة الزيارات تختلف بين قناتين لنفس المنتج بحجم كافٍ؛ "
            "التجربة محدودة وليست توصية عامة بقناة."
        )
    if sid == "G_retention":
        return (
            "مهمة لأن مشترين حاليين لديهم ميل أعلى لشراء منتج مكمل لاحقًا؛ "
            "هذا احتفاظ موجّه وليس اكتسابًا."
        )
    if sid == "E_bundle_cross_sell":
        return (
            "مهمة لأن علاقة الشراء المشتركة مثبتة في السلة؛ "
            "اقتراح متقاطع محدود المخاطر وقابل للقياس."
        )
    # fallback from factor blurbs
    bits = [
        factors["evidence"][1],
        factors["actionability"][1],
        factors["measurement"][1],
    ]
    return " ".join(bits)


def score_mission_internal_v1(m: dict[str, Any], world: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Bounded internal ordering aid — not merchant-facing.
    Does NOT invent revenue uplift forecasts.
    """
    oid = str(m.get("opportunity_id") or "")
    st = m.get("status")
    sid = str(m.get("scenario_id") or "")

    ev = _factor_evidence(m)
    rev = _factor_revenue_exposure(m, world)
    act = _factor_actionability(m)
    urg = _factor_urgency(m)
    revr = _factor_reversibility(m)
    dec = _factor_decision_required(m)
    meas = _factor_measurement_ready(m)
    factors = {
        "evidence": ev,
        "revenue_exposure": rev,
        "actionability": act,
        "urgency": urg,
        "reversibility": revr,
        "decision_required": dec,
        "measurement": meas,
    }

    if st == "insufficient_evidence" or sid == "H_insufficient_evidence":
        internal = 0
        tier = TIER_INSUFFICIENT
    elif st == "won" or st in ("lost", "inconclusive"):
        internal = 15
        tier = TIER_COMPLETED
    elif st == "measuring":
        internal = 35
        tier = TIER_MEASURING
    elif st == "active":
        internal = 40
        tier = TIER_IN_PROGRESS
    else:
        # proposed: weighted factors + scenario significance (ordering only)
        sig = _SCENARIO_SIGNIFICANCE.get(sid, 50)
        # Evidence is a hard gate — zero evidence => cannot be decide_now
        if ev[0] < 50 or meas[0] < 40:
            internal = max(10, int(0.4 * ev[0] + 0.2 * sig))
            tier = TIER_MONITOR
        else:
            internal = int(
                0.20 * ev[0]
                + 0.12 * rev[0]
                + 0.14 * act[0]
                + 0.16 * urg[0]
                + 0.10 * revr[0]
                + 0.10 * dec[0]
                + 0.10 * meas[0]
                + 0.18 * sig
            )
            # clones shouldn't compete as decide_now
            if _clone_suffix(oid):
                internal = min(internal, 45)
            tier = TIER_DECIDE_NOW if internal >= 70 else TIER_IMPORTANT if internal >= 55 else TIER_MONITOR

    why = explain_priority_ar(m, factors=factors)
    return {
        "internal_priority_score": internal,  # never primary merchant copy
        "priority_tier": tier,
        "priority_tier_ar": TIER_LABEL_AR[tier],
        "why_prioritized_ar": why,
        "priority_factors": {k: {"band": v[0], "note_ar": v[1]} for k, v in factors.items()},
        "forecast_used": False,
    }


def assign_tiers_and_sort_v1(
    missions: list[dict[str, Any]],
    world: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for m in missions:
        row = dict(m)
        pri = score_mission_internal_v1(row, world)
        row.update(pri)
        # After scoring all proposed, refine decide_now vs important by rank later
        enriched.append(row)
    # Sort proposed by internal score desc for ordering
    proposed = [m for m in enriched if m.get("status") == "proposed"]
    proposed_sorted = sorted(
        proposed,
        key=lambda x: int(x.get("internal_priority_score") or 0),
        reverse=True,
    )
    # Top proposed (non-clone) get decide_now; rest important or monitor as scored
    rank = 0
    for m in proposed_sorted:
        oid = str(m.get("opportunity_id") or "")
        if _clone_suffix(oid):
            continue
        rank += 1
        m["priority_rank_among_decisions"] = rank
        if rank == 1:
            m["priority_tier"] = TIER_DECIDE_NOW
            m["priority_tier_ar"] = TIER_LABEL_AR[TIER_DECIDE_NOW]
        elif rank <= 4:
            # still "تحتاج قرارك" list but tier label فرصة مهمة for home secondary
            m["priority_tier"] = TIER_IMPORTANT if rank > 1 else TIER_DECIDE_NOW
            if rank > 1:
                m["priority_tier"] = TIER_IMPORTANT
                m["priority_tier_ar"] = TIER_LABEL_AR[TIER_IMPORTANT]
        else:
            m["priority_tier"] = TIER_MONITOR
            m["priority_tier_ar"] = TIER_LABEL_AR[TIER_MONITOR]
    # Ensure #1 keeps decide_now
    if proposed_sorted:
        top = next(
            (m for m in proposed_sorted if not _clone_suffix(str(m.get("opportunity_id") or ""))),
            None,
        )
        if top:
            top["priority_tier"] = TIER_DECIDE_NOW
            top["priority_tier_ar"] = TIER_LABEL_AR[TIER_DECIDE_NOW]
            top["priority_rank_among_decisions"] = 1
    return enriched


__all__ = ["assign_tiers_and_sort_v1", "score_mission_internal_v1"]
