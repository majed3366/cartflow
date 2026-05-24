# -*- coding: utf-8 -*-
"""
Adaptive merchant dashboard home layout (read-only).

Stages: activation (new) → activated (operational) → production (history/revenue).
Does not touch recovery, WhatsApp, widget, or scheduler behavior.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.cartflow_onboarding_readiness import (
    BLOCKER_COPY,
    evaluate_onboarding_readiness,
)

HOME_STAGE_ACTIVATION = "activation"
HOME_STAGE_ACTIVATED = "activated"
HOME_STAGE_PRODUCTION = "production"

ACTIVATION_DISPLAY_PROMINENT = "prominent"
ACTIVATION_DISPLAY_COMPACT = "compact"
ACTIVATION_DISPLAY_HIDDEN = "hidden"


@dataclass
class MerchantHomeLayout:
    home_stage: str = HOME_STAGE_ACTIVATION
    activation_display: str = ACTIVATION_DISPLAY_PROMINENT
    hide_setup_card: bool = False
    operational_alerts_ar: list[str] = field(default_factory=list)
    activation_summary_lines_ar: list[str] = field(default_factory=list)
    last_activity_ar: str = ""
    setup_collapsed_default: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _any_activation_milestone(
    *,
    first_cart: bool,
    first_reason: bool,
    first_scheduled: bool,
    first_sent: bool,
) -> bool:
    return bool(first_cart or first_reason or first_scheduled or first_sent)


def production_signal_reasons(
    *,
    first_recovered: bool = False,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> list[str]:
    """
    Reasons that classify a merchant as production (mature) for home layout.

    Requires recovery outcome or revenue — not first send + abandoned volume alone.
    """
    reasons: list[str] = []
    if first_recovered:
        reasons.append("first_recovered")
    if int(month_recovered) > 0:
        reasons.append("month_recovered_gt_0")
    if float(month_revenue) > 0.0:
        reasons.append("month_revenue_gt_0")
    return reasons


def has_production_signal(
    *,
    first_recovered: bool = False,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> bool:
    return bool(
        production_signal_reasons(
            first_recovered=first_recovered,
            month_recovered=month_recovered,
            month_revenue=month_revenue,
        )
    )


def _operational_alerts_from_readiness(ev: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for code in list(ev.get("blocking_steps") or []) + list(ev.get("soft_notes") or []):
        if code in seen:
            continue
        meta = BLOCKER_COPY.get(code) or {}
        title = (meta.get("title_ar") or "").strip()
        action = (meta.get("action_ar") or "").strip()
        if not title:
            continue
        seen.add(code)
        line = title if not action else f"{title} — {action}"
        out.append(line[:240])
        if len(out) >= 4:
            break
    return out


def resolve_merchant_home_layout(
    store: Optional[Any],
    *,
    onboarding_complete: bool = False,
    first_cart: bool = False,
    first_reason: bool = False,
    first_scheduled: bool = False,
    first_sent: bool = False,
    first_recovered: bool = False,
    activation_working: bool = False,
    current_state_label_ar: str = "",
    month_abandoned: int = 0,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> MerchantHomeLayout:
    ev = evaluate_onboarding_readiness(store) if store is not None else {}
    alerts = _operational_alerts_from_readiness(ev)

    any_ms = _any_activation_milestone(
        first_cart=first_cart,
        first_reason=first_reason,
        first_scheduled=first_scheduled,
        first_sent=first_sent,
    )

    mature = has_production_signal(
        first_recovered=first_recovered,
        month_recovered=month_recovered,
        month_revenue=month_revenue,
    )

    state_a = bool(
        not onboarding_complete or not first_cart or not any_ms
    )

    summary_lines: list[str] = []
    if onboarding_complete:
        summary_lines.append("✓ التفعيل مكتمل")
    elif any_ms:
        summary_lines.append("◯ إعداد التفعيل قيد الإكمال")
    if first_sent:
        summary_lines.append("✓ أول رسالة أُرسلت")
    elif first_scheduled:
        summary_lines.append("✓ الاسترجاع مُجدول")
    elif first_cart:
        summary_lines.append("✓ أول سلة مُسجَّلة")

    last_activity = (current_state_label_ar or "").strip() or "—"

    if mature and not state_a:
        return MerchantHomeLayout(
            home_stage=HOME_STAGE_PRODUCTION,
            activation_display=ACTIVATION_DISPLAY_HIDDEN,
            hide_setup_card=True,
            operational_alerts_ar=alerts,
            activation_summary_lines_ar=summary_lines,
            last_activity_ar=last_activity,
            setup_collapsed_default=True,
        )

    merchant_active = bool(
        activation_working or first_sent or first_scheduled or first_cart
    )
    if (
        not state_a
        and onboarding_complete
        and merchant_active
    ):
        return MerchantHomeLayout(
            home_stage=HOME_STAGE_ACTIVATED,
            activation_display=ACTIVATION_DISPLAY_COMPACT,
            hide_setup_card=True,
            operational_alerts_ar=alerts,
            activation_summary_lines_ar=summary_lines,
            last_activity_ar=last_activity,
            setup_collapsed_default=True,
        )

    return MerchantHomeLayout(
        home_stage=HOME_STAGE_ACTIVATION,
        activation_display=ACTIVATION_DISPLAY_PROMINENT,
        hide_setup_card=False,
        operational_alerts_ar=alerts,
        activation_summary_lines_ar=summary_lines,
        last_activity_ar=last_activity,
        setup_collapsed_default=False,
    )


__all__ = [
    "HOME_STAGE_ACTIVATED",
    "HOME_STAGE_ACTIVATION",
    "HOME_STAGE_PRODUCTION",
    "ACTIVATION_DISPLAY_COMPACT",
    "ACTIVATION_DISPLAY_HIDDEN",
    "ACTIVATION_DISPLAY_PROMINENT",
    "MerchantHomeLayout",
    "has_production_signal",
    "production_signal_reasons",
    "resolve_merchant_home_layout",
]
