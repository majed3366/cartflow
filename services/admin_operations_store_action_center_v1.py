# -*- coding: utf-8 -*-
"""
Admin Operations V3 — Store Action Center (read-only, presentation-only).

Groups store-scoped operational issues so operators can see which stores need
action. Uses existing Widget Health, alerts, and store readiness truth only.
"""
from __future__ import annotations

from typing import Any, Optional

from services.admin_operations_action_engine_v1 import resolve_current_issue_guidance
from services.admin_operations_production_truth_v1 import (
    count_dev_test_buckets,
    is_production_store,
)

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


def _issue_count_label(*, count: int, highest_severity: str) -> str:
    if count <= 0:
        return "Healthy"
    if count == 1 and highest_severity == "critical":
        return "1 Critical"
    suffix = "Issue" if count == 1 else "Issues"
    return f"{count} {suffix}"


def _store_row_from_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    issues = list((bucket.get("issues_by_kind") or {}).values())
    issues.sort(
        key=lambda i: (
            _SEVERITY_RANK.get(str(i.get("severity") or "warning"), 99),
            str(i.get("kind") or ""),
        )
    )
    slug = str(bucket.get("store_slug") or "")
    if issues:
        highest = str(bucket.get("highest_severity") or "warning")
    else:
        highest = "healthy"
    if highest == "healthy":
        emoji, label = "🟢", "Healthy"
    else:
        emoji, label = _SEVERITY_META.get(highest, ("🟡", "Warning"))
    issue_count = len(issues)
    return {
        "store_slug": slug,
        "store_name": bucket.get("store_name") or slug or "Store",
        "environment": "demo_test" if not is_production_store(slug) else "production",
        "highest_severity": highest,
        "severity_emoji": emoji,
        "severity_label": label,
        "issue_count": issue_count,
        "issue_count_label": _issue_count_label(
            count=issue_count,
            highest_severity=highest,
        ),
        "issues": issues,
        "primary_issue": issues[0] if issues else None,
        "has_issues": issue_count > 0,
    }


def _finalize_stores(stores: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for bucket in stores.values():
        slug = str(bucket.get("store_slug") or "")
        if not is_production_store(slug):
            continue
        row = _store_row_from_bucket(bucket)
        if row.get("has_issues"):
            out.append(row)
    out.sort(
        key=lambda s: (
            _SEVERITY_RANK.get(str(s.get("highest_severity") or "warning"), 99),
            str(s.get("store_name") or s.get("store_slug") or ""),
        )
    )
    return out


def _build_queue_rows(
    *,
    store_rows: list[dict[str, Any]],
    grouped: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """One row per scanned store — affected and healthy."""
    merged: dict[str, dict[str, Any]] = {}
    for st in store_rows or []:
        if not isinstance(st, dict):
            continue
        slug = str(st.get("store_slug") or "").strip()
        if not slug:
            continue
        name = str(st.get("display_name") or slug)
        merged[slug] = {
            "store_slug": slug,
            "store_name": name,
            "highest_severity": "healthy",
            "issues_by_kind": {},
        }
    for slug, bucket in grouped.items():
        if slug in merged:
            merged[slug]["issues_by_kind"] = dict(bucket.get("issues_by_kind") or {})
            merged[slug]["highest_severity"] = bucket.get("highest_severity") or "warning"
            if bucket.get("store_name"):
                merged[slug]["store_name"] = bucket["store_name"]
        elif bucket.get("issues_by_kind"):
            merged[slug] = bucket

    rows = [_store_row_from_bucket(b) for b in merged.values()]
    rows.sort(
        key=lambda s: (
            0 if s.get("has_issues") else 1,
            _SEVERITY_RANK.get(
                str(s.get("highest_severity") or "healthy"),
                99 if s.get("has_issues") else 100,
            ),
            str(s.get("store_name") or s.get("store_slug") or ""),
        )
    )
    return rows


def _split_queues(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    production: list[dict[str, Any]] = []
    demo_test: list[dict[str, Any]] = []
    for row in rows:
        if is_production_store(str(row.get("store_slug") or "")):
            production.append(row)
        else:
            demo_test.append(row)
    return production, demo_test


def _build_summary(
    *,
    production_queue: list[dict[str, Any]],
    demo_test_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    def _counts(queue: list[dict[str, Any]]) -> dict[str, int]:
        affected = [s for s in queue if s.get("has_issues")]
        critical = sum(1 for s in affected if s.get("highest_severity") == "critical")
        warning = sum(1 for s in affected if s.get("highest_severity") == "warning")
        information = sum(1 for s in affected if s.get("highest_severity") == "information")
        healthy = sum(1 for s in queue if not s.get("has_issues"))
        return {
            "store_count": len(queue),
            "affected_count": len(affected),
            "critical_count": critical,
            "warning_count": warning,
            "information_count": information,
            "healthy_count": healthy,
        }

    prod = _counts(production_queue)
    demo = _counts(demo_test_queue)
    highest = "healthy"
    if prod["affected_count"] > 0:
        for sev in ("critical", "warning", "information"):
            if prod.get(f"{sev}_count", 0) > 0:
                highest = sev
                break
    emoji, label = _SEVERITY_META.get(highest, ("🟢", "Healthy"))
    if prod["affected_count"] == 0:
        emoji, label = "🟢", "Healthy"

    return {
        # Operational truth — production merchants only.
        "affected_count": prod["affected_count"],
        "highest_severity": highest,
        "highest_severity_emoji": emoji,
        "highest_severity_label": label,
        "critical_count": prod["critical_count"],
        "warning_count": prod["warning_count"],
        "information_count": prod["information_count"],
        "healthy_count": prod["healthy_count"],
        "production_store_count": prod["store_count"],
        "production_affected_count": prod["affected_count"],
        "production_critical_count": prod["critical_count"],
        "production_warning_count": prod["warning_count"],
        "production_healthy_count": prod["healthy_count"],
        "demo_test_store_count": demo["store_count"],
        "demo_test_affected_count": demo["affected_count"],
        "all_affected_count": prod["affected_count"] + demo["affected_count"],
    }


def _dev_test_breakdown(
    *,
    demo_test_queue: list[dict[str, Any]],
    store_rows: list[dict[str, Any]],
) -> dict[str, int]:
    base = count_dev_test_buckets(store_rows)
    # Ensure buckets reflect scanned rows even if queue is partial.
    return {
        "demo_stores": base.get("demo", 0),
        "loadtest_stores": base.get("loadtest", 0),
        "sandbox_stores": base.get("sandbox", 0),
        "other_test_stores": base.get("other_test", 0),
        "affected_in_scan": sum(1 for s in demo_test_queue if s.get("has_issues")),
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

    queue_rows = _build_queue_rows(store_rows=store_rows, grouped=grouped)
    production_queue, demo_test_queue = _split_queues(queue_rows)
    stores = _finalize_stores(grouped)
    summary = _build_summary(
        production_queue=production_queue,
        demo_test_queue=demo_test_queue,
    )
    dev_test = _dev_test_breakdown(
        demo_test_queue=demo_test_queue,
        store_rows=store_rows,
    )
    production_action_queue = [s for s in production_queue if s.get("has_issues")]

    production_affected = summary.get("production_affected_count", 0)
    if production_affected == 0:
        healthy_msg = "No production stores currently require intervention."
        if summary.get("demo_test_affected_count", 0) > 0:
            healthy_msg = (
                "No production stores currently require intervention. "
                "Development & Test activity is listed separately below."
            )
        return {
            "section": SECTION_KEY,
            "status": "healthy",
            "summary": summary,
            "dev_test": dev_test,
            "healthy": {
                "status_label": "Healthy",
                "message_en": healthy_msg,
                "verification_en": "All monitored production stores are operating normally.",
                "verification_lines_en": [
                    "All monitored production stores are operating normally.",
                ],
            },
            "stores": stores,
            "production_queue": production_queue,
            "production_action_queue": production_action_queue,
            "demo_test_queue": demo_test_queue,
        }

    return {
        "section": SECTION_KEY,
        "status": "affected",
        "summary": summary,
        "dev_test": dev_test,
        "healthy": None,
        "stores": stores,
        "production_queue": production_queue,
        "production_action_queue": production_action_queue,
        "demo_test_queue": demo_test_queue,
    }


__all__ = [
    "SECTION_KEY",
    "build_store_action_center_readonly",
]
