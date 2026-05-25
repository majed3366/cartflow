# -*- coding: utf-8 -*-
"""
Merchant Setup Unified P0 — one guided path from existing evaluators only.

Does not change recovery, WhatsApp send, truth, or queue behavior.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness
from services.merchant_activation_v1 import (
    build_merchant_activation_payload,
    merchant_activation_test_store_url,
)
from services.merchant_onboarding_v1 import (
    _step_is_complete as onboarding_step_complete,
)
from services.merchant_setup_experience_v1 import (
    SETUP_STATE_FULL,
    SETUP_STATE_NEAR,
    SETUP_STATE_NOT_READY,
    SETUP_STATE_READY,
    MerchantSetupExperience,
    MerchantSetupStep,
)

log = logging.getLogger("cartflow")

PHASE_SANDBOX = "sandbox"
PHASE_PRODUCTION = "production"

SANDBOX_ACCOUNT = "sandbox_account"
SANDBOX_TEST_WIDGET = "sandbox_test_widget"
SANDBOX_FIRST_RECOVERY = "sandbox_first_recovery"
SANDBOX_VIEW_CARTS = "sandbox_view_carts"
SANDBOX_VERIFIED = "sandbox_verified"

PROD_OAUTH = "prod_oauth"
PROD_WHATSAPP = "prod_whatsapp"
PROD_TEMPLATES = "prod_templates"
PROD_LIVE_WIDGET = "prod_live_widget"


@dataclass
class UnifiedSetupStep:
    step_id: str
    order: int
    phase: str
    title_ar: str
    outcome_ar: str
    proof_ar: str
    action_href: str
    action_label_ar: str
    is_complete: bool = False
    is_current: bool = False
    locked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MerchantSetupUnifiedP0:
    unified_p0: bool = True
    setup_mode: bool = True
    sandbox_verified: bool = False
    production_unlocked: bool = False
    card_title_ar: str = "متجرك قريب من التشغيل الكامل"
    card_lead_ar: str = ""
    current_step_ar: str = ""
    current_outcome_ar: str = ""
    proof_ar: str = ""
    next_step_ar: str = ""
    action_href: str = "/dashboard/test-widget"
    action_label_ar: str = "انتقل للخطوة"
    delay_hint_ar: str = ""
    test_store_url: str = "/dashboard/test-widget"
    readiness_percent: int = 0
    completed_steps: int = 0
    total_steps: int = 0
    remaining_setup_count: int = 0
    setup_state_label_ar: str = SETUP_STATE_NEAR
    show_card: bool = True
    onboarding_complete: bool = False
    first_recovery_ready: bool = False
    celebration_message_ar: str = ""
    steps: list[UnifiedSetupStep] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


def _sandbox_flags(
    store: Optional[Any],
    ev: dict[str, Any],
    *,
    merchant_user_id: Optional[int] = None,
) -> dict[str, bool]:
    ms = dict(ev.get("milestones") or {})
    account_ok = store is not None
    if account_ok and merchant_user_id is not None:
        owner = getattr(store, "merchant_user_id", None)
        if owner is not None and int(owner) != int(merchant_user_id):
            account_ok = False
    first_cart = bool(ms.get("first_cart_detected"))
    first_scheduled = bool(ms.get("first_recovery_scheduled"))
    first_sent = bool(ms.get("first_whatsapp_sent"))
    first_reason = False
    if store is not None:
        try:
            from services.merchant_activation_v1 import (  # noqa: PLC0415
                _first_reason_captured_readonly,
            )

            first_reason = _first_reason_captured_readonly(store)
        except Exception:  # noqa: BLE001
            pass
    recovery_started = first_scheduled or first_sent
    view_ok = first_sent
    verified = first_sent
    return {
        "account": account_ok,
        "test_widget": first_cart,
        "first_recovery": recovery_started,
        "view_carts": view_ok,
        "sandbox_verified": verified,
        "first_reason": first_reason,
    }


def _production_flags(
    store: Optional[Any],
    ev: dict[str, Any],
    *,
    merchant_user_id: Optional[int] = None,
) -> dict[str, bool]:
    flags = dict(ev.get("flags") or {})
    templates_ok = bool(flags.get("templates_local"))
    if not templates_ok and store is not None:
        raw = (getattr(store, "reason_templates_json", None) or "").strip()
        templates_ok = len(raw) > 2
    token_ok = bool(
        store is not None and (getattr(store, "access_token", None) or "").strip()
    )
    return {
        "oauth": token_ok,
        "whatsapp": onboarding_step_complete(
            "whatsapp", store, ev, merchant_user_id=merchant_user_id
        ),
        "templates": templates_ok,
        "live_widget": onboarding_step_complete(
            "widget", store, ev, merchant_user_id=merchant_user_id
        ),
    }


def _build_step_list(
    *,
    sandbox: dict[str, bool],
    production: dict[str, bool],
    slug: str,
    delay_hint: str,
) -> list[UnifiedSetupStep]:
    test_url = (
        merchant_activation_test_store_url(slug)
        if slug
        else "/dashboard/test-widget"
    )
    sandbox_specs: list[dict[str, Any]] = [
        {
            "id": SANDBOX_ACCOUNT,
            "order": 1,
            "title_ar": "الحساب",
            "outcome_ar": "حسابك جاهز للوصول إلى لوحة التحكم",
            "proof_ar": "تم إنشاء المتجر وتسجيل الدخول.",
            "action_href": "/dashboard",
            "action_label_ar": "الرئيسية",
            "done": sandbox["account"],
        },
        {
            "id": SANDBOX_TEST_WIDGET,
            "order": 2,
            "title_ar": "تجربة الودجيت (إثبات التجربة)",
            "outcome_ar": "تسجّل أول سلة من متجر الاختبار",
            "proof_ar": "تظهر سلة في قائمة السلال بعد التجربة.",
            "action_href": test_url,
            "action_label_ar": "فتح متجر الاختبار",
            "done": sandbox["test_widget"],
        },
        {
            "id": SANDBOX_FIRST_RECOVERY,
            "order": 3,
            "title_ar": "اختبار أول استرجاع",
            "outcome_ar": "جدولة وإرسال أول رسالة تجريبية",
            "proof_ar": "حالة «تم إرسال رسالة» أو جدولة في السلة.",
            "action_href": test_url,
            "action_label_ar": "متابعة التجربة",
            "done": sandbox["first_recovery"],
        },
        {
            "id": SANDBOX_VIEW_CARTS,
            "order": 4,
            "title_ar": "عرض السلال والشرح",
            "outcome_ar": "افهم الفرق بين «إرسال رسالة» و«تم استردادها»",
            "proof_ar": "الرسالة التجريبية لا تعني شراءاً فورياً — الاسترداد يظهر عند شراء حقيقي.",
            "action_href": "/dashboard#carts",
            "action_label_ar": "عرض السلال",
            "done": sandbox["view_carts"],
        },
        {
            "id": SANDBOX_VERIFIED,
            "order": 5,
            "title_ar": "تجربة التشغيل مُثبتة",
            "outcome_ar": "إثبات التجربة مكتمل — جاهز لإعداد الإنتاج",
            "proof_ar": "أول رسالة استرجاع تجريبية سُجّلت بنجاح.",
            "action_href": "/dashboard#carts",
            "action_label_ar": "مراجعة الإثبات",
            "done": sandbox["sandbox_verified"],
        },
    ]
    prod_unlocked = sandbox["sandbox_verified"]
    prod_specs: list[dict[str, Any]] = [
        {
            "id": PROD_OAUTH,
            "order": 6,
            "title_ar": "ربط متجر زد (OAuth)",
            "outcome_ar": "مزامنة الطلبات مع منصة زد",
            "proof_ar": "يظهر «متجر مربوط» في إعدادات الحساب.",
            "action_href": "/dashboard#settings",
            "action_label_ar": "ربط المتجر",
            "done": production["oauth"],
        },
        {
            "id": PROD_WHATSAPP,
            "order": 7,
            "title_ar": "إعداد واتساب",
            "outcome_ar": "رقم المتجر وتفعيل الاسترجاع عبر واتساب",
            "proof_ar": "رقم واتساب محفوظ والاسترجاع مفعّل في الإعدادات.",
            "action_href": "/dashboard#whatsapp",
            "action_label_ar": "إعداد واتساب",
            "done": production["whatsapp"],
        },
        {
            "id": PROD_TEMPLATES,
            "order": 8,
            "title_ar": "قوالب الرسائل",
            "outcome_ar": "نصوص أسباب التردد جاهزة للإرسال",
            "proof_ar": "قوالب غير فارغة — لا يُتخطى الإرسال لسبب قالب.",
            "action_href": "/dashboard#whatsapp",
            "action_label_ar": "تحرير القوالب",
            "done": production["templates"],
        },
        {
            "id": PROD_LIVE_WIDGET,
            "order": 9,
            "title_ar": "الودجيت على متجرك الحقيقي",
            "outcome_ar": "لصق الشيفرة في قالب زد أو موقعك",
            "proof_ar": "الودجيت مُثبت على واجهة المتجر الفعلية.",
            "action_href": "/dashboard#widget",
            "action_label_ar": "إعداد الودجيت",
            "done": production["live_widget"],
        },
    ]

    steps: list[UnifiedSetupStep] = []
    current_assigned = False

    def _append(spec: dict[str, Any], *, phase: str, locked: bool) -> None:
        nonlocal current_assigned
        done = bool(spec["done"]) if not locked else False
        is_current = not current_assigned and not locked and not done
        if is_current:
            current_assigned = True
        steps.append(
            UnifiedSetupStep(
                step_id=str(spec["id"]),
                order=int(spec["order"]),
                phase=phase,
                title_ar=str(spec["title_ar"]),
                outcome_ar=str(spec["outcome_ar"]),
                proof_ar=str(spec["proof_ar"]),
                action_href=str(spec["action_href"]),
                action_label_ar=str(spec["action_label_ar"]),
                is_complete=bool(spec["done"]) if not locked else False,
                is_current=is_current,
                locked=locked,
            )
        )

    for spec in sandbox_specs:
        _append(spec, phase=PHASE_SANDBOX, locked=False)
    for spec in prod_specs:
        _append(spec, phase=PHASE_PRODUCTION, locked=not prod_unlocked)
    return steps


def build_merchant_setup_unified_p0(
    store: Optional[Any] = None,
    *,
    merchant_user_id: Optional[int] = None,
    cookies: Optional[dict[str, str]] = None,
    emit_logs: bool = True,
) -> MerchantSetupUnifiedP0:
    ev = evaluate_onboarding_readiness(store) if store is not None else {}
    slug = (getattr(store, "zid_store_id", None) or "").strip() if store else ""
    act = build_merchant_activation_payload(store, cookies=cookies)
    sandbox = _sandbox_flags(store, ev, merchant_user_id=merchant_user_id)
    production = _production_flags(
        store, ev, merchant_user_id=merchant_user_id
    )
    steps = _build_step_list(
        sandbox=sandbox,
        production=production,
        slug=slug,
        delay_hint=act.delay_hint_ar,
    )

    visible = [s for s in steps if not s.locked or s.phase == PHASE_SANDBOX]
    sandbox_steps = [s for s in steps if s.phase == PHASE_SANDBOX]
    prod_steps = [s for s in steps if s.phase == PHASE_PRODUCTION]
    sandbox_done = sum(1 for s in sandbox_steps if s.is_complete)
    prod_done = sum(1 for s in prod_steps if s.is_complete) if sandbox["sandbox_verified"] else 0

    total_track = len(sandbox_steps) + (
        len(prod_steps) if sandbox["sandbox_verified"] else 0
    )
    completed_track = sandbox_done + prod_done
    percent = (
        int(round(100.0 * completed_track / total_track)) if total_track else 0
    )

    current = next((s for s in steps if s.is_current), None)
    if current is None:
        incomplete = [s for s in visible if not s.is_complete and not s.locked]
        current = incomplete[0] if incomplete else None

    sandbox_verified = sandbox["sandbox_verified"]
    prod_complete = sandbox_verified and all(
        production[k] for k in ("oauth", "whatsapp", "templates", "live_widget")
    )
    setup_mode = not sandbox_verified or not prod_complete

    if prod_complete:
        title = "متجرك يعمل بالكامل"
        state_label = SETUP_STATE_FULL
        lead = "يمكنك متابعة السلال والرسائل من لوحة التحكم اليومية."
        celebration = lead
    elif sandbox_verified:
        title = "متجرك قريب من التشغيل الكامل"
        state_label = SETUP_STATE_READY
        lead = "أكمل إعداد الإنتاج — الخطوات أدناه مفعّلة الآن."
        celebration = "✅ تجربة التشغيل مُثبتة — يمكنك إكمال إعداد الإنتاج."
    else:
        title = "متجرك قريب من التشغيل الكامل"
        state_label = SETUP_STATE_NEAR if sandbox_done else SETUP_STATE_NOT_READY
        lead = "اتبع الخطوة التالية بالترتيب — إعداد الإنتاج يُفتح بعد إثبات التجربة."
        celebration = ""

    next_ar = act.next_step_ar or ""
    if current is not None:
        next_ar = (
            f"الخطوة الحالية: {current.title_ar} — {current.outcome_ar}"
        )
    proof = (current.proof_ar if current else "") or act.delay_hint_ar or ""
    action_href = (current.action_href if current else "") or act.test_store_url
    action_label = (
        (current.action_label_ar if current else "") or "انتقل للخطوة"
    )

    out = MerchantSetupUnifiedP0(
        unified_p0=True,
        setup_mode=setup_mode,
        sandbox_verified=sandbox_verified,
        production_unlocked=sandbox_verified,
        card_title_ar=title,
        card_lead_ar=lead,
        current_step_ar=(current.title_ar if current else ""),
        current_outcome_ar=(current.outcome_ar if current else ""),
        proof_ar=proof[:400],
        next_step_ar=next_ar[:500],
        action_href=action_href,
        action_label_ar=action_label,
        delay_hint_ar=act.delay_hint_ar,
        test_store_url=act.test_store_url or "/dashboard/test-widget",
        readiness_percent=max(0, min(100, percent)),
        completed_steps=completed_track,
        total_steps=total_track,
        remaining_setup_count=max(0, total_track - completed_track),
        setup_state_label_ar=state_label,
        show_card=True,
        onboarding_complete=prod_complete,
        first_recovery_ready=sandbox_verified,
        celebration_message_ar=celebration,
        steps=steps,
    )

    if emit_logs:
        log.info(
            "[MERCHANT SETUP UNIFIED P0] setup_mode=%s sandbox_verified=%s "
            "percent=%s current=%s",
            setup_mode,
            sandbox_verified,
            percent,
            out.current_step_ar,
        )
    return out


def unified_to_setup_experience(
    unified: MerchantSetupUnifiedP0,
) -> MerchantSetupExperience:
    """Map unified path onto existing setup experience shape for API compat."""
    steps = [
        MerchantSetupStep(
            step_id=s.step_id,
            order=s.order,
            title_ar=s.title_ar,
            outcome_ar=s.outcome_ar,
            action_href=s.action_href,
            complete_action_ar=s.action_label_ar,
            is_complete=s.is_complete,
        )
        for s in unified.steps
        if not s.locked
    ]
    return MerchantSetupExperience(
        show_card=unified.show_card,
        card_title_ar=unified.card_title_ar,
        setup_state_label_ar=unified.setup_state_label_ar,
        readiness_percent=unified.readiness_percent,
        remaining_setup_count=unified.remaining_setup_count,
        outcome_summary_ar=unified.proof_ar or unified.card_lead_ar,
        next_step_ar=unified.next_step_ar,
        action_href=unified.action_href,
        steps=steps,
        merchant_understands_in_30s=bool(
            unified.current_step_ar and unified.current_outcome_ar
        ),
    )


def unified_api_payload(
    unified: MerchantSetupUnifiedP0,
    *,
    flow_dict: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    exp = unified_to_setup_experience(unified)
    out = exp.to_dict()
    out.update(unified.to_dict())
    out["unified_p0"] = True
    out["setup_mode"] = unified.setup_mode
    if flow_dict:
        out["onboarding_complete"] = unified.onboarding_complete
        out["first_recovery_ready"] = unified.first_recovery_ready
        out["completed_steps"] = unified.completed_steps
        out["total_steps"] = unified.total_steps
        out["current_step_ar"] = unified.current_step_ar or out.get("current_step_ar")
        out["current_outcome_ar"] = unified.current_outcome_ar or out.get(
            "current_outcome_ar"
        )
        out["card_title_ar"] = unified.card_title_ar
        out["card_lead_ar"] = unified.card_lead_ar
        out["celebration_message_ar"] = unified.celebration_message_ar
        out["action_href"] = unified.action_href
    return out


__all__ = [
    "MerchantSetupUnifiedP0",
    "UnifiedSetupStep",
    "build_merchant_setup_unified_p0",
    "unified_api_payload",
    "unified_to_setup_experience",
]
