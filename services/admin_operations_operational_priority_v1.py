# -*- coding: utf-8 -*-
"""
Admin Operations V3.4 — Operational priority queue (presentation-only).

Classifies affected production stores by operational urgency so operators know
what to work on first. Additive layer — does not change detection or grouping.
"""
from __future__ import annotations

from typing import Any

from services.admin_operations_root_cause_groups_v1 import (
    ROOT_CAUSE_IDENTITY,
    ROOT_CAUSE_ONBOARDING,
    ROOT_CAUSE_WHATSAPP,
    ROOT_CAUSE_WIDGET_RUNTIME,
)

PRIORITY_CRITICAL = "CRITICAL"
PRIORITY_HIGH = "HIGH"
PRIORITY_MEDIUM = "MEDIUM"
PRIORITY_LOW = "LOW"

_PRIORITY_RANK: dict[str, int] = {
    PRIORITY_CRITICAL: 0,
    PRIORITY_HIGH: 1,
    PRIORITY_MEDIUM: 2,
    PRIORITY_LOW: 3,
}

_PRIORITY_LABELS: dict[str, tuple[str, str]] = {
    PRIORITY_CRITICAL: ("🔥", "Requires Immediate Action"),
    PRIORITY_HIGH: ("⚠", "Needs Review"),
    PRIORITY_MEDIUM: ("⚠", "Needs Review"),
    PRIORITY_LOW: ("ℹ", "Monitoring"),
}

_ROOT_CAUSE_DEFAULT_PRIORITY: dict[str, str] = {
    ROOT_CAUSE_IDENTITY: PRIORITY_CRITICAL,
    ROOT_CAUSE_WIDGET_RUNTIME: PRIORITY_HIGH,
    ROOT_CAUSE_WHATSAPP: PRIORITY_HIGH,
    ROOT_CAUSE_ONBOARDING: PRIORITY_MEDIUM,
}

_WHATSAPP_PROVIDER_FAILURE_KINDS = frozenset(
    {"provider_unavailable", "provider_paused", "whatsapp_failed"}
)

_CRITICAL_STANDALONE_KINDS = frozenset(
    {
        "request_health_failure",
        "widget_module_failed",
        "widget_bootstrap_blocked",
        "failed_recovery",
        "stale_recovery",
        "whatsapp_failed",
        "store_identity_mismatch",
    }
)

_HIGH_STANDALONE_KINDS = frozenset(
    {
        "widget_runtime_missing",
        "widget_runtime_object_missing",
        "runtime_beacon_missing",
        "widget_not_seen",
        "cart_event_bridge_missing",
        "no_cart_events",
        "no_recent_cart_events",
        "whatsapp_missing",
        "whatsapp_not_connected",
    }
)

_MEDIUM_STANDALONE_KINDS = frozenset(
    {
        "store_needs_setup",
        "onboarding_incomplete",
        "store_setup_incomplete",
    }
)


def _symptom_kinds(root_cause: dict[str, Any]) -> set[str]:
    return {
        str(k).strip()
        for k in (root_cause.get("symptom_kinds") or [])
        if str(k).strip()
    }


def classify_root_cause_priority(root_cause: dict[str, Any]) -> str:
    """Return CRITICAL | HIGH | MEDIUM | LOW for one root cause card."""
    if not isinstance(root_cause, dict):
        return PRIORITY_LOW

    group_id = str(root_cause.get("root_cause_id") or "")
    kinds = _symptom_kinds(root_cause)
    severity = str(root_cause.get("severity") or "warning").strip().lower()

    if group_id == ROOT_CAUSE_WHATSAPP:
        if kinds & _WHATSAPP_PROVIDER_FAILURE_KINDS:
            return PRIORITY_CRITICAL
        return PRIORITY_HIGH

    if group_id in _ROOT_CAUSE_DEFAULT_PRIORITY:
        return _ROOT_CAUSE_DEFAULT_PRIORITY[group_id]

    if group_id.startswith("ROOT_CAUSE_STANDALONE_"):
        if kinds & _CRITICAL_STANDALONE_KINDS:
            return PRIORITY_CRITICAL
        if kinds & _MEDIUM_STANDALONE_KINDS:
            return PRIORITY_MEDIUM
        if kinds & _HIGH_STANDALONE_KINDS:
            return PRIORITY_HIGH
        if severity == "critical":
            return PRIORITY_CRITICAL
        if severity == "information":
            return PRIORITY_LOW
        return PRIORITY_HIGH

    if severity == "critical":
        return PRIORITY_CRITICAL
    if severity == "information":
        return PRIORITY_LOW
    return PRIORITY_HIGH


def _priority_meta(priority: str) -> dict[str, Any]:
    key = priority if priority in _PRIORITY_RANK else PRIORITY_LOW
    emoji, label = _PRIORITY_LABELS[key]
    return {
        "priority": key,
        "priority_rank": _PRIORITY_RANK[key],
        "priority_emoji": emoji,
        "priority_label_en": label,
        "priority_display_en": f"{emoji} {label}",
    }


def _escalate_store_priority(current: str, incoming: str) -> str:
    cur_rank = _PRIORITY_RANK.get(current, 99)
    inc_rank = _PRIORITY_RANK.get(incoming, 99)
    return current if cur_rank <= inc_rank else incoming


def apply_store_operational_priority(store_row: dict[str, Any]) -> dict[str, Any]:
    """Attach operational priority fields to a store queue row."""
    row = dict(store_row or {})
    root_causes = list(row.get("root_causes") or [])
    if not root_causes:
        row.update(_priority_meta(PRIORITY_LOW))
        row["primary_root_cause_name_en"] = ""
        return row

    store_priority = PRIORITY_LOW
    enriched_rc: list[dict[str, Any]] = []
    for rc in root_causes:
        if not isinstance(rc, dict):
            continue
        rc_copy = dict(rc)
        rc_prio = classify_root_cause_priority(rc_copy)
        rc_copy.update(_priority_meta(rc_prio))
        enriched_rc.append(rc_copy)
        store_priority = _escalate_store_priority(store_priority, rc_prio)

    enriched_rc.sort(
        key=lambda rc: (
            _PRIORITY_RANK.get(str(rc.get("priority") or PRIORITY_LOW), 99),
            str(rc.get("display_name_en") or ""),
        )
    )
    row["root_causes"] = enriched_rc
    row.update(_priority_meta(store_priority))
    primary = enriched_rc[0] if enriched_rc else None
    if primary:
        row["primary_root_cause"] = primary
        row["primary_root_cause_name_en"] = str(
            primary.get("display_name_en") or primary.get("problem_en") or ""
        )
    else:
        row["primary_root_cause_name_en"] = ""
    return row


def sort_stores_by_operational_priority(
    stores: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort affected stores by operational priority — never alphabetical by name."""
    return sorted(
        stores,
        key=lambda s: (
            0 if s.get("has_issues") else 1,
            int(s.get("priority_rank") if s.get("has_issues") else 99),
            str(s.get("store_slug") or ""),
        ),
    )


def summarize_operational_priority_stores(
    stores: list[dict[str, Any]],
) -> dict[str, int]:
    """Count production affected stores by operational priority bucket."""
    affected = [s for s in stores if s.get("has_issues")]
    return {
        "critical_priority_store_count": sum(
            1 for s in affected if s.get("priority") == PRIORITY_CRITICAL
        ),
        "high_priority_store_count": sum(
            1 for s in affected if s.get("priority") == PRIORITY_HIGH
        ),
        "medium_priority_store_count": sum(
            1 for s in affected if s.get("priority") == PRIORITY_MEDIUM
        ),
        "monitoring_store_count": sum(
            1 for s in affected if s.get("priority") == PRIORITY_LOW
        ),
    }


__all__ = [
    "PRIORITY_CRITICAL",
    "PRIORITY_HIGH",
    "PRIORITY_LOW",
    "PRIORITY_MEDIUM",
    "apply_store_operational_priority",
    "classify_root_cause_priority",
    "sort_stores_by_operational_priority",
    "summarize_operational_priority_stores",
]
