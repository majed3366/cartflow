# -*- coding: utf-8 -*-
"""
Operational-first Arabic copy for admin operational health (Layer 1).

Technical/raw values remain in card ``technical_detail_lines`` (Layer 2).
Does not change runtime behavior, APIs, or merchant surfaces.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

_SCANNER_STATUS_AR = {
    "healthy": ("يعمل طبيعي", "🟢"),
    "idle": ("في انتظار — المراقبة غير نشطة", "🟡"),
    "disabled": ("معطّل", "⚪"),
    "error": ("يوجد مشكلة", "🔴"),
    "unknown": ("غير معروف", "🟡"),
}

_CARD_STATUS_AR = {
    "ok": ("سليم", "🟢"),
    "warn": ("يحتاج انتباه", "🟡"),
    "unknown": ("غير معروف", "🟡"),
}


def _yes_no(value: bool) -> str:
    return "نعم" if value else "لا"


def _build_operational_common(
    *,
    has_risk: bool,
    needs_intervention: bool,
    merchant_impact: bool,
    suggested_action: str,
    last_problem: Optional[str],
    last_success: Optional[str],
) -> Dict[str, str]:
    return {
        "has_risk_ar": _yes_no(has_risk),
        "needs_intervention_ar": _yes_no(needs_intervention),
        "merchant_impact_ar": "نعم" if merchant_impact else "لا يوجد",
        "suggested_action_ar": suggested_action,
        "last_problem_ar": last_problem or "لا يوجد",
        "last_success_ar": last_success or "—",
    }


def build_db_due_scanner_operational_layer(h: Dict[str, Any]) -> Dict[str, Any]:
    """Layer 1 — فحص المهام المؤجلة."""
    status = str(h.get("status") or "unknown")
    label, emoji = _SCANNER_STATUS_AR.get(status, _SCANNER_STATUS_AR["unknown"])
    enabled = bool(h.get("enabled"))
    loop_running = bool(h.get("loop_running"))
    last_error = h.get("last_error")
    last_found = int(h.get("last_found") or 0)
    total_dispatches = int(h.get("total_dispatches") or 0)
    needs_intervention = bool(
        last_error
        or (enabled and not loop_running and status != "disabled")
        or (enabled and last_found > 0 and status == "error")
    )
    has_risk = status == "error" or (enabled and not loop_running and status == "idle")
    pending_work = last_found > 0

    if not enabled:
        suggested = "تفعيل المراقبة عبر CARTFLOW_DB_DUE_SCANNER_ENABLED=true إن رُغب بالفحص التلقائي"
        monitoring = "معطّلة"
    elif last_error:
        suggested = "راجع آخر مشكلة في التفاصيل التقنية أو سجلات [DB DUE SCANNER *]"
    elif pending_work and loop_running:
        suggested = "مراقبة — قد تُعالج المهام في الدورة القادمة"
    else:
        suggested = "لا حاجة لأي تدخل"

    last_success = None
    if total_dispatches > 0:
        ago = h.get("last_dispatch_ago")
        last_success = f"آخر معالجة: {ago}" if ago else "تمت معالجة مهام سابقاً"
    elif loop_running and status == "healthy":
        last_success = "المراقبة تعمل — لم تُسجَّل معالجة بعد"

    monitoring_ar = "تعمل" if loop_running else ("معطّلة" if not enabled else "متوقفة")

    op = {
        "title_ar": "فحص المهام المؤجلة",
        "status_line_ar": f"{emoji} {label}",
        "status_emoji": emoji,
        "status_label_ar": label,
        "monitoring_ar": monitoring_ar,
        "processed_tasks_ar": str(total_dispatches),
        "pending_tasks_need_action_ar": _yes_no(pending_work and needs_intervention),
        "enabled_ar": _yes_no(enabled),
        "interval_ar": f"{int(h.get('interval_seconds') or 0)} ثانية",
        "last_tick_ar": h.get("last_tick_ago") or "—",
        "last_dispatch_ar": h.get("last_dispatch_ago") or "—",
    }
    op.update(
        _build_operational_common(
            has_risk=has_risk,
            needs_intervention=needs_intervention,
            merchant_impact=False,
            suggested_action=suggested,
            last_problem=str(last_error) if last_error else None,
            last_success=last_success,
        )
    )
    return op


def build_db_due_scanner_technical_lines(h: Dict[str, Any]) -> List[str]:
    """Layer 2 — raw labels for support."""
    return [
        f"DB Due Scanner — status: {h.get('status_emoji', '')} {h.get('status_label', '—')}",
        f"enabled: {str(h.get('enabled')).lower()}",
        f"interval_seconds: {int(h.get('interval_seconds') or 0)}",
        f"loop_running: {str(h.get('loop_running')).lower()}",
        f"last_tick_at: {h.get('last_tick_at') or '—'} ({h.get('last_tick_ago') or '—'})",
        f"last_dispatch_at: {h.get('last_dispatch_at') or '—'} ({h.get('last_dispatch_ago') or '—'})",
        f"found (مهام بحاجة معالجة): {h.get('last_found')}",
        f"dispatched (مهام تمت معالجتها): {h.get('last_dispatched')}",
        f"skipped (تم التجاوز بأمان): {h.get('last_skipped')}",
        f"total_ticks: {h.get('total_ticks')} | total_dispatches: {h.get('total_dispatches')}",
        f"last_error: {h.get('last_error') or 'None'}",
        "API: GET /api/admin/db-due-scanner-health",
    ]


def enrich_cart_event_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    _, emoji = _CARD_STATUS_AR.get(status, _CARD_STATUS_AR["unknown"])
    slow = bool(card.get("slow_warning"))
    label = str(card.get("status_label_ar") or "—")
    has_risk = slow or status == "warn"
    needs = slow
    out = dict(card)
    out["title_ar"] = "استقبال أحداث السلة"
    out["operational"] = {
        "title_ar": "استقبال أحداث السلة",
        "status_line_ar": f"{emoji} {label}",
        "summary_ar": str(card.get("last_status_ar") or "—"),
        **_build_operational_common(
            has_risk=has_risk,
            needs_intervention=needs,
            merchant_impact=has_risk,
            suggested_action=(
                "راجع بطء مسار استقبال السلة أو ضغط القاعدة"
                if slow
                else "لا حاجة لأي تدخل"
            ),
            last_problem=str(card.get("last_status_ar")) if status == "warn" else None,
            last_success="آخر طلب طبيعي" if status == "ok" else None,
        ),
    }
    out["technical_detail_lines"] = [
        "cart-event (POST /api/cart-event)",
        f"status: {status}",
        f"recent_count: {card.get('recent_count')}",
        f"avg_duration_ms: {card.get('avg_duration_ms')}",
        f"latest_duration_ms: {card.get('latest_duration_ms')}",
        *(card.get("detail_lines_ar") or []),
    ]
    return out


def enrich_db_pool_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    timeout_n = int(card.get("timeout_count") or 0)
    status = str(card.get("status") or "unknown")
    _, emoji = _CARD_STATUS_AR.get(status, _CARD_STATUS_AR["unknown"])
    label = str(card.get("status_label_ar") or "—")
    has_risk = timeout_n > 0
    out = dict(card)
    out["title_ar"] = "اتصالات قاعدة البيانات"
    out["operational"] = {
        "title_ar": "اتصالات قاعدة البيانات",
        "status_line_ar": f"{emoji} {label}",
        "summary_ar": str(card.get("pool_summary_ar") or "—"),
        **_build_operational_common(
            has_risk=has_risk,
            needs_intervention=has_risk,
            merchant_impact=has_risk,
            suggested_action=(
                "راجع ضغط القاعدة أو حد المسبح (QueuePool)"
                if has_risk
                else "لا حاجة لأي تدخل"
            ),
            last_problem=(
                f"انتهاء مهلة مسبح: {timeout_n} مرة"
                if timeout_n
                else None
            ),
            last_success="لا انتهاء مهلة في هذه العملية" if not timeout_n else None,
        ),
    }
    out["technical_detail_lines"] = [
        "db_pool / QueuePool",
        f"timeout_count: {timeout_n}",
        *(card.get("detail_lines_ar") or []),
    ]
    return out


def enrich_background_tasks_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    _, emoji = _CARD_STATUS_AR.get(status, _CARD_STATUS_AR["unknown"])
    label = str(card.get("status_label_ar") or "—")
    err_n = int(card.get("background_error_count") or 0)
    has_risk = status == "warn"
    out = dict(card)
    out["title_ar"] = "المهام الخلفية والاسترداد"
    out["operational"] = {
        "title_ar": "المهام الخلفية والاسترداد",
        "status_line_ar": f"{emoji} {label}",
        "summary_ar": str(card.get("last_recovery_dispatch_ar") or "—"),
        **_build_operational_common(
            has_risk=has_risk,
            needs_intervention=has_risk,
            merchant_impact=has_risk,
            suggested_action=(
                "راجع مسار الاسترداد والمهام الخلفية"
                if has_risk
                else "لا حاجة لأي تدخل"
            ),
            last_problem=f"إشارات/أخطاء: {err_n}" if err_n else None,
            last_success=str(card.get("last_recovery_dispatch_ar")) if not has_risk else None,
        ),
    }
    out["technical_detail_lines"] = [
        "background_tasks / recovery_runtime",
        f"background_error_count: {err_n}",
        f"last_recovery_dispatch: {card.get('last_recovery_dispatch_ar')}",
        *(card.get("detail_lines_ar") or []),
    ]
    return out


def enrich_whatsapp_card_operational(card: Dict[str, Any]) -> Dict[str, Any]:
    status = str(card.get("status") or "unknown")
    _, emoji = _CARD_STATUS_AR.get(status, _CARD_STATUS_AR["unknown"])
    label = str(card.get("status_label_ar") or "—")
    fail_i = card.get("recent_failed_24h")
    has_risk = status == "warn"
    out = dict(card)
    out["title_ar"] = "إرسال واتساب"
    out["operational"] = {
        "title_ar": "إرسال واتساب",
        "status_line_ar": f"{emoji} {label}",
        "summary_ar": str(card.get("last_provider_failure_ar") or "—"),
        **_build_operational_common(
            has_risk=has_risk,
            needs_intervention=has_risk,
            merchant_impact=has_risk,
            suggested_action=(
                "راجع إعدادات المزود أو فشل الإرسال"
                if has_risk
                else "لا حاجة لأي تدخل"
            ),
            last_problem=str(card.get("last_provider_failure_ar")) if has_risk else None,
            last_success="المزود مُهيّأ" if card.get("configured") and not has_risk else None,
        ),
    }
    out["technical_detail_lines"] = [
        "whatsapp / provider",
        f"configured: {card.get('configured')}",
        f"recent_failed_24h: {fail_i}",
        *(card.get("detail_lines_ar") or []),
    ]
    return out


def enrich_db_due_scanner_admin_card(card: Dict[str, Any]) -> Dict[str, Any]:
    h = {k: v for k, v in card.items() if k not in ("operational", "technical_detail_lines", "detail_lines")}
    out = dict(h)
    out["title"] = "DB Due Scanner"
    out["title_ar"] = "فحص المهام المؤجلة"
    out["operational"] = build_db_due_scanner_operational_layer(h)
    out["technical_detail_lines"] = build_db_due_scanner_technical_lines(h)
    out["detail_lines"] = out["technical_detail_lines"]
    return out


def enrich_operational_health_cards(cards: Dict[str, Any]) -> Dict[str, Any]:
    """Attach Layer 1 operational + Layer 2 technical lines to diagnostic cards."""
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
