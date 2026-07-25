# -*- coding: utf-8 -*-
"""
Business Theme Engine V1 — many Business Facts → one canonical Theme.

Never invents themes from counters. Never emits recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.business_facts_v1.contract_v1 import (
    FACT_TYPE_COMMUNICATION,
    FACT_TYPE_CONVERSION,
    FACT_TYPE_CUSTOMER_BEHAVIOUR,
    FACT_TYPE_PRODUCT_DEMAND,
    FACT_TYPE_RECOVERY,
    FACT_TYPE_STORE_HEALTH,
)
from services.business_themes_v1.contract_v1 import (
    BUSINESS_THEMES_VERSION_V1,
    OWNER_COMMUNICATION,
    OWNER_DECISION_WORKSPACE,
    OWNER_HOME,
    THEME_COMMUNICATION_COVERAGE,
    THEME_CUSTOMER_RETURN_BEHAVIOUR,
    THEME_PRIMARY_OWNER_V1,
    THEME_PRODUCT_CONVERSION,
    THEME_PRODUCT_DEMAND,
    THEME_RECOVERY_OPPORTUNITY,
    THEME_SHIPPING_FRICTION,
    THEME_STORE_HEALTH,
    THEME_TITLE_AR_V1,
    empty_theme_shell_v1,
    validate_business_theme_v1,
)
from services.business_themes_v1.flag_v1 import business_themes_v1_enabled

# Minimum supporting facts / confidence to admit a theme publicly.
_MIN_FACTS = 1
_MIN_CONFIDENCE_SCORE = 40


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _conf_score(fact: Mapping[str, Any]) -> int:
    conf = fact.get("confidence") if isinstance(fact.get("confidence"), Mapping) else {}
    try:
        return int(conf.get("score") or 0)
    except (TypeError, ValueError):
        level = _norm(conf.get("level")).lower()
        return {"high": 80, "medium": 55, "low": 30}.get(level, 0)


def _classify_fact_theme_type_v1(fact: Mapping[str, Any]) -> Optional[str]:
    """Map a Business Fact into exactly one theme bucket."""
    ft = _norm(fact.get("fact_type"))
    meaning = _norm(fact.get("business_meaning_ar"))
    evid = fact.get("evidence") if isinstance(fact.get("evidence"), Mapping) else {}
    caps = [str(c) for c in list(evid.get("capability_ids") or [])]

    if "shipping_stronger_than_price" in caps or "الشحن" in meaning:
        return THEME_SHIPPING_FRICTION
    if "repeated_return_without_purchase" in caps or "يعودون" in meaning:
        return THEME_CUSTOMER_RETURN_BEHAVIOUR
    if ft == FACT_TYPE_CONVERSION or "high_interest_low_conversion" in caps:
        return THEME_PRODUCT_CONVERSION
    if ft == FACT_TYPE_PRODUCT_DEMAND:
        return THEME_PRODUCT_DEMAND
    if ft == FACT_TYPE_RECOVERY:
        return THEME_RECOVERY_OPPORTUNITY
    if ft == FACT_TYPE_COMMUNICATION:
        return THEME_COMMUNICATION_COVERAGE
    if ft == FACT_TYPE_STORE_HEALTH:
        return THEME_STORE_HEALTH
    if ft == FACT_TYPE_CUSTOMER_BEHAVIOUR:
        return THEME_CUSTOMER_RETURN_BEHAVIOUR
    return None


def _priority_for_theme_type(theme_type: str, fact_count: int, score: int) -> int:
    base = {
        THEME_PRODUCT_CONVERSION: 90,
        THEME_SHIPPING_FRICTION: 85,
        THEME_RECOVERY_OPPORTUNITY: 80,
        THEME_CUSTOMER_RETURN_BEHAVIOUR: 75,
        THEME_PRODUCT_DEMAND: 70,
        THEME_COMMUNICATION_COVERAGE: 60,
        THEME_STORE_HEALTH: 50,
    }.get(theme_type, 40)
    return min(99, base + min(8, fact_count) + (5 if score >= 70 else 0))


def _summary_for_bucket(
    theme_type: str, facts: list[Mapping[str, Any]]
) -> tuple[str, str, str]:
    """Return (summary_ar, summary_en, subject_name_ar)."""
    # Lead with strongest-confidence product fact when present.
    product_facts = [
        f
        for f in facts
        if isinstance(f.get("subject"), Mapping)
        and (f.get("subject") or {}).get("kind") == "product"
    ]
    product_facts.sort(key=_conf_score, reverse=True)
    lead = product_facts[0] if product_facts else facts[0]
    lead_meaning = _norm(lead.get("business_meaning_ar"))
    subject = ""
    if isinstance(lead.get("subject"), Mapping):
        subject = _norm((lead.get("subject") or {}).get("name_ar"))

    if theme_type == THEME_PRODUCT_CONVERSION:
        if subject:
            return (
                f"تحويل {subject} ضعيف رغم اهتمام واضح — هذه أولوية تجارية اليوم.",
                f"Conversion for {subject} is weak despite clear interest.",
                subject,
            )
        return (
            "تحويل المنتجات ضعيف رغم الاهتمام — يستحق قراراً اليوم.",
            "Product conversion is weak despite interest.",
            subject,
        )
    if theme_type == THEME_SHIPPING_FRICTION:
        if subject:
            return (
                f"الشحن يبدو أنه يضعف إتمام الشراء لـ {subject}.",
                f"Shipping appears to reduce conversion for {subject}.",
                subject,
            )
        return (
            "الشحن يبدو أنه يضعف إتمام الشراء في المتجر.",
            "Shipping appears to reduce store conversion.",
            subject,
        )
    if theme_type == THEME_CUSTOMER_RETURN_BEHAVIOUR:
        if subject:
            return (
                f"العملاء يعودون مراراً إلى {subject} دون الإتمام.",
                f"Customers repeatedly return to {subject} without completing purchase.",
                subject,
            )
        return (
            "سلوك عودة العملاء يشير إلى تردد قبل الشراء.",
            "Return behaviour indicates hesitation before purchase.",
            subject,
        )
    if theme_type == THEME_RECOVERY_OPPORTUNITY:
        return (
            lead_meaning or "فرص استعادة المبيعات محدودة حالياً.",
            "Recovery opportunities are currently limited.",
            "المتجر",
        )
    if theme_type == THEME_COMMUNICATION_COVERAGE:
        return (
            lead_meaning or "تغطية التواصل مع العملاء تحتاج انتباهاً.",
            "Customer communication coverage needs attention.",
            "المتجر",
        )
    if theme_type == THEME_STORE_HEALTH:
        return (
            lead_meaning or "لا توجد مشكلات تجارية حرجة ظاهرة.",
            "No critical business issues detected.",
            "المتجر",
        )
    if theme_type == THEME_PRODUCT_DEMAND:
        return (
            lead_meaning or "طلب المنتجات يظهر إشارات تستحق المتابعة.",
            "Product demand shows signals worth watching.",
            subject or "المتجر",
        )
    return (lead_meaning, lead_meaning, subject or "المتجر")


def _admit_theme_v1(theme: dict[str, Any]) -> dict[str, Any]:
    """
    Publish only when evidence, confidence, impact, and merchant action exist.
    Otherwise keep internal.
    """
    fact_count = int((theme.get("evidence") or {}).get("fact_count") or 0)
    score = 0
    conf = theme.get("confidence") if isinstance(theme.get("confidence"), Mapping) else {}
    try:
        score = int(conf.get("score") or 0)
    except (TypeError, ValueError):
        score = 0
    impact = theme.get("business_impact") if isinstance(theme.get("business_impact"), Mapping) else {}
    has_impact = bool(_norm(impact.get("category")) or _norm(impact.get("ar")))
    action = bool(theme.get("merchant_action_exists"))
    owner = _norm(theme.get("primary_owner"))

    # Store-health / healthy communication may publish as Home teasers without a Workspace decision.
    soft_action = owner in (OWNER_HOME, OWNER_COMMUNICATION) and theme.get(
        "theme_type"
    ) in (THEME_STORE_HEALTH, THEME_COMMUNICATION_COVERAGE)

    ok = (
        fact_count >= _MIN_FACTS
        and score >= _MIN_CONFIDENCE_SCORE
        and has_impact
        and (action or soft_action)
    )
    theme["admitted"] = bool(ok)
    theme["internal_only"] = not bool(ok)
    if ok:
        dest = theme.get("destination_surfaces")
        if not isinstance(dest, dict):
            dest = {}
        if owner == OWNER_DECISION_WORKSPACE:
            dest["decision_workspace"] = True
            dest["home_teaser"] = True
        elif owner == OWNER_HOME:
            dest["home_teaser"] = True
        elif owner == OWNER_COMMUNICATION:
            dest["communication"] = True
            dest["home_teaser"] = True
        theme["destination_surfaces"] = dest
    return theme


def compose_business_themes_v1(
    facts_package: Mapping[str, Any] | None,
    *,
    store_slug: str = "",
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Collapse many facts into a small set of canonical themes (one per type)."""
    slug = _norm(store_slug) or _norm(
        (facts_package or {}).get("store_slug") if isinstance(facts_package, Mapping) else ""
    )
    if not business_themes_v1_enabled(environ=environ):
        return {
            "ok": False,
            "enabled": False,
            "schema": BUSINESS_THEMES_VERSION_V1,
            "store_slug": slug,
            "themes": [],
            "published_themes": [],
            "counts": {"facts_in": 0, "themes": 0, "published": 0},
        }

    facts = [
        f
        for f in list((facts_package or {}).get("facts") or [])
        if isinstance(f, Mapping)
    ]
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    for fact in facts:
        tt = _classify_fact_theme_type_v1(fact)
        if not tt:
            continue
        buckets.setdefault(tt, []).append(fact)

    themes: list[dict[str, Any]] = []
    for theme_type, bucket in buckets.items():
        # ONE theme per type — never five product conversion themes.
        scores = [_conf_score(f) for f in bucket]
        avg = int(sum(scores) / max(1, len(scores)))
        summary_ar, summary_en, subject = _summary_for_bucket(theme_type, bucket)
        caps: list[str] = []
        for f in bucket:
            evid = f.get("evidence") if isinstance(f.get("evidence"), Mapping) else {}
            for c in list(evid.get("capability_ids") or []):
                if str(c) not in caps:
                    caps.append(str(c))
        owner = THEME_PRIMARY_OWNER_V1.get(theme_type, OWNER_DECISION_WORKSPACE)
        action = owner == OWNER_DECISION_WORKSPACE
        impact_cat = _norm((bucket[0].get("impact_category") if bucket else "") or "")
        theme = empty_theme_shell_v1()
        theme.update(
            {
                "theme_id": f"bt:{theme_type}:{slug or 'store'}",
                "theme_type": theme_type,
                "title_ar": THEME_TITLE_AR_V1.get(theme_type, theme_type),
                "title_en": theme_type.replace("_", " ").title(),
                "executive_summary_ar": summary_ar,
                "executive_summary_en": summary_en,
                "subject_name_ar": subject,
                "supporting_fact_ids": [
                    _norm(f.get("fact_id")) for f in bucket if _norm(f.get("fact_id"))
                ],
                "supporting_facts": [
                    {
                        "fact_id": f.get("fact_id"),
                        "fact_type": f.get("fact_type"),
                        "business_meaning_ar": f.get("business_meaning_ar"),
                        "subject_name_ar": (
                            (f.get("subject") or {}).get("name_ar")
                            if isinstance(f.get("subject"), Mapping)
                            else ""
                        ),
                    }
                    for f in bucket
                ],
                "evidence": {
                    "source_kinds": ["business_facts_v1"],
                    "fact_count": len(bucket),
                    "capability_ids": caps,
                },
                "confidence": {
                    "level": "high" if avg >= 70 else ("medium" if avg >= 45 else "low"),
                    "ar": "مرتفع" if avg >= 70 else ("متوسط" if avg >= 45 else "منخفض"),
                    "score": avg,
                },
                "business_impact": {
                    "category": impact_cat or theme_type,
                    "ar": summary_ar,
                },
                "freshness": {"status": "current", "as_of_utc": _utc_now()},
                "priority": _priority_for_theme_type(theme_type, len(bucket), avg),
                "primary_owner": owner,
                "destination_surfaces": {
                    "home_teaser": False,
                    "decision_workspace": False,
                    "communication": False,
                },
                "merchant_action_exists": action,
                "recommendation": None,
            }
        )
        theme = _admit_theme_v1(theme)
        if validate_business_theme_v1(theme):
            continue
        themes.append(theme)

    themes.sort(key=lambda t: (-int(t.get("priority") or 0), str(t.get("theme_id"))))
    published = [t for t in themes if t.get("admitted")]
    return {
        "ok": True,
        "enabled": True,
        "schema": BUSINESS_THEMES_VERSION_V1,
        "version": BUSINESS_THEMES_VERSION_V1,
        "store_slug": slug,
        "constitution": "one_theme_one_owner_many_consumers",
        "themes": themes,
        "published_themes": published,
        "counts": {
            "facts_in": len(facts),
            "themes": len(themes),
            "published": len(published),
            "collapsed_ratio": (
                round(len(facts) / max(1, len(themes)), 2) if themes else 0
            ),
        },
        "recommendation": None,
        "product_intelligence": False,
        "composed_at_utc": _utc_now(),
    }


__all__ = ["compose_business_themes_v1"]
