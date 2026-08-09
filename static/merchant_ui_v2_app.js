/**
 * CartFlow Merchant UI V2 — App shell router.
 * Exactly TWO navigation levels from ONE registry:
 *   1) GLOBAL — Upbar / App Bar + Global Drawer
 *   2) CONTEXTUAL — Sidebar (desktop column / mobile drawer)
 * Never invent a third layer (page-chrome, context strip, floating pills).
 */
(function () {
  "use strict";

  /** Canonical navigation registry — desktop and mobile consume this only. */
  var NAV = {
    global: [
      { id: "home", label: "الرئيسية", slice: true },
      { id: "workspace", label: "مساحة القرار", slice: true },
      { id: "products", label: "المنتجات", slice: false },
      { id: "carts", label: "السلال", slice: false },
      { id: "comms", label: "التواصل", slice: false },
      { id: "settings", label: "الإعدادات", slice: false },
    ],
    contextual: {
      home: {
        title: "الرئيسية",
        items: [{ id: "overview", label: "نظرة عامة" }],
      },
      workspace: {
        title: "مساحة القرار",
        items: [{ id: "attention", label: "ما يحتاج قرارك" }],
      },
      products: null,
      carts: null,
      comms: null,
      settings: null,
    },
  };

  var SECTIONS = NAV.global;

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

  function contextualFor(section) {
    var conf = NAV.contextual[section];
    if (!conf || !(conf.items && conf.items.length)) return null;
    return conf;
  }

  function setActiveNav(section) {
    $all("[data-cf2-nav]").forEach(function (btn) {
      var on = btn.getAttribute("data-cf2-nav") === section;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-current", on ? "page" : "false");
    });
  }

  function paintCtxMarkup(conf, activeId) {
    var title = conf.title || "";
    var html =
      '<div class="cf2-ctx__toolbar">' +
      '<button type="button" class="cf2-ctx__close" id="cf2-ctx-close" aria-label="إغلاق شريط القسم">×</button>' +
      "</div>" +
      '<p class="cf2-ctx__area">' +
      title +
      "</p>";
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
    var ctxBtn = $("#cf2-ctx-btn");
    if (!shell || !ctx) return;

    closeCtxDrawer();

    var conf = contextualFor(section);
    if (!conf) {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      ctx.hidden = true;
      if (ctxBtn) {
        ctxBtn.hidden = true;
        ctxBtn.setAttribute("aria-expanded", "false");
      }
      return;
    }

    shell.setAttribute("data-cf2-ctx", "on");
    ctx.hidden = false;
    ctx.innerHTML = paintCtxMarkup(conf, conf.items[0].id);
    bindCtxClose();
    if (ctxBtn) {
      ctxBtn.hidden = false;
      ctxBtn.setAttribute("aria-expanded", "false");
      ctxBtn.setAttribute(
        "aria-label",
        "فتح شريط " + (conf.title || sectionLabel(section))
      );
    }
  }

  function bindCtxClose() {
    var close = $("#cf2-ctx-close");
    if (close) {
      close.addEventListener("click", closeCtxDrawer);
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
    if (!document.body.classList.contains("is-ctx-open")) {
      document.body.style.overflow = "";
    }
    setMenuExpanded(false);
  }

  function openDrawer() {
    closeCtxDrawer();
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

  function closeCtxDrawer() {
    var ctx = $("#cf2-ctx");
    var backdrop = $("#cf2-ctx-backdrop");
    var ctxBtn = $("#cf2-ctx-btn");
    document.body.classList.remove("is-ctx-open");
    if (ctx) ctx.classList.remove("is-open");
    if (backdrop) {
      backdrop.classList.remove("is-open");
      backdrop.hidden = true;
    }
    if (ctxBtn) ctxBtn.setAttribute("aria-expanded", "false");
    if (!document.body.classList.contains("is-drawer-open")) {
      document.body.style.overflow = "";
    }
  }

  function openCtxDrawer() {
    closeDrawer();
    var ctx = $("#cf2-ctx");
    var backdrop = $("#cf2-ctx-backdrop");
    var ctxBtn = $("#cf2-ctx-btn");
    if (!ctx || ctx.hidden || !ctx.querySelector("[data-cf2-ctx-item]")) return;
    ctx.classList.add("is-open");
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add("is-open");
    }
    document.body.classList.add("is-ctx-open");
    document.body.style.overflow = "hidden";
    if (ctxBtn) ctxBtn.setAttribute("aria-expanded", "true");
  }

  function toggleCtxDrawer() {
    if (document.body.classList.contains("is-ctx-open")) closeCtxDrawer();
    else openCtxDrawer();
  }

  function loadSection(section) {
    setActiveNav(section);
    setContext(section);
    showPage(section);
    closeDrawer();
    closeCtxDrawer();

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

    var ctxBtn = $("#cf2-ctx-btn");
    if (ctxBtn) ctxBtn.addEventListener("click", toggleCtxDrawer);
    var ctxBackdrop = $("#cf2-ctx-backdrop");
    if (ctxBackdrop) ctxBackdrop.addEventListener("click", closeCtxDrawer);

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
    nav: NAV,
    sections: SECTIONS,
    ctx: NAV.contextual,
    openCtxDrawer: openCtxDrawer,
    closeCtxDrawer: closeCtxDrawer,
  };
})();
