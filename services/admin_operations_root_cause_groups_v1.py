# -*- coding: utf-8 -*-
"""
Admin Operations V3.3 — Root cause grouping (presentation-only).

Collapses dependent symptom alerts into operational root causes for Store Action
Center. Does not change detection, alert generation, or data sources.
"""
from __future__ import annotations

from typing import Any

from services.admin_operations_action_engine_v1 import resolve_current_issue_guidance

_SEVERITY_RANK = {"critical": 0, "warning": 1, "information": 2}
_SEVERITY_META: dict[str, tuple[str, str]] = {
    "critical": ("🔴", "Critical"),
    "warning": ("🟡", "Warning"),
    "information": ("🔵", "Information"),
}

ROOT_CAUSE_WIDGET_RUNTIME = "ROOT_CAUSE_WIDGET_RUNTIME"
ROOT_CAUSE_WHATSAPP = "ROOT_CAUSE_WHATSAPP"
ROOT_CAUSE_ONBOARDING = "ROOT_CAUSE_ONBOARDING"
ROOT_CAUSE_IDENTITY = "ROOT_CAUSE_IDENTITY"

_ROOT_CAUSE_META: dict[str, dict[str, Any]] = {
    ROOT_CAUSE_WIDGET_RUNTIME: {
        "display_name_en": "Widget Runtime Missing",
        "impact_en": (
            "Customers may not see the widget. "
            "Cart tracking may not function. "
            "Recovery flows may not start."
        ),
        "where_en": "Widget Health",
        "action_en": "Verify widget installation and runtime connectivity.",
        "verification_en": "Widget Health shows runtime beacon and cart activity.",
        "verification_lines_en": [
            "Widget Health = Healthy",
            "Runtime beacon received",
            "Cart events detected after test add-to-cart",
        ],
        "kinds": frozenset(
            {
                "widget_runtime_missing",
                "widget_runtime_object_missing",
                "runtime_beacon_missing",
                "widget_not_seen",
                "cart_event_bridge_missing",
                "no_recent_cart_events",
                "no_cart_events",
            }
        ),
    },
    ROOT_CAUSE_WHATSAPP: {
        "display_name_en": "WhatsApp Not Ready",
        "impact_en": "Recovery messages cannot be sent to customers.",
        "where_en": "WhatsApp Readiness",
        "action_en": "Complete WhatsApp provider connection and confirm send readiness.",
        "verification_en": "Successful provider communication detected.",
        "verification_lines_en": [
            "WhatsApp provider connected",
            "Test recovery message delivers successfully",
        ],
        "kinds": frozenset(
            {
                "whatsapp_not_connected",
                "whatsapp_missing",
                "provider_unavailable",
                "provider_paused",
            }
        ),
    },
    ROOT_CAUSE_ONBOARDING: {
        "display_name_en": "Store Setup Incomplete",
        "impact_en": "CartFlow functionality may be unavailable until setup is finished.",
        "where_en": "Merchant Setup",
        "action_en": "Complete the merchant setup checklist for the store.",
        "verification_en": "Setup checklist completed.",
        "verification_lines_en": [
            "All required setup steps are complete",
            "Store readiness shows ready",
        ],
        "kinds": frozenset(
            {
                "onboarding_incomplete",
                "store_setup_incomplete",
                "store_needs_setup",
            }
        ),
    },
    ROOT_CAUSE_IDENTITY: {
        "display_name_en": "Store Identity Mismatch",
        "impact_en": "Data may appear under the wrong store or fail to reconcile.",
        "where_en": "Store Identity",
        "action_en": "Verify store identity mapping and canonical slug linkage.",
        "verification_en": "Canonical store identity resolved across sources.",
        "verification_lines_en": [
            "Store identity matches across dashboard, public-config, and beacon",
        ],
        "kinds": frozenset({"store_identity_mismatch"}),
    },
}

_SIGNAL_LABELS: dict[str, str] = {
    "widget_runtime_missing": "Widget Visibility",
    "widget_runtime_object_missing": "Runtime Object",
    "runtime_beacon_missing": "Runtime Beacon",
    "widget_not_seen": "Widget Visibility",
    "cart_event_bridge_missing": "Cart Events",
    "no_recent_cart_events": "Cart Events",
    "no_cart_events": "Cart Events",
    "whatsapp_not_connected": "WhatsApp Connection",
    "whatsapp_missing": "WhatsApp Provider",
    "provider_unavailable": "Provider Availability",
    "provider_paused": "Provider Paused",
    "onboarding_incomplete": "Onboarding Steps",
    "store_setup_incomplete": "Setup Checklist",
    "store_needs_setup": "Setup Checklist",
    "store_identity_mismatch": "Identity Mapping",
}

_KIND_TO_GROUP: dict[str, str] = {}
for _gid, _meta in _ROOT_CAUSE_META.items():
    for _k in _meta["kinds"]:
        _KIND_TO_GROUP[_k] = _gid


def resolve_root_cause_group(kind: str) -> str | None:
    """Return root cause group id for a symptom kind, or None when ungrouped."""
    return _KIND_TO_GROUP.get((kind or "").strip())


def _symptom_kind(issue: dict[str, Any]) -> str:
    return str(issue.get("source_kind") or issue.get("kind") or "").strip()


def _signal_label(kind: str) -> str:
    k = (kind or "").strip()
    return _SIGNAL_LABELS.get(k) or k.replace("_", " ").title()


def _escalate_severity(current: str, incoming: str) -> str:
    cur = current if current in _SEVERITY_RANK else "information"
    inc = incoming if incoming in _SEVERITY_RANK else "information"
    return cur if _SEVERITY_RANK[cur] <= _SEVERITY_RANK[inc] else inc


def _severity_meta(severity: str) -> tuple[str, str, str]:
    sev = severity if severity in _SEVERITY_META else "warning"
    emoji, label = _SEVERITY_META[sev]
    return sev, emoji, label


def _build_grouped_root_cause(
    group_id: str,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    meta = _ROOT_CAUSE_META[group_id]
    severity = "information"
    for issue in issues:
        severity = _escalate_severity(severity, str(issue.get("severity") or "warning"))

    signals: list[str] = []
    seen_signals: set[str] = set()
    for issue in issues:
        label = _signal_label(_symptom_kind(issue))
        if label not in seen_signals:
            seen_signals.add(label)
            signals.append(label)

    sev, emoji, label = _severity_meta(severity)
    guidance = resolve_current_issue_guidance(
        _symptom_kind(issues[0]) if issues else group_id
    )
    return {
        "root_cause_id": group_id,
        "display_name_en": meta["display_name_en"],
        "severity": sev,
        "severity_emoji": emoji,
        "severity_label": label,
        "problem_en": meta["display_name_en"],
        "impact_en": meta["impact_en"],
        "where_en": meta.get("where_en") or guidance.get("where_en", ""),
        "affected_signals": signals,
        "action_en": meta.get("action_en") or guidance.get("action_en", ""),
        "investigation_intro_en": guidance.get("investigation_intro_en", ""),
        "investigation_lines_en": list(guidance.get("investigation_lines_en") or []),
        "verification_en": meta.get("verification_en") or guidance.get("verification_en", ""),
        "verification_lines_en": list(
            meta.get("verification_lines_en")
            or guidance.get("verification_lines_en")
            or []
        ),
        "symptom_count": len(issues),
        "symptom_kinds": sorted({_symptom_kind(i) for i in issues if _symptom_kind(i)}),
    }


def _build_standalone_root_cause(issue: dict[str, Any]) -> dict[str, Any]:
    kind = _symptom_kind(issue)
    sev, emoji, label = _severity_meta(str(issue.get("severity") or "warning"))
    display = str(issue.get("problem_en") or kind.replace("_", " ").title())
    signal = _signal_label(kind)
    return {
        "root_cause_id": f"ROOT_CAUSE_STANDALONE_{kind or 'unknown'}",
        "display_name_en": display,
        "severity": sev,
        "severity_emoji": emoji,
        "severity_label": label,
        "problem_en": display,
        "impact_en": issue.get("impact_en", ""),
        "where_en": issue.get("where_en", ""),
        "affected_signals": [signal] if signal else [],
        "action_en": issue.get("action_en", ""),
        "investigation_intro_en": issue.get("investigation_intro_en", ""),
        "investigation_lines_en": list(issue.get("investigation_lines_en") or []),
        "verification_en": issue.get("verification_en", ""),
        "verification_lines_en": list(issue.get("verification_lines_en") or []),
        "symptom_count": 1,
        "symptom_kinds": [kind] if kind else [],
    }


def group_issues_into_root_causes(issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse symptom issues into root cause cards (presentation-only)."""
    grouped: dict[str, list[dict[str, Any]]] = {}
    standalone: list[dict[str, Any]] = []

    for issue in issues or []:
        if not isinstance(issue, dict):
            continue
        kind = _symptom_kind(issue)
        group_id = resolve_root_cause_group(kind)
        if group_id:
            grouped.setdefault(group_id, []).append(issue)
        else:
            standalone.append(issue)

    root_causes: list[dict[str, Any]] = []
    for group_id in (
        ROOT_CAUSE_WIDGET_RUNTIME,
        ROOT_CAUSE_WHATSAPP,
        ROOT_CAUSE_ONBOARDING,
        ROOT_CAUSE_IDENTITY,
    ):
        if group_id in grouped:
            root_causes.append(_build_grouped_root_cause(group_id, grouped[group_id]))

    for issue in standalone:
        root_causes.append(_build_standalone_root_cause(issue))

    root_causes.sort(
        key=lambda rc: (
            _SEVERITY_RANK.get(str(rc.get("severity") or "warning"), 99),
            str(rc.get("display_name_en") or ""),
        )
    )
    return root_causes


def root_cause_count_label(*, count: int) -> str:
    if count <= 0:
        return "Healthy"
    suffix = "Root Cause" if count == 1 else "Root Causes"
    return f"{count} {suffix}"


def summarize_root_causes(
    stores: list[dict[str, Any]],
) -> dict[str, int]:
    """Aggregate root-cause metrics across store rows."""
    affected = [s for s in stores if s.get("has_issues")]
    total = sum(int(s.get("root_cause_count") or 0) for s in affected)
    critical = 0
    warning = 0
    for store in affected:
        for rc in store.get("root_causes") or []:
            sev = str(rc.get("severity") or "warning")
            if sev == "critical":
                critical += 1
            elif sev == "warning":
                warning += 1
    return {
        "root_cause_count": total,
        "critical_root_cause_count": critical,
        "warning_root_cause_count": warning,
    }


__all__ = [
    "ROOT_CAUSE_IDENTITY",
    "ROOT_CAUSE_ONBOARDING",
    "ROOT_CAUSE_WHATSAPP",
    "ROOT_CAUSE_WIDGET_RUNTIME",
    "group_issues_into_root_causes",
    "resolve_root_cause_group",
    "root_cause_count_label",
    "summarize_root_causes",
]
