# -*- coding: utf-8 -*-
"""Revenue Intelligence Model V1 — contracts (lab layer on RRV)."""
from __future__ import annotations

INTELLIGENCE_VERSION_V1 = "revenue_intelligence_model_v1"

# Merchant-facing priority tiers (minimal set)
TIER_DECIDE_NOW = "decide_now"
TIER_IMPORTANT = "important"
TIER_MEASURING = "measuring"
TIER_IN_PROGRESS = "in_progress"
TIER_MONITOR = "monitor"
TIER_INSUFFICIENT = "insufficient"
TIER_COMPLETED = "completed"

TIER_LABEL_AR = {
    TIER_DECIDE_NOW: "تحتاج قرارك الآن",
    TIER_IMPORTANT: "فرصة مهمة",
    TIER_MEASURING: "تحت القياس",
    TIER_IN_PROGRESS: "قيد التنفيذ",
    TIER_MONITOR: "للمراقبة",
    TIER_INSUFFICIENT: "الدليل غير كافٍ",
    TIER_COMPLETED: "مكتملة",
}

# Commercial objectives (bounded)
OBJ_GROW_REVENUE = "GROW_REVENUE"
OBJ_PROTECT_REVENUE = "PROTECT_REVENUE"
OBJ_INCREASE_CONVERSION = "INCREASE_CONVERSION"
OBJ_IMPROVE_CUSTOMER_VALUE = "IMPROVE_CUSTOMER_VALUE"
OBJ_IMPROVE_DISCOVERY = "IMPROVE_DISCOVERY"
OBJ_TEST_ACQUISITION = "TEST_ACQUISITION"
OBJ_PROTECT_MARGIN = "PROTECT_MARGIN"

OBJECTIVE_LABEL_AR = {
    OBJ_GROW_REVENUE: "تنمية الإيراد",
    OBJ_PROTECT_REVENUE: "حماية الإيراد",
    OBJ_INCREASE_CONVERSION: "رفع التحويل إلى شراء",
    OBJ_IMPROVE_CUSTOMER_VALUE: "رفع قيمة العميل",
    OBJ_IMPROVE_DISCOVERY: "تحسين الاكتشاف",
    OBJ_TEST_ACQUISITION: "اختبار اكتساب",
    OBJ_PROTECT_MARGIN: "حماية المساهمة / الهامش المحاكى",
}

# Banned primary abbreviations on merchant surfaces
BANNED_PRIMARY_ABBREVIATIONS = ("ATC", "AOV", "CTR", "CVR", "ROAS", "CAC")

__all__ = [
    "BANNED_PRIMARY_ABBREVIATIONS",
    "INTELLIGENCE_VERSION_V1",
    "OBJECTIVE_LABEL_AR",
    "OBJ_GROW_REVENUE",
    "OBJ_IMPROVE_CUSTOMER_VALUE",
    "OBJ_IMPROVE_DISCOVERY",
    "OBJ_INCREASE_CONVERSION",
    "OBJ_PROTECT_MARGIN",
    "OBJ_PROTECT_REVENUE",
    "OBJ_TEST_ACQUISITION",
    "TIER_COMPLETED",
    "TIER_DECIDE_NOW",
    "TIER_IMPORTANT",
    "TIER_INSUFFICIENT",
    "TIER_IN_PROGRESS",
    "TIER_LABEL_AR",
    "TIER_MEASURING",
    "TIER_MONITOR",
]
