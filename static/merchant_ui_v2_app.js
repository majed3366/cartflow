/**
 * CartFlow Merchant UI V2 — App shell router.
 * GLOBAL UPBAR / drawer = primary destinations.
 * CONTEXTUAL SIDEBAR / mobile strip = current-area navigation only.
 * Hash routes: #home | #workspace | stubs for other primary sections.
 */
(function () {
  "use strict";

  var SECTIONS = [
    { id: "home", label: "الرئيسية", slice: true },
    { id: "workspace", label: "مساحة القرار", slice: true },
    { id: "products", label: "المنتجات", slice: false },
    { id: "carts", label: "السلال", slice: false },
    { id: "comms", label: "التواصل", slice: false },
    { id: "settings", label: "الإعدادات", slice: false },
  ];

  /**
   * Contextual items — real V2 area views only (no invented subroutes).
   * Home: frozen executive board = نظرة عامة.
   * Workspace: decision attention surface = ما يحتاج قرارك.
   * (V1 "الملخص العام" / #home-month is not a live V2 composition.)
   */
  var CTX = {
    home: {
      title: "الرئيسية",
      items: [{ id: "overview", label: "نظرة عامة" }],
    },
    workspace: {
      title: "مساحة القرار",
      items: [{ id: "attention", label: "ما يحتاج قرارك" }],
    },
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function currentHash() {
    var h = (location.hash || "#home").replace(/^#/, "").split("?")[0];
    if (!h) return "home";
    if (h === "communication") return "comms";
    return h;
  }

  function sectionLabel(section) {
    for (var i = 0; i < SECTIONS.length; i++) {
      if (SECTIONS[i].id === section) return SECTIONS[i].label;
    }
    return "CartFlow";
  }

  function setActiveNav(section) {
    $all("[data-cf2-nav]").forEach(function (btn) {
      var on = btn.getAttribute("data-cf2-nav") === section;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-current", on ? "page" : "false");
    });
  }

  function paintCtxItems(conf, activeId) {
    var html = "";
    (conf.items || []).forEach(function (item) {
      var on = item.id === activeId;
      html +=
        '<button type="button" class="cf2-ctx__item' +
        (on ? " is-active" : "") +
        '" data-cf2-ctx-item="' +
        item.id +
        '"' +
        (on ? ' aria-current="true"' : "") +
        ">" +
        item.label +
        "</button>";
    });
    return html;
  }

  function setContext(section) {
    var shell = $(".cf2-shell");
    var ctx = $("#cf2-ctx");
    var mobile = $("#cf2-ctx-mobile");
    if (!shell || !ctx) return;

    var conf = CTX[section];
    if (!conf || !(conf.items && conf.items.length)) {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      if (mobile) {
        mobile.innerHTML = "";
        mobile.hidden = true;
        mobile.setAttribute("data-cf2-ctx-mobile", "off");
      }
      return;
    }

    shell.setAttribute("data-cf2-ctx", "on");
    var activeId = conf.items[0].id;
    var title = conf.title || sectionLabel(section);

    ctx.innerHTML =
      '<p class="cf2-ctx__area">' +
      title +
      "</p>" +
      '<p class="cf2-ctx__label">في هذا القسم</p>' +
      paintCtxItems(conf, activeId);

    if (mobile) {
      mobile.innerHTML =
        '<p class="cf2-ctx-mobile__area">' +
        title +
        "</p>" +
        '<div class="cf2-ctx-mobile__items">' +
        paintCtxItems(conf, activeId) +
        "</div>";
      mobile.hidden = false;
      mobile.setAttribute("data-cf2-ctx-mobile", "on");
    }
  }

  function showPage(section) {
    $all(".cf2-page").forEach(function (page) {
      var on = page.getAttribute("data-cf2-page") === section;
      page.classList.toggle("is-active", on);
      page.hidden = !on;
    });
  }

  function setMenuExpanded(open) {
    var menu = $(".cf2-menu-btn");
    if (!menu) return;
    menu.setAttribute("aria-expanded", open ? "true" : "false");
    menu.setAttribute("aria-label", open ? "إغلاق القائمة" : "فتح القائمة");
  }

  function closeDrawer() {
    var d = $(".cf2-drawer");
    var b = $(".cf2-drawer-backdrop");
    if (d) d.classList.remove("is-open");
    if (b) b.classList.remove("is-open");
    document.body.classList.remove("is-drawer-open");
    document.body.style.overflow = "";
    setMenuExpanded(false);
  }

  function openDrawer() {
    var d = $(".cf2-drawer");
    var b = $(".cf2-drawer-backdrop");
    if (d) d.classList.add("is-open");
    if (b) b.classList.add("is-open");
    document.body.classList.add("is-drawer-open");
    document.body.style.overflow = "hidden";
    setMenuExpanded(true);
  }

  function toggleDrawer() {
    if (document.body.classList.contains("is-drawer-open")) closeDrawer();
    else openDrawer();
  }

  function loadSection(section) {
    setActiveNav(section);
    setContext(section);
    showPage(section);
    closeDrawer();

    if (section === "home") {
      var homeRoot = $("#cf2-home-root");
      if (homeRoot && window.CartFlowUiV2Home) {
        window.CartFlowUiV2Home.loadAndPaint(homeRoot);
      }
      return;
    }
    if (section === "workspace") {
      var wsRoot = $("#cf2-workspace-root");
      if (wsRoot && window.CartFlowUiV2Workspace) {
        window.CartFlowUiV2Workspace.loadAndPaint(wsRoot);
      }
    }
  }

  function go(section) {
    var id = section || "home";
    if (location.hash !== "#" + id) {
      location.hash = "#" + id;
    } else {
      loadSection(id);
    }
  }

  function bind() {
    $all("[data-cf2-nav]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        go(btn.getAttribute("data-cf2-nav"));
      });
    });
    var menu = $(".cf2-menu-btn");
    if (menu) menu.addEventListener("click", toggleDrawer);
    var mobileAcc = $("#cf2-mobile-account");
    if (mobileAcc) mobileAcc.addEventListener("click", openDrawer);
    var deskAcc = $("#cf2-account-btn");
    if (deskAcc) deskAcc.addEventListener("click", openDrawer);
    var close = $(".cf2-drawer__close");
    if (close) close.addEventListener("click", closeDrawer);
    var backdrop = $(".cf2-drawer-backdrop");
    if (backdrop) backdrop.addEventListener("click", closeDrawer);
    var brand = $(".cf2-brand");
    if (brand) {
      brand.addEventListener("click", function (e) {
        e.preventDefault();
        go("home");
      });
    }
    window.addEventListener("hashchange", function () {
      loadSection(currentHash());
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bind();
    loadSection(currentHash());
  });

  window.CartFlowUiV2 = {
    go: go,
    sections: SECTIONS,
    ctx: CTX,
  };
})();
