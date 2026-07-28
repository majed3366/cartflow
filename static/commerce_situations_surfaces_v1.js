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
    // Continuity: arriving from Workspace commitment = execution surface,
    // not a second explanation of the same diagnosis.
    var fromWorkspace = !!focusId;
    var html =
      '<section class="cs-surface" data-cs-surface="products">' +
      "<h2>" +
      (fromWorkspace
        ? "تنفيذ القرار على المنتجات"
        : "المنتجات التي تستحق انتباهك") +
      "</h2>" +
      (fromWorkspace
        ? '<p class="cs-continuity">وصلت إلى هنا لمتابعة التنفيذ — التشخيص اكتمل في مساحة القرار.</p>'
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
        '<li class="cs-card">' +
        '<p class="cs-card__title">' +
        esc(it.title_ar || "") +
        "</p>" +
        (fromWorkspace
          ? '<p class="cs-card__body">' +
            esc(names.join(" · ") || "المنتج المرتبط بالتزامك.") +
            "</p>"
          : '<p class="cs-card__body">' +
            esc(it.why_it_matters_ar || names.join(" · ") || "") +
            "</p>") +
        '<p class="cs-card__links">' +
        (fromWorkspace
          ? '<a href="#workspace">العودة لمساحة القرار</a>'
          : '<a href="#workspace">افتح القرار ←</a>') +
        "</p></li>";    }
    html += "</ul></section>";
    root.innerHTML = html;
  }

  function paintPublicationTruth(summary) {
    var pub = summary && summary.merchant_publication_v1;
    if (!pub || !pub.ok) return;

    var cartsFocus = document.getElementById("meif-carts-focus-root");
    if (cartsFocus) {
      var cartOps = pub.cart_condition || pub.cart_operational_action || {};
      /* Constitution: Carts owns operational status only — no business decision text. */
      var cartHtml =
        '<section class="cs-ops-banner cs-pub-truth" data-cs-surface="carts">' +
        "<h3>حالة السلال</h3>" +
        "<p>" +
        esc(cartOps.summary_ar || "تقدّم سلال العملاء مستقر.") +
        "</p>" +
        "<p>" +
        esc(cartOps.individual_action_ar || "لا يحتاج إجراءً فردياً الآن.") +
        "</p>" +
        '<p class="cs-ops-banner__cta"><a href="#workspace">عرض القرارات في مساحة القرار ←</a></p>' +
        "</section>";
      var existingCart = cartsFocus.querySelector(
        "[data-cs-surface='carts'].cs-pub-truth"
      );
      if (existingCart) existingCart.outerHTML = cartHtml;
      else cartsFocus.insertAdjacentHTML("afterbegin", cartHtml);
      cartsFocus.hidden = false;
      var meifBanner = document.getElementById("meif-carts-truth-banner");
      if (meifBanner) {
        meifBanner.hidden = true;
        meifBanner.innerHTML = "";
      }
    }

    var commRoot = document.getElementById("meif-communication-root");
    if (commRoot) {
      var cc = pub.communication_condition || {};
      var constrained = !!(cc.constrained || cc.normal_forbidden);
      var meif =
        summary && summary.merchant_experience_integration_v1
          ? summary.merchant_experience_integration_v1
          : null;
      var ops =
        meif &&
        meif.pages &&
        meif.pages.communication &&
        meif.pages.communication.operational_truth
          ? meif.pages.communication.operational_truth
          : {};
      var sent = Number(ops.mock_whatsapp_sent || ops.whatsapp_sent || 0);
      var delivered = Number(ops.delivered_total || ops.whatsapp_delivered || 0);
      var replied = Number(ops.replied_total || ops.customer_replies || 0);
      var returned = Number(ops.returned_total || ops.recovery_success || 0);
      var noPhone = Number(ops.no_phone_total || ops.missing_phone || 0);
      if (!noPhone && summary && summary.home_teaser_inputs_v1) {
        var ht = summary.home_teaser_inputs_v1;
        noPhone = Number(
          (ht.communication && ht.communication.no_phone) || 0
        );
      }
      if (!noPhone && constrained) noPhone = Math.max(noPhone, 1);
      var schedules = Number(ops.recovery_schedules || 0);
      var needsFollow = schedules > 0 || constrained || noPhone > 0;
      var statusAr =
        (cc.summary_ar || "").trim() ||
        (constrained
          ? "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل."
          : "تواصل العملاء يسير بشكل طبيعي.");
      var actions = [];
      if (noPhone > 0 || constrained) {
        actions.push(
          '<a href="#carts?tab=nophone">عرض العملاء بلا رقم ←</a>'
        );
      }
      if (schedules > 0) {
        actions.push(
          '<a href="#carts?tab=waiting">عرض ما بانتظار الإرسال ←</a>'
        );
      }
      actions.push('<a href="#messages">سجل الرسائل ←</a>');
      if (constrained) {
        actions.push('<a href="#whatsapp">ضبط التواصل ←</a>');
      }
      /* Constitution: Communication owns facts + immediate action paths. */
      commRoot.hidden = false;
      commRoot.innerHTML =
        '<section class="cs-ops-banner cs-pub-truth meif-comms" data-cs-surface="communication" data-constitution="communication">' +
        "<h3>حالة التواصل</h3>" +
        "<p>" +
        esc(statusAr) +
        "</p>" +
        '<ul class="meif-facts meif-facts--3">' +
        "<li><strong>" +
        esc(String(sent)) +
        "</strong><span>تم الإرسال</span></li>" +
        "<li><strong>" +
        esc(String(delivered || "—")) +
        "</strong><span>تم التسليم</span></li>" +
        "<li><strong>" +
        esc(String(replied || "—")) +
        "</strong><span>تم الرد</span></li>" +
        "<li><strong>" +
        esc(String(returned || "—")) +
        "</strong><span>عاد العميل</span></li>" +
        "<li><strong>" +
        esc(String(noPhone)) +
        "</strong><span>لا يوجد رقم</span></li>" +
        "<li><strong>" +
        esc(needsFollow ? "نعم" : "لا") +
        "</strong><span>يحتاج متابعة</span></li>" +
        "</ul>" +
        '<p class="cs-ops-banner__cta meif-next">' +
        actions.join(" · ") +
        "</p></section>";
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
