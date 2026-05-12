(function () {
  "use strict";

  var TITLES = {
    home: "الرئيسية",
    carts: "السلال المتروكة",
    followup: "سلال تحتاج متابعة",
    vip: "سلال VIP",
    messages: "الرسائل المرسلة",
    reasons: "أسباب التردد",
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
    "#widget": "widget",
    "#whatsapp": "whatsapp",
    "#settings": "settings",
  };

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

  document.addEventListener("DOMContentLoaded", function () {
    syncFromHash();
    document.querySelectorAll(".filter-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var bar = this.closest(".filter-bar");
        if (!bar) return;
        bar.querySelectorAll(".filter-btn").forEach(function (b) {
          b.classList.remove("active");
        });
        this.classList.add("active");
      });
    });
  });

  window.addEventListener("hashchange", syncFromHash);
})();
