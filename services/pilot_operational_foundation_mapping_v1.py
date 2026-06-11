# -*- coding: utf-8 -*-
"""
Pilot Operational Visibility Foundation v1 — pure mapping tables.

Presentation-only normalization; no detection logic.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

FOUNDATION_VERSION = "pilot_operational_foundation_v1"

STATUS_HEALTHY = "healthy"
STATUS_WARNING = "warning"
STATUS_CRITICAL = "critical"

READINESS_NOT_READY = "not_ready"
READINESS_PARTIALLY_READY = "partially_ready"
READINESS_READY = "ready"
READINESS_LAUNCH_READY = "launch_ready"

PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

OWNER_CARTFLOW = "cartflow"
OWNER_MERCHANT = "merchant"
OWNER_META = "meta"
OWNER_ZID = "zid"
OWNER_SALLA = "salla"
OWNER_EXTERNAL = "external_provider"

HEALTHY_PROBLEM_AR = "لا توجد مشكلة تشغيلية ظاهرة"
PRIMARY_REASON_LABEL_AR = "سبب الحالة"
NO_ACTIVITY_AR = "لا يوجد نشاط"
UNAVAILABLE_AR = "غير متوفر"

STATUS_LABELS_AR: dict[str, str] = {
    STATUS_HEALTHY: "سليم",
    STATUS_WARNING: "يحتاج متابعة",
    STATUS_CRITICAL: "حرج",
}

READINESS_LABELS_AR: dict[str, str] = {
    READINESS_NOT_READY: "غير جاهز",
    READINESS_PARTIALLY_READY: "جاهز جزئياً",
    READINESS_READY: "جاهز",
    READINESS_LAUNCH_READY: "جاهز للإطلاق",
}

PRIORITY_LABELS_AR: dict[str, str] = {
    PRIORITY_HIGH: "مرتفعة",
    PRIORITY_MEDIUM: "متوسطة",
    PRIORITY_LOW: "منخفضة",
}

OWNER_LABELS_AR: dict[str, str] = {
    OWNER_CARTFLOW: "CartFlow",
    OWNER_MERCHANT: "صاحب المتجر",
    OWNER_META: "ميتا",
    OWNER_ZID: "زد",
    OWNER_SALLA: "سلة",
    OWNER_EXTERNAL: "مزود خارجي",
}

STATUS_SORT_RANK: dict[str, int] = {
    STATUS_CRITICAL: 0,
    STATUS_WARNING: 1,
    STATUS_HEALTHY: 2,
}

PRIORITY_SORT_RANK: dict[str, int] = {
    PRIORITY_HIGH: 0,
    PRIORITY_MEDIUM: 1,
    PRIORITY_LOW: 2,
}

OPS_PRIORITY_TO_PILOT: dict[str, str] = {
    "CRITICAL": PRIORITY_HIGH,
    "HIGH": PRIORITY_HIGH,
    "MEDIUM": PRIORITY_MEDIUM,
    "LOW": PRIORITY_LOW,
}

SEVERITY_TO_STATUS: dict[str, str] = {
    "critical": STATUS_CRITICAL,
    "warning": STATUS_WARNING,
    "information": STATUS_WARNING,
    "healthy": STATUS_HEALTHY,
    "high": STATUS_WARNING,
    "medium": STATUS_WARNING,
    "low": STATUS_WARNING,
}

ISSUE_TITLE_AR: dict[str, str] = {
    "whatsapp_missing": "واتساب غير مربوط",
    "no_cart_events": "لا توجد أحداث سلة",
    "no_recent_cart_events": "لا توجد أحداث سلة",
    "store_needs_setup": "إعداد المتجر غير مكتمل",
    "store_setup_incomplete": "إعداد المتجر غير مكتمل",
    "onboarding_incomplete": "إعداد المتجر غير مكتمل",
    "failed_recovery": "مشكلة مزود خارجي",
    "whatsapp_failed": "مشكلة مزود خارجي",
    "stale_recovery": "حاجة لمراجعة تشغيلية",
    "widget_runtime_missing": "الودجيت غير نشط",
    "widget_runtime_object_missing": "الودجيت غير نشط",
    "runtime_beacon_missing": "الودجيت غير نشط",
    "widget_not_seen": "الودجيت غير نشط",
    "widget_module_failed": "الودجيت غير نشط",
    "widget_bootstrap_blocked": "الودجيت غير نشط",
    "recovery_not_enabled": "الاسترجاع غير مفعل",
    "template_approval_pending": "بانتظار اعتماد القالب",
    "templates_not_provider_approved": "بانتظار اعتماد القالب",
    "widget_settings_mismatch": "عدم تطابق إعدادات الودجيت",
    "widget_runtime_mismatch": "عدم تطابق إعدادات الودجيت",
    "store_identity_mismatch": "عدم تطابق هوية المتجر",
    "cart_event_bridge_missing": "لا توجد أحداث سلة",
    "provider_unavailable": "مشكلة مزود خارجي",
}

WAITING_ONLY_ISSUE_KINDS = frozenset(
    {
        "template_approval_pending",
        "templates_not_provider_approved",
    }
)

WHATSAPP_ISSUE_KINDS = frozenset(
    {
        "whatsapp_missing",
        "whatsapp_failed",
        "whatsapp_not_connected",
        "provider_unavailable",
        "provider_paused",
    }
)

PLATFORM_CONNECTION_KINDS = frozenset(
    {
        "store_needs_setup",
        "store_setup_incomplete",
        "onboarding_incomplete",
    }
)

ACTIONABLE_OWNER_KEYS = frozenset(
    {
        OWNER_CARTFLOW,
        OWNER_MERCHANT,
        OWNER_ZID,
        OWNER_SALLA,
        OWNER_EXTERNAL,
    }
)


def status_from_severity(severity: str, *, has_issues: bool) -> dict[str, str]:
    sev = (severity or "").strip().lower()
    if not has_issues or sev == "healthy":
        key = STATUS_HEALTHY
    else:
        key = SEVERITY_TO_STATUS.get(sev, STATUS_WARNING)
    return {"key": key, "label_ar": STATUS_LABELS_AR[key]}


def readiness_from_onboarding_state(
    onboarding_state: str,
    *,
    has_blocking: bool,
) -> dict[str, str]:
    state = (onboarding_state or "").strip().lower()
    if state == "production_ready":
        key = READINESS_LAUNCH_READY
    elif state in ("not_started", "sandbox_only"):
        key = READINESS_NOT_READY
    elif has_blocking:
        key = READINESS_PARTIALLY_READY
    elif state == "partial":
        key = READINESS_READY
    else:
        key = READINESS_NOT_READY
    return {"key": key, "label_ar": READINESS_LABELS_AR[key]}


def priority_from_ops_row(ops_row: dict[str, Any]) -> dict[str, str]:
    raw = str(ops_row.get("priority") or "LOW").strip().upper()
    key = OPS_PRIORITY_TO_PILOT.get(raw, PRIORITY_LOW)
    if not ops_row.get("has_issues"):
        key = PRIORITY_LOW
    return {"key": key, "label_ar": PRIORITY_LABELS_AR[key]}


def issue_title_ar(issue_code: str, business_copy: Optional[dict[str, str]] = None) -> str:
    if business_copy and business_copy.get("title_ar"):
        return str(business_copy["title_ar"]).strip()
    code = (issue_code or "").strip()
    return ISSUE_TITLE_AR.get(code, code.replace("_", " ").strip() or "مشكلة تشغيلية")


def resolve_pilot_owner(
    issue_code: str,
    *,
    integration_source: str = "",
    provider_readiness: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    from services.admin_operations_center_v1 import _ownership_for_kind  # noqa: PLC0415

    code = (issue_code or "").strip()
    ops_owner = _ownership_for_kind(code)
    ops_key = str(ops_owner.get("owner_key") or "unknown")

    if code in WHATSAPP_ISSUE_KINDS:
        prov = provider_readiness if isinstance(provider_readiness, dict) else {}
        primary = str(prov.get("provider") or "").strip().lower()
        meta = prov.get("meta") if isinstance(prov.get("meta"), dict) else {}
        if primary == "meta" and bool(meta.get("configured")):
            key = OWNER_META
        elif code == "whatsapp_missing":
            key = OWNER_MERCHANT
        else:
            key = OWNER_EXTERNAL
    elif ops_key in ("cartflow_system", "scheduler"):
        key = OWNER_CARTFLOW
    elif ops_key == "merchant_setup":
        key = OWNER_MERCHANT
    elif ops_key == "whatsapp_provider":
        key = OWNER_EXTERNAL
    elif ops_key == "widget_integration":
        src = (integration_source or "").strip().lower()
        if "salla" in src:
            key = OWNER_SALLA
        elif "zid" in src or src.startswith("zid"):
            key = OWNER_ZID
        else:
            key = OWNER_MERCHANT
    elif code in PLATFORM_CONNECTION_KINDS:
        src = (integration_source or "").strip().lower()
        if "salla" in src:
            key = OWNER_SALLA
        elif "zid" in src or src.startswith("zid"):
            key = OWNER_ZID
        else:
            key = OWNER_MERCHANT
    else:
        key = OWNER_CARTFLOW

    return {"key": key, "label_ar": OWNER_LABELS_AR[key]}


def classify_action_required(
    *,
    status_key: str,
    owner_key: str,
    issue_code: str,
    recommended_action_ar: str,
) -> bool:
    if status_key == STATUS_HEALTHY:
        return False
    action = (recommended_action_ar or "").strip()
    code = (issue_code or "").strip()
    if code in WAITING_ONLY_ISSUE_KINDS:
        return False
    if owner_key == OWNER_META and (
        code in WAITING_ONLY_ISSUE_KINDS
        or "بانتظار" in action
        or action.startswith("انتظار")
    ):
        return False
    if owner_key in ACTIONABLE_OWNER_KEYS:
        return True
    return False


def parse_foundation_timestamp(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        dt = raw
    else:
        text = str(raw).strip()
        if not text or text in (UNAVAILABLE_AR, "—", "-", "null", "None"):
            return None
        dt = None
        for candidate in (text, text.replace("Z", "+00:00")):
            try:
                dt = datetime.fromisoformat(candidate)
                break
            except ValueError:
                pass
        if dt is None:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    dt = datetime.strptime(text, fmt)
                    break
                except ValueError:
                    continue
        if dt is None:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def compose_last_activity_fields(
    *,
    last_cart_event_at: Any,
    last_recovery_at: Any,
    widget_last_seen_at: Any,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    cart_dt = parse_foundation_timestamp(last_cart_event_at)
    recovery_dt = parse_foundation_timestamp(last_recovery_at)
    widget_dt = parse_foundation_timestamp(widget_last_seen_at)
    candidates = [dt for dt in (cart_dt, recovery_dt, widget_dt) if dt is not None]
    if not candidates:
        return {
            "last_cart_event_at": None,
            "last_recovery_at": None,
            "last_activity_at": None,
            "last_activity_display_ar": NO_ACTIVITY_AR,
        }
    latest = max(candidates)
    cart_iso = cart_dt.isoformat() + "Z" if cart_dt else None
    recovery_iso = recovery_dt.isoformat() + "Z" if recovery_dt else None
    latest_iso = latest.isoformat() + "Z"
    return {
        "last_cart_event_at": cart_iso,
        "last_recovery_at": recovery_iso,
        "last_activity_at": latest_iso,
        "last_activity_display_ar": format_relative_activity_ar(latest, now=now),
    }


def format_relative_activity_ar(
    activity_at: datetime,
    *,
    now: Optional[datetime] = None,
) -> str:
    ref = now or datetime.utcnow()
    if activity_at.tzinfo is not None:
        activity_at = activity_at.astimezone(timezone.utc).replace(tzinfo=None)
    delta = ref - activity_at
    seconds = max(int(delta.total_seconds()), 0)
    if seconds <= 300:
        return "آخر نشاط قبل 5 دقائق"
    if seconds <= 3600:
        return "آخر نشاط قبل ساعة"
    if seconds <= 86400:
        return "آخر نشاط قبل يوم"
    days = max(seconds // 86400, 1)
    return f"آخر نشاط قبل {days} يوم"


def map_onboarding_state_to_readiness_key(
    onboarding_state: str,
    *,
    blocking_steps: list[Any],
) -> str:
    return readiness_from_onboarding_state(
        onboarding_state,
        has_blocking=bool(blocking_steps),
    )["key"]


__all__ = [
    "FOUNDATION_VERSION",
    "HEALTHY_PROBLEM_AR",
    "PRIMARY_REASON_LABEL_AR",
    "STATUS_LABELS_AR",
    "READINESS_LABELS_AR",
    "PRIORITY_LABELS_AR",
    "OWNER_LABELS_AR",
    "STATUS_SORT_RANK",
    "PRIORITY_SORT_RANK",
    "ISSUE_TITLE_AR",
    "WAITING_ONLY_ISSUE_KINDS",
    "classify_action_required",
    "compose_last_activity_fields",
    "format_relative_activity_ar",
    "issue_title_ar",
    "map_onboarding_state_to_readiness_key",
    "parse_foundation_timestamp",
    "priority_from_ops_row",
    "readiness_from_onboarding_state",
    "resolve_pilot_owner",
    "status_from_severity",
]
