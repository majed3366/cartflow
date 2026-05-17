# -*- coding: utf-8 -*-
"""Part 2 — impact layer per detected issue."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.admin_risk_severity import impact_text_for_issue
from services.admin_operational_control.context import OperationalControlContext

_URGENCY_AR = {
    "low": "منخفض",
    "medium": "متوسط",
    "high": "عالي",
}


def build_admin_impact_layer(ctx: OperationalControlContext) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for issue in ctx.issues:
        if not issue.active:
            continue
        aff = issue.affected_stores
        if aff <= 0:
            affected_ar = "لا متاجر متأثرة حالياً"
        elif aff == 1:
            affected_ar = "متجر واحد"
        else:
            affected_ar = f"{aff} متجر"
        impact_ar = impact_text_for_issue(issue)
        items.append(
            {
                "code": issue.code,
                "tier": issue.tier,
                "problem_ar": issue.problem_ar,
                "impact_ar": impact_ar,
                "if_ignored_ar": issue.if_ignored_ar,
                "affected_ar": affected_ar,
                "affected_stores": aff,
                "urgency": issue.urgency,
                "urgency_ar": _URGENCY_AR.get(issue.urgency, issue.urgency),
            }
        )
    return {
        "has_issues": bool(items),
        "items": items,
        "empty_message_ar": "لا مشاكل نشطة — الأثر التشغيلي منخفض",
    }
