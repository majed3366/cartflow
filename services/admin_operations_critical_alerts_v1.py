# -*- coding: utf-8 -*-
"""
Admin Operations V2 — Critical Alert Hook (read-only, presentation-only).

Surfaces actionable operational problems at the top of Admin Operations using
existing operational truth only. Does not change detection, snapshots, or runtime.
"""
from __future__ import annotations

from typing import Any, Optional

from services.admin_operations_action_engine_v1 import resolve_current_issue_guidance
from services.admin_operations_production_truth_v1 import is_production_store

SECTION_KEY = "critical_alerts"

_SEVERITY_RANK = {"critical": 0, "warning": 1, "information": 2}
_SEVERITY_META: dict[str, tuple[str, str]] = {
    "critical": ("🔴", "Critical"),
    "warning": ("🟡", "Warning"),
    "information": ("🔵", "Information"),
}

# Operator-facing copy for critical hook (may differ slightly from Current Issues).
_CRITICAL_PRESENTATION: dict[str, dict[str, str]] = {
    "dashboard_restart_survival_failed": {
        "problem_en": "Dashboard startup protection failed.",
        "impact_en": "Merchants may experience slow dashboard loading after restart.",
        "where_en": "Dashboard Initialization",
    },
    "dashboard_db_init_slow": {
        "problem_en": "Dashboard initialization is slower than expected.",
        "impact_en": (
            "Some merchants may experience slower dashboard loading after restart."
        ),
        "where_en": "Dashboard Initialization",
    },
    "widget_runtime_missing": {
        "problem_en": "Widget runtime not detected.",
        "impact_en": "Customers may not see the widget.",
        "where_en": "Widget Health",
    },
    "request_health_failure": {
        "problem_en": "Critical request failures detected.",
        "impact_en": "Affected pages or APIs may be unavailable.",
        "where_en": "Request Health",
    },
}

_WIDGET_RUNTIME_KINDS = frozenset(
    {"runtime_beacon_missing", "widget_runtime_object_missing", "widget_runtime_missing"}
)


def _presentation_for_kind(kind: str, guidance: dict[str, Any]) -> dict[str, Any]:
    preset = dict(_CRITICAL_PRESENTATION.get(kind) or {})
    return {
        "kind": kind,
        "problem_en": preset.get("problem_en") or guidance.get("problem_en", ""),
        "impact_en": preset.get("impact_en") or guidance.get("impact_en", ""),
        "where_en": preset.get("where_en") or guidance.get("where_en", ""),
        "action_en": guidance.get("action_en", ""),
        "investigation_intro_en": guidance.get("investigation_intro_en", ""),
        "investigation_lines_en": list(guidance.get("investigation_lines_en") or []),
        "verification_en": guidance.get("verification_en", ""),
        "verification_lines_en": list(guidance.get("verification_lines_en") or []),
    }


def _finalize_alert(kind: str, *, severity: str, meta: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    sev = severity if severity in _SEVERITY_META else "warning"
    emoji, label = _SEVERITY_META[sev]
    guidance = resolve_current_issue_guidance(kind)
    card = _presentation_for_kind(kind, guidance)
    card["severity"] = sev
    card["severity_emoji"] = emoji
    card["severity_label"] = label
    if meta:
        card["meta"] = meta
    return card


def _should_raise_db_init_slow_alert(snap: dict[str, Any], rs: dict[str, Any]) -> bool:
    """V2 filter — do not alert when startup protection metrics are healthy."""
    rs_result = str(rs.get("verification_result") or "PENDING").upper()
    if rs_result == "FAIL":
        return False
    first_dur = float(rs.get("first_dashboard_duration_ms") or 0.0)
    first_cached = rs.get("first_dashboard_cached_verification")
    cached = snap.get("last_request_cached_verification")
    if (
        rs_result == "PASS"
        and first_dur < 1000
        and (first_cached is True or cached is True)
    ):
        return False
    if rs_result != "PASS":
        return True
    return first_dur >= 1000


def _collect_dashboard_alerts() -> list[dict[str, Any]]:
    from services.db_ready_admin_v1 import (  # noqa: PLC0415
        build_restart_survival_admin_alert,
    )
    from services.db_ready_operational_snapshot_v1 import (  # noqa: PLC0415
        load_db_ready_operational_snapshot,
    )
    from services.db_ready_restart_survival_v1 import restart_survival_public_view  # noqa: PLC0415

    out: list[dict[str, Any]] = []
    snap = load_db_ready_operational_snapshot(reload_db=False)
    rs = restart_survival_public_view(snap)

    restart = build_restart_survival_admin_alert()
    if restart:
        out.append(
            _finalize_alert(
                "dashboard_restart_survival_failed",
                severity="critical",
                meta=restart.get("meta"),
            )
        )

    if _should_raise_db_init_slow_alert(snap, rs):
        out.append(
            _finalize_alert(
                "dashboard_db_init_slow",
                severity="warning",
                meta={
                    "verification_result": rs.get("verification_result"),
                    "first_dashboard_duration_ms": rs.get("first_dashboard_duration_ms"),
                    "last_duration_ms": snap.get("last_duration_ms"),
                },
            )
        )

    if not bool(snap.get("last_success", True)):
        out.append(
            _finalize_alert(
                "request_health_failure",
                severity="critical",
                meta={
                    "last_failure_message": snap.get("last_failure_message"),
                    "last_stage": snap.get("last_stage"),
                },
            )
        )

    return out


def _collect_widget_runtime_alert() -> Optional[dict[str, Any]]:
    try:
        from services.widget_health_v1 import (  # noqa: PLC0415
            STATUS_CRITICAL,
            build_admin_widget_health_section_readonly,
        )
    except Exception:  # noqa: BLE001
        return None

    try:
        health = build_admin_widget_health_section_readonly()
    except Exception:  # noqa: BLE001
        return None

    matches = [
        it
        for it in (health.get("issues") or [])
        if str(it.get("kind") or "") in _WIDGET_RUNTIME_KINDS
        and is_production_store(str(it.get("store_slug") or ""))
    ]
    if not matches:
        return None

    severity = "warning"
    if any(str(it.get("severity") or "") == STATUS_CRITICAL for it in matches):
        severity = "critical"

    stores = sorted(
        {str(it.get("store_slug") or "") for it in matches if it.get("store_slug")}
    )
    return _finalize_alert(
        "widget_runtime_missing",
        severity=severity,
        meta={"affected_stores": len(stores), "issue_count": len(matches)},
    )


def _build_summary(alerts: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"critical": 0, "warning": 0, "information": 0}
    for a in alerts:
        sev = str(a.get("severity") or "warning")
        if sev in counts:
            counts[sev] += 1
    highest = "healthy"
    if alerts:
        highest = min(
            (str(a.get("severity") or "warning") for a in alerts),
            key=lambda s: _SEVERITY_RANK.get(s, 99),
        )
    emoji, label = _SEVERITY_META.get(highest, ("🟢", "Healthy"))
    if not alerts:
        emoji, label = "🟢", "Healthy"
    return {
        "total": len(alerts),
        "highest_severity": highest,
        "highest_severity_emoji": emoji,
        "highest_severity_label": label,
        "critical_count": counts["critical"],
        "warning_count": counts["warning"],
        "information_count": counts["information"],
    }


def build_critical_alerts_readonly() -> dict[str, Any]:
    """Top-level Critical Alerts payload for Admin Operations."""
    alerts: list[dict[str, Any]] = []
    alerts.extend(_collect_dashboard_alerts())

    widget_alert = _collect_widget_runtime_alert()
    if widget_alert:
        alerts.append(widget_alert)

    alerts.sort(
        key=lambda a: (
            _SEVERITY_RANK.get(str(a.get("severity") or "warning"), 99),
            str(a.get("kind") or ""),
        )
    )

    summary = _build_summary(alerts)
    if not alerts:
        return {
            "section": SECTION_KEY,
            "status": "healthy",
            "summary": summary,
            "healthy": {
                "status_label": "Healthy",
                "message_en": "No critical operational issues detected.",
                "verification_en": "All monitored systems are operating normally.",
                "verification_lines_en": [
                    "All monitored systems are operating normally.",
                ],
            },
            "alerts": [],
        }

    return {
        "section": SECTION_KEY,
        "status": "alerts",
        "summary": summary,
        "healthy": None,
        "alerts": alerts,
    }


__all__ = [
    "SECTION_KEY",
    "build_critical_alerts_readonly",
    "_should_raise_db_init_slow_alert",
]
