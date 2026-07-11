(function () {
  "use strict";

  var TITLES = {
    home: "نظرة عامة",
    "home-setup": "إعداد المتجر",
    "home-month": "الملخص العام",
    "home-test-tools": "أدوات التجربة",
    carts: "السلال",
    followup: "السلال",
    completed: "السلال",
    vip: "السلال",
    messages: "الرسائل المرسلة",
    reasons: "أسباب التردد",
    "trigger-templates": "قوالب الاسترجاع",
    widget: "الودجيت",
    whatsapp: "واتساب",
    "whatsapp-connect": "ربط واتساب",
    plans: "الباقات",
    settings: "الحساب والمتجر",
  };

  var PAGE_SUBTITLES = {
    messages: "سجل رسائل استرداد واتساب المسجّلة لمتجرك",
    reasons: "توزيع أسباب ترك السلة خلال آخر 30 يوماً",
    "trigger-templates":
      "حدد محتوى رسائل الاسترجاع لكل سبب — وقم بإدارة مراحل المتابعة.",
    widget: "مظهر الودجيت ومتى يظهر للعميل — بدون إعدادات تقنية معقدة",
    whatsapp:
      "اختر كيف تتواصل CartFlow مع عملائك عبر واتساب.",
    "whatsapp-connect":
      "اربط رقم واتساب أعمال متجرك لإرسال رسائل الاسترجاع باسم متجرك.",
    plans:
      "قارن Starter و Growth و Pro — عرض للمقارنة فقط بدون ترقية أو دفع",
    settings:
      "ربط المتجر مع زد أو سلة، ثم تفضيلات الحساب — لا تغيّر الاسترجاع تلقائياً",
  };

  /** One-sentence page purpose — hero rhythm (Product Polish V1). */
  var PAGE_PURPOSE = {
    home: "ماذا حدث أثناء غيابك؟",
    "home-setup": "تحقق من جاهزية متجرك قبل التشغيل الكامل.",
    "home-month": "أرقام الاسترداد والأداء لهذا الشهر.",
    "home-test-tools": "اختبر الودجيت والاسترجاع بدون إرسال حقيقي.",
    carts: "ما الذي يحتاج انتباهك الآن؟",
    followup: "ردود العملاء والمتابعة التي يحتاج المتجر مراجعتها.",
    completed: "سلال أنهت مسار الاسترجاع — شراء أو استرداد ناجح.",
    vip: "سلال عالية القيمة تحتاج متابعة خاصة منك.",
    messages: "سجل رسائل استرداد واتساب المسجّلة لمتجرك.",
    reasons: "ما يمنع عملاءك من إتمام الشراء — خلال آخر 30 يوماً.",
    "trigger-templates": "محتوى رسائل الاسترجاع لكل سبب تردد.",
    widget: "مظهر الودجيت ومتى يظهر للعميل في المتجر.",
    whatsapp: "صحة تواصل متجرك عبر واتساب — حالة الربط والإرسال.",
    "whatsapp-connect": "اربط رقم واتساب أعمال متجرك لإرسال الاسترجاع.",
    plans: "اشتراكك الحالي — ما تشمله باقتك وكيف تقارن.",
    settings: "إعداد متجرك — الربط والحساب والتفضيلات.",
  };

  var CART_TAB_TITLES = {
    all: "السلال — الكل",
    intervention: "السلال — تفاعل العملاء",
    waiting: "السلال — بانتظار الإرسال",
    completed: "السلال — مكتملة",
    vip: "السلال — VIP",
  };

  var CART_SUB_PAGES = {
    carts: true,
    followup: true,
    completed: true,
    vip: true,
  };

  var PAGE_TO_SECTION = {
    home: "home",
    "home-setup": "home",
    "home-month": "home",
    "home-test-tools": "home",
    carts: "carts",
    followup: "carts",
    completed: "carts",
    vip: "carts",
    messages: "comms",
    reasons: "comms",
    "trigger-templates": "comms",
    widget: "settings",
    whatsapp: "settings",
    "whatsapp-connect": "settings",
    plans: "settings",
    settings: "settings",
  };

  var SECTION_LABELS = {
    home: "الرئيسية",
    carts: "السلال",
    comms: "التواصل",
    settings: "الإعدادات",
  };

  var HOME_SUB_PAGES = {
    home: true,
    "home-setup": true,
    "home-month": true,
    "home-test-tools": true,
  };

  var HOME_NAV_FOR_PAGE = {
    home: "overview",
    "home-setup": "setup",
    "home-month": "month",
    "home-test-tools": "test-tools",
  };

  var HOME_PAGE_FOR_NAV = {
    overview: "home",
    setup: "home-setup",
    month: "home-month",
    "test-tools": "home-test-tools",
  };

  var PAGE_FOR_HASH = {
    "": "home",
    "#": "home",
    "#home": "home",
    "#home-setup": "home-setup",
    "#home-month": "home-month",
    "#home-test-tools": "home-test-tools",
    "#carts": "carts",
    "#followup": "followup",
    "#completed": "completed",
    "#vip": "vip",
    "#messages": "messages",
    "#reasons": "reasons",
    "#trigger-templates": "trigger-templates",
    "#templates": "trigger-templates",
    "#widget": "widget",
    "#whatsapp": "whatsapp",
    "#whatsapp-connect": "whatsapp-connect",
    "#plans": "plans",
    "#settings": "settings",
  };

  var HASH_FOR_CART_TAB = {
    all: "#carts",
    intervention: "#followup",
    waiting: "#carts",
    completed: "#completed",
    vip: "#vip",
  };

  var CART_TAB_FOR_PAGE = {
    carts: "all",
    followup: "intervention",
    completed: "completed",
    vip: "vip",
  };

  function byId(id) {
    return document.getElementById(id);
  }

  function isCartSubPage(page) {
    return !!CART_SUB_PAGES[page];
  }

  function pageToSection(page) {
    return PAGE_TO_SECTION[page] || "home";
  }

  function parseHash() {
    var raw = (location.hash || "").split("?")[0];
    var h = raw.toLowerCase();
    if (h === "" || h === "#") h = "#home";
    var page = PAGE_FOR_HASH[h] || "home";
    var cartTab = null;
    try {
      var qs = (location.hash || "").split("?")[1] || "";
      if (qs) {
        var p = new URLSearchParams(qs);
        cartTab = p.get("tab");
      }
    } catch (e) {
      cartTab = null;
    }
    if (!cartTab && isCartSubPage(page)) {
      cartTab = CART_TAB_FOR_PAGE[page] || "all";
    }
    return { page: page, cartTab: cartTab };
  }

  function rowMatchesCartFilterMode(tr, mode) {
    var m = (mode || "all").trim().toLowerCase();
    if (m === "all") return true;
    var primary = (tr.getAttribute("data-ma-primary-bucket") || "").trim().toLowerCase();
    if (primary && primary === m) return true;
    var ui = (tr.getAttribute("data-ma-filter") || "").trim().toLowerCase();
    if (ui && ui === m) return true;
    var tabsRaw = tr.getAttribute("data-ma-visible-tabs") || "";
    if (tabsRaw) {
      try {
        var tabs = JSON.parse(tabsRaw);
        if (Array.isArray(tabs)) {
          for (var i = 0; i < tabs.length; i++) {
            if (String(tabs[i] || "").trim().toLowerCase() === m) return true;
          }
        }
      } catch (e) {
        /* ignore */
      }
    }
    return false;
  }

  function cartTabToFilterMode(cartTab) {
    var t = (cartTab || "all").trim().toLowerCase();
    if (t === "intervention" || t === "followup") return "attention";
    if (t === "completed") return "recovered";
    if (t === "no_phone") return "nophone";
    return t;
  }

  window.rowMatchesCartFilterMode = rowMatchesCartFilterMode;
  window.cartTabToFilterMode = cartTabToFilterMode;

  /** Persisted #page-carts filter-bar mode (all|recovered|sent|attention|nophone). */
  var currentNormalCartFilter = null;
  var NORMAL_CART_FILTER_STORAGE_KEY = "ma_normal_cart_filter_v1";

  function readPersistedNormalCartFilterFromStorage() {
    try {
      var raw = sessionStorage.getItem(NORMAL_CART_FILTER_STORAGE_KEY);
      if (!raw) return null;
      var m = cartTabToFilterMode(raw);
      if (!m || m === "all") return null;
      return m;
    } catch (_storageReadErr) {
      return null;
    }
  }

  function persistNormalCartFilterToStorage(mode) {
    try {
      if (mode && mode !== "all") {
        sessionStorage.setItem(NORMAL_CART_FILTER_STORAGE_KEY, mode);
      } else {
        sessionStorage.removeItem(NORMAL_CART_FILTER_STORAGE_KEY);
      }
    } catch (_storageWriteErr) {
      /* ignore */
    }
  }

  function getEffectiveNormalCartFilter() {
    if (currentNormalCartFilter) return currentNormalCartFilter;
    return readPersistedNormalCartFilterFromStorage();
  }

  /** Sidebar hash ?tab= — only non-default tabs override filter-bar selection. */
  function urlCartTabShouldApplyToFilterBar(urlTab) {
    if (!urlTab) return false;
    var t = urlTab.trim().toLowerCase();
    return t !== "all";
  }

  function getCurrentNormalCartFilter() {
    return currentNormalCartFilter;
  }

  function setCurrentNormalCartFilter(modeOrTab) {
    currentNormalCartFilter = cartTabToFilterMode(modeOrTab || "all");
    persistNormalCartFilterToStorage(currentNormalCartFilter);
  }

  window.getCurrentNormalCartFilter = getCurrentNormalCartFilter;
  window.setCurrentNormalCartFilter = setCurrentNormalCartFilter;
  window.getEffectiveNormalCartFilter = getEffectiveNormalCartFilter;
  window.urlCartTabShouldApplyToFilterBar = urlCartTabShouldApplyToFilterBar;
  window.NORMAL_CART_FILTER_STORAGE_KEY = NORMAL_CART_FILTER_STORAGE_KEY;

  function applyCartFilterMode(mode) {
    var m = cartTabToFilterMode(mode);
    var tbody = document.querySelector("#page-carts tbody");
    if (tbody) {
      tbody.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
        var show = rowMatchesCartFilterMode(tr, m);
        tr.style.display = show ? "" : "none";
      });
    }
    var queue =
      document.getElementById("ma-carts-groups-v2") ||
      document.getElementById("ma-carts-queue-v2");
    if (queue) {
      queue.querySelectorAll(".v2-queue-item[data-ma-filter]").forEach(function (item) {
        var show = rowMatchesCartFilterMode(item, m);
        item.style.display = show ? "" : "none";
        item.hidden = !show;
      });
      if (typeof window.maPeV2OnFilterApplied === "function") {
        window.maPeV2OnFilterApplied(m);
      }
    }
  }

  function initCartFiltersOnce() {
    var bar = document.querySelector("#page-carts .filter-bar");
    if (!bar || bar.getAttribute("data-ma-bound") === "1") return;
    bar.setAttribute("data-ma-bound", "1");
    bar.querySelectorAll(".filter-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var mode = btn.getAttribute("data-filter") || "all";
        bar.querySelectorAll(".filter-btn").forEach(function (b) {
          b.classList.remove("active");
        });
        btn.classList.add("active");
        setCurrentNormalCartFilter(mode);
        applyCartFilterMode(mode);
        try {
          console.info("[CLIENT REFRESH] cart_filter_selected", {
            mode: mode,
            source: "click",
          });
        } catch (_clickLogErr) {
          /* ignore */
        }
      });
    });
    var active = bar.querySelector(".filter-btn.active");
    var initialMode = active ? active.getAttribute("data-filter") || "all" : "all";
    var effective = getEffectiveNormalCartFilter();
    if (effective) {
      initialMode = effective;
      bar.querySelectorAll(".filter-btn").forEach(function (b) {
        var f = (b.getAttribute("data-filter") || "").trim().toLowerCase();
        b.classList.toggle("active", f === initialMode);
      });
    }
    applyCartFilterMode(initialMode);
  }

  function setContextSection(section) {
    var sec = section || "home";
    document.body.setAttribute("data-ma-section", sec);
    document.querySelectorAll(".ma-ctx-panel").forEach(function (panel) {
      var on = panel.getAttribute("data-ma-ctx") === sec;
      panel.hidden = !on;
    });
    document.querySelectorAll(".ma-gtb-section").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-ma-section") === sec);
    });
  }

  function setHomeNavActive(target) {
    document.querySelectorAll("[data-home-nav]").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-home-nav") === target);
    });
  }

  /* Carts uses shared global Hero (Experience Sprint 2) — same as Home/Messages. */
  var PAGES_WITH_INLINE_HERO = {
    followup: true,
    completed: true,
    vip: true,
  };

  var CARTS_HERO_QUESTION = "ما الذي يحتاج انتباهك الآن؟";

  /**
   * Hero Experience Sprint 2.1 — Question → Answer → Optional.
   * pageSub = eyebrow question; pageTitle = story (visual focus); pagePurpose = support.
   */
  function fillQuestionFirstHero(opts) {
    opts = opts || {};
    var hero = byId("ma-page-hero-global");
    var pt = byId("pageTitle");
    var pp = byId("pagePurpose");
    var ps = byId("pageSub");
    var question = String(opts.question || "").trim();
    var story = String(opts.story || "").trim();
    var support = String(opts.support || "").trim();
    if (hero) {
      hero.classList.add("ma-vi-hero");
      hero.removeAttribute("hidden");
      hero.setAttribute("data-hero-narrative", "question-first");
      if (!hero.querySelector(".ma-vi-hero__glow")) {
        var glow = document.createElement("div");
        glow.className = "ma-vi-hero__glow";
        glow.setAttribute("aria-hidden", "true");
        hero.insertBefore(glow, hero.firstChild);
      }
    }
    if (ps) {
      ps.textContent = question;
      ps.hidden = !question;
      ps.classList.add("ma-vi-hero__summary");
    }
    if (pt) pt.textContent = story || "";
    if (pp) {
      if (support) {
        pp.textContent = support;
        pp.hidden = false;
      } else {
        pp.textContent = "";
        pp.hidden = true;
      }
    }
  }

  function clearQuestionFirstHero() {
    var hero = byId("ma-page-hero-global");
    if (hero) hero.removeAttribute("data-hero-narrative");
  }

  /** Carts Sprint 2.2 — hold partial UI until one canonical snapshot is ready. */
  function setCartsExperienceReady(ready) {
    if (!document.body) return;
    document.body.setAttribute("data-carts-ready", ready ? "1" : "0");
    var loading = byId("ma-carts-unified-loading");
    if (loading) {
      if (ready) {
        loading.hidden = true;
        loading.setAttribute("hidden", "");
        loading.setAttribute("aria-busy", "false");
      } else {
        loading.hidden = false;
        loading.removeAttribute("hidden");
        loading.setAttribute("aria-busy", "true");
      }
    }
  }

  function beginCartsExperienceShell() {
    var globalHero = byId("ma-page-hero-global");
    if (globalHero) {
      globalHero.setAttribute("data-shared-hero-carts", "1");
    }
    // Keep last canonical Hero on re-entry; never wipe with empty/technical story.
    if (
      typeof window.maCartsExperienceHasCanonical === "function" &&
      window.maCartsExperienceHasCanonical()
    ) {
      setCartsExperienceReady(true);
      return;
    }
    fillQuestionFirstHero({
      question: CARTS_HERO_QUESTION,
      story: "",
      support: "",
    });
    setCartsExperienceReady(false);
    if (typeof window.maScheduleCartsRevealSafety === "function") {
      window.maScheduleCartsRevealSafety();
    }
  }

  window.maFillQuestionFirstHero = fillQuestionFirstHero;
  window.maClearQuestionFirstHero = clearQuestionFirstHero;
  window.maSetCartsExperienceReady = setCartsExperienceReady;

  function syncVisualHero(pageKey) {
    var globalHero = byId("ma-page-hero-global");
    if (globalHero) {
      var usePremium = pageKey && !PAGES_WITH_INLINE_HERO[pageKey];
      globalHero.classList.toggle("ma-vi-hero", !!usePremium);
      if (usePremium && !globalHero.querySelector(".ma-vi-hero__glow")) {
        var g = document.createElement("div");
        g.className = "ma-vi-hero__glow";
        g.setAttribute("aria-hidden", "true");
        globalHero.insertBefore(g, globalHero.firstChild);
      }
    }
    document.querySelectorAll(".ma-page-hero--inline").forEach(function (el) {
      el.classList.add("ma-vi-hero");
      if (!el.querySelector(".ma-vi-hero__glow")) {
        var glow = document.createElement("div");
        glow.className = "ma-vi-hero__glow";
        glow.setAttribute("aria-hidden", "true");
        el.insertBefore(glow, el.firstChild);
      }
    });
  }

  function setPageTitle(text, pageKey) {
    var pt = byId("pageTitle");
    var pp = byId("pagePurpose");
    var ps = byId("pageSub");
    var globalHero = byId("ma-page-hero-global");
    if (document.body && pageKey) {
      document.body.setAttribute("data-ma-page", pageKey);
    }
    if (pageKey && pageKey !== "carts" && globalHero) {
      globalHero.removeAttribute("data-shared-hero-carts");
    }
    if (pageKey && pageKey !== "home" && pageKey !== "carts") {
      clearQuestionFirstHero();
      if (document.body) document.body.removeAttribute("data-carts-ready");
    }
    // Home Pulse owns the shared global Hero — re-assert, do not clobber with page defaults.
    if (pageKey === "home") {
      var homeRoot = byId("ma-home-experience-root");
      var pulseOwned =
        homeRoot && homeRoot.querySelector('[data-shared-hero="1"]');
      if (pulseOwned) {
        if (typeof window.maRefillHomeSharedHero === "function") {
          window.maRefillHomeSharedHero();
        }
        syncVisualHero(pageKey);
        return;
      }
    }
    // Carts Experience Sprint 2.2 — question shell; reveal only with canonical snapshot.
    if (pageKey === "carts") {
      beginCartsExperienceShell();
      syncVisualHero(pageKey);
      return;
    }
    if (pt) pt.textContent = text || "";
    var purpose = pageKey && PAGE_PURPOSE[pageKey] ? PAGE_PURPOSE[pageKey] : "";
    if (pp) {
      pp.textContent = purpose;
      pp.hidden = !purpose;
    }
    var sub = pageKey && PAGE_SUBTITLES[pageKey] ? PAGE_SUBTITLES[pageKey] : "";
    if (ps) {
      ps.textContent = sub;
      ps.hidden = !sub;
    }
    syncVisualHero(pageKey);
  }

  function isHomeSubPage(page) {
    return !!HOME_SUB_PAGES[page];
  }

  function openSetupSteps() {
    var panel = byId("ma-setup-steps-panel");
    var btn = byId("ma-setup-toggle-btn");
    if (panel) {
      panel.hidden = false;
      panel.classList.remove("hidden");
    }
    if (btn) btn.setAttribute("aria-expanded", "true");
    var root = byId("ma-setup-experience-root");
    if (root) {
      requestAnimationFrame(function () {
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  window.maHomeNav = function (target) {
    var t = (target || "overview").trim();
    var page = HOME_PAGE_FOR_NAV[t] || "home";
    goTo(page);
    setHomeNavActive(t);
    if (t === "setup") {
      setTimeout(openSetupSteps, 0);
    }
  };

  window.maOpenSetupDetail = openSetupSteps;

  function updateNavActive(page, cartTab) {
    var section = pageToSection(page);
    document.querySelectorAll(".ma-context-sidebar .nav-item").forEach(function (b) {
      var k = b.getAttribute("data-nav");
      var t = b.getAttribute("data-cart-tab");
      var on = false;
      if (section === "carts" && cartTab) {
        on = t === cartTab;
      } else if (!t) {
        on = k === page;
      }
      b.classList.toggle("active", on);
    });
  }

  function runPageHooks(page) {
    if (typeof window.maSyncHomeActivation === "function") {
      window.maSyncHomeActivation();
    }
    if (typeof window.maEnsureTriggerTemplatesLoaded === "function" && page === "trigger-templates") {
      window.maEnsureTriggerTemplatesLoaded();
    }
    if (typeof window.maInitWhatsappSettingsPage === "function" && page === "whatsapp") {
      window.maInitWhatsappSettingsPage();
    }
    if (typeof window.maInitWhatsappConnectPage === "function" && page === "whatsapp-connect") {
      window.maInitWhatsappConnectPage();
    }
    if (typeof window.maInitVipSettingsPage === "function" && page === "vip") {
      window.maInitVipSettingsPage();
    }
    if (typeof window.maInitStoreConnectionPage === "function" && page === "settings") {
      window.maInitStoreConnectionPage();
    }
    if (typeof window.maInitGeneralSettingsPage === "function" && page === "settings") {
      window.maInitGeneralSettingsPage();
    }
    if (typeof window.maInitPlansPage === "function" && page === "plans") {
      window.maInitPlansPage();
    }
  }

  function resolveCartPage(cartTab) {
    if (cartTab === "intervention") return "followup";
    if (cartTab === "completed") return "completed";
    if (cartTab === "vip") return "vip";
    return "carts";
  }

  function getUrlCartTabFromHash() {
    try {
      var hashQs = (location.hash || "").split("?")[1] || "";
      return (new URLSearchParams(hashQs).get("tab") || "").trim();
    } catch (_urlTabErr) {
      return "";
    }
  }

  function hasExplicitUrlCartTab() {
    return !!getUrlCartTabFromHash();
  }

  window.getUrlCartTabFromHash = getUrlCartTabFromHash;
  window.hasExplicitUrlCartTab = hasExplicitUrlCartTab;

  function applyCartTabFilters(cartTab, options) {
    options = options || {};
    var before = getCurrentNormalCartFilter();
    var mode = cartTabToFilterMode(cartTab);
    if (options.persist !== false) {
      setCurrentNormalCartFilter(mode);
    }
    applyCartFilterMode(mode);
    var bar = document.querySelector("#page-carts .filter-bar");
    if (bar) {
      bar.querySelectorAll(".filter-btn").forEach(function (b) {
        var f = (b.getAttribute("data-filter") || "").trim().toLowerCase();
        b.classList.toggle("active", f === mode);
      });
    }
    try {
      console.info("[CLIENT REFRESH] cart_filter_apply", {
        selected_filter_before: before,
        selected_filter_after: mode,
        persist: options.persist !== false,
        source: options.source || "apply",
      });
    } catch (_logErr) {
      /* ignore */
    }
  }

  function activatePage(page, options) {
    options = options || {};
    var cartTab = options.cartTab;
    var section = pageToSection(page);

    document.querySelectorAll(".page").forEach(function (p) {
      p.classList.remove("active");
    });

    setContextSection(section);

    if (isCartSubPage(page)) {
      if (!cartTab) cartTab = CART_TAB_FOR_PAGE[page] || "all";
      var visiblePage = resolveCartPage(cartTab);
      var el = byId("page-" + visiblePage);
      if (el) el.classList.add("active");
      setPageTitle(CART_TAB_TITLES[cartTab] || TITLES.carts, visiblePage);
      if (visiblePage === "carts") {
        initCartFiltersOnce();
        var urlTab = getUrlCartTabFromHash();
        if (urlCartTabShouldApplyToFilterBar(urlTab)) {
          applyCartTabFilters(urlTab, { persist: true, source: "url" });
        } else if (getEffectiveNormalCartFilter()) {
          applyCartTabFilters(getEffectiveNormalCartFilter(), {
            persist: false,
            source: "persisted",
          });
        } else {
          applyCartTabFilters("all", { persist: true, source: "default" });
        }
      }
      if (visiblePage === "completed" && typeof window.maRefreshCompletedCartsTable === "function") {
        window.maRefreshCompletedCartsTable();
      }
      updateNavActive(visiblePage, cartTab);
      runPageHooks(visiblePage);
      if (typeof window.maApplyJourneyPageGate === "function") {
        window.maApplyJourneyPageGate(visiblePage);
      }
    } else {
      var pageEl = byId("page-" + page);
      if (pageEl) pageEl.classList.add("active");
      setPageTitle(TITLES[page] || SECTION_LABELS[section] || "", page);
      updateNavActive(page, null);
      if (isHomeSubPage(page)) {
        setHomeNavActive(HOME_NAV_FOR_PAGE[page] || "overview");
      }
      runPageHooks(page);
      if (typeof window.maApplyJourneyPageGate === "function") {
        window.maApplyJourneyPageGate(page);
      }
    }

    var cb = byId("ma-sidebar-toggle");
    if (cb) cb.checked = false;
    var scrollRoot = document.querySelector(".ma-content-root");
    if (scrollRoot) scrollRoot.scrollTop = 0;
    else window.scrollTo(0, 0);
  }

  function syncFromHash() {
    var parsed = parseHash();
    activatePage(parsed.page, { cartTab: parsed.cartTab });
  }

  window.goTo = function (page, cartTab) {
    var hash = "#" + page;
    if (cartTab && HASH_FOR_CART_TAB[cartTab]) {
      hash = HASH_FOR_CART_TAB[cartTab];
      if (cartTab === "all") {
        hash = "#carts";
      } else if (cartTab === "waiting") {
        hash = "#carts?tab=" + encodeURIComponent(cartTab);
      }
    }
    if (location.hash !== hash) {
      location.hash = hash;
    } else {
      activatePage(page, { cartTab: cartTab });
    }
  };

  window.goToCartTab = function (cartTab) {
    var tab = (cartTab || "all").trim().toLowerCase();
    if (tab === "all") {
      setCurrentNormalCartFilter("all");
      applyCartTabFilters("all", { persist: true, source: "nav_all" });
    }
    var page = resolveCartPage(cartTab);
    goTo(page, cartTab);
  };

  window.goToSection = function (section) {
    var sec = (section || "home").trim();
    if (sec === "home") {
      goTo("home");
      return;
    }
    if (sec === "carts") {
      goTo("carts");
      return;
    }
    if (sec === "comms") {
      goTo("messages");
      return;
    }
    if (sec === "settings") {
      goTo("whatsapp");
      return;
    }
    goTo("home");
  };

  window.applyCartTabFilters = applyCartTabFilters;

  window.merchantAppReinitCartFilters = function () {
    var bar = document.querySelector("#page-carts .filter-bar");
    if (bar) bar.removeAttribute("data-ma-bound");
    initCartFiltersOnce();
  };

  function initGlobalTopbar() {
    document.querySelectorAll(".ma-gtb-section").forEach(function (btn) {
      btn.addEventListener("click", function () {
        goToSection(btn.getAttribute("data-ma-section") || "home");
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var stored = readPersistedNormalCartFilterFromStorage();
    if (stored) {
      currentNormalCartFilter = stored;
    }
    initGlobalTopbar();
    syncFromHash();
  });

  window.addEventListener("hashchange", syncFromHash);
})();
