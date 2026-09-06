# -*- coding: utf-8 -*-
"""
Commercial Mission — family profiles (config only) + shared lifecycle constants.

Lifecycle mechanics are family-agnostic (CDC). Family-specific data here is:
  A — evidence mapping (reason key)
  B — copy / action / confirm CTA
  C — metric / recheck / window / authority note

No family-specific state machine (D forbidden).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, Optional

MISSION_VERSION = "commercial_mission_v1"

# Material change threshold shared across share-based missions (C).
MATERIAL_SHARE_DELTA = 0.10


@dataclass(frozen=True)
class MissionFamilyProfile:
    """Bounded family contract — never a lifecycle SoT."""

    family: str
    reason: str  # A — hesitation reason key in COL evidence
    metric_key: str  # C
    measurement_window_days: int  # C
    execution_authority: str  # C (must be CDC-allowlisted)
    execution_confirm_note: str  # C — ref string at measurement start
    recheck_condition: str  # C
    action_summary_ar: str  # B — persisted on accept
    confirm_cta_ar: str  # B — merchant execution confirm label
    measuring_status_ar: str  # B


PROFILE_SHIPPING_FRICTION = MissionFamilyProfile(
    family="shipping_friction",
    reason="shipping",
    metric_key="hesitation_share",
    measurement_window_days=7,
    execution_authority="merchant_execution_confirm",
    execution_confirm_note="widget_shipping_cost_vs_delivery_clarified",
    recheck_condition="shipping_share_material_change_or_sample_ge_8",
    action_summary_ar=(
        "افصل في الودجيت بين تكلفة الشحن ومدة التوصيل — بلا خصم."
    ),
    confirm_cta_ar=(
        "أكّد: فصلت تكلفة الشحن عن مدة التوصيل في الودجيت"
    ),
    measuring_status_ar="تحت القياس — نافذة 7 أيام على حصة أسباب الشحن.",
)

PROFILE_PRICE_HESITATION = MissionFamilyProfile(
    family="price_hesitation",
    reason="price",
    metric_key="hesitation_share",
    measurement_window_days=7,
    execution_authority="merchant_execution_confirm",
    execution_confirm_note="product_page_offer_clarity_no_blanket_discount",
    recheck_condition="price_share_material_change_or_sample_ge_8",
    # COL/OGL: clarify value/offer — not discount / not price cut
    action_summary_ar="وضّح العرض في صفحة المنتج — بلا خصم عام.",
    confirm_cta_ar="أكّد: وضّحت العرض في صفحة المنتج بلا خصم عام",
    measuring_status_ar="تحت القياس — نافذة 7 أيام على حصة سبب السعر.",
)

PROFILE_PRODUCT_CONFIDENCE = MissionFamilyProfile(
    family="product_confidence",
    reason="quality",  # COL may also emit warranty:* keys; assert matches family prefix
    metric_key="hesitation_share",
    measurement_window_days=7,
    execution_authority="merchant_execution_confirm",
    execution_confirm_note="product_page_confidence_proof_clarified_no_discount",
    recheck_condition="product_confidence_share_material_change_or_sample_ge_8",
    action_summary_ar=(
        "وضّح إثباتات المنتج (مواصفات/ضمان/ما يشمله العرض) في صفحة المنتج والودجيت — بلا خصم."
    ),
    confirm_cta_ar="أكّد: وضّحت إثباتات ثقة المنتج في الصفحة والودجيت بلا خصم",
    measuring_status_ar="تحت القياس — نافذة 7 أيام على حصة أسباب ثقة المنتج.",
)

PROFILE_PRODUCT_OPPORTUNITY_FOCUS = MissionFamilyProfile(
    family="product_opportunity_focus",
    reason="product_trust",
    metric_key="hesitation_share",
    measurement_window_days=7,
    execution_authority="merchant_execution_confirm",
    execution_confirm_note="merchant_focused_product_trust_clarity_no_placement_no_ads",
    recheck_condition="product_trust_pool_share_material_change_or_sample_ge_8",
    action_summary_ar=(
        "ركّز على توضيح ثقة المنتج حيث تتركّز أسباب الجودة/الضمان — بلا خصم وبلا إعلان وبلا تغيير موضع عرض."
    ),
    confirm_cta_ar=(
        "أكّد: ركّزت توضيح ثقة المنتج على مواضع التردد المسجّلة — بلا خصم/إعلان/موضع"
    ),
    measuring_status_ar="تحت القياس — نافذة 7 أيام على حصة أسباب ثقة المنتج المجمّعة.",
)

MISSION_PROFILES: Dict[str, MissionFamilyProfile] = {
    PROFILE_SHIPPING_FRICTION.family: PROFILE_SHIPPING_FRICTION,
    PROFILE_PRICE_HESITATION.family: PROFILE_PRICE_HESITATION,
    PROFILE_PRODUCT_CONFIDENCE.family: PROFILE_PRODUCT_CONFIDENCE,
    PROFILE_PRODUCT_OPPORTUNITY_FOCUS.family: PROFILE_PRODUCT_OPPORTUNITY_FOCUS,
}

MISSION_FAMILIES: FrozenSet[str] = frozenset(MISSION_PROFILES.keys())

# --- V1 shipping aliases (backward compatible exports) ---
MISSION_FAMILY = PROFILE_SHIPPING_FRICTION.family
MISSION_REASON = PROFILE_SHIPPING_FRICTION.reason
METRIC_KEY = PROFILE_SHIPPING_FRICTION.metric_key
MEASUREMENT_WINDOW_DAYS = PROFILE_SHIPPING_FRICTION.measurement_window_days
EXECUTION_AUTHORITY = PROFILE_SHIPPING_FRICTION.execution_authority
RECHECK_CONDITION = PROFILE_SHIPPING_FRICTION.recheck_condition
ACTION_SUMMARY_AR = PROFILE_SHIPPING_FRICTION.action_summary_ar
EXECUTION_CONFIRM_NOTE = PROFILE_SHIPPING_FRICTION.execution_confirm_note


def get_mission_profile(family: str) -> Optional[MissionFamilyProfile]:
    return MISSION_PROFILES.get(str(family or "").strip())


def opportunity_key_for_store(
    store_slug: str,
    *,
    family: Optional[str] = None,
    reason: Optional[str] = None,
) -> str:
    """
    Build COL opportunity_id shape.

    Backward compatible: opportunity_key_for_store(slug) → shipping V1 key.
    """
    slug = str(store_slug or "").strip()[:191] or "store"
    fam = str(family or MISSION_FAMILY).strip() or "family"
    rsn = str(reason or MISSION_REASON).strip() or "reason"
    return f"col:{fam}:{rsn}:{slug}"


__all__ = [
    "ACTION_SUMMARY_AR",
    "EXECUTION_AUTHORITY",
    "EXECUTION_CONFIRM_NOTE",
    "MATERIAL_SHARE_DELTA",
    "MEASUREMENT_WINDOW_DAYS",
    "METRIC_KEY",
    "MISSION_FAMILIES",
    "MISSION_FAMILY",
    "MISSION_PROFILES",
    "MISSION_REASON",
    "MISSION_VERSION",
    "MissionFamilyProfile",
    "PROFILE_PRICE_HESITATION",
    "PROFILE_PRODUCT_CONFIDENCE",
    "PROFILE_PRODUCT_OPPORTUNITY_FOCUS",
    "PROFILE_SHIPPING_FRICTION",
    "RECHECK_CONDITION",
    "get_mission_profile",
    "opportunity_key_for_store",
]
