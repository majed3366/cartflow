/**
 * Knowledge Layer v1 — merchant dashboard surface (read-only display).
 * Consumes GET /api/knowledge/report — no insight generation here.
 */
(function () {
  "use strict";

  var MAX_CARDS = 5;
  var MIN_CARDS = 3;

  var INSIGHT_PRIORITY = {
    hesitation_top_reason: 100,
    recovery_activity_summary: 90,
    recovery_bottleneck: 85,
    conversion_cart_to_purchase: 80,
    hesitation_distribution: 70,
    traffic_cart_demand_trend: 60,
    store_health_overview: 50,
    conversion_funnel_gaps: 40,
    conversion_no_carts: 30,
    recovery_insufficient_sample: 20,
    hesitation_insufficient_sample: 20,
    traffic_visitor_unavailable: 5,
  };

  var SEVERITY_RANK = { critical: 4, warning: 3, notice: 2, info: 1 };
  var CONF_RANK = { high: 4, medium: 3, low: 2, insufficient: 1 };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function insightScore(ins) {
    if (!ins) return 0;
    var base = INSIGHT_PRIORITY[ins.insight_key] || 25;
    var sev = SEVERITY_RANK[(ins.severity || "").toLowerCase()] || 1;
    var conf = CONF_RANK[(ins.confidence || "").toLowerCase()] || 1;
    if ((ins.confidence || "").toLowerCase() === "insufficient") {
      return base * 0.2;
    }
    return base + sev * 5 + conf * 3;
  }

  function pickTopInsights(insights) {
    var list = (insights || []).slice();
    if (!list.length) return [];
    list.sort(function (a, b) {
      return insightScore(b) - insightScore(a);
    });
    var actionable = list.filter(function (i) {
      return (i.confidence || "").toLowerCase() !== "insufficient";
    });
    var pool = actionable.length ? actionable : [];
    var n = Math.min(MAX_CARDS, Math.max(MIN_CARDS, pool.length));
    if (pool.length <= MAX_CARDS) {
      return pool;
    }
    return pool.slice(0, n);
  }

  function formatEvidence(ins) {
    var ev = ins.evidence || {};
    var key = ins.insight_key || "";

    if (key === "hesitation_top_reason" && ev.top_count != null && ev.hesitation_total != null) {
      return String(ev.top_count) + " حالة من أصل " + String(ev.hesitation_total) + " حالة تردد";
    }
    if (key === "hesitation_distribution" && ev.distribution) {
      var parts = [];
      Object.keys(ev.distribution).forEach(function (k) {
        parts.push(k + ": " + ev.distribution[k]);
      });
      if (parts.length) return parts.join(" · ");
    }
    if (key === "recovery_activity_summary") {
      return (
        "رسائل: " +
        String(ev.messages_sent != null ? ev.messages_sent : 0) +
        " · ردود: " +
        String(ev.replies != null ? ev.replies : 0) +
        " · مشتريات: " +
        String(ev.purchases != null ? ev.purchases : 0)
      );
    }
    if (key === "recovery_bottleneck" && ev.bottlenecks && ev.bottlenecks.length) {
      var b0 = ev.bottlenecks[0];
      return String(b0.count || 0) + " حدث — " + String(b0.label || b0.key || "");
    }
    if (key === "conversion_cart_to_purchase" && ev.cart_to_purchase_rate != null) {
      return (
        String(ev.purchase_count != null ? ev.purchase_count : 0) +
        " شراء من " +
        String(ev.cart_count != null ? ev.cart_count : ins.sample_size || 0) +
        " سلة"
      );
    }
    if (key === "traffic_cart_demand_trend") {
      return (
        "الفترة الحالية: " +
        String(ev.cart_count != null ? ev.cart_count : 0) +
        " · السابقة: " +
        String(ev.prev_cart_count != null ? ev.prev_cart_count : 0)
      );
    }
    if (ins.sample_size > 0) {
      return "عيّنة: " + String(ins.sample_size);
    }
    return "";
  }

  function renderEmptyState(host) {
    host.innerHTML =
      '<div class="ma-knowledge-empty">' +
      '<p class="ma-knowledge-empty-title">لا توجد بيانات كافية حالياً لإعطاء استنتاجات موثوقة.</p>' +
      '<p class="ma-knowledge-empty-sub">استمر في جمع النشاط وسيعرض CartFlow استنتاجات عندما تتوفر بيانات كافية.</p>' +
      "</div>";
  }

  function renderInsightCards(host, insights) {
    var cards = pickTopInsights(insights);
    if (!cards.length) {
      renderEmptyState(host);
      return;
    }
    host.innerHTML =
      '<div class="ma-knowledge-cards">' +
      cards
        .map(function (ins) {
          var evidence = formatEvidence(ins);
          var action = (ins.recommended_action_ar || "").trim();
          return (
            '<article class="ma-knowledge-insight" data-category="' +
            esc(ins.category || "") +
            '" data-severity="' +
            esc(ins.severity || "info") +
            '">' +
            '<div class="ma-knowledge-insight-body">' +
            '<h3 class="ma-knowledge-insight-title">' +
            esc(ins.title_ar || "") +
            "</h3>" +
            '<p class="ma-knowledge-insight-msg">' +
            esc(ins.message_ar || "") +
            "</p>" +
            "</div>" +
            '<div class="ma-knowledge-insight-foot">' +
            (evidence
              ? '<p class="ma-knowledge-insight-evidence">' + esc(evidence) + "</p>"
              : "") +
            (action
              ? '<p class="ma-knowledge-insight-action">' + esc(action) + "</p>"
              : "") +
            "</div>" +
            "</article>"
          );
        })
        .join("") +
      "</div>";
  }

  function applyKnowledgePayload(payload) {
    var root = byId("ma-knowledge-root");
    var host = byId("ma-knowledge-body");
    if (!root || !host) return;

    if (!payload || !payload.ok || !payload.insights) {
      renderEmptyState(host);
      return;
    }

    var actionable = (payload.insights || []).some(function (i) {
      return (i.confidence || "").toLowerCase() !== "insufficient";
    });
    if (!actionable) {
      renderEmptyState(host);
      return;
    }
    renderInsightCards(host, payload.insights);
  }

  function fetchKnowledgeReport() {
    var host = byId("ma-knowledge-body");
    if (!host) return Promise.resolve();

    var url = "/api/knowledge/report?window_days=7&_ts=" + Date.now();
    return fetch(url, { credentials: "same-origin", cache: "no-store" })
      .then(function (r) {
        if (!r.ok) {
          renderEmptyState(host);
          return null;
        }
        return r.json();
      })
      .then(function (d) {
        if (d) applyKnowledgePayload(d);
      })
      .catch(function () {
        renderEmptyState(host);
      });
  }

  function bootKnowledgeLayer() {
    if (!document.body || document.body.getAttribute("data-cf-merchant-app") !== "1") {
      return;
    }
    if (!byId("ma-knowledge-root")) return;
    fetchKnowledgeReport();
  }

  window.maApplyKnowledgePayload = applyKnowledgePayload;
  window.maFetchKnowledgeReport = fetchKnowledgeReport;

  window.__maKnowledgeTestHooks = {
    pickTopInsights: pickTopInsights,
    formatEvidence: formatEvidence,
    applyKnowledgePayload: applyKnowledgePayload,
    renderEmptyState: renderEmptyState,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootKnowledgeLayer);
  } else {
    bootKnowledgeLayer();
  }
})();
