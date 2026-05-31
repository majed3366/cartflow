# -*- coding: utf-8 -*-
"""
Onboarding Experience V2 — guided activation journey (UX only).

Builds merchant-facing checklist, progress, nav locks, readiness, and empty-state
copy from existing onboarding evaluators. Does not change recovery, widget, WhatsApp,
database, decision engine, lifecycle, or cart behavior.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.merchant_activation_v1 import merchant_activation_test_store_url
from services.merchant_setup_unified_p0 import (
    MerchantSetupUnifiedP0,
    build_merchant_setup_unified_p0,
)
from services.cartflow_onboarding_readiness import evaluate_onboarding_readiness

_FORBIDDEN = re.compile(
    r"\boauth\b|\bwebhook\b|\bprovider\b|\bruntime\b|recovery engine|"
    r"callback|twilio|status_callback",
    re.I,
)

JOURNEY_VERSION = 2


@dataclass
class JourneyStep:
    step_id: str
    order: int
    title_ar: str
    why_ar: str
    action_href: str
    action_label_ar: str
    status: str  # done | current | locked
    is_complete: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NavLock:
    page: str
    unlocked: bool
    reason_ar: str
    required_step_title_ar: str
    cta_href: str
    cta_label_ar: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReadinessCard:
    title_ar: str
    lead_ar: str
    checklist_ar: list[str]
    footer_ar: str
    cta_href: str
    cta_label_ar: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EmptyStateHint:
    page: str
    title_ar: str
    body_ar: str
    cta_href: str
    cta_label_ar: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActivationJourneyV2:
    version: int = JOURNEY_VERSION
    journey_title_ar: str = "تفعيل المتجر"
    progress_percent: int = 0
    completed_steps: int = 0
    total_steps: int = 0
    progress_label_ar: str = ""
    onboarding_complete: bool = False
    show_journey: bool = True
    current_step_id: str = ""
    steps: list[JourneyStep] = field(default_factory=list)
    readiness_card: Optional[ReadinessCard] = None
    nav_locks: dict[str, NavLock] = field(default_factory=dict)
    empty_states: dict[str, EmptyStateHint] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        d["nav_locks"] = {k: v.to_dict() for k, v in self.nav_locks.items()}
        if self.readiness_card:
            d["readiness_card"] = self.readiness_card.to_dict()
        d["empty_states"] = {k: v.to_dict() for k, v in self.empty_states.items()}
        return d


def _sanitize(text: str) -> str:
    t = (text or "").strip()
    for old, new in (
        ("OAuth", ""),
        ("oauth", ""),
        ("Webhook", ""),
        ("webhook", ""),
        ("Provider", ""),
        ("provider", ""),
        ("Recovery Engine", "الاسترجاع"),
        ("Runtime", ""),
    ):
        t = t.replace(old, new)
    return " ".join(t.split())


def _flags_from_unified(
    unified: MerchantSetupUnifiedP0,
    store: Optional[Any],
    ev: Optional[dict[str, Any]] = None,
) -> dict[str, bool]:
    slug = (getattr(store, "zid_store_id", None) or "").strip() if store else ""
    by_id = {s.step_id: s for s in unified.steps}
    account = bool(by_id.get("sandbox_account") and by_id["sandbox_account"].is_complete)
    widget_test = bool(
        by_id.get("sandbox_test_widget") and by_id["sandbox_test_widget"].is_complete
    )
    connect_store = bool(by_id.get("prod_oauth") and by_id["prod_oauth"].is_complete)
    whatsapp = bool(by_id.get("prod_whatsapp") and by_id["prod_whatsapp"].is_complete)
    review_messages = bool(
        by_id.get("prod_templates") and by_id["prod_templates"].is_complete
    )
    live_widget = bool(
        by_id.get("prod_live_widget") and by_id["prod_live_widget"].is_complete
    )
    ready = unified.onboarding_complete
    test_url = unified.test_store_url or merchant_activation_test_store_url(slug)
    recovery_on = bool((ev or {}).get("flags", {}).get("recovery_enabled"))
    return {
        "account": account,
        "widget_test": widget_test,
        "connect_store": connect_store,
        "configure_whatsapp": whatsapp,
        "review_messages": review_messages,
        "ready_for_launch": ready and live_widget,
        "live_widget": live_widget,
        "recovery_enabled": recovery_on,
        "test_url": test_url,
        "sandbox_verified": unified.sandbox_verified,
    }


def _readiness_checklist(flags: dict[str, bool]) -> list[str]:
    """Merchant-safe checklist — only lines backed by current activation flags."""
    lines: list[str] = []
    if flags.get("live_widget") or flags.get("ready_for_launch"):
        lines.append("الودجيت مُعدّ")
    if flags.get("connect_store"):
        lines.append("المتجر مربوط")
    if flags.get("configure_whatsapp"):
        lines.append("واتساب مُعدّ")
    if flags.get("recovery_enabled"):
        lines.append("الاسترجاع مفعّل")
    return lines


def _assign_statuses(checks: list[tuple[str, bool]]) -> list[str]:
    statuses: list[str] = []
    current_set = False
    for i, (_, done) in enumerate(checks):
        if done:
            statuses.append("done")
            continue
        prior_done = all(checks[j][1] for j in range(i))
        if not prior_done:
            statuses.append("locked")
        elif not current_set:
            statuses.append("current")
            current_set = True
        else:
            statuses.append("locked")
    return statuses


def build_activation_journey_v2(
    store: Optional[Any] = None,
    *,
    merchant_user_id: Optional[int] = None,
    unified: Optional[MerchantSetupUnifiedP0] = None,
) -> ActivationJourneyV2:
    u = unified or build_merchant_setup_unified_p0(
        store,
        merchant_user_id=merchant_user_id,
        emit_logs=False,
    )
    ev = evaluate_onboarding_readiness(store) if store is not None else {}
    flags = _flags_from_unified(u, store, ev)
    test_url = str(flags.get("test_url") or "/dashboard/test-widget")

    specs: list[dict[str, Any]] = [
        {
            "step_id": "account",
            "title_ar": "تم إنشاء الحساب",
            "why_ar": "حسابك يفتح لوحة التحكم ومسار تفعيل المتجر.",
            "action_href": "/dashboard#home",
            "action_label_ar": "الرئيسية",
            "done": flags["account"],
        },
        {
            "step_id": "widget_test",
            "title_ar": "تجربة الودجيت",
            "why_ar": "CartFlow يحتاج أول سلة ليفهم سبب تردد العميل.",
            "action_href": test_url,
            "action_label_ar": "فتح متجر الاختبار",
            "done": flags["widget_test"],
        },
        {
            "step_id": "connect_store",
            "title_ar": "ربط المتجر",
            "why_ar": "CartFlow يحتاج الوصول لنشاط السلال في متجرك.",
            "action_href": "/dashboard#settings",
            "action_label_ar": "ربط المتجر",
            "done": flags["connect_store"],
        },
        {
            "step_id": "configure_whatsapp",
            "title_ar": "إعداد واتساب",
            "why_ar": "لإرسال رسائل المتابعة للعملاء عند ترك السلة.",
            "action_href": "/dashboard#whatsapp",
            "action_label_ar": "إعداد واتساب",
            "done": flags["configure_whatsapp"],
        },
        {
            "step_id": "review_messages",
            "title_ar": "مراجعة رسائل الاسترجاع",
            "why_ar": "تخصيص ما يصل للعميل حسب سبب التردد.",
            "action_href": "/dashboard#trigger-templates",
            "action_label_ar": "مراجعة الرسائل",
            "done": flags["review_messages"],
        },
        {
            "step_id": "ready_for_launch",
            "title_ar": "جاهز للتشغيل",
            "why_ar": "CartFlow يراقب السلال المهجورة ويشرح كل خطوة لك.",
            "action_href": "/dashboard#widget",
            "action_label_ar": "إعداد الودجيت على المتجر",
            "done": flags["ready_for_launch"],
        },
    ]

    checks = [(s["step_id"], bool(s["done"])) for s in specs]
    statuses = _assign_statuses(checks)
    steps: list[JourneyStep] = []
    current_id = ""
    completed = 0
    for i, spec in enumerate(specs):
        done = bool(spec["done"])
        if done:
            completed += 1
        st = statuses[i]
        if st == "current":
            current_id = str(spec["step_id"])
        steps.append(
            JourneyStep(
                step_id=str(spec["step_id"]),
                order=i + 1,
                title_ar=_sanitize(str(spec["title_ar"])),
                why_ar=_sanitize(str(spec["why_ar"])),
                action_href=str(spec["action_href"]),
                action_label_ar=_sanitize(str(spec["action_label_ar"])),
                status=st,
                is_complete=done,
            )
        )

    total = len(steps)
    percent = int(round(100.0 * completed / total)) if total else 0
    complete = u.onboarding_complete

    nav_specs: list[tuple[str, str, str, str, str]] = [
        (
            "settings",
            "connect_store",
            "ربط المتجر",
            "أكمل تجربة الودجيت أولاً لفهم كيف يعمل CartFlow.",
            "/dashboard/test-widget",
        ),
        (
            "whatsapp",
            "configure_whatsapp",
            "إعداد واتساب",
            "اربط متجرك أولاً — CartFlow يحتاج نشاط السلال.",
            "/dashboard#settings",
        ),
        (
            "trigger-templates",
            "review_messages",
            "مراجعة رسائل الاسترجاع",
            "أكمل إعداد واتساب قبل تخصيص الرسائل.",
            "/dashboard#whatsapp",
        ),
        (
            "widget",
            "connect_store",
            "ربط المتجر",
            "اربط متجرك قبل تثبيت الودجيت على واجهة المتجر.",
            "/dashboard#settings",
        ),
    ]
    nav_locks: dict[str, NavLock] = {}
    step_titles = {s.step_id: s.title_ar for s in steps}
    for page, unlock_after, title, reason, cta in nav_specs:
        if unlock_after == "connect_store":
            unlocked = flags["widget_test"]
        elif unlock_after == "configure_whatsapp":
            unlocked = flags["connect_store"]
        elif unlock_after == "review_messages":
            unlocked = flags["configure_whatsapp"]
        else:
            unlocked = bool(flags.get(unlock_after))
        if complete:
            unlocked = True
        req_title = step_titles.get(unlock_after, title)
        cta_href = test_url if unlock_after == "connect_store" and not flags["widget_test"] else cta
        nav_locks[page] = NavLock(
            page=page,
            unlocked=unlocked,
            reason_ar=_sanitize(reason),
            required_step_title_ar=_sanitize(req_title),
            cta_href=cta_href,
            cta_label_ar="متابعة الإعداد" if not unlocked else "متابعة",
        )

    empty_states = {
        "carts": EmptyStateHint(
            page="carts",
            title_ar="لا توجد سلال مهجورة بعد",
            body_ar=(
                "بعد تجربة الودجيت أو ربط متجرك واستقبال زوار، "
                "ستظهر هنا فرص الاسترجاع مع سبب التردد والخطوة التالية."
            ),
            cta_href=test_url if not flags["widget_test"] else "/dashboard#settings",
            cta_label_ar="تجربة الودجيت"
            if not flags["widget_test"]
            else "ربط المتجر",
        ),
        "messages": EmptyStateHint(
            page="messages",
            title_ar="لا توجد رسائل مرسلة بعد",
            body_ar=(
                "عند تفعيل واتساب وبدء متابعة السلال، "
                "سيسجل CartFlow كل رسالة مع حالتها هنا."
            ),
            cta_href="/dashboard#whatsapp",
            cta_label_ar="إعداد واتساب",
        ),
        "reasons": EmptyStateHint(
            page="reasons",
            title_ar="لا توجد بيانات أسباب التردد بعد",
            body_ar=(
                "عندما يتردد العملاء عبر الودجيت، "
                "سترى توزيع الأسباب وتوصيات واضحة في هذه الصفحة."
            ),
            cta_href=test_url,
            cta_label_ar="تجربة الودجيت",
        ),
    }

    readiness: Optional[ReadinessCard] = None
    if complete:
        checklist = _readiness_checklist(flags)
        readiness = ReadinessCard(
            title_ar="متجرك جاهز للتشغيل",
            lead_ar="CartFlow يراقب الآن السلال المهجورة ويشرح كل خطوة.",
            checklist_ar=checklist,
            footer_ar="يمكنك متابعة السلال والرسائل من لوحة التحكم.",
            cta_href="/dashboard#carts",
            cta_label_ar="الذهاب إلى لوحة السلال",
        )

    progress_label = f"{completed} / {total} خطوات مكتملة"

    return ActivationJourneyV2(
        version=JOURNEY_VERSION,
        journey_title_ar="تفعيل المتجر",
        progress_percent=percent,
        completed_steps=completed,
        total_steps=total,
        progress_label_ar=progress_label,
        onboarding_complete=complete,
        show_journey=not complete,
        current_step_id=current_id,
        steps=steps,
        readiness_card=readiness,
        nav_locks=nav_locks,
        empty_states=empty_states,
    )


def journey_copy_is_merchant_safe(journey: ActivationJourneyV2) -> bool:
    blob = journey.journey_title_ar + " " + journey.progress_label_ar
    for s in journey.steps:
        blob += s.title_ar + " " + s.why_ar + " " + s.action_label_ar
    for lock in journey.nav_locks.values():
        blob += lock.reason_ar + " " + lock.required_step_title_ar
    if journey.readiness_card:
        blob += journey.readiness_card.title_ar + " " + journey.readiness_card.lead_ar
    return _FORBIDDEN.search(blob) is None


def attach_journey_to_setup_payload(
    payload: dict[str, Any],
    store: Optional[Any] = None,
    *,
    merchant_user_id: Optional[int] = None,
) -> dict[str, Any]:
    """Merge activation journey v2 into merchant_setup_experience API dict."""
    unified = build_merchant_setup_unified_p0(
        store,
        merchant_user_id=merchant_user_id,
        emit_logs=False,
    )
    journey = build_activation_journey_v2(
        store,
        merchant_user_id=merchant_user_id,
        unified=unified,
    )
    payload["activation_journey_v2"] = journey.to_dict()
    payload["onboarding_journey_v2"] = True
    return payload


__all__ = [
    "ActivationJourneyV2",
    "JourneyStep",
    "NavLock",
    "ReadinessCard",
    "attach_journey_to_setup_payload",
    "build_activation_journey_v2",
    "journey_copy_is_merchant_safe",
]
