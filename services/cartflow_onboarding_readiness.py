# -*- coding: utf-8 -*-
"""
Read-only onboarding readiness for merchants: blockers, milestones, and trust hints.

Does not change recovery, WhatsApp sending, widget runtime, lifecycle/duplicate/session
guards, or provider internals — only consumes public readiness APIs.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import exists, func, or_
from sqlalchemy.exc import SQLAlchemyError

# ─— Blocker metadata (merchant-safe Arabic) —────────────────────────────────

BLOCKER_COPY: dict[str, dict[str, str]] = {
    "dashboard_not_initialized": {
        "title_ar": "لم يبدأ إعداد المتجر بعد",
        "explanation_ar": "لا يوجد سجل متجر مهيأ في لوحة التحكم بعد.",
        "action_ar": "أكمل ربط المتجر أو أنشئ إعدادات المتجر من لوحة التحكم.",
    },
    "store_not_connected": {
        "title_ar": "المتجر غير مربوط بالكامل",
        "explanation_ar": "لم يكتمل الربط مع المعرف أو الرمز المطلوب لاستمرار المزامنة.",
        "action_ar": "أكمل خطوات ربط زد أو تحديث الاعتماد من إعدادات الاسترجاع.",
    },
    "whatsapp_not_connected": {
        "title_ar": "واتساب غير مفعّل",
        "explanation_ar": "وضع الإنتاج يتطلب إكمال إعداد قناة واتساب للرسائل.",
        "action_ar": "أكمل ضبط مزود الرسائل المعتمد وفق دليل الإعداد أو راجع فريق الدعم.",
    },
    "provider_not_ready": {
        "title_ar": "مزود الرسائل غير جاهز",
        "explanation_ar": "الإعدادات موجودة لكن المزود غير جاهز لإرسال حقيقي بعد.",
        "action_ar": "راجع حالة الجاهزية في لوحة التشغيل أو رقم المرسل المعتمد.",
    },
    "no_customer_phone_source": {
        "title_ar": "لا يوجد مصدر موثوق لرقم العميل بعد",
        "explanation_ar": "وُجدت سلّة دون أرقام يمكن التواصل عبرها وفق البيانات الحالية.",
        "action_ar": "تأكد أن نموذج السلة يجمع رقم الجوال وأن الودجت يعمل على المتجر.",
    },
    "recovery_disabled": {
        "title_ar": "الاسترجاع الآلي معطّل",
        "explanation_ar": "حالة المتجر أو إعداد المحاولات تمنع تشغيل الأتمتة.",
        "action_ar": "فعّل الاسترجاع وعدد المحاولات من إعدادات السلال العادية.",
    },
    "sandbox_mode_active": {
        "title_ar": "وضع Sandbox مفعّل",
        "explanation_ar": "لن تُرسل رسائل إنتاج حقيقية؛ التجربة للتحقق من التدفق فقط.",
        "action_ar": "للإنتاج: فعّل وضع الإنتاج واكمل مزود واتساب حسب الدليل.",
    },
    "widget_not_installed": {
        "title_ar": "الودجت غير مثبت",
        "explanation_ar": "واجهة استعادة السلة معطّلة على هذا المتجر.",
        "action_ar": "فعّل ودجت CartFlow من الإعدادات وضع الشيفرة في المتجر.",
    },
    "no_test_cart_seen": {
        "title_ar": "لم يتم رصد أي سلة حتى الآن",
        "explanation_ar": "النظام لم يسجل بعد سلّة مهجورة عبر الودجت لهذا المتجر.",
        "action_ar": "جرّب زيارة المتجر وإكمال خطوة ترك السلة للتحقق.",
    },
}


def get_onboarding_blocker_catalog() -> dict[str, dict[str, str]]:
    """Static copy for docs/APIs; merchant-safe wording only."""
    return {k: dict(v) for k, v in BLOCKER_COPY.items()}


def _resolve_dashboard_store_row():
    """Same selection as dashboard recovery row — avoid importing main."""
    try:
        from extensions import db  # noqa: PLC0415
        from models import Store  # noqa: PLC0415

        db.create_all()
        return db.session.query(Store).order_by(Store.id.desc()).first()
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
        return None


def _milestones_readonly(store: Any) -> dict[str, bool]:
    out = {
        "first_cart_detected": False,
        "first_recovery_scheduled": False,
        "first_whatsapp_sent": False,
        "first_reply_received": False,
        "first_recovered_cart": False,
    }
    try:
        from extensions import db  # noqa: PLC0415
        from models import (  # noqa: PLC0415
            AbandonedCart,
            CartRecoveryLog,
            MerchantFollowupAction,
        )

        db.create_all()
        sid = int(getattr(store, "id", 0) or 0)
        slug = (getattr(store, "zid_store_id", None) or "").strip()[:255]
        if sid <= 0:
            return out

        n_carts = (
            db.session.query(func.count(AbandonedCart.id))
            .filter(AbandonedCart.store_id == sid)
            .scalar()
            or 0
        )
        out["first_cart_detected"] = int(n_carts) > 0

        reply_log = False
        if slug:
            out["first_recovery_scheduled"] = bool(
                db.session.query(
                    exists().where(CartRecoveryLog.store_slug == slug)
                ).scalar()
            )
            out["first_whatsapp_sent"] = bool(
                db.session.query(
                    exists().where(
                        CartRecoveryLog.store_slug == slug,
                        CartRecoveryLog.status.in_(("mock_sent", "sent_real")),
                    )
                ).scalar()
            )
            reply_log = bool(
                db.session.query(
                    exists().where(
                        CartRecoveryLog.store_slug == slug,
                        CartRecoveryLog.status.in_(
                            (
                                "skipped_followup_customer_replied",
                                "customer_replied",
                            )
                        ),
                    )
                ).scalar()
            )
        followup = bool(
            db.session.query(
                exists().where(MerchantFollowupAction.store_id == sid)
            ).scalar()
        )
        out["first_reply_received"] = bool(reply_log or followup)

        out["first_recovered_cart"] = bool(
            db.session.query(
                exists().where(
                    AbandonedCart.store_id == sid,
                    or_(
                        AbandonedCart.status == "recovered",
                        AbandonedCart.recovered_at.isnot(None),
                    ),
                )
            ).scalar()
        )
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
    return out


def _phone_coverage_readonly(store: Any) -> tuple[bool, bool]:
    """Returns (any_cart_has_phone, store_merchant_phone_set)."""
    try:
        from extensions import db  # noqa: PLC0415
        from models import AbandonedCart  # noqa: PLC0415

        db.create_all()
        sid = int(getattr(store, "id", 0) or 0)
        if sid <= 0:
            return False, False
        merchant_phone = bool(
            (getattr(store, "store_whatsapp_number", None) or "").strip()
        )
        has_cart_phone = bool(
            db.session.query(
                exists().where(
                    AbandonedCart.store_id == sid,
                    AbandonedCart.customer_phone.isnot(None),
                    AbandonedCart.customer_phone != "",
                )
            ).scalar()
        )
        return has_cart_phone, merchant_phone
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        try:
            from extensions import db as _db  # noqa: PLC0415

            _db.session.rollback()
        except Exception:
            pass
        return False, False


def evaluate_onboarding_readiness(store: Optional[Any] = None) -> dict[str, Any]:
    """
    Read-only onboarding evaluation. No mutations.

    ``ready`` is True only when the store can operate in the **current** mode
    (sandbox: mock path ok; production: Twilio + provider readiness).
    """
    from services.whatsapp_send import (  # noqa: PLC0415
        recovery_uses_real_whatsapp,
        whatsapp_real_configured,
    )

    st = store
    sandbox_mode = not bool(recovery_uses_real_whatsapp())
    need_real_wa = bool(recovery_uses_real_whatsapp())

    twilio_ok = bool(whatsapp_real_configured())
    provider_ready = False
    try:
        from services.cartflow_provider_readiness import (  # noqa: PLC0415
            get_whatsapp_provider_readiness,
        )

        pr = get_whatsapp_provider_readiness()
        provider_ready = bool(pr.get("ready"))
    except Exception:
        provider_ready = False

    flags: dict[str, bool] = {
        "dashboard_ready": st is not None,
        "store_connected": False,
        "whatsapp_configured": twilio_ok,
        "provider_ready": provider_ready,
        "recovery_enabled": False,
        "widget_installed": False,
        "test_recovery_possible": False,
        "sandbox_mode_active": sandbox_mode,
    }

    blocking: list[str] = []
    soft_notes: list[str] = []

    if st is None:
        blocking.append("dashboard_not_initialized")
        empty_ms = {
            "first_cart_detected": False,
            "first_recovery_scheduled": False,
            "first_whatsapp_sent": False,
            "first_reply_received": False,
            "first_recovered_cart": False,
        }
        return _finalize_payload(
            ready=False,
            blocking=blocking,
            soft_notes=soft_notes,
            flags=flags,
            milestones=empty_ms,
            sandbox_mode=sandbox_mode,
        )

    token_ok = bool((getattr(st, "access_token", None) or "").strip())
    zid_ok = bool((getattr(st, "zid_store_id", None) or "").strip())
    flags["store_connected"] = token_ok or zid_ok
    if not flags["store_connected"]:
        blocking.append("store_not_connected")

    active = bool(getattr(st, "is_active", True))
    try:
        attempts = int(getattr(st, "recovery_attempts", 1) or 0)
    except (TypeError, ValueError):
        attempts = 0
    flags["recovery_enabled"] = active and attempts >= 1
    if not active or attempts < 1:
        blocking.append("recovery_disabled")

    wid_en = bool(getattr(st, "cartflow_widget_enabled", True))
    flags["widget_installed"] = wid_en
    if not wid_en:
        blocking.append("widget_not_installed")

    if sandbox_mode:
        soft_notes.append("sandbox_mode_active")
    else:
        if not twilio_ok:
            blocking.append("whatsapp_not_connected")
        if twilio_ok and not provider_ready:
            blocking.append("provider_not_ready")

    milestones = _milestones_readonly(st)
    has_cart_phone, merchant_phone = _phone_coverage_readonly(st)
    if milestones["first_cart_detected"] and not has_cart_phone and not merchant_phone:
        if need_real_wa:
            blocking.append("no_customer_phone_source")

    if not milestones["first_cart_detected"]:
        soft_notes.append("no_test_cart_seen")

    flags["test_recovery_possible"] = bool(flags["store_connected"] and wid_en and active)

    ready = len(blocking) == 0

    return _finalize_payload(
        ready=ready,
        blocking=blocking,
        soft_notes=soft_notes,
        flags=flags,
        milestones=milestones,
        sandbox_mode=sandbox_mode,
    )


def _finalize_payload(
    *,
    ready: bool,
    blocking: list[str],
    soft_notes: list[str],
    flags: dict[str, bool],
    milestones: dict[str, bool],
    sandbox_mode: bool,
) -> dict[str, Any]:
    # Completion: weighted checklist (0–100)
    weights = [
        ("dashboard_ready", 12, flags.get("dashboard_ready")),
        ("store_connected", 18, flags.get("store_connected")),
        ("recovery_enabled", 15, flags.get("recovery_enabled")),
        ("widget_installed", 15, flags.get("widget_installed")),
        (
            "messaging_path",
            20,
            (
                sandbox_mode
                or (flags.get("whatsapp_configured") and flags.get("provider_ready"))
            ),
        ),
        ("first_cart", 10, milestones.get("first_cart_detected")),
        ("first_send", 10, milestones.get("first_whatsapp_sent")),
    ]
    total_w = sum(w for _, w, _ in weights)
    earned = sum(w for _, w, ok in weights if ok)
    pct = int(round(100.0 * earned / total_w)) if total_w else 0

    primary_block = blocking[0] if blocking else (soft_notes[0] if soft_notes else None)
    rec_ar, tc_ar, status_ar, sandbox_ar = _merchant_strings(
        ready=ready,
        blocking=blocking,
        soft_notes=soft_notes,
        milestones=milestones,
        sandbox_mode=sandbox_mode,
        primary=primary_block,
    )

    return {
        "ready": ready,
        "completion_percent": max(0, min(100, pct)),
        "blocking_steps": list(blocking),
        "soft_notes": list(soft_notes),
        "recommended_next_step_ar": rec_ar,
        "merchant_status_ar": status_ar,
        "merchant_trust_line_ar": tc_ar,
        "sandbox_notice_ar": sandbox_ar,
        "sandbox_mode_active": sandbox_mode,
        "milestones": dict(milestones),
        "flags": dict(flags),
    }


def _merchant_strings(
    *,
    ready: bool,
    blocking: list[str],
    soft_notes: list[str],
    milestones: dict[str, bool],
    sandbox_mode: bool,
    primary: Optional[str],
) -> tuple[str, str, str, str]:
    """Returns recommended_next, trust line, status headline, sandbox notice."""
    sandbox_ar = ""
    if sandbox_mode:
        sandbox_ar = BLOCKER_COPY["sandbox_mode_active"]["explanation_ar"]

    if blocking and primary:
        meta = BLOCKER_COPY.get(primary, {})
        title = meta.get("title_ar", "يتطلب الإعداد خطوة إضافية")
        act = meta.get("action_ar", "راجع إعدادات السلال العادية والربط.")
        return act, title, title, sandbox_ar

    if ready:
        if milestones.get("first_cart_detected"):
            st_line = "النظام جاهز لاستقبال السلال"
            rec = "تابع لوحة السلال العادية لمراقبة الإرسال والردود."
        else:
            st_line = "النظام جاهز؛ لم يتم رصد سلّة بعد"
            rec = BLOCKER_COPY["no_test_cart_seen"]["action_ar"]
        trust = "تمت تهيئة التشغيل الأساسي — راقب أول نشاط لسلّة عادية."
        return rec, trust, st_line, sandbox_ar

    rec = "راجع إعدادات الربط والاسترجاع من لوحة السلال العادية."
    status = "يتطلب الإعداد خطوة إضافية"
    if soft_notes:
        sn = soft_notes[0]
        meta = BLOCKER_COPY.get(sn, {})
        if meta:
            status = meta.get("title_ar", status)
            rec = meta.get("action_ar", rec)
    trust = status
    return rec, trust, status, sandbox_ar


def get_onboarding_dashboard_visibility(store: Optional[Any]) -> dict[str, Any]:
    """Minimal payload for dashboard strip (no layout redesign)."""
    ev = evaluate_onboarding_readiness(store)
    titles: list[str] = []
    for code in ev.get("blocking_steps") or []:
        t = BLOCKER_COPY.get(code, {}).get("title_ar")
        if t:
            titles.append(t)
    for code in ev.get("soft_notes") or []:
        if code in BLOCKER_COPY and code not in (ev.get("blocking_steps") or []):
            t = BLOCKER_COPY[code].get("title_ar")
            if t and t not in titles:
                titles.append(t)
    return {
        "show_strip": True,
        "ready": ev["ready"],
        "completion_percent": ev["completion_percent"],
        "status_ar": ev.get("merchant_status_ar") or "",
        "recommended_ar": ev.get("recommended_next_step_ar") or "",
        "trust_ar": ev.get("merchant_trust_line_ar") or "",
        "sandbox_notice_ar": ev.get("sandbox_notice_ar") or "",
        "blocking_titles_ar": titles[:4],
        "milestones": ev.get("milestones") or {},
    }


def build_onboarding_health_section() -> dict[str, Any]:
    """Compact section for runtime health snapshot."""
    st = _resolve_dashboard_store_row()
    ev = evaluate_onboarding_readiness(st)
    return {
        "onboarding_ready": bool(ev.get("ready")),
        "onboarding_blocked": bool(ev.get("blocking_steps")),
        "onboarding_completion_percent": int(ev.get("completion_percent") or 0),
        "sandbox_mode_active": bool(ev.get("sandbox_mode_active")),
        "onboarding_blocking_steps": list(ev.get("blocking_steps") or []),
        "onboarding_milestones": dict(ev.get("milestones") or {}),
        "onboarding_flags": dict(ev.get("flags") or {}),
    }


def reset_onboarding_readiness_for_tests() -> None:
    """No module-local mutable state; placeholder for test symmetry."""
    return None
