# -*- coding: utf-8 -*-
"""
Merchant Setup Experience v1 — merchant-safe setup progression (no ops jargon).

Translates production readiness path into: progress, remaining setup count,
ordered steps, and expected outcomes. Admin operational cards unchanged.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.merchant_onboarding_reality_v1 import (
    LEVEL_NOT_STARTED,
    LEVEL_PARTIAL,
    LEVEL_PRODUCTION_READY,
    LEVEL_SANDBOX_ONLY,
)
from services.merchant_production_readiness_path_v1 import (
    build_merchant_production_readiness_path,
)

log = logging.getLogger("cartflow")

SETUP_STATE_NOT_READY = "غير جاهز"
SETUP_STATE_NEAR = "قريب من التشغيل"
SETUP_STATE_READY = "جاهز"
SETUP_STATE_FULL = "تشغيل كامل"

_FORBIDDEN_MERCHANT_TERMS = re.compile(
    r"callback|status_callback|twilio|provider|ownership|"
    r"risk|effort|cartflow_ops|platform|queued|delivery_truth|"
    r"production_ready|sandbox_only|partial|not_started",
    re.I,
)

# Merchant-facing step catalog (covers internal path codes).
_MERCHANT_STEP_DEFS: list[dict[str, Any]] = [
    {
        "id": "store_basics",
        "order": 1,
        "title_ar": "ربط المتجر وتفعيل الاسترجاع",
        "outcome_ar": "يُسجَّل المتجر وتبدأ متابعة السلال المهجورة",
        "action_href": "/dashboard#settings",
        "complete_action_ar": "أكملت هذا الإعداد",
        "codes": frozenset(
            {
                "dashboard_init",
                "store_not_connected",
                "store_connected",
                "widget_not_installed",
                "widget_enabled",
                "recovery_disabled",
                "recovery_enabled",
                "recovery_delays",
                "store_whatsapp_number",
                "templates_not_configured",
                "templates_local",
                "template_routing",
            }
        ),
    },
    {
        "id": "connect_whatsapp",
        "order": 2,
        "title_ar": "ربط واتساب الإنتاج",
        "outcome_ar": "ستُرسل رسائل الاسترجاع للعملاء عبر واتساب",
        "action_href": "/dashboard#whatsapp",
        "complete_action_ar": "أكملت ربط واتساب",
        "codes": frozenset(
            {
                "production_provider",
                "production_mode_off_or_twilio_missing",
                "provider_not_connected",
            }
        ),
    },
    {
        "id": "approve_messages",
        "order": 3,
        "title_ar": "اعتماد الرسائل",
        "outcome_ar": "تُقبل رسائل الاسترجاع خارج وقت المحادثة مع العميل",
        "action_href": "/dashboard#whatsapp",
        "complete_action_ar": "أكملت اعتماد الرسائل",
        "codes": frozenset(
            {
                "templates_approved",
                "templates_not_provider_approved",
            }
        ),
    },
    {
        "id": "test_send",
        "order": 4,
        "title_ar": "اختبار الإرسال",
        "outcome_ar": "تتأكد أن رسالة تجريبية وصلت لعميلك بنجاح",
        "action_href": "/dashboard#carts",
        "complete_action_ar": "أكملت الاختبار",
        "codes": frozenset(
            {
                "delivery_truth",
                "delivery_truth_callback",
            }
        ),
    },
]


@dataclass
class MerchantSetupStep:
    step_id: str
    order: int
    title_ar: str
    outcome_ar: str
    action_href: str
    complete_action_ar: str
    is_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MerchantSetupExperience:
    show_card: bool = True
    card_title_ar: str = "متجرك قريب من التشغيل الكامل"
    setup_state_label_ar: str = SETUP_STATE_NEAR
    readiness_percent: int = 0
    remaining_setup_count: int = 0
    outcome_summary_ar: str = ""
    next_step_ar: str = ""
    action_href: str = "/dashboard#whatsapp"
    steps: list[MerchantSetupStep] = field(default_factory=list)
    merchant_understands_in_30s: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


def _setup_state_label(percent: int, onboarding_state: str) -> str:
    if onboarding_state == LEVEL_PRODUCTION_READY or percent >= 100:
        return SETUP_STATE_FULL
    if percent >= 67:
        return SETUP_STATE_READY
    if percent >= 25:
        return SETUP_STATE_NEAR
    return SETUP_STATE_NOT_READY


def _card_title(onboarding_state: str, percent: int) -> str:
    if onboarding_state == LEVEL_PRODUCTION_READY or percent >= 100:
        return "متجرك يعمل بالكامل"
    return "متجرك قريب من التشغيل الكامل"


def _default_outcome_summary(onboarding_state: str) -> str:
    if onboarding_state == LEVEL_PRODUCTION_READY:
        return "رسائل الاسترجاع تصل للعملاء وتُتابع من لوحة التحكم"
    return "ستبدأ رسائل الاسترجاع بالوصول للعملاء"


def _build_merchant_steps(missing_codes: set[str]) -> list[MerchantSetupStep]:
    steps_out: list[MerchantSetupStep] = []
    prior_complete = True
    for spec in sorted(_MERCHANT_STEP_DEFS, key=lambda x: int(x["order"])):
        codes = set(spec["codes"])
        blocking = codes & missing_codes
        is_complete = prior_complete and len(blocking) == 0
        if not is_complete:
            prior_complete = False
        steps_out.append(
            MerchantSetupStep(
                step_id=str(spec["id"]),
                order=int(spec["order"]),
                title_ar=str(spec["title_ar"]),
                outcome_ar=str(spec["outcome_ar"]),
                action_href=str(spec["action_href"]),
                complete_action_ar=str(spec["complete_action_ar"]),
                is_complete=is_complete,
            )
        )
    return steps_out


def _visible_setup_steps(steps: list[MerchantSetupStep]) -> list[MerchantSetupStep]:
    """After store basics, surface the three WhatsApp setup steps merchants expect."""
    if not steps:
        return []
    if steps[0].is_complete:
        return steps[1:]
    return steps


def _merchant_progress_percent(
    steps: list[MerchantSetupStep],
    onboarding_state: str,
    path_score: int,
) -> int:
    if onboarding_state == LEVEL_PRODUCTION_READY:
        return 100
    if not steps:
        return 0
    if not steps[0].is_complete:
        return 0
    wa_steps = steps[1:]
    if not wa_steps:
        return min(100, max(0, int(path_score)))
    done = sum(1 for s in wa_steps if s.is_complete)
    ladder = {0: 0, 1: 33, 2: 66, 3: 100}
    return ladder.get(done, min(100, int(path_score)))


def _sanitize_merchant_text(text: str) -> str:
    t = (text or "").strip()
    replacements = {
        "delivery_truth_callback": "متابعة وصول الرسائل",
        "delivery_truth": "متابعة وصول الرسائل",
        "provider_not_connected": "ربط واتساب الإنتاج",
        "production_mode_off_or_twilio_missing": "تفعيل واتساب الإنتاج",
        "templates_not_provider_approved": "اعتماد الرسائل",
        "Twilio": "واتساب",
        "callback": "",
    }
    for old, new in replacements.items():
        t = t.replace(old, new)
    return " ".join(t.split())


def build_merchant_setup_experience(
    store: Optional[Any] = None,
    *,
    merchant_user_id: Optional[int] = None,
    emit_logs: bool = True,
) -> MerchantSetupExperience:
    from services.merchant_setup_unified_p0 import (
        build_merchant_setup_unified_p0,
        unified_to_setup_experience,
    )

    unified = build_merchant_setup_unified_p0(
        store,
        merchant_user_id=merchant_user_id,
        emit_logs=emit_logs,
    )
    return unified_to_setup_experience(unified)


def merchant_copy_is_safe_for_display(experience: MerchantSetupExperience) -> bool:
    """True when no forbidden jargon appears in merchant-visible strings."""
    blob = " ".join(
        [
            experience.card_title_ar,
            experience.outcome_summary_ar,
            experience.next_step_ar,
            experience.setup_state_label_ar,
        ]
        + [s.title_ar + " " + s.outcome_ar for s in experience.steps]
    )
    return _FORBIDDEN_MERCHANT_TERMS.search(blob) is None


def build_merchant_setup_experience_api_payload(
    store: Optional[Any] = None,
    *,
    cookies: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    from services.merchant_onboarding_store import (
        log_onboarding_flow_result,
        resolve_merchant_onboarding_store,
    )
    from services.merchant_onboarding_v1 import build_merchant_onboarding_flow

    owned_store, resolution = resolve_merchant_onboarding_store(cookies=cookies)
    if store is not None and owned_store is None:
        pass
    elif owned_store is not None:
        store = owned_store

    mid = resolution.merchant_id
    from services.merchant_setup_unified_p0 import (  # noqa: PLC0415
        build_merchant_setup_unified_p0,
        unified_api_payload,
    )

    unified = build_merchant_setup_unified_p0(
        store,
        merchant_user_id=mid,
        emit_logs=False,
    )
    flow = build_merchant_onboarding_flow(
        store,
        merchant_user_id=mid,
        emit_logs=False,
    )
    log_onboarding_flow_result(
        resolution,
        ready=unified.onboarding_complete,
        completed_steps=unified.completed_steps,
    )
    out = unified_api_payload(unified, flow_dict=flow.to_dict())
    out["merchant_store_display_name"] = resolution.store_name or "متجرك"
    return out
