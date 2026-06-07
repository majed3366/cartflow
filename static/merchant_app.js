(function () {
  "use strict";

  var TITLES = {
    home: "الرئيسية",
    carts: "السلال",
    followup: "السلال",
    completed: "السلال",
    vip: "السلال",
    messages: "الرسائل المرسلة",
    reasons: "أسباب التردد",
    "trigger-templates": "قوالب الاسترجاع",
    widget: "الودجيت",
    whatsapp: "واتساب",
    plans: "الباقات",
    settings: "الحساب والمتجر",
  };

  var PAGE_SUBTITLES = {
    messages: "سجل رسائل استرداد واتساب المسجّلة لمتجرك",
    reasons: "توزيع أسباب ترك السلة خلال آخر 30 يوماً",
    "trigger-templates":
      "سلسلة مراحل الاسترجاع لكل سبب — طمأنة ثم عرض ثم بديل (وليس تكرار نفس الرسالة).",
    widget: "مظهر الودجيت ومتى يظهر للعميل — بدون إعدادات تقنية معقدة",
    whatsapp:
      "رقم المتجر وتفعيل استرجاع الواتساب — تُحفظ لمتجرك دون إرسال تجريبي من هذه الصفحة",
    plans:
      "قارن Starter و Growth و Pro — عرض للمقارنة فقط بدون ترقية أو دفع",
    settings:
      "ربط المتجر مع زد أو سلة، ثم تفضيلات الحساب — لا تغيّر الاسترجاع تلقائياً",
  };

  var CART_TAB_TITLES = {
    all: "السلال — الكل",
    intervention: "السلال — تحتاج تدخل",
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
    carts: "carts",
    followup: "carts",
    completed: "carts",
    vip: "carts",
    messages: "comms",
    reasons: "comms",
    "trigger-templates": "comms",
    widget: "settings",
    whatsapp: "settings",
    plans: "settings",
    settings: "settings",
  };

  var SECTION_LABELS = {
    home: "الرئيسية",
    carts: "السلال",
    comms: "التواصل",
    settings: "الإعدادات",
  };

  var PAGE_FOR_HASH = {
    "": "home",
    "#": "home",
    "#home": "home",
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

  function applyCartFilterMode(mode) {
    var tbody = document.querySelector("#page-carts tbody");
    if (!tbody) return;
    var m = cartTabToFilterMode(mode);
    tbody.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
      var show = rowMatchesCartFilterMode(tr, m);
      tr.style.display = show ? "" : "none";
    });
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
        applyCartFilterMode(mode);
      });
    });
    var active = bar.querySelector(".filter-btn.active");
    applyCartFilterMode(active ? active.getAttribute("data-filter") || "all" : "all");
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

  function setPageTitle(text, pageKey) {
    var pt = byId("pageTitle");
    var ps = byId("pageSub");
    if (pt) pt.textContent = text || "";
    var sub = pageKey && PAGE_SUBTITLES[pageKey] ? PAGE_SUBTITLES[pageKey] : "";
    if (ps) {
      ps.textContent = sub;
      ps.hidden = !sub;
    }
  }

  function openSetupSteps() {
    var root = byId("ma-setup-experience-root");
    var panel = byId("ma-setup-steps-panel");
    var btn = byId("ma-setup-toggle-btn");
    if (panel) panel.hidden = false;
    if (btn) btn.setAttribute("aria-expanded", "true");
    if (root) {
      requestAnimationFrame(function () {
        root.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }

  window.maHomeNav = function (target) {
    var t = (target || "overview").trim();
    goTo("home");
    setHomeNavActive(t);
    if (t === "setup") {
      setTimeout(openSetupSteps, 0);
      return;
    }
    if (t === "month") {
      var monthEl = byId("ma-home-month-summary");
      if (monthEl) {
        requestAnimationFrame(function () {
          monthEl.scrollIntoView({ behavior: "smooth", block: "start" });
        });
      }
      return;
    }
    var scrollRoot = document.querySelector(".ma-content-root");
    if (scrollRoot) scrollRoot.scrollTop = 0;
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
    if (typeof window.maInitWhatsappTemplateRegistryPage === "function" && page === "whatsapp") {
      window.maInitWhatsappTemplateRegistryPage();
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

  function applyCartTabFilters(cartTab) {
    var mode = cartTabToFilterMode(cartTab);
    applyCartFilterMode(mode);
    var bar = document.querySelector("#page-carts .filter-bar");
    if (bar) {
      bar.querySelectorAll(".filter-btn").forEach(function (b) {
        var f = (b.getAttribute("data-filter") || "").trim().toLowerCase();
        b.classList.toggle("active", f === mode);
      });
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
      setPageTitle(CART_TAB_TITLES[cartTab] || TITLES.carts, null);
      if (visiblePage === "carts") {
        initCartFiltersOnce();
        applyCartTabFilters(cartTab);
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
      if (page === "home") setHomeNavActive("overview");
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
      if (cartTab === "all" || cartTab === "waiting") {
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
      goToCartTab("all");
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
    initGlobalTopbar();
    syncFromHash();
  });

  window.addEventListener("hashchange", syncFromHash);
})();
