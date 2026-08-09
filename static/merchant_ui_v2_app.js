/**
 * CartFlow Merchant UI V2 — App shell router.
 * GLOBAL UPBAR / drawer = primary destinations.
 * CONTEXTUAL SIDEBAR (desktop) / CONTEXTUAL SHEET (mobile) = current-area only.
 * These are separate systems — never mixed in one list.
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
   * Real V2 contextual views only (no invented subroutes).
   * Home: نظرة عامة. Workspace: ما يحتاج قرارك.
   * V1 الملخص العام is not a live V2 composition.
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
    var sheetBody = $("#cf2-ctx-sheet-body");
    var sheetTitle = $("#cf2-ctx-sheet-title");
    var pageChrome = $("#cf2-page-chrome");
    var trigger = $("#cf2-ctx-trigger");
    var triggerText = $("#cf2-ctx-trigger-text");
    if (!shell || !ctx) return;

    closeCtxSheet();

    var conf = CTX[section];
    if (!conf || !(conf.items && conf.items.length)) {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      if (sheetBody) sheetBody.innerHTML = "";
      if (sheetTitle) sheetTitle.textContent = "";
      if (pageChrome) pageChrome.hidden = true;
      if (trigger) trigger.setAttribute("aria-expanded", "false");
      if (triggerText) triggerText.textContent = "";
      return;
    }

    shell.setAttribute("data-cf2-ctx", "on");
    var activeId = conf.items[0].id;
    var title = conf.title || sectionLabel(section);
    var activeLabel = conf.items[0].label || "";
    var itemsHtml = paintCtxItems(conf, activeId);

    ctx.innerHTML =
      '<p class="cf2-ctx__area">' +
      title +
      "</p>" +
      '<p class="cf2-ctx__label">في هذا القسم</p>' +
      itemsHtml;

    if (sheetBody) sheetBody.innerHTML = itemsHtml;
    if (sheetTitle) sheetTitle.textContent = title;
    // Frame page-chrome only — never inject into App Bar or page content title row.
    if (pageChrome) pageChrome.hidden = false;
    if (triggerText) triggerText.textContent = activeLabel;
    if (trigger) trigger.setAttribute("aria-expanded", "false");
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
    if (!document.body.classList.contains("is-ctx-sheet-open")) {
      document.body.style.overflow = "";
    }
    setMenuExpanded(false);
  }

  function openDrawer() {
    closeCtxSheet();
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

  function closeCtxSheet() {
    var sheet = $("#cf2-ctx-sheet");
    var backdrop = $("#cf2-ctx-sheet-backdrop");
    var trigger = $("#cf2-ctx-trigger");
    if (sheet) {
      sheet.classList.remove("is-open");
      sheet.hidden = true;
    }
    if (backdrop) {
      backdrop.classList.remove("is-open");
      backdrop.hidden = true;
    }
    document.body.classList.remove("is-ctx-sheet-open");
    if (trigger) trigger.setAttribute("aria-expanded", "false");
    if (!document.body.classList.contains("is-drawer-open")) {
      document.body.style.overflow = "";
    }
  }

  function openCtxSheet() {
    closeDrawer();
    var sheet = $("#cf2-ctx-sheet");
    var backdrop = $("#cf2-ctx-sheet-backdrop");
    var trigger = $("#cf2-ctx-trigger");
    if (!sheet || sheet.querySelectorAll("[data-cf2-ctx-item]").length === 0) return;
    sheet.hidden = false;
    sheet.classList.add("is-open");
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add("is-open");
    }
    document.body.classList.add("is-ctx-sheet-open");
    document.body.style.overflow = "hidden";
    if (trigger) trigger.setAttribute("aria-expanded", "true");
  }

  function toggleCtxSheet() {
    if (document.body.classList.contains("is-ctx-sheet-open")) closeCtxSheet();
    else openCtxSheet();
  }

  function loadSection(section) {
    setActiveNav(section);
    setContext(section);
    showPage(section);
    closeDrawer();
    closeCtxSheet();

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

    var ctxTrigger = $("#cf2-ctx-trigger");
    if (ctxTrigger) ctxTrigger.addEventListener("click", toggleCtxSheet);
    var ctxClose = $("#cf2-ctx-sheet-close");
    if (ctxClose) ctxClose.addEventListener("click", closeCtxSheet);
    var ctxBackdrop = $("#cf2-ctx-sheet-backdrop");
    if (ctxBackdrop) ctxBackdrop.addEventListener("click", closeCtxSheet);

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
    openCtxSheet: openCtxSheet,
    closeCtxSheet: closeCtxSheet,
  };
})();
