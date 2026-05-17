# -*- coding: utf-8 -*-
"""Part 1 — operational risk summary (top section)."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.context import OperationalControlContext


def build_admin_risk_summary(ctx: OperationalControlContext) -> dict[str, Any]:
    active = [i for i in ctx.issues if i.active]
    risk_detected = len(active) > 0

    if not risk_detected:
        headline_ar = "لا يوجد خطر تشغيلي حالياً"
        status = "ok"
        status_emoji = "🟢"
        status_label_ar = "لا خطر فوري"
    else:
        n = max(ctx.affected_stores_estimate, max((i.affected_stores for i in active), default=0))
        if n <= 1:
            headline_ar = "قد تتأثر عمليات الاسترداد لدى متجر واحد"
        else:
            headline_ar = f"قد تتأثر عمليات الاسترداد لدى {n} متاجر"
        status = "risk"
        status_emoji = "🔴"
        status_label_ar = "خطر تشغيلي"

    wa_fail = ctx.whatsapp_failed_24h
    return {
        "risk_detected": risk_detected,
        "status": status,
        "status_emoji": status_emoji,
        "status_label_ar": status_label_ar,
        "headline_ar": headline_ar,
        "active_issue_count": len(active),
        "metrics": {
            "affected_stores": ctx.affected_stores_estimate,
            "whatsapp_failed_24h": wa_fail if wa_fail is not None else "—",
            "queuepool_timeout_count": ctx.pool_timeout_count,
            "slow_cart_events_count": ctx.slow_cart_event_count,
            "provider_unstable": ctx.provider_unstable,
            "background_task_failures": ctx.background_failure_count,
        },
        "metrics_labels_ar": {
            "affected_stores": "متاجر متأثرة (تقدير)",
            "whatsapp_failed_24h": "فشل واتساب (24 ساعة)",
            "queuepool_timeout_count": "انتهاء مهلة QueuePool",
            "slow_cart_events_count": "cart-event بطيء",
            "provider_unstable": "عدم استقرار المزود",
            "background_task_failures": "فشل مهام خلفية",
        },
    }
