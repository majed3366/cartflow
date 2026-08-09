/**
 * CartFlow Merchant UI V2 — App shell router (frame only).
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

  var CTX = {
    home: {
      items: [{ id: "overview", label: "نظرة عامة" }],
      note: "ماذا يجب أن أعرف الآن عن متجري؟",
    },
    workspace: {
      items: [{ id: "attention", label: "ما يحتاج قرارك" }],
      note: "قرار واحد واضح — ماذا نفعل، ولماذا، ومتى الآن.",
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
    var title = $("#cf2-appbar-section");
    if (title) title.textContent = sectionLabel(section);
  }

  function setContext(section) {
    var shell = $(".cf2-shell");
    var ctx = $(".cf2-ctx");
    if (!shell || !ctx) return;
    // Home + Workspace: stage owns the field — no legacy ctx rail.
    if (section === "home" || section === "workspace") {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      return;
    }
    var conf = CTX[section];
    if (!conf) {
      shell.setAttribute("data-cf2-ctx", "off");
      ctx.innerHTML = "";
      return;
    }
    shell.setAttribute("data-cf2-ctx", "on");
    var html = '<p class="cf2-ctx__label">في هذا القسم</p>';
    (conf.items || []).forEach(function (item, idx) {
      html +=
        '<button type="button" class="cf2-ctx__item' +
        (idx === 0 ? " is-active" : "") +
        '" data-cf2-ctx-item="' +
        item.id +
        '">' +
        item.label +
        "</button>";
    });
    if (conf.note) {
      html += '<p class="cf2-ctx__note">' + conf.note + "</p>";
    }
    ctx.innerHTML = html;
  }

  function showPage(section) {
    $all(".cf2-page").forEach(function (page) {
      var on = page.getAttribute("data-cf2-page") === section;
      page.classList.toggle("is-active", on);
      page.hidden = !on;
    });
  }

  function closeDrawer() {
    var d = $(".cf2-drawer");
    var b = $(".cf2-drawer-backdrop");
    if (d) d.classList.remove("is-open");
    if (b) b.classList.remove("is-open");
    document.body.classList.remove("is-drawer-open");
    document.body.style.overflow = "";
  }

  function openDrawer() {
    var d = $(".cf2-drawer");
    var b = $(".cf2-drawer-backdrop");
    if (d) d.classList.add("is-open");
    if (b) b.classList.add("is-open");
    document.body.classList.add("is-drawer-open");
    document.body.style.overflow = "hidden";
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
    if (menu) menu.addEventListener("click", openDrawer);
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
  };
})();
