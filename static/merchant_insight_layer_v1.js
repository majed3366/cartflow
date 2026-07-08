/**
 * Merchant Insight Layer V1 — client mirror (meaning before evidence).
 * Mirrors services/merchant_insight_layer_v1.py for page consumption without API changes.
 */
(function (global) {
  "use strict";

  var INSIGHT_VERSION = "v1";
  var AUTHORITY = "merchant_insight_layer_v1";

  var INSIGHT_HEALTHY = "healthy";
  var INSIGHT_ATTENTION = "attention";
  var INSIGHT_AUTOMATIC_PROGRESS = "automatic_progress";
  var INSIGHT_MERCHANT_REQUIRED = "merchant_required";
  var INSIGHT_MONITORING_ONLY = "monitoring_only";

  var CARTS_INSIGHT_ALL_NEED_MERCHANT = "كل السلال الحالية بانتظار قرار منك.";
  var CARTS_INSIGHT_SOME_NEED_MERCHANT = "بعض السلال تحتاج انتباهك الآن.";
  var CARTS_INSIGHT_ONE_NEEDS_MERCHANT = "سلة واحدة تحتاج انتباهك الآن.";
  var CARTS_INSIGHT_AUTOMATIC_UNDERWAY =
    "معظم السلال تتقدم تلقائياً — لا يلزم إجراء منك الآن.";
  var CARTS_INSIGHT_NO_ACTION = "لا يلزم إجراء منك على السلال الآن.";
  var CARTS_INSIGHT_MONITORING_EMPTY =
    "CartFlow يراقب المتجر — ستظهر الخلاصة عند توفر سلال.";

  var CARTS_REASON_ALL_INTERVENTION =
    "لأن الحالات الحالية لم تعد مناسبة للمتابعة التلقائية وحدها.";
  var CARTS_REASON_PARTIAL_INTERVENTION =
    "لأن {attention_count} من {monitored_count} سلة مراقَبة تحتاج تدخلاً.";
  var CARTS_REASON_ONE_INTERVENTION = "لأن سلة واحدة مراقَبة تحتاج تدخلاً حالياً.";
  var CARTS_REASON_AUTOMATIC = "لأن {automatic_count} سلة تتقدم دون حاجة لتدخلك.";
  var CARTS_REASON_CALM = "لأن CartFlow يتابع السلال دون حاجة لتدخلك حالياً.";
  var CARTS_REASON_MONITORING =
    "لأن لا توجد سلات نشطة كافية لاستنتاج وضع تشغيلي بعد.";

  var CARTS_ACTION_ALL_MERCHANT_NEXT_STEP =
    "أكمل CartFlow المتابعة التلقائية، وينتظر قرارك قبل الخطوة التالية.";
  var CARTS_ACTION_WAITING_DECISION = "CartFlow ينتظر قرارك قبل المتابعة.";
  var CARTS_ACTION_MONITORING_REPLIES = "CartFlow يراقب ردود العملاء ويُكمل المتابعة.";
  var CARTS_ACTION_OBSERVING = "CartFlow يراقب سلوك العملاء في المتجر.";
  var CARTS_ACTION_HOLDING = "CartFlow جاهز للمتابعة — لا يلزم إجراء الآن.";

  function norm(v) {
    return String(v == null ? "" : v).trim();
  }

  function intVal(v, fallback) {
    var n = parseInt(v, 10);
    return isNaN(n) ? fallback || 0 : n;
  }

  function refs() {
    var out = [];
    var i;
    for (i = 0; i < arguments.length; i++) {
      var k = norm(arguments[i]);
      if (k && out.indexOf(k) < 0) out.push(k);
    }
    return out.sort();
  }

  function cartsEvidenceSummary(evidence) {
    var summary = {};
    if (evidence.monitored_count != null) summary.monitored_count = intVal(evidence.monitored_count);
    if (evidence.attention_count != null) summary.attention_count = intVal(evidence.attention_count);
    if (evidence.automatic_count != null) summary.automatic_count = intVal(evidence.automatic_count);
    return summary;
  }

  function classifyCartsInsightType(evidence) {
    var monitored = intVal(evidence.monitored_count);
    var attention = intVal(evidence.attention_count);
    var automatic = intVal(evidence.automatic_count);
    if (monitored <= 0) return INSIGHT_MONITORING_ONLY;
    if (attention <= 0) {
      if (automatic > 0) return INSIGHT_AUTOMATIC_PROGRESS;
      return INSIGHT_HEALTHY;
    }
    if (attention >= monitored) return INSIGHT_MERCHANT_REQUIRED;
    return INSIGHT_ATTENTION;
  }

  function tpl(template, vars) {
    var out = template;
    vars = vars || {};
    Object.keys(vars).forEach(function (key) {
      out = out.replace("{" + key + "}", String(vars[key]));
    });
    return out;
  }

  function composeCartsInsightV1(evidence) {
    evidence = evidence || {};
    if (!evidence.has_sufficient_evidence) {
      return {
        insight_type: INSIGHT_MONITORING_ONLY,
        primary_insight: CARTS_INSIGHT_MONITORING_EMPTY,
        reason: CARTS_REASON_MONITORING,
        cartflow_action: CARTS_ACTION_OBSERVING,
        evidence_summary: {},
        source_refs: refs("has_sufficient_evidence"),
        confidence: "insufficient",
      };
    }

    var monitored = intVal(evidence.monitored_count);
    var attention = intVal(evidence.attention_count);
    var automatic = intVal(evidence.automatic_count);
    var insightType = classifyCartsInsightType(evidence);
    var primary;
    var reason;
    var action;
    var sourceRefs;

    if (insightType === INSIGHT_MERCHANT_REQUIRED) {
      primary = CARTS_INSIGHT_ALL_NEED_MERCHANT;
      reason = CARTS_REASON_ALL_INTERVENTION;
      action = CARTS_ACTION_ALL_MERCHANT_NEXT_STEP;
      sourceRefs = refs("monitored_count", "attention_count");
    } else if (insightType === INSIGHT_ATTENTION) {
      if (attention === 1) {
        primary = CARTS_INSIGHT_ONE_NEEDS_MERCHANT;
        reason = CARTS_REASON_ONE_INTERVENTION;
      } else {
        primary = CARTS_INSIGHT_SOME_NEED_MERCHANT;
        reason = tpl(CARTS_REASON_PARTIAL_INTERVENTION, {
          attention_count: attention,
          monitored_count: monitored,
        });
      }
      action = CARTS_ACTION_WAITING_DECISION;
      sourceRefs = refs("monitored_count", "attention_count");
    } else if (insightType === INSIGHT_AUTOMATIC_PROGRESS) {
      primary = CARTS_INSIGHT_AUTOMATIC_UNDERWAY;
      reason = tpl(CARTS_REASON_AUTOMATIC, { automatic_count: automatic });
      action =
        norm(evidence.cartflow_action_key) === "monitoring_replies"
          ? CARTS_ACTION_MONITORING_REPLIES
          : CARTS_ACTION_OBSERVING;
      sourceRefs = refs("monitored_count", "automatic_count", "cartflow_action_key");
    } else {
      primary = CARTS_INSIGHT_NO_ACTION;
      reason = CARTS_REASON_CALM;
      action = CARTS_ACTION_HOLDING;
      sourceRefs = refs("monitored_count", "attention_count");
    }

    return {
      insight_type: insightType,
      primary_insight: primary,
      reason: reason,
      cartflow_action: action.trim(),
      evidence_summary: cartsEvidenceSummary(evidence),
      source_refs: sourceRefs,
      confidence: monitored > 0 || evidence.attention_count != null ? "high" : "low",
    };
  }

  function composePageInsightV1(pageKey, evidence) {
    var key = norm(pageKey).toLowerCase();
    if (key !== "carts") return null;
    var block = composeCartsInsightV1(evidence);
    return {
      version: INSIGHT_VERSION,
      authority: AUTHORITY,
      page_key: "carts",
      insight_type: block.insight_type,
      primary_insight: block.primary_insight,
      reason: block.reason,
      cartflow_action: block.cartflow_action,
      evidence_summary: block.evidence_summary,
      source_refs: block.source_refs,
      confidence: block.confidence,
      composition_order: [
        "primary_insight",
        "reason",
        "cartflow_action",
        "evidence_summary",
      ],
    };
  }

  global.maInsightLayerV1 = {
    INSIGHT_VERSION: INSIGHT_VERSION,
    AUTHORITY: AUTHORITY,
    composePageInsightV1: composePageInsightV1,
  };
})(typeof window !== "undefined" ? window : this);
