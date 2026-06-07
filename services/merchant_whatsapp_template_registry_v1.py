# -*- coding: utf-8 -*-
"""Canonical WhatsApp template registry — source of truth (no Meta/send/runtime)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

TEMPLATE_TYPE_REASON = "reason_recovery"
TEMPLATE_TYPE_FOLLOWUP = "followup"
TEMPLATE_TYPE_VIP = "vip_alert"
TEMPLATE_TYPE_FALLBACK = "fallback"

META_STATUS_DRAFT = "draft"
META_STATUS_APPROVED = "approved"
META_STATUS_REJECTED = "rejected"
META_STATUS_DISABLED = "disabled"

CANONICAL_META_STATUSES: frozenset[str] = frozenset(
    {META_STATUS_DRAFT, META_STATUS_APPROVED, META_STATUS_REJECTED, META_STATUS_DISABLED}
)

PLAN_TIER_STARTER = "starter"
PLAN_TIER_GROWTH = "growth"
PLAN_TIER_PRO = "pro"

META_STATUS_LABEL_AR: Mapping[str, str] = {
    META_STATUS_DRAFT: "مسودة",
    META_STATUS_APPROVED: "معتمد",
    META_STATUS_REJECTED: "مرفوض",
    META_STATUS_DISABLED: "معطّل",
}


@dataclass(frozen=True)
class TemplateRegistryEntry:
    template_key: str
    display_name_ar: str
    reason_tag: Optional[str]
    template_type: str
    default_content: str
    enabled: bool
    future_meta_template_name: str
    future_meta_status: str
    merchant_editable: bool = False
    customization_plan_tier: str = PLAN_TIER_STARTER

    def to_dict(self) -> dict[str, Any]:
        return {
            "template_key": self.template_key,
            "display_name_ar": self.display_name_ar,
            "reason_tag": self.reason_tag,
            "template_type": self.template_type,
            "default_content": self.default_content,
            "enabled": self.enabled,
            "future_meta_template_name": self.future_meta_template_name,
            "future_meta_status": self.future_meta_status,
            "future_meta_status_ar": meta_status_label_ar(self.future_meta_status),
            "merchant_editable": self.merchant_editable,
            "customization_plan_tier": self.customization_plan_tier,
        }


def meta_status_label_ar(status: str) -> str:
    return META_STATUS_LABEL_AR.get((status or "").strip().lower(), status)


def normalize_meta_status(raw: Any) -> str:
    key = (raw or "").strip().lower()
    return key if key in CANONICAL_META_STATUSES else META_STATUS_DRAFT


# Default bodies aligned with recovery_message_templates.py (runtime unchanged).
_PRICE = (
    "وفرنا لك خيار بنفس الفكرة بسعر أقل 👌\n"
    "تقدر تكمل الطلب مباشرة من هنا 👇"
)
_SHIPPING = (
    "أتفهمك 👍 تكلفة الشحن تفرق... أحيانًا فيه عروض أو خيارات أفضل 👍 تحب أشوف لك؟"
)
_QUALITY = (
    "سؤال مهم 👌 الجودة تهم... هذا المنتج عليه ضمان وجودة عالية 👍 تحب تفاصيل أكثر؟"
)
_DELIVERY = (
    "واضح 👍 وقت التوصيل مهم... نقدر نشوف لك أسرع خيار متاح 🚚 تحب؟"
)
_WARRANTY = (
    "أفهمك 👌 الضمان مهم... هذا المنتج عليه ضمان رسمي 👍 تحب أوضح لك؟"
)
_OTHER = (
    "تمام 👍 خلني أساعدك بشكل أفضل... وش أكثر شيء مسبب لك تردد؟"
)
_UNKNOWN = "لاحظنا إنك مهتم 👌 حاب نساعدك تكمل الطلب؟"
_FOLLOWUP_1 = "مرحبًا 👋 ما زال طلبك محفوظ — تحب نكمل؟"
_FOLLOWUP_2 = "تذكير سريع 👌 سلّتك لسه موجودة — جاهز تكمل؟"
_FOLLOWUP_3 = "آخر تذكير 👍 إذا احتجت مساعدة نحن هنا."
_VIP = (
    "تنبيه CartFlow — سلّة VIP\n"
    "افتح لوحة التحكم لمتابعة السلّة."
)

TEMPLATE_REGISTRY: dict[str, TemplateRegistryEntry] = {
    "PRICE_TEMPLATE": TemplateRegistryEntry(
        template_key="PRICE_TEMPLATE",
        display_name_ar="السعر",
        reason_tag="price",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_PRICE,
        enabled=True,
        future_meta_template_name="cartflow_price_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "QUALITY_TEMPLATE": TemplateRegistryEntry(
        template_key="QUALITY_TEMPLATE",
        display_name_ar="الجودة",
        reason_tag="quality",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_QUALITY,
        enabled=True,
        future_meta_template_name="cartflow_quality_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "SHIPPING_TEMPLATE": TemplateRegistryEntry(
        template_key="SHIPPING_TEMPLATE",
        display_name_ar="الشحن",
        reason_tag="shipping",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_SHIPPING,
        enabled=True,
        future_meta_template_name="cartflow_shipping_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "DELIVERY_TEMPLATE": TemplateRegistryEntry(
        template_key="DELIVERY_TEMPLATE",
        display_name_ar="التوصيل",
        reason_tag="delivery",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_DELIVERY,
        enabled=True,
        future_meta_template_name="cartflow_delivery_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "WARRANTY_TEMPLATE": TemplateRegistryEntry(
        template_key="WARRANTY_TEMPLATE",
        display_name_ar="الضمان",
        reason_tag="warranty",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_WARRANTY,
        enabled=True,
        future_meta_template_name="cartflow_warranty_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "OTHER_TEMPLATE": TemplateRegistryEntry(
        template_key="OTHER_TEMPLATE",
        display_name_ar="سبب آخر",
        reason_tag="other",
        template_type=TEMPLATE_TYPE_REASON,
        default_content=_OTHER,
        enabled=True,
        future_meta_template_name="cartflow_other_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=True,
        customization_plan_tier=PLAN_TIER_GROWTH,
    ),
    "UNKNOWN_REASON_TEMPLATE": TemplateRegistryEntry(
        template_key="UNKNOWN_REASON_TEMPLATE",
        display_name_ar="سبب غير معروف",
        reason_tag="unknown",
        template_type=TEMPLATE_TYPE_FALLBACK,
        default_content=_UNKNOWN,
        enabled=True,
        future_meta_template_name="cartflow_unknown_recovery_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=False,
        customization_plan_tier=PLAN_TIER_STARTER,
    ),
    "FOLLOWUP_1_TEMPLATE": TemplateRegistryEntry(
        template_key="FOLLOWUP_1_TEMPLATE",
        display_name_ar="متابعة 1",
        reason_tag=None,
        template_type=TEMPLATE_TYPE_FOLLOWUP,
        default_content=_FOLLOWUP_1,
        enabled=True,
        future_meta_template_name="cartflow_followup_1_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=False,
        customization_plan_tier=PLAN_TIER_PRO,
    ),
    "FOLLOWUP_2_TEMPLATE": TemplateRegistryEntry(
        template_key="FOLLOWUP_2_TEMPLATE",
        display_name_ar="متابعة 2",
        reason_tag=None,
        template_type=TEMPLATE_TYPE_FOLLOWUP,
        default_content=_FOLLOWUP_2,
        enabled=True,
        future_meta_template_name="cartflow_followup_2_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=False,
        customization_plan_tier=PLAN_TIER_PRO,
    ),
    "FOLLOWUP_3_TEMPLATE": TemplateRegistryEntry(
        template_key="FOLLOWUP_3_TEMPLATE",
        display_name_ar="متابعة 3",
        reason_tag=None,
        template_type=TEMPLATE_TYPE_FOLLOWUP,
        default_content=_FOLLOWUP_3,
        enabled=True,
        future_meta_template_name="cartflow_followup_3_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=False,
        customization_plan_tier=PLAN_TIER_PRO,
    ),
    "VIP_ALERT_TEMPLATE": TemplateRegistryEntry(
        template_key="VIP_ALERT_TEMPLATE",
        display_name_ar="تنبيه VIP",
        reason_tag=None,
        template_type=TEMPLATE_TYPE_VIP,
        default_content=_VIP,
        enabled=True,
        future_meta_template_name="cartflow_vip_alert_v1",
        future_meta_status=META_STATUS_DRAFT,
        merchant_editable=False,
        customization_plan_tier=PLAN_TIER_PRO,
    ),
}

MERCHANT_EDITABLE_TEMPLATE_KEYS: frozenset[str] = frozenset(
    k for k, e in TEMPLATE_REGISTRY.items() if e.merchant_editable
)

REASON_TEMPLATE_KEYS: frozenset[str] = frozenset(
    e.template_key
    for e in TEMPLATE_REGISTRY.values()
    if e.template_type == TEMPLATE_TYPE_REASON
)


def get_registry_entry(template_key: str) -> Optional[TemplateRegistryEntry]:
    return TEMPLATE_REGISTRY.get((template_key or "").strip().upper())


def list_registry_entries() -> list[TemplateRegistryEntry]:
    return list(TEMPLATE_REGISTRY.values())


def list_registry_dicts() -> list[dict[str, Any]]:
    return [e.to_dict() for e in list_registry_entries()]
