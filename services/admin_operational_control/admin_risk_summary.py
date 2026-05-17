# -*- coding: utf-8 -*-
"""Part 1 — operational risk summary (top section) with severity tiers."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.admin_risk_severity import classify_operational_risk
from services.admin_operational_control.context import OperationalControlContext


def build_admin_risk_summary(ctx: OperationalControlContext) -> dict[str, Any]:
    severity = classify_operational_risk(ctx, ctx.issues)
    wa_fail = ctx.whatsapp_failed_24h

    return {
        "risk_detected": bool(severity.get("risk_detected")),
        "risk_level": int(severity.get("level", 0)),
        "actual_risk": bool(severity.get("actual_risk")),
        "potential_only": bool(severity.get("potential_only")),
        "status": severity.get("status", "healthy"),
        "status_emoji": severity.get("status_emoji", "🟢"),
        "status_label_ar": severity.get("status_label_ar", "سليم"),
        "headline_ar": severity.get("headline_ar", "لا يوجد خطر تشغيلي"),
        "subheadline_ar": severity.get("subheadline_ar", ""),
        "active_issue_count": len([i for i in ctx.issues if i.active]),
        "failure_categories": severity.get("failure_categories") or [],
        "metrics": {
            "affected_stores": int(severity.get("affected_stores_display") or 0),
            "whatsapp_failed_24h": wa_fail if wa_fail is not None else "—",
            "queuepool_timeout_count": ctx.pool_timeout_count,
            "slow_cart_events_count": ctx.slow_cart_event_count,
            "provider_unstable": ctx.provider_unstable,
            "background_task_failures": ctx.background_failure_count,
        },
        "metrics_labels_ar": {
            "affected_stores": "متاجر متأثرة (فعلي)",
            "whatsapp_failed_24h": "فشل واتساب (24 ساعة)",
            "queuepool_timeout_count": "انتهاء مهلة QueuePool",
            "slow_cart_events_count": "cart-event بطيء",
            "provider_unstable": "إشارة عدم استقرار المزود",
            "background_task_failures": "فشل مهام خلفية",
        },
    }
