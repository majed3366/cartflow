# -*- coding: utf-8 -*-
"""
Operations Center V1.1 presentation projection.

Read-only mapping of existing command-center payloads onto the approved
layout. Does not classify new issues or invent eligibility.
Intervention vs monitoring uses existing operational priority labels:
LOW = Monitoring; CRITICAL / HIGH / MEDIUM = action or review.
Platform يحتاجني uses the existing action-engine ``action_en`` field.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from services.admin_operations_operational_priority_v1 import PRIORITY_LOW
from services.admin_operations_root_cause_groups_v1 import ROOT_CAUSE_WIDGET_RUNTIME
from services.admin_operations_store_action_center_v1 import _PLATFORM_ONLY_KINDS
from services.provider_retry_ledger_v1 import retry_active

_WIDGET_SIGNAL_KINDS = frozenset(
    {
        "runtime_beacon_missing",
        "widget_runtime_missing",
        "widget_runtime_object_missing",
        "widget_not_seen",
    }
)

_MONTHS_AR = (
    "يناير",
    "فبراير",
    "مارس",
    "أبريل",
    "مايو",
    "يونيو",
    "يوليو",
    "أغسطس",
    "سبتمبر",
    "أكتوبر",
    "نوفمبر",
    "ديسمبر",
)

# Existing action-engine copy (admin_operations_action_engine_v1). Not a new classifier.
_NO_OPERATOR_ACTION_PREFIXES = (
    "no immediate action required",
    "no action required",
)

_EVIDENCE_FRESHNESS_PRODUCERS = (
    "store_action_center",
    "critical_alerts",
    "recovery_resume_health",
)


def _parse_iso(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def format_generated_at_ar(iso_value: Any) -> str:
    dt = _parse_iso(iso_value)
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return f"{dt.day} {_MONTHS_AR[dt.month - 1]} {dt.year}، الساعة {dt.hour:02d}:{dt.minute:02d} UTC"


def explicit_int(container: Any, key: str) -> int | None:
    """Return an int only when the producer supplied the key with a numeric value (including 0)."""
    if not isinstance(container, dict) or key not in container:
        return None
    raw = container.get(key)
    if raw is None or isinstance(raw, bool):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def operator_action_required(action_en: Any) -> bool:
    """Existing action-engine ``action_en`` is the operator-action rule.

    Empty / missing rule → not يحتاجني. ``No immediate action required`` /
    ``No action required`` (authoritative copy) → not يحتاجني.
    Does not read kind or severity.
    """
    text = " ".join(str(action_en or "").split())
    if not text:
        return False
    head = text.lower()
    return not any(head.startswith(prefix) for prefix in _NO_OPERATOR_ACTION_PREFIXES)


def split_intervention_queues(
    production_action_queue: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Same list used for count and يحتاجني. LOW stays مراقبة."""
    intervene: list[dict[str, Any]] = []
    monitor: list[dict[str, Any]] = []
    for row in production_action_queue or []:
        if not isinstance(row, dict) or not row.get("has_issues"):
            continue
        if str(row.get("priority") or "") == PRIORITY_LOW:
            monitor.append(row)
        else:
            intervene.append(row)
    return intervene, monitor


def _store_has_widget_observation(row: dict[str, Any]) -> bool:
    for rc in row.get("root_causes") or []:
        if not isinstance(rc, dict):
            continue
        if str(rc.get("root_cause_id") or "") == ROOT_CAUSE_WIDGET_RUNTIME:
            return True
        kinds = {str(k).strip() for k in (rc.get("symptom_kinds") or [])}
        if kinds & _WIDGET_SIGNAL_KINDS:
            return True
    return False


def scoped_observation_headline_ar(widget_store_count: int) -> str:
    if widget_store_count <= 0:
        return ""
    if widget_store_count == 1:
        return "الرصد غير مكتمل لمتجر واحد"
    return f"الرصد غير مكتمل لـ {widget_store_count} متاجر"


def _platform_scoped_alerts(critical_alerts: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Placement only (shared-platform vs store). Not an actionability rule."""
    out: list[dict[str, Any]] = []
    payload = critical_alerts if isinstance(critical_alerts, dict) else {}
    for alert in payload.get("alerts") or []:
        if not isinstance(alert, dict):
            continue
        kind = str(alert.get("kind") or "")
        if kind in _PLATFORM_ONLY_KINDS:
            out.append(alert)
    return out


def split_platform_alerts_by_action(
    critical_alerts: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actionable: list[dict[str, Any]] = []
    monitor: list[dict[str, Any]] = []
    for alert in _platform_scoped_alerts(critical_alerts):
        if operator_action_required(alert.get("action_en")):
            actionable.append(alert)
        else:
            monitor.append(alert)
    return actionable, monitor


def build_operations_center_v11_presentation(
    *,
    store_action_center: dict[str, Any] | None,
    critical_alerts: dict[str, Any] | None,
    recovery_resume_health: dict[str, Any] | None,
    generated_at_utc: Any,
) -> dict[str, Any]:
    sac = store_action_center if isinstance(store_action_center, dict) else {}
    summary = sac.get("summary") if isinstance(sac.get("summary"), dict) else {}
    queue = list(sac.get("production_action_queue") or [])
    intervene, monitor = split_intervention_queues(queue)
    actionable_platform, monitoring_platform = split_platform_alerts_by_action(
        critical_alerts
    )
    widget_n = sum(1 for row in queue if _store_has_widget_observation(row))
    resume = recovery_resume_health if isinstance(recovery_resume_health, dict) else {}
    retry_on = bool(retry_active())
    missing_freshness = list(_EVIDENCE_FRESHNESS_PRODUCERS)
    return {
        "intervention_stores": intervene,
        "monitoring_stores": monitor,
        "actionable_platform_alerts": actionable_platform,
        "monitoring_platform_alerts": monitoring_platform,
        "intervention_count": len(intervene) + len(actionable_platform),
        "monitoring_count": len(monitor),
        "widget_observation_store_count": widget_n,
        "scoped_observation_headline_ar": scoped_observation_headline_ar(widget_n),
        "retry_active": retry_on,
        "retry_label_ar": "مفعّلة" if retry_on else "غير مفعّلة",
        "schedule_running": explicit_int(resume, "running"),
        "presentation_generated_at_utc": generated_at_utc,
        "presentation_generated_at_ar": format_generated_at_ar(generated_at_utc),
        "generated_at_utc": generated_at_utc,
        "generated_at_ar": format_generated_at_ar(generated_at_utc),
        "evidence_freshness_utc": None,
        "evidence_freshness_source": None,
        "evidence_freshness_missing_sources": missing_freshness,
        "production_store_count": explicit_int(summary, "production_store_count"),
        "production_affected_count": explicit_int(summary, "production_affected_count"),
    }


__all__ = [
    "build_operations_center_v11_presentation",
    "explicit_int",
    "format_generated_at_ar",
    "operator_action_required",
    "scoped_observation_headline_ar",
    "split_intervention_queues",
    "split_platform_alerts_by_action",
]
