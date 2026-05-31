# -*- coding: utf-8 -*-
"""
Admin Operations Center v1 — read-only operational truth for /admin/operations.

Uses existing models and scheduler health only; no recovery/WhatsApp behavior changes.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, RecoverySchedule, Store

_MAX_STORES = 400
_RECENT_CART_DAYS = 7
_MAX_ALERTS = 40

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


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _naive_now() -> datetime:
    return _utc_now().replace(tzinfo=None)


def _safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return default


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
            is_ready = bool(ev.get("ready"))
            store_id = int(getattr(st, "id", 0) or 0)
            has_recent = store_id in recent_store_ids if store_id else False
            first_cart = bool(milestones.get("first_cart_detected"))

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
                    "store_slug": slug[:128],
                    "display_name": name[:128],
                    "ready": is_ready,
                    "blocking_steps": blocking,
                    "has_recent_cart_activity": has_recent,
                    "first_cart_detected": first_cart,
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


def _schedule_alerts_by_store(*, status_filter: Any, limit: int = 12) -> list[tuple[str, int]]:
    try:
        db.create_all()
        rows = (
            db.session.query(
                RecoverySchedule.store_slug,
                func.count(RecoverySchedule.id),
            )
            .filter(status_filter)
            .group_by(RecoverySchedule.store_slug)
            .order_by(func.count(RecoverySchedule.id).desc())
            .limit(max(1, int(limit)))
            .all()
        )
        return [
            (str(slug or "").strip()[:128], _safe_int(cnt))
            for slug, cnt in rows
            if str(slug or "").strip()
        ]
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _build_basic_alerts(
    *,
    scheduler: dict[str, Any],
    recovery: dict[str, Any],
    stores: list[dict[str, Any]],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    now_naive = _naive_now()
    cutoff_stale = (_utc_now() - timedelta(seconds=600)).replace(tzinfo=None)

    stale_by_store = _schedule_alerts_by_store(
        status_filter=(
            (RecoverySchedule.status == "scheduled")
            & (RecoverySchedule.due_at <= now_naive)
        ),
        limit=10,
    )
    running_stale_by_store = _schedule_alerts_by_store(
        status_filter=(
            (RecoverySchedule.status == "running")
            & (RecoverySchedule.updated_at < cutoff_stale)
        ),
        limit=10,
    )
    failed_by_store = _schedule_alerts_by_store(
        status_filter=RecoverySchedule.status.in_(tuple(_FAILED_STATUSES)),
        limit=10,
    )

    overdue = _safe_int(scheduler.get("overdue_scheduled_count"))
    running_stale = _safe_int(scheduler.get("running_stale_count"))
    if overdue > 0 and not stale_by_store:
        alerts.append(
            {
                "kind": "stale_recovery",
                "severity": "warning",
                "title_ar": "استرجاع متأخر",
                "detail_ar": f"يوجد {overdue} جدولة متأخرة عن موعدها.",
            }
        )
    for slug, cnt in stale_by_store:
        alerts.append(
            {
                "kind": "stale_recovery",
                "severity": "warning",
                "title_ar": "استرجاع متأخر",
                "detail_ar": f"المتجر {slug}: {cnt} جدولة متأخرة.",
            }
        )
    if running_stale > 0 and not running_stale_by_store:
        alerts.append(
            {
                "kind": "stale_recovery",
                "severity": "warning",
                "title_ar": "تشغيل عالق",
                "detail_ar": f"يوجد {running_stale} جدولة في حالة running بدون تحديث حديث.",
            }
        )
    for slug, cnt in running_stale_by_store:
        alerts.append(
            {
                "kind": "stale_recovery",
                "severity": "warning",
                "title_ar": "تشغيل عالق",
                "detail_ar": f"المتجر {slug}: {cnt} جدولة running قديمة.",
            }
        )

    failed_total = _safe_int(recovery.get("failed"))
    if failed_total > 0 and not failed_by_store:
        alerts.append(
            {
                "kind": "failed_recovery",
                "severity": "danger",
                "title_ar": "استرجاع فاشل",
                "detail_ar": f"إجمالي الجدولات الفاشلة: {failed_total}.",
            }
        )
    for slug, cnt in failed_by_store:
        alerts.append(
            {
                "kind": "failed_recovery",
                "severity": "danger",
                "title_ar": "استرجاع فاشل",
                "detail_ar": f"المتجر {slug}: {cnt} جدولة فاشلة.",
            }
        )

    for st in stores:
        slug = st.get("store_slug") or ""
        name = st.get("display_name") or slug or "متجر"
        blocking = st.get("blocking_steps") or []
        blocking_set = {str(x).strip() for x in blocking if str(x).strip()}
        if not st.get("ready"):
            alerts.append(
                {
                    "kind": "store_needs_setup",
                    "severity": "info",
                    "title_ar": "متجر يحتاج إعداد",
                    "detail_ar": f"{name} ({slug or '—'}) — لم يكتمل الإعداد بعد.",
                }
            )
        if "whatsapp_not_connected" in blocking_set or "provider_not_ready" in blocking_set:
            alerts.append(
                {
                    "kind": "whatsapp_missing",
                    "severity": "warning",
                    "title_ar": "واتساب غير مكتمل",
                    "detail_ar": f"{name} ({slug or '—'}) — إعداد واتساب/المزود ناقص.",
                }
            )
        if not st.get("has_recent_cart_activity") and not st.get("first_cart_detected"):
            alerts.append(
                {
                    "kind": "no_cart_events",
                    "severity": "info",
                    "title_ar": "لا أحداث سلة حديثة",
                    "detail_ar": f"{name} ({slug or '—'}) — لا سلال حديثة خلال {_RECENT_CART_DAYS} أيام.",
                }
            )
        if len(alerts) >= _MAX_ALERTS:
            break

    return alerts[:_MAX_ALERTS]


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

    return {
        "version": "admin_operations_center_v1",
        "generated_at_utc": _utc_now().isoformat(),
        "scheduler": scheduler,
        "recovery": recovery,
        "store_readiness": store_readiness,
        "alerts": alerts,
        "health_scheduler_path": "/health/scheduler",
    }


__all__ = ["build_admin_operations_center_v1_readonly"]
