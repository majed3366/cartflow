# -*- coding: utf-8 -*-
"""
Operations Center V1.1 presentation projection.

Read-only mapping of existing command-center payloads onto the approved
layout. Does not classify new issues or invent eligibility.
Intervention vs monitoring uses existing operational priority labels:
LOW = Monitoring; CRITICAL / HIGH / MEDIUM = action or review.
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


def _platform_alerts(critical_alerts: dict[str, Any] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    payload = critical_alerts if isinstance(critical_alerts, dict) else {}
    for alert in payload.get("alerts") or []:
        if not isinstance(alert, dict):
            continue
        kind = str(alert.get("kind") or "")
        if kind in _PLATFORM_ONLY_KINDS:
            out.append(alert)
    return out


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
    widget_n = sum(1 for row in queue if _store_has_widget_observation(row))
    running = None
    resume = recovery_resume_health if isinstance(recovery_resume_health, dict) else {}
    if "running" in resume:
        try:
            running = int(resume.get("running") or 0)
        except (TypeError, ValueError):
            running = None
    retry_on = bool(retry_active())
    return {
        "intervention_stores": intervene,
        "monitoring_stores": monitor,
        "intervention_count": len(intervene),
        "monitoring_count": len(monitor),
        "widget_observation_store_count": widget_n,
        "scoped_observation_headline_ar": scoped_observation_headline_ar(widget_n),
        "platform_alerts": _platform_alerts(critical_alerts),
        "retry_active": retry_on,
        "retry_label_ar": "مفعّلة" if retry_on else "غير مفعّلة",
        "schedule_running": running,
        "generated_at_utc": generated_at_utc,
        "generated_at_ar": format_generated_at_ar(generated_at_utc),
        "production_store_count": int(summary.get("production_store_count") or 0),
        "production_affected_count": int(summary.get("production_affected_count") or 0),
    }


__all__ = [
    "build_operations_center_v11_presentation",
    "format_generated_at_ar",
    "scoped_observation_headline_ar",
    "split_intervention_queues",
]
