/**
 * Merchant Pulse V1 — presentation only.
 * Renders merchant_pulse_v1 from GET /api/dashboard/summary.
 * No business logic, no calculations, no extra API calls.
 */
(function () {
  "use strict";

  var SLOT_KEYS = [
    "executive_brief",
    "decision_summary",
    "cartflow_progress",
    "merchant_decision",
  ];

  var SECTION_LABELS = {
    executive_brief: "ماذا يحدث",
    decision_summary: "هل تحتاج أن تتدخل",
    cartflow_progress: "ماذا أنجز CartFlow",
    merchant_decision: "قرارك التالي",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function uiFlagOn() {
    var body = document.body;
    if (!body) return false;
    return body.getAttribute("data-merchant-pulse-ui-v1") === "1";
  }

  function isSlot(obj) {
    return (
      obj &&
      typeof obj === "object" &&
      typeof obj.message === "string" &&
      typeof obj.status === "string"
    );
  }

  function isValidPulse(pulse) {
    if (!pulse || typeof pulse !== "object") return false;
    if (pulse.ok === false) return false;
    if (pulse.fork !== "leave" && pulse.fork !== "enter_work") return false;
    for (var i = 0; i < SLOT_KEYS.length; i++) {
      if (!isSlot(pulse[SLOT_KEYS[i]])) return false;
    }
    return true;
  }

  function statusClass(status) {
    var s = String(status || "unknown").trim().toLowerCase();
    if (
      s === "loading" ||
      s === "healthy" ||
      s === "no_action" ||
      s === "unknown" ||
      s === "require_action"
    ) {
      return "ma-pulse-slot--" + s;
    }
    return "ma-pulse-slot--unknown";
  }

  function renderSlot(key, slot) {
    var label = SECTION_LABELS[key] || key;
    var conf = String(slot.confidence || "").trim();
    var confHtml = conf
      ? '<p class="ma-pulse-slot__confidence">' + esc(conf) + "</p>"
      : "";
    return (
      '<section class="ma-pulse-slot ' +
      statusClass(slot.status) +
      '" data-pulse-slot="' +
      esc(key) +
      '" data-pulse-status="' +
      esc(slot.status) +
      '">' +
      '<p class="ma-pulse-slot__label">' +
      esc(label) +
      "</p>" +
      '<p class="ma-pulse-slot__message">' +
      esc(slot.message || "—") +
      "</p>" +
      confHtml +
      "</section>"
    );
  }

  function renderCta(pulse) {
    if (pulse.fork !== "enter_work") return "";
    var decision = pulse.merchant_decision || {};
    var label = String(decision.message || "").trim() || "متابعة السلال";
    return (
      '<div class="ma-pulse-cta" data-pulse-cta="enter_work">' +
      '<button type="button" class="ma-pulse-cta__btn" id="ma-pulse-enter-work-btn">' +
      esc(label) +
      "</button>" +
      "</div>"
    );
  }

  function bindCta() {
    var btn = byId("ma-pulse-enter-work-btn");
    if (!btn || btn.getAttribute("data-bound") === "1") return;
    btn.setAttribute("data-bound", "1");
    btn.addEventListener("click", function () {
      if (typeof window.goTo === "function") {
        window.goTo("carts");
        return;
      }
      window.location.hash = "carts";
    });
  }

  function renderPulseHtml(pulse) {
    var html =
      '<div class="ma-pulse-v1" data-pulse-fork="' +
      esc(pulse.fork) +
      '" data-pulse-status="' +
      esc(pulse.status || "") +
      '">';
    for (var i = 0; i < SLOT_KEYS.length; i++) {
      var key = SLOT_KEYS[i];
      html += renderSlot(key, pulse[key]);
    }
    html += renderCta(pulse);
    html += "</div>";
    return html;
  }

  /**
   * @param {object} summary — full dashboard summary payload
   * @returns {boolean} true if Pulse was rendered; false → caller must keep Home
   */
  function applyMerchantPulseV1(summary) {
    var root = byId("ma-home-experience-root");
    if (!root) return false;
    if (!uiFlagOn()) return false;
    var pulse = summary && summary.merchant_pulse_v1;
    if (!isValidPulse(pulse)) return false;

    root.classList.remove(
      "ma-home-experience--loading",
      "ma-home-experience--calm",
      "ma-home-experience--legacy",
      "ma-pe-v2-home"
    );
    root.classList.add("ma-pulse-v1-root");
    root.setAttribute("aria-label", "نبض المتجر");
    root.innerHTML = renderPulseHtml(pulse);
    bindCta();
    return true;
  }

  window.maApplyMerchantPulseV1 = applyMerchantPulseV1;
  window.maMerchantPulseV1IsValid = isValidPulse;
})();
