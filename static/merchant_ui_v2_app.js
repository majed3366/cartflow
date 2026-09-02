/**
 * CartFlow Merchant UI V2 — App shell router.
 * Approved MerchantShell ownership:
 *   UtilityRow → GlobalUpbar → ContextualSidebar → PageStage
 * One GlobalNavigation model + one ContextualNavigation model.
 * Presentation may differ by breakpoint; ownership must not.
 */
(function () {
  "use strict";

  /** Canonical navigation registry — desktop and mobile consume this only. */
  var NAV = {
    global: [
      { id: "home", label: "الرئيسية", slice: true },
      { id: "workspace", label: "مساحة القرار", slice: true },
      { id: "products", label: "المنتجات", slice: false },
      { id: "carts", label: "السلال", slice: true },
      { id: "comms", label: "التواصل", slice: true },
      { id: "settings", label: "الإعدادات", slice: false },
    ],
    contextual: {
      home: {
        title: "الرئيسية",
        items: [
          { id: "overview", label: "نظرة عامة" },
          { id: "summary", label: "الملخص" },
        ],
      },
      workspace: {
        title: "مساحة القرار",
        items: [{ id: "attention", label: "ما يحتاج قرارك" }],
      },
      products: null,
      carts: {
        title: "السلال",
        items: [
          { id: "attention", label: "يحتاجني" },
          { id: "nophone", label: "بانتظار رقم العميل" },
          { id: "sent", label: "بانتظار الرد" },
          { id: "recovered", label: "اكتمل" },
        ],
      },
      comms: {
        title: "التواصل",
        items: [
          { id: "needs", label: "يحتاج متابعتي" },
          { id: "active", label: "جاري" },
          { id: "all", label: "السجل" },
        ],
      },
      settings: {
        title: "الإعدادات",
        items: [
          { id: "store", label: "المتجر" },
          { id: "communication", label: "إعدادات واتساب" },
          { id: "recovery", label: "سياسة الاسترجاع" },
          { id: "policy", label: "سياسة السلال المهمة" },
          { id: "experience", label: "الودجيت" },
        ],
      },
    },
  };

  var SECTIONS = NAV.global;
  var activeCtxItem = null;
  /** One-shot product-data init per surface. Chrome may re-paint; data may not. */
  var SURFACE_PRODUCT_INIT = {
    home: false,
    workspace: false,
    carts: false,
    comms: false,
    settings: false,
  };

  function $(sel, root) {
    return (root || document).querySelector(sel);
  }

  function $all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  var SETTINGS_HASH_ALIASES = {
    settings: "settings",
    whatsapp: "settings",
    "whatsapp-connect": "settings",
    widget: "settings",
    "trigger-templates": "settings",
    templates: "settings",
    plans: "settings",
  };

  function currentHash() {
    var h = (location.hash || "#home").replace(/^#/, "").split("?")[0];
    if (!h) return "home";
    if (h === "communication" || h === "messages") return "comms";
    if (SETTINGS_HASH_ALIASES[h]) return "settings";
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
      document.body.classList.contains("is-ctx-open")
    );
  }

  function unlockScrollIfIdle() {
    if (!anyOverlayOpen()) document.body.style.overflow = "";
  }

  function revealActiveNavItem(section) {
    var nav = document.getElementById("cf2-nav");
    var btn = nav && nav.querySelector('[data-cf2-nav="' + section + '"]');
    if (!nav || !btn) return;
    if (typeof btn.scrollIntoView === "function") {
      try {
        btn.scrollIntoView({ inline: "nearest", block: "nearest" });
      } catch (err) {
        btn.scrollIntoView();
      }
    }
    var navBox = nav.getBoundingClientRect();
    var btnBox = btn.getBoundingClientRect();
    var pad = 8;
    var shift = 0;
    if (btnBox.left < navBox.left + pad) {
      shift = btnBox.left - navBox.left - pad;
    } else if (btnBox.right > navBox.right - pad) {
      shift = btnBox.right - navBox.right + pad;
    }
    if (shift && typeof nav.scrollBy === "function") {
      nav.scrollBy(shift, 0);
    }
  }

  function setActiveNav(section) {
    $all("[data-cf2-nav]").forEach(function (btn) {
      var on = btn.getAttribute("data-cf2-nav") === section;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-current", on ? "page" : "false");
    });
    revealActiveNavItem(section);
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

  /** Paint Global destinations into the single GlobalUpbar mount. */
  function paintGlobalNavigation(activeSection) {
    var active = activeSection || currentHash();
    var upbar = $("#cf2-nav");
    if (!upbar) return;
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
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          revealActiveNavItem(active);
        });
      });
    } else {
      revealActiveNavItem(active);
    }
  }

  function ctxCountSuffix(section, itemId) {
    if (section === "carts" && window.CartFlowUiV2Carts && window.CartFlowUiV2Carts.ctxCounts) {
      var cc = window.CartFlowUiV2Carts.ctxCounts()[itemId];
      if (cc > 0) return " · " + cc;
    }
    if (section === "comms" && window.CartFlowUiV2Comms && window.CartFlowUiV2Comms.ctxCounts) {
      var cm = window.CartFlowUiV2Comms.ctxCounts()[itemId];
      if (cm > 0) return " · " + cm;
    }
    if (section === "settings" && window.CartFlowUiV2Settings && window.CartFlowUiV2Settings.ctxHint) {
      var hint = window.CartFlowUiV2Settings.ctxHint(itemId);
      if (hint) return " · " + hint;
    }
    return "";
  }

  function paintCtxMarkup(conf, activeId, section) {
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
      var suffix = section ? ctxCountSuffix(section, item.id) : "";
      html +=
        '<button type="button" class="cf2-ctx__item' +
        (on ? " is-active" : "") +
        '" data-cf2-ctx-item="' +
        item.id +
        '"' +
        (on ? ' aria-current="true"' : "") +
        ">" +
        item.label +
        suffix +
        "</button>";
    });
    return html;
  }

  function applyCtxItem(section, itemId) {
    if (!itemId) return;
    if (
      section === "home" &&
      window.CartFlowUiV2Home &&
      typeof window.CartFlowUiV2Home.showView === "function"
    ) {
      window.CartFlowUiV2Home.showView(itemId === "summary" ? "summary" : "overview");
      return;
    }
    if (section === "carts" && window.CartFlowUiV2Carts && typeof window.CartFlowUiV2Carts.setFilter === "function") {
      window.CartFlowUiV2Carts.setFilter(itemId);
      return;
    }
    if (section === "comms" && window.CartFlowUiV2Comms && typeof window.CartFlowUiV2Comms.setFilter === "function") {
      window.CartFlowUiV2Comms.setFilter(itemId);
      return;
    }
    if (
      section === "settings" &&
      window.CartFlowUiV2Settings &&
      typeof window.CartFlowUiV2Settings.showPanel === "function"
    ) {
      window.CartFlowUiV2Settings.showPanel(itemId);
    }
  }

  function bindCtxItems() {
    $all("[data-cf2-ctx-item]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        activeCtxItem = btn.getAttribute("data-cf2-ctx-item");
        var section = currentHash();
        var conf = contextualFor(section);
        if (!conf) return;
        var ctx = $("#cf2-ctx");
        if (!ctx) return;
        ctx.innerHTML = paintCtxMarkup(conf, activeCtxItem, section);
        bindCtxClose();
        bindCtxItems();
        applyCtxItem(section, activeCtxItem);
        if (window.matchMedia("(max-width: 1023px)").matches) {
          closeCtxDrawer();
        }
      });
    });
  }

  function setContext(section) {
    var shell = $(".cf2-shell");
    var ctx = $("#cf2-ctx");
    var handle = $("#cf2-ctx-handle");
    if (!shell || !ctx) return;

    closeCtxDrawer();

    var conf = contextualFor(section);
    if (!conf) {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      ctx.hidden = true;
      activeCtxItem = null;
      if (handle) {
        handle.hidden = true;
        handle.setAttribute("aria-expanded", "false");
      }
      return;
    }

    shell.setAttribute("data-cf2-ctx", "on");
    ctx.hidden = false;
    activeCtxItem = conf.items[0].id;
    ctx.innerHTML = paintCtxMarkup(conf, activeCtxItem, section);
    bindCtxClose();
    bindCtxItems();
    applyCtxItem(section, activeCtxItem);
    if (handle) {
      handle.hidden = false;
      handle.setAttribute("aria-expanded", "false");
      handle.setAttribute(
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
    menu.setAttribute("aria-label", open ? "إغلاق قائمة الحساب" : "فتح قائمة الحساب");
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

  function paintAccountDrawer(identity, subscription) {
    var nameEl = $("#cf2-account-store-name");
    var metaEl = $("#cf2-account-store-meta");
    var planEl = $("#cf2-account-plan");
    if (!nameEl) return;
    var storeName = (identity && identity.store_name) || "";
    if (!String(storeName).trim()) {
      var utilName = $(".cf2-utility__identity-name");
      if (utilName) storeName = utilName.textContent || "";
    }
    nameEl.textContent = String(storeName || "متجرك").trim() || "متجرك";
    if (metaEl) {
      var bits = [];
      if (identity && identity.commerce_provider && identity.commerce_provider !== "—") {
        bits.push(String(identity.commerce_provider));
      }
      if (identity && identity.connection_status) {
        bits.push(String(identity.connection_status));
      }
      metaEl.textContent = bits.join(" · ");
      metaEl.hidden = !bits.length;
    }
    if (planEl) {
      var sub = subscription && (subscription.subscription || subscription);
      var planLabel =
        (sub &&
          (sub.current_plan_label_ar ||
            sub.plan_label_ar ||
            sub.plan_name_ar ||
            sub.current_plan)) ||
        "";
      var statusLabel =
        (sub &&
          (sub.plan_status_label_ar ||
            sub.status_label_ar ||
            sub.subscription_health_ar)) ||
        "";
      var line = String(planLabel || "").trim();
      if (statusLabel) line = line ? line + " · " + statusLabel : statusLabel;
      planEl.textContent = line ? "الباقة: " + line : "الباقة: غير متاحة";
    }
  }

  function refreshAccountDrawer() {
    var nameEl = $("#cf2-account-store-name");
    if (nameEl && (!nameEl.textContent || nameEl.textContent.indexOf("جاري") === 0)) {
      nameEl.textContent = "جاري التحميل…";
    }
    Promise.all([
      fetch("/api/merchant/session-identity", {
        credentials: "same-origin",
        cache: "no-store",
      })
        .then(function (r) {
          return r.json().catch(function () {
            return {};
          });
        })
        .catch(function () {
          return {};
        }),
      fetch("/api/merchant/subscription", {
        credentials: "same-origin",
        cache: "no-store",
      })
        .then(function (r) {
          return r.json().catch(function () {
            return {};
          });
        })
        .catch(function () {
          return {};
        }),
    ]).then(function (pair) {
      paintAccountDrawer(pair[0] || {}, pair[1] || {});
    });
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
    refreshAccountDrawer();
  }

  function openSettingsArea(areaId) {
    closeDrawer();
    go("settings");
    window.setTimeout(function () {
      if (window.CartFlowUiV2Settings && CartFlowUiV2Settings.showPanel) {
        CartFlowUiV2Settings.showPanel(areaId || "store");
      }
    }, 80);
  }

  function toggleDrawer() {
    if (document.body.classList.contains("is-drawer-open")) closeDrawer();
    else openDrawer();
  }

  function setCtxHandleExpanded(open) {
    var handle = $("#cf2-ctx-handle");
    if (!handle) return;
    handle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function closeCtxDrawer() {
    var ctx = $("#cf2-ctx");
    var backdrop = $("#cf2-ctx-backdrop");
    document.body.classList.remove("is-ctx-open");
    if (ctx) ctx.classList.remove("is-open");
    if (backdrop) {
      backdrop.classList.remove("is-open");
      backdrop.hidden = true;
    }
    setCtxHandleExpanded(false);
    unlockScrollIfIdle();
  }

  function openCtxDrawer() {
    closeDrawer();
    var ctx = $("#cf2-ctx");
    var backdrop = $("#cf2-ctx-backdrop");
    if (!ctx || ctx.hidden || !ctx.querySelector("[data-cf2-ctx-item]")) return;
    ctx.classList.add("is-open");
    if (backdrop) {
      backdrop.hidden = false;
      backdrop.classList.add("is-open");
    }
    document.body.classList.add("is-ctx-open");
    document.body.style.overflow = "hidden";
    setCtxHandleExpanded(true);
  }

  function toggleCtxDrawer() {
    if (document.body.classList.contains("is-ctx-open")) closeCtxDrawer();
    else openCtxDrawer();
  }

  function initSurfaceProductData(section, opts) {
    var force = !!(opts && opts.force);
    if (SURFACE_PRODUCT_INIT[section] && !force) {
      return;
    }
    var started = false;
    if (section === "home") {
      var homeRoot = $("#cf2-home-root");
      if (homeRoot && window.CartFlowUiV2Home) {
        window.CartFlowUiV2Home.loadAndPaint(homeRoot);
        started = true;
      }
    } else if (section === "workspace") {
      var wsRoot = $("#cf2-workspace-root");
      if (wsRoot && window.CartFlowUiV2Workspace) {
        window.CartFlowUiV2Workspace.loadAndPaint(wsRoot);
        started = true;
      }
    } else if (section === "carts") {
      var cartsRoot = $("#cf2-carts-root");
      if (cartsRoot && window.CartFlowUiV2Carts) {
        window.CartFlowUiV2Carts.loadAndPaint(cartsRoot);
        started = true;
      }
    } else if (section === "comms") {
      var commsRoot = $("#cf2-comms-root");
      if (commsRoot && window.CartFlowUiV2Comms) {
        window.CartFlowUiV2Comms.loadAndPaint(commsRoot);
        started = true;
      }
    } else if (section === "settings") {
      var settingsRoot = $("#cf2-settings-root");
      if (settingsRoot && window.CartFlowUiV2Settings) {
        window.CartFlowUiV2Settings.loadAndPaint(settingsRoot);
        started = true;
      }
    }
    if (started) {
      SURFACE_PRODUCT_INIT[section] = true;
    }
  }

  function refreshContextualSidebar() {
    var section = currentHash();
    var conf = contextualFor(section);
    var ctx = $("#cf2-ctx");
    if (!conf || !ctx || ctx.hidden) return;
    ctx.innerHTML = paintCtxMarkup(conf, activeCtxItem || conf.items[0].id, section);
    bindCtxClose();
    bindCtxItems();
  }

  function loadSection(section, opts) {
    paintGlobalNavigation(section);
    setActiveNav(section);
    setContext(section);
    showPage(section);
    closeDrawer();
    closeCtxDrawer();
    initSurfaceProductData(section, opts);
  }

  function go(section) {
    var id = section || "home";
    var hashId = id === "comms" ? "communication" : id;
    if (location.hash !== "#" + hashId) {
      location.hash = "#" + hashId;
    } else {
      loadSection(id, { force: true });
    }
  }

  function bind() {
    paintGlobalNavigation(currentHash());

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

    var utilSettings = $('[data-cf2-util="settings"]');
    if (utilSettings) {
      utilSettings.addEventListener("click", function () {
        openSettingsArea("store");
      });
    }
    var utilStore = $('[data-cf2-util="settings-store"]');
    if (utilStore) {
      utilStore.addEventListener("click", function () {
        openSettingsArea("store");
      });
    }
    var utilPlan = $('[data-cf2-util="settings-plan"]');
    if (utilPlan) {
      utilPlan.addEventListener("click", function () {
        openSettingsArea("store");
      });
    }

    var handle = $("#cf2-ctx-handle");
    if (handle) handle.addEventListener("click", toggleCtxDrawer);
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
    currentHash: currentHash,
    surfaceProductInit: SURFACE_PRODUCT_INIT,
    paintGlobalNavigation: paintGlobalNavigation,
    openCtxDrawer: openCtxDrawer,
    closeCtxDrawer: closeCtxDrawer,
    refreshContextualSidebar: refreshContextualSidebar,
  };
})();
