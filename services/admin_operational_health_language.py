# -*- coding: utf-8 -*-
"""
Operations-first decision format for admin operational health cards.

Fixed field order (Layer 1); raw metrics in ``technical_detail_lines`` (Layer 2).
Presentation only — no runtime/recovery/API changes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Fixed operational decision order (labels) for every card
DECISION_FIELD_LABELS_AR: List[tuple[str, str]] = [
    ("status", "الحالة"),
    ("risk_level", "هل يوجد خطر؟"),
    ("customer_impact", "هل يؤثر على العملاء؟"),
    ("merchant_impact", "هل يؤثر على المتاجر؟"),
    ("intervention", "هل يحتاج تدخل؟"),
    ("suggested_action", "الإجراء المقترح"),
    ("last_success", "آخر نجاح"),
    ("last_problem", "آخر مشكلة"),
]

_STATUS_TIER_AR = {
    "ok": ("🟢", "يعمل طبيعي"),
    "watch": ("🟡", "يحتاج متابعة"),
    "action": ("🔴", "يحتاج تدخل"),
}

_RISK_LEVEL_AR = {
    "none": "لا يوجد",
    "low": "منخفض",
    "medium": "متوسط",
    "high": "مرتفع",
}

_INTERVENTION_AR = {
    "no": "لا",
    "watch": "يفضل المراقبة",
    "required": "مطلوب تدخل",
}

# Operational card titles (Layer 1) — engineering names only in technical lines
TITLE_DELAYED_RECOVERY_AR = "متابعة الاسترجاعات المجدولة"
TITLE_CUSTOMER_ACTIVITY_AR = "متابعة نشاط العملاء"
TITLE_INTERNAL_HEALTH_AR = "صحة النظام الداخلية"
TITLE_AUTO_RECOVERY_AR = "عمليات الاسترجاع التلقائي"
TITLE_CUSTOMER_COMMS_AR = "التواصل مع العملاء"

_NO_RECENT_PROBLEMS_AR = "لا توجد مشاكل حديثة"


def build_standard_operational_decision(
    *,
    title_ar: str,
    status_tier: str,
    risk_level: str,
    customer_impact_ar: str,
    merchant_impact_ar: str,
    intervention: str,
    suggested_action_ar: str,
    last_success_ar: str,
    last_problem_ar: str = _NO_RECENT_PROBLEMS_AR,
) -> Dict[str, Any]:
    """
    Standard Layer 1 decision block for one operational health card.

    status_tier: ok | watch | action
    risk_level: none | low | medium | high
    intervention: no | watch | required
    """
    emoji, status_label = _STATUS_TIER_AR.get(status_tier, _STATUS_TIER_AR["watch"])
    values: Dict[str, str] = {
        "status": f"{emoji} {status_label}",
        "risk_level": _RISK_LEVEL_AR.get(risk_level, risk_level),
        "customer_impact": customer_impact_ar,
        "merchant_impact": merchant_impact_ar,
        "intervention": _INTERVENTION_AR.get(intervention, intervention),
        "suggested_action": suggested_action_ar,
        "last_success": last_success_ar or "—",
        "last_problem": last_problem_ar or _NO_RECENT_PROBLEMS_AR,
    }
    rows = [
        {"key": key, "label_ar": label, "value_ar": values[key]}
        for key, label in DECISION_FIELD_LABELS_AR
    ]
    return {
        "title_ar": title_ar,
        "rows": rows,
        "status_line_ar": values["status"],
        "status_emoji": emoji,
        "status_label_ar": status_label,
        "risk_level_ar": values["risk_level"],
        "customer_impact_ar": values["customer_impact"],
        "merchant_impact_ar": values["merchant_impact"],
        "intervention_ar": values["intervention"],
        "suggested_action_ar": values["suggested_action"],
        "last_success_ar": values["last_success"],
        "last_problem_ar": values["last_problem"],
        # Legacy aliases used by tests / older template paths
        "has_risk_ar": values["risk_level"],
        "needs_intervention_ar": values["intervention"],
    }


def _attach_operational(
    card: Dict[str, Any],
    *,
    title_ar: str,
    operational: Dict[str, Any],
    technical_lines: List[str],
    technical_title: str,
) -> Dict[str, Any]:
    out = dict(card)
    out["title_ar"] = title_ar
    out["title"] = technical_title
    out["operational"] = operational
    out["technical_detail_lines"] = technical_lines
    out["detail_lines"] = technical_lines
    return out


def build_db_due_scanner_operational_layer(h: Dict[str, Any]) -> Dict[str, Any]:
    status = str(h.get("status") or "unknown")
    enabled = bool(h.get("enabled"))
    loop_running = bool(h.get("loop_running"))
    last_error = h.get("last_error")
    last_found = int(h.get("last_found") or 0)
    total_dispatches = int(h.get("total_dispatches") or 0)

    if not enabled:
        tier, risk, intervention = "watch", "low", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل — المتابعة التلقائية غير مفعّلة"
        last_success = "لا متابعة تلقائية نشطة حالياً"
        last_problem = _NO_RECENT_PROBLEMS_AR
    elif last_error:
        tier, risk, intervention = "action", "high", "required"
        customer = "قد تتأخر الاسترجاعات"
        merchant = "قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من التفاصيل التقنية أو تواصل مع الدعم"
        ago = h.get("last_dispatch_ago")
        last_success = f"آخر معالجة ناجحة {ago}" if ago and total_dispatches else "—"
        last_problem = f"آخر مشكلة مسجّلة — راجع التفاصيل التقنية"
    elif enabled and not loop_running:
        tier, risk, intervention = "action", "medium", "required"
        customer = "قد تتأخر الاسترجاعات"
        merchant = "قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من استمرار المتابعة بعد إعادة التشغيل"
        last_success = (
            f"آخر معالجة ناجحة {h.get('last_dispatch_ago')}"
            if total_dispatches and h.get("last_dispatch_ago")
            else "—"
        )
        last_problem = "المتابعة التلقائية متوقفة"
    elif last_found > 0:
        tier, risk, intervention = "watch", "low", "watch"
        customer = "لا"
        merchant = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        last_success = (
            f"آخر معالجة ناجحة {h.get('last_dispatch_ago')}"
            if h.get("last_dispatch_ago")
            else "—"
        )
        last_problem = _NO_RECENT_PROBLEMS_AR
    else:
        tier, risk, intervention = "ok", "none", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل"
        if total_dispatches and h.get("last_dispatch_ago"):
            last_success = f"آخر معالجة ناجحة {h.get('last_dispatch_ago')}"
        elif loop_running:
            last_success = "المتابعة تعمل — لا مشاكل حديثة"
        else:
            last_success = "—"
        last_problem = _NO_RECENT_PROBLEMS_AR

    if status == "healthy" and tier == "ok":
        pass  # keep ok
    elif status == "idle" and tier == "ok":
        tier, risk = "watch", "low"

    return build_standard_operational_decision(
        title_ar=TITLE_DELAYED_RECOVERY_AR,
        status_tier=tier,
        risk_level=risk,
        customer_impact_ar=customer,
        merchant_impact_ar=merchant,
        intervention=intervention,
        suggested_action_ar=action,
        last_success_ar=last_success,
        last_problem_ar=last_problem,
    )


def build_db_due_scanner_technical_lines(h: Dict[str, Any]) -> List[str]:
    return [
        f"DB Due Scanner — status: {h.get('status_emoji', '')} {h.get('status_label', '—')}",
        f"enabled: {str(h.get('enabled')).lower()}",
        f"interval_seconds: {int(h.get('interval_seconds') or 0)}",
        f"loop_running: {str(h.get('loop_running')).lower()}",
        f"last_tick_at: {h.get('last_tick_at') or '—'} ({h.get('last_tick_ago') or '—'})",
        f"last_dispatch_at: {h.get('last_dispatch_at') or '—'} ({h.get('last_dispatch_ago') or '—'})",
        f"found: {h.get('last_found')}",
        f"dispatched: {h.get('last_dispatched')}",
        f"skipped: {h.get('last_skipped')}",
        f"total_ticks: {h.get('total_ticks')} | total_dispatches: {h.get('total_dispatches')}",
        f"last_error: {h.get('last_error') or 'None'}",
        f"stale_running_repair: (via scanner tick)",
        "API: GET /api/admin/db-due-scanner-health",
    ]


def enrich_cart_event_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    slow = bool(card.get("slow_warning"))
    latest_ms = card.get("latest_duration_ms")

    if slow or status == "warn":
        tier, risk, intervention = "watch", "medium", "watch"
        customer = "قد لا تُسجل العمليات"
        merchant = "قد تقل الدقة"
        action = "يفضل المراقبة خلال 10 دقائق — راقب نشاط العملاء"
        last_problem = "بطء في تسجيل نشاط العملاء"
        last_success = "—"
    elif status == "unknown":
        tier, risk, intervention = "watch", "low", "watch"
        customer = "لا"
        merchant = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "لا نشاط مسجّل بعد في هذه الجلسة"
    else:
        tier, risk, intervention = "ok", "none", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "آخر نشاط مسجّل بنجاح"

    op = build_standard_operational_decision(
        title_ar=TITLE_CUSTOMER_ACTIVITY_AR,
        status_tier=tier,
        risk_level=risk,
        customer_impact_ar=customer,
        merchant_impact_ar=merchant,
        intervention=intervention,
        suggested_action_ar=action,
        last_success_ar=last_success,
        last_problem_ar=last_problem,
    )
    return _attach_operational(
        card,
        title_ar=TITLE_CUSTOMER_ACTIVITY_AR,
        operational=op,
        technical_title="cart_event",
        technical_lines=[
            "cart-event (POST /api/cart-event)",
            f"status: {status}",
            f"recent_count: {card.get('recent_count')}",
            f"avg_duration_ms: {card.get('avg_duration_ms')}",
            f"latest_duration_ms: {latest_ms}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_db_pool_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    timeout_n = int(card.get("timeout_count") or 0)
    status = str(card.get("status") or "unknown")

    if timeout_n > 0:
        tier, risk, intervention = "action", "high", "required"
        customer = "قد لا تُسجل العمليات"
        merchant = "قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من صحة النظام الداخلي (التفاصيل التقنية)"
        last_problem = f"ضغط على النظام الداخلي ({timeout_n} تنبيه)"
        last_success = "—"
    elif status == "unknown":
        tier, risk, intervention = "watch", "low", "watch"
        customer = "لا"
        merchant = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "—"
    else:
        tier, risk, intervention = "ok", "none", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "النظام الداخلي مستقر في هذه الجلسة"

    op = build_standard_operational_decision(
        title_ar=TITLE_INTERNAL_HEALTH_AR,
        status_tier=tier,
        risk_level=risk,
        customer_impact_ar=customer,
        merchant_impact_ar=merchant,
        intervention=intervention,
        suggested_action_ar=action,
        last_success_ar=last_success,
        last_problem_ar=last_problem,
    )
    return _attach_operational(
        card,
        title_ar=TITLE_INTERNAL_HEALTH_AR,
        operational=op,
        technical_title="db_pool",
        technical_lines=[
            "db_pool / QueuePool",
            f"timeout_count: {timeout_n}",
            f"pool_summary: {card.get('pool_summary_ar')}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_background_tasks_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    err_n = int(card.get("background_error_count") or 0)

    if status == "warn" or err_n > 0:
        tier, risk, intervention = "watch", "medium", "watch"
        customer = "قد تتأخر الرسائل"
        merchant = "قد تتأخر الاسترجاعات"
        action = "يفضل المراقبة خلال 10 دقائق — تحقق من عمليات الاسترجاع التلقائي"
        last_problem = f"تنبيهات تشغيل ({err_n})" if err_n else "الاسترجاع التلقائي يحتاج مراجعة"
        last_success = "آخر استرداد تم جدولته" if card.get("last_recovery_dispatch_ar") else "—"
    else:
        tier, risk, intervention = "ok", "none", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "آخر استرداد تم بنجاح — المسار نشط"

    op = build_standard_operational_decision(
        title_ar=TITLE_AUTO_RECOVERY_AR,
        status_tier=tier,
        risk_level=risk,
        customer_impact_ar=customer,
        merchant_impact_ar=merchant,
        intervention=intervention,
        suggested_action_ar=action,
        last_success_ar=last_success,
        last_problem_ar=last_problem,
    )
    return _attach_operational(
        card,
        title_ar=TITLE_AUTO_RECOVERY_AR,
        operational=op,
        technical_title="background_tasks",
        technical_lines=[
            "background_tasks / recovery_runtime",
            f"background_error_count: {err_n}",
            f"last_recovery_dispatch: {card.get('last_recovery_dispatch_ar')}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_whatsapp_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    configured = bool(card.get("configured"))
    fail_i = card.get("recent_failed_24h")
    fail_n = int(fail_i) if isinstance(fail_i, int) and fail_i >= 0 else 0
    failure_class = str(card.get("last_provider_failure_ar") or "").strip()

    if fail_n > 0:
        tier, risk, intervention = "action", "high", "required"
        customer = "قد تتأخر الرسائل"
        merchant = "قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من إعدادات التواصل مع العملاء"
        last_problem = f"فشل إرسال ({fail_n} خلال 24 ساعة)"
        last_success = "—"
    elif not configured:
        tier, risk, intervention = "watch", "medium", "watch"
        customer = "قد تتأخر الرسائل"
        merchant = "لا"
        action = "تحقق من إعدادات التواصل — الوضع تجريبي أو معطّل"
        last_problem = "قناة التواصل غير مُفعّلة بالكامل"
        last_success = "—"
    elif status == "warn":
        tier, risk, intervention = "watch", "medium", "watch"
        customer = "قد تتأخر الرسائل"
        merchant = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        last_problem = "تنبيه على قناة التواصل"
        last_success = "—"
    else:
        tier, risk, intervention = "ok", "none", "no"
        customer = "لا"
        merchant = "لا"
        action = "لا حاجة لأي تدخل"
        last_problem = _NO_RECENT_PROBLEMS_AR
        last_success = "آخر إرسال ناجح — لا فشل حديث"

    op = build_standard_operational_decision(
        title_ar=TITLE_CUSTOMER_COMMS_AR,
        status_tier=tier,
        risk_level=risk,
        customer_impact_ar=customer,
        merchant_impact_ar=merchant,
        intervention=intervention,
        suggested_action_ar=action,
        last_success_ar=last_success,
        last_problem_ar=last_problem,
    )
    return _attach_operational(
        card,
        title_ar=TITLE_CUSTOMER_COMMS_AR,
        operational=op,
        technical_title="whatsapp",
        technical_lines=[
            "whatsapp / provider",
            f"configured: {configured}",
            f"recent_failed_24h: {fail_i}",
            f"provider_failure_class: {failure_class or '—'}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_db_due_scanner_admin_card(card: Dict[str, Any]) -> Dict[str, Any]:
    h = {k: v for k, v in card.items() if k not in ("operational", "technical_detail_lines", "detail_lines")}
    op = build_db_due_scanner_operational_layer(h)
    return _attach_operational(
        h,
        title_ar=TITLE_DELAYED_RECOVERY_AR,
        operational=op,
        technical_title="db_due_scanner",
        technical_lines=build_db_due_scanner_technical_lines(h),
    )


def enrich_operational_health_cards(cards: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(cards)
    if "cart_event" in out and isinstance(out["cart_event"], dict):
        out["cart_event"] = enrich_cart_event_card_operational(out["cart_event"])
    if "db_pool" in out and isinstance(out["db_pool"], dict):
        out["db_pool"] = enrich_db_pool_card_operational(out["db_pool"])
    if "background_tasks" in out and isinstance(out["background_tasks"], dict):
        out["background_tasks"] = enrich_background_tasks_card_operational(out["background_tasks"])
    if "whatsapp" in out and isinstance(out["whatsapp"], dict):
        out["whatsapp"] = enrich_whatsapp_card_operational(out["whatsapp"])
    if "db_due_scanner" in out and isinstance(out["db_due_scanner"], dict):
        out["db_due_scanner"] = enrich_db_due_scanner_admin_card(out["db_due_scanner"])
    return out


def operational_card_display_order() -> List[tuple[str, str]]:
    """Key and anchor id for template iteration."""
    return [
        ("db_due_scanner", "issue-db-due-scanner"),
        ("cart_event", "issue-cart-event"),
        ("db_pool", "issue-db-pool"),
        ("background_tasks", "issue-background-tasks"),
        ("whatsapp", "issue-whatsapp"),
    ]
