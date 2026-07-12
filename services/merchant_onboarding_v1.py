# -*- coding: utf-8 -*-
"""
Merchant Onboarding v1 — guided first-success path (read-only, no duplicate truth).

State is **derived** from ``evaluate_onboarding_readiness`` + store fields only.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

log = logging.getLogger("cartflow")

TOTAL_GUIDED_STEPS = 5

# Internal state indices (for logs); merchants see 5 checklist steps.
STATE_ACCOUNT = 0
STATE_STORE = 1
STATE_WHATSAPP = 2
STATE_WIDGET = 3
STATE_TEST_READY = 4
STATE_PRODUCTION_READY = 5


@dataclass
class MerchantOnboardingStep:
    step_id: str
    order: int
    title_ar: str
    outcome_ar: str
    action_href: str
    is_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MerchantOnboardingFlow:
    """Guided onboarding payload for dashboard setup card + lazy JS."""

    show_card: bool = True
    onboarding_complete: bool = False
    first_recovery_ready: bool = False
    show_simplified_home: bool = True
    completed_steps: int = 0
    total_steps: int = TOTAL_GUIDED_STEPS
    current_step_ar: str = ""
    current_outcome_ar: str = ""
    action_href: str = "/dashboard#settings"
    card_title_ar: str = "ابدأ إعداد متجرك"
    card_lead_ar: str = ""
    celebration_message_ar: str = ""
    steps: list[MerchantOnboardingStep] = field(default_factory=list)
    state_index: int = STATE_ACCOUNT

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


_STEP_SPECS: list[dict[str, str]] = [
    {
        "id": "account",
        "title_ar": "إنشاء الحساب",
        "outcome_ar": "حسابك جاهز للوصول إلى لوحة التحكم",
        "action_href": "/dashboard",
    },
    {
        "id": "store",
        "title_ar": "ربط المتجر",
        "outcome_ar": "قراءة الطلبات والسلال",
        "action_href": "/dashboard#settings",
    },
    {
        "id": "whatsapp",
        "title_ar": "ربط واتساب",
        "outcome_ar": "بدء إرسال الرسائل",
        "action_href": "/dashboard#whatsapp",
    },
    {
        "id": "widget",
        "title_ar": "تفعيل الودجيت",
        "outcome_ar": "فهم أسباب التردد",
        "action_href": "/dashboard#widget",
    },
    {
        "id": "test_ready",
        "title_ar": "جاهز للاختبار",
        "outcome_ar": "إرسال أول رسالة تجريبية",
        "action_href": "__primary_dashboard__",
    },
]


def merchant_whatsapp_setup_complete(store: Optional[Any]) -> bool:
    """
    Merchant-facing WhatsApp setup step — persisted Store fields only.

    Matches PROD_WHATSAPP proof: saved number + recovery toggle enabled.
    Does not gate on Twilio/provider (that stays in readiness / send paths).
    """
    if store is None:
        return False
    num = (getattr(store, "store_whatsapp_number", None) or "").strip()
    wa_on = bool(getattr(store, "whatsapp_recovery_enabled", True))
    return bool(num and wa_on)


def log_onboarding_status(
    store: Optional[Any],
    *,
    merchant_user_id: Optional[int] = None,
    completed_steps: int = 0,
    total_steps: int = 0,
    widget_test_completed: bool = False,
    store_connected: bool = False,
    context: str = "dashboard",
) -> None:
    """Structured onboarding calculation log (read-only fields)."""
    slug = (getattr(store, "zid_store_id", None) or "").strip() if store else ""
    wa_present = merchant_whatsapp_setup_complete(store)
    whatsapp_step = merchant_whatsapp_setup_complete(store)
    line = (
        "[ONBOARDING STATUS] "
        f"context={context} "
        f"store_slug={slug or '-'} "
        f"store_id={getattr(store, 'id', None) or '-'} "
        f"merchant_user_id={merchant_user_id if merchant_user_id is not None else '-'} "
        f"store_whatsapp_number_present={str(wa_present).lower()} "
        f"whatsapp_recovery_enabled={str(bool(getattr(store, 'whatsapp_recovery_enabled', True) if store else False)).lower()} "
        f"widget_test_completed={str(widget_test_completed).lower()} "
        f"store_connected={str(store_connected).lower()} "
        f"whatsapp_step_complete={str(whatsapp_step).lower()} "
        f"completed_steps={completed_steps} "
        f"total_steps={total_steps}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def _step_is_complete(
    step_id: str,
    store: Optional[Any],
    ev: dict[str, Any],
    *,
    merchant_user_id: Optional[int] = None,
) -> bool:
    """Onboarding-only milestones — stricter than global ``evaluate_onboarding_readiness``."""
    flags = ev.get("flags") or {}
    milestones = ev.get("milestones") or {}

    if step_id == "account":
        if store is None or merchant_user_id is None:
            return False
        owner = getattr(store, "merchant_user_id", None)
        if owner is not None and int(owner) != int(merchant_user_id):
            return False
        return True

    if store is None:
        return False

    if step_id == "store":
        token_ok = bool((getattr(store, "access_token", None) or "").strip())
        recovery_on = bool(flags.get("recovery_enabled"))
        return token_ok and recovery_on

    if step_id == "whatsapp":
        return merchant_whatsapp_setup_complete(store)

    if step_id == "widget":
        return bool(flags.get("widget_installed"))

    if step_id == "test_ready":
        return bool(
            milestones.get("first_cart_detected")
            or milestones.get("first_whatsapp_sent")
            or milestones.get("first_recovery_scheduled")
        )

    return False


def _compute_state_index(steps: list[MerchantOnboardingStep]) -> int:
    if not steps:
        return STATE_ACCOUNT
    if not steps[0].is_complete:
        return STATE_ACCOUNT
    mapping = ["store", "whatsapp", "widget", "test_ready"]
    for i, sid in enumerate(mapping):
        idx = i + 1
        step = next((s for s in steps if s.step_id == sid), None)
        if step and not step.is_complete:
            return idx
    if all(s.is_complete for s in steps):
        return STATE_PRODUCTION_READY
    return STATE_TEST_READY


def build_merchant_onboarding_flow(
    store: Optional[Any] = None,
    *,
    merchant_user_id: Optional[int] = None,
    emit_logs: bool = True,
) -> MerchantOnboardingFlow:
    ev = evaluate_onboarding_readiness(store) if store is not None else {
        "ready": False,
        "flags": {},
        "milestones": {},
    }
    steps_out: list[MerchantOnboardingStep] = []
    from services.cart_workspace.feature_flag_v1 import (  # noqa: PLC0415
        cart_workspace_primary_dashboard_path,
    )

    primary = cart_workspace_primary_dashboard_path()
    for i, spec in enumerate(_STEP_SPECS, start=1):
        sid = spec["id"]
        href = spec["action_href"]
        if href == "__primary_dashboard__":
            href = primary
        steps_out.append(
            MerchantOnboardingStep(
                step_id=sid,
                order=i,
                title_ar=spec["title_ar"],
                outcome_ar=spec["outcome_ar"],
                action_href=href,
                is_complete=_step_is_complete(
                    sid, store, ev, merchant_user_id=merchant_user_id
                ),
            )
        )

    completed = sum(1 for s in steps_out if s.is_complete)
    incomplete = [s for s in steps_out if not s.is_complete]
    state_index = _compute_state_index(steps_out)

    first_recovery_ready = completed >= TOTAL_GUIDED_STEPS
    onboarding_complete = first_recovery_ready

    if incomplete:
        current = incomplete[0]
        current_step_ar = current.title_ar
        current_outcome_ar = current.outcome_ar
        action_href = current.action_href
    else:
        current_step_ar = ""
        current_outcome_ar = ""
        action_href = cart_workspace_primary_dashboard_path()

    if onboarding_complete:
        card_title = "🎉 متجرك جاهز"
        card_lead = "يمكن لـ CartFlow الآن البدء بمتابعة السلال."
        celebration = card_lead
        show_card = True
        show_simplified = False
    else:
        card_title = "إعداد متجرك"
        card_lead = "أكمل الخطوات التالية للوصول إلى أول جاهزية للاسترجاع."
        celebration = ""
        show_card = True
        show_simplified = True

    if emit_logs:
        log.info(
            "[MERCHANT ONBOARDING] completed=%s/%s state=%s ready=%s store_present=%s",
            completed,
            TOTAL_GUIDED_STEPS,
            state_index,
            first_recovery_ready,
            store is not None,
        )

    return MerchantOnboardingFlow(
        show_card=show_card,
        onboarding_complete=onboarding_complete,
        first_recovery_ready=first_recovery_ready,
        show_simplified_home=show_simplified,
        completed_steps=completed,
        total_steps=TOTAL_GUIDED_STEPS,
        current_step_ar=current_step_ar,
        current_outcome_ar=current_outcome_ar,
        action_href=action_href,
        card_title_ar=card_title,
        card_lead_ar=card_lead,
        celebration_message_ar=celebration,
        steps=steps_out,
        state_index=state_index,
    )


__all__ = [
    "MerchantOnboardingFlow",
    "MerchantOnboardingStep",
    "TOTAL_GUIDED_STEPS",
    "build_merchant_onboarding_flow",
    "log_onboarding_status",
    "merchant_whatsapp_setup_complete",
]
