(function () {
  "use strict";

  var TITLES = {
    home: "الرئيسية",
    carts: "السلال",
    followup: "السلال",
    completed: "السلال",
    vip: "السلال",
    messages: "الرسائل",
    reasons: "أسباب التردد",
    "trigger-templates": "القوالب",
    widget: "الودجيت",
    whatsapp: "واتساب",
    settings: "إعدادات عامة",
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
    "#widget": "widget",
    "#whatsapp": "whatsapp",
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

  function applyCartFilterMode(mode) {
    var tbody = document.querySelector("#page-carts tbody");
    if (!tbody) return;
    tbody.querySelectorAll("tr[data-ma-filter]").forEach(function (tr) {
      var b = tr.getAttribute("data-ma-filter") || "other";
      var show = mode === "all" || b === mode;
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

  function setCartHubVisible(show) {
    var hub = byId("ma-cart-hub-bar");
    if (hub) hub.hidden = !show;
    document.body.classList.toggle("ma-carts-hub-active", !!show);
  }

  function setCartTabUi(cartTab) {
    var tab = cartTab || "all";
    document.querySelectorAll("[data-cart-tab]").forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-cart-tab") === tab);
    });
    var pt = byId("pageTitle");
    if (pt) pt.textContent = CART_TAB_TITLES[tab] || TITLES.carts;
  }

  function resolveCartPage(cartTab) {
    if (cartTab === "intervention") return "followup";
    if (cartTab === "completed") return "completed";
    if (cartTab === "vip") return "vip";
    return "carts";
  }

  function applyCartTabFilters(cartTab) {
    if (cartTab === "all") {
      applyCartFilterMode("all");
      var bar = document.querySelector("#page-carts .filter-bar");
      if (bar) {
        bar.querySelectorAll(".filter-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-filter") === "all");
        });
      }
    } else if (cartTab === "waiting") {
      applyCartFilterMode("all");
      var barW = document.querySelector("#page-carts .filter-bar");
      if (barW) {
        barW.querySelectorAll(".filter-btn").forEach(function (b) {
          b.classList.toggle("active", b.getAttribute("data-filter") === "all");
        });
      }
    }
  }

  function updateNavActive(page, cartTab) {
    document.querySelectorAll(".nav-item").forEach(function (b) {
      var k = b.getAttribute("data-nav");
      var t = b.getAttribute("data-cart-tab");
      var on = false;
      if (cartTab && isCartSubPage(page)) {
        on = t === cartTab;
      } else if (!cartTab) {
        on = k === page && !t;
      }
      b.classList.toggle("active", on);
    });
    document.querySelectorAll(".ma-nav-group").forEach(function (g) {
      var any = g.querySelector(".nav-item.active");
      if (any) g.open = true;
    });
  }

  function runPageHooks(page) {
    if (typeof window.maEnsureTriggerTemplatesLoaded === "function" && page === "trigger-templates") {
      window.maEnsureTriggerTemplatesLoaded();
    }
    if (typeof window.maInitWhatsappSettingsPage === "function" && page === "whatsapp") {
      window.maInitWhatsappSettingsPage();
    }
    if (typeof window.maInitVipSettingsPage === "function" && page === "vip") {
      window.maInitVipSettingsPage();
    }
    if (typeof window.maInitGeneralSettingsPage === "function" && page === "settings") {
      window.maInitGeneralSettingsPage();
    }
  }

  function activatePage(page, options) {
    options = options || {};
    var cartTab = options.cartTab;

    document.querySelectorAll(".page").forEach(function (p) {
      p.classList.remove("active");
    });

    if (isCartSubPage(page)) {
      if (!cartTab) cartTab = CART_TAB_FOR_PAGE[page] || "all";
      var visiblePage = resolveCartPage(cartTab);
      setCartHubVisible(true);
      setCartTabUi(cartTab);
      var el = byId("page-" + visiblePage);
      if (el) el.classList.add("active");
      if (visiblePage === "carts") {
        initCartFiltersOnce();
        applyCartTabFilters(cartTab);
      }
      updateNavActive(visiblePage, cartTab);
      runPageHooks(visiblePage);
    } else {
      setCartHubVisible(false);
      var pageEl = byId("page-" + page);
      if (pageEl) pageEl.classList.add("active");
      var pt = byId("pageTitle");
      if (pt) pt.textContent = TITLES[page] || "";
      updateNavActive(page, null);
      runPageHooks(page);
    }

    var cb = byId("ma-sidebar-toggle");
    if (cb) cb.checked = false;
    window.scrollTo(0, 0);
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

  window.merchantAppReinitCartFilters = function () {
    var bar = document.querySelector("#page-carts .filter-bar");
    if (bar) bar.removeAttribute("data-ma-bound");
    initCartFiltersOnce();
  };

  function initCartHubBar() {
    var hub = byId("ma-cart-hub-bar");
    if (!hub || hub.getAttribute("data-ma-bound") === "1") return;
    hub.setAttribute("data-ma-bound", "1");
    hub.querySelectorAll("[data-cart-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tab = btn.getAttribute("data-cart-tab") || "all";
        goToCartTab(tab);
      });
    });
  }

  function initNavGroups() {
    document.querySelectorAll(".ma-nav-group summary").forEach(function (sum) {
      sum.addEventListener("click", function (ev) {
        ev.stopPropagation();
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initCartHubBar();
    initNavGroups();
    syncFromHash();
  });

  window.addEventListener("hashchange", syncFromHash);
})();
