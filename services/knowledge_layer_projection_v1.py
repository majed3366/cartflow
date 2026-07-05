# -*- coding: utf-8 -*-
"""
Knowledge Layer Projection v1 — presentation-only consumer of routed KL knowledge.

Moved from merchant_knowledge_layer.js OIA builders (Sprint 1 migration).
Routing owns selection, ranking, aggregation; this module projects routed items only.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    SURFACE_KNOWLEDGE_LAYER,
    route_knowledge_layer_knowledge_v1,
)

PROJECTION_VERSION = "v1"
MAX_KL_DISPLAY_ITEMS = 5

GENERIC_WATCH_PHRASE = "راقب هذا المؤشر خلال الأيام القادمة"

REASON_AR = {
    "price": "السعر",
    "quality": "الجودة",
    "shipping": "الشحن",
    "delivery": "التوصيل",
    "warranty": "الضمان",
    "other": "سبب آخر",
    "thinking": "يفكّر",
}

REASON_IMPACT_AR = {
    "price": "معظم حالات التردد المسجلة مرتبطة بالسعر.",
    "quality": "معظم حالات التردد المسجلة مرتبطة بالجودة.",
    "shipping": "معظم حالات التردد المسجلة مرتبطة بالشحن.",
    "delivery": "معظم حالات التردد المسجلة مرتبطة بالتوصيل.",
    "warranty": "معظم حالات التردد المسجلة مرتبطة بالضمان.",
    "other": "حالات التردد موزعة على أسباب متنوعة.",
    "thinking": "بعض العملاء يحتاجون وقتاً إضافياً قبل الشراء.",
}

REASON_ACTION_AR = {
    "price": "راجع التسعير أو وضّح قيمة المنتج بشكل أكبر.",
    "quality": "وضّح مواصفات المنتج وضمانات الجودة في صفحة المنتج.",
    "shipping": "راجع تكلفة أو مدة الشحن المعروضة للعميل.",
    "delivery": "وضّح خيارات التوصيل والمدة المتوقعة بوضوح.",
    "warranty": "أبرز سياسة الضمان وخدمة ما بعد البيع.",
    "other": "راجع تجربة الشراء من صفحة المنتج حتى الدفع.",
    "thinking": "قد يساعد توضيح العروض أو ضمانات الإرجاع في تقريب القرار.",
}

BOTTLENECK_AR = {
    "failed": "فشل الإرسال",
    "ignored": "رفض العميل المساعدة",
    "stopped": "توقّف المسار",
    "no_reply": "لم يرد العميل",
}


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _norm_lower(value: Any) -> str:
    return _norm(value).lower()


def localize_reason(raw: Any) -> str:
    key = _norm_lower(raw)
    return REASON_AR.get(key, REASON_AR["other"])


def localize_bottleneck(raw: Any) -> str:
    key = _norm_lower(raw)
    return BOTTLENECK_AR.get(key, "يحتاج متابعة")


def comparison_period_label(window_days: int) -> str:
    days = int(window_days or 7)
    if days == 7:
        return "مقارنة بالأسبوع السابق"
    if days == 30:
        return "مقارنة بآخر 30 يوماً"
    return f"مقارنة بآخر {days} يوماً"


def replace_known_tokens(text: Any) -> str:
    s = _norm(text)
    for key, ar in REASON_AR.items():
        s = s.replace(f"«{key}»", f"«{ar}»")
    for key, ar in BOTTLENECK_AR.items():
        s = s.replace(key, ar)
    return s


def card_title(ins: Mapping[str, Any]) -> str:
    key = _norm(ins.get("insight_key"))
    if key == "recovery_bottleneck":
        return "أكبر فرصة لتحسين الاسترجاع"
    if key == "traffic_cart_demand_trend":
        return "اتجاه الطلب (سلات مهجورة)"
    return _norm(ins.get("title_ar"))


def _top_reason_from_distribution(dist: Mapping[str, Any]) -> str:
    best = ""
    best_n = -1
    for k, v in dist.items():
        n = int(v or 0)
        if n > best_n:
            best_n = n
            best = _norm(k)
    return best


def _format_distribution_observation(dist: Mapping[str, Any]) -> str:
    if not dist:
        return "لا يوجد توزيع مسجّل بعد."
    parts: list[str] = []
    for k in sorted(dist.keys(), key=lambda x: int(dist.get(x) or 0), reverse=True):
        parts.append(f"{localize_reason(k)}: {dist[k]}")
    return " · ".join(parts) if parts else "لا يوجد توزيع مسجّل بعد."


def build_hesitation_top_reason_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any]
) -> dict[str, str]:
    reason = localize_reason(ev.get("top_reason"))
    reason_key = _norm_lower(ev.get("top_reason")) or "other"
    obs = f"{reason} هو السبب الأكثر تسجيلاً حالياً."
    if ev.get("top_count") is not None and ev.get("hesitation_total") is not None:
        obs += f" ({ev['top_count']} من {ev['hesitation_total']} حالة تردد)."
    return {
        "title": card_title(ins),
        "observation": obs,
        "impact": REASON_IMPACT_AR.get(reason_key, REASON_IMPACT_AR["other"]),
        "action": REASON_ACTION_AR.get(reason_key, REASON_ACTION_AR["other"]),
    }


def build_hesitation_distribution_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any]
) -> dict[str, str]:
    top_key = _top_reason_from_distribution(ev.get("distribution") or {})
    action = "ركز أولاً على السبب الأكثر تكراراً."
    if top_key:
        action = f"ركز أولاً على «{localize_reason(top_key)}» لأنه الأكثر تكراراً."
    return {
        "title": card_title(ins),
        "observation": _format_distribution_observation(ev.get("distribution") or {}),
        "impact": "يساعدك على معرفة ما إذا كانت المشكلة مركزة في سبب واحد أو موزعة بين عدة أسباب.",
        "action": action,
    }


def build_recovery_bottleneck_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any]
) -> dict[str, str]:
    bottlenecks = ev.get("bottlenecks")
    b0: Mapping[str, Any] = {}
    if isinstance(bottlenecks, list) and bottlenecks:
        first = bottlenecks[0]
        if isinstance(first, Mapping):
            b0 = first
    bk = _norm_lower(b0.get("key") or b0.get("label") or "no_reply")
    obs_map = {
        "no_reply": "لم يرد العميل على الرسائل في أغلب الحالات.",
        "failed": "فشل إرسال الرسائل في أغلب الحالات المسجّلة.",
        "ignored": "رفض العميل المساعدة في أغلب الحالات المسجّلة.",
        "stopped": "توقّف مسار الاسترجاع في أغلب الحالات المسجّلة.",
    }
    impact_map = {
        "no_reply": "عدم التفاعل يقلل فرص تحويل التردد إلى حوار.",
        "failed": "فشل الإرسال يمنع الوصول إلى العميل في الوقت المناسب.",
        "ignored": "رفض المساعدة يحدّ من فرص متابعة العميل تلقائياً.",
        "stopped": "توقّف المسار يترك سلات دون متابعة كاملة.",
    }
    action_map = {
        "no_reply": "تأكد من صحة بيانات التواصل ونص الرسالة وتوقيت الإرسال.",
        "failed": "تحقق من إعدادات واتساب وحالة رقم التواصل.",
        "ignored": "راجع نص الرسالة الأولى وتوقيت ظهور الودجت.",
        "stopped": "راجع إعدادات الاسترجاع وعدد المحاولات المسموح بها.",
    }
    obs = obs_map.get(bk, "هناك نقطة ضغط واضحة في مسار الاسترجاع.")
    if b0.get("count") is not None:
        obs += f" ({b0['count']} حدث — {localize_bottleneck(bk)})."
    return {
        "title": card_title(ins),
        "observation": obs,
        "impact": impact_map.get(bk, "قد يحدّ ذلك من فعالية الاسترجاع الحالية."),
        "action": action_map.get(bk, "راجع إعدادات الاسترجاع وبيانات التواصل."),
    }


def build_recovery_activity_summary_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any]
) -> dict[str, str]:
    sent = ev.get("messages_sent", 0)
    replies = ev.get("replies", 0)
    purchase_count = ev.get("purchase_count", 0)
    attributed = ev.get("attributed_recovery_purchase_count", 0)
    returns = ev.get("returns", 0)
    return {
        "title": card_title(ins),
        "observation": (
            f"رسائل مُرسَلة: {sent} · ردود: {replies} · عائدون للموقع: {returns} · "
            f"مشتريات مؤكدة: {purchase_count} · مُنسَبة للاسترجاع: {attributed}."
        ),
        "impact": "يوضح مدى تقدم جهود الاسترجاع الحالية.",
        "action": "استمر بجمع البيانات حتى تظهر أنماط أوضح.",
    }


def build_cart_trend_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any], *, window_days: int
) -> dict[str, str]:
    period = comparison_period_label(window_days)
    cur = ev.get("cart_count", 0)
    prev = ev.get("prev_cart_count", 0)
    trend = _norm_lower(ev.get("trend")) or "stable"
    if trend == "up":
        obs = f"عدد السلات المسجلة أعلى من الفترة المقارنة ({period})."
    elif trend == "down":
        obs = f"عدد السلات المسجلة أقل من الفترة المقارنة ({period})."
    else:
        obs = f"عدد السلات المسجلة مستقر نسبياً ({period})."
    obs += (
        f" الحالي: {cur} · المقارنة: {prev}."
        " (مؤشر طلب من CartFlow وليس عدد زوار.)"
    )
    impact_map = {
        "up": "هناك اهتمام أكبر بالمنتجات.",
        "down": "الاهتمام بالسلات أقل من الفترة المقارنة.",
        "stable": "الطلب على السلات ثابت نسبياً.",
    }
    action_map = {
        "up": "راقب ما إذا كانت الزيادة تتحول إلى مبيعات فعلية.",
        "down": "راجع أسباب التردد وتابع السلات التي لم تُكمل الشراء.",
        "stable": "استمر بمراقبة السلات ومسارات الاسترجاع.",
    }
    return {
        "title": card_title(ins),
        "observation": obs,
        "impact": impact_map.get(trend, impact_map["stable"]),
        "action": action_map.get(trend, action_map["stable"]),
    }


def build_conversion_cart_to_purchase_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any]
) -> dict[str, str]:
    purchases = ev.get("purchase_count", 0)
    carts = ev.get("cart_count", ins.get("sample_size") or 0)
    return {
        "title": card_title(ins),
        "observation": f"{purchases} عملية شراء مؤكدة من {carts} سلة في نافذة البيانات.",
        "impact": "يوضح ما إذا كانت السلات تتحول إلى شراء فعلي.",
        "action": "تابع السلال المفتوحة التي لم تُكمل الشراء بعد.",
    }


def build_store_health_oia(ins: Mapping[str, Any], ev: Mapping[str, Any]) -> dict[str, str]:
    signals = ev.get("signals")
    if isinstance(signals, list) and signals:
        obs = "إشارات البيانات الحالية: " + "، ".join(str(s) for s in signals) + "."
    else:
        obs = replace_known_tokens(ins.get("message_ar") or "البيانات الأساسية متاحة.")
    return {
        "title": card_title(ins),
        "observation": obs,
        "impact": "تساعدك على فهم جاهزية البيانات قبل الاعتماد على الاستنتاجات.",
        "action": "تأكد أن بيانات المتجر والودجت تصل بشكل صحيح.",
    }


def build_generic_oia(
    ins: Mapping[str, Any], ev: Mapping[str, Any], *, window_days: int
) -> dict[str, str]:
    action_raw = _norm(ins.get("recommended_action_ar"))
    if action_raw == GENERIC_WATCH_PHRASE:
        action = "راجع البيانات المصدرية وتأكد من اكتمال التتبع."
    else:
        action = replace_known_tokens(action_raw)
    return {
        "title": card_title(ins),
        "observation": replace_known_tokens(ins.get("message_ar") or "—"),
        "impact": "قد يؤثر ذلك على فهمك لما يحدث في المتجر.",
        "action": action,
    }


_OIA_BUILDERS = {
    "hesitation_top_reason": build_hesitation_top_reason_oia,
    "hesitation_distribution": build_hesitation_distribution_oia,
    "recovery_bottleneck": build_recovery_bottleneck_oia,
    "recovery_activity_summary": build_recovery_activity_summary_oia,
    "traffic_cart_demand_trend": build_cart_trend_oia,
    "conversion_cart_to_purchase": build_conversion_cart_to_purchase_oia,
    "store_health_overview": build_store_health_oia,
}


def project_kl_oia_v1(
    ins: Mapping[str, Any],
    *,
    window_days: int = 7,
) -> dict[str, str]:
    """Project one producer insight into OIA presentation fields (routed payload only)."""
    key = _norm(ins.get("insight_key"))
    ev = ins.get("evidence")
    if not isinstance(ev, Mapping):
        ev = {}
    builder = _OIA_BUILDERS.get(key)
    if builder is build_cart_trend_oia:
        card = builder(ins, ev, window_days=window_days)
    elif builder is build_generic_oia:
        card = builder(ins, ev, window_days=window_days)
    elif builder:
        card = builder(ins, ev)
    else:
        card = build_generic_oia(ins, ev, window_days=window_days)
    return {
        "title_ar": _norm(card.get("title")) or card_title(ins),
        "observation_ar": _norm(card.get("observation")),
        "impact_ar": _norm(card.get("impact")),
        "action_ar": _norm(card.get("action")),
    }


def _payload_confidence_ok(payload: Mapping[str, Any]) -> bool:
    return _norm_lower(payload.get("confidence")) != "insufficient"


def flatten_kl_routed_display_items_v1(
    routed_feed: Mapping[str, Any],
    *,
    max_items: int = MAX_KL_DISPLAY_ITEMS,
) -> list[dict[str, Any]]:
    """Order routed items achievements-first; exclude insufficient-confidence payloads."""
    ordered: list[Mapping[str, Any]] = []
    achievements = routed_feed.get("achievements")
    if isinstance(achievements, list):
        ordered.extend(r for r in achievements if isinstance(r, Mapping))
    attention = routed_feed.get("attention_items")
    if isinstance(attention, list):
        ordered.extend(r for r in attention if isinstance(r, Mapping))

    selected: list[dict[str, Any]] = []
    for routed in ordered:
        payload = routed.get("knowledge_payload")
        if not isinstance(payload, Mapping):
            continue
        if not _payload_confidence_ok(payload):
            continue
        selected.append(dict(routed))
        if len(selected) >= max(0, int(max_items)):
            break
    return selected


def project_kl_display_card_v1(
    routed: Mapping[str, Any],
    *,
    window_days: int = 7,
) -> dict[str, Any]:
    """Project one routed KL item into a display card for the UI."""
    payload = routed.get("knowledge_payload")
    ins = payload if isinstance(payload, Mapping) else {}
    oia = project_kl_oia_v1(ins, window_days=window_days)
    producer_ref = routed.get("producer_reference")
    source_knowledge_id = _norm(ins.get("knowledge_id"))
    if isinstance(producer_ref, Mapping):
        source_knowledge_id = _norm(producer_ref.get("representative_knowledge_id")) or source_knowledge_id
    return {
        "display_card_id": f"kl:{source_knowledge_id}",
        "routing_knowledge_id": _norm(routed.get("knowledge_id")),
        "source_knowledge_id": source_knowledge_id,
        "routing_priority": int(routed.get("routing_priority") or 0),
        "section": _norm(routed.get("section")),
        "insight_key": _norm(ins.get("insight_key")),
        "category": _norm(ins.get("category")),
        "severity": _norm(ins.get("severity")) or "info",
        "confidence": _norm(ins.get("confidence")) or "insufficient",
        "evidence_id": _norm(ins.get("evidence_id")),
        "evidence_label_ar": _norm(ins.get("evidence_label_ar")),
        "title_ar": oia["title_ar"],
        "observation_ar": oia["observation_ar"],
        "impact_ar": oia["impact_ar"],
        "action_ar": oia["action_ar"],
        "traceability": routed.get("traceability"),
    }


def build_knowledge_layer_projection_v1(
    routed_feed: Mapping[str, Any],
    *,
    window_days: int = 7,
    max_display_items: int = MAX_KL_DISPLAY_ITEMS,
) -> dict[str, Any]:
    """Build KL API projection block from a routed feed."""
    selected = flatten_kl_routed_display_items_v1(
        routed_feed,
        max_items=max_display_items,
    )
    cards = [
        project_kl_display_card_v1(r, window_days=window_days)
        for r in selected
    ]
    empty_reason = None
    if not cards:
        empty_reason = "insufficient_actionable_knowledge"
    return {
        "version": PROJECTION_VERSION,
        "surface": SURFACE_KNOWLEDGE_LAYER,
        "routing_version": ROUTING_VERSION,
        "window_days": int(window_days or 7),
        "display_cards": cards,
        "empty_reason": empty_reason,
        "observability": {
            "routed_achievement_groups": len(routed_feed.get("achievements") or []),
            "routed_attention_groups": len(routed_feed.get("attention_items") or []),
            "display_card_count": len(cards),
        },
    }


def enrich_knowledge_report_kl_routing_and_projection_v1(
    payload: dict[str, Any],
    *,
    max_display_items: int = MAX_KL_DISPLAY_ITEMS,
) -> None:
    """Attach KL routing feed + projection to /api/knowledge/report payload."""
    if not isinstance(payload, dict):
        return
    insights = payload.get("insights")
    if not isinstance(insights, list):
        return
    window_days = int(payload.get("window_days") or 7)
    routed = route_knowledge_layer_knowledge_v1(
        kl_insights=insights,
        max_display_items=max_display_items,
    )
    payload["knowledge_routing_v1"] = routed
    payload["knowledge_layer_projection_v1"] = build_knowledge_layer_projection_v1(
        routed,
        window_days=window_days,
        max_display_items=max_display_items,
    )


__all__ = [
    "MAX_KL_DISPLAY_ITEMS",
    "PROJECTION_VERSION",
    "build_knowledge_layer_projection_v1",
    "comparison_period_label",
    "enrich_knowledge_report_kl_routing_and_projection_v1",
    "flatten_kl_routed_display_items_v1",
    "localize_reason",
    "project_kl_display_card_v1",
    "project_kl_oia_v1",
]
