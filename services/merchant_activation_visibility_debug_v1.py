# -*- coding: utf-8 -*-
"""
Temporary debug payload for dashboard home activation visibility (read-only).

Does not change recovery, WhatsApp, widget, or stage resolution behavior.
"""
from __future__ import annotations

from typing import Any, Optional

from services.merchant_dashboard_home_stage_v1 import (
    ACTIVATION_DISPLAY_HIDDEN,
    MerchantHomeLayout,
    _any_activation_milestone,
    production_signal_reasons,
)


def build_activation_visibility_debug(
    layout: MerchantHomeLayout,
    *,
    store_slug: str = "",
    onboarding_complete: bool = False,
    first_cart: bool = False,
    first_reason: bool = False,
    first_scheduled: bool = False,
    first_sent: bool = False,
    first_recovered: bool = False,
    activation_working: bool = False,
    month_abandoned: int = 0,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> dict[str, Any]:
    any_ms = _any_activation_milestone(
        first_cart=first_cart,
        first_reason=first_reason,
        first_scheduled=first_scheduled,
        first_sent=first_sent,
    )
    prod_reasons = production_signal_reasons(
        first_recovered=first_recovered,
        month_recovered=month_recovered,
        month_revenue=month_revenue,
    )
    has_production_signal = bool(prod_reasons)
    state_a = bool(not onboarding_complete or not first_cart or not any_ms)
    merchant_active = bool(
        activation_working or first_sent or first_scheduled or first_cart
    )

    display = layout.activation_display
    if display == ACTIVATION_DISPLAY_HIDDEN:
        verdict_primary = "B"
        verdict_note = (
            "Server resolved production: activation_display=hidden. "
            "JS should show compact strip only when #page-home.active at apply time."
        )
        ui_blocker_server = "stage_production_hidden"
    elif state_a:
        verdict_primary = "B"
        verdict_note = (
            "New merchant path: activation_display should be prominent unless "
            "layout resolver returned something else."
        )
        ui_blocker_server = "stage_activation_or_incomplete"
    else:
        verdict_primary = "B"
        verdict_note = (
            f"Server home_stage={layout.home_stage}, "
            f"activation_display={display}."
        )
        ui_blocker_server = "stage_activated_compact_or_prominent"

    return {
        "verdict_primary": verdict_primary,
        "verdict_note": verdict_note,
        "ui_blocker_server": ui_blocker_server,
        "css_hidden_attr_blocks_show_rule": True,
        "home_stage": layout.home_stage,
        "activation_display": layout.activation_display,
        "hide_setup_card": bool(layout.hide_setup_card),
        "store_slug": store_slug,
        "state_a_new_or_incomplete": state_a,
        "onboarding_complete": onboarding_complete,
        "any_activation_milestone": any_ms,
        "merchant_active": merchant_active,
        "has_production_signal": has_production_signal,
        "production_signal_reasons": prod_reasons,
        "milestones": {
            "first_cart_detected": first_cart,
            "first_reason_captured": first_reason,
            "first_recovery_scheduled": first_scheduled,
            "first_whatsapp_sent": first_sent,
            "first_recovered_cart": first_recovered,
        },
        "month_window": {
            "abandoned_total": int(month_abandoned),
            "recovered_total": int(month_recovered),
            "recovered_revenue": float(month_revenue or 0.0),
        },
        "activation_working": activation_working,
        "client_expectation": {
            "when_page_home_active": (
                "compact"
                if display == ACTIVATION_DISPLAY_HIDDEN
                else display
            ),
            "when_page_home_not_active_at_apply": (
                "root stays hidden if activation_display=hidden"
            ),
        },
        "likely_missing_ui_causes": [
            "js_apply_while_not_on_home_then_navigate_home",
            "server_activation_display_hidden_and_early_return",
            "missing_or_invalid_merchant_activation_in_summary",
            "css_ma_activation_root_hidden_attr",
        ],
    }


__all__ = ["build_activation_visibility_debug"]
