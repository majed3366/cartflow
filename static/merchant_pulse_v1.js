/**
 * Merchant Pulse V1 — Home Experience Sprint 1.1 (presentation only).
 *
 * Reuses the shared global Hero (#ma-page-hero-global.ma-vi-hero) —
 * same component as Messages / WhatsApp. Pulse fills content only.
 * Cards never repeat the Hero story.
 */
(function () {
  "use strict";

  var SLOT_KEYS = [
    "executive_brief",
    "decision_summary",
    "cartflow_progress",
    "merchant_decision",
  ];

  /** Decision cards only — Hero story lives in the shared page Hero. */
  var HOME_CARD_SPECS = [
    { key: "decision_summary", label: "هل تحتاجني؟" },
    { key: "cartflow_progress", label: "ماذا تعلمنا؟" },
    { key: "merchant_decision", label: "قرارك التالي" },
  ];

  var HOME_HERO_QUESTION = "ماذا حدث أثناء غيابك؟";
  var HOME_STORY_FALLBACK = "لم يحدث ما يحتاج انتباهك منذ آخر زيارة.";
  var HOME_HERO_SUPPORT_RECOVERED =
    "CartFlow تابع عمليات الاسترداد أثناء غيابك.";
  var ENTER_WORK_CTA_LABEL = "افتح السلال";
  var lastHomeHeroStory = HOME_STORY_FALLBACK;

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
    return (
      m.indexOf("اكتمل مسار") !== -1 ||
      m.indexOf("مسار استرجاع") !== -1 ||
      m.indexOf("recovery_") !== -1 ||
      m.indexOf("signal") !== -1
    );
  }

  function resolveHeroStory(brief) {
    var msg = normMsg(brief && brief.message);
    if (isPlaceholderMessage(msg) || isTechnicalWording(msg)) {
      return HOME_STORY_FALLBACK;
    }
    return msg;
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

  /**
   * Fill the shared global Hero (Messages / WhatsApp component).
   * Same slots only — no Home-specific Hero markup or CSS.
   * Title = Home hero title; purpose = Pulse story (body weight);
   * pageSub = framing question (shared caption slot).
   */
  /**
   * Hero Experience Sprint 2.1 — Question → Answer → Optional.
   * Eyebrow question first; story is the large visual focus.
   */
  function homeHeroSupport(storyMsg) {
    var s = normMsg(storyMsg);
    if (/تم استرداد|عمليات شراء|عملية شراء/.test(s)) {
      return HOME_HERO_SUPPORT_RECOVERED;
    }
    return "";
  }

  function fillSharedHero(storyMsg) {
    lastHomeHeroStory = normMsg(storyMsg) || HOME_STORY_FALLBACK;
    var pageKey =
      (document.body && document.body.getAttribute("data-ma-page")) || "";
    var homePage = byId("page-home");
    var homeActive =
      pageKey === "home" ||
      (homePage && homePage.classList.contains("active"));
    // Never clobber Carts/Messages while Home Pulse arrives late.
    if (!homeActive) return;
    var hero = byId("ma-page-hero-global");
    if (hero) {
      hero.removeAttribute("data-shared-hero-carts");
    }
    if (document.body) {
      document.body.setAttribute("data-ma-page", "home");
    }
    var payload = {
      question: HOME_HERO_QUESTION,
      story: lastHomeHeroStory,
      support: homeHeroSupport(lastHomeHeroStory),
    };
    if (typeof window.maFillQuestionFirstHero === "function") {
      window.maFillQuestionFirstHero(payload);
      return;
    }
    // Fallback if app helper not yet available
    if (hero) {
      hero.classList.add("ma-vi-hero");
      hero.removeAttribute("hidden");
      hero.setAttribute("data-hero-narrative", "question-first");
    }
    var pt = byId("pageTitle");
    if (pt) pt.textContent = payload.story;
    var pp = byId("pagePurpose");
    if (pp) {
      if (payload.support) {
        pp.textContent = payload.support;
        pp.hidden = false;
      } else {
        pp.textContent = "";
        pp.hidden = true;
      }
    }
    var ps = byId("pageSub");
    if (ps) {
      ps.textContent = payload.question;
      ps.hidden = false;
      ps.classList.add("ma-vi-hero__summary");
    }
  }

  /** Re-assert Home shared Hero after other pages may have filled it. */
  function refillHomeSharedHero() {
    var root = byId("ma-home-experience-root");
    if (!root || !root.querySelector('[data-shared-hero="1"]')) return false;
    fillSharedHero(lastHomeHeroStory);
    return true;
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
    return (
      '<div class="ma-pulse-cards" data-pulse-cards="' +
      count +
      '">' +
      html +
      "</div>"
    );
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

  function renderPulseHtml(pulse, heroMsg) {
    return (
      '<div class="ma-pulse-v1 ma-pulse-v1--home-ref" data-pulse-fork="' +
      esc(pulse.fork) +
      '" data-pulse-status="' +
      esc(pulse.status || "") +
      '" data-home-sprint="1" data-shared-hero="1">' +
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

    var heroMsg = resolveHeroStory(pulse.executive_brief);
    // Cards always render on Home root; Hero only when Home is the active page.
    fillSharedHero(heroMsg);

    root.classList.remove(
      "ma-home-experience--loading",
      "ma-home-experience--calm",
      "ma-home-experience--legacy",
      "ma-pe-v2-home"
    );
    root.classList.add("ma-pulse-v1-root", "ma-pulse-v1-root--home-ref");
    root.setAttribute("aria-label", HOME_HERO_QUESTION);
    root.innerHTML = renderPulseHtml(pulse, heroMsg);
    bindCta();
    return true;
  }

  window.maApplyMerchantPulseV1 = applyMerchantPulseV1;
  window.maRefillHomeSharedHero = refillHomeSharedHero;
  window.maMerchantPulseV1IsValid = isValidPulse;
})();
