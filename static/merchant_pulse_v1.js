/**
 * Merchant Pulse V1 — Home Experience Sprint 1 (presentation only).
 *
 * Home reference layout:
 *   Hero (executive_brief story) → max 3 decision cards → optional Work CTA
 *
 * Cards never repeat Hero. Empty / placeholder / duplicate cards are omitted.
 * Payload shape unchanged — no new architecture.
 */
(function () {
  "use strict";

  var SLOT_KEYS = [
    "executive_brief",
    "decision_summary",
    "cartflow_progress",
    "merchant_decision",
  ];

  /** Home Sprint 1 — cards only (Hero owns executive_brief). Max three. */
  var HOME_CARD_SPECS = [
    { key: "decision_summary", label: "هل تحتاجني؟" },
    { key: "cartflow_progress", label: "ماذا تعلمنا؟" },
    { key: "merchant_decision", label: "قرارك التالي" },
  ];

  var HOME_PAGE_PURPOSE = "ماذا حدث أثناء غيابك؟";
  var ENTER_WORK_CTA_LABEL = "افتح السلال";

  var PLACEHOLDER_RE =
    /^(—|–|-|…|\.{1,3}|جارٍ التحديث…?|جاري التحديث…?)$/;

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

  function normMsg(s) {
    return String(s || "")
      .replace(/\s+/g, " ")
      .trim();
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

  function isPlaceholderMessage(msg) {
    var m = normMsg(msg);
    if (!m) return true;
    return PLACEHOLDER_RE.test(m);
  }

  function isTechnicalWording(msg) {
    var m = normMsg(msg);
    if (!m) return false;
    // Internal / process wording must never surface on Home.
    return (
      m.indexOf("اكتمل مسار") !== -1 ||
      m.indexOf("مسار استرجاع") !== -1 ||
      m.indexOf("recovery_") !== -1 ||
      m.indexOf("signal") !== -1
    );
  }

  function cardIsUseful(slot, heroMsg, seenMsgs) {
    if (!isSlot(slot)) return false;
    if (slot.hidden === true) return false;
    var msg = normMsg(slot.message);
    if (isPlaceholderMessage(msg)) return false;
    if (isTechnicalWording(msg)) return false;
    if (heroMsg && msg === heroMsg) return false;
    if (seenMsgs[msg]) return false;
    return true;
  }

  function renderHero(brief) {
    var msg = normMsg(brief && brief.message);
    if (isPlaceholderMessage(msg) || isTechnicalWording(msg)) {
      msg = "لم يحدث ما يحتاج انتباهك منذ آخر زيارة.";
    }
    var st = (brief && brief.status) || "healthy";
    return (
      '<header class="ma-pulse-hero ' +
      statusClass(st) +
      '" data-pulse-hero="executive_brief" data-pulse-status="' +
      esc(st) +
      '">' +
      '<p class="ma-pulse-hero__story">' +
      esc(msg) +
      "</p>" +
      "</header>"
    );
  }

  function renderCard(key, label, slot) {
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
      esc(normMsg(slot.message)) +
      "</p>" +
      "</section>"
    );
  }

  function renderCards(pulse, heroMsg) {
    var html = "";
    var count = 0;
    var seen = {};
    if (heroMsg) seen[heroMsg] = true;

    for (var i = 0; i < HOME_CARD_SPECS.length; i++) {
      if (count >= 3) break;
      var spec = HOME_CARD_SPECS[i];
      var slot = pulse[spec.key];
      if (!cardIsUseful(slot, heroMsg, seen)) continue;
      var msg = normMsg(slot.message);
      seen[msg] = true;
      html += renderCard(spec.key, spec.label, slot);
      count += 1;
    }
    if (!html) return "";
    return '<div class="ma-pulse-cards" data-pulse-cards="' + count + '">' + html + "</div>";
  }

  function renderCta(pulse) {
    if (pulse.fork !== "enter_work") return "";
    return (
      '<div class="ma-pulse-cta" data-pulse-cta="enter_work">' +
      '<button type="button" class="ma-pulse-cta__btn" id="ma-pulse-enter-work-btn">' +
      esc(ENTER_WORK_CTA_LABEL) +
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

  function syncHomePageChrome(heroMsg) {
    var pp = byId("pagePurpose");
    if (pp) {
      pp.textContent = HOME_PAGE_PURPOSE;
      pp.hidden = false;
    }
    var pt = byId("pageTitle");
    if (pt && !normMsg(pt.textContent)) {
      pt.textContent = "الرئيسية";
    }
    // Supporting global subtitle must not repeat the hero story.
    var ps = byId("pageSub");
    if (ps) {
      var sub = normMsg(ps.textContent);
      if (!sub || (heroMsg && sub === heroMsg) || isPlaceholderMessage(sub)) {
        ps.textContent = "";
        ps.hidden = true;
      }
    }
  }

  function renderPulseHtml(pulse) {
    var brief = pulse.executive_brief || {};
    var heroMsg = normMsg(brief.message);
    if (isPlaceholderMessage(heroMsg) || isTechnicalWording(heroMsg)) {
      heroMsg = "لم يحدث ما يحتاج انتباهك منذ آخر زيارة.";
    }
    return (
      '<div class="ma-pulse-v1 ma-pulse-v1--home-ref" data-pulse-fork="' +
      esc(pulse.fork) +
      '" data-pulse-status="' +
      esc(pulse.status || "") +
      '" data-home-sprint="1">' +
      renderHero(brief) +
      renderCards(pulse, heroMsg) +
      renderCta(pulse) +
      "</div>"
    );
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

    var brief = pulse.executive_brief || {};
    var heroMsg = normMsg(brief.message);
    if (isPlaceholderMessage(heroMsg) || isTechnicalWording(heroMsg)) {
      heroMsg = "لم يحدث ما يحتاج انتباهك منذ آخر زيارة.";
    }

    root.classList.remove(
      "ma-home-experience--loading",
      "ma-home-experience--calm",
      "ma-home-experience--legacy",
      "ma-pe-v2-home"
    );
    root.classList.add("ma-pulse-v1-root", "ma-pulse-v1-root--home-ref");
    root.setAttribute("aria-label", "ماذا حدث أثناء غيابك");
    root.innerHTML = renderPulseHtml(pulse);
    syncHomePageChrome(heroMsg);
    bindCta();
    return true;
  }

  window.maApplyMerchantPulseV1 = applyMerchantPulseV1;
  window.maMerchantPulseV1IsValid = isValidPulse;
})();
