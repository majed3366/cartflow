# -*- coding: utf-8 -*-
"""Products V1 — commercial product truth surface. Presentation over existing facts."""
from __future__ import annotations

from services.product_data.product_read_model_contract_v1 import (
    KNOWN_UNKNOWNS,
    PRODUCT_READ_MODEL_SCHEMA,
    PRODUCT_READ_MODEL_VERSION,
    PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED,
    VISIT_FIELD_CLASS_LAB_ONLY,
    VISIT_FIELD_NAME,
    visit_field_label,
)

LAYER_SCHEMA = "products_commercial_truth_v1"
LAYER_VERSION = "products_commercial_truth_v1_1"

READ_MODEL_OWNER = "product_read_model_contract_v1"
ATTENTION_OWNER = "products_commercial_truth_v1"
COMMERCIAL_STATUS_OWNER = "catalog_cdc_portfolio"

MAX_PRODUCTS = 40
MAX_CART_LINK_ROWS = 400
# One store-scoped CTE read. Lab visits ride the same statement (lab SQL only).
QUERY_COUNT_NORMAL = 1
QUERY_COUNT_LAB = 1

QUESTION_AR = "أي المنتجات تستحق انتباهي، وماذا يحدث تجارياً لكل منتج؟"
KICKER_AR = "حقيقة كل منتج من السلال والمشتريات وأسباب التردد — دون افتراض غير مثبت."
NOTE_AR = (
    "تعرض هذه الصفحة حقيقة كل منتج من السلال والمشتريات وأسباب التردد، "
    "دون افتراض سبب تجاري غير مثبت."
)

ATTENTION_NEEDS = "needs_attention"
ATTENTION_MONITORING = "monitoring"
ATTENTION_STABLE = "stable"
ATTENTION_INSUFFICIENT = "insufficient"

ATTENTION_LABEL_AR = {
    ATTENTION_NEEDS: "يحتاج انتباه",
    ATTENTION_MONITORING: "تحت المراقبة",
    ATTENTION_STABLE: "مستقر",
    ATTENTION_INSUFFICIENT: "بيانات غير كافية",
}

MISSING_NAME_TITLE_AR = "منتج بدون اسم في الكتالوج"
MISSING_NAME_IDENTITY_AR = "هوية الكتالوج غير مكتملة"
EXPOSURE_NOT_STORED = "NOT_STORED"
EXPOSURE_LAB_SYNTHETIC = "LAB_SYNTHETIC"
EXPOSURE_NONE_RECORDED = "NONE_RECORDED"

STORE_CONTEXT_BODY_AR = NOTE_AR
STORE_CONTEXT_CTA_AR = "افتح مساحة القرار"

PRESENTATION_STRONG = "strong_signal"
PRESENTATION_NEUTRAL = "neutral_truth"
PRESENTATION_INSUFFICIENT = "insufficient"
PRESENTATION_DEGRADED = "degraded_identity"

SIGNAL_HEADING_AR = "أبرز إشارة"
EXPOSURE_HEADING_AR = "بيانات الزيارة"
EXPOSURE_UNAVAILABLE_AR = "غير متاحة بعد"
LAB_VISIT_HEADING_AR = "زيارات تجريبية"
LAB_VISIT_NOT_REAL_AR = "ليست زيارات متجر حقيقية."

REASON_NOUN_AR = {
    "shipping": "الشحن",
    "delivery": "مدة التوصيل",
    "price": "السعر",
    "thinking": "التفكير",
    "quality": "الجودة",
    "warranty": "الضمان",
}

CARTS_WITHOUT_PURCHASE_AR = "توجد سلال لهذا المنتج دون شراء."
NO_RELIABLE_VISIT_AR = "لا تتوفر لدينا بيانات زيارة موثوقة لهذا المنتج."
LAB_VISIT_NOTE_AR = "زيارات تجريبية معلّمة — ليست زيارة متجر حقيقية."

FORBIDDEN_CAUSAL_AR = (
    "المنتج لا يبيع بسبب الشحن",
    "السعر مرتفع",
    "الإعلان ضعيف",
    "المنتج يحتاج إعلاناً",
    "السعر يمنع الشراء",
    "الشحن سبب خسارة المنتج",
    "المنتج ضعيف",
    "الإعلان لا يعمل",
    "12 customers abandoned this product because of shipping",
)

__all__ = [
    "ATTENTION_INSUFFICIENT",
    "ATTENTION_LABEL_AR",
    "ATTENTION_MONITORING",
    "ATTENTION_NEEDS",
    "ATTENTION_OWNER",
    "ATTENTION_STABLE",
    "CARTS_WITHOUT_PURCHASE_AR",
    "COMMERCIAL_STATUS_OWNER",
    "EXPOSURE_LAB_SYNTHETIC",
    "EXPOSURE_NONE_RECORDED",
    "EXPOSURE_NOT_STORED",
    "FORBIDDEN_CAUSAL_AR",
    "KICKER_AR",
    "KNOWN_UNKNOWNS",
    "LAB_VISIT_HEADING_AR",
    "LAB_VISIT_NOTE_AR",
    "LAB_VISIT_NOT_REAL_AR",
    "NOTE_AR",
    "PRESENTATION_DEGRADED",
    "PRESENTATION_INSUFFICIENT",
    "PRESENTATION_NEUTRAL",
    "PRESENTATION_STRONG",
    "SIGNAL_HEADING_AR",
    "EXPOSURE_HEADING_AR",
    "EXPOSURE_UNAVAILABLE_AR",
    "LAYER_SCHEMA",
    "LAYER_VERSION",
    "MAX_CART_LINK_ROWS",
    "MAX_PRODUCTS",
    "MISSING_NAME_IDENTITY_AR",
    "MISSING_NAME_TITLE_AR",
    "NO_RELIABLE_VISIT_AR",
    "PRODUCT_READ_MODEL_SCHEMA",
    "PRODUCT_READ_MODEL_VERSION",
    "PRODUCT_SCOPED_SHIPPING_CLAIM_ALLOWED",
    "QUERY_COUNT_LAB",
    "QUERY_COUNT_NORMAL",
    "QUESTION_AR",
    "READ_MODEL_OWNER",
    "REASON_NOUN_AR",
    "STORE_CONTEXT_BODY_AR",
    "STORE_CONTEXT_CTA_AR",
    "VISIT_FIELD_CLASS_LAB_ONLY",
    "VISIT_FIELD_NAME",
    "visit_field_label",
]
