# -*- coding: utf-8 -*-
"""
Shipping mission execution path — reachability only.

CartFlow must not recommend an action the merchant cannot execute or reach.
Does not change CDC: accept remains decision accepted, not execution started.
"""
from __future__ import annotations

from services.merchant_widget_panel import _WIDGET_FIXED_HESITATION_LABEL_AR
from services.store_reason_templates import _REASON_TAGS

FAMILY_SHIPPING = "shipping_friction"

# Platform-authoritative hesitation keys (not merchant-created).
REASON_SHIPPING_COST = "shipping"
REASON_DELIVERY_DURATION = "delivery"

EXECUTION_CTA_AR = "اضبط أسباب التردد"
EXECUTION_HINT_AR = (
    "راجع سببي «الشحن» و«مدة التوصيل» — فعّلهما منفصلين حتى يفرّق العميل "
    "بين تكلفة الشحن ومدة التوصيل."
)
# UI location only — never tenant/security authority.
SETTINGS_EXECUTION_HASH = (
    "#settings?area=recovery&focus=shipping-hesitation"
)
SETTINGS_SURFACE_AR = "الإعدادات → سياسة الاسترجاع → أسباب التردد"


def platform_has_shipping_cost_reason() -> bool:
    return REASON_SHIPPING_COST in _REASON_TAGS and REASON_SHIPPING_COST in (
        _WIDGET_FIXED_HESITATION_LABEL_AR
    )


def platform_has_delivery_duration_reason() -> bool:
    return REASON_DELIVERY_DURATION in _REASON_TAGS and REASON_DELIVERY_DURATION in (
        _WIDGET_FIXED_HESITATION_LABEL_AR
    )


def shipping_distinction_executable_v1() -> dict[str, object]:
    """Authoritative reachability for the R17 shipping distinction action."""
    cost = platform_has_shipping_cost_reason()
    duration = platform_has_delivery_duration_reason()
    executable = bool(cost and duration)
    return {
        "shipping_cost_reason_exists": cost,
        "delivery_duration_reason_exists": duration,
        "merchant_can_enable_each": executable,
        "merchant_can_edit_recovery_wording": executable,
        "merchant_can_configure_stages": executable,
        "merchant_can_add_or_delete_reasons": False,
        "action_executable": executable,
        "cta_ar": EXECUTION_CTA_AR if executable else "",
        "destination_hash": SETTINGS_EXECUTION_HASH if executable else "",
        "destination_surface_ar": SETTINGS_SURFACE_AR if executable else "",
        "unavailable_ar": "" if executable else "ACTION CURRENTLY NOT EXECUTABLE",
    }


def execution_control_for_family_v1(family: str) -> dict[str, object] | None:
    if str(family or "").strip() != FAMILY_SHIPPING:
        return None
    return shipping_distinction_executable_v1()


__all__ = [
    "EXECUTION_CTA_AR",
    "EXECUTION_HINT_AR",
    "FAMILY_SHIPPING",
    "REASON_DELIVERY_DURATION",
    "REASON_SHIPPING_COST",
    "SETTINGS_EXECUTION_HASH",
    "SETTINGS_SURFACE_AR",
    "execution_control_for_family_v1",
    "shipping_distinction_executable_v1",
]
