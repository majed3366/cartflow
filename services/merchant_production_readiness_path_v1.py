# -*- coding: utf-8 -*-
"""
Merchant Production Readiness Path v1 — actionable progression to production_ready.

Read-only: builds on merchant_onboarding_reality_v1. No recovery/send/widget changes.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from services.merchant_onboarding_reality_v1 import (
    LEVEL_NOT_STARTED,
    LEVEL_PARTIAL,
    LEVEL_PRODUCTION_READY,
    LEVEL_SANDBOX_ONLY,
    MerchantOnboardingReality,
    evaluate_merchant_onboarding_reality,
)

log = logging.getLogger("cartflow")

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

EFFORT_LOW = "low"
EFFORT_MEDIUM = "medium"
EFFORT_HIGH = "high"


@dataclass
class ReadinessPathItem:
    code: str
    label_ar: str
    satisfied: bool
    next_action_ar: str = ""
    expected_result_ar: str = ""
    risk_level: str = RISK_MEDIUM
    estimated_effort: str = EFFORT_MEDIUM
    weight: int = 10

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MerchantProductionReadinessPath:
    store_slug: str = ""
    onboarding_state: str = LEVEL_NOT_STARTED
    readiness_score: int = 0
    remaining_count: int = 0
    missing_items: list[ReadinessPathItem] = field(default_factory=list)
    next_action_ar: str = ""
    expected_result_ar: str = ""
    risk_level: str = RISK_MEDIUM
    estimated_effort: str = EFFORT_MEDIUM
    state_summary_ar: str = ""
    progression_steps: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["missing_items"] = [i.to_dict() for i in self.missing_items]
        return d


def _item(
    code: str,
    label_ar: str,
    satisfied: bool,
    *,
    next_action_ar: str,
    expected_result_ar: str,
    risk_level: str,
    estimated_effort: str,
    weight: int,
) -> ReadinessPathItem:
    return ReadinessPathItem(
        code=code,
        label_ar=label_ar,
        satisfied=satisfied,
        next_action_ar=next_action_ar,
        expected_result_ar=expected_result_ar,
        risk_level=risk_level,
        estimated_effort=estimated_effort,
        weight=weight,
    )


def _production_path_checks(
    reality: MerchantOnboardingReality,
) -> list[ReadinessPathItem]:
    """Ordered checklist toward production_ready (merchant-safe Arabic)."""
    r = reality
    return [
        _item(
            "store_connected",
            "ربط المتجر",
            r.store_connected,
            next_action_ar="أكمل ربط المتجر مع زد من لوحة التحكم",
            expected_result_ar="يظهر المتجر كمربوط ويمكن مزامنة السلال",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_MEDIUM,
            weight=12,
        ),
        _item(
            "widget_enabled",
            "ودجت استعادة السلة",
            r.widget_enabled,
            next_action_ar="فعّل ودجت CartFlow وضع الشيفرة في المتجر",
            expected_result_ar="تُسجَّل السلال المهجورة من المتجر",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_LOW,
            weight=12,
        ),
        _item(
            "recovery_enabled",
            "تفعيل الاسترجاع",
            r.recovery_enabled,
            next_action_ar="فعّل الاسترجاع الآلي وعدد المحاولات",
            expected_result_ar="يُجدول إرسال رسائل الاسترجاع تلقائياً",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_LOW,
            weight=12,
        ),
        _item(
            "recovery_delays",
            "تأخير المحاولات",
            r.delays_configured,
            next_action_ar="اضبط تأخير المحاولة الأولى والثانية",
            expected_result_ar="تُحترم فترات الانتظار قبل الإرسال",
            risk_level=RISK_MEDIUM,
            estimated_effort=EFFORT_LOW,
            weight=8,
        ),
        _item(
            "templates_local",
            "قوالب الاسترجاع",
            r.templates_present,
            next_action_ar="أكمل قوالب الاسترجاع حسب أسباب التردد",
            expected_result_ar="تُرسل رسائل متسقة مع سبب ترك السلة",
            risk_level=RISK_MEDIUM,
            estimated_effort=EFFORT_MEDIUM,
            weight=10,
        ),
        _item(
            "store_whatsapp_number",
            "رقم واتساب المتجر",
            r.store_whatsapp_number_set,
            next_action_ar="أضف رقم واتساب الدعم/التاجر في الإعدادات",
            expected_result_ar="يظهر رقم تواصل صحيح للعملاء والتشغيل",
            risk_level=RISK_MEDIUM,
            estimated_effort=EFFORT_LOW,
            weight=8,
        ),
        _item(
            "production_provider",
            "مزود واتساب الإنتاج",
            r.provider_connected,
            next_action_ar="ربط مزود واتساب الإنتاج",
            expected_result_ar="يُفعَّل إرسال واتساب حقيقي عبر Twilio في الإنتاج",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_MEDIUM,
            weight=15,
        ),
        _item(
            "delivery_truth",
            "متابعة تسليم الرسائل",
            r.delivery_truth_ready,
            next_action_ar="اضبط عنوان استدعاء حالة التسليم على الخادم",
            expected_result_ar="تُسجَّل حالات queued/delivered/failed بدقة",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_MEDIUM,
            weight=12,
        ),
        _item(
            "templates_approved",
            "اعتماد قوالب المزود",
            r.onboarding_state == LEVEL_PRODUCTION_READY
            or "templates_not_provider_approved" not in r.missing,
            next_action_ar="قدّم قوالب واتساب للاعتماد لدى المزود",
            expected_result_ar="لا تُرفض الرسائل خارج نافذة 24 ساعة",
            risk_level=RISK_HIGH,
            estimated_effort=EFFORT_HIGH,
            weight=11,
        ),
    ]


def _state_progression_meta(state: str) -> dict[str, str]:
    meta = {
        LEVEL_NOT_STARTED: {
            "summary_ar": "لم يبدأ إعداد المتجر بعد",
            "default_next_ar": "أنشئ أو اربط سجل المتجر من لوحة التحكم",
            "default_expected_ar": "يظهر المتجر في لوحة CartFlow ويمكن متابعة الإعداد",
            "risk": RISK_HIGH,
            "effort": EFFORT_MEDIUM,
        },
        LEVEL_SANDBOX_ONLY: {
            "summary_ar": "التشغيل تجريبي — ليس إنتاج واتساب كامل",
            "default_next_ar": "ربط مزود واتساب الإنتاج",
            "default_expected_ar": "يتحول المسار من تجريبي إلى إرسال إنتاجي حقيقي",
            "risk": RISK_HIGH,
            "effort": EFFORT_MEDIUM,
        },
        LEVEL_PARTIAL: {
            "summary_ar": "قريب من الإنتاج — بقيت خطوات محددة",
            "default_next_ar": "أكمل البنود الناقصة أدناه بالترتيب",
            "default_expected_ar": "يصل المستوى إلى جاهز للإنتاج",
            "risk": RISK_MEDIUM,
            "effort": EFFORT_MEDIUM,
        },
        LEVEL_PRODUCTION_READY: {
            "summary_ar": "جاهز للإنتاج — راقب الإرسال والتسليم",
            "default_next_ar": "تابع لوحة السلال ومراقبة التشغيل",
            "default_expected_ar": "استمرار استرجاع موثوق مع حقيقة التسليم",
            "risk": RISK_LOW,
            "effort": EFFORT_LOW,
        },
    }
    return meta.get(state, meta[LEVEL_PARTIAL])


def build_merchant_production_readiness_path(
    store: Optional[Any] = None,
    *,
    emit_logs: bool = True,
) -> MerchantProductionReadinessPath:
    reality = evaluate_merchant_onboarding_reality(store, emit_log=False)
    if emit_logs:
        from services.merchant_onboarding_reality_v1 import _log_merchant_readiness

        _log_merchant_readiness(reality)
    state = reality.onboarding_state
    meta = _state_progression_meta(state)

    if state == LEVEL_NOT_STARTED:
        items = [
            _item(
                "dashboard_init",
                "تهيئة المتجر",
                False,
                next_action_ar=meta["default_next_ar"],
                expected_result_ar=meta["default_expected_ar"],
                risk_level=RISK_HIGH,
                estimated_effort=EFFORT_MEDIUM,
                weight=100,
            ),
        ]
        missing = list(items)
        score = 0
    elif state == LEVEL_PRODUCTION_READY:
        items = _production_path_checks(reality)
        missing = [i for i in items if not i.satisfied]
        total_w = sum(i.weight for i in items) or 1
        earned = sum(i.weight for i in items if i.satisfied)
        score = 100
    else:
        items = _production_path_checks(reality)
        if state == LEVEL_SANDBOX_ONLY:
            sandbox_only_codes = {
                "store_connected",
                "widget_enabled",
                "recovery_enabled",
                "recovery_delays",
                "templates_local",
                "store_whatsapp_number",
            }
            for it in items:
                if it.code not in sandbox_only_codes:
                    it.satisfied = False
            extra = [
                _item(
                    "production_provider",
                    "مزود واتساب الإنتاج",
                    False,
                    next_action_ar="ربط مزود واتساب الإنتاج",
                    expected_result_ar="يُفعَّل PRODUCTION_MODE وTwilio على الخادم",
                    risk_level=RISK_HIGH,
                    estimated_effort=EFFORT_MEDIUM,
                    weight=15,
                ),
                _item(
                    "delivery_truth",
                    "متابعة تسليم الرسائل",
                    False,
                    next_action_ar="اضبط رابط استدعاء حالة التسليم",
                    expected_result_ar="تُعرَف حالات التسليم بعد الإرسال",
                    risk_level=RISK_HIGH,
                    estimated_effort=EFFORT_MEDIUM,
                    weight=12,
                ),
                _item(
                    "templates_approved",
                    "اعتماد قوالب المزود",
                    False,
                    next_action_ar="قدّم قوالب واتساب للاعتماد",
                    expected_result_ar="رسائل خارج 24 ساعة مقبولة من المزود",
                    risk_level=RISK_HIGH,
                    estimated_effort=EFFORT_HIGH,
                    weight=11,
                ),
            ]
            items = items + extra
        missing = [i for i in items if not i.satisfied]
        total_w = sum(i.weight for i in items) or 1
        earned = sum(i.weight for i in items if i.satisfied)
        score = int(round(100.0 * earned / total_w))
        if state == LEVEL_SANDBOX_ONLY:
            score = min(score, 55)

    remaining = len(missing)
    if missing:
        top = missing[0]
        next_action = top.next_action_ar
        expected = top.expected_result_ar
        risk = top.risk_level
        effort = top.estimated_effort
    else:
        next_action = meta["default_next_ar"]
        expected = meta["default_expected_ar"]
        risk = meta["risk"]
        effort = meta["effort"]

    progression = _build_capability_progression(items, state)

    path = MerchantProductionReadinessPath(
        store_slug=reality.store_slug,
        onboarding_state=state,
        readiness_score=max(0, min(100, score)),
        remaining_count=remaining,
        missing_items=missing,
        next_action_ar=next_action,
        expected_result_ar=expected,
        risk_level=risk,
        estimated_effort=effort,
        state_summary_ar=meta["summary_ar"],
        progression_steps=progression,
    )

    if emit_logs:
        _log_merchant_next_action(path)

    return path


def _build_capability_progression(
    items: list[ReadinessPathItem],
    state: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for it in items:
        rows.append(
            {
                "state": state,
                "item": it.label_ar,
                "missing": "لا" if it.satisfied else "نعم",
                "action": it.next_action_ar,
                "expected_outcome": it.expected_result_ar,
            }
        )
    return rows


def _log_merchant_next_action(path: MerchantProductionReadinessPath) -> None:
    remaining_labels = [m.label_ar for m in path.missing_items[:8]]
    rem_s = ",".join(remaining_labels) if remaining_labels else "-"
    line = (
        f"[MERCHANT NEXT ACTION] store_slug={path.store_slug} "
        f"state={path.onboarding_state} next_action={path.next_action_ar} "
        f"remaining={rem_s}"
    )
    print(line, flush=True)
    log.info("%s", line)


def build_merchant_production_readiness_card(
    store: Optional[Any] = None,
) -> dict[str, Any]:
    """Admin card: current state → missing → next step → expected result + score."""
    from services.admin_operational_health_language import (
        build_operations_center_decision,
    )

    path = build_merchant_production_readiness_path(store, emit_logs=False)
    level_ar = {
        LEVEL_NOT_STARTED: "لم يبدأ",
        LEVEL_SANDBOX_ONLY: "تجريبي فقط",
        LEVEL_PARTIAL: "جزئي",
        LEVEL_PRODUCTION_READY: "جاهز للإنتاج",
    }.get(path.onboarding_state, path.onboarding_state)

    missing_lines = [
        f"• {m.label_ar} ({m.risk_level}/{m.estimated_effort})"
        for m in path.missing_items[:6]
    ]
    if not missing_lines:
        missing_lines = ["• لا يوجد — جاهز للإنتاج"]

    detail_lines = [
        f"الحالة الحالية: {level_ar}",
        f"جاهزية الإنتاج: {path.readiness_score}%",
        f"متبقي: {path.remaining_count} بند",
        "البنود الناقصة:",
        *missing_lines[:6],
        f"الخطوة التالية: {path.next_action_ar}",
        f"النتيجة المتوقعة: {path.expected_result_ar}",
    ]
    tier = "ok" if path.onboarding_state == LEVEL_PRODUCTION_READY else (
        "watch" if path.onboarding_state == LEVEL_PARTIAL else "action"
    )
    return {
        "title": "merchant_onboarding",
        "title_ar": "جاهزية المتجر",
        "onboarding_state": path.onboarding_state,
        "store_slug": path.store_slug,
        "readiness_score": path.readiness_score,
        "remaining_count": path.remaining_count,
        "path": path.to_dict(),
        "operational": build_operations_center_decision(
            title_ar="جاهزية المتجر",
            problem_ar=f"{level_ar} — {path.readiness_score}%",
            impact_ar=path.state_summary_ar,
            affected_stores_ar=path.store_slug,
            affected_customers_ar="—",
            urgency_ar=(
                "عالية"
                if path.risk_level == RISK_HIGH
                else ("متوسطة" if path.risk_level == RISK_MEDIUM else "منخفضة")
            ),
            suggested_action_ar=path.next_action_ar,
            verification_lines=[
                f"النتيجة المتوقعة: {path.expected_result_ar}",
                f"متبقي {path.remaining_count} بند",
            ],
            status_tier=tier,
        ),
        "technical_detail_lines": detail_lines,
        "detail_lines": detail_lines,
    }


def merchant_understands_next_step(path: MerchantProductionReadinessPath) -> bool:
    """Verification helper: actionable Arabic next step + expected result present."""
    return bool(
        (path.next_action_ar or "").strip()
        and (path.expected_result_ar or "").strip()
        and path.onboarding_state
    )
