# -*- coding: utf-8 -*-
"""
Rule-based action + verification guidance for Admin Operations (V1).

Deterministic operator-facing copy — no LLM. Diagnostics inform rules only.
"""
from __future__ import annotations

from typing import Any, Optional

from services.db_ready_operational_snapshot_v1 import HEALTHY_MAX_MS

# Alert kinds with explicit operator guidance (extend as new alerts appear).
_ALERT_RULES: dict[str, dict[str, str]] = {
    "dashboard_restart_survival_failed": {
        "action_en": "Inspect Startup Warm execution and [RESTART SURVIVAL] logs.",
        "verification_en": "Restart Survival must return PASS with cached verification and first dashboard under 1000 ms.",
    },
    "dashboard_db_init_slow": {
        "action_en": "Review DB Ready stages in logs ([DB READY STAGE] / [DB READY SUBSTAGE]).",
        "verification_en": f"Last dashboard initialization duration returns below {int(HEALTHY_MAX_MS)} ms (healthy threshold).",
    },
    "widget_runtime_missing": {
        "action_en": "Verify widget installation and runtime beacon on the storefront.",
        "verification_en": "Widget Health shows Healthy and runtime beacon is received.",
    },
    "runtime_beacon_missing": {
        "action_en": "Verify widget installation and runtime beacon on the storefront.",
        "verification_en": "Widget Health shows Healthy and runtime beacon is received.",
    },
    "widget_not_seen": {
        "action_en": "Confirm widget script loads on the storefront and test a cart event.",
        "verification_en": "Widget appears for customers and Widget Health status improves.",
    },
    "widget_bootstrap_blocked": {
        "action_en": "Check storefront console for failed widget modules and reinstall if needed.",
        "verification_en": "Widget bootstrap completes and Widget Health is no longer critical.",
    },
    "widget_module_failed": {
        "action_en": "Check storefront console for failed widget modules and reinstall if needed.",
        "verification_en": "Widget modules load successfully on the storefront.",
    },
    "public_config_not_loaded": {
        "action_en": "Verify store slug, public-config endpoint, and merchant dashboard settings.",
        "verification_en": "Public config loads and Widget Health shows config OK.",
    },
    "cart_event_bridge_missing": {
        "action_en": "Verify cart-event bridge wiring and test add-to-cart on the storefront.",
        "verification_en": "Cart events appear after a test add-to-cart.",
    },
    "store_identity_mismatch": {
        "action_en": "Review store identity aliases and dashboard store linkage.",
        "verification_en": "Store identity matches across dashboard, public-config, and beacon.",
    },
    "widget_settings_mismatch": {
        "action_en": "Compare dashboard settings with public-config and storefront beacon.",
        "verification_en": "Settings match across dashboard, public-config, and beacon.",
    },
    "stale_recovery": {
        "action_en": "Review scheduler health and overdue recovery schedules.",
        "verification_en": "Overdue scheduled recoveries return to zero.",
    },
    "failed_recovery": {
        "action_en": "Review WhatsApp provider delivery status and recent failure logs.",
        "verification_en": "Latest recovery messages deliver successfully.",
    },
    "whatsapp_missing": {
        "action_en": "Complete WhatsApp provider setup and store sending number.",
        "verification_en": "Store shows ready for WhatsApp send.",
    },
    "store_needs_setup": {
        "action_en": "Guide the merchant through remaining setup steps.",
        "verification_en": "Store readiness shows ready.",
    },
    "no_cart_events": {
        "action_en": "Verify widget install and test add-to-cart on the storefront.",
        "verification_en": "New cart events appear after test.",
    },
}

# English problem/impact/where for Current Issues cards (presentation-only).
_ISSUE_EN: dict[str, dict[str, str]] = {
    "dashboard_restart_survival_failed": {
        "problem_en": "Dashboard startup protection failed after restart.",
        "impact_en": (
            "The first merchant dashboard request after restart may not have been "
            "protected from cold-start initialization."
        ),
        "where_en": "Dashboard Initialization",
    },
    "dashboard_db_init_slow": {
        "problem_en": "Dashboard initialization is slower than expected.",
        "impact_en": (
            "Some merchants may experience slower dashboard loading, "
            "especially immediately after a restart."
        ),
        "where_en": "Dashboard Initialization",
    },
    "widget_runtime_missing": {
        "problem_en": "Widget runtime is missing on affected storefronts.",
        "impact_en": "Customers may not see the widget and cart recovery may not run.",
        "where_en": "Storefront widget runtime",
    },
    "runtime_beacon_missing": {
        "problem_en": "Widget runtime beacon is not received from affected stores.",
        "impact_en": "CartFlow cannot confirm the widget is running on the storefront.",
        "where_en": "Storefront widget runtime",
    },
    "widget_not_seen": {
        "problem_en": "Widget is not visible to customers on affected stores.",
        "impact_en": "Cart recovery and hesitation flows may not engage shoppers.",
        "where_en": "Storefront widget display",
    },
    "widget_bootstrap_blocked": {
        "problem_en": "Widget bootstrap is blocked on affected stores.",
        "impact_en": "The widget cannot start and cart events may not be captured.",
        "where_en": "Storefront widget bootstrap",
    },
    "widget_module_failed": {
        "problem_en": "Widget module failed to load on affected stores.",
        "impact_en": "The widget cannot run and recovery features are unavailable.",
        "where_en": "Storefront widget modules",
    },
    "public_config_not_loaded": {
        "problem_en": "Public widget config is not loading for affected stores.",
        "impact_en": "The widget may use defaults instead of merchant settings.",
        "where_en": "Public config / widget settings",
    },
    "cart_event_bridge_missing": {
        "problem_en": "Cart event bridge is missing on affected stores.",
        "impact_en": "Add-to-cart activity may not be detected for recovery.",
        "where_en": "Storefront cart event bridge",
    },
    "store_identity_mismatch": {
        "problem_en": "Store identity mismatch detected.",
        "impact_en": "Widget settings may not match the merchant dashboard.",
        "where_en": "Store identity / linkage",
    },
    "widget_settings_mismatch": {
        "problem_en": "Widget settings mismatch across sources.",
        "impact_en": "Customers may see incorrect branding or behavior.",
        "where_en": "Dashboard / public-config / beacon",
    },
    "stale_recovery": {
        "problem_en": "Scheduled recoveries are overdue.",
        "impact_en": "Recovery messages may be delayed and miss conversion opportunities.",
        "where_en": "Scheduled recovery processing",
    },
    "failed_recovery": {
        "problem_en": "Recovery messages are failing to deliver.",
        "impact_en": "Stores may lose abandoned-cart recovery opportunities.",
        "where_en": "WhatsApp / recovery delivery",
    },
    "whatsapp_missing": {
        "problem_en": "WhatsApp provider is not configured for affected stores.",
        "impact_en": "Stores cannot send recovery messages until setup is complete.",
        "where_en": "Store WhatsApp setup",
    },
    "store_needs_setup": {
        "problem_en": "Store setup is incomplete.",
        "impact_en": "Recovery will not work correctly until setup is finished.",
        "where_en": "Merchant onboarding / setup",
    },
    "no_cart_events": {
        "problem_en": "No recent cart events detected.",
        "impact_en": "May indicate widget install or integration problems.",
        "where_en": "Cart tracking / storefront widget",
    },
}


def _line(label: str, value: Any) -> str:
    if value is None or value == "":
        return f"{label} = —"
    if isinstance(value, bool):
        return f"{label} = {'Yes' if value else 'No'}"
    return f"{label} = {value}"


def resolve_alert_guidance(
    alert_type: str,
    *,
    diagnostics: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Guidance for a Current Issues alert kind."""
    kind = (alert_type or "").strip()
    base = dict(_ALERT_RULES.get(kind) or {})
    if not base:
        base = {
            "action_en": "Review the linked operational logs and affected stores.",
            "verification_en": "The alert clears and affected stores return to healthy.",
        }
    return base


def resolve_current_issue_guidance(
    alert_type: str,
    *,
    diagnostics: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Full operator guidance for a Current Issues alert kind."""
    kind = (alert_type or "").strip()
    action = resolve_alert_guidance(kind, diagnostics=diagnostics)
    base = dict(_ISSUE_EN.get(kind) or {})
    if not base.get("problem_en"):
        base["problem_en"] = kind.replace("_", " ").strip() or "Operational issue detected"
    if not base.get("impact_en"):
        base["impact_en"] = "Review affected stores and operational logs."
    if not base.get("where_en"):
        base["where_en"] = "Operations"
    return {
        "problem_en": base.get("problem_en", ""),
        "impact_en": base.get("impact_en", ""),
        "where_en": base.get("where_en", ""),
        "action_en": action.get("action_en", ""),
        "verification_en": action.get("verification_en", ""),
    }


def resolve_widget_issue_guidance(kind: str) -> dict[str, str]:
    """Operator guidance for grouped widget health issues."""
    k = (kind or "").strip()
    if k == "widget_runtime_missing":
        k = "runtime_beacon_missing"
    g = resolve_current_issue_guidance(k)
    return {
        "problem_en": g["problem_en"],
        "impact_en": g["impact_en"],
        "where_en": g["where_en"],
        "suggested_action_en": g["action_en"],
        "verification_en": g["verification_en"],
    }


def resolve_dashboard_db_ready_guidance(
    *,
    operational_status: str,
    diagnostics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Operations-first guidance for Dashboard Initialization card."""
    diag = diagnostics or {}
    status = (operational_status or "healthy").strip().lower()
    rs = diag.get("restart_survival") or {}
    rs_result = str(rs.get("verification_result") or "PENDING").upper()
    last_ms = round(float(diag.get("last_duration_ms") or 0.0), 1)
    startup_status = str(diag.get("startup_warm_status") or "not_started")
    cached = diag.get("last_request_cached_verification")
    first_dur = round(float(rs.get("first_dashboard_duration_ms") or 0.0), 1)
    first_cached = rs.get("first_dashboard_cached_verification")

    if rs_result == "FAIL":
        problem_en = "Dashboard startup protection failed after restart."
        impact_en = (
            "The first merchant dashboard request after restart may not have been "
            "protected from cold-start initialization."
        )
        action_en = resolve_alert_guidance("dashboard_restart_survival_failed")["action_en"]
        verification_lines = [
            _line("Restart Survival", rs_result),
            _line("Startup warm status", startup_status),
            _line("First dashboard duration", f"{first_dur} ms"),
            _line("Cached verification", first_cached),
        ]
    elif status in ("slow", "blocking"):
        problem_en = "Dashboard initialization is slower than expected."
        impact_en = (
            "Some merchants may experience slower dashboard loading, "
            "especially immediately after a restart."
        )
        action_en = resolve_alert_guidance("dashboard_db_init_slow")["action_en"]
        verification_lines = [
            _line("Last duration", f"{last_ms} ms"),
            _line("Healthy threshold", f"< {int(HEALTHY_MAX_MS)} ms"),
            _line("Operational status", status),
        ]
    elif rs_result == "PASS" or status == "healthy":
        problem_en = "Dashboard initialization is operating normally."
        impact_en = (
            "Merchants should experience normal dashboard loading after restart."
        )
        action_en = (
            "No action required. Startup Warm is active and protecting requests."
        )
        verification_lines = [
            _line("Restart Survival", rs_result if rs_result != "PENDING" else "PASS"),
            _line("First dashboard request", f"{first_dur} ms" if first_dur else f"{last_ms} ms"),
            _line("First dashboard under 1000 ms", (first_dur or last_ms) < 1000),
            _line("Cached verification", first_cached if first_cached is not None else cached),
            _line("Startup warm status", startup_status),
        ]
    else:
        problem_en = "Dashboard initialization status is pending verification."
        impact_en = (
            "Await the first merchant dashboard request after restart to confirm protection."
        )
        action_en = (
            "No immediate action. Open the merchant dashboard once after restart to complete verification."
        )
        verification_lines = [
            _line("Restart Survival", rs_result),
            _line("Startup warm status", startup_status),
            _line("Last duration", f"{last_ms} ms"),
        ]

    verification_en = " · ".join(verification_lines)
    return {
        "problem_en": problem_en,
        "impact_en": impact_en,
        "where_en": "Dashboard Initialization",
        "action_en": action_en,
        "verification_en": verification_en,
        "verification_lines_en": verification_lines,
    }


def resolve_operations_guidance(
    *,
    card_key: str = "",
    operational_status: str = "healthy",
    pass_fail: Optional[str] = None,
    alert_type: Optional[str] = None,
    diagnostics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Unified entry — returns operator-facing guidance for an Operations card.

    Parameters
    ----------
    card_key:
        Section identifier (e.g. ``dashboard_db_ready``, ``widget_health``).
    operational_status:
        healthy | slow | blocking | warning | critical
    pass_fail:
        PASS | FAIL | PENDING for survival-style checks
    alert_type:
        Alert kind when resolving from Current Issues
    diagnostics:
        Read-only metrics dict informing rules
    """
    key = (card_key or "").strip().lower()
    if alert_type:
        g = resolve_current_issue_guidance(alert_type, diagnostics=diagnostics)
        return {
            **g,
            "verification_lines_en": [g.get("verification_en", "")],
        }
    if key in ("dashboard_db_ready", "db_ready", "dashboard_initialization"):
        d = dict(diagnostics or {})
        if pass_fail:
            rs = dict(d.get("restart_survival") or {})
            rs["verification_result"] = pass_fail
            d["restart_survival"] = rs
        return resolve_dashboard_db_ready_guidance(
            operational_status=operational_status,
            diagnostics=d,
        )
    return {
        "problem_en": "Operational review needed.",
        "impact_en": "See section diagnostics for affected areas.",
        "where_en": card_key or "Operations",
        "action_en": "Review operational logs for this section.",
        "verification_en": "Status returns to healthy.",
        "verification_lines_en": [],
    }


__all__ = [
    "resolve_alert_guidance",
    "resolve_current_issue_guidance",
    "resolve_dashboard_db_ready_guidance",
    "resolve_operations_guidance",
    "resolve_widget_issue_guidance",
]
