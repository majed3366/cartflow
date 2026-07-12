/**
 * Cart Workspace Decision Card Presenter V1 — paint only.
 * Consumes DecisionRecord-shaped objects from WorkspaceProjection.
 * Must not evaluate admission matrix rows, ownership, admission, or provider state.
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function explanationOf(card) {
    var ex = card && card.explanation;
    if (!ex || typeof ex !== "object") {
      return {
        why_here: "",
        cartflow_did: "",
        why_stopped: "",
        expected_after: "",
      };
    }
    return ex;
  }

  /**
   * @param {object} card Decision card from projection zone_a|zone_b
   * @returns {string} HTML
   */
  function renderDecisionCardHtml(card) {
    if (!card || typeof card !== "object") return "";
    var id = esc(card.decision_id || "");
    var ex = explanationOf(card);
    var action = esc(card.required_action || "");
    var actionLabel = esc(card.action_label_ar || card.required_action || "");
    var secondary =
      action === "approve_discount"
        ? '<button type="button" class="cw-decision-card__secondary" data-cw-command="reject_exception" data-decision-id="' +
          id +
          '">رفض الاستثناء</button>'
        : "";
    return (
      '<article class="cw-decision-card" data-decision-id="' +
      id +
      '" data-decision-class="' +
      esc(card.decision_class || "") +
      '" data-required-action="' +
      action +
      '">' +
      '<dl class="cw-decision-card__fields">' +
      "<dt>لماذا ظهرت؟</dt><dd>" +
      esc(ex.why_here) +
      "</dd>" +
      "<dt>ماذا فعل CartFlow؟</dt><dd>" +
      esc(ex.cartflow_did) +
      "</dd>" +
      "<dt>لماذا توقفت الأتمتة؟</dt><dd>" +
      esc(ex.why_stopped) +
      "</dd>" +
      "<dt>ما المطلوب منك؟</dt><dd>" +
      actionLabel +
      "</dd>" +
      "<dt>ماذا بعد قرارك؟</dt><dd>" +
      esc(ex.expected_after) +
      "</dd>" +
      "</dl>" +
      '<div class="cw-decision-card__actions">' +
      '<button type="button" class="cw-decision-card__primary" data-cw-command="' +
      action +
      '" data-decision-id="' +
      id +
      '">' +
      actionLabel +
      "</button>" +
      secondary +
      "</div>" +
      "</article>"
    );
  }

  global.CartWorkspaceDecisionCardV1 = {
    renderDecisionCardHtml: renderDecisionCardHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
