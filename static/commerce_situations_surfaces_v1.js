/**
 * Commerce Situation surfaces — Products / Carts / Communication consumers.
 * Merchant-safe: no situation_id, run stamps, or identity chips on merchant pages.
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
        "<h2>المنتجات التي تستحق انتباهك</h2>" +
        '<p class="cs-empty">لا توجد منتجات تستحق انتباهاً خاصاً حالياً.</p></section>';
      return;
    }
    var html =
      '<section class="cs-surface" data-cs-surface="products">' +
      "<h2>المنتجات التي تستحق انتباهك</h2>" +
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
        '<li class="cs-card">' +
        '<p class="cs-card__title">' +
        esc(it.title_ar || "") +
        "</p>" +
        '<p class="cs-card__body">' +
        esc(it.why_it_matters_ar || names.join(" · ") || "") +
        "</p>" +
        '<p class="cs-card__links">' +
        '<a href="#workspace">وسّع في مساحة القرار ←</a>' +
        "</p></li>";
    }
    html += "</ul></section>";
    root.innerHTML = html;
  }

  function paintPublicationTruth(summary) {
    var pub = summary && summary.merchant_publication_v1;
    if (!pub || !pub.ok) return;

    var cartsFocus = document.getElementById("meif-carts-focus-root");
    if (cartsFocus) {
      var cartOps = pub.cart_condition || pub.cart_operational_action || {};
      var systemic = pub.systemic_business_action || {};
      var cartHtml =
        '<section class="cs-ops-banner cs-pub-truth" data-cs-surface="carts">' +
        "<h3>حالة السلال</h3>" +
        "<p>" +
        esc(cartOps.summary_ar || "تقدّم سلال العملاء مستقر.") +
        "</p>" +
        "<p><strong>مستوى السلة:</strong> " +
        esc(cartOps.individual_action_ar || "لا يحتاج إجراءً فردياً الآن.") +
        "</p>";
      if (systemic.summary_ar) {
        cartHtml +=
          "<p><strong>قرار العمل:</strong> " +
          esc(systemic.summary_ar) +
          ' <a href="#workspace">مساحة القرار ←</a></p>';
      }
      cartHtml += "</section>";
      var existingCart = cartsFocus.querySelector(
        "[data-cs-surface='carts'].cs-pub-truth"
      );
      if (existingCart) existingCart.outerHTML = cartHtml;
      else cartsFocus.insertAdjacentHTML("afterbegin", cartHtml);
    }

    var commRoot = document.getElementById("meif-communication-root");
    if (commRoot) {
      var cc = pub.communication_condition || {};
      var commHtml =
        '<section class="cs-ops-banner cs-pub-truth" data-cs-surface="communication">' +
        "<h3>حالة التواصل</h3>" +
        "<p>" +
        esc(cc.summary_ar || "تواصل العملاء يسير بشكل طبيعي.") +
        "</p></section>";
      var existing = commRoot.querySelector(
        "[data-cs-surface='communication'].cs-pub-truth"
      );
      if (existing) existing.outerHTML = commHtml;
      else {
        if (!document.getElementById("cs-comms-banner")) {
          commRoot.insertAdjacentHTML(
            "afterbegin",
            '<div id="cs-comms-banner" class="cs-ops-banner-wrap"></div>'
          );
        }
        var host = document.getElementById("cs-comms-banner");
        if (host) host.insertAdjacentHTML("afterbegin", commHtml);
        else commRoot.insertAdjacentHTML("afterbegin", commHtml);
      }
    }
  }

  window.maApplyCommerceSituationSurfacesV1 = function (summary) {
    var cs = pkgFromSummary(summary);
    paintPublicationTruth(summary);
    // Remove any leftover identity chips from prior paints.
    ["cs-products-root", "meif-carts-focus-root", "meif-communication-root"].forEach(
      function (id) {
        var host = document.getElementById(id);
        if (!host) return;
        var chips = host.querySelectorAll("[data-rv-audit-chip], .cs-rv-chip");
        for (var i = 0; i < chips.length; i++) chips[i].remove();
      }
    );
    if (!cs) return !!summary && !!summary.merchant_publication_v1;
    var focus = readSituationIdFromHash();
    var productsRoot = document.getElementById("cs-products-root");
    var products = consumer(cs, "products");
    if (productsRoot && products) {
      renderProducts(productsRoot, products.items || [], focus);
    }
    // Carts / Communication: publication banner is the merchant-facing layer.
    // Do not paint raw situation-id banners above operational lists.
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
