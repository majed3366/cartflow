# -*- coding: utf-8 -*-
"""
Merchant Insight Layer V1 — governed Arabic insight templates.

Meaning-first phrasing: what the situation means for the merchant — never raw
data dumps, predictions, or business advice.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

# ---------------------------------------------------------------------------
# Insight type registry
# ---------------------------------------------------------------------------

INSIGHT_HEALTHY = "healthy"
INSIGHT_ATTENTION = "attention"
INSIGHT_RISK = "risk"
INSIGHT_OPPORTUNITY = "opportunity"
INSIGHT_WAITING = "waiting"
INSIGHT_AUTOMATIC_PROGRESS = "automatic_progress"
INSIGHT_MERCHANT_REQUIRED = "merchant_required"
INSIGHT_RECOVERY_WORKING = "recovery_working"
INSIGHT_STORE_READY = "store_ready"
INSIGHT_MONITORING_ONLY = "monitoring_only"

INSIGHT_TYPE_LABEL_AR: dict[str, str] = {
    INSIGHT_HEALTHY: "وضع مستقر",
    INSIGHT_ATTENTION: "يستحق انتباه",
    INSIGHT_RISK: "نمط يستحق المراقبة",
    INSIGHT_OPPORTUNITY: "فرصة للمتابعة",
    INSIGHT_WAITING: "بانتظار",
    INSIGHT_AUTOMATIC_PROGRESS: "تقدم تلقائي",
    INSIGHT_MERCHANT_REQUIRED: "يحتاج قرارك",
    INSIGHT_RECOVERY_WORKING: "الاسترداد يعمل",
    INSIGHT_STORE_READY: "المتجر جاهز",
    INSIGHT_MONITORING_ONLY: "مراقبة فقط",
}

# ---------------------------------------------------------------------------
# Carts — primary insight (meaning, not counts)
# ---------------------------------------------------------------------------

CARTS_INSIGHT_ALL_NEED_MERCHANT = "كل السلال الحالية بانتظار قرار منك."
CARTS_INSIGHT_SOME_NEED_MERCHANT = "بعض السلال تحتاج انتباهك الآن."
CARTS_INSIGHT_ONE_NEEDS_MERCHANT = "سلة واحدة تحتاج انتباهك الآن."
CARTS_INSIGHT_AUTOMATIC_UNDERWAY = "معظم السلال تتقدم تلقائياً — لا يلزم إجراء منك الآن."
CARTS_INSIGHT_NO_ACTION = "لا يلزم إجراء منك على السلال الآن."
CARTS_INSIGHT_MONITORING_EMPTY = "CartFlow يراقب المتجر — ستظهر الخلاصة عند توفر سلال."

# Carts — reason (because…)
CARTS_REASON_ALL_INTERVENTION = (
    "لأن الحالات الحالية لم تعد مناسبة للمتابعة التلقائية وحدها."
)
CARTS_REASON_PARTIAL_INTERVENTION = (
    "لأن {attention_count} من {monitored_count} سلة مراقَبة تحتاج تدخلاً."
)
CARTS_REASON_ONE_INTERVENTION = "لأن سلة واحدة مراقَبة تحتاج تدخلاً حالياً."
CARTS_REASON_AUTOMATIC = "لأن {automatic_count} سلة تتقدم دون حاجة لتدخلك."
CARTS_REASON_CALM = "لأن CartFlow يتابع السلال دون حاجة لتدخلك حالياً."
CARTS_REASON_MONITORING = "لأن لا توجد سلات نشطة كافية لاستنتاج وضع تشغيلي بعد."

# Carts — CartFlow action (delegation)
CARTS_ACTION_ALL_MERCHANT_NEXT_STEP = (
    "أكمل CartFlow المتابعة التلقائية، وينتظر قرارك قبل الخطوة التالية."
)
CARTS_ACTION_AUTO_DONE_MERCHANT_REMAINS = (
    "أكمل CartFlow العمل التلقائي. يبقى فقط القرارات التي تحتاجك."
)
CARTS_ACTION_WAITING_DECISION = "CartFlow ينتظر قرارك قبل المتابعة."
CARTS_ACTION_MONITORING_REPLIES = "CartFlow يراقب ردود العملاء ويُكمل المتابعة."
CARTS_ACTION_OBSERVING = "CartFlow يراقب سلوك العملاء في المتجر."
CARTS_ACTION_HOLDING = "CartFlow جاهز للمتابعة — لا يلزم إجراء الآن."

# ---------------------------------------------------------------------------
# Home (foundation stubs — governed templates)
# ---------------------------------------------------------------------------

HOME_INSIGHT_NO_URGENCY = "لا توجد أمور عاجلة في متجرك اليوم."
HOME_INSIGHT_NEEDS_LOOK = "هناك أمور تستحق نظرة سريعة اليوم."
HOME_REASON_CALM = "لأن ملخص اليوم لا يظهر حاجة فورية للتدخل."
HOME_REASON_ATTENTION = "لأن {attention_count} موضوعاً يحتاج نظرة منك."
HOME_ACTION_ROUTINE = "CartFlow يتابع المتجر وفق إعداداتك."

# ---------------------------------------------------------------------------
# Generic / cross-page
# ---------------------------------------------------------------------------

GENERIC_ACTION_MONITORING = "CartFlow يراقب الوضع ويُبلغك عند الحاجة."
GENERIC_INSIGHT_MONITORING = "CartFlow يتابع الوضع — لا يلزم إجراء الآن."
GENERIC_REASON_INSUFFICIENT = "لأن البيانات المتاحة لا تكفي لاستنتاج أوسع بعد."

InsightComposer = Callable[[Mapping[str, Any]], dict[str, Any]]
