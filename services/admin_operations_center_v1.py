# -*- coding: utf-8 -*-
"""
Admin Operations Center v1 — read-only operational truth for /admin/operations.

Uses existing models and scheduler health only; no recovery/WhatsApp behavior changes.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart, CartRecoveryLog, RecoverySchedule, Store
from services.cartflow_onboarding_readiness import BLOCKER_COPY

# Recovery message log statuses that represent an actual send (read-only display).
_RECOVERY_SENT_LOG_STATUSES = frozenset({"mock_sent", "sent_real"})

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

# Guided investigation steps per alert kind (v2.1).
_INVESTIGATION_STEPS_AR: dict[str, list[str]] = {
    "store_needs_setup": [
        "راجع حالة إعداد المتجر.",
        "تحقق من الحقول الناقصة.",
        "تأكد من اكتمال خطوات التفعيل.",
    ],
    "whatsapp_missing": [
        "تحقق من إعداد واتساب للمتجر.",
        "راجع حالة مزود الإرسال.",
        "تأكد من اكتمال الربط.",
    ],
    "no_cart_events": [
        "تحقق من تحميل الودجيت.",
        "راجع آخر cart event.",
        "اختبر إضافة منتج للسلة.",
    ],
    "stale_recovery": [
        "راجع حالة Scheduler.",
        "تحقق من وقت آخر تحديث.",
        "راجع سجل الاسترجاع.",
    ],
    "failed_recovery": [
        "راجع سبب الفشل.",
        "تحقق من مزود الإرسال.",
        "راجع سجل المحاولة الأخيرة.",
    ],
}

_DEFAULT_INVESTIGATION_STEPS_AR: list[str] = [
    "راجع التفاصيل المتاحة.",
    "تحقق من السجلات المرتبطة.",
]

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

_OPERATIONAL_OWNERS_AR: dict[str, str] = {
    "merchant_setup": "إعداد المتجر",
    "whatsapp_provider": "مزود واتساب",
    "cartflow_system": "نظام CartFlow",
    "scheduler": "المجدول",
    "widget_integration": "الودجيت / التكامل",
    "unknown": "غير محدد",
}

_OWNERSHIP_BY_KIND: dict[str, str] = {
    "store_needs_setup": "merchant_setup",
    "whatsapp_missing": "whatsapp_provider",
    "no_cart_events": "widget_integration",
    "stale_recovery": "scheduler",
    "failed_recovery": "cartflow_system",
}

_VALID_SEVERITY_BUCKETS = frozenset({"critical", "high", "medium", "low"})

_SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}

_SEVERITY_AR_BY_BUCKET: dict[str, str] = {
    "critical": "حرج",
    "high": "عالي",
    "medium": "متوسط",
    "low": "منخفض",
}

_STORE_SNAPSHOT_KINDS = frozenset(
    {
        "store_needs_setup",
        "whatsapp_missing",
        "no_cart_events",
        "failed_recovery",
        "stale_recovery",
    }
)

_MAX_STORE_SNAPSHOT = 150
_TREND_WINDOW_HOURS = 24
_MAX_TOP_RISKS = 5
_MAX_TIMELINE_EVENTS = 25
_MAX_TIMELINE_FETCH = 100

_TIMELINE_EVENT_KINDS = frozenset(
    {
        "stale_recovery",
        "failed_recovery",
        "whatsapp_missing",
        "no_cart_events",
        "store_needs_setup",
    }
)

_TIMELINE_EVENT_COPY: dict[str, dict[str, str]] = {
    "failed_recovery": {
        "title_ar": "فشل استرجاع",
        "short_detail_ar": "تم تسجيل محاولة استرجاع بحالة فشل.",
    },
    "stale_recovery": {
        "title_ar": "استرجاع عالق",
        "short_detail_ar": "تم رصد استرجاع لم يكتمل خلال المدة المتوقعة.",
    },
    "whatsapp_missing": {
        "title_ar": "واتساب غير جاهز",
        "short_detail_ar": "المتجر لا يملك إعداد واتساب صالحًا للإرسال.",
    },
    "no_cart_events": {
        "title_ar": "غياب أحداث السلة",
        "short_detail_ar": "لم يتم رصد أحداث سلة حديثة لهذا المتجر.",
    },
    "store_needs_setup": {
        "title_ar": "إعداد المتجر غير مكتمل",
        "short_detail_ar": "لا تزال هناك خطوات إعداد ناقصة.",
    },
}

_TOP_RISK_KINDS = frozenset(
    {
        "stale_recovery",
        "failed_recovery",
        "whatsapp_missing",
        "no_cart_events",
        "store_needs_setup",
    }
)

_TOP_RISK_COPY: dict[str, dict[str, str]] = {
    "stale_recovery": {
        "risk_title_ar": "استرجاع عالق",
        "why_it_matters_ar": (
            "قد يشير إلى مشكلة تشغيلية تمنع إكمال دورة الاسترجاع."
        ),
        "suggested_next_step_ar": "راجع حالة الـ Scheduler وسجل الاسترجاع.",
    },
    "failed_recovery": {
        "risk_title_ar": "استرجاع فاشل",
        "why_it_matters_ar": "قد يؤدي إلى فقدان فرصة استرجاع سلة محتملة.",
        "suggested_next_step_ar": "راجع تفاصيل الفشل ومزود الإرسال.",
    },
    "whatsapp_missing": {
        "risk_title_ar": "واتساب غير جاهز",
        "why_it_matters_ar": "لن يتمكن المتجر من إرسال رسائل الاسترجاع.",
        "suggested_next_step_ar": "استكمل إعداد واتساب للمتجر.",
    },
    "no_cart_events": {
        "risk_title_ar": "لا توجد أحداث سلة",
        "why_it_matters_ar": "قد يشير إلى مشكلة في الودجيت أو التكامل.",
        "suggested_next_step_ar": "اختبر إضافة منتج للسلة وتحقق من وصول الأحداث.",
    },
    "store_needs_setup": {
        "risk_title_ar": "إعداد المتجر غير مكتمل",
        "why_it_matters_ar": "قد يمنع تشغيل CartFlow بشكل صحيح.",
        "suggested_next_step_ar": "استكمل خطوات الإعداد الأساسية.",
    },
}

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

# Executive "traffic light" tone per system-health status (presentation only).
_PLATFORM_STATUS_TONE: dict[str, str] = {
    "urgent_attention": "action",
    "needs_followup": "watch",
    "stable_with_notes": "ok",
    "stable": "ok",
}

# Business-language framing per operational issue kind (read-only presentation).
# Structure mirrors: Problem → Impact → Where → Owner → Suggested Action → Verification.
_BUSINESS_ISSUE_COPY_AR: dict[str, dict[str, str]] = {
    "stale_recovery": {
        "title_ar": "تأخير في معالجة الاسترجاع",
        "impact_ar": "قد تتأخر رسائل الاسترجاع عن موعدها وتفوت فرصًا على المتاجر.",
        "where_ar": "معالجة الاسترجاع المجدولة",
        "owner_ar": "CartFlow / المجدول",
        "action_ar": "راجع حالة المعالجة المجدولة وتأكد من عدم وجود صفوف عالقة.",
        "verification_ar": "تأكد أن الاسترجاعات المتأخرة عادت إلى المسار الطبيعي.",
    },
    "failed_recovery": {
        "title_ar": "رسائل الاسترجاع لا يتم تسليمها",
        "impact_ar": "قد تفقد المتاجر فرص استرجاع سلات متروكة.",
        "where_ar": "قناة واتساب / إرسال الاسترجاع",
        "owner_ar": "مزود واتساب / CartFlow",
        "action_ar": "راجع حالة مزود التسليم (واتساب).",
        "verification_ar": "تأكد من تسليم آخر رسالة استرجاع بنجاح.",
    },
    "whatsapp_missing": {
        "title_ar": "مشكلة في مزود التسليم",
        "impact_ar": "لن يتمكن المتجر من إرسال رسائل الاسترجاع حتى يكتمل الربط.",
        "where_ar": "إعداد واتساب للمتجر",
        "owner_ar": "المتجر / مزود واتساب",
        "action_ar": "أكمل ربط واتساب ورقم الإرسال للمتجر.",
        "verification_ar": "تأكد أن المتجر أصبح جاهزًا لإرسال واتساب.",
    },
    "store_needs_setup": {
        "title_ar": "متجر يحتاج انتباهًا",
        "impact_ar": "لن يعمل الاسترجاع بشكل صحيح قبل اكتمال الإعداد.",
        "where_ar": "إعداد المتجر والتفعيل",
        "owner_ar": "المتجر",
        "action_ar": "ساعد المتجر على إكمال خطوات الإعداد الأساسية.",
        "verification_ar": "تأكد أن المتجر أصبح في حالة جاهز.",
    },
    "no_cart_events": {
        "title_ar": "لا توجد أحداث سلة حديثة",
        "impact_ar": "قد يشير إلى مشكلة في تركيب الودجيت أو التكامل.",
        "where_ar": "تتبع السلة / الودجيت على المتجر",
        "owner_ar": "الودجيت / التكامل",
        "action_ar": "تحقق من تركيب الودجيت واختبر إضافة منتج للسلة.",
        "verification_ar": "تأكد من وصول حدث سلة جديد بعد الاختبار.",
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


def _ownership_for_kind(kind: str) -> dict[str, str]:
    """Operational ownership classification (read-only)."""
    owner_key = _OWNERSHIP_BY_KIND.get(_safe_str(kind, 64)) or "unknown"
    return {
        "owner_key": owner_key,
        "owner_ar": _OPERATIONAL_OWNERS_AR.get(owner_key)
        or _OPERATIONAL_OWNERS_AR["unknown"],
    }


def _investigation_steps_for_kind(kind: str) -> list[str]:
    """Ordered investigation hints for an alert kind (read-only)."""
    steps = _INVESTIGATION_STEPS_AR.get(_safe_str(kind, 64))
    if steps:
        return [str(s).strip() for s in steps if str(s).strip()]
    return list(_DEFAULT_INVESTIGATION_STEPS_AR)


def _evidence_display_dt(val: Any) -> str | None:
    """Compact UTC display for evidence timestamps (from existing values only)."""
    if isinstance(val, datetime):
        iso = _fmt_dt(val)
    else:
        iso = None
    if not iso:
        s = _safe_str(val, 64)
        if not s or s == "غير متوفر":
            return None
        iso = s
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return iso[:19] if iso else None


def _evidence_from_record(record: dict[str, Any] | None) -> dict[str, Any]:
    """Build safe evidence references from an existing alert record (read-only)."""
    rec = record if isinstance(record, dict) else {}
    evidence: dict[str, Any] = {}

    recovery_key = _safe_str(rec.get("recovery_key"), 512)
    if recovery_key:
        evidence["recovery_key"] = recovery_key

    schedule_id = rec.get("schedule_id")
    if schedule_id is None:
        schedule_id = rec.get("id")
    try:
        sid = int(schedule_id) if schedule_id is not None else 0
        if sid > 0:
            evidence["schedule_id"] = sid
    except (TypeError, ValueError):
        pass

    store_slug = _safe_str(rec.get("store_slug"), 128)
    if store_slug:
        evidence["store_slug"] = store_slug

    last_status = _safe_str(rec.get("status"), 64)
    if last_status:
        evidence["last_status"] = last_status

    last_updated = _evidence_display_dt(rec.get("updated_at"))
    if last_updated:
        evidence["last_updated_at"] = last_updated

    return evidence


def _escalate_severity(current: str, candidate: str) -> str:
    cur = _safe_str(current, 32).lower()
    cand = _safe_str(candidate, 32).lower()
    if cand not in _VALID_SEVERITY_BUCKETS:
        cand = "low"
    if cur not in _VALID_SEVERITY_BUCKETS:
        return cand
    if _SEVERITY_RANK.get(cand, 99) < _SEVERITY_RANK.get(cur, 99):
        return cand
    return cur


def _severity_ar_for_bucket(bucket: str) -> str:
    key = _safe_str(bucket, 32).lower()
    return _SEVERITY_AR_BY_BUCKET.get(key) or _SEVERITY_AR_BY_BUCKET["low"]


def _store_slugs_from_alert(alert: dict[str, Any]) -> set[str]:
    slugs: set[str] = set()
    for rec in alert.get("records") or []:
        if not isinstance(rec, dict):
            continue
        slug = _safe_str(rec.get("store_slug"), 128)
        if slug:
            slugs.add(slug)
    return slugs


def _sort_root_cause_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple[int, int, int, str]:
        sev = _safe_str(row.get("highest_severity"), 32).lower()
        return (
            _SEVERITY_RANK.get(sev, 99),
            -_safe_int(row.get("alerts_count"), 0),
            -_safe_int(row.get("stores_count"), 0),
            _safe_str(row.get("owner_key"), 64),
        )

    return sorted(groups, key=_key)


def _build_root_cause_groups(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate alerts by operational owner (read-only root cause groups)."""
    grouped: dict[str, dict[str, Any]] = {}

    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        owner_key = _safe_str(alert.get("owner_key"), 64) or _ownership_for_kind(kind)[
            "owner_key"
        ]
        owner_ar = (
            _safe_str(alert.get("owner_ar"), 64)
            or _OPERATIONAL_OWNERS_AR.get(owner_key)
            or _OPERATIONAL_OWNERS_AR["unknown"]
        )
        if owner_key not in _OPERATIONAL_OWNERS_AR:
            owner_key = "unknown"
            owner_ar = _OPERATIONAL_OWNERS_AR["unknown"]

        if owner_key not in grouped:
            grouped[owner_key] = {
                "owner_key": owner_key,
                "owner_ar": owner_ar,
                "alerts_count": 0,
                "_store_slugs": set(),
                "highest_severity": "low",
                "_alert_kinds": set(),
            }

        bucket = grouped[owner_key]
        bucket["alerts_count"] = _safe_int(bucket.get("alerts_count"), 0) + 1
        bucket["_store_slugs"].update(_store_slugs_from_alert(alert))
        bucket["highest_severity"] = _escalate_severity(
            str(bucket.get("highest_severity") or "low"),
            _alert_severity_bucket(alert),
        )
        if kind:
            bucket["_alert_kinds"].add(kind)

    groups: list[dict[str, Any]] = []
    for row in grouped.values():
        highest = _safe_str(row.get("highest_severity"), 32).lower()
        if highest not in _VALID_SEVERITY_BUCKETS:
            highest = "low"
        kinds = sorted(str(k) for k in (row.get("_alert_kinds") or set()) if k)
        groups.append(
            {
                "owner_key": row.get("owner_key") or "unknown",
                "owner_ar": row.get("owner_ar") or _OPERATIONAL_OWNERS_AR["unknown"],
                "alerts_count": _safe_int(row.get("alerts_count"), 0),
                "stores_count": len(row.get("_store_slugs") or set()),
                "highest_severity": highest,
                "highest_severity_ar": _severity_ar_for_bucket(highest),
                "alert_kinds": kinds,
            }
        )

    sorted_groups = _sort_root_cause_groups(groups)
    return {
        "groups": sorted_groups,
        "total_groups": len(sorted_groups),
        "available": True,
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


def _severity_ar_for_bucket(severity: str) -> str:
    sev = _safe_str(severity, 32).lower()
    for meta in _ALERT_SEVERITY_AR.values():
        if meta.get("severity") == sev:
            return str(meta.get("severity_ar") or _DEFAULT_ALERT_SEVERITY["severity_ar"])
    return str(_DEFAULT_ALERT_SEVERITY["severity_ar"])


def _escalate_severity(current: str, new: str) -> str:
    cur_rank = _SEVERITY_RANK.get(_safe_str(current, 32).lower(), 99)
    new_rank = _SEVERITY_RANK.get(_safe_str(new, 32).lower(), 99)
    if new_rank < cur_rank:
        return _safe_str(new, 32).lower() or "low"
    return _safe_str(current, 32).lower() or "low"


def _store_lookup_by_slug(store_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in store_rows or []:
        if not isinstance(row, dict):
            continue
        slug = _safe_str(row.get("store_slug"), 128)
        if slug:
            out[slug] = row
    return out


def _empty_store_snapshot_row(
    slug: str,
    store_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    meta = store_meta if isinstance(store_meta, dict) else {}
    ready = bool(meta.get("ready"))
    return {
        "store_slug": slug,
        "display_name": _safe_str(meta.get("display_name"), 128) or slug,
        "highest_severity": "low",
        "highest_severity_ar": _DEFAULT_ALERT_SEVERITY["severity_ar"],
        "alerts_count": 0,
        "alert_kinds": [],
        "readiness_status": "ready" if ready else "not_ready",
        "readiness_status_ar": _safe_str(meta.get("readiness_status_ar"), 200)
        or ("جاهز" if ready else "غير متوفر"),
        "last_cart_event_at": meta.get("last_cart_event_at") or "غير متوفر",
    }


def _merge_store_snapshot_row(
    entry: dict[str, Any],
    *,
    kind: str,
    severity: str,
    record: dict[str, Any] | None,
    store_meta: dict[str, Any] | None,
) -> None:
    kinds: list[str] = list(entry.get("alert_kinds") or [])
    if kind and kind not in kinds:
        kinds.append(kind)
        entry["alerts_count"] = _safe_int(entry.get("alerts_count")) + 1
    entry["alert_kinds"] = kinds

    highest = _escalate_severity(str(entry.get("highest_severity") or "low"), severity)
    entry["highest_severity"] = highest
    entry["highest_severity_ar"] = _severity_ar_for_bucket(highest)

    rec = record if isinstance(record, dict) else {}
    meta = store_meta if isinstance(store_meta, dict) else {}

    display = _safe_str(rec.get("display_name"), 128) or _safe_str(meta.get("display_name"), 128)
    if display:
        entry["display_name"] = display
    elif not entry.get("display_name"):
        entry["display_name"] = entry.get("store_slug") or "—"

    if meta:
        ready = bool(meta.get("ready"))
        entry["readiness_status"] = "ready" if ready else "not_ready"
        status_ar = _safe_str(meta.get("readiness_status_ar"), 200)
        if status_ar:
            entry["readiness_status_ar"] = status_ar
    elif rec.get("readiness_ready") is not None:
        ready = bool(rec.get("readiness_ready"))
        entry["readiness_status"] = "ready" if ready else "not_ready"
        status_ar = _safe_str(rec.get("readiness_status_ar"), 200)
        if status_ar:
            entry["readiness_status_ar"] = status_ar

    last_at = _safe_str(rec.get("last_cart_event_at"), 64) or meta.get("last_cart_event_at")
    if last_at and last_at != "غير متوفر":
        entry["last_cart_event_at"] = last_at
    elif not entry.get("last_cart_event_at"):
        entry["last_cart_event_at"] = "غير متوفر"


def _sort_store_snapshot_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple[int, int, str]:
        sev = _safe_str(row.get("highest_severity"), 32).lower()
        rank = _SEVERITY_RANK.get(sev, 99)
        count = _safe_int(row.get("alerts_count"))
        slug = _safe_str(row.get("store_slug"), 128)
        return (rank, -count, slug)

    return sorted(rows, key=_key)


def _build_store_health_snapshot(
    alerts: list[dict[str, Any]],
    store_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge alert-affected stores into one row per store (read-only)."""
    lookup = _store_lookup_by_slug(store_rows)
    merged: dict[str, dict[str, Any]] = {}

    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        if kind not in _STORE_SNAPSHOT_KINDS:
            continue
        severity = _alert_severity_bucket(alert)
        records = alert.get("records") or []
        if not records:
            continue

        slugs_in_alert: dict[str, dict[str, Any] | None] = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            slug = _safe_str(rec.get("store_slug"), 128)
            if not slug:
                continue
            if slug not in slugs_in_alert:
                slugs_in_alert[slug] = rec
            elif slugs_in_alert[slug] is None:
                slugs_in_alert[slug] = rec

        for slug, sample_rec in slugs_in_alert.items():
            if slug not in merged:
                merged[slug] = _empty_store_snapshot_row(slug, lookup.get(slug))
            _merge_store_snapshot_row(
                merged[slug],
                kind=kind,
                severity=severity,
                record=sample_rec,
                store_meta=lookup.get(slug),
            )

    stores = _sort_store_snapshot_rows(list(merged.values()))[:_MAX_STORE_SNAPSHOT]
    return {
        "stores": stores,
        "total_stores": len(stores),
        "available": True,
    }


def _trend_window_bounds() -> tuple[datetime, datetime, datetime, datetime]:
    """Current and previous 24h windows (naive UTC, aligned with schedule queries)."""
    now = _naive_now()
    current_end = now
    current_start = now - timedelta(hours=_TREND_WINDOW_HOURS)
    previous_end = current_start
    previous_start = now - timedelta(hours=_TREND_WINDOW_HOURS * 2)
    return current_start, current_end, previous_start, previous_end


def _compute_trend_from_counts(current_count: int, previous_count: int) -> dict[str, Any]:
    current = _safe_int(current_count)
    previous = _safe_int(previous_count)
    delta = current - previous
    if current > previous:
        trend_key = "worsening"
        trend_ar = "↑ تزايد"
    elif current < previous:
        trend_key = "improving"
        trend_ar = "↓ تحسن"
    else:
        trend_key = "stable"
        trend_ar = "→ مستقر"
    return {
        "current_count": current,
        "previous_count": previous,
        "delta": delta,
        "trend_key": trend_key,
        "trend_ar": trend_ar,
    }


def _count_failed_recovery_in_window(start: datetime, end: datetime) -> int:
    try:
        db.create_all()
        return _safe_int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.status.in_(tuple(_FAILED_STATUSES)),
                RecoverySchedule.updated_at >= start,
                RecoverySchedule.updated_at < end,
            )
            .scalar()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


def _count_stale_recovery_in_window(start: datetime, end: datetime) -> int:
    stale_cutoff = end - timedelta(seconds=_RUNNING_STALE_SECONDS)
    try:
        db.create_all()
        return _safe_int(
            db.session.query(func.count(RecoverySchedule.id))
            .filter(
                RecoverySchedule.updated_at >= start,
                RecoverySchedule.updated_at < end,
                or_(
                    and_(
                        RecoverySchedule.status == "scheduled",
                        RecoverySchedule.due_at <= end,
                    ),
                    and_(
                        RecoverySchedule.status == "running",
                        RecoverySchedule.updated_at <= stale_cutoff,
                    ),
                ),
            )
            .scalar()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0


def _count_stores_readiness_in_window(
    start: datetime,
    end: datetime,
    *,
    whatsapp_only: bool,
) -> int:
    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    try:
        db.create_all()
        rows = (
            db.session.query(Store)
            .filter(
                or_(
                    and_(Store.updated_at >= start, Store.updated_at < end),
                    and_(Store.created_at >= start, Store.created_at < end),
                )
            )
            .limit(_MAX_STORES)
            .all()
        )
        count = 0
        for st in rows:
            ev = evaluate_onboarding_readiness(st)
            blocking = {str(x).strip() for x in (ev.get("blocking_steps") or [])}
            if whatsapp_only:
                if "whatsapp_not_connected" in blocking or "provider_not_ready" in blocking:
                    count += 1
            elif not ev.get("ready"):
                count += 1
        return count
    except SQLAlchemyError:
        db.session.rollback()
        return 0
    except Exception:  # noqa: BLE001
        return 0


def _build_operational_trends() -> dict[str, Any]:
    """24h vs previous 24h operational trend counts (read-only)."""
    cur_start, cur_end, prev_start, prev_end = _trend_window_bounds()
    metrics: list[tuple[str, str, Any]] = [
        (
            "failed_recovery",
            "استرجاع فاشل",
            lambda s, e: _count_failed_recovery_in_window(s, e),
        ),
        (
            "stale_recovery",
            "استرجاع عالق / متأخر",
            lambda s, e: _count_stale_recovery_in_window(s, e),
        ),
        (
            "stores_needing_setup",
            "متاجر تحتاج إعداد",
            lambda s, e: _count_stores_readiness_in_window(s, e, whatsapp_only=False),
        ),
        (
            "stores_without_whatsapp",
            "متاجر بدون واتساب",
            lambda s, e: _count_stores_readiness_in_window(s, e, whatsapp_only=True),
        ),
    ]
    trends: list[dict[str, Any]] = []
    for metric_key, metric_ar, counter in metrics:
        try:
            current = _safe_int(counter(cur_start, cur_end))
            previous = _safe_int(counter(prev_start, prev_end))
        except Exception:  # noqa: BLE001
            current = 0
            previous = 0
        row = _compute_trend_from_counts(current, previous)
        trends.append(
            {
                "metric_key": metric_key,
                "metric_ar": metric_ar,
                **row,
            }
        )
    return {
        "window_hours": _TREND_WINDOW_HOURS,
        "current_window_start_utc": _fmt_dt(cur_start.replace(tzinfo=timezone.utc)),
        "current_window_end_utc": _fmt_dt(cur_end.replace(tzinfo=timezone.utc)),
        "previous_window_start_utc": _fmt_dt(prev_start.replace(tzinfo=timezone.utc)),
        "previous_window_end_utc": _fmt_dt(prev_end.replace(tzinfo=timezone.utc)),
        "trends": trends,
        "available": True,
    }


def _record_recency_key(record: dict[str, Any]) -> str:
    rec = record if isinstance(record, dict) else {}
    for field in ("updated_at", "due_at", "last_cart_event_at"):
        val = _safe_str(rec.get(field), 64)
        if val and val != "غير متوفر":
            return val
    return ""


def _recency_timestamp(recency: str) -> float:
    raw = _safe_str(recency, 64)
    if not raw or raw == "غير متوفر":
        return 0.0
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except (TypeError, ValueError):
        return 0.0


def _risk_row_from_alert_record(
    *,
    kind: str,
    alert: dict[str, Any],
    record: dict[str, Any] | None,
) -> dict[str, Any]:
    copy = _TOP_RISK_COPY.get(kind) or {}
    sev_meta = _severity_for_kind(kind)
    sev = _alert_severity_bucket(alert)
    sev_ar = _safe_str(alert.get("severity_ar"), 32) or sev_meta["severity_ar"]
    rec = record if isinstance(record, dict) else {}
    slug = _safe_str(rec.get("store_slug"), 128)
    name = _safe_str(rec.get("display_name"), 128) or slug or "—"
    if not slug and kind in ("stale_recovery", "failed_recovery"):
        slug = _safe_str(rec.get("store_slug"), 128)
    return {
        "risk_kind": kind,
        "risk_title_ar": copy.get("risk_title_ar")
        or _safe_str(alert.get("title_ar"), 128)
        or kind,
        "severity": sev,
        "severity_ar": sev_ar,
        "affected_store": slug or "",
        "affected_store_name": name,
        "why_it_matters_ar": copy.get("why_it_matters_ar")
        or _safe_str(alert.get("why_ar"), 300),
        "suggested_next_step_ar": copy.get("suggested_next_step_ar")
        or _safe_str(alert.get("suggested_fix_ar"), 300),
        "investigation_steps_ar": _investigation_steps_for_kind(kind),
        "evidence": _evidence_from_record(rec if rec else None),
        **_ownership_for_kind(kind),
        "_recency_ts": _recency_timestamp(_record_recency_key(rec)),
        "_priority_order": sev_meta["priority_order"],
        "_store_slug_sort": slug or "",
    }


def _sort_top_risks(risks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple[int, float, int, str]:
        sev = _safe_str(row.get("severity"), 32).lower()
        return (
            _SEVERITY_RANK.get(sev, 99),
            -_safe_int(row.get("_recency_ts"), 0),
            _safe_int(row.get("_priority_order"), 999),
            _safe_str(row.get("_store_slug_sort"), 128),
        )

    return sorted(risks, key=_key)


def _build_top_risks(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """Top operational risks from existing alerts (read-only, max 5)."""
    candidates: list[dict[str, Any]] = []
    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        if kind not in _TOP_RISK_KINDS:
            continue
        records = alert.get("records") or []
        if records:
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                candidates.append(
                    _risk_row_from_alert_record(kind=kind, alert=alert, record=rec)
                )
        else:
            candidates.append(
                _risk_row_from_alert_record(kind=kind, alert=alert, record=None)
            )

    ranked = _sort_top_risks(candidates)[:_MAX_TOP_RISKS]
    risks: list[dict[str, Any]] = []
    for row in ranked:
        item: dict[str, Any] = {
                "risk_kind": row.get("risk_kind"),
                "risk_title_ar": row.get("risk_title_ar"),
                "severity": row.get("severity"),
                "severity_ar": row.get("severity_ar"),
                "affected_store": row.get("affected_store") or "",
                "affected_store_name": row.get("affected_store_name") or "—",
                "why_it_matters_ar": row.get("why_it_matters_ar") or "",
                "suggested_next_step_ar": row.get("suggested_next_step_ar") or "",
                "owner_key": row.get("owner_key") or "unknown",
                "owner_ar": row.get("owner_ar") or _OPERATIONAL_OWNERS_AR["unknown"],
                "investigation_steps_ar": list(row.get("investigation_steps_ar") or []),
        }
        evidence = dict(row.get("evidence") or {})
        if evidence:
            item["evidence"] = evidence
        risks.append(item)
    return {
        "risks": risks,
        "total_candidates": len(candidates),
        "shown_count": len(risks),
        "max_shown": _MAX_TOP_RISKS,
        "available": True,
    }


def _timeline_window_bounds() -> tuple[datetime, datetime]:
    """Last 24h window (naive UTC, aligned with schedule queries)."""
    now = _naive_now()
    return now - timedelta(hours=_TREND_WINDOW_HOURS), now


def _naive_dt_timestamp(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _timestamp_in_window(sort_ts: float, start: datetime, end: datetime) -> bool:
    if sort_ts <= 0:
        return False
    start_ts = _naive_dt_timestamp(start)
    end_ts = _naive_dt_timestamp(end)
    return start_ts <= sort_ts < end_ts


def _pick_happened_at(record: dict[str, Any], *fields: str) -> tuple[str, float]:
    rec = record if isinstance(record, dict) else {}
    for field in fields:
        val = rec.get(field)
        if isinstance(val, datetime):
            iso = _fmt_dt(val)
            if iso:
                return iso, _naive_dt_timestamp(val)
        iso = _fmt_dt(val) if val is not None and not isinstance(val, str) else None
        if iso:
            return iso, _recency_timestamp(iso)
        s = _safe_str(val, 64)
        if s and s != "غير متوفر":
            return s, _recency_timestamp(s)
    return "غير متوفر", 0.0


def _timeline_event_row(
    *,
    event_type: str,
    store_slug: str,
    store_name: str,
    happened_at: str,
    sort_ts: float,
) -> dict[str, Any]:
    copy = _TIMELINE_EVENT_COPY.get(event_type) or {}
    sev = _severity_for_kind(event_type)
    slug = _safe_str(store_slug, 128)
    name = _safe_str(store_name, 128) or slug or "—"
    owner = _ownership_for_kind(event_type)
    return {
        "event_type": event_type,
        "title_ar": copy.get("title_ar") or event_type,
        "store_slug": slug,
        "store_name": name,
        "severity": sev["severity"],
        "severity_ar": sev["severity_ar"],
        "happened_at": happened_at or "غير متوفر",
        "short_detail_ar": copy.get("short_detail_ar") or "",
        "owner_key": owner["owner_key"],
        "owner_ar": owner["owner_ar"],
        "_sort_ts": sort_ts,
    }


def _sort_operational_timeline(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def _key(row: dict[str, Any]) -> tuple[float, str, str]:
        return (
            -_safe_int(row.get("_sort_ts"), 0),
            _safe_str(row.get("store_slug"), 128),
            _safe_str(row.get("event_type"), 64),
        )

    return sorted(events, key=_key)


def _timeline_event_from_alert_record(
    *,
    kind: str,
    record: dict[str, Any],
    store_lookup: dict[str, dict[str, Any]],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, Any] | None:
    if kind not in _TIMELINE_EVENT_KINDS:
        return None
    rec = record if isinstance(record, dict) else {}
    slug = _safe_str(rec.get("store_slug"), 128)
    meta = store_lookup.get(slug) or {}
    name = _safe_str(rec.get("display_name"), 128) or _safe_str(meta.get("display_name"), 128)
    if kind in ("failed_recovery", "stale_recovery"):
        happened_at, sort_ts = _pick_happened_at(rec, "updated_at", "due_at")
    elif kind == "no_cart_events":
        happened_at, sort_ts = _pick_happened_at(
            rec, "updated_at", "last_cart_event_at", "created_at"
        )
    else:
        happened_at, sort_ts = _pick_happened_at(rec, "updated_at", "created_at")
    if not _timestamp_in_window(sort_ts, window_start, window_end):
        return None
    return _timeline_event_row(
        event_type=kind,
        store_slug=slug,
        store_name=name or slug,
        happened_at=happened_at,
        sort_ts=sort_ts,
    )


def _fetch_failed_recovery_timeline_rows(
    start: datetime, end: datetime
) -> list[Any]:
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
            .filter(
                RecoverySchedule.status.in_(tuple(_FAILED_STATUSES)),
                RecoverySchedule.updated_at >= start,
                RecoverySchedule.updated_at < end,
            )
            .order_by(RecoverySchedule.updated_at.desc())
            .limit(_MAX_TIMELINE_FETCH)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _fetch_stale_recovery_timeline_rows(
    start: datetime, end: datetime
) -> list[Any]:
    stale_cutoff = end - timedelta(seconds=_RUNNING_STALE_SECONDS)
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
            .filter(
                RecoverySchedule.updated_at >= start,
                RecoverySchedule.updated_at < end,
                or_(
                    and_(
                        RecoverySchedule.status == "scheduled",
                        RecoverySchedule.due_at <= end,
                    ),
                    and_(
                        RecoverySchedule.status == "running",
                        RecoverySchedule.updated_at <= stale_cutoff,
                    ),
                ),
            )
            .order_by(RecoverySchedule.updated_at.desc())
            .limit(_MAX_TIMELINE_FETCH)
            .all()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return []


def _store_timeline_events_in_window(
    start: datetime,
    end: datetime,
    *,
    last_event_by_store: dict[int, datetime],
) -> list[dict[str, Any]]:
    from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

    events: list[dict[str, Any]] = []
    try:
        db.create_all()
        rows = (
            db.session.query(Store)
            .filter(
                or_(
                    and_(Store.updated_at >= start, Store.updated_at < end),
                    and_(Store.created_at >= start, Store.created_at < end),
                )
            )
            .limit(_MAX_STORES)
            .all()
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

        for st in rows:
            ev = evaluate_onboarding_readiness(st)
            slug = _safe_str(getattr(st, "zid_store_id", None), 128)
            name = (
                _safe_str(getattr(st, "widget_name", None), 128) or slug or "متجر"
            )
            store_id = int(getattr(st, "id", 0) or 0)
            has_recent = store_id in recent_store_ids if store_id else False
            milestones = (
                ev.get("milestones") if isinstance(ev.get("milestones"), dict) else {}
            )
            first_cart = bool(milestones.get("first_cart_detected"))
            blocking = {str(x).strip() for x in (ev.get("blocking_steps") or [])}
            last_cart_at = last_event_by_store.get(store_id) if store_id else None
            ts_record = {
                "updated_at": getattr(st, "updated_at", None),
                "created_at": getattr(st, "created_at", None),
                "last_cart_event_at": last_cart_at,
            }
            base_happened_at, base_sort_ts = _pick_happened_at(
                ts_record, "updated_at", "last_cart_event_at", "created_at"
            )
            if not _timestamp_in_window(base_sort_ts, start, end):
                continue

            if not ev.get("ready"):
                events.append(
                    _timeline_event_row(
                        event_type="store_needs_setup",
                        store_slug=slug,
                        store_name=name,
                        happened_at=base_happened_at,
                        sort_ts=base_sort_ts,
                    )
                )
            if "whatsapp_not_connected" in blocking or "provider_not_ready" in blocking:
                events.append(
                    _timeline_event_row(
                        event_type="whatsapp_missing",
                        store_slug=slug,
                        store_name=name,
                        happened_at=base_happened_at,
                        sort_ts=base_sort_ts,
                    )
                )
            if not has_recent and not first_cart:
                events.append(
                    _timeline_event_row(
                        event_type="no_cart_events",
                        store_slug=slug,
                        store_name=name,
                        happened_at=base_happened_at,
                        sort_ts=base_sort_ts,
                    )
                )
    except SQLAlchemyError:
        db.session.rollback()
    except Exception:  # noqa: BLE001
        pass
    return events


def _build_operational_timeline(
    alerts: list[dict[str, Any]] | None = None,
    store_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Operational timeline — last 24h events from existing truth (read-only)."""
    window_start, window_end = _timeline_window_bounds()
    lookup = _store_lookup_by_slug(store_rows or [])
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    def _add(row: dict[str, Any] | None) -> None:
        if not row:
            return
        dedupe_key = (
            _safe_str(row.get("event_type"), 64),
            _safe_str(row.get("store_slug"), 128),
            _safe_str(row.get("happened_at"), 64),
        )
        if dedupe_key in seen:
            return
        seen.add(dedupe_key)
        candidates.append(row)

    for row in _fetch_failed_recovery_timeline_rows(window_start, window_end):
        rec = _recovery_record(row)
        slug = _safe_str(rec.get("store_slug"), 128)
        meta = lookup.get(slug) or {}
        name = _safe_str(meta.get("display_name"), 128) or slug
        happened_at, sort_ts = _pick_happened_at(rec, "updated_at", "due_at")
        _add(
            _timeline_event_row(
                event_type="failed_recovery",
                store_slug=slug,
                store_name=name,
                happened_at=happened_at,
                sort_ts=sort_ts,
            )
        )

    for row in _fetch_stale_recovery_timeline_rows(window_start, window_end):
        rec = _recovery_record(row)
        slug = _safe_str(rec.get("store_slug"), 128)
        meta = lookup.get(slug) or {}
        name = _safe_str(meta.get("display_name"), 128) or slug
        happened_at, sort_ts = _pick_happened_at(rec, "updated_at", "due_at")
        _add(
            _timeline_event_row(
                event_type="stale_recovery",
                store_slug=slug,
                store_name=name,
                happened_at=happened_at,
                sort_ts=sort_ts,
            )
        )

    last_event_by_store = _last_cart_event_by_store_id()
    for ev in _store_timeline_events_in_window(
        window_start, window_end, last_event_by_store=last_event_by_store
    ):
        _add(ev)

    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        if kind not in _TIMELINE_EVENT_KINDS:
            continue
        for rec in alert.get("records") or []:
            if not isinstance(rec, dict):
                continue
            _add(
                _timeline_event_from_alert_record(
                    kind=kind,
                    record=rec,
                    store_lookup=lookup,
                    window_start=window_start,
                    window_end=window_end,
                )
            )

    ranked = _sort_operational_timeline(candidates)[:_MAX_TIMELINE_EVENTS]
    events: list[dict[str, Any]] = []
    for row in ranked:
        events.append(
            {
                "event_type": row.get("event_type"),
                "title_ar": row.get("title_ar"),
                "store_slug": row.get("store_slug") or "",
                "store_name": row.get("store_name") or "—",
                "severity": row.get("severity"),
                "severity_ar": row.get("severity_ar"),
                "happened_at": row.get("happened_at") or "غير متوفر",
                "short_detail_ar": row.get("short_detail_ar") or "",
                "owner_key": row.get("owner_key") or "unknown",
                "owner_ar": row.get("owner_ar") or _OPERATIONAL_OWNERS_AR["unknown"],
            }
        )
    return {
        "window_hours": _TREND_WINDOW_HOURS,
        "window_start_utc": _fmt_dt(window_start.replace(tzinfo=timezone.utc)),
        "window_end_utc": _fmt_dt(window_end.replace(tzinfo=timezone.utc)),
        "events": events,
        "total_candidates": len(candidates),
        "shown_count": len(events),
        "max_shown": _MAX_TIMELINE_EVENTS,
        "available": True,
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
    owner = _ownership_for_kind(kind)
    primary = shown[0] if shown else None
    evidence = _evidence_from_record(primary if isinstance(primary, dict) else None)
    payload: dict[str, Any] = {
        "kind": kind,
        "severity": sev["severity"],
        "severity_ar": sev["severity_ar"],
        "priority_order": sev["priority_order"],
        "title_ar": title_ar,
        "detail_ar": detail_ar,
        "why_ar": why_ar or expl.get("why_ar") or "",
        "suggested_fix_ar": suggested_fix_ar or expl.get("suggested_fix_ar") or "",
        "owner_key": owner["owner_key"],
        "owner_ar": owner["owner_ar"],
        "investigation_steps_ar": _investigation_steps_for_kind(kind),
        "records": shown,
        "records_total": total,
        "records_hidden": hidden,
    }
    if evidence:
        payload["evidence"] = evidence
    return payload


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
                RecoverySchedule.id,
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
    try:
        row_id = getattr(row, "id", None)
        if row_id is not None:
            rec["schedule_id"] = int(row_id)
    except (TypeError, ValueError):
        pass
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


def _build_ops_scheduler_card() -> dict[str, Any]:
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
    return scheduler


def _build_ops_shared_context() -> dict[str, Any]:
    """Scheduler, recovery, readiness, alerts — shared by command + lazy sections."""
    scheduler = _build_ops_scheduler_card()
    recovery = _recovery_status_summary()
    store_readiness, store_rows = _store_readiness_summary()
    alerts = _build_basic_alerts(
        scheduler=scheduler,
        recovery=recovery,
        stores=store_rows,
    )
    return {
        "scheduler": scheduler,
        "recovery": recovery,
        "store_readiness": store_readiness,
        "store_rows": store_rows,
        "alerts": alerts,
    }


def _count_recoveries_today() -> int:
    """Read-only count of recovery messages actually sent since UTC midnight."""
    try:
        db.create_all()
        start = _naive_now().replace(hour=0, minute=0, second=0, microsecond=0)
        return _safe_int(
            db.session.query(func.count(CartRecoveryLog.id))
            .filter(
                CartRecoveryLog.status.in_(tuple(_RECOVERY_SENT_LOG_STATUSES)),
                CartRecoveryLog.created_at >= start,
            )
            .scalar()
        )
    except SQLAlchemyError:
        db.session.rollback()
        return 0
    except Exception:  # noqa: BLE001
        return 0


def _platform_status_tone(status_key: str) -> str:
    return _PLATFORM_STATUS_TONE.get(_safe_str(status_key, 64), "ok")


def _affected_stores_label_ar(count: int) -> str:
    """Arabic count phrasing for affected stores (presentation only)."""
    n = _safe_int(count)
    if n <= 0:
        return "غير محدد"
    if n == 1:
        return "متجر واحد"
    if n == 2:
        return "متجرين"
    if 3 <= n <= 10:
        return f"{n} متاجر"
    return f"{n} متجرًا"


def _build_current_issues(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    """Operational alerts re-expressed in business language (read-only).

    Groups existing alerts by kind into one issue per kind:
    Problem → Impact → Affected → Owner → Suggested Action → Verification.
    """
    grouped: dict[str, dict[str, Any]] = {}
    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = _safe_str(alert.get("kind"), 64)
        if kind not in _BUSINESS_ISSUE_COPY_AR:
            continue
        bucket = grouped.setdefault(
            kind,
            {"_slugs": set(), "_records": 0, "severity": "low"},
        )
        bucket["_slugs"].update(_store_slugs_from_alert(alert))
        bucket["_records"] += _safe_int(
            alert.get("records_total"), len(alert.get("records") or [])
        )
        bucket["severity"] = _escalate_severity(
            str(bucket.get("severity") or "low"), _alert_severity_bucket(alert)
        )

    issues: list[dict[str, Any]] = []
    for kind, bucket in grouped.items():
        copy = _BUSINESS_ISSUE_COPY_AR[kind]
        affected = len(bucket.get("_slugs") or set()) or _safe_int(bucket.get("_records"))
        sev = _safe_str(bucket.get("severity"), 32).lower() or "low"
        if sev not in _VALID_SEVERITY_BUCKETS:
            sev = "low"
        issues.append(
            {
                "kind": kind,
                "severity": sev,
                "severity_ar": _severity_ar_for_bucket(sev),
                "title_ar": copy["title_ar"],
                "problem_ar": copy["title_ar"],
                "impact_ar": copy["impact_ar"],
                "where_ar": copy.get("where_ar") or "عبر المنصة",
                "owner_ar": copy["owner_ar"],
                "action_ar": copy["action_ar"],
                "verification_ar": copy["verification_ar"],
                "affected_count": affected,
                "affected_label_ar": _affected_stores_label_ar(affected),
            }
        )

    issues.sort(
        key=lambda r: (
            _SEVERITY_RANK.get(_safe_str(r.get("severity"), 32).lower(), 99),
            -_safe_int(r.get("affected_count")),
            _safe_str(r.get("kind"), 64),
        )
    )
    return {"issues": issues, "total": len(issues), "available": True}


def _build_executive_summary(
    *,
    system_health: dict[str, Any],
    store_readiness: dict[str, Any],
    store_health_snapshot: dict[str, Any],
    recoveries_today: int,
) -> dict[str, Any]:
    """Top-level executive KPIs for the operations overview (read-only)."""
    sh = system_health if isinstance(system_health, dict) else {}
    sr = store_readiness if isinstance(store_readiness, dict) else {}
    snap = store_health_snapshot if isinstance(store_health_snapshot, dict) else {}
    status_key = _safe_str(sh.get("status_key"), 64) or "stable"
    return {
        "platform_status_key": status_key,
        "platform_status_ar": _safe_str(sh.get("status_ar"), 64) or "مستقرة",
        "platform_status_tone": _platform_status_tone(status_key),
        "platform_description_ar": _safe_str(sh.get("description_ar"), 300),
        "active_stores": _safe_int(sr.get("total_stores")),
        "ready_stores": _safe_int(sr.get("ready_stores")),
        "affected_stores": _safe_int(snap.get("total_stores")),
        "open_alerts": _safe_int(sh.get("total_alerts")),
        "recoveries_today": _safe_int(recoveries_today),
    }


def build_admin_operations_command_center_readonly() -> dict[str, Any]:
    """Lightweight initial payload for /admin/operations (executive overview)."""
    ctx = _build_ops_shared_context()
    alerts = ctx["alerts"]
    store_rows = ctx["store_rows"]
    store_readiness = ctx["store_readiness"]
    from services.admin_recovery_resume_inspect_scan_v1 import (  # noqa: PLC0415
        build_recovery_resume_health_summary_readonly,
    )

    system_health = _build_system_health_summary(alerts)
    store_health_snapshot = _build_store_health_snapshot(alerts, store_rows)
    current_issues = _build_current_issues(alerts)
    executive_summary = _build_executive_summary(
        system_health=system_health,
        store_readiness=store_readiness,
        store_health_snapshot=store_health_snapshot,
        recoveries_today=_count_recoveries_today(),
    )
    # Open issues count aligns with business-language issue cards (presentation only).
    executive_summary["open_issues"] = _safe_int(current_issues.get("total"))
    return {
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "executive_summary": executive_summary,
        "current_issues": current_issues,
        "system_health_summary": system_health,
        "top_risks": _build_top_risks(alerts),
        "store_health_snapshot": store_health_snapshot,
        "recovery_resume_health": build_recovery_resume_health_summary_readonly(),
        "health_scheduler_path": "/health/scheduler",
    }


def build_admin_operations_current_issues_readonly() -> dict[str, Any]:
    """Full current-issues view in business language (read-only)."""
    ctx = _build_ops_shared_context()
    alerts = ctx["alerts"]
    return {
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "system_health_summary": _build_system_health_summary(alerts),
        "current_issues": _build_current_issues(alerts),
        "health_scheduler_path": "/health/scheduler",
    }


def build_admin_support_diagnostics_overview_readonly() -> dict[str, Any]:
    """Initial payload for the Support Diagnostics page (recovery resume health)."""
    from services.admin_recovery_resume_inspect_scan_v1 import (  # noqa: PLC0415
        build_recovery_resume_health_summary_readonly,
    )

    return {
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "recovery_resume_health": build_recovery_resume_health_summary_readonly(),
        "health_scheduler_path": "/health/scheduler",
    }


def build_admin_operations_investigation_section_readonly() -> dict[str, Any]:
    """Lazy investigation section: scheduler, recovery, readiness, alerts."""
    ctx = _build_ops_shared_context()
    return {
        "section": "investigation",
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "scheduler": ctx["scheduler"],
        "recovery": ctx["recovery"],
        "store_readiness": ctx["store_readiness"],
        "alerts": ctx["alerts"],
        "health_scheduler_path": "/health/scheduler",
    }


def build_admin_operations_analytics_section_readonly() -> dict[str, Any]:
    """Lazy analytics section: trends, timeline, root cause groups."""
    ctx = _build_ops_shared_context()
    alerts = ctx["alerts"]
    store_rows = ctx["store_rows"]
    return {
        "section": "analytics",
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "operational_trends": _build_operational_trends(),
        "operational_timeline": _build_operational_timeline(alerts, store_rows),
        "root_cause_groups": _build_root_cause_groups(alerts),
    }


def build_admin_operations_center_v1_readonly() -> dict[str, Any]:
    """Full read-only payload (all sections — tests and compatibility)."""
    ctx = _build_ops_shared_context()
    alerts = ctx["alerts"]
    store_rows = ctx["store_rows"]
    return {
        "version": "admin_operations_center_v2_2",
        "generated_at_utc": _utc_now().isoformat(),
        "system_health_summary": _build_system_health_summary(alerts),
        "store_health_snapshot": _build_store_health_snapshot(alerts, store_rows),
        "operational_trends": _build_operational_trends(),
        "top_risks": _build_top_risks(alerts),
        "operational_timeline": _build_operational_timeline(alerts, store_rows),
        "root_cause_groups": _build_root_cause_groups(alerts),
        "scheduler": ctx["scheduler"],
        "recovery": ctx["recovery"],
        "store_readiness": ctx["store_readiness"],
        "alerts": alerts,
        "health_scheduler_path": "/health/scheduler",
    }


__all__ = [
    "build_admin_operations_center_v1_readonly",
    "build_admin_operations_command_center_readonly",
    "build_admin_operations_current_issues_readonly",
    "build_admin_support_diagnostics_overview_readonly",
    "build_admin_operations_investigation_section_readonly",
    "build_admin_operations_analytics_section_readonly",
    "_build_current_issues",
    "_build_executive_summary",
    "_BUSINESS_ISSUE_COPY_AR",
    "_count_recoveries_today",
    "_ALERT_SEVERITY_AR",
    "_sort_alerts",
    "_build_system_health_summary",
    "_build_store_health_snapshot",
    "_build_operational_trends",
    "_compute_trend_from_counts",
    "_build_top_risks",
    "_sort_top_risks",
    "_build_operational_timeline",
    "_sort_operational_timeline",
    "_pick_happened_at",
    "_timeline_event_from_alert_record",
    "_ownership_for_kind",
    "_OWNERSHIP_BY_KIND",
    "_OPERATIONAL_OWNERS_AR",
    "_build_root_cause_groups",
    "_sort_root_cause_groups",
    "_escalate_severity",
    "_investigation_steps_for_kind",
    "_INVESTIGATION_STEPS_AR",
    "_evidence_from_record",
]
