# -*- coding: utf-8 -*-
"""
Admin Operational Health v1 — read-only wiring visibility for internal operators.

Consumes in-process samples and existing runtime health helpers only.
Does not change recovery, WhatsApp sends, merchant UX, or API contracts.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

from services.cartflow_runtime_health import (
    ANOMALY_PROVIDER_SEND_FAILURE,
    drain_recent_anomalies,
    recent_anomaly_type_counts,
)

_CART_EVENT_SLOW_MS = 2500.0
_MAX_CART_SAMPLES = 80
_MAX_POOL_EVENTS = 40
_MAX_BG_ERRORS = 40

_lock = threading.Lock()
_cart_event_samples: deque[dict[str, Any]] = deque(maxlen=_MAX_CART_SAMPLES)
_pool_timeout_events: deque[dict[str, Any]] = deque(maxlen=_MAX_POOL_EVENTS)
_background_task_errors: deque[dict[str, Any]] = deque(maxlen=_MAX_BG_ERRORS)
_listeners_installed = False


def record_cart_event_finish_sample(
    *,
    duration_ms: float,
    http_status: int,
    recovery_outcome: str = "",
    event: str = "",
) -> None:
    """Observability-only ring buffer for admin health (no request behavior change)."""
    entry = {
        "duration_ms": round(float(duration_ms), 1),
        "http_status": int(http_status),
        "recovery_outcome": (recovery_outcome or "").strip()[:64],
        "event": (event or "").strip()[:64],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _cart_event_samples.append(entry)


def record_db_pool_timeout(*, detail: str = "") -> None:
    """Called when pool checkout times out (listener or explicit probe)."""
    entry = {
        "detail": (detail or "").strip()[:200],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _pool_timeout_events.append(entry)


def record_background_task_error(*, source: str = "", detail: str = "") -> None:
    """Optional hook for deferred/background work failures (observability only)."""
    entry = {
        "source": (source or "").strip()[:80],
        "detail": (detail or "").strip()[:200],
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        _background_task_errors.append(entry)


def clear_operational_health_buffers_for_tests() -> None:
    with _lock:
        _cart_event_samples.clear()
        _pool_timeout_events.clear()
        _background_task_errors.clear()


def get_db_pool_snapshot_readonly() -> dict[str, Any]:
    """Public read-only pool snapshot for admin load tests."""
    return _pool_snapshot_safe()


def get_operational_counter_snapshots() -> dict[str, int]:
    """In-process counters for load-test before/after deltas."""
    with _lock:
        return {
            "pool_timeout_count": len(_pool_timeout_events),
            "background_task_errors": len(_background_task_errors),
        }


def _maybe_install_pool_error_listener() -> None:
    global _listeners_installed
    if _listeners_installed:
        return
    try:
        from sqlalchemy import event
        from sqlalchemy.exc import TimeoutError as SATimeoutError

        from extensions import db

        eng = db.engine

        @event.listens_for(eng, "handle_error")
        def _on_engine_pool_error(exception_context: Any) -> None:
            exc = getattr(exception_context, "original_exception", None)
            if exc is None:
                return
            is_timeout = isinstance(exc, (SATimeoutError, TimeoutError))
            msg = str(exc).lower()
            if is_timeout or "queuepool" in msg or "timed out" in msg:
                record_db_pool_timeout(detail=str(exc)[:200])

        _listeners_installed = True
    except Exception:
        _listeners_installed = True


def _pool_snapshot_safe() -> dict[str, Any]:
    try:
        from extensions import db

        pool = getattr(db.engine, "pool", None)
        if pool is None:
            return {"available": False, "summary_ar": "غير متاح حالياً"}

        pname = pool.__class__.__name__
        parts: list[str] = [pname]
        metrics: dict[str, Any] = {"pool_class": pname}

        checked = getattr(pool, "checkedout", None)
        if callable(checked):
            try:
                co = int(checked())
                parts.append(f"محجوز={co}")
                metrics["checked_out"] = co
            except Exception:
                pass

        psz = getattr(pool, "size", None)
        if callable(psz):
            try:
                sz = int(psz())
                parts.append(f"حجم={sz}")
                metrics["size"] = sz
            except Exception:
                pass

        overflow = getattr(pool, "overflow", None)
        if callable(overflow):
            try:
                ov = int(overflow())
                parts.append(f"تجاوز={ov}")
                metrics["overflow"] = ov
            except Exception:
                pass

        return {
            "available": True,
            "summary_ar": " — ".join(parts),
            "metrics": metrics,
        }
    except Exception:
        return {"available": False, "summary_ar": "غير متاح حالياً"}


def _cart_event_card() -> dict[str, Any]:
    with _lock:
        samples = list(_cart_event_samples)

    recent_n = len(samples)
    if not samples:
        return {
            "status": "unknown",
            "status_label_ar": "لا بيانات بعد",
            "recent_count": 0,
            "avg_duration_ms": None,
            "latest_duration_ms": None,
            "last_status_ar": "لم يُسجَّل طلب cart-event في هذه العملية بعد",
            "slow_warning": False,
            "detail_lines_ar": [
                "يُحدَّث العدّ عند معالجة POST /api/cart-event في هذا العامل.",
            ],
        }

    durations = [float(s.get("duration_ms") or 0) for s in samples]
    avg_ms = sum(durations) / len(durations)
    latest = samples[-1]
    latest_ms = float(latest.get("duration_ms") or 0)
    slow = latest_ms >= _CART_EVENT_SLOW_MS or avg_ms >= _CART_EVENT_SLOW_MS * 0.85

    http_st = int(latest.get("http_status") or 0)
    recovery = str(latest.get("recovery_outcome") or "").strip()
    if http_st >= 500:
        last_status = f"آخر طلب: خطأ خادم ({http_st})"
        status = "warn"
    elif slow:
        last_status = f"آخر طلب: بطيء ({latest_ms:.0f} مللي ثانية)"
        status = "warn"
    elif http_st >= 400:
        last_status = f"آخر طلب: رفض ({http_st})"
        status = "warn"
    else:
        last_status = "آخر طلب: طبيعي"
        status = "ok"

    if recovery:
        last_status += f" — مسار الاسترداد: {recovery}"

    lines = [
        f"عينات حديثة في الذاكرة: {recent_n}",
        f"متوسط المدة: {avg_ms:.0f} مللي ثانية",
        f"آخر مدة: {latest_ms:.0f} مللي ثانية",
    ]
    if slow:
        lines.append(f"تنبيه: المدة تتجاوز عتبة الأمان ({_CART_EVENT_SLOW_MS:.0f} مللي ثانية)")

    return {
        "status": status,
        "status_label_ar": "بطيء" if slow else ("تنبيه" if status == "warn" else "سليم"),
        "recent_count": recent_n,
        "avg_duration_ms": round(avg_ms, 1),
        "latest_duration_ms": round(latest_ms, 1),
        "last_status_ar": last_status,
        "slow_warning": slow,
        "detail_lines_ar": lines,
    }


def _db_pool_card() -> dict[str, Any]:
    pool = _pool_snapshot_safe()
    with _lock:
        timeouts = list(_pool_timeout_events)
    timeout_n = len(timeouts)
    last_timeout = timeouts[-1] if timeouts else None

    status = "ok"
    if timeout_n > 0:
        status = "warn"
    elif not pool.get("available"):
        status = "unknown"

    lines: list[str] = []
    if pool.get("available"):
        lines.append(f"حالة المسبح: {pool.get('summary_ar')}")
    else:
        lines.append(pool.get("summary_ar") or "غير متاح حالياً")

    if timeout_n:
        lines.append(f"انتهاء مهلة QueuePool مُسجَّل: {timeout_n} مرة في هذه العملية")
        if last_timeout:
            lines.append(
                f"آخر حدث: {last_timeout.get('recorded_at_utc', '')[:19]} — "
                f"{last_timeout.get('detail', '')[:120]}"
            )
    else:
        lines.append("لم يُرصد انتهاء مهلة مسبح في هذه العملية")

    return {
        "status": status,
        "status_label_ar": "ضغط" if timeout_n else ("غير معروف" if status == "unknown" else "سليم"),
        "pool_summary_ar": pool.get("summary_ar") or "غير متاح حالياً",
        "timeout_count": timeout_n,
        "detail_lines_ar": lines,
    }


def _background_tasks_card(admin_rt: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        bg_errs = list(_background_task_errors)

    anomalies = drain_recent_anomalies(limit=30)
    sched_fail = [
        a
        for a in anomalies
        if str(a.get("type") or "") == ANOMALY_PROVIDER_SEND_FAILURE
        or "background" in str(a.get("source") or "").lower()
        or "recovery" in str(a.get("source") or "").lower()
    ]

    recovery_ok = bool(admin_rt.get("recovery_runtime_ok"))
    last_dispatch = "غير متاح حالياً"
    with _lock:
        for s in reversed(_cart_event_samples):
            ro = str(s.get("recovery_outcome") or "")
            if ro:
                last_dispatch = ro
                break

    err_n = len(bg_errs) + len(sched_fail)
    status = "ok"
    if err_n or not recovery_ok:
        status = "warn"

    lines = [
        f"مسار الاسترداد نشط: {'نعم' if recovery_ok else 'لا — راجع البيئة/القاعدة'}",
        f"آخر نتيجة جدولة من cart-event: {last_dispatch}",
    ]
    if bg_errs:
        lines.append(f"أخطاء مهام خلفية مُسجَّلة: {len(bg_errs)}")
        lines.append(f"آخر خطأ: {bg_errs[-1].get('detail', '')[:120]}")
    elif sched_fail:
        lines.append(f"إشارات تشغيل حديثة في الذاكرة: {len(sched_fail)}")
    else:
        lines.append("لا أخطاء مهام خلفية مُسجَّلة في هذه العملية")

    return {
        "status": status,
        "status_label_ar": "تنبيه" if status == "warn" else "سليم",
        "last_recovery_dispatch_ar": last_dispatch,
        "background_error_count": err_n,
        "detail_lines_ar": lines,
    }


def _whatsapp_card(admin_rt: dict[str, Any]) -> dict[str, Any]:
    prov = admin_rt.get("provider") if isinstance(admin_rt.get("provider"), dict) else {}
    configured = bool(prov.get("configured"))
    fail_n = prov.get("recent_send_failures_24h")
    fail_i = int(fail_n) if isinstance(fail_n, int) and fail_n >= 0 else None
    failure_class = str(prov.get("provider_failure_class") or "").strip()

    status = "ok"
    if fail_i and fail_i > 0:
        status = "warn"
    elif not configured:
        status = "unknown"

    lines = [
        f"مزود مُهيّأ: {'نعم' if configured else 'لا (وضع تجريبي/معطّل)'}",
    ]
    if fail_i is not None:
        lines.append(f"فشل إرسال (24 ساعة): {fail_i}")
    else:
        lines.append("فشل إرسال (24 ساعة): غير متاح حالياً")
    if failure_class:
        lines.append(f"آخر تصنيف فشل مزود: {failure_class}")
    else:
        lines.append("آخر فشل مزود: لا يوجد تصنيف حديث")

    return {
        "status": status,
        "status_label_ar": "تنبيه" if status == "warn" else ("غير معروف" if status == "unknown" else "سليم"),
        "configured": configured,
        "recent_failed_24h": fail_i,
        "last_provider_failure_ar": failure_class or "—",
        "detail_lines_ar": lines,
    }


def _build_warnings(
    *,
    cart: dict[str, Any],
    pool: dict[str, Any],
    bg: dict[str, Any],
    wa: dict[str, Any],
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if cart.get("slow_warning"):
        out.append(
            {
                "code": "cart_event_slow",
                "label_ar": "cart-event بطيء — قد يختنق المسار السريع",
                "severity": "warn",
            }
        )
    if int(pool.get("timeout_count") or 0) > 0:
        out.append(
            {
                "code": "db_pool_timeout",
                "label_ar": "انتهاء مهلة مسبح الاتصالات (QueuePool)",
                "severity": "warn",
            }
        )
    if int(pool.get("timeout_count") or 0) >= 2:
        out.append(
            {
                "code": "db_pool_pressure",
                "label_ar": "ضغط على مسبح قاعدة البيانات",
                "severity": "warn",
            }
        )
    if int(bg.get("background_error_count") or 0) > 0 or bg.get("status") == "warn":
        out.append(
            {
                "code": "background_task_failure",
                "label_ar": "إشارة فشل أو ضعف في المهام الخلفية/الجدولة",
                "severity": "warn",
            }
        )
    if wa.get("status") == "warn":
        out.append(
            {
                "code": "whatsapp_failure",
                "label_ar": "فشل إرسال واتساب حديث أو مزود غير جاهز",
                "severity": "warn",
            }
        )
    return out


def _headline_answers(warnings: list[dict[str, str]], admin_rt: dict[str, Any]) -> dict[str, str]:
    choke = "لا — لا مؤشرات اختناق حادة في اللحظة الحالية"
    where = "لا موضع محدد"
    risk = "لا مؤشر خطر حديث"
    intervene = "لا — مراقبة روتينية كافية"

    if warnings:
        choke = "ربما — راجع البطاقات الملوّنة أدناه"
        codes = {w.get("code") for w in warnings}
        parts = []
        if "cart_event_slow" in codes:
            parts.append("مسار cart-event")
        if "db_pool_timeout" in codes or "db_pool_pressure" in codes:
            parts.append("مسبح قاعدة البيانات")
        if "background_task_failure" in codes:
            parts.append("المهام الخلفية/الجدولة")
        if "whatsapp_failure" in codes:
            parts.append("واتساب/المزود")
        where = " — ".join(parts) if parts else "عام — راجع التحذيرات"
        risk = warnings[-1].get("label_ar") or risk
        intervene = "نعم — يُفضَّل مراجعة فنية عند استمرار التحذيرات"

    if not bool(admin_rt.get("recovery_runtime_ok")):
        choke = "احتمال ضغط — مسار الاسترداد غير نشط"
        intervene = "نعم — تحقق من اتصال القاعدة والبيئة"

    return {
        "is_choked_ar": choke,
        "bottleneck_ar": where,
        "last_risk_ar": risk,
        "needs_intervention_ar": intervene,
    }


def _count_slow_cart_events() -> int:
    with _lock:
        samples = list(_cart_event_samples)
    return sum(1 for s in samples if float(s.get("duration_ms") or 0) >= _CART_EVENT_SLOW_MS)


def get_operational_timeline_source_events() -> list[dict[str, Any]]:
    """Events for operational timeline (newest sort done by caller)."""
    events: list[dict[str, Any]] = []
    with _lock:
        for t in _pool_timeout_events:
            events.append(
                {
                    "recorded_at_utc": t.get("recorded_at_utc"),
                    "kind": "pool",
                    "message_ar": "ارتفع ضغط QueuePool — انتهاء مهلة مسبح",
                }
            )
        for s in _cart_event_samples:
            ms = float(s.get("duration_ms") or 0)
            if ms >= _CART_EVENT_SLOW_MS:
                events.append(
                    {
                        "recorded_at_utc": s.get("recorded_at_utc"),
                        "kind": "cart_event",
                        "message_ar": f"cart-event بطيء ({ms:.0f} مللي ثانية)",
                    }
                )
    try:
        from services.cartflow_runtime_health import drain_recent_anomalies

        for a in drain_recent_anomalies(limit=15):
            events.append(
                {
                    "recorded_at_utc": a.get("recorded_at_utc"),
                    "kind": "anomaly",
                    "message_ar": f"إشارة: {a.get('type', '—')}",
                }
            )
    except Exception:
        pass
    if not events:
        events.append(
            {
                "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "kind": "stable",
                "message_ar": "المزود والمسار مستقران",
            }
        )
    return events


def build_operational_control_context() -> "OperationalControlContext":
    from services.admin_operational_control.context import OperationalControlContext

    _maybe_install_pool_error_listener()

    admin_rt: dict[str, Any] = {}
    try:
        from services.cartflow_runtime_health import build_admin_runtime_summary

        admin_rt = build_admin_runtime_summary()
    except Exception:
        admin_rt = {}

    admin_summary: dict[str, Any] = {}
    try:
        from services.cartflow_admin_operational_summary import (
            build_admin_operational_summary_readonly,
        )

        admin_summary = build_admin_operational_summary_readonly()
    except Exception:
        admin_summary = {}

    cart = _cart_event_card()
    pool = _db_pool_card()
    bg = _background_tasks_card(admin_rt)
    wa = _whatsapp_card(admin_rt)
    warnings = _build_warnings(cart=cart, pool=pool, bg=bg, wa=wa)

    prov = admin_rt.get("provider") if isinstance(admin_rt.get("provider"), dict) else {}
    wa_fail = prov.get("recent_send_failures_24h")
    wa_fail_i = int(wa_fail) if isinstance(wa_fail, int) and wa_fail >= 0 else None
    provider_unstable = bool(
        (wa_fail_i and wa_fail_i > 0)
        or not bool(prov.get("configured"))
        or bool(str(prov.get("provider_failure_class") or "").strip())
    )

    affected = 0
    rows = admin_summary.get("store_operational_rows")
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            if str(row.get("trust_bucket") or "") in (
                "degraded",
                "unstable",
                "partially_ready",
            ):
                affected += 1
    if affected == 0 and warnings:
        affected = min(int(admin_summary.get("stores_scanned_for_trust") or 1), 3)

    return OperationalControlContext(
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        admin_rt=admin_rt,
        admin_summary=admin_summary,
        cart=cart,
        pool=pool,
        bg=bg,
        wa=wa,
        warnings=warnings,
        affected_stores_estimate=affected,
        slow_cart_event_count=_count_slow_cart_events(),
        pool_timeout_count=int(pool.get("timeout_count") or 0),
        whatsapp_failed_24h=wa_fail_i,
        background_failure_count=int(bg.get("background_error_count") or 0),
        provider_unstable=provider_unstable,
    )


def build_admin_operational_health_readonly() -> dict[str, Any]:
    """
    Aggregate for GET /admin/operational-health — v2 control + v1 diagnostics.
    """
    from services.admin_operational_control import build_admin_operational_control_readonly

    control = build_admin_operational_control_readonly()
    diag = control.get("diagnostics_v1") or {}
    warnings = diag.get("warnings") or []
    admin_rt = {}
    try:
        from services.cartflow_runtime_health import build_admin_runtime_summary

        admin_rt = build_admin_runtime_summary()
    except Exception:
        pass
    headlines = _headline_answers(warnings, admin_rt)
    anomaly_ct = recent_anomaly_type_counts(limit=50)

    return {
        **control,
        "generated_at_utc": control.get("generated_at_utc"),
        "headlines": headlines,
        "cards": diag.get("cards") or {},
        "warnings": warnings,
        "anomaly_types_preview": anomaly_ct,
        "needs_technical_attention": bool(
            (control.get("admin_risk_summary") or {}).get("actual_risk")
        ),
    }
