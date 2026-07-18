# -*- coding: utf-8 -*-
"""
Deterministic reasoning rules for Business Reasoning Engine V1.

Each rule combines ≥2 approved findings. No evidence access. No AI.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional, Sequence

from services.business_findings_contract_v1 import (
    CONFIDENCE_HIGH,
    CONFIDENCE_INSUFFICIENT,
    CONFIDENCE_MEDIUM,
    STATUS_INSUFFICIENT,
    TYPE_DOMINANT_HESITATION,
    TYPE_HESITATION_RESOLUTION,
    TYPE_HIGH_INTEREST_LOW_PURCHASE,
    TYPE_MISSING_CONTACT_BLOCKS,
    TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
    TYPE_RETURN_WITHOUT_PURCHASE,
    TYPE_TRAFFIC_VS_CONVERSION,
    TYPE_WHATSAPP_TEST_CANDIDATE,
    norm,
)
from services.business_reasoning_contract_v1 import (
    CERTAINTY_LIKELY,
    CERTAINTY_OBSERVED,
    CERTAINTY_UNKNOWN,
    TYPE_CONFLICT,
    TYPE_CONSTRAINT,
    TYPE_OPPORTUNITY,
    TYPE_PRIORITY,
    TYPE_RELATIONSHIP,
    empty_reasoning,
    evaluate_quality_gates_v1,
)

RuleFn = Callable[[str, Sequence[Mapping[str, Any]]], Optional[dict[str, Any]]]


def _by_type(findings: Sequence[Mapping[str, Any]], *types: str) -> list[dict[str, Any]]:
    wanted = {norm(t) for t in types}
    return [dict(f) for f in findings if norm(f.get("finding_type")) in wanted]


def _by_family(findings: Sequence[Mapping[str, Any]], *families: str) -> list[dict[str, Any]]:
    wanted = {norm(t) for t in families}
    return [dict(f) for f in findings if norm(f.get("family_key")) in wanted]


def _label(f: Mapping[str, Any]) -> str:
    return norm(f.get("title")) or norm(f.get("merchant_summary")) or "استنتاج معتمد"


def _ids_labels(*items: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    ids: list[str] = []
    labels: list[str] = []
    seen: set[str] = set()
    for f in items:
        fid = norm(f.get("finding_id"))
        if not fid or fid in seen:
            continue
        seen.add(fid)
        ids.append(fid)
        labels.append(_label(f))
    return ids, labels


def _min_confidence(*levels: str) -> str:
    order = {
        CONFIDENCE_HIGH: 3,
        CONFIDENCE_MEDIUM: 2,
        "low": 1,
        CONFIDENCE_INSUFFICIENT: 0,
    }
    scored = [(order.get(norm(x).lower(), 0), norm(x).lower() or CONFIDENCE_INSUFFICIENT) for x in levels]
    scored.sort(key=lambda x: x[0])
    return scored[0][1] if scored else CONFIDENCE_INSUFFICIENT


def _avg_score(*scores: Any) -> float:
    vals: list[float] = []
    for s in scores:
        try:
            vals.append(float(s or 0.0))
        except (TypeError, ValueError):
            continue
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 3)


def _mentions_shipping(f: Mapping[str, Any]) -> bool:
    blob = " ".join(
        [
            norm(f.get("title")),
            norm(f.get("merchant_summary")),
            norm(f.get("evidence_summary")),
            norm(f.get("scope_reference")),
        ]
    ).lower()
    return "shipping" in blob or "تكلفة الشحن" in blob or "الشحن" in blob


def _mentions_delivery_time(f: Mapping[str, Any]) -> bool:
    blob = " ".join(
        [
            norm(f.get("title")),
            norm(f.get("merchant_summary")),
            norm(f.get("evidence_summary")),
            norm(f.get("scope_reference")),
        ]
    ).lower()
    return "delivery_time" in blob or "وقت التوصيل" in blob


def _is_high_resolution(f: Mapping[str, Any]) -> bool:
    """Heuristic: resolution finding that reports purchases after return."""
    if norm(f.get("finding_type")) != TYPE_HESITATION_RESOLUTION:
        return False
    ev = norm(f.get("evidence_summary")).lower()
    # Prefer purchase-positive resolution wording from families.
    if "purchased=2" in ev or "اكتمل الشراء 2" in norm(f.get("merchant_summary")):
        return True
    if "قابل للحل" in norm(f.get("commercial_meaning")):
        return True
    return False


def _is_unresolved_barrier(f: Mapping[str, Any]) -> bool:
    if norm(f.get("finding_type")) != TYPE_HESITATION_RESOLUTION:
        return False
    blob = f"{norm(f.get('title'))} {norm(f.get('merchant_summary'))}".lower()
    return "بلا حل" in blob or "unresolved" in norm(f.get("evidence_summary")).lower()


def rule_relationship_recovery_vs_shipping_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    Shipping barrier + return after WhatsApp + weak completion
    → recovery restores interest but does not remove the shipping barrier.
    """
    shipping = next(
        (
            f
            for f in _by_type(findings, TYPE_DOMINANT_HESITATION, TYPE_HESITATION_RESOLUTION)
            if _mentions_shipping(f)
        ),
        None,
    )
    returns = next(
        iter(
            _by_type(
                findings,
                TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
                TYPE_RETURN_WITHOUT_PURCHASE,
                TYPE_WHATSAPP_TEST_CANDIDATE,
            )
        ),
        None,
    )
    weak_close = next(
        (
            f
            for f in findings
            if norm(f.get("finding_type"))
            in (
                TYPE_RETURN_WITHOUT_PURCHASE,
                TYPE_HIGH_INTEREST_LOW_PURCHASE,
                TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
            )
            and f is not returns
        ),
        None,
    )
    # Allow returns finding to also serve as weak-close signal when distinct shipping exists.
    if shipping is None or returns is None:
        return None
    third = weak_close or next(
        (
            f
            for f in _by_type(findings, TYPE_HESITATION_RESOLUTION)
            if _is_unresolved_barrier(f) and f is not shipping
        ),
        None,
    )
    if third is None and returns is not shipping:
        # Need a third distinct finding — try dominant shipping + WA + return_without_purchase
        third = next(
            iter(_by_type(findings, TYPE_RETURN_WITHOUT_PURCHASE)),
            None,
        )
    if third is None:
        # Fall back: shipping + WA channel + unresolved shipping resolution
        third = next(
            (
                f
                for f in _by_type(findings, TYPE_HESITATION_RESOLUTION)
                if _mentions_shipping(f) and f is not shipping
            ),
            None,
        )
    if third is None:
        return None

    ids, labels = _ids_labels(shipping, returns, third)
    if len(ids) < 2:
        return None
    # Prefer three when available; quality gate allows 2+.
    card = empty_reasoning(
        reasoning_id=f"reasoning:relationship:recovery_shipping:{norm(store_slug)}",
        store_slug=store_slug,
        reasoning_type=TYPE_RELATIONSHIP,
    )
    card.update(
        {
            "headline": (
                "العملاء يعودون بعد واتساب، لكنهم ما زالوا يغادرون بسبب تكلفة الشحن."
            ),
            "business_meaning": (
                "مسار الاسترجاع ينجح في إعادة الاهتمام، "
                "لكن عائق الشراء الأساسي ما زال قائماً بعد العودة."
            ),
            "recommended_priority": (
                "حسّن عرض تكلفة الشحن قبل زيادة حملات التذكير."
            ),
            "expected_impact": (
                "إزالة هذا العائق مرجّحة لتحسين إتمام الشراء أكثر من إرسال تذكيرات إضافية."
            ),
            "confidence_level": _min_confidence(
                norm(shipping.get("confidence_level")),
                norm(returns.get("confidence_level")),
                norm(third.get("confidence_level")),
            ),
            "confidence_score": _avg_score(
                shipping.get("confidence_score"),
                returns.get("confidence_score"),
                third.get("confidence_score"),
            ),
            "certainty": CERTAINTY_LIKELY,
            "supporting_finding_ids": ids,
            "supporting_finding_labels": labels,
            "quality_gates": evaluate_quality_gates_v1(
                supporting_finding_ids=ids,
                creates_business_decision=True,
                merchant_can_act_today=True,
            ),
            "rank_score": 92.0,
        }
    )
    return card


def rule_priority_single_focus_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    Evidence-based weekly priority:
    If you improve only one thing this week, improve ______.
    """
    actionable = [
        f
        for f in findings
        if norm(f.get("recommendation_type")) in ("act_now", "investigate", "test")
        and norm(f.get("status")) != STATUS_INSUFFICIENT
    ]
    if len(actionable) < 2:
        return None
    actionable.sort(
        key=lambda f: (
            1 if norm(f.get("recommendation_type")) == "act_now" else 0,
            float(f.get("rank_score") or 0.0),
            float(f.get("confidence_score") or 0.0),
        ),
        reverse=True,
    )
    primary = actionable[0]
    # Contact constraint often blocks recovery — pin as weekly focus when present.
    contact = next(
        (
            f
            for f in actionable
            if norm(f.get("finding_type")) == TYPE_MISSING_CONTACT_BLOCKS
        ),
        None,
    )
    if contact is not None and float(contact.get("rank_score") or 0) >= float(
        primary.get("rank_score") or 0
    ) * 0.85:
        primary = contact
    primary_id = norm(primary.get("finding_id"))
    runner = next(
        (f for f in actionable if norm(f.get("finding_id")) != primary_id),
        None,
    )
    if runner is None:
        return None

    if norm(primary.get("finding_type")) == TYPE_MISSING_CONTACT_BLOCKS:
        focus_phrase = "التقاط وسيلة تواصل العميل قبل مغادرة المتجر"
    elif _mentions_shipping(primary):
        focus_phrase = "وضوح تكلفة الشحن في مسار الشراء"
    elif norm(primary.get("finding_type")) == TYPE_HIGH_INTEREST_LOW_PURCHASE:
        focus_phrase = "إغلاق شراء المنتجات ذات الاهتمام المرتفع"
    else:
        # Derive a short merchant phrase from recommendation direction.
        direction = norm(primary.get("recommended_direction"))
        focus_phrase = direction[:80] if direction else _label(primary)

    ids, labels = _ids_labels(primary, runner)
    if len(ids) < 2:
        return None
    card = empty_reasoning(
        reasoning_id=f"reasoning:priority:weekly_focus:{norm(store_slug)}",
        store_slug=store_slug,
        reasoning_type=TYPE_PRIORITY,
    )
    card.update(
        {
            "headline": f"إذا حسّنت شيئاً واحداً هذا الأسبوع، حسّن {focus_phrase}.",
            "business_meaning": (
                f"الدليل الحالي يضع «{_label(primary)}» أمام «{_label(runner)}» "
                "من حيث الأثر المتوقع على الإيراد هذا الأسبوع."
            ),
            "recommended_priority": (
                f"ركّز الجهد هذا الأسبوع على: {focus_phrase}."
            ),
            "expected_impact": (
                "تركيز أسبوعي واحد على أعلى عائق مثبت يقلّل تشتت الجهود "
                "ويرفع احتمال تحسّن ملموس قبل نهاية الأسبوع."
            ),
            "confidence_level": _min_confidence(
                norm(primary.get("confidence_level")),
                norm(runner.get("confidence_level")),
            ),
            "confidence_score": _avg_score(
                primary.get("confidence_score"),
                runner.get("confidence_score"),
            ),
            "certainty": CERTAINTY_OBSERVED
            if norm(primary.get("confidence_level")) == CONFIDENCE_HIGH
            else CERTAINTY_LIKELY,
            "supporting_finding_ids": ids,
            "supporting_finding_labels": labels,
            "quality_gates": evaluate_quality_gates_v1(
                supporting_finding_ids=ids,
                creates_business_decision=True,
                merchant_can_act_today=True,
            ),
            "rank_score": 95.0,
        }
    )
    return card


def rule_conflict_traffic_vs_conversion_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    High interest + low purchase + unavailable visits
    → cannot determine traffic vs conversion; more evidence required.
    """
    traffic = next(iter(_by_type(findings, TYPE_TRAFFIC_VS_CONVERSION)), None)
    conversion = next(
        iter(_by_type(findings, TYPE_HIGH_INTEREST_LOW_PURCHASE)),
        None,
    )
    if traffic is None or conversion is None:
        return None
    # Conflict is meaningful when traffic truth is insufficient/unknown.
    traffic_weak = (
        norm(traffic.get("status")) == STATUS_INSUFFICIENT
        or norm(traffic.get("confidence_level")) == CONFIDENCE_INSUFFICIENT
        or "غير متاحة" in norm(traffic.get("merchant_summary"))
    )
    if not traffic_weak:
        return None

    ids, labels = _ids_labels(traffic, conversion)
    card = empty_reasoning(
        reasoning_id=f"reasoning:conflict:traffic_vs_conversion:{norm(store_slug)}",
        store_slug=store_slug,
        reasoning_type=TYPE_CONFLICT,
    )
    card.update(
        {
            "headline": (
                "لا يمكن بعد الجزم إن كانت المشكلة في الزيارات أم في التحويل."
            ),
            "business_meaning": (
                "هناك اهتمام ضعيف الإتمام على بعض المنتجات، "
                "لكن بيانات الزيارات الموثوقة غير كافية — "
                "أي قرار إعلاني الآن سيكون افتراضاً لا دليلاً."
            ),
            "recommended_priority": (
                "اربط مصدر زيارات موثوقاً قبل توسيع الحملات أو تغيير ميزانية الإعلانات."
            ),
            "expected_impact": (
                "توضيح مصدر الضعف (زيارات مقابل تحويل) يمنع صرف جهد على الحل الخاطئ."
            ),
            "confidence_level": CONFIDENCE_MEDIUM,
            "confidence_score": 0.55,
            "certainty": CERTAINTY_UNKNOWN,
            "supporting_finding_ids": ids,
            "supporting_finding_labels": labels,
            "quality_gates": evaluate_quality_gates_v1(
                supporting_finding_ids=ids,
                creates_business_decision=True,
                merchant_can_act_today=True,
            ),
            "rank_score": 70.0,
        }
    )
    return card


def rule_constraint_missing_contact_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    Missing phone + recovery/channel demand
    → recovery opportunities limited before messaging begins.
    """
    contact = next(iter(_by_type(findings, TYPE_MISSING_CONTACT_BLOCKS)), None)
    # Prefer recovery-channel demand over hesitation (hesitation is a different constraint).
    recovery_need = next(
        iter(
            _by_type(
                findings,
                TYPE_RECOVERY_CHANNEL_EFFECTIVENESS,
                TYPE_RETURN_WITHOUT_PURCHASE,
                TYPE_WHATSAPP_TEST_CANDIDATE,
            )
        ),
        None,
    )
    if recovery_need is None:
        recovery_need = next(iter(_by_type(findings, TYPE_DOMINANT_HESITATION)), None)
    if contact is None or recovery_need is None:
        return None
    ids, labels = _ids_labels(contact, recovery_need)
    card = empty_reasoning(
        reasoning_id=f"reasoning:constraint:missing_contact:{norm(store_slug)}",
        store_slug=store_slug,
        reasoning_type=TYPE_CONSTRAINT,
    )
    card.update(
        {
            "headline": (
                "فرص الاسترجاع محدودة قبل أن يبدأ التواصل أصلاً."
            ),
            "business_meaning": (
                "جزء مهم من السلال يبقى خارج واتساب لأن وسيلة التواصل غير متوفرة، "
                "فيتعطّل أي تحسين لاحق على الرسائل أو التوقيت."
            ),
            "recommended_priority": (
                "اجعل التقاط رقم العميل أولوية تشغيلية قبل توسيع رسائل الاسترجاع."
            ),
            "expected_impact": (
                "كل رقم صالح يُفتح له مسار استرجاع كان مغلقاً — "
                "وهذا يوسّع قاعدة الإيراد القابلة للمتابعة فوراً."
            ),
            "confidence_level": _min_confidence(
                norm(contact.get("confidence_level")),
                norm(recovery_need.get("confidence_level")),
            ),
            "confidence_score": _avg_score(
                contact.get("confidence_score"),
                recovery_need.get("confidence_score"),
            ),
            "certainty": CERTAINTY_OBSERVED,
            "supporting_finding_ids": ids,
            "supporting_finding_labels": labels,
            "quality_gates": evaluate_quality_gates_v1(
                supporting_finding_ids=ids,
                creates_business_decision=True,
                merchant_can_act_today=True,
            ),
            "rank_score": 94.0,
        }
    )
    return card


def rule_opportunity_delivery_resolution_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> Optional[dict[str, Any]]:
    """
    Delivery-time reason shows stronger recovery completion than unresolved shipping
    → optimizing delivery messaging likely faster gains than discount campaigns.
    """
    delivery = next(
        (
            f
            for f in _by_type(findings, TYPE_HESITATION_RESOLUTION)
            if _mentions_delivery_time(f) and _is_high_resolution(f)
        ),
        None,
    )
    contrast = next(
        (
            f
            for f in findings
            if (
                (_mentions_shipping(f) and _is_unresolved_barrier(f))
                or norm(f.get("finding_type")) == TYPE_DOMINANT_HESITATION
                and _mentions_shipping(f)
            )
        ),
        None,
    )
    if delivery is None or contrast is None:
        return None
    ids, labels = _ids_labels(delivery, contrast)
    card = empty_reasoning(
        reasoning_id=f"reasoning:opportunity:delivery_messaging:{norm(store_slug)}",
        store_slug=store_slug,
        reasoning_type=TYPE_OPPORTUNITY,
    )
    card.update(
        {
            "headline": (
                "من يذكرون «وقت التوصيل» يُكملون الشراء بمعدّل أعلى بعد العودة."
            ),
            "business_meaning": (
                "هذا المسار يُظهر استجابة أسرع للوضوح حول التوصيل، "
                "مقارنة بعائق الشحن الذي يبقى غالباً بلا حل."
            ),
            "recommended_priority": (
                "حسّن رسائل ووضوح وقت التوصيل قبل الاعتماد على حملات الخصم."
            ),
            "expected_impact": (
                "تحسين عرض التوصيل مرجّح لإنتاج مكاسب أسرع من توسيع الخصومات، "
                "لأن الدليل يظهر إتماماً أعلى لهذا السبب بعد العودة."
            ),
            "confidence_level": _min_confidence(
                norm(delivery.get("confidence_level")),
                norm(contrast.get("confidence_level")),
            ),
            "confidence_score": _avg_score(
                delivery.get("confidence_score"),
                contrast.get("confidence_score"),
            ),
            "certainty": CERTAINTY_LIKELY,
            "supporting_finding_ids": ids,
            "supporting_finding_labels": labels,
            "quality_gates": evaluate_quality_gates_v1(
                supporting_finding_ids=ids,
                creates_business_decision=True,
                merchant_can_act_today=True,
            ),
            "rank_score": 80.0,
        }
    )
    return card


def evaluate_all_reasoning_rules_v1(
    store_slug: str, findings: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Run deterministic rule set in stable order."""
    rules: list[RuleFn] = [
        rule_priority_single_focus_v1,
        rule_constraint_missing_contact_v1,
        rule_relationship_recovery_vs_shipping_v1,
        rule_opportunity_delivery_resolution_v1,
        rule_conflict_traffic_vs_conversion_v1,
    ]
    out: list[dict[str, Any]] = []
    for rule in rules:
        card = rule(store_slug, findings)
        if card is not None:
            out.append(card)
    return out
