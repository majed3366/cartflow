# -*- coding: utf-8 -*-
"""Part 5 — revenue protection estimates (read-only, no new heavy queries)."""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.context import OperationalControlContext


def build_admin_revenue_protection(ctx: OperationalControlContext) -> dict[str, Any]:
    summary = ctx.admin_summary
    agg = summary.get("aggregate_onboarding") or {}
    trust_ready = int((agg.get("trust_bucket_counts") or {}).get("operationally_ready", 0) or 0)
    if not trust_ready:
        buckets = agg.get("trust_bucket_counts") or {}
        trust_ready = int(buckets.get("operationally_ready", 0) or 0)

    scanned = int(summary.get("stores_scanned_for_trust") or 0)
    stores_healthy = trust_ready if trust_ready > 0 else max(0, scanned - ctx.affected_stores_estimate)

    wa_fail = ctx.whatsapp_failed_24h
    blocked = int(ctx.background_failure_count or 0)
    dup_blocked = False
    deg = summary.get("degradation_flags") or {}
    if deg.get("duplicate_guard_pressure"):
        blocked = max(blocked, 1)
        dup_blocked = True

    ano = summary.get("anomaly_visibility") or {}
    lc_ct = ano.get("lifecycle_counters") if isinstance(ano.get("lifecycle_counters"), dict) else {}
    sends_hint = None
    for key in ("send_success", "sent_real", "mock_sent", "queued"):
        if key in lc_ct:
            try:
                sends_hint = int(lc_ct.get(key) or 0)
                break
            except (TypeError, ValueError):
                pass

    protected_lines = [
        {
            "label_ar": "متاجر بمسار مستقر (تقدير)",
            "value": stores_healthy if stores_healthy else "—",
        },
        {
            "label_ar": "عمليات الاسترداد المستقرة اليوم",
            "value": sends_hint if sends_hint is not None else "—",
        },
        {
            "label_ar": "إرسالات ناجحة (عداد دورة حياة)",
            "value": sends_hint if sends_hint is not None else "—",
        },
    ]

    risk_lines = [
        {
            "label_ar": "رسائل فشلت (24 ساعة)",
            "value": wa_fail if wa_fail is not None else "—",
        },
        {
            "label_ar": "استردادات معطّلة أو معلّقة (إشارة)",
            "value": blocked if blocked else (1 if dup_blocked else 0),
        },
    ]

    stable_ar = (
        f"عمليات الاسترداد المستقرة اليوم: {sends_hint}"
        if sends_hint is not None
        else "عمليات الاسترداد المستقرة اليوم: — (غير متاح في هذه العملية)"
    )
    fail_ar = (
        f"رسائل فشلت: {wa_fail}"
        if wa_fail is not None
        else "رسائل فشلت: —"
    )

    return {
        "protected": protected_lines,
        "risk": risk_lines,
        "summary_stable_ar": stable_ar,
        "summary_fail_ar": fail_ar,
        "headline_ar": "حماية الإيراد — قراءة تقديرية وليست محاسبة مالية",
    }
