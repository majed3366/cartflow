# -*- coding: utf-8 -*-
"""
Admin Support Diagnostics v1 — read-only answers for common merchant support questions.

Consumes existing truth: CartRecoveryLog, RecoverySchedule, delivery truth,
purchase truth, onboarding readiness, template enforcement, recovery-health failures.
Does not change recovery, WhatsApp send, widget, lifecycle, or merchant dashboard.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import desc
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, RecoverySchedule, Store, WhatsAppDeliveryTruth
from services.recovery_failure_explanation_v1 import explain_failure_status
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    STATUS_SKIPPED_NO_PHONE,
    STATUS_SKIPPED_NO_REASON,
)

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"


@dataclass
class AdminSupportDiagnostic:
    summary: str
    severity: str
    issue_type: str
    likely_cause: str
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = ""
    merchant_safe_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    try:
        if getattr(dt, "tzinfo", None) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.isoformat()
    except (TypeError, ValueError, AttributeError):
        return None


def _parse_recovery_key(recovery_key: str) -> tuple[str, str]:
    rk = (recovery_key or "").strip()
    if ":" in rk:
        parts = rk.split(":", 1)
        return parts[0].strip()[:255], parts[1].strip()[:512]
    return "", rk[:512]


def _resolve_store(store_slug: str) -> Optional[Store]:
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return None
    try:
        db.create_all()
        return (
            db.session.query(Store)
            .filter(Store.zid_store_id == ss)
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _resolve_scope(
    *,
    store_slug: str = "",
    session_id: str = "",
    recovery_key: str = "",
) -> dict[str, str]:
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    rk = (recovery_key or "").strip()[:512]
    if rk and not ss:
        ss, sid_from_rk = _parse_recovery_key(rk)
        if not sid:
            sid = sid_from_rk
    elif ss and sid and not rk:
        rk = f"{ss}:{sid}"[:512]
    return {"store_slug": ss, "session_id": sid, "recovery_key": rk}


def _latest_recovery_logs(
    *,
    store_slug: str,
    session_id: str = "",
    limit: int = 8,
) -> list[CartRecoveryLog]:
    if not store_slug:
        return []
    try:
        db.create_all()
        q = db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == store_slug
        )
        if session_id:
            q = q.filter(CartRecoveryLog.session_id == session_id)
        return list(
            q.order_by(desc(CartRecoveryLog.id)).limit(max(1, min(limit, 20))).all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _latest_schedule(
    *,
    store_slug: str,
    session_id: str = "",
    recovery_key: str = "",
) -> Optional[RecoverySchedule]:
    try:
        db.create_all()
        q = db.session.query(RecoverySchedule)
        if recovery_key:
            q = q.filter(RecoverySchedule.recovery_key == recovery_key)
        elif store_slug and session_id:
            q = q.filter(
                RecoverySchedule.store_slug == store_slug,
                RecoverySchedule.session_id == session_id,
            )
        elif store_slug:
            q = q.filter(RecoverySchedule.store_slug == store_slug)
        else:
            return None
        return q.order_by(desc(RecoverySchedule.id)).first()
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _delivery_truth_for_session(
    *,
    store_slug: str,
    session_id: str = "",
) -> Optional[dict[str, Any]]:
    try:
        db.create_all()
        q = db.session.query(WhatsAppDeliveryTruth).filter(
            WhatsAppDeliveryTruth.store_slug == store_slug
        )
        if session_id:
            q = q.filter(WhatsAppDeliveryTruth.session_id == session_id)
        row = q.order_by(desc(WhatsAppDeliveryTruth.last_event_time)).first()
        if row is None:
            return None
        return {
            "message_sid": (row.message_sid or "")[:64],
            "truth_level": (row.truth_level or "")[:64],
            "delivery_status": (row.delivery_status or "")[:64],
            "read_status": (row.read_status or "")[:64],
            "send_status": (row.send_status or "")[:64],
            "last_event_time": _iso(row.last_event_time),
        }
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _abandoned_cart_for_session(
    store: Optional[Store],
    session_id: str,
) -> Optional[AbandonedCart]:
    if store is None or not session_id:
        return None
    try:
        db.create_all()
        return (
            db.session.query(AbandonedCart)
            .filter(
                AbandonedCart.store_id == int(store.id),
                AbandonedCart.recovery_session_id == session_id,
            )
            .order_by(desc(AbandonedCart.id))
            .first()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return None


def _diag(
    *,
    issue_type: str,
    summary: str,
    likely_cause: str,
    severity: str,
    recommended_action: str,
    merchant_safe_message: str,
    evidence: list[str],
) -> AdminSupportDiagnostic:
    return AdminSupportDiagnostic(
        summary=summary,
        severity=severity,
        issue_type=issue_type,
        likely_cause=likely_cause,
        evidence=evidence,
        recommended_action=recommended_action,
        merchant_safe_message=merchant_safe_message,
    )


_DIAG_BY_LOG_STATUS: dict[str, dict[str, str]] = {
    "blocked_template_required": {
        "summary": "WhatsApp send blocked — template required outside 24h window",
        "likely_cause": "Production mode: no customer reply within 24h and provider templates not marked approved",
        "severity": SEVERITY_WARNING,
        "recommended_action": (
            "Confirm Meta/Twilio templates are approved; set "
            "CARTFLOW_WHATSAPP_PROVIDER_TEMPLATES_APPROVED=1 only after approval; "
            "or wait for customer inbound to open session window."
        ),
        "merchant_safe_message": (
            "رسائل واتساب تحتاج إكمال الإعداد قبل الإرسال — يلزم اعتماد القوالب "
            "أو بدء محادثة مع العميل خلال ٢٤ ساعة."
        ),
    },
    "whatsapp_failed": {
        "summary": "WhatsApp send failed",
        "likely_cause": "Provider rejected send, missing credentials, or invalid number/template",
        "severity": SEVERITY_CRITICAL,
        "recommended_action": (
            "Check Twilio/Meta console, template approval, TWILIO_* env, and customer phone; "
            "review CartRecoveryLog message and recovery-health failed_detail."
        ),
        "merchant_safe_message": (
            "تعذّر إرسال رسالة واتساب. فريق الدعم يتحقق من إعدادات المزود ورقم العميل."
        ),
    },
    "sent_real": {
        "summary": "WhatsApp accepted by provider (sent_real)",
        "likely_cause": "Twilio returned message SID — delivery may still be in progress",
        "severity": SEVERITY_INFO,
        "recommended_action": (
            "Confirm delivery via whatsapp_delivery_truth / status callback; "
            "if merchant says not received, check sandbox join or handset."
        ),
        "merchant_safe_message": (
            "تم إرسال رسالة الاسترجاع من النظام. قد يستغرق وصولها دقائق حسب واتساب."
        ),
    },
    "mock_sent": {
        "summary": "Recovery message recorded as sandbox/mock (mock_sent)",
        "likely_cause": "PRODUCTION_MODE off or mock path — no real customer WhatsApp",
        "severity": SEVERITY_INFO,
        "recommended_action": (
            "Explain sandbox to merchant; enable PRODUCTION_MODE + Twilio only when ready for live sends."
        ),
        "merchant_safe_message": (
            "تمت تجربة الإرسال في وضع تجريبي — الرسالة لم تُرسل لعميل حقيقي على واتساب بعد."
        ),
    },
    "queued": {
        "summary": "Send queued before provider call",
        "likely_cause": "Recovery reached provider step; check schedule due_at and worker",
        "severity": SEVERITY_INFO,
        "recommended_action": "Wait for delay window; check RecoverySchedule and recovery-health pending_due.",
        "merchant_safe_message": "الرسالة في قائمة الإرسال — ستُرسل بعد انتهاء مدة الانتظار المحددة.",
    },
    "stopped_converted": {
        "summary": "Recovery stopped — purchase detected",
        "likely_cause": "purchase_truth or conversion stopped further recovery",
        "severity": SEVERITY_INFO,
        "recommended_action": "Verify purchase_truth_records / POST /api/conversion; no resend needed if purchase is valid.",
        "merchant_safe_message": "توقف الاسترجاع لأن الطلب اكتمل — هذا السلوك المتوقع.",
    },
    "skipped_anti_spam": {
        "summary": "Recovery stopped — customer returned to site",
        "likely_cause": "Anti-spam / returned_to_site guard",
        "severity": SEVERITY_INFO,
        "recommended_action": "Confirm behavioral return signal; explain to merchant as protective stop.",
        "merchant_safe_message": "توقف الاسترجاع لأن العميل عاد للمتجر — لحماية تجربته.",
    },
    "returned_to_site": {
        "summary": "Recovery stopped — customer returned",
        "likely_cause": "returned_to_site lifecycle guard",
        "severity": SEVERITY_INFO,
        "recommended_action": "Same as skipped_anti_spam — verify session behavioral flags.",
        "merchant_safe_message": "توقف الاسترجاع بعد عودة العميل للموقع.",
    },
    "skipped_no_phone": {
        "summary": "Recovery skipped — missing phone",
        "likely_cause": "No customer phone on abandon / reason row",
        "severity": SEVERITY_WARNING,
        "recommended_action": "Ensure widget captures phone; check CartRecoveryReason and abandon payload.",
        "merchant_safe_message": "لم نتمكن من الإرسال لأن رقم جوال العميل غير متوفر في السلة.",
    },
    "skipped_no_reason": {
        "summary": "Recovery skipped — missing reason",
        "likely_cause": "Reason widget step not completed",
        "severity": SEVERITY_WARNING,
        "recommended_action": "Merchant test must complete widget reason step before abandon registers.",
        "merchant_safe_message": "لم يكتمل سبب ترك السلة — يُرجى إكمال خطوة الودجيت في المتجر.",
    },
}


def _diagnose_from_log(
    log: CartRecoveryLog,
    *,
    delivery: Optional[dict[str, Any]],
    purchase: bool,
) -> AdminSupportDiagnostic:
    st = (log.status or "").strip()
    meta = _DIAG_BY_LOG_STATUS.get(st)
    evidence = [
        f"CartRecoveryLog id={log.id} status={st} step={log.step}",
        f"log_time={_iso(log.sent_at or log.created_at)}",
    ]
    if log.phone:
        evidence.append(f"phone={str(log.phone)[:24]}")
    if delivery:
        evidence.append(
            f"whatsapp_delivery_truth truth_level={delivery.get('truth_level')} "
            f"sid={delivery.get('message_sid')}"
        )
    if purchase:
        evidence.append("purchase_truth_records=detected_for_recovery_key")

    if st == "sent_real" and delivery:
        tl = (delivery.get("truth_level") or "").strip()
        if tl == "delivered_to_customer":
            return _diag(
                issue_type="delivered_to_customer",
                summary="Message delivered to customer (delivery truth)",
                likely_cause="Twilio status callback reported delivered",
                severity=SEVERITY_INFO,
                recommended_action="No action if merchant confirms receipt; else check handset/WhatsApp app.",
                merchant_safe_message="وصلت رسالة الاسترجاع إلى واتساب العميل.",
                evidence=evidence,
            )
        if tl == "read_by_customer":
            return _diag(
                issue_type="read_by_customer",
                summary="Message read by customer",
                likely_cause="Provider read receipt recorded",
                severity=SEVERITY_INFO,
                recommended_action="Monitor for reply / conversion; no resend needed.",
                merchant_safe_message="قرأ العميل رسالة الاسترجاع.",
                evidence=evidence,
            )

    if meta:
        return _diag(issue_type=st, evidence=evidence, **meta)

    fail = explain_failure_status(st, log_message=(log.message or "")[:220])
    return _diag(
        issue_type=st or "unknown_log_status",
        summary=f"Recovery log status: {st or 'unknown'}",
        likely_cause=fail.get("explanation", "Unclassified log status"),
        severity=SEVERITY_WARNING,
        recommended_action=fail.get("action_summary", "Inspect CartRecoveryLog and schedule."),
        merchant_safe_message="حالة الاسترجاع قيد المتابعة — فريق الدعم يتحقق من التفاصيل.",
        evidence=evidence + [f"failure_explanation={fail.get('reason_code', '')}"],
    )


def _diagnose_waiting_delay(
    sched: RecoverySchedule,
    logs: list[CartRecoveryLog],
) -> AdminSupportDiagnostic:
    due = sched.due_at
    due_iso = _iso(due)
    now = _utc_now()
    if due is not None:
        if due.tzinfo is None:
            due_aware = due.replace(tzinfo=timezone.utc)
        else:
            due_aware = due.astimezone(timezone.utc)
        remaining = max(0, int((due_aware - now).total_seconds()))
    else:
        remaining = None
    evidence = [
        f"RecoverySchedule id={sched.id} status={sched.status} due_at={due_iso}",
        f"effective_delay_seconds={sched.effective_delay_seconds}",
        f"delay_source={sched.delay_source}",
    ]
    if logs and (logs[0].status or "") == "queued":
        evidence.append(f"latest_log=queued id={logs[0].id}")
    return _diag(
        issue_type="recovery_waiting_delay",
        summary="Recovery waiting for scheduled delay",
        likely_cause=f"Schedule due in ~{remaining}s" if remaining is not None else "Delay not yet elapsed",
        severity=SEVERITY_INFO,
        recommended_action=(
            "Wait until due_at; confirm recovery-health scheduler not stale; "
            "merchant should not refresh expecting instant send."
        ),
        merchant_safe_message=(
            "الاسترجاع مجدول — ستُرسل الرسالة تلقائياً بعد انتهاء مدة الانتظار (عادة دقيقتان)."
        ),
        evidence=evidence,
    )


def _diagnose_store_readiness(
    store: Optional[Store],
    onboarding: dict[str, Any],
) -> Optional[AdminSupportDiagnostic]:
    blocking = list(onboarding.get("blocking_steps") or [])
    if not blocking:
        return None
    primary = blocking[0]
    flags = onboarding.get("flags") or {}
    evidence = [
        f"onboarding_ready={onboarding.get('ready')}",
        f"blocking_steps={','.join(blocking[:5])}",
    ]
    if flags.get("sandbox_mode_active"):
        evidence.append("sandbox_mode_active=true")

    if primary == "provider_not_ready":
        return _diag(
            issue_type="provider_not_ready",
            summary="Store not production-ready — provider not ready",
            likely_cause="Twilio/provider readiness check failed while production mode expected",
            severity=SEVERITY_WARNING,
            recommended_action="Complete TWILIO_* env, PRODUCTION_MODE, callbacks; verify get_twilio_readiness.",
            merchant_safe_message="إعداد واتساب للإنتاج غير مكتمل بعد — فريق الدعم يكمل الربط مع المزود.",
            evidence=evidence,
        )
    if primary in ("whatsapp_not_connected", "store_not_connected", "widget_not_installed"):
        issue = "store_not_ready"
        if primary == "widget_not_installed":
            issue = "widget_not_installed"
        return _diag(
            issue_type=issue,
            summary=f"Store onboarding blocker: {primary}",
            likely_cause=f"evaluate_onboarding_readiness blocking={primary}",
            severity=SEVERITY_WARNING,
            recommended_action=f"Resolve blocker {primary} per merchant dashboard / readiness card.",
            merchant_safe_message=(
                "المتجر لم يكتمل إعداده بعد — يرجى متابعة خطوات الإعداد في لوحة التحكم."
            ),
            evidence=evidence,
        )
    return _diag(
        issue_type="store_not_ready",
        summary="Store not ready for automated recovery",
        likely_cause=f"Onboarding blockers: {', '.join(blocking[:3])}",
        severity=SEVERITY_WARNING,
        recommended_action="Walk merchant through setup card; resolve top blocking_steps.",
        merchant_safe_message="يرجى إكمال إعداد المتجر من لوحة التحكم قبل توقع رسائل الاسترجاع.",
        evidence=evidence,
    )


def _diagnose_activation(
    store: Optional[Store],
    onboarding: dict[str, Any],
) -> Optional[AdminSupportDiagnostic]:
    ms = onboarding.get("milestones") or {}
    if ms.get("first_whatsapp_sent"):
        return None
    if not ms.get("first_cart_detected"):
        return None
    evidence = [f"milestones={ms}"]
    return _diag(
        issue_type="activation_not_complete",
        summary="Activation incomplete — no first WhatsApp send milestone",
        likely_cause="Cart detected but first_whatsapp_sent milestone false",
        severity=SEVERITY_INFO,
        recommended_action="Guide merchant through test abandon + wait delay; check logs for skips.",
        merchant_safe_message="لم تُسجَّل أول رسالة استرجاع بعد — جرّب اختبار السلة مع الودجيت.",
        evidence=evidence,
    )


def _diagnose_no_cart(
    store: Optional[Store],
    session_id: str,
    logs: list[CartRecoveryLog],
) -> Optional[AdminSupportDiagnostic]:
    if not session_id or logs:
        return None
    ac = _abandoned_cart_for_session(store, session_id)
    if ac is not None:
        return None
    return _diag(
        issue_type="cart_not_visible",
        summary="No abandoned cart row for this session",
        likely_cause="Widget/cart-event not received or wrong store slug on embed",
        severity=SEVERITY_WARNING,
        recommended_action=(
            "Verify widget embed data-store matches merchant slug; trigger test abandon; "
            "check POST /api/cart-event."
        ),
        merchant_safe_message="لم تظهر السلة في لوحة التحكم بعد — تأكد من تثبيت الودجيت على المتجر.",
        evidence=[
            f"session_id={session_id[:80]}",
            "AbandonedCart=not_found",
            f"CartRecoveryLog_count={len(logs)}",
        ],
    )


def _diagnose_schedule_terminal(
    sched: RecoverySchedule,
) -> Optional[AdminSupportDiagnostic]:
    st = (sched.status or "").strip()
    if st == STATUS_SKIPPED_NO_PHONE:
        return _diag(
            issue_type="missing_phone",
            summary="Schedule terminal — no phone",
            likely_cause="STATUS_SKIPPED_NO_PHONE on RecoverySchedule",
            severity=SEVERITY_WARNING,
            recommended_action="Capture phone in widget abandon flow.",
            merchant_safe_message="لم نتمكن من الإرسال لأن رقم جوال العميل غير متوفر.",
            evidence=[f"RecoverySchedule id={sched.id} status={st}"],
        )
    if st == STATUS_SKIPPED_NO_REASON:
        return _diag(
            issue_type="missing_reason",
            summary="Schedule terminal — no reason",
            likely_cause="STATUS_SKIPPED_NO_REASON on RecoverySchedule",
            severity=SEVERITY_WARNING,
            recommended_action="Complete widget reason step in test.",
            merchant_safe_message="لم يكتمل سبب ترك السلة في الودجيت.",
            evidence=[f"RecoverySchedule id={sched.id} status={st}"],
        )
    if st == "whatsapp_failed":
        fail = explain_failure_status(st, last_error=(sched.last_error or "")[:220])
        return _diag(
            issue_type="whatsapp_failed",
            summary="Schedule marked WhatsApp failed",
            likely_cause=fail.get("explanation", "Provider failure"),
            severity=SEVERITY_CRITICAL,
            recommended_action=fail.get("action_summary", "Check provider."),
            merchant_safe_message="تعذّر إرسال رسالة واتساب — فريق الدعم يتحقق من الإعداد.",
            evidence=[
                f"RecoverySchedule id={sched.id} status={st}",
                f"last_error={(sched.last_error or '')[:120]}",
            ],
        )
    return None


def build_admin_support_diagnostics(
    *,
    store_slug: str = "",
    session_id: str = "",
    recovery_key: str = "",
) -> dict[str, Any]:
    """
    Primary diagnostic for admin support — read-only aggregation.
    """
    scope = _resolve_scope(
        store_slug=store_slug,
        session_id=session_id,
        recovery_key=recovery_key,
    )
    ss = scope["store_slug"]
    sid = scope["session_id"]
    rk = scope["recovery_key"]

    if not ss and not rk:
        empty = _diag(
            issue_type="missing_input",
            summary="store_slug or recovery_key required",
            likely_cause="No scope provided",
            severity=SEVERITY_WARNING,
            recommended_action="Pass store_slug= and optional session_id= or recovery_key=.",
            merchant_safe_message="",
            evidence=[],
        )
        return {
            "ok": False,
            "error": "missing_store_slug",
            "scope": scope,
            "diagnostic": empty.to_dict(),
            "support_questions": list_support_question_inventory(),
        }

    store = _resolve_store(ss)
    if store is not None and not ss:
        ss = (getattr(store, "zid_store_id", None) or "").strip()[:255]
        scope["store_slug"] = ss

    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    onboarding = evaluate_onboarding_readiness(store)
    logs = _latest_recovery_logs(store_slug=ss, session_id=sid)
    sched = _latest_schedule(store_slug=ss, session_id=sid, recovery_key=rk)
    delivery = _delivery_truth_for_session(store_slug=ss, session_id=sid)

    purchase = False
    if rk:
        try:
            from services.cartflow_purchase_truth import has_purchase

            purchase = bool(has_purchase(rk))
        except Exception:  # noqa: BLE001
            purchase = False

    diagnostic: Optional[AdminSupportDiagnostic] = None

    if logs:
        diagnostic = _diagnose_from_log(logs[0], delivery=delivery, purchase=purchase)
        if (
            sched is not None
            and (sched.status or "") == STATUS_SCHEDULED
            and (logs[0].status or "") in ("queued",)
        ):
            due = sched.due_at
            if due is not None:
                if due.tzinfo is None:
                    due_a = due.replace(tzinfo=timezone.utc)
                else:
                    due_a = due.astimezone(timezone.utc)
                if due_a > _utc_now():
                    diagnostic = _diagnose_waiting_delay(sched, logs)
    elif sched is not None:
        sched_diag = _diagnose_schedule_terminal(sched)
        if sched_diag is not None:
            diagnostic = sched_diag
        elif (sched.status or "") == STATUS_SCHEDULED:
            diagnostic = _diagnose_waiting_delay(sched, logs)
        else:
            diagnostic = _diag(
                issue_type=f"schedule_{sched.status}",
                summary=f"Recovery schedule status: {sched.status}",
                likely_cause="No CartRecoveryLog yet for this session",
                severity=SEVERITY_INFO,
                recommended_action="Inspect RecoverySchedule context_json and wait for due_at.",
                merchant_safe_message="الاسترجاع قيد المعالجة — يرجى الانتظار قليلاً.",
                evidence=[f"RecoverySchedule id={sched.id} status={sched.status}"],
            )
    else:
        for fn in (
            lambda: _diagnose_no_cart(store, sid, logs),
            lambda: _diagnose_store_readiness(store, onboarding),
            lambda: _diagnose_activation(store, onboarding),
        ):
            alt = fn()
            if alt is not None:
                diagnostic = alt
                break
        if diagnostic is None:
            diagnostic = _diag(
                issue_type="no_recovery_activity",
                summary="No recovery logs or schedules for this scope",
                likely_cause="Session not started or wrong store/session/recovery_key",
                severity=SEVERITY_INFO,
                recommended_action=(
                    "Confirm widget test; use /dashboard/test-widget; verify store_slug."
                ),
                merchant_safe_message="لا يوجد نشاط استرجاع مسجّل لهذه الجلسة بعد.",
                evidence=[f"scope={scope}"],
            )

    assert diagnostic is not None

    if purchase and diagnostic.issue_type not in (
        "stopped_converted",
        "recovery_stopped_purchase",
        "blocked_template_required",
        "whatsapp_failed",
    ):
        diagnostic = _diag(
            issue_type="recovery_stopped_purchase",
            summary="Purchase recorded — recovery should be stopped",
            likely_cause="purchase_truth_records has entry for recovery_key",
            severity=SEVERITY_INFO,
            recommended_action="Confirm dashboard KPI; no further recovery sends expected.",
            merchant_safe_message="تم إكمال الشراء — توقف الاسترجاع بشكل صحيح.",
            evidence=diagnostic.evidence
            + ["purchase_truth=detected", f"recovery_key={rk[:120]}"],
        )

    lifecycle_closure = None
    if rk:
        try:
            from services.lifecycle_closure_records_v1 import get_durable_closure

            lifecycle_closure = get_durable_closure(rk)
        except Exception:  # noqa: BLE001
            lifecycle_closure = None
    if lifecycle_closure:
        cs = lifecycle_closure.get("closure_status") or ""
        diagnostic.evidence.append(f"lifecycle_closure={cs}")
        if cs == "purchase_completed" and diagnostic.issue_type not in (
            "recovery_stopped_purchase",
            "stopped_converted",
        ):
            diagnostic = _diag(
                issue_type="recovery_stopped_purchase",
                summary="Lifecycle closed — purchase completed",
                likely_cause=f"closure_source={lifecycle_closure.get('closure_source', '-')}",
                severity=SEVERITY_INFO,
                recommended_action="No further recovery; closure is durable.",
                merchant_safe_message="تم إكمال الشراء — توقف الاسترجاع.",
                evidence=diagnostic.evidence
                + [f"closure_reason={lifecycle_closure.get('closure_reason', '-')}"],
            )

    enrichment: dict[str, Any] = {
        "lifecycle_closure": lifecycle_closure,
        "onboarding": {
            "ready": onboarding.get("ready"),
            "blocking_steps": onboarding.get("blocking_steps"),
            "flags": onboarding.get("flags"),
            "milestones": onboarding.get("milestones"),
        },
        "latest_log_status": (logs[0].status if logs else None),
        "latest_schedule_status": (sched.status if sched else None),
        "delivery_truth": delivery,
        "recovery_health_hint": None,
    }

    try:
        from services.recovery_health_v1 import build_recovery_health_snapshot

        rh = build_recovery_health_snapshot(emit_warn_log=False)
        enrichment["recovery_health_hint"] = rh.get("failed_detail", {}).get("summary")
    except Exception:  # noqa: BLE001
        pass

    if sid and store is not None:
        try:
            from services.whatsapp_production_reality_v2 import (
                evaluate_whatsapp_template_enforcement,
            )

            phone = (logs[0].phone if logs else None) or (
                getattr(sched, "customer_phone", None) if sched else None
            )
            if phone:
                te = evaluate_whatsapp_template_enforcement(
                    customer_phone=str(phone),
                    store_slug=ss,
                    store=store,
                )
                enrichment["template_enforcement"] = te
        except Exception:  # noqa: BLE001
            pass

    return {
        "ok": True,
        "scope": scope,
        "store_found": store is not None,
        "diagnostic": diagnostic.to_dict(),
        "context": enrichment,
        "recent_logs": [
            {
                "id": lg.id,
                "status": lg.status,
                "step": lg.step,
                "created_at": _iso(lg.created_at),
                "sent_at": _iso(lg.sent_at),
            }
            for lg in logs[:5]
        ],
        "support_questions": list_support_question_inventory(),
        "generated_at": _iso(_utc_now()),
    }


def list_support_question_inventory() -> list[dict[str, str]]:
    """Part 1 — merchant question → evidence map (static)."""
    return [
        {
            "question": "Why did the WhatsApp message not arrive?",
            "evidence": "CartRecoveryLog, whatsapp_delivery_truth, sent_real/mock_sent, recovery-health failed_detail",
        },
        {
            "question": "Why is cart not showing?",
            "evidence": "AbandonedCart.recovery_session_id, CartRecoveryLog, POST /api/cart-event / widget embed",
        },
        {
            "question": "Why is recovery still waiting?",
            "evidence": "RecoverySchedule due_at, CartRecoveryLog queued, recovery_delay",
        },
        {
            "question": "Why did recovery stop?",
            "evidence": "CartRecoveryLog stopped_converted/skipped_*, purchase_truth_records, lifecycle guards",
        },
        {
            "question": "Why does dashboard show warning?",
            "evidence": "evaluate_onboarding_readiness blocking_steps, merchant activation home_stage",
        },
        {
            "question": "Why is store not ready?",
            "evidence": "evaluate_onboarding_readiness, merchant_onboarding_reality_v1",
        },
        {
            "question": "Why is widget not appearing?",
            "evidence": "Store.cartflow_widget_enabled, onboarding widget_not_installed, storefront embed",
        },
        {
            "question": "Why was message blocked?",
            "evidence": "CartRecoveryLog blocked_template_required, [WA TEMPLATE ENFORCEMENT], template enforcement API",
        },
        {
            "question": "Why did purchase not mark recovered?",
            "evidence": "purchase_truth_records, POST /api/conversion, KPI vs sent milestone (not same)",
        },
        {
            "question": "Why is WhatsApp failed?",
            "evidence": "CartRecoveryLog whatsapp_failed, RecoverySchedule STATUS_WHATSAPP_FAILED, recovery_failure_explanation_v1",
        },
    ]


__all__ = [
    "AdminSupportDiagnostic",
    "build_admin_support_diagnostics",
    "list_support_question_inventory",
]
