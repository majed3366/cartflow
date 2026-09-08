# -*- coding: utf-8 -*-
"""Live Decision Hierarchy & Portfolio Visibility V1 — presentation labels only."""
from __future__ import annotations

LAYER_VERSION = "live_decision_hierarchy_v1"
LAYER_SCHEMA = "live_decision_hierarchy_v1"

COMMERCIAL_STATUS_OWNER = "catalog_cdc_portfolio"
OPERATIONAL_GUIDANCE_OWNER = "ogl"

LABEL_NOW_AR = "مهمتك الآن"
LABEL_MONITORING_AR = "تحت المراقبة"
LABEL_NEXT_AR = "المهمة التجارية التالية"
LABEL_LATER_AR = "لاحقاً"
LABEL_WHY_NOW_AR = "لماذا هذه المهمة الآن؟"
LABEL_DECISION_AR = "القرار"
LABEL_DONT_AR = "لا تفعل هذا الآن"
LABEL_RECHECK_AR = "سنغيّر رأينا إذا..."
LABEL_EXECUTION_AR = "تنفيذ المهمة"
LABEL_HOME_QUESTION_AR = "ما الذي يستحق انتباهي الآن؟"
CTA_OPEN_DECISION_AR = "افتح القرار"

SIDEBAR_NOW_AR = "الآن"
SIDEBAR_IN_PROGRESS_AR = "قيد التنفيذ / القياس"
SIDEBAR_ACTION_CHOSEN_AR = "قيد التنفيذ"
SIDEBAR_MEASURING_AR = "قيد القياس"
SIDEBAR_REVIEW_AR = "للمراجعة"
SIDEBAR_LATER_AR = "لاحقاً"
SIDEBAR_COMPLETED_AR = "مكتملة"
SUBSTATE_AWAITING_EXEC_AR = "بانتظار التنفيذ"
SUBSTATE_MEASURING_AR = "قيد القياس"

JOURNEY_ACCEPT_AR = "اعتمد هذه المهمة"
JOURNEY_EXECUTE_AR = "نفّذ المهمة"
JOURNEY_CONFIRM_AR = "أكّد إتمام التنفيذ"
JOURNEY_MEASURE_AR = "يبدأ القياس"
JOURNEY_RECHECK_AR = "إعادة المراجعة"

FORBIDDEN_INSUFFICIENCY_AR = (
    "يحتاج مزيداً من الأدلة",
    "يحتاج مزيدًا من الأدلة",
    "الأدلة ما زالت محدودة",
    "الأدلة ما زالت محدودة.",
)

AMBIGUOUS_NEXT_LABEL_AR = "بعده"

FAMILY_NOUN_AR = {
    "shipping_friction": "الشحن",
    "price_hesitation": "السعر",
    "product_confidence": "ثقة المنتج",
    "product_opportunity_focus": "ثقة المنتج",
}

PORTFOLIO_STATE_CURRENT = "CURRENT"
PORTFOLIO_STATE_SAFE_SECONDARY = "SAFE_SECONDARY"
PORTFOLIO_STATE_NEXT_MISSION = "NEXT_MISSION"
PORTFOLIO_STATE_DEFERRED = "DEFERRED"
PORTFOLIO_STATE_SUPPRESSED = "SUPPRESSED"

__all__ = [
    "AMBIGUOUS_NEXT_LABEL_AR",
    "COMMERCIAL_STATUS_OWNER",
    "CTA_OPEN_DECISION_AR",
    "FAMILY_NOUN_AR",
    "FORBIDDEN_INSUFFICIENCY_AR",
    "LABEL_DECISION_AR",
    "LABEL_DONT_AR",
    "LABEL_EXECUTION_AR",
    "LABEL_HOME_QUESTION_AR",
    "LABEL_LATER_AR",
    "LABEL_MONITORING_AR",
    "LABEL_NEXT_AR",
    "LABEL_NOW_AR",
    "LABEL_RECHECK_AR",
    "LABEL_WHY_NOW_AR",
    "LAYER_SCHEMA",
    "LAYER_VERSION",
    "OPERATIONAL_GUIDANCE_OWNER",
    "PORTFOLIO_STATE_CURRENT",
    "PORTFOLIO_STATE_DEFERRED",
    "PORTFOLIO_STATE_NEXT_MISSION",
    "PORTFOLIO_STATE_SAFE_SECONDARY",
    "PORTFOLIO_STATE_SUPPRESSED",
    "JOURNEY_ACCEPT_AR",
    "JOURNEY_CONFIRM_AR",
    "JOURNEY_EXECUTE_AR",
    "JOURNEY_MEASURE_AR",
    "JOURNEY_RECHECK_AR",
    "SIDEBAR_ACTION_CHOSEN_AR",
    "SIDEBAR_COMPLETED_AR",
    "SIDEBAR_IN_PROGRESS_AR",
    "SIDEBAR_LATER_AR",
    "SIDEBAR_MEASURING_AR",
    "SIDEBAR_NOW_AR",
    "SIDEBAR_REVIEW_AR",
    "SUBSTATE_AWAITING_EXEC_AR",
    "SUBSTATE_MEASURING_AR",
]
