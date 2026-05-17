# -*- coding: utf-8 -*-
"""
Admin Operational Control v2 — modular read-only control layer.

Modules: risk_summary, impact_layer, actions_layer, verification_layer,
revenue_protection, operational_timeline.
"""
from __future__ import annotations

from typing import Any

from services.admin_operational_control.admin_actions_layer import build_admin_actions_layer
from services.admin_operational_control.admin_impact_layer import build_admin_impact_layer
from services.admin_operational_control.admin_operational_timeline import (
    build_admin_operational_timeline,
)
from services.admin_operational_control.admin_revenue_protection import (
    build_admin_revenue_protection,
)
from services.admin_operational_control.admin_risk_summary import build_admin_risk_summary
from services.admin_operational_control.admin_verification_layer import (
    build_admin_verification_layer,
    clear_verification_state_for_tests,
)
from services.admin_operational_control.context import OperationalControlContext
from services.admin_operational_control.signals import build_operational_issues


def build_admin_operational_control_readonly() -> dict[str, Any]:
    from services.admin_operational_health import (  # noqa: PLC0415
        build_operational_control_context,
    )

    ctx = build_operational_control_context()
    ctx.issues = build_operational_issues(ctx)

    risk = build_admin_risk_summary(ctx)
    impact = build_admin_impact_layer(ctx)
    actions = build_admin_actions_layer(ctx)
    verification = build_admin_verification_layer(ctx)
    revenue = build_admin_revenue_protection(ctx)
    timeline = build_admin_operational_timeline(ctx)

    quick_answers = {
        "is_healthy_ar": (
            "نعم — لا خطر فوري"
            if not risk.get("risk_detected")
            else "لا — يوجد خطر تشغيلي"
        ),
        "what_failing_ar": (
            "؛ ".join(i.problem_ar for i in ctx.issues if i.active)[:240]
            if ctx.issues
            else "لا فشل نشط"
        ),
        "who_affected_ar": (
            f"{ctx.affected_stores_estimate} متجر (تقدير)"
            if risk.get("risk_detected")
            else "لا تأثير مباشر"
        ),
        "what_to_do_ar": (
            actions["items"][0]["recommended_action_ar"]
            if actions.get("items")
            else "مراقبة روتينية"
        ),
        "did_recover_ar": (
            verification["items"][0]["recovered_ago_ar"]
            if verification.get("items")
            else "لا استعادة حديثة"
        ),
    }

    return {
        "version": "admin_operational_control_v2",
        "generated_at_utc": ctx.generated_at_utc,
        "admin_risk_summary": risk,
        "admin_impact_layer": impact,
        "admin_actions_layer": actions,
        "admin_verification_layer": verification,
        "admin_revenue_protection": revenue,
        "admin_operational_timeline": timeline,
        "quick_answers": quick_answers,
        # Legacy v1 diagnostics (collapsed section)
        "diagnostics_v1": {
            "cards": {
                "cart_event": ctx.cart,
                "db_pool": ctx.pool,
                "background_tasks": ctx.bg,
                "whatsapp": ctx.wa,
            },
            "warnings": ctx.warnings,
        },
    }


__all__ = [
    "build_admin_operational_control_readonly",
    "clear_verification_state_for_tests",
]
