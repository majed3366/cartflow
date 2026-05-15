(function () {
  "use strict";

  var TITLES = {
    home: "الرئيسية",
    carts: "السلال المتروكة",
    followup: "سلال تحتاج متابعة",
    vip: "سلال VIP",
    messages: "الرسائل المرسلة",
    reasons: "أسباب التردد",
    "trigger-templates": "قوالب الاسترجاع",
    widget: "الودجيت",
    whatsapp: "إعدادات واتساب",
    settings: "الإعدادات العامة",
  };

  var PAGE_FOR_HASH = {
    "": "home",
    "#": "home",
    "#home": "home",
    "#carts": "carts",
    "#followup": "followup",
    "#vip": "vip",
    "#messages": "messages",
    "#reasons": "reasons",
    "#trigger-templates": "trigger-templates",
    "#widget": "widget",
    "#whatsapp": "whatsapp",
    "#settings": "settings",
  };

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

  function activatePage(page) {
    var titles = TITLES;
    document.querySelectorAll(".page").forEach(function (p) {
      p.classList.remove("active");
    });
    var el = document.getElementById("page-" + page);
    if (el) el.classList.add("active");
    var pt = document.getElementById("pageTitle");
    if (pt) pt.textContent = titles[page] || "";
    document.querySelectorAll(".nav-item").forEach(function (b) {
      var k = b.getAttribute("data-nav");
      b.classList.toggle("active", k === page);
    });
    var cb = document.getElementById("ma-sidebar-toggle");
    if (cb) cb.checked = false;
    window.scrollTo(0, 0);
    initCartFiltersOnce();
    if (typeof window.maEnsureTriggerTemplatesLoaded === "function" && page === "trigger-templates") {
      window.maEnsureTriggerTemplatesLoaded();
    }
    if (page === "carts") {
      var bar = document.querySelector("#page-carts .filter-bar");
      var active = bar && bar.querySelector(".filter-btn.active");
      applyCartFilterMode(active ? active.getAttribute("data-filter") || "all" : "all");
    }
  }

  function syncFromHash() {
    var raw = (location.hash || "").split("?")[0];
    var h = raw.toLowerCase();
    if (h === "" || h === "#") h = "#home";
    var page = PAGE_FOR_HASH[h];
    if (!page) page = "home";
    activatePage(page);
  }

  window.goTo = function (page) {
    var next = "#" + page;
    if (location.hash !== next) {
      location.hash = next;
    } else {
      activatePage(page);
    }
  };

  window.merchantAppReinitCartFilters = function () {
    var bar = document.querySelector("#page-carts .filter-bar");
    if (bar) {
      bar.removeAttribute("data-ma-bound");
    }
    initCartFiltersOnce();
  };

  document.addEventListener("DOMContentLoaded", function () {
    syncFromHash();
  });

  window.addEventListener("hashchange", syncFromHash);
})();
