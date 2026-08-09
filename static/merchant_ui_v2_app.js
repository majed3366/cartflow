/**
 * CartFlow Merchant UI V2 — App shell router.
 * Exactly TWO navigation levels from ONE registry:
 *   1) GLOBAL — Upbar / Mobile Global control / optional utility drawer
 *   2) CONTEXTUAL — Sidebar (desktop column / mobile overlay)
 * Presentation may differ by breakpoint; ownership must not.
 */
(function () {
  "use strict";

  /** Canonical navigation registry — every Global host consumes this only. */
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

  function anyOverlayOpen() {
    return (
      document.body.classList.contains("is-drawer-open") ||
      document.body.classList.contains("is-ctx-open") ||
      document.body.classList.contains("is-global-nav-open")
    );
  }

  function unlockScrollIfIdle() {
    if (!anyOverlayOpen()) document.body.style.overflow = "";
  }

  function setActiveNav(section) {
    $all("[data-cf2-nav]").forEach(function (btn) {
      var on = btn.getAttribute("data-cf2-nav") === section;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-current", on ? "page" : "false");
    });
  }

  function bindGlobalNavClicks(root) {
    $all("[data-cf2-nav]", root || document).forEach(function (btn) {
      if (btn.getAttribute("data-cf2-nav-bound") === "1") return;
      btn.setAttribute("data-cf2-nav-bound", "1");
      btn.addEventListener("click", function () {
        go(btn.getAttribute("data-cf2-nav"));
      });
    });
  }

  /** Paint Global destinations from NAV.global into every mount. */
  function paintGlobalNavigation(activeSection) {
    var active = activeSection || currentHash();

    var upbar = $("#cf2-nav");
    if (upbar) {
      upbar.innerHTML = NAV.global
        .map(function (item) {
          var on = item.id === active;
          return (
            '<button type="button" class="cf2-nav__item' +
            (on ? " is-active" : "") +
            '" data-cf2-nav="' +
            item.id +
            '"' +
            (on ? ' aria-current="page"' : ' aria-current="false"') +
            ">" +
            item.label +
            "</button>"
          );
        })
        .join("");
      bindGlobalNavClicks(upbar);
    }

    var mobileList = $("#cf2-global-panel-list");
    if (mobileList) {
      mobileList.innerHTML = NAV.global
        .map(function (item) {
          var on = item.id === active;
          return (
            '<button type="button" class="cf2-global-panel__item' +
            (on ? " is-active" : "") +
            '" data-cf2-nav="' +
            item.id +
            '"' +
            (on ? ' aria-current="page"' : ' aria-current="false"') +
            ">" +
            item.label +
            "</button>"
          );
        })
        .join("");
      bindGlobalNavClicks(mobileList);
    }

    var drawerMount = $("#cf2-drawer-global");
    if (drawerMount) {
      var label = drawerMount.querySelector(".cf2-drawer__label");
      var labelHtml = label
        ? '<p class="cf2-drawer__label">' + (label.textContent || "أقسام المنصة") + "</p>"
        : '<p class="cf2-drawer__label">أقسام المنصة</p>';
      drawerMount.innerHTML =
        labelHtml +
        NAV.global
          .map(function (item) {
            var on = item.id === active;
            return (
              '<button type="button" class="cf2-drawer__item' +
              (on ? " is-active" : "") +
              '" data-cf2-nav="' +
              item.id +
              '"' +
              (on ? ' aria-current="page"' : ' aria-current="false"') +
              ">" +
              item.label +
              "</button>"
            );
          })
          .join("");
      bindGlobalNavClicks(drawerMount);
    }
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

  function setGlobalBtnExpanded(open) {
    var btn = $("#cf2-global-btn");
    if (!btn) return;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    btn.setAttribute(
      "aria-label",
      open ? "إغلاق أقسام المنصة" : "أقسام المنصة"
    );
  }

  function closeGlobalNav() {
    var panel = $("#cf2-global-panel");
    var backdrop = $("#cf2-global-backdrop");
    document.body.classList.remove("is-global-nav-open");
    if (panel) {
      panel.classList.remove("is-open");
      panel.hidden = true;
    }
    if (backdrop) {
      backdrop.classList.remove("is-open");
      backdrop.hidden = true;
    }
    setGlobalBtnExpanded(false);
    unlockScrollIfIdle();
  }

  function openGlobalNav() {
    closeDrawer();
    closeCtxDrawer();
    var panel = $("#cf2-global-panel");
    var backdrop = $("#cf2-global-backdrop");
    if (!panel) return;
    panel.hidden = false;
    panel.classList.add("is-open");
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add("is-open");
    }
    document.body.classList.add("is-global-nav-open");
    document.body.style.overflow = "hidden";
    setGlobalBtnExpanded(true);
  }

  function toggleGlobalNav() {
    if (document.body.classList.contains("is-global-nav-open")) closeGlobalNav();
    else openGlobalNav();
  }

  function closeDrawer() {
    var d = $(".cf2-drawer");
    var b = $(".cf2-drawer-backdrop");
    if (d) d.classList.remove("is-open");
    if (b) b.classList.remove("is-open");
    document.body.classList.remove("is-drawer-open");
    setMenuExpanded(false);
    unlockScrollIfIdle();
  }

  function openDrawer() {
    closeCtxDrawer();
    closeGlobalNav();
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
    unlockScrollIfIdle();
  }

  function openCtxDrawer() {
    closeDrawer();
    closeGlobalNav();
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
    paintGlobalNavigation(section);
    setActiveNav(section);
    setContext(section);
    showPage(section);
    closeDrawer();
    closeCtxDrawer();
    closeGlobalNav();

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
    paintGlobalNavigation(currentHash());
    bindGlobalNavClicks(document);

    var globalBtn = $("#cf2-global-btn");
    if (globalBtn) globalBtn.addEventListener("click", toggleGlobalNav);
    var globalClose = $("#cf2-global-panel-close");
    if (globalClose) globalClose.addEventListener("click", closeGlobalNav);
    var globalBackdrop = $("#cf2-global-backdrop");
    if (globalBackdrop) globalBackdrop.addEventListener("click", closeGlobalNav);

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
    paintGlobalNavigation: paintGlobalNavigation,
    openGlobalNav: openGlobalNav,
    closeGlobalNav: closeGlobalNav,
    openCtxDrawer: openCtxDrawer,
    closeCtxDrawer: closeCtxDrawer,
  };
})();
