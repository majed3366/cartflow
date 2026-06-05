# -*- coding: utf-8 -*-
"""
Admin Operations V3 — Store Action Center (read-only, presentation-only).

Groups store-scoped operational issues so operators can see which stores need
action. Uses existing Widget Health, alerts, and store readiness truth only.
"""
from __future__ import annotations

from typing import Any, Optional

from services.admin_operations_action_engine_v1 import resolve_current_issue_guidance

SECTION_KEY = "store_action_center"

_SEVERITY_RANK = {"critical": 0, "warning": 1, "information": 2}
_SEVERITY_META: dict[str, tuple[str, str]] = {
    "critical": ("🔴", "Critical"),
    "warning": ("🟡", "Warning"),
    "information": ("🔵", "Information"),
}

_PLATFORM_ONLY_KINDS = frozenset(
    {
        "dashboard_restart_survival_failed",
        "dashboard_db_init_slow",
        "request_health_failure",
        "stale_recovery",
    }
)

_WIDGET_RUNTIME_KINDS = frozenset(
    {"runtime_beacon_missing", "widget_runtime_object_missing", "widget_runtime_missing"}
)

# Store-scoped operator copy (overrides action-engine defaults where specified).
_STORE_ISSUE_PRESENTATION: dict[str, dict[str, str]] = {
    "widget_runtime_missing": {
        "problem_en": "Widget runtime not detected.",
        "impact_en": "Customers may not see the widget.",
        "where_en": "Widget Health",
    },
    "whatsapp_missing": {
        "problem_en": "WhatsApp provider unavailable.",
        "impact_en": "Recovery messages cannot be sent.",
        "where_en": "WhatsApp Readiness",
        "verification_en": "Successful provider communication detected.",
    },
    "store_needs_setup": {
        "problem_en": "Store setup is incomplete.",
        "impact_en": "CartFlow functionality may be unavailable.",
        "where_en": "Merchant Setup",
        "verification_en": "Setup checklist completed.",
    },
    "store_identity_mismatch": {
        "problem_en": "Store identity mismatch detected.",
        "impact_en": "Data may appear under the wrong store.",
        "where_en": "Store Identity",
        "action_en": "Verify store identity mapping.",
        "verification_en": "Canonical store identity resolved.",
    },
}

_OPS_SEVERITY_TO_STORE: dict[str, str] = {
    "critical": "critical",
    "high": "warning",
    "medium": "warning",
    "low": "information",
}

_WIDGET_SEVERITY_TO_STORE: dict[str, str] = {
    "critical": "critical",
    "warning": "warning",
    "healthy": "information",
}


def _normalize_kind(kind: str) -> str:
    k = (kind or "").strip()
    if k in _WIDGET_RUNTIME_KINDS and k != "widget_runtime_missing":
        return "widget_runtime_missing"
    return k


def _escalate_severity(current: str, incoming: str) -> str:
    cur = current if current in _SEVERITY_RANK else "information"
    inc = incoming if incoming in _SEVERITY_RANK else "information"
    return cur if _SEVERITY_RANK[cur] <= _SEVERITY_RANK[inc] else inc


def _build_issue(kind: str, *, severity: str) -> dict[str, Any]:
    k = _normalize_kind(kind)
    guidance = resolve_current_issue_guidance(k)
    preset = dict(_STORE_ISSUE_PRESENTATION.get(k) or {})
    sev = severity if severity in _SEVERITY_META else "warning"
    emoji, label = _SEVERITY_META[sev]
    verification_lines = list(guidance.get("verification_lines_en") or [])
    verification_en = preset.get("verification_en") or guidance.get("verification_en", "")
    if preset.get("verification_en") and verification_en not in verification_lines:
        verification_lines = [verification_en]
    return {
        "kind": k,
        "severity": sev,
        "severity_emoji": emoji,
        "severity_label": label,
        "problem_en": preset.get("problem_en") or guidance.get("problem_en", ""),
        "impact_en": preset.get("impact_en") or guidance.get("impact_en", ""),
        "where_en": preset.get("where_en") or guidance.get("where_en", ""),
        "action_en": preset.get("action_en") or guidance.get("action_en", ""),
        "investigation_intro_en": guidance.get("investigation_intro_en", ""),
        "investigation_lines_en": list(guidance.get("investigation_lines_en") or []),
        "verification_en": verification_en,
        "verification_lines_en": verification_lines,
    }


def _store_bucket(
    stores: dict[str, dict[str, Any]],
    *,
    slug: str,
    name: str,
) -> dict[str, Any]:
    key = (slug or "").strip()
    if not key:
        key = "__unknown__"
    bucket = stores.get(key)
    if bucket is None:
        bucket = {
            "store_slug": slug or "",
            "store_name": name or slug or "Store",
            "highest_severity": "information",
            "issues_by_kind": {},
        }
        stores[key] = bucket
    if name and bucket.get("store_name") in ("Store", "", slug):
        bucket["store_name"] = name
    return bucket


def _add_issue(
    stores: dict[str, dict[str, Any]],
    *,
    slug: str,
    name: str,
    kind: str,
    severity: str,
) -> None:
    if not slug:
        return
    bucket = _store_bucket(stores, slug=slug, name=name)
    k = _normalize_kind(kind)
    issue = _build_issue(k, severity=severity)
    existing = bucket["issues_by_kind"].get(k)
    if existing is None or _SEVERITY_RANK.get(issue["severity"], 99) < _SEVERITY_RANK.get(
        existing.get("severity", "information"), 99
    ):
        bucket["issues_by_kind"][k] = issue
    bucket["highest_severity"] = _escalate_severity(
        str(bucket.get("highest_severity") or "information"),
        issue["severity"],
    )


def _collect_widget_issues(
    stores: dict[str, dict[str, Any]],
    *,
    store_rows: list[dict[str, Any]],
) -> None:
    try:
        from services.widget_health_v1 import (  # noqa: PLC0415
            STATUS_HEALTHY,
            build_admin_widget_health_section_readonly,
        )
    except Exception:  # noqa: BLE001
        return

    try:
        health = build_admin_widget_health_section_readonly(stores=store_rows)
    except Exception:  # noqa: BLE001
        return

    for issue in health.get("issues") or []:
        if not isinstance(issue, dict):
            continue
        slug = str(issue.get("store_slug") or "").strip()
        if not slug:
            continue
        kind = str(issue.get("kind") or "").strip()
        widget_sev = str(issue.get("severity") or STATUS_HEALTHY)
        if widget_sev == STATUS_HEALTHY:
            continue
        sev = _WIDGET_SEVERITY_TO_STORE.get(widget_sev, "warning")
        _add_issue(
            stores,
            slug=slug,
            name=str(issue.get("store_name") or slug),
            kind=kind,
            severity=sev,
        )


def _collect_readiness_issues(
    stores: dict[str, dict[str, Any]],
    *,
    store_rows: list[dict[str, Any]],
) -> None:
    for st in store_rows or []:
        if not isinstance(st, dict):
            continue
        slug = str(st.get("store_slug") or "").strip()
        if not slug:
            continue
        name = str(st.get("display_name") or slug)
        if not st.get("ready"):
            _add_issue(
                stores,
                slug=slug,
                name=name,
                kind="store_needs_setup",
                severity="warning",
            )
        if st.get("whatsapp_missing"):
            _add_issue(
                stores,
                slug=slug,
                name=name,
                kind="whatsapp_missing",
                severity="warning",
            )
        truth = str(st.get("widget_runtime_truth_status") or "").strip().lower()
        if truth in ("mismatch", "unresolved"):
            _add_issue(
                stores,
                slug=slug,
                name=name,
                kind="store_identity_mismatch",
                severity="warning",
            )


def _alert_severity(alert: dict[str, Any]) -> str:
    sev = str(alert.get("severity") or "low").strip().lower()
    return _OPS_SEVERITY_TO_STORE.get(sev, "information")


def _collect_alert_issues(
    stores: dict[str, dict[str, Any]],
    *,
    alerts: list[dict[str, Any]],
) -> None:
    for alert in alerts or []:
        if not isinstance(alert, dict):
            continue
        kind = str(alert.get("kind") or "").strip()
        if not kind or kind in _PLATFORM_ONLY_KINDS:
            continue
        records = alert.get("records") or []
        if not records:
            continue
        sev = _alert_severity(alert)
        for rec in records:
            if not isinstance(rec, dict):
                continue
            slug = str(rec.get("store_slug") or "").strip()
            if not slug:
                continue
            name = str(rec.get("store_name") or rec.get("display_name") or slug)
            _add_issue(stores, slug=slug, name=name, kind=kind, severity=sev)


def _finalize_stores(stores: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bucket in stores.values():
        issues = list((bucket.get("issues_by_kind") or {}).values())
        if not issues:
            continue
        issues.sort(
            key=lambda i: (
                _SEVERITY_RANK.get(str(i.get("severity") or "warning"), 99),
                str(i.get("kind") or ""),
            )
        )
        highest = str(bucket.get("highest_severity") or "warning")
        emoji, label = _SEVERITY_META.get(highest, ("🟡", "Warning"))
        out.append(
            {
                "store_slug": bucket.get("store_slug") or "",
                "store_name": bucket.get("store_name") or "",
                "highest_severity": highest,
                "severity_emoji": emoji,
                "severity_label": label,
                "issue_count": len(issues),
                "issues": issues,
                "primary_issue": issues[0],
            }
        )
    out.sort(
        key=lambda s: (
            _SEVERITY_RANK.get(str(s.get("highest_severity") or "warning"), 99),
            str(s.get("store_name") or s.get("store_slug") or ""),
        )
    )
    return out


def _build_summary(stores: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"critical": 0, "warning": 0, "information": 0}
    for store in stores:
        sev = str(store.get("highest_severity") or "warning")
        if sev in counts:
            counts[sev] += 1
    highest = "healthy"
    if stores:
        highest = min(
            (str(s.get("highest_severity") or "warning") for s in stores),
            key=lambda x: _SEVERITY_RANK.get(x, 99),
        )
    emoji, label = _SEVERITY_META.get(highest, ("🟢", "Healthy"))
    if not stores:
        emoji, label = "🟢", "Healthy"
    return {
        "affected_count": len(stores),
        "highest_severity": highest,
        "highest_severity_emoji": emoji,
        "highest_severity_label": label,
        "critical_count": counts["critical"],
        "warning_count": counts["warning"],
        "information_count": counts["information"],
    }


def build_store_action_center_readonly(
    *,
    store_rows: Optional[list[dict[str, Any]]] = None,
    alerts: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Store-level operational action payload for Admin Operations."""
    if store_rows is None or alerts is None:
        from services.admin_operations_center_v1 import _build_ops_shared_context  # noqa: PLC0415

        ctx = _build_ops_shared_context()
        store_rows = ctx.get("store_rows") or []
        alerts = ctx.get("alerts") or []

    grouped: dict[str, dict[str, Any]] = {}
    _collect_widget_issues(grouped, store_rows=store_rows)
    _collect_readiness_issues(grouped, store_rows=store_rows)
    _collect_alert_issues(grouped, alerts=alerts)

    stores = _finalize_stores(grouped)
    summary = _build_summary(stores)

    if not stores:
        return {
            "section": SECTION_KEY,
            "status": "healthy",
            "summary": summary,
            "healthy": {
                "status_label": "Healthy",
                "message_en": "No stores currently require operational intervention.",
                "verification_en": "All monitored stores are operating normally.",
                "verification_lines_en": [
                    "All monitored stores are operating normally.",
                ],
            },
            "stores": [],
        }

    return {
        "section": SECTION_KEY,
        "status": "affected",
        "summary": summary,
        "healthy": None,
        "stores": stores,
    }


__all__ = [
    "SECTION_KEY",
    "build_store_action_center_readonly",
]
