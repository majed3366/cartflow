/**
 * Merchant Product Language V1 — presentation-language layer (client).
 * Formats Merchant Insight output into merchant-facing narrative.
 * Legacy composePageNarrativeV1 remains for compatibility only.
 */
(function (global) {
  "use strict";

  var LANGUAGE_VERSION = "v1";
  var AUTHORITY = "merchant_product_language_v1";
  var INSIGHT_AUTHORITY = "merchant_insight_layer_v1";

  var CARTS_FALLBACK =
    "CartFlow يتابع السلال المتاحة، وستظهر الخلاصة عندما تتوفر بيانات كافية.";

  var PAGE_INTENT = {
    carts: "أي السلال تستحق الانتباه الآن؟",
  };

  var EVIDENCE_MONITORING = "CartFlow يراقب {monitored_count} سلة في متجرك.";
  var EVIDENCE_ATTENTION_ONE = "واحدة منها تحتاج انتباهك.";
  var EVIDENCE_ATTENTION_MANY = "{attention_count} منها تحتاج انتباهك.";
  var EVIDENCE_AUTOMATIC = "{automatic_count} تتقدم تلقائياً.";
  var EVIDENCE_ALL_NEED_DECISION_ONE =
    "الأدلة: سلة واحدة تحت المتابعة، وهي ضمن حالة تحتاج قرارك.";
  var EVIDENCE_ALL_NEED_DECISION_MANY =
    "الأدلة: {monitored_count} سلال تحت المتابعة، وكلها ضمن حالات تحتاج قرارك.";

  function norm(v) {
    return String(v == null ? "" : v).trim();
  }

  function deriveCountsFromRows(rows) {
    var counts = { all: 0, sent: 0, attention: 0, recovered: 0, nophone: 0 };
    if (!rows || !rows.length) return counts;
    counts.all = rows.length;
    var i;
    for (i = 0; i < rows.length; i++) {
      var row = rows[i] || {};
      var tabs = row.merchant_cart_visible_tabs;
      if (!Array.isArray(tabs)) tabs = [];
      if (!tabs.length) {
        var b = norm(row.merchant_cart_bucket || row.merchant_cart_primary_bucket).toLowerCase();
        if (b) tabs = [b];
      }
      var j;
      for (j = 0; j < tabs.length; j++) {
        var t = norm(tabs[j]).toLowerCase();
        if (t === "sent") counts.sent += 1;
        else if (t === "attention") counts.attention += 1;
        else if (t === "recovered") counts.recovered += 1;
        else if (t === "nophone") counts.nophone += 1;
      }
    }
    return counts;
  }

  function resolveFilterCounts(d, rows) {
    var store = (d && d.merchant_store_cart_counts) || {};
    if (store.active_total != null || store.waiting_total != null) {
      return {
        all: parseInt(store.active_total, 10) || 0,
        sent: parseInt(store.sent_total, 10) || 0,
        attention: parseInt(store.engaged_total, 10) || 0,
        recovered: parseInt(store.completed_total, 10) || 0,
        nophone: parseInt(store.no_phone_total, 10) || 0,
      };
    }
    var fc = (d && d.merchant_cart_filter_counts) || {};
    if (fc.all != null) return fc;
    return deriveCountsFromRows(rows);
  }

  function buildCartsEvidenceFromPayload(d, rows) {
    var evidence = {};
    var hasAny = false;
    rows = rows || [];
    var filterFc = resolveFilterCounts(d, rows);
    var storeFc = (d && d.merchant_store_cart_counts) || {};

    if (rows.length > 0) {
      evidence.monitored_count = rows.length;
      hasAny = true;
    } else if (filterFc.all != null && parseInt(filterFc.all, 10) > 0) {
      evidence.monitored_count = parseInt(filterFc.all, 10);
      hasAny = true;
    } else if (storeFc.active_total != null && parseInt(storeFc.active_total, 10) > 0) {
      evidence.monitored_count = parseInt(storeFc.active_total, 10);
      hasAny = true;
    }

    var attention = 0;
    var stories =
      (d && d.merchant_value_stories_v1 && d.merchant_value_stories_v1.stories) || [];
    var i;
    if (stories.length) {
      hasAny = true;
      for (i = 0; i < stories.length; i++) {
        if (stories[i] && stories[i].action_required) {
          attention += parseInt(stories[i].affected_carts || 0, 10);
        }
      }
    }

    var groups =
      (d && d.merchant_intelligence_store_v1 && d.merchant_intelligence_store_v1.groups) ||
      [];
    if (groups.length) hasAny = true;
    if (attention <= 0) {
      for (i = 0; i < groups.length; i++) {
        if (norm(groups[i] && groups[i].group_id) === "needs_merchant") {
          attention += parseInt((groups[i] && groups[i].affected_carts) || 0, 10);
        }
      }
    }

    if (hasAny && evidence.monitored_count != null) {
      evidence.attention_count = attention;
      evidence.automatic_count = Math.max(0, evidence.monitored_count - attention);
    }

    var sent = parseInt(filterFc.sent, 10) || parseInt(storeFc.sent_total, 10) || 0;
    if (attention > 0) evidence.cartflow_action_key = "waiting_merchant";
    else if (sent > 0) evidence.cartflow_action_key = "monitoring_replies";
    else if (hasAny) evidence.cartflow_action_key = "observing_behavior";

    evidence.has_sufficient_evidence = !!(
      hasAny &&
      (stories.length || groups.length || rows.length || evidence.monitored_count)
    );
    return evidence;
  }

  function hasCartsSufficientEvidence(d, rows) {
    return !!buildCartsEvidenceFromPayload(d, rows).has_sufficient_evidence;
  }

  function formatCartsEvidenceSummary(summary) {
    summary = summary || {};
    var monitored = summary.monitored_count;
    var attention = summary.attention_count;
    if (monitored != null && attention != null) {
      var mc = parseInt(monitored, 10);
      var ac = parseInt(attention, 10);
      if (mc > 0 && ac >= mc) {
        if (mc === 1) {
          return {
            lines_ar: [EVIDENCE_ALL_NEED_DECISION_ONE],
            source_refs: ["monitored_count", "attention_count"],
          };
        }
        return {
          lines_ar: [
            EVIDENCE_ALL_NEED_DECISION_MANY.replace("{monitored_count}", String(mc)),
          ],
          source_refs: ["monitored_count", "attention_count"],
        };
      }
    }
    var lines = [];
    var refs = [];
    if (summary.monitored_count != null) {
      var mc = parseInt(summary.monitored_count, 10);
      if (mc > 0) {
        lines.push(EVIDENCE_MONITORING.replace("{monitored_count}", String(mc)));
        refs.push("monitored_count");
      }
    }
    if (summary.attention_count != null) {
      var ac = parseInt(summary.attention_count, 10);
      if (ac === 1) {
        lines.push(EVIDENCE_ATTENTION_ONE);
        refs.push("attention_count");
      } else if (ac > 1) {
        lines.push(EVIDENCE_ATTENTION_MANY.replace("{attention_count}", String(ac)));
        refs.push("attention_count");
      }
    }
    if (summary.automatic_count != null) {
      var auto = parseInt(summary.automatic_count, 10);
      if (auto > 0) {
        lines.push(EVIDENCE_AUTOMATIC.replace("{automatic_count}", String(auto)));
        refs.push("automatic_count");
      }
    }
    return { lines_ar: lines, source_refs: refs };
  }

  function renderProductLanguageFromInsightV1(pageKey, insight) {
    var key = norm(pageKey).toLowerCase();
    if (key !== "carts" || !insight) return null;
    var refs = insight.source_refs || [];
    return {
      version: LANGUAGE_VERSION,
      authority: AUTHORITY,
      page_key: "carts",
      primary_question_ar: PAGE_INTENT.carts,
      insight_type: insight.insight_type,
      confidence: insight.confidence,
      sections: {
        headline: { text_ar: norm(insight.primary_insight), source_refs: refs },
        reason: { text_ar: norm(insight.reason), source_refs: refs },
        cartflow_action: {
          text_ar: norm(insight.cartflow_action),
          source_refs: ["cartflow_action"],
        },
        evidence: formatCartsEvidenceSummary(insight.evidence_summary),
      },
      composition_order: ["headline", "reason", "cartflow_action", "evidence"],
      source_insight: {
        version: insight.version,
        authority: insight.authority,
      },
      observability: {
        renders_from_insight: true,
        meaning_source: INSIGHT_AUTHORITY,
      },
    };
  }

  /** @deprecated Legacy — use renderProductLanguageFromInsightV1 after composePageInsightV1. */
  function composePageNarrativeV1(pageKey, evidence) {
    var key = norm(pageKey).toLowerCase();
    if (key !== "carts") return null;
    var mil = global.maInsightLayerV1;
    if (mil && typeof mil.composePageInsightV1 === "function") {
      var insight = mil.composePageInsightV1("carts", evidence);
      if (insight) return renderProductLanguageFromInsightV1("carts", insight);
    }
    return null;
  }

  function escHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderPageNarrativeHtml(narrative) {
    if (!narrative || !narrative.sections) return "";
    var sec = narrative.sections;
    var evidenceText = ((sec.evidence && sec.evidence.lines_ar) || []).join(" ");
    var parts =
      '<section class="ma-mpl-narrative" data-ma-mpl-page="carts">' +
      '<p class="ma-mpl-narrative__question">' +
      escHtml(narrative.primary_question_ar) +
      "</p>" +
      '<h2 class="ma-mpl-narrative__headline">' +
      escHtml(sec.headline && sec.headline.text_ar) +
      "</h2>";
    if (sec.reason && sec.reason.text_ar) {
      parts +=
        '<p class="ma-mpl-narrative__reason">' + escHtml(sec.reason.text_ar) + "</p>";
    }
    if (sec.cartflow_action && sec.cartflow_action.text_ar) {
      parts +=
        '<p class="ma-mpl-narrative__action">' +
        escHtml(sec.cartflow_action.text_ar) +
        "</p>";
    }
    if (evidenceText) {
      parts +=
        '<p class="ma-mpl-narrative__evidence">' + escHtml(evidenceText) + "</p>";
    }
    parts += "</section>";
    return parts;
  }

  function renderCartsNarrativeFallbackHtml() {
    return (
      '<section class="ma-mpl-narrative ma-mpl-narrative--fallback" data-ma-mpl-page="carts">' +
      '<p class="ma-mpl-narrative__fallback">' +
      escHtml(CARTS_FALLBACK) +
      "</p></section>"
    );
  }

  global.maProductLanguageV1 = {
    LANGUAGE_VERSION: LANGUAGE_VERSION,
    AUTHORITY: AUTHORITY,
    INSIGHT_AUTHORITY: INSIGHT_AUTHORITY,
    CARTS_FALLBACK: CARTS_FALLBACK,
    buildCartsEvidenceFromPayload: buildCartsEvidenceFromPayload,
    hasCartsSufficientEvidence: hasCartsSufficientEvidence,
    renderProductLanguageFromInsightV1: renderProductLanguageFromInsightV1,
    composePageNarrativeV1: composePageNarrativeV1,
    renderPageNarrativeHtml: renderPageNarrativeHtml,
    renderCartsNarrativeFallbackHtml: renderCartsNarrativeFallbackHtml,
  };
})(typeof window !== "undefined" ? window : this);
