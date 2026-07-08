# -*- coding: utf-8 -*-
"""Read-only plans catalog for merchant dashboard — pricing + marketing features."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from services.cartflow_plans_v1 import (
    CANONICAL_PLAN_IDS,
    PLAN_GROWTH,
    PLAN_LABEL_AR,
    PLAN_PRO,
    PLAN_STARTER,
    PlanId,
)

PLAN_PRICING_SAR: Mapping[PlanId, dict[str, int]] = {
    PLAN_STARTER: {"monthly": 99, "annual": 990},
    PLAN_GROWTH: {"monthly": 199, "annual": 1990},
    PLAN_PRO: {"monthly": 399, "annual": 3990},
}

PLAN_SUPPORT_AR: Mapping[PlanId, str] = {
    PLAN_STARTER: "دعم قياسي",
    PLAN_GROWTH: "دعم أولوية",
    PLAN_PRO: "أعلى أولوية للدعم",
}

# Marketing feature lists (aligned with packages pricing foundation audit).
PLAN_MARKETING_FEATURES_AR: Mapping[PlanId, tuple[str, ...]] = {
    PLAN_STARTER: (
        "الودجيت",
        "التقاط سبب التردد",
        "استرجاع واتساب",
        "لوحة التحكم",
        "خط زمني للاسترجاع",
        "تحليلات أساسية",
        "قوالب افتراضية",
        "توقيت موصى به",
        "تجربة mobile-first",
        "دعم قياسي",
    ),
    PLAN_GROWTH: (
        "كل ميزات Starter",
        "كشف VIP",
        "تنبيهات VIP",
        "رسائل متعددة",
        "قوالب لكل سبب",
        "توقيت لكل سبب",
        "تحليلات متقدمة",
        "رؤى الاسترجاع",
        "تحكم التاجر",
        "دعم أولوية",
    ),
    PLAN_PRO: (
        "كل ميزات Growth",
        "منطق رسائل متقدم",
        "تحكم استرجاع متقدم",
        "رؤى تشغيلية",
        "الوصول المبكر للميزات",
        "ذكاء المنتج (قريباً)",
        "ذكاء العروض (قريباً)",
        "ذكاء تشغيلي (قريباً)",
        "أعلى أولوية للدعم",
    ),
}

MOST_POPULAR_PLAN_ID: PlanId = PLAN_GROWTH


@dataclass
class MerchantPlanCatalogEntry:
    plan_id: PlanId
    label_ar: str
    monthly_sar: int
    annual_sar: int
    monthly_label_ar: str
    annual_label_ar: str
    features_ar: tuple[str, ...]
    support_ar: str
    most_popular: bool
    upgrade_path_note_ar: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "label_ar": self.label_ar,
            "monthly_sar": self.monthly_sar,
            "annual_sar": self.annual_sar,
            "monthly_label_ar": self.monthly_label_ar,
            "annual_label_ar": self.annual_label_ar,
            "features_ar": list(self.features_ar),
            "support_ar": self.support_ar,
            "most_popular": self.most_popular,
            "upgrade_path_note_ar": self.upgrade_path_note_ar,
        }


def _price_label(amount: int, *, cycle: str) -> str:
    if cycle == "annual":
        return f"{amount:,} SR / سنة"
    return f"{amount} SR / شهر"


def build_plan_catalog_entry(plan_id: PlanId) -> MerchantPlanCatalogEntry:
    pricing = PLAN_PRICING_SAR[plan_id]
    monthly = int(pricing["monthly"])
    annual = int(pricing["annual"])
    popular = plan_id == MOST_POPULAR_PLAN_ID
    if plan_id == PLAN_STARTER:
        note = "نقطة البداية — استرجع أول سلة متروكة."
    elif plan_id == PLAN_GROWTH:
        note = "الأنسب للمتاجر النشطة — VIP ورسائل متابعة."
    else:
        note = "للمتاجر المتقدمة — ميزات ذكاء قادمة."
    return MerchantPlanCatalogEntry(
        plan_id=plan_id,
        label_ar=PLAN_LABEL_AR[plan_id],
        monthly_sar=monthly,
        annual_sar=annual,
        monthly_label_ar=_price_label(monthly, cycle="monthly"),
        annual_label_ar=_price_label(annual, cycle="annual"),
        features_ar=PLAN_MARKETING_FEATURES_AR[plan_id],
        support_ar=PLAN_SUPPORT_AR[plan_id],
        most_popular=popular,
        upgrade_path_note_ar=note,
    )


def build_merchant_plans_catalog() -> dict[str, Any]:
    plans: Sequence[MerchantPlanCatalogEntry] = tuple(
        build_plan_catalog_entry(plan_id) for plan_id in CANONICAL_PLAN_IDS
    )
    return {
        "read_only": True,
        "billing_available": False,
        "upgrade_available": False,
        "currency": "SAR",
        "most_popular_plan_id": MOST_POPULAR_PLAN_ID,
        "footnote_ar": (
            "عرض للمقارنة فقط — لا ترقية ولا دفع من لوحة التحكم بعد. "
            "التفعيل مستقبلاً عبر زد أو سلة أو CartFlow."
        ),
        "plans": [entry.to_api_dict() for entry in plans],
    }
