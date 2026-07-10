/**
 * Knowledge Layer — merchant dashboard surface (routing consumer).
 * Consumes GET /api/knowledge/report → knowledge_layer_projection_v1.display_cards.
 * Routing + projection own selection, ranking, aggregation, and OIA copy.
 * This module owns presentation, layout, and interaction only.
 */
(function () {
  "use strict";

  var OIA_LABEL_OBSERVATION = "الملاحظة";
  var OIA_LABEL_IMPACT = "التأثير";
  var OIA_LABEL_ACTION = "الإجراء المقترح";

  var lastEvidenceRegistry = null;

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s == null ? "" : String(s);
    return d.innerHTML;
  }

  function evidenceLabelForCard(card) {
    if (card && card.evidence_label_ar) {
      return String(card.evidence_label_ar).trim();
    }
    var eid = card && card.evidence_id ? String(card.evidence_id).trim() : "";
    if (eid && lastEvidenceRegistry && lastEvidenceRegistry.entries) {
      var entries = lastEvidenceRegistry.entries;
      for (var i = 0; i < entries.length; i++) {
        if (entries[i] && entries[i].evidence_id === eid) {
          return String(entries[i].label_ar || "").trim();
        }
      }
    }
    return "—";
  }

  function renderKnowledgeProofMeta(card) {
    var sourceLabel = evidenceLabelForCard(card);
    // confidence (high/medium/low/unknown) is internal metadata — never render.
    return (
      '<div class="ma-knowledge-proof-meta" aria-label="دليل الاستنتاج">' +
      '<span class="ma-knowledge-proof-evidence-label">المصدر:</span> ' +
      '<span class="ma-knowledge-proof-evidence-value">' +
      esc(sourceLabel) +
      "</span>" +
      "</div>"
    );
  }

  function renderOIABlock(label, text) {
    if (!text) return "";
    return (
      '<div class="ma-knowledge-oia-block">' +
      '<p class="ma-knowledge-oia-label">' +
      esc(label) +
      "</p>" +
      '<p class="ma-knowledge-oia-text">' +
      esc(text) +
      "</p>" +
      "</div>"
    );
  }

  function renderDisplayCard(card) {
    return (
      '<article class="ma-knowledge-insight" data-insight-key="' +
      esc(card.insight_key || "") +
      '" data-category="' +
      esc(card.category || "") +
      '" data-severity="' +
      esc(card.severity || "info") +
      '" data-source-knowledge-id="' +
      esc(card.source_knowledge_id || "") +
      '" data-routing-knowledge-id="' +
      esc(card.routing_knowledge_id || "") +
      '">' +
      '<h3 class="ma-knowledge-insight-title">' +
      esc(card.title_ar || "") +
      "</h3>" +
      '<div class="ma-knowledge-oia-stack">' +
      renderOIABlock(OIA_LABEL_OBSERVATION, card.observation_ar) +
      renderOIABlock(OIA_LABEL_IMPACT, card.impact_ar) +
      renderOIABlock(OIA_LABEL_ACTION, card.action_ar) +
      "</div>" +
      renderKnowledgeProofMeta(card) +
      "</article>"
    );
  }

  function renderEmptyState(host) {
    host.innerHTML =
      '<div class="ma-knowledge-empty">' +
      '<p class="ma-knowledge-empty-title">لا توجد بيانات كافية حالياً لإعطاء استنتاجات موثوقة.</p>' +
      '<p class="ma-knowledge-empty-sub">استمر في جمع النشاط وسيعرض CartFlow استنتاجات عندما تتوفر بيانات كافية.</p>' +
      "</div>";
  }

  function renderDisplayCards(host, cards) {
    if (!cards || !cards.length) {
      renderEmptyState(host);
      return;
    }
    host.innerHTML =
      '<div class="ma-knowledge-cards">' +
      cards.map(renderDisplayCard).join("") +
      "</div>";
  }

  function applyKnowledgePayload(payload) {
    var root = byId("ma-knowledge-root");
    var host = byId("ma-knowledge-body");
    if (!root || !host) return;

    lastEvidenceRegistry =
      (payload && payload.merchant_evidence_registry_v1) || null;

    if (!payload || !payload.ok) {
      renderEmptyState(host);
      return;
    }

    var projection = payload.knowledge_layer_projection_v1;
    if (!projection || !Array.isArray(projection.display_cards)) {
      renderEmptyState(host);
      return;
    }

    renderDisplayCards(host, projection.display_cards);
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
    applyKnowledgePayload: applyKnowledgePayload,
    renderEmptyState: renderEmptyState,
    renderDisplayCard: renderDisplayCard,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootKnowledgeLayer);
  } else {
    bootKnowledgeLayer();
  }
})();
