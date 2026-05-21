# -*- coding: utf-8 -*-
"""
CartFlow Operations Center — presentation layer for admin operational health.

Decision order: problem → impact → stores → customers → urgency → action → verify.
Technical metrics stay in ``technical_detail_lines`` only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Operations Center field order (Layer 1) — same on every component card
OPS_CENTER_FIELD_LABELS_AR: List[tuple[str, str]] = [
    ("problem", "المشكلة"),
    ("impact", "الأثر"),
    ("affected_stores", "المتاجر المتأثرة"),
    ("affected_customers", "العملاء المحتمل تأثرهم"),
    ("urgency", "درجة الإلحاح"),
    ("suggested_action", "الإجراء المقترح"),
    ("verification", "كيف نتحقق أن المشكلة انتهت؟"),
]

# Legacy alias for tests migrating from prior decision format
DECISION_FIELD_LABELS_AR = OPS_CENTER_FIELD_LABELS_AR

_URGENCY_AR = {
    "none": "لا إلحاح",
    "low": "منخفضة",
    "medium": "متوسطة",
    "high": "مرتفع",
}

TITLE_DELAYED_RECOVERY_AR = "متابعة الاسترجاعات المجدولة"
TITLE_CUSTOMER_ACTIVITY_AR = "متابعة نشاط العملاء"
TITLE_INTERNAL_HEALTH_AR = "صحة النظام الداخلية"
TITLE_AUTO_RECOVERY_AR = "عمليات الاسترجاع التلقائي"
TITLE_CUSTOMER_COMMS_AR = "التواصل مع العملاء"

_OK_PROBLEM_AR = "لا توجد مشكلة تؤثر على العملاء حالياً"
_OK_IMPACT_AR = "لا أثر ملحوظ على العملاء أو المتاجر"


def build_operations_center_presentation_context(control: Dict[str, Any]) -> Dict[str, Any]:
    """Read-only view of existing risk metrics for presentation estimates."""
    risk = control.get("admin_risk_summary") or {}
    metrics = risk.get("metrics") or {}
    rl = int(risk.get("risk_level") or 0)
    affected_stores = int(metrics.get("affected_stores") or 0)
    slow = int(metrics.get("slow_cart_events_count") or 0)
    wa_raw = metrics.get("whatsapp_failed_24h")
    wa_n = int(wa_raw) if isinstance(wa_raw, int) and wa_raw >= 0 else 0
    pool = int(metrics.get("queuepool_timeout_count") or 0)
    bg = int(metrics.get("background_task_failures") or 0)

    est_customers = slow * 4 + wa_n * 3 + pool * 8 + bg * 2
    if affected_stores > 0:
        est_customers = max(est_customers, affected_stores * 6)
    if rl >= 2 and est_customers < 8:
        est_customers = max(est_customers, 8)

    actions = control.get("admin_actions_layer") or {}
    action_items = actions.get("items") or []
    recommended = (
        str(action_items[0].get("recommended_action_ar") or "").strip()
        if action_items and isinstance(action_items[0], dict)
        else ""
    )
    qa = control.get("quick_answers") or {}
    if not recommended:
        recommended = str(qa.get("what_to_do_ar") or "مراقبة روتينية").strip()

    verify_items = (control.get("admin_verification_layer") or {}).get("items") or []
    verify_lines: List[str] = []
    for v in verify_items[:4]:
        if isinstance(v, dict) and v.get("headline_ar"):
            verify_lines.append(str(v["headline_ar"]))

    return {
        "risk_level": rl,
        "affected_stores_platform": affected_stores,
        "estimated_customers_platform": est_customers,
        "recommended_action_platform": recommended,
        "verification_lines_platform": verify_lines or [
            "عودة المؤشرات إلى الوضع الطبيعي في البطاقات أدناه",
            "لا تنبيهات جديدة خلال 10–15 دقيقة",
        ],
    }


def build_operations_center_page_summary(control: Dict[str, Any]) -> Dict[str, Any]:
    """Top-of-page operations banner (presentation only)."""
    pctx = build_operations_center_presentation_context(control)
    risk = control.get("admin_risk_summary") or {}
    rl = pctx["risk_level"]
    stores = pctx["affected_stores_platform"]
    customers = pctx["estimated_customers_platform"]

    if rl == 0:
        summary = "لا توجد مشاكل تؤثر على العملاء حالياً"
        customer_problem = "لا"
    elif rl == 1:
        summary = "تم اكتشاف تنبيهات محدودة — تتم المراقبة"
        customer_problem = "محتمل — مراقبة"
    elif stores <= 2 and stores > 0:
        summary = f"قد تتأثر بعض الرسائل في {stores} متجر"
        customer_problem = "نعم"
    elif rl >= 2:
        summary = "قد يتأثر تجربة العملاء — راجع البطاقات أدناه"
        customer_problem = "نعم"
    else:
        summary = "تم اكتشاف بطء محدود — تتم المراقبة"
        customer_problem = "محتمل"

    urgency = _URGENCY_AR.get(
        "high" if rl >= 3 else ("medium" if rl == 2 else ("low" if rl == 1 else "none")),
        "متوسطة",
    )

    return {
        "title_ar": "مركز عمليات CartFlow",
        "title_en": "CartFlow Operations Center",
        "summary_ar": summary,
        "customer_impacting_problem_ar": customer_problem,
        "affected_stores_ar": "لا" if stores <= 0 else f"{stores} متجر",
        "affected_customers_ar": "لا"
        if customers <= 0
        else (f"~{customers} عميل" if customers > 0 else "لا"),
        "urgency_ar": urgency,
        "recommended_action_ar": pctx["recommended_action_platform"],
        "verification_lines_ar": list(pctx["verification_lines_platform"]),
        "risk_headline_ar": str(risk.get("headline_ar") or ""),
        "risk_emoji": str(risk.get("status_emoji") or "🟢"),
    }


def _format_stores(count: int) -> str:
    if count <= 0:
        return "لا"
    if count == 1:
        return "متجر واحد"
    return f"{count} متاجر"


def _format_customers(count: int) -> str:
    if count <= 0:
        return "لا يوجد"
    return f"~{count} عميل"


def _card_affected_estimate(pctx: Dict[str, Any], risk_level: str) -> tuple[str, str]:
    """Presentation-only store/customer counts scoped to a component card."""
    if risk_level == "none":
        return "لا", "لا يوجد"
    platform_s = int(pctx.get("affected_stores_platform") or 0)
    platform_c = int(pctx.get("estimated_customers_platform") or 0)
    if risk_level == "low":
        s = min(platform_s, 1) if platform_s else 0
        c = min(platform_c, 6) if platform_c else 3
        return (_format_stores(s) if s else "لا", _format_customers(c))
    if risk_level == "medium":
        s = min(max(platform_s, 1), 3)
        c = max(int(platform_c * 0.45), 8) if platform_c else 8
        return (_format_stores(s), _format_customers(c))
    # high
    s = max(platform_s, 1)
    c = max(int(platform_c * 0.85), 12) if platform_c else 18
    return (_format_stores(s), _format_customers(c))


def build_operations_center_decision(
    *,
    title_ar: str,
    problem_ar: str,
    impact_ar: str,
    affected_stores_ar: str,
    affected_customers_ar: str,
    urgency_ar: str,
    suggested_action_ar: str,
    verification_lines: List[str],
    status_tier: str = "ok",
) -> Dict[str, Any]:
    """Layer 1 operations decision block for one component."""
    values: Dict[str, Any] = {
        "problem": problem_ar,
        "impact": impact_ar,
        "affected_stores": affected_stores_ar,
        "affected_customers": affected_customers_ar,
        "urgency": urgency_ar,
        "suggested_action": suggested_action_ar,
        "verification": verification_lines,
    }
    rows = [
        {
            "key": key,
            "label_ar": label,
            "value_ar": values[key] if key != "verification" else "",
            "verification_lines": verification_lines if key == "verification" else None,
        }
        for key, label in OPS_CENTER_FIELD_LABELS_AR
    ]
    emoji = {"ok": "🟢", "watch": "🟡", "action": "🔴"}.get(status_tier, "🟡")
    return {
        "title_ar": title_ar,
        "rows": rows,
        "verification_lines_ar": verification_lines,
        "status_line_ar": f"{emoji} {problem_ar[:48]}",
        "status_emoji": emoji,
        "problem_ar": problem_ar,
        "impact_ar": impact_ar,
        "urgency_ar": urgency_ar,
        "suggested_action_ar": suggested_action_ar,
        "has_risk_ar": urgency_ar if urgency_ar != "لا إلحاح" else "لا يوجد",
        "needs_intervention_ar": (
            "مطلوب تدخل"
            if urgency_ar == "مرتفع"
            else ("يفضل المراقبة" if urgency_ar in ("متوسطة", "منخفضة") else "لا")
        ),
    }


def build_standard_operational_decision(**kwargs: Any) -> Dict[str, Any]:
    """Backward-compatible wrapper — maps old kwargs to operations center shape."""
    risk = str(kwargs.get("risk_level") or "none")
    urgency = _URGENCY_AR.get(risk, "منخفضة")
    stores, customers = _card_affected_estimate(
        {
            "affected_stores_platform": 0,
            "estimated_customers_platform": 0,
        },
        risk,
    )
    if kwargs.get("merchant_impact_ar") == "لا" and risk == "none":
        stores, customers = "لا", "لا يوجد"
    return build_operations_center_decision(
        title_ar=str(kwargs.get("title_ar") or "—"),
        problem_ar=str(kwargs.get("last_problem_ar") or _OK_PROBLEM_AR),
        impact_ar=str(kwargs.get("customer_impact_ar") or _OK_IMPACT_AR),
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=urgency,
        suggested_action_ar=str(kwargs.get("suggested_action_ar") or "—"),
        verification_lines=[
            str(kwargs.get("last_success_ar") or "استقرار المؤشرات"),
            "لا تنبيهات جديدة",
        ],
        status_tier=str(kwargs.get("status_tier") or "ok"),
    )


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


def build_db_due_scanner_operational_layer(
    h: Dict[str, Any], pctx: Dict[str, Any]
) -> Dict[str, Any]:
    enabled = bool(h.get("enabled"))
    loop_running = bool(h.get("loop_running"))
    last_error = h.get("last_error")
    last_found = int(h.get("last_found") or 0)
    total_dispatches = int(h.get("total_dispatches") or 0)

    if not enabled:
        risk, tier = "low", "watch"
        problem = "المتابعة التلقائية للاسترجاعات غير مفعّلة"
        impact = "لا أثر مباشر — قد تتأخر الاسترجاعات عند التفعيل لاحقاً"
        action = "لا حاجة لأي تدخل — أو فعّل المتابعة عند الحاجة"
        verify = ["تفعيل المتابعة عند الحاجة", "عودة معالجة الاسترجاعات المجدولة"]
    elif last_error:
        risk, tier = "high", "action"
        problem = "قد تتأخر بعض عمليات الاسترجاع"
        impact = "قد تتأخر الرسائل لبعض العملاء"
        action = "مطلوب تدخل — تحقق من التفاصيل التقنية\nإذا استمر: تواصل مع الدعم"
        verify = [
            "عودة الاسترجاعات دون أخطاء",
            "انخفاض المهام المتأخرة",
            "نجاح آخر معالجة",
        ]
    elif enabled and not loop_running:
        risk, tier = "medium", "action"
        problem = "قد تتأخر بعض عمليات الاسترجاع"
        impact = "قد تتأخر الرسائل لبعض العملاء"
        action = "مطلوب تدخل — تحقق من استمرار المتابعة بعد إعادة التشغيل"
        verify = ["عودة المتابعة التلقائية", "معالجة المهام المجدولة"]
    elif last_found > 0:
        risk, tier = "medium", "watch"
        problem = "مهام استرجاع بانتظار المعالجة"
        impact = "قد تتأخر رسائل لبعض العملاء قريباً"
        action = "يفضل المراقبة خلال 10 دقائق\nإذا استمر: راجع التفاصيل التقنية"
        verify = ["انخفاض المهام المعلقة", "نجاح آخر معالجة"]
    else:
        risk, tier = "none", "ok"
        problem = _OK_PROBLEM_AR
        impact = _OK_IMPACT_AR
        action = "لا حاجة لأي تدخل"
        verify = ["استمرار المتابعة دون أخطاء", "لا مهام متأخرة جديدة"]

    stores, customers = _card_affected_estimate(pctx, risk)
    if risk == "none":
        stores, customers = "لا", "لا يوجد"

    return build_operations_center_decision(
        title_ar=TITLE_DELAYED_RECOVERY_AR,
        problem_ar=problem,
        impact_ar=impact,
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=_URGENCY_AR[risk],
        suggested_action_ar=action,
        verification_lines=verify,
        status_tier=tier,
    )


def build_db_due_scanner_technical_lines(h: Dict[str, Any]) -> List[str]:
    return [
        f"DB Due Scanner — status: {h.get('status_emoji', '')} {h.get('status_label', '—')}",
        f"enabled: {str(h.get('enabled')).lower()}",
        f"interval_seconds: {int(h.get('interval_seconds') or 0)}",
        f"loop_running: {str(h.get('loop_running')).lower()}",
        f"last_tick_at: {h.get('last_tick_at') or '—'} ({h.get('last_tick_ago') or '—'})",
        f"found: {h.get('last_found')}",
        f"dispatched: {h.get('last_dispatched')}",
        f"skipped: {h.get('last_skipped')}",
        f"total_dispatches: {h.get('total_dispatches')}",
        f"last_error: {h.get('last_error') or 'None'}",
        "API: GET /api/admin/db-due-scanner-health",
    ]


def enrich_cart_event_card_operational(
    card: Dict[str, Any], pctx: Dict[str, Any]
) -> Dict[str, Any]:
    slow = bool(card.get("slow_warning"))
    status = str(card.get("status") or "unknown")

    if slow or status == "warn":
        risk, tier = "medium", "watch"
        problem = "بطء في تسجيل نشاط العملاء"
        impact = "قد لا تُسجل العمليات — قد تقل الدقة"
        action = "يفضل المراقبة خلال 10 دقائق\nإذا استمر: تحقق من صحة النظام الداخلية"
        verify = ["عودة زمن التسجيل للطبيعي", "تسجيل العمليات دون تأخير"]
    elif status == "unknown":
        risk, tier = "low", "watch"
        problem = "لا بيانات كافية عن نشاط العملاء بعد"
        impact = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        verify = ["ظهور نشاط مسجّل بنجاح"]
    else:
        risk, tier = "none", "ok"
        problem = _OK_PROBLEM_AR
        impact = _OK_IMPACT_AR
        action = "لا حاجة لأي تدخل"
        verify = ["استمرار تسجيل النشاط بنجاح"]

    stores, customers = _card_affected_estimate(pctx, risk)
    op = build_operations_center_decision(
        title_ar=TITLE_CUSTOMER_ACTIVITY_AR,
        problem_ar=problem,
        impact_ar=impact,
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=_URGENCY_AR[risk],
        suggested_action_ar=action,
        verification_lines=verify,
        status_tier=tier,
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
            f"latest_duration_ms: {card.get('latest_duration_ms')}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_db_pool_card_operational(card: Dict[str, Any], pctx: Dict[str, Any]) -> Dict[str, Any]:
    timeout_n = int(card.get("timeout_count") or 0)
    status = str(card.get("status") or "unknown")

    if timeout_n > 0:
        risk, tier = "high", "action"
        problem = "ضغط على النظام الداخلي"
        impact = "قد لا تُسجل العمليات — قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من صحة النظام الداخلية (التفاصيل التقنية)"
        verify = ["اختفاء ضغط النظام الداخلي", "عودة تسجيل العمليات"]
    elif status == "unknown":
        risk, tier = "low", "watch"
        problem = "حالة النظام الداخلي غير واضحة"
        impact = "لا"
        action = "يفضل المراقبة خلال 10 دقائق"
        verify = ["ثبات مؤشرات النظام الداخلي"]
    else:
        risk, tier = "none", "ok"
        problem = _OK_PROBLEM_AR
        impact = _OK_IMPACT_AR
        action = "لا حاجة لأي تدخل"
        verify = ["استقرار النظام الداخلي"]

    stores, customers = _card_affected_estimate(pctx, risk)
    op = build_operations_center_decision(
        title_ar=TITLE_INTERNAL_HEALTH_AR,
        problem_ar=problem,
        impact_ar=impact,
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=_URGENCY_AR[risk],
        suggested_action_ar=action,
        verification_lines=verify,
        status_tier=tier,
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


def enrich_background_tasks_card_operational(
    card: Dict[str, Any], pctx: Dict[str, Any]
) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    err_n = int(card.get("background_error_count") or 0)

    if status == "warn" or err_n > 0:
        risk, tier = "medium", "watch"
        problem = "قد تتأخر بعض عمليات الاسترجاع"
        impact = "قد تتأخر الرسائل لبعض العملاء"
        action = "يفضل المراقبة خلال 10 دقائق — تحقق من عمليات الاسترجاع التلقائي"
        verify = ["عودة الاسترجاعات للجدولة", "نجاح آخر استرداد"]
    else:
        risk, tier = "none", "ok"
        problem = _OK_PROBLEM_AR
        impact = _OK_IMPACT_AR
        action = "لا حاجة لأي تدخل"
        verify = ["استمرار الاسترجاع التلقائي", "آخر استرداد تم بنجاح"]

    stores, customers = _card_affected_estimate(pctx, risk)
    op = build_operations_center_decision(
        title_ar=TITLE_AUTO_RECOVERY_AR,
        problem_ar=problem,
        impact_ar=impact,
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=_URGENCY_AR[risk],
        suggested_action_ar=action,
        verification_lines=verify,
        status_tier=tier,
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


def enrich_whatsapp_card_operational(card: Dict[str, Any], pctx: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    configured = bool(card.get("configured"))
    fail_i = card.get("recent_failed_24h")
    fail_n = int(fail_i) if isinstance(fail_i, int) and fail_i >= 0 else 0

    if fail_n > 0:
        risk, tier = "high", "action"
        problem = "فشل في إرسال رسائل لبعض العملاء"
        impact = "قد تتأخر الرسائل — قد تتأخر الاسترجاعات"
        action = "مطلوب تدخل — تحقق من إعدادات التواصل مع العملاء"
        verify = ["نجاح آخر إرسال", "انخفاض فشل الإرسال (24 ساعة)"]
    elif not configured:
        risk, tier = "medium", "watch"
        problem = "قناة التواصل مع العملاء غير مكتملة"
        impact = "قد تتأخر الرسائل"
        action = "تحقق من إعدادات التواصل — الوضع تجريبي أو معطّل"
        verify = ["تفعيل قناة التواصل", "نجاح إرسال تجريبي"]
    elif status == "warn":
        risk, tier = "medium", "watch"
        problem = "تنبيه على التواصل مع العملاء"
        impact = "قد تتأخر الرسائل"
        action = "يفضل المراقبة خلال 10 دقائق"
        verify = ["نجاح آخر إرسال", "لا فشل حديث"]
    else:
        risk, tier = "none", "ok"
        problem = _OK_PROBLEM_AR
        impact = _OK_IMPACT_AR
        action = "لا حاجة لأي تدخل"
        verify = ["نجاح آخر إرسال", "لا فشل حديث"]

    stores, customers = _card_affected_estimate(pctx, risk)
    op = build_operations_center_decision(
        title_ar=TITLE_CUSTOMER_COMMS_AR,
        problem_ar=problem,
        impact_ar=impact,
        affected_stores_ar=stores,
        affected_customers_ar=customers,
        urgency_ar=_URGENCY_AR[risk],
        suggested_action_ar=action,
        verification_lines=verify,
        status_tier=tier,
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
            f"provider_failure_class: {card.get('last_provider_failure_ar') or '—'}",
            *(card.get("detail_lines_ar") or []),
        ],
    )


def enrich_db_due_scanner_admin_card(
    card: Dict[str, Any], pctx: Dict[str, Any]
) -> Dict[str, Any]:
    h = {k: v for k, v in card.items() if k not in ("operational", "technical_detail_lines", "detail_lines")}
    op = build_db_due_scanner_operational_layer(h, pctx)
    return _attach_operational(
        h,
        title_ar=TITLE_DELAYED_RECOVERY_AR,
        operational=op,
        technical_title="db_due_scanner",
        technical_lines=build_db_due_scanner_technical_lines(h),
    )


def enrich_operational_health_cards(
    cards: Dict[str, Any],
    presentation_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    pctx = presentation_context or {
        "affected_stores_platform": 0,
        "estimated_customers_platform": 0,
    }
    out = dict(cards)
    if "cart_event" in out and isinstance(out["cart_event"], dict):
        out["cart_event"] = enrich_cart_event_card_operational(out["cart_event"], pctx)
    if "db_pool" in out and isinstance(out["db_pool"], dict):
        out["db_pool"] = enrich_db_pool_card_operational(out["db_pool"], pctx)
    if "background_tasks" in out and isinstance(out["background_tasks"], dict):
        out["background_tasks"] = enrich_background_tasks_card_operational(
            out["background_tasks"], pctx
        )
    if "whatsapp" in out and isinstance(out["whatsapp"], dict):
        out["whatsapp"] = enrich_whatsapp_card_operational(out["whatsapp"], pctx)
    if "db_due_scanner" in out and isinstance(out["db_due_scanner"], dict):
        out["db_due_scanner"] = enrich_db_due_scanner_admin_card(out["db_due_scanner"], pctx)
    return out


def operational_card_display_order() -> List[tuple[str, str]]:
    return [
        ("db_due_scanner", "issue-db-due-scanner"),
        ("cart_event", "issue-cart-event"),
        ("db_pool", "issue-db-pool"),
        ("background_tasks", "issue-background-tasks"),
        ("whatsapp", "issue-whatsapp"),
    ]
