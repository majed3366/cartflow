/**
 * Commerce Situation surfaces — Products / Carts / Communication consumers.
 * Same situation_id across pages; no reinterpretation.
 */
(function () {
  "use strict";

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function readSituationIdFromHash() {
    try {
      var h = String(location.hash || "");
      var q = h.indexOf("?") >= 0 ? h.split("?")[1] : "";
      if (!q && h.indexOf("situation_id=") >= 0) q = h.replace(/^#/, "");
      var params = new URLSearchParams(q || "");
      return String(params.get("situation_id") || "").trim();
    } catch (e) {
      return "";
    }
  }

  function pkgFromSummary(summary) {
    var cs = summary && summary.commerce_situations_v1;
    if (!cs || !cs.ok) return null;
    return cs;
  }

  function consumer(cs, surface) {
    var cons = (cs && cs.consumers) || {};
    return cons[surface] || null;
  }

  function filterItems(items, situationId) {
    var rows = Array.isArray(items) ? items : [];
    if (!situationId) return rows;
    return rows.filter(function (it) {
      return String((it && it.situation_id) || "") === situationId;
    });
  }

  function renderProducts(root, items, focusId) {
    var rows = filterItems(items, focusId);
    if (!rows.length) {
      root.innerHTML =
        '<section class="cs-surface" data-cs-surface="products">' +
        "<h2>المنتجات في مواقف العمل</h2>" +
        '<p class="cs-empty">لا توجد منتجات مشاركة في موقف تجاري حالياً.</p></section>';
      return;
    }
    var html =
      '<section class="cs-surface" data-cs-surface="products">' +
      "<h2>المنتجات المشاركة في المواقف</h2>" +
      (focusId
        ? '<p class="cs-focus">الموقف: <code data-situation-id="' +
          esc(focusId) +
          '">' +
          esc(focusId) +
          "</code></p>"
        : "") +
      '<ul class="cs-list">';
    for (var i = 0; i < rows.length; i++) {
      var it = rows[i] || {};
      var products = Array.isArray(it.affected_products) ? it.affected_products : [];
      var names = products
        .map(function (p) {
          return (p && p.name_ar) || "";
        })
        .filter(Boolean);
      if (!names.length && it.title_ar) names = [it.title_ar];
      html +=
        '<li class="cs-card" data-situation-id="' +
        esc(it.situation_id || "") +
        '">' +
        '<p class="cs-card__title">' +
        esc(it.title_ar || "") +
        "</p>" +
        '<p class="cs-card__body">' +
        esc(names.join(" · ") || it.why_it_matters_ar || "") +
        "</p>" +
        '<p class="cs-card__id"><code>' +
        esc(it.situation_id || "") +
        "</code></p>" +
        '<p class="cs-card__links">' +
        '<a href="#workspace?situation_id=' +
        encodeURIComponent(it.situation_id || "") +
        '">وسّع في مساحة القرار</a>' +
        "</p></li>";
    }
    html += "</ul></section>";
    root.innerHTML = html;
  }

  function renderOpsBanner(root, surface, items, focusId, emptyAr) {
    if (!root) return;
    var rows = filterItems(items, focusId);
    root.hidden = false;
    if (!rows.length) {
      root.innerHTML =
        '<section class="cs-ops-banner" data-cs-surface="' +
        esc(surface) +
        '"><p>' +
        esc(emptyAr) +
        "</p></section>";
      return;
    }
    var html =
      '<section class="cs-ops-banner" data-cs-surface="' +
      esc(surface) +
      '">' +
      "<h3>مشاركة في مواقف العمل</h3><ul>";
    for (var i = 0; i < rows.length; i++) {
      var it = rows[i] || {};
      var note =
        surface === "carts"
          ? (it.ops_note_ar ||
              (it.affected_carts && it.affected_carts.summary_ar) ||
              "")
          : it.why_it_matters_ar || it.merchant_action_ar || "";
      html +=
        '<li data-situation-id="' +
        esc(it.situation_id || "") +
        '">' +
        "<strong>" +
        esc(it.title_ar || "") +
        "</strong> — " +
        esc(note) +
        ' <code class="cs-inline-id">' +
        esc(it.situation_id || "") +
        "</code></li>";
    }
    html += "</ul></section>";
    root.innerHTML = html;
  }

  function paintIdentityChip(hostId, summary) {
    var id = summary && summary.reality_validation_identity_v1;
    if (!id) return;
    var host = document.getElementById(hostId);
    if (!host) return;
    var el = host.querySelector("[data-rv-audit-chip]") || document.createElement("div");
    el.setAttribute("data-rv-audit-chip", "1");
    el.className = "cs-rv-chip";
    el.setAttribute("data-rv-status", String(id.status || ""));
    el.innerHTML =
      "<strong>" +
      esc(id.status || "?") +
      "</strong> · store=<code>" +
      esc(id.store_slug || "") +
      "</code> · run=<code>" +
      esc(id.simulation_run_id || "—") +
      "</code> · situations=" +
      esc(String(id.situation_count ?? "—"));
    if (!el.parentNode) host.insertBefore(el, host.firstChild);
  }

  window.maApplyCommerceSituationSurfacesV1 = function (summary) {
    var cs = pkgFromSummary(summary);
    paintIdentityChip("cs-products-root", summary);
    paintIdentityChip("meif-carts-focus-root", summary);
    paintIdentityChip("meif-communication-root", summary);
    if (!cs) return false;
    var focus = readSituationIdFromHash();
    var productsRoot = document.getElementById("cs-products-root");
    var products = consumer(cs, "products");
    if (productsRoot && products) {
      renderProducts(productsRoot, products.items || [], focus);
    }
    var cartsFocus = document.getElementById("meif-carts-focus-root");
    var carts = consumer(cs, "carts");
    if (cartsFocus && carts) {
      renderOpsBanner(
        cartsFocus,
        "carts",
        carts.items || [],
        focus,
        "لا توجد سلال مشاركة في موقف تجاري معلن حالياً — تشغيل السلال أدناه."
      );
    }
    var commRoot = document.getElementById("meif-communication-root");
    var comm = consumer(cs, "communication");
    if (commRoot && comm && Array.isArray(comm.items) && comm.items.length) {
      if (!document.getElementById("cs-comms-banner")) {
        commRoot.insertAdjacentHTML(
          "afterbegin",
          '<div id="cs-comms-banner" class="cs-ops-banner-wrap"></div>'
        );
      }
      var host = document.getElementById("cs-comms-banner");
      if (host) {
        renderOpsBanner(
          host,
          "communication",
          comm.items || [],
          focus,
          "لا يوجد عملاء مشاركون في موقف تواصل معلن حالياً."
        );
      }
    }
    return true;
  };

  window.maCommerceSituationFocusIdV1 = readSituationIdFromHash;

  window.addEventListener("hashchange", function () {
    if (
      window.maApplyCommerceSituationSurfacesV1 &&
      window.__cfLastSummaryForSituations
    ) {
      try {
        window.maApplyCommerceSituationSurfacesV1(
          window.__cfLastSummaryForSituations
        );
      } catch (e) {}
    }
  });
})();
