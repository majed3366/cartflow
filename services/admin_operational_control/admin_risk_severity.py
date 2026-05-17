# -*- coding: utf-8 -*-
"""
Operational risk severity tiers — display/classification only.

Levels:
  0 healthy | 1 warning (potential) | 2 actual risk | 3 critical
"""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.context import OperationalControlContext, OperationalIssue

LEVEL_HEALTHY = 0
LEVEL_WARNING = 1
LEVEL_ACTUAL = 2
LEVEL_CRITICAL = 3

_TIER_POTENTIAL = "potential"
_TIER_ACTUAL = "actual"

_LEVEL_META: dict[int, dict[str, str]] = {
    LEVEL_HEALTHY: {
        "status": "healthy",
        "status_emoji": "🟢",
        "status_label_ar": "سليم",
        "headline_ar": "لا يوجد خطر تشغيلي",
        "subheadline_ar": "",
    },
    LEVEL_WARNING: {
        "status": "warning",
        "status_emoji": "🟡",
        "status_label_ar": "تحذير",
        "headline_ar": "يوجد تحذير يحتاج مراجعة",
        "subheadline_ar": "لا يوجد أثر حالي على عمليات الاسترداد",
    },
    LEVEL_ACTUAL: {
        "status": "actual",
        "status_emoji": "🔴",
        "status_label_ar": "خطر فعلي",
        "headline_ar": "قد تتأثر عمليات الاسترداد",
        "subheadline_ar": "",
    },
    LEVEL_CRITICAL: {
        "status": "critical",
        "status_emoji": "🚨",
        "status_label_ar": "أزمة تشغيل",
        "headline_ar": "خطر مرتفع — قد تتوقف أجزاء من النظام",
        "subheadline_ar": "",
    },
}

_IMPACT_NONE_AR = "لا يوجد أثر حالي"


def impact_text_for_issue(issue: OperationalIssue) -> str:
    if issue.tier == _TIER_POTENTIAL or issue.affected_stores <= 0:
        return _IMPACT_NONE_AR
    return issue.impact_ar


def _actual_failure_categories(ctx: OperationalControlContext) -> set[str]:
    cats: set[str] = set()
    if (ctx.whatsapp_failed_24h or 0) > 0:
        cats.add("whatsapp")
    if ctx.pool_timeout_count > 0:
        cats.add("queue")
    if ctx.slow_cart_event_count > 0:
        cats.add("cart_event")
    if ctx.background_failure_count > 0:
        cats.add("background")
    if not bool(ctx.admin_rt.get("recovery_runtime_ok")):
        cats.add("recovery")
    return cats


def _actual_affected_stores(issues: list[OperationalIssue]) -> int:
    actual = [i.affected_stores for i in issues if i.tier == _TIER_ACTUAL and i.affected_stores > 0]
    return max(actual, default=0)


def classify_operational_risk(
    ctx: OperationalControlContext,
    issues: list[OperationalIssue],
) -> dict[str, Any]:
    """
    Map issues + metrics to severity level 0–3.
    Does not change upstream health signals.
    """
    active = [i for i in issues if i.active]
    potential = [i for i in active if i.tier == _TIER_POTENTIAL]
    actual_issues = [i for i in active if i.tier == _TIER_ACTUAL]

    cats = _actual_failure_categories(ctx)
    for i in actual_issues:
        if i.code in ("whatsapp_failure", "provider_instability"):
            cats.add("whatsapp")
        elif i.code == "db_pool_timeout":
            cats.add("queue")
        elif i.code == "cart_event_slow":
            cats.add("cart_event")
        elif i.code == "background_task_failure":
            cats.add("background")
        elif i.code == "recovery_runtime_down":
            cats.add("recovery")

    wa_fail = int(ctx.whatsapp_failed_24h or 0)
    affected = _actual_affected_stores(active)

    has_actual_signal = bool(cats) or bool(actual_issues)
    has_potential_only = bool(potential) and not has_actual_signal

    pressure = (
        ctx.pool_timeout_count > 0
        or ctx.slow_cart_event_count > 0
        or ctx.background_failure_count > 0
    )

    # Level 0 — clean
    if (
        not active
        and not has_actual_signal
        and wa_fail == 0
        and not pressure
        and not ctx.provider_unstable
    ):
        meta = dict(_LEVEL_META[LEVEL_HEALTHY])
        return {
            "level": LEVEL_HEALTHY,
            "risk_detected": False,
            "actual_risk": False,
            "potential_only": False,
            "affected_stores_display": 0,
            **meta,
        }

    # Level 3 — critical
    critical = (
        len(cats) >= 2
        or affected >= 3
        or (ctx.pool_timeout_count > 0 and wa_fail > 0)
        or (ctx.pool_timeout_count > 0 and not bool(ctx.admin_rt.get("recovery_runtime_ok")))
        or (wa_fail >= 5)
    )
    if critical:
        meta = dict(_LEVEL_META[LEVEL_CRITICAL])
        if affected > 0:
            meta["subheadline_ar"] = f"متاجر متأثرة (تقدير): {affected}"
        return {
            "level": LEVEL_CRITICAL,
            "risk_detected": True,
            "actual_risk": True,
            "potential_only": False,
            "affected_stores_display": affected,
            "failure_categories": sorted(cats),
            **meta,
        }

    # Level 2 — actual risk
    if has_actual_signal or affected > 0 or wa_fail > 0 or pressure:
        meta = dict(_LEVEL_META[LEVEL_ACTUAL])
        if affected <= 0 and wa_fail > 0:
            meta["subheadline_ar"] = f"فشل إرسال مسجّل (24 ساعة): {wa_fail}"
        elif affected == 1:
            meta["subheadline_ar"] = "متجر واحد متأثر (تقدير)"
        elif affected > 1:
            meta["subheadline_ar"] = f"{affected} متاجر متأثرة (تقدير)"
        elif ctx.pool_timeout_count > 0:
            meta["subheadline_ar"] = "ضغط على مسبح قاعدة البيانات"
        elif ctx.slow_cart_event_count > 0:
            meta["subheadline_ar"] = "بطء في مسار cart-event"
        return {
            "level": LEVEL_ACTUAL,
            "risk_detected": True,
            "actual_risk": True,
            "potential_only": False,
            "affected_stores_display": affected,
            "failure_categories": sorted(cats),
            **meta,
        }

    # Level 1 — warning (potential only)
    meta = dict(_LEVEL_META[LEVEL_WARNING])
    return {
        "level": LEVEL_WARNING,
        "risk_detected": True,
        "actual_risk": False,
        "potential_only": True,
        "affected_stores_display": 0,
        "failure_categories": [],
        **meta,
    }
