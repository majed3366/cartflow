# -*- coding: utf-8 -*-
"""
Admin Operations Center v1 — read-only operational truth for /admin/operations.

Uses existing models and scheduler health only; no recovery/WhatsApp behavior changes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, RecoverySchedule, Store
from services.cartflow_onboarding_readiness import BLOCKER_COPY

_MAX_STORES = 400
_RECENT_CART_DAYS = 7
_MAX_ALERTS = 40
_MAX_RECORDS_PER_ALERT = 5
_MAX_SCHEDULE_ROWS_FETCH = 80
_RUNNING_STALE_SECONDS = 600

# RecoverySchedule terminal / failure buckets (read-only aggregates).
_FAILED_STATUSES = frozenset(
    {
        "failed_resume",
        "failed_resume_stale",
        "whatsapp_failed",
    }
)
_EXPIRED_STATUSES = frozenset(
    {
        "cancelled",
        "failed_resume_stale",
        "skipped_resume_unsafe",
    }
)

# Read-only admin copy — why + suggested fix per alert kind (v1.2).
_ALERT_EXPLANATIONS_AR: dict[str, dict[str, str]] = {
    "store_needs_setup": {
        "why_ar": "ظهر هذا التنبيه لأن المتجر لم يكمل إعداداته الأساسية بعد.",
        "suggested_fix_ar": (
            "راجع إعدادات المتجر وأكمل الحقول الناقصة قبل تفعيل الاسترجاع."
        ),
    },
    "whatsapp_missing": {
        "why_ar": "ظهر هذا التنبيه لأن المتجر لا يملك إعداد واتساب جاهزًا للإرسال.",
        "suggested_fix_ar": (
            "أكمل ربط مزود واتساب أو رقم الإرسال قبل تشغيل الاسترجاع الفعلي."
        ),
    },
    "no_cart_events": {
        "why_ar": (
            "ظهر هذا التنبيه لأن النظام لم يستقبل أحداث سلة حديثة "
            "لهذا المتجر خلال آخر 7 أيام."
        ),
        "suggested_fix_ar": (
            "تحقق من تركيب الودجيت أو التكامل، ثم اختبر إضافة منتج للسلة "
            "للتأكد من وصول الأحداث."
        ),
    },
    "failed_recovery": {
        "why_ar": "ظهر هذا التنبيه لأن محاولة استرجاع واحدة أو أكثر انتهت بحالة فشل.",
        "suggested_fix_ar": (
            "راجع تفاصيل الاسترجاع والخطأ المختصر، ثم تحقق من مزود واتساب "
            "أو بيانات العميل قبل إعادة المحاولة يدويًا."
        ),
    },
    "stale_recovery": {
        "why_ar": (
            "ظهر هذا التنبيه لأن هناك استرجاعًا عالقًا في حالة تشغيل "
            "لمدة أطول من المتوقع."
        ),
        "suggested_fix_ar": (
            "راجع مفتاح الاسترجاع ووقت آخر تحديث، ثم تحقق من حالة "
            "الـ Scheduler قبل اتخاذ أي إجراء."
        ),
    },
}

# Operational severity + priority per alert kind (v1.3).
_ALERT_SEVERITY_AR: dict[str, dict[str, Any]] = {
    "stale_recovery": {
        "severity": "critical",
        "severity_ar": "حرج",
        "priority_order": 10,
    },
    "failed_recovery": {
        "severity": "high",
        "severity_ar": "عالي",
        "priority_order": 20,
    },
    "whatsapp_missing": {
        "severity": "high",
        "severity_ar": "عالي",
        "priority_order": 30,
    },
    "store_needs_setup": {
        "severity": "medium",
        "severity_ar": "متوسط",
        "priority_order": 40,
    },
    "no_cart_events": {
        "severity": "low",
        "severity_ar": "منخفض",
        "priority_order": 50,
    },
}

_DEFAULT_ALERT_SEVERITY: dict[str, Any] = {
    "severity": "low",
    "severity_ar": "منخفض",
    "priority_order": 999,
}

_VALID_SEVERITY_BUCKETS = frozenset({"critical", "high", "medium", "low"})

_SYSTEM_HEALTH_STATUS_AR: dict[str, dict[str, str]] = {
    "urgent_attention": {
        "status_ar": "تحتاج انتباه عاجل",
        "description_ar": (
            "توجد تنبيهات حرجة تحتاج مراجعة قبل الاعتماد على التشغيل الطبيعي."
        ),
    },
    "needs_followup": {
        "status_ar": "تحتاج متابعة",
        "description_ar": (
            "توجد تنبيهات عالية الأهمية، لكن لا توجد مؤشرات حرجة حاليًا."
        ),
    },
    "stable_with_notes": {
        "status_ar": "مستقرة مع ملاحظات",
        "description_ar": (
            "النظام يعمل، مع وجود ملاحظات تشغيلية يمكن مراجعتها."
        ),
    },
    "stable": {
        "status_ar": "مستقرة",
        "description_ar": "لا توجد تنبيهات تشغيلية ظاهرة حاليًا.",
    },
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive_now() -> datetime:
    return _utc_now().replace(tzinfo=None)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return default


def _safe_str(val: Any, max_len: int = 256) -> str:
    try:
        s = str(val or "").strip()
    except Exception:  # noqa: BLE001
        return ""
    if not s:
        return ""
    return s[:max_len]


def _fmt_dt(val: Any) -> str | None:
    if val is None:
        return None
    try:
        if isinstance(val, datetime):
            dt = val
        else:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, AttributeError):
        return None


def _blocking_labels_ar(codes: list[str]) -> list[str]:
    labels: list[str] = []
    for code in codes:
        key = _safe_str(code, 128)
        if not key:
            continue
        title = (BLOCKER_COPY.get(key) or {}).get("title_ar")
        labels.append(title or key)
    return labels


def _severity_for_kind(kind: str) -> dict[str, Any]:
    meta = _ALERT_SEVERITY_AR.get(kind) or {}
    return {
        "severity": str(meta.get("severity") or _DEFAULT_ALERT_SEVERITY["severity"]),
        "severity_ar": str(meta.get("severity_ar") or _DEFAULT_ALERT_SEVERITY["severity_ar"]),
        "priority_order": _safe_int(
            meta.get("priority_order"), _DEFAULT_ALERT_SEVERITY["priority_order"]
        ),
    }


def _sort_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """priority_order asc → records_total desc → kind → title_ar."""

    def _key(alert: dict[str, Any]) -> tuple[int, int, str, str]:
        sev = _severity_for_kind(str(alert.get("kind") or ""))
        priority = _safe_int(alert.get("priority_order"), sev["priority_order"])
        total = _safe_int(alert.get("records_total"), 0)
        kind = str(alert.get("kind") or "")
        title = str(alert.get("title_ar") or "")
        return (priority, -total, kind, title)

    return sorted(alerts, key=_key)


def _alert_severity_bucket(alert: dict[str, Any]) -> str:
    """Normalize alert severity; unknown values count as low."""
    sev = _safe_str(alert.get("severity"), 32).lower()
    if sev in _VALID_SEVERITY_BUCKETS:
        return sev
    return str(_severity_for_kind(str(alert.get("kind") or ""))["severity"])


def _build_system_health_summary(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """Top-level operational health derived from alert severities (read-only)."""
    critical_count = 0
    high_count = 0
    medium_count = 0
    low_count = 0
    for alert in alerts or []:
        bucket = _alert_severity_bucket(alert if isinstance(alert, dict) else {})
        if bucket == "critical":
            critical_count += 1
        elif bucket == "high":
            high_count += 1
        elif bucket == "medium":
            medium_count += 1
        else:
            low_count += 1

    total_alerts = critical_count + high_count + medium_count + low_count

    if critical_count > 0:
        status_key = "urgent_attention"
        highest_severity = "critical"
    elif high_count > 0:
        status_key = "needs_followup"
        highest_severity = "high"
    elif medium_count > 0 or low_count > 0:
        status_key = "stable_with_notes"
        highest_severity = "medium" if medium_count > 0 else "low"
    else:
        status_key = "stable"
        highest_severity = "none"

    copy = _SYSTEM_HEALTH_STATUS_AR.get(status_key) or _SYSTEM_HEALTH_STATUS_AR["stable"]
    return {
        "status_key": status_key,
        "status_ar": copy["status_ar"],
        "description_ar": copy["description_ar"],
        "highest_severity": highest_severity,
        "critical_count": critical_count,
        "high_count": high_count,
        "medium_count": medium_count,
        "low_count": low_count,
        "total_alerts": total_alerts,
    }


def _alert_with_records(
    *,
    kind: str,
    title_ar: str,
    detail_ar: str,
    records: list[dict[str, Any]] | None = None,
    records_total: int | None = None,
    why_ar: str | None = None,
    suggested_fix_ar: str | None = None,
) -> dict[str, Any]:
    recs = list(records or [])
    total = _safe_int(records_total, len(recs))
    shown = recs[:_MAX_RECORDS_PER_ALERT]
    hidden = max(0, total - len(shown))
    expl = _ALERT_EXPLANATIONS_AR.get(kind) or {}
    sev = _severity_for_kind(kind)
    return {
        "kind": kind,
        "severity": sev["severity"],
        "severity_ar": sev["severity_ar"],
        "priority_order": sev["priority_order"],
        "title_ar": title_ar,
        "detail_ar": detail_ar,
        "why_ar": why_ar or expl.get("why_ar") or "",
        "suggested_fix_ar": suggested_fix_ar or expl.get("suggested_fix_ar") or "",
        "records": shown,
        "records_total": total,
        "records_hidden": hidden,
    }


def _recovery_status_summary() -> dict[str, Any]:
    """Single group_by on RecoverySchedule.status."""
    out: dict[str, Any] = {
        "scheduled": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "expired": 0,
        "available": True,
    }
    try:
        db.create_all()
        counts: dict[str, int] = {}
        for st, cnt in (
            db.session.query(RecoverySchedule.status, func.count(RecoverySchedule.id))
            .group_by(RecoverySchedule.status)
            .all()
        ):
            key = str(st or "").strip().lower()
            if key:
                counts[key] = _safe_int(cnt)
        out["scheduled"] = counts.get("scheduled", 0)
        out["running"] = counts.get("running", 0)
        out["completed"] = counts.get("completed", 0)
        out["failed"] = sum(counts.get(s, 0) for s in _FAILED_STATUSES)
        out["expired"] = sum(counts.get(s, 0) for s in _EXPIRED_STATUSES)
        out["by_status"] = counts
    except SQLAlchemyError as exc:
        db.session.rollback()
        out["available"] = False
        out["error"] = str(exc)[:200]
    return out


def _last_cart_event_by_store_id() -> dict[int, datetime]:
    """One aggregate query: max(last_seen_at) per store."""
    out: dict[int, datetime] = {}
    try:
        db.create_all()
        for store_id, last_at in (
            db.session.query(
                AbandonedCart.store_id,
                func.max(AbandonedCart.last_seen_at),
            )
            .filter(AbandonedCart.store_id.isnot(None))
            .group_by(AbandonedCart.store_id)
            .all()
        ):
            if store_id is None or last_at is None:
                continue
            try:
                out[int(store_id)] = last_at
            except (TypeError, ValueError):
                pass
    except SQLAlchemyError:
        db.session.rollback()
    return out


def _store_readiness_summary() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    summary: dict[str, Any] = {
        "total_stores": 0,
        "ready_stores": 0,
        "stores_missing_whatsapp": 0,
        "stores_no_recent_cart_events": 0,
        "stores_needing_setup": 0,
        "available": True,
    }
    per_store: list[dict[str, Any]] = []
    try:
        db.create_all()
        total = _safe_int(db.session.query(func.count(Store.id)).scalar())
        summary["total_stores"] = total

        store_rows = (
            db.session.query(Store).order_by(Store.id.desc()).limit(_MAX_STORES).all()
        )
        cutoff = _naive_now() - timedelta(days=_RECENT_CART_DAYS)
        recent_store_ids: set[int] = set()
        for row in (
            db.session.query(AbandonedCart.store_id)
            .filter(
                AbandonedCart.store_id.isnot(None),
                AbandonedCart.last_seen_at >= cutoff,
            )
            .distinct()
            .all()
        ):
            sid = row[0] if row else None
            if sid is not None:
                try:
                    recent_store_ids.add(int(sid))
                except (TypeError, ValueError):
                    pass

        last_event_by_store = _last_cart_event_by_store_id()

        ready_n = 0
        wa_missing_n = 0
        no_events_n = 0
        setup_n = 0

        for st in store_rows:
            ev = evaluate_onboarding_readiness(st)
            slug = (getattr(st, "zid_store_id", None) or "").strip()
            name = (getattr(st, "widget_name", None) or "").strip() or slug or "متجر"
            blocking = list(ev.get("blocking_steps") or [])
            blocking_set = {str(x).strip() for x in blocking if str(x).strip()}
            milestones = ev.get("milestones") if isinstance(ev.get("milestones"), dict) else {}
            flags = ev.get("flags") if isinstance(ev.get("flags"), dict) else {}
            is_ready = bool(ev.get("ready"))
            store_id = int(getattr(st, "id", 0) or 0)
            has_recent = store_id in recent_store_ids if store_id else False
            first_cart = bool(milestones.get("first_cart_detected"))
            last_cart_at = last_event_by_store.get(store_id) if store_id else None

            if is_ready:
                ready_n += 1
            else:
                setup_n += 1
            if "whatsapp_not_connected" in blocking_set or "provider_not_ready" in blocking_set:
                wa_missing_n += 1
            if not has_recent and not first_cart:
                no_events_n += 1

            per_store.append(
                {
                    "store_id": store_id,
                    "store_slug": slug[:128],
                    "display_name": name[:128],
                    "ready": is_ready,
                    "readiness_status_ar": _safe_str(ev.get("merchant_status_ar"), 200),
                    "readiness_percent": _safe_int(ev.get("completion_percent")),
                    "blocking_steps": blocking,
                    "missing_setup_labels_ar": _blocking_labels_ar(blocking),
                    "has_recent_cart_activity": has_recent,
                    "first_cart_detected": first_cart,
                    "last_cart_event_at": _fmt_dt(last_cart_at),
                    "recent_window_days": _RECENT_CART_DAYS,
                    "whatsapp_configured": bool(flags.get("whatsapp_configured")),
                    "whatsapp_provider_ready": bool(flags.get("provider_ready")),
                    "whatsapp_missing": (
                        "whatsapp_not_connected" in blocking_set
                        or "provider_not_ready" in blocking_set
                    ),
                }
            )

        summary["ready_stores"] = ready_n
        summary["stores_missing_whatsapp"] = wa_missing_n
        summary["stores_no_recent_cart_events"] = no_events_n
        summary["stores_needing_setup"] = setup_n
        summary["_scan_cap"] = _MAX_STORES
    except SQLAlchemyError as exc:
        db.session.rollback()
        summary["available"] = False
        summary["error"] = str(exc)[:200]
    except Exception as exc:  # noqa: BLE001
        summary["available"] = False
        summary["error"] = str(exc)[:200]
    return summary, per_store


def _fetch_schedule_rows(*, status_filter: Any) -> list[Any]:
    try:
        db.create_all()
        return (
            db.session.query(
                RecoverySchedule.recovery_key,
                RecoverySchedule.store_slug,
                RecoverySchedule.status,
                RecoverySchedule.updated_at,
                RecoverySchedule.due_at,
                RecoverySchedule.last_error,
            )
            .filter(status_filter)
            .order_by(RecoverySchedule.updated_at.asc())
            .limit(_MAX_SCHEDULE_ROWS_FETCH)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _recovery_record(
    row: Any,
    *,
    stale_reason_ar: str | None = None,
) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "recovery_key": _safe_str(getattr(row, "recovery_key", None), 512),
        "store_slug": _safe_str(getattr(row, "store_slug", None), 128),
        "status": _safe_str(getattr(row, "status", None), 64),
        "updated_at": _fmt_dt(getattr(row, "updated_at", None)) or "غير متوفر",
    }
    due = _fmt_dt(getattr(row, "due_at", None))
    if due:
        rec["due_at"] = due
    if stale_reason_ar:
        rec["stale_reason_ar"] = stale_reason_ar
    err = _safe_str(getattr(row, "last_error", None), 120)
    if err:
        rec["extra_detail_ar"] = err
    return rec


def _group_recovery_alerts(
    *,
    rows: list[Any],
    kind: str,
    title_ar: str,
    stale_reason_ar: str | None = None,
) -> list[dict[str, Any]]:
    by_store: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        slug = _safe_str(getattr(row, "store_slug", None), 128) or "—"
        by_store[slug].append(
            _recovery_record(row, stale_reason_ar=stale_reason_ar)
        )
    alerts: list[dict[str, Any]] = []
    for slug, recs in sorted(by_store.items(), key=lambda x: (-len(x[1]), x[0])):
        cnt = len(recs)
        alerts.append(
            _alert_with_records(
                kind=kind,
                title_ar=title_ar,
                detail_ar=f"المتجر {slug}: {cnt} جدولة.",
                records=recs,
                records_total=cnt,
            )
        )
    return alerts


def _store_setup_record(st: dict[str, Any]) -> dict[str, Any]:
    slug = st.get("store_slug") or ""
    name = st.get("display_name") or slug or "متجر"
    return {
        "store_slug": slug,
        "display_name": name,
        "readiness_ready": bool(st.get("ready")),
        "readiness_status_ar": st.get("readiness_status_ar") or "غير متوفر",
        "readiness_percent": st.get("readiness_percent"),
        "missing_setup_fields": list(st.get("blocking_steps") or []),
        "missing_setup_labels_ar": list(st.get("missing_setup_labels_ar") or []),
    }


def _whatsapp_record(st: dict[str, Any]) -> dict[str, Any]:
    slug = st.get("store_slug") or ""
    name = st.get("display_name") or slug or "متجر"
    wa_flags: list[str] = []
    if not st.get("whatsapp_configured"):
        wa_flags.append("واتساب غير مفعّل")
    if not st.get("whatsapp_provider_ready"):
        wa_flags.append("المزود غير جاهز")
    return {
        "store_slug": slug,
        "display_name": name,
        "whatsapp_missing": True,
        "whatsapp_status": {
            "configured": bool(st.get("whatsapp_configured")),
            "provider_ready": bool(st.get("whatsapp_provider_ready")),
        },
        "whatsapp_flags_ar": wa_flags or ["غير متوفر"],
    }


def _no_cart_events_record(st: dict[str, Any]) -> dict[str, Any]:
    slug = st.get("store_slug") or ""
    name = st.get("display_name") or slug or "متجر"
    return {
        "store_slug": slug,
        "display_name": name,
        "last_cart_event_at": st.get("last_cart_event_at") or "غير متوفر",
        "recent_window_days": _safe_int(st.get("recent_window_days"), _RECENT_CART_DAYS),
    }


def _build_basic_alerts(
    *,
    scheduler: dict[str, Any],
    recovery: dict[str, Any],
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    now_naive = _naive_now()
    cutoff_stale = (_utc_now() - timedelta(seconds=_RUNNING_STALE_SECONDS)).replace(
        tzinfo=None
    )

    overdue_rows = _fetch_schedule_rows(
        status_filter=(
            (RecoverySchedule.status == "scheduled")
            & (RecoverySchedule.due_at <= now_naive)
        ),
    )
    running_stale_rows = _fetch_schedule_rows(
        status_filter=(
            (RecoverySchedule.status == "running")
            & (RecoverySchedule.updated_at < cutoff_stale)
        ),
    )
    failed_rows = _fetch_schedule_rows(
        status_filter=RecoverySchedule.status.in_(tuple(_FAILED_STATUSES)),
    )

    overdue = _safe_int(scheduler.get("overdue_scheduled_count"))
    running_stale = _safe_int(scheduler.get("running_stale_count"))

    if overdue_rows:
        alerts.extend(
            _group_recovery_alerts(
                rows=overdue_rows,
                kind="stale_recovery",
                title_ar="استرجاع متأخر",
                stale_reason_ar="متأخرة عن موعد الاستحقاق",
            )
        )
    elif overdue > 0:
        alerts.append(
            _alert_with_records(
                kind="stale_recovery",
                title_ar="استرجاع متأخر",
                detail_ar=f"يوجد {overdue} جدولة متأخرة عن موعدها.",
            )
        )

    if running_stale_rows:
        alerts.extend(
            _group_recovery_alerts(
                rows=running_stale_rows,
                kind="stale_recovery",
                title_ar="تشغيل عالق",
                stale_reason_ar="running بدون تحديث حديث",
            )
        )
    elif running_stale > 0:
        alerts.append(
            _alert_with_records(
                kind="stale_recovery",
                title_ar="تشغيل عالق",
                detail_ar=(
                    f"يوجد {running_stale} جدولة في حالة running "
                    "بدون تحديث حديث."
                ),
            )
        )

    failed_total = _safe_int(recovery.get("failed"))
    if failed_rows:
        alerts.extend(
            _group_recovery_alerts(
                rows=failed_rows,
                kind="failed_recovery",
                title_ar="استرجاع فاشل",
            )
        )
    elif failed_total > 0:
        alerts.append(
            _alert_with_records(
                kind="failed_recovery",
                title_ar="استرجاع فاشل",
                detail_ar=f"إجمالي الجدولات الفاشلة: {failed_total}.",
            )
        )

    for st in stores:
        slug = st.get("store_slug") or ""
        name = st.get("display_name") or slug or "متجر"
        if not st.get("ready"):
            alerts.append(
                _alert_with_records(
                    kind="store_needs_setup",
                    title_ar="متجر يحتاج إعداد",
                    detail_ar=f"{name} — لم يكتمل الإعداد بعد.",
                    records=[_store_setup_record(st)],
                    records_total=1,
                )
            )
        if st.get("whatsapp_missing"):
            alerts.append(
                _alert_with_records(
                    kind="whatsapp_missing",
                    title_ar="واتساب غير مكتمل",
                    detail_ar=f"{name} — إعداد واتساب/المزود ناقص.",
                    records=[_whatsapp_record(st)],
                    records_total=1,
                )
            )
        if not st.get("has_recent_cart_activity") and not st.get("first_cart_detected"):
            alerts.append(
                _alert_with_records(
                    kind="no_cart_events",
                    title_ar="لا أحداث سلة حديثة",
                    detail_ar=(
                        f"{name} — لا سلال حديثة خلال "
                        f"{_RECENT_CART_DAYS} أيام."
                    ),
                    records=[_no_cart_events_record(st)],
                    records_total=1,
                )
            )
        if len(alerts) >= _MAX_ALERTS * 2:
            break

    return _sort_alerts(alerts)[:_MAX_ALERTS]


def build_admin_operations_center_v1_readonly() -> dict[str, Any]:
    """Read-only payload for Admin Operations Center v1."""
    from services.recovery_process_role_v1 import build_scheduler_health_snapshot

    scheduler_raw = build_scheduler_health_snapshot()
    scheduler: dict[str, Any] = {
        "role": str(scheduler_raw.get("role") or "غير متوفر"),
        "overdue_scheduled_count": _safe_int(scheduler_raw.get("overdue_scheduled_count")),
        "running_stale_count": _safe_int(scheduler_raw.get("running_stale_count")),
        "resume_enabled": bool(scheduler_raw.get("resume_enabled")),
        "due_scanner_enabled": bool(scheduler_raw.get("due_scanner_enabled")),
        "ok": bool(scheduler_raw.get("ok", True)),
    }
    if scheduler_raw.get("database_error"):
        scheduler["database_error"] = str(scheduler_raw.get("database_error"))[:200]

    recovery = _recovery_status_summary()
    store_readiness, store_rows = _store_readiness_summary()
    alerts = _build_basic_alerts(
        scheduler=scheduler,
        recovery=recovery,
        stores=store_rows,
    )
    system_health_summary = _build_system_health_summary(alerts)

    return {
        "version": "admin_operations_center_v1_4",
        "generated_at_utc": _utc_now().isoformat(),
        "system_health_summary": system_health_summary,
        "scheduler": scheduler,
        "recovery": recovery,
        "store_readiness": store_readiness,
        "alerts": alerts,
        "health_scheduler_path": "/health/scheduler",
    }


__all__ = [
    "build_admin_operations_center_v1_readonly",
    "_ALERT_SEVERITY_AR",
    "_sort_alerts",
    "_build_system_health_summary",
]
