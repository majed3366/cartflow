# -*- coding: utf-8 -*-
"""
Merchant Home Composition v1 — presentation-only composition of governed knowledge.

Consumes Daily Brief (routing-backed), Knowledge Layer projection, and read-model nav
metadata. Never mints decisions, explanations, routing, or KPI knowledge.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from services.knowledge_layer_projection_v1 import (
    flatten_kl_routed_display_items_v1,
    project_kl_display_card_v1,
)
from services.knowledge_routing_v1 import (
    ROUTING_VERSION,
    SURFACE_MERCHANT_HOME,
    route_merchant_home_knowledge_v1,
)
from services.merchant_daily_brief_time_v1 import brief_date_iso
from services.merchant_daily_brief_v1 import MAX_BRIEF_ITEMS

COMPOSITION_VERSION = "v1"
EXPERIENCE_TIER_STARTER = "starter"
EXPERIENCE_TIER_GROWTH = "growth"
EXPERIENCE_TIER_PRO = "pro"

HOME_MAX_ATTENTION_DISPLAY = 3
HOME_MAX_UNDERSTANDING_DISPLAY = 3

_SECTION_WHILE_AWAY = "while_away"
_SECTION_ATTENTION = "attention_today"
_SECTION_UNDERSTANDING = "store_understanding"


def _norm(value: Any) -> str:
    return str(value or "").strip()


def _greeting_ar(hour: Optional[int] = None) -> str:
    from services.knowledge_time_authority_v1 import knowledge_stamp_now  # noqa: PLC0415

    h = hour if hour is not None else knowledge_stamp_now().hour
    if 5 <= h < 12:
        return "صباح الخير"
    return "مساء الخير"


def _dedupe_key_from_topic(topic: Mapping[str, Any]) -> str:
    agg = _norm(topic.get("aggregation_key"))
    if agg:
        return f"agg:{agg}"
    kid = _norm(topic.get("routed_knowledge_id"))
    if kid:
        return f"kid:{kid}"
    return f"bid:{_norm(topic.get('brief_item_id'))}"


def _dedupe_key_from_card(card: Mapping[str, Any]) -> str:
    kid = _norm(card.get("routing_knowledge_id")) or _norm(card.get("source_knowledge_id"))
    if kid:
        return f"kid:{kid}"
    return f"key:{_norm(card.get('insight_key'))}"


def _project_while_away_item(topic: Mapping[str, Any]) -> dict[str, Any]:
    headline = _norm(topic.get("headline_ar"))
    if not headline:
        headline = _norm(topic.get("what_ar")) or "—"
    detail = _norm(topic.get("why_ar")) or _norm(topic.get("what_ar"))
    return {
        "headline_ar": headline,
        "detail_ar": detail,
        "action_ar": _norm(topic.get("action_ar")),
        "aggregation_key": _norm(topic.get("aggregation_key")),
        "source_knowledge_id": _norm(topic.get("routed_knowledge_id")),
        "routing_priority": int(topic.get("routing_priority") or 0),
        "section": _SECTION_WHILE_AWAY,
    }


def _project_attention_item(topic: Mapping[str, Any]) -> dict[str, Any]:
    headline = _norm(topic.get("headline_ar"))
    if not headline:
        if topic.get("action_present") and topic.get("action_ar"):
            headline = _norm(topic.get("action_ar"))
        else:
            headline = _norm(topic.get("what_ar")) or "—"
    cls = _norm(topic.get("decision_class"))
    severity = "observation"
    if cls == "critical_action":
        severity = "critical"
    elif cls == "suggested_action":
        severity = "suggested"
    elif cls == "needs_attention":
        severity = "attention"
    return {
        "headline_ar": headline,
        "why_ar": _norm(topic.get("why_ar")),
        "action_ar": _norm(topic.get("action_ar")),
        "action_present": bool(topic.get("action_present")),
        "decision_class": cls,
        "decision_class_label_ar": _norm(topic.get("decision_class_label_ar")),
        "severity": severity,
        "aggregation_key": _norm(topic.get("aggregation_key")),
        "source_knowledge_id": _norm(topic.get("routed_knowledge_id")),
        "routing_priority": int(topic.get("routing_priority") or 0),
        "section": _SECTION_ATTENTION,
    }


def _project_understanding_item(
    card: Mapping[str, Any],
    *,
    window_days: int = 7,
) -> dict[str, Any]:
    return {
        "title_ar": _norm(card.get("title_ar")),
        "observation_ar": _norm(card.get("observation_ar")),
        "impact_ar": _norm(card.get("impact_ar")),
        "action_ar": _norm(card.get("action_ar")),
        "insight_key": _norm(card.get("insight_key")),
        "source_knowledge_id": _norm(card.get("routing_knowledge_id"))
        or _norm(card.get("source_knowledge_id")),
        "confidence": _norm(card.get("confidence")) or "insufficient",
        "evidence_label_ar": _norm(card.get("evidence_label_ar")),
        "window_days": int(window_days or 7),
        "section": _SECTION_UNDERSTANDING,
    }


def _build_quick_nav_v1(nav: Optional[Mapping[str, Any]] = None) -> list[dict[str, Any]]:
    n = nav if isinstance(nav, Mapping) else {}
    active_carts = int(n.get("active_carts") or 0)
    waiting = int(n.get("waiting_send") or 0)
    return [
        {
            "id": "knowledge",
            "label_ar": "طبقة المعرفة",
            "nav_type": "anchor",
            "href": "#ma-home-understanding",
        },
        {
            "id": "active_carts",
            "label_ar": "السلال النشطة",
            "nav_type": "cart_tab",
            "cart_tab": "all",
            "badge_count": active_carts if active_carts > 0 else 0,
        },
        {
            "id": "completed",
            "label_ar": "الاستردادات المكتملة",
            "nav_type": "cart_tab",
            "cart_tab": "completed",
        },
        {
            "id": "settings",
            "label_ar": "الإعدادات",
            "nav_type": "settings",
            "settings_page": "settings",
        },
        {
            "id": "waiting",
            "label_ar": "بانتظار الإرسال",
            "nav_type": "cart_tab",
            "cart_tab": "waiting",
            "badge_count": waiting if waiting > 0 else 0,
            "visible": waiting > 0,
        },
    ]


def _tier_capabilities_v1() -> dict[str, dict[str, Any]]:
    """Progressive experience tiers — architecture only; Starter active today."""
    return {
        EXPERIENCE_TIER_STARTER: {
            "max_attention_display": HOME_MAX_ATTENTION_DISPLAY,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY,
            "trend_awareness": False,
            "executive_summary": False,
        },
        EXPERIENCE_TIER_GROWTH: {
            "max_attention_display": HOME_MAX_ATTENTION_DISPLAY,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY + 2,
            "trend_awareness": True,
            "executive_summary": False,
        },
        EXPERIENCE_TIER_PRO: {
            "max_attention_display": MAX_BRIEF_ITEMS,
            "max_understanding_display": HOME_MAX_UNDERSTANDING_DISPLAY + 2,
            "trend_awareness": True,
            "executive_summary": True,
        },
    }


def compose_merchant_home_experience_v1(
    *,
    merchant_name_ar: str = "",
    date_ar: str = "",
    brief_date: Optional[str] = None,
    daily_brief: Optional[Mapping[str, Any]] = None,
    kl_insights: Iterable[Mapping[str, Any] | None] | None = None,
    window_days: int = 7,
    nav_metadata: Optional[Mapping[str, Any]] = None,
    experience_tier: str = EXPERIENCE_TIER_STARTER,
    routed_home_feed: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Compose Merchant Home experience sections from governed upstream payloads."""
    day = brief_date or brief_date_iso()
    brief = daily_brief if isinstance(daily_brief, Mapping) else {}
    tier = _norm(experience_tier) or EXPERIENCE_TIER_STARTER
    tier_caps = _tier_capabilities_v1().get(tier, _tier_capabilities_v1()[EXPERIENCE_TIER_STARTER])
    max_attention = int(tier_caps.get("max_attention_display") or HOME_MAX_ATTENTION_DISPLAY)
    max_understanding = int(
        tier_caps.get("max_understanding_display") or HOME_MAX_UNDERSTANDING_DISPLAY
    )

    seen_keys: set[str] = set()
    while_away: list[dict[str, Any]] = []
    for raw in brief.get("achievements") or []:
        if not isinstance(raw, Mapping):
            continue
        key = _dedupe_key_from_topic(raw)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        while_away.append(_project_while_away_item(raw))

    attention: list[dict[str, Any]] = []
    for raw in brief.get("attention_items") or brief.get("items") or []:
        if not isinstance(raw, Mapping):
            continue
        key = _dedupe_key_from_topic(raw)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        attention.append(_project_attention_item(raw))
        if len(attention) >= max_attention:
            break

    feed = routed_home_feed or route_merchant_home_knowledge_v1(
        kl_insights=kl_insights,
        max_display_items=max_understanding,
    )
    selected = flatten_kl_routed_display_items_v1(feed, max_items=max_understanding)
    understanding: list[dict[str, Any]] = []
    for routed in selected:
        card = project_kl_display_card_v1(routed, window_days=window_days)
        key = _dedupe_key_from_card(card)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        understanding.append(_project_understanding_item(card, window_days=window_days))

    attention_count = len(attention)
    empty_calm = not while_away and not attention and not understanding

    return {
        "version": COMPOSITION_VERSION,
        "experience_tier": tier,
        "tier_capabilities": _tier_capabilities_v1(),
        "brief_date": day,
        "greeting": {
            "greeting_ar": _greeting_ar(),
            "merchant_name_ar": _norm(merchant_name_ar) or "متجرك",
            "date_ar": _norm(date_ar),
        },
        "while_away": {
            "title_ar": "بينما كنت بعيداً",
            "lead_ar": "CartFlow يتابع متجرك تلقائياً — هذا ما اكتمل:",
            "items": while_away,
            "empty_message_ar": "CartFlow يتابع متجرك — سنُظهر الإنجازات هنا عند توفرها.",
        },
        "attention_today": {
            "title_ar": "يحتاج انتباهك اليوم",
            "lead_ar": "إجراءات مقترحة — بدون تكرار.",
            "items": attention,
            "max_display": max_attention,
            "platform_max": MAX_BRIEF_ITEMS,
            "count": attention_count,
            "empty_message_ar": "لا أمور تتطلب انتباهك الآن — CartFlow يتابع الحالات الروتينية.",
        },
        "store_understanding": {
            "title_ar": "فهم المتجر",
            "lead_ar": "فهم تشغيلي — ليس أرقاماً فقط.",
            "items": understanding,
            "max_display": max_understanding,
            "empty_message_ar": "لا توجد استنتاجات كافية بعد — استمر في جمع النشاط.",
        },
        "quick_nav": {
            "title_ar": "انتقال سريع",
            "items": _build_quick_nav_v1(nav_metadata),
        },
        "empty_calm": empty_calm,
        "knowledge_routing_v1": {
            "routing_version": _norm(feed.get("routing_version")) or ROUTING_VERSION,
            "surface": SURFACE_MERCHANT_HOME,
            "observability": dict(feed.get("observability") or {}),
        },
        "sources": {
            "daily_brief_version": _norm(brief.get("version")),
            "daily_brief_composer": _norm(brief.get("composer_version")),
            "achievement_count": len(brief.get("achievements") or []),
            "attention_source_count": len(brief.get("attention_items") or brief.get("items") or []),
            "understanding_routed_groups": len(selected),
        },
        "observability": {
            "while_away_items": len(while_away),
            "attention_items": len(attention),
            "understanding_items": len(understanding),
            "dedupe_keys": len(seen_keys),
        },
    }


def build_merchant_home_experience_api_payload(
    db_session: Any,
    store_slug: str,
    dash_store: Any,
    *,
    merchant_name_ar: str = "",
    date_ar: str = "",
    nav_metadata: Optional[Mapping[str, Any]] = None,
    experience_tier: str = EXPERIENCE_TIER_STARTER,
) -> dict[str, Any]:
    """Build store home experience by composing certified upstream consumers."""
    slug = _norm(store_slug)
    kl_insights: list[Mapping[str, Any]] = []
    window_days = 7

    if not _norm(merchant_name_ar):
        try:
            from services.merchant_onboarding_store import (  # noqa: PLC0415
                merchant_store_display_name,
            )

            merchant_name_ar = merchant_store_display_name(dash_store) or "متجرك"
        except (ImportError, TypeError, ValueError):
            merchant_name_ar = _norm(getattr(dash_store, "store_name", None)) or "متجرك"

    from services.merchant_daily_brief_v1 import build_merchant_daily_brief_api_payload  # noqa: PLC0415

    brief = build_merchant_daily_brief_api_payload(db_session, slug, dash_store)

    try:
        from services.knowledge_layer_v1 import build_knowledge_report  # noqa: PLC0415

        report = build_knowledge_report(db_session, slug, window_days=window_days)
        for raw in report.to_dict().get("insights") or []:
            if isinstance(raw, Mapping):
                kl_insights.append(raw)
    except (OSError, TypeError, ValueError, ImportError):
        pass

    composed = compose_merchant_home_experience_v1(
        merchant_name_ar=merchant_name_ar,
        date_ar=date_ar,
        brief_date=_norm(brief.get("brief_date")) or brief_date_iso(),
        daily_brief=brief,
        kl_insights=kl_insights,
        window_days=window_days,
        nav_metadata=nav_metadata,
        experience_tier=experience_tier,
    )
    from services.knowledge_time_authority_v1 import knowledge_stamp_now  # noqa: PLC0415

    composed["ok"] = True
    composed["generated_at"] = (
        knowledge_stamp_now().replace(microsecond=0).isoformat()
    )
    composed["store_slug"] = slug
    composed["daily_brief_v1"] = brief
    return composed


__all__ = [
    "COMPOSITION_VERSION",
    "EXPERIENCE_TIER_GROWTH",
    "EXPERIENCE_TIER_PRO",
    "EXPERIENCE_TIER_STARTER",
    "HOME_MAX_ATTENTION_DISPLAY",
    "HOME_MAX_UNDERSTANDING_DISPLAY",
    "build_merchant_home_experience_api_payload",
    "compose_merchant_home_experience_v1",
]
