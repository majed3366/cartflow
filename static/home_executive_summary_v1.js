/**
 * Home Executive Summary V1 — executive control order.
 * Merchant-safe: no identity diagnostics, no situation_id, no run stamps.
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

  function hideOrvSibling() {
    var orv = document.getElementById("observation-reality-validation-root");
    if (orv) {
      orv.innerHTML = "";
      orv.hidden = true;
    }
  }

  function renderSituationItems(items) {
    if (!Array.isArray(items) || !items.length) return "";
    var html = '<ul class="hes-situation-list" data-hes-situations="1">';
    for (var i = 0; i < items.length; i++) {
      var it = items[i] || {};
      var href = String(it.href || "#workspace");
      html +=
        '<li class="hes-situation-card">' +
        '<p class="hes-situation-card__title">' +
        esc(it.title_ar || it.product_name_ar || "") +
        "</p>" +
        '<p class="hes-situation-card__statement">' +
        esc(it.statement_ar || "") +
        "</p>" +
        '<p class="hes-situation-card__meta">' +
        '<a href="' +
        esc(href) +
        '">وسّع في مساحة القرار ←</a>' +
        "</p></li>";
    }
    html += "</ul>";
    return html;
  }

  function renderSection(sec) {
    if (!sec) return "";
    var countHtml = "";
    var countRaw = sec.count;
    var countOk =
      countRaw !== null &&
      countRaw !== undefined &&
      countRaw !== "" &&
      String(countRaw).toLowerCase() !== "none" &&
      String(countRaw).toLowerCase() !== "null";
    // Hide zero counts on calm sections — reduces noise.
    if (countOk && !(sec.empty && Number(countRaw) === 0)) {
      countHtml =
        '<span class="hes-count" data-hes-count="1">' +
        esc(String(countRaw)) +
        "</span>";
    }
    var statusHtml = sec.status_ar
      ? '<span class="hes-status" data-hes-status="1">' +
        esc(sec.status_ar) +
        "</span>"
      : "";
    var body = "";
    if (sec.id === "situations" && Array.isArray(sec.items) && sec.items.length) {
      body = renderSituationItems(sec.items);
    } else {
      body =
        '<p class="hes-section__summary" data-hes-summary="1">' +
        esc(sec.summary_ar || "") +
        "</p>";
      if (sec.id === "carts" && sec.cart_level_action_ar) {
        body +=
          '<p class="hes-section__note">' +
          esc(sec.cart_level_action_ar) +
          "</p>";
        if (sec.systemic_business_action_ar) {
          body +=
            '<p class="hes-section__note hes-section__note--systemic">' +
            "قرار العمل: " +
            esc(sec.systemic_business_action_ar) +
            ' <a href="#workspace">مساحة القرار ←</a></p>';
        }
      }
    }
    var dominant = sec.dominant || sec.id === "decisions" ? ' data-hes-dominant="1"' : "";
    return (
      '<section class="hes-section' +
      (sec.dominant || sec.id === "decisions" ? " hes-section--dominant" : "") +
      '" data-hes-section="' +
      esc(sec.id || "") +
      '"' +
      dominant +
      (sec.executive_rank
        ? ' data-hes-rank="' + esc(String(sec.executive_rank)) + '"'
        : "") +
      ">" +
      '<div class="hes-section__head">' +
      "<h3>" +
      esc(sec.title_ar || "") +
      "</h3>" +
      '<div class="hes-section__meta">' +
      statusHtml +
      countHtml +
      "</div></div>" +
      body +
      '<p class="hes-section__cta"><a href="' +
      esc(sec.view_details_href || "#") +
      '" data-hes-view-details="' +
      esc(sec.id || "") +
      '">' +
      esc(sec.view_details_ar || "عرض التفاصيل") +
      " ←</a></p>" +
      "</section>"
    );
  }

  function paintShell(root, pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    // Stable executive order by rank when present.
    sections = sections.slice().sort(function (a, b) {
      var ra = parseInt((a && a.executive_rank) || 99, 10);
      var rb = parseInt((b && b.executive_rank) || 99, 10);
      return ra - rb;
    });
    var html =
      '<section class="hes-surface" data-hes="1" data-hes-stabilization="1" data-executive-control="1" aria-label="ملخص تنفيذي">' +
      '<header class="hes-header">' +
      '<p class="hes-eyebrow">' +
      esc(pkg.eyebrow_ar || "ملخص تنفيذي") +
      "</p>" +
      "<h2>" +
      esc(pkg.title_ar || "ماذا يجب أن تعرف الآن؟") +
      "</h2>" +
      '<p class="hes-lede">' +
      esc(pkg.lede_ar || "ملخص سريع فقط — التفاصيل في صفحاتها.") +
      "</p>" +
      "</header>" +
      '<div class="hes-sections">';
    if (!sections.length) {
      html +=
        '<p class="hes-empty" data-hes-attach-empty="1">' +
        esc(pkg.lede_ar || "تعذّر تحميل الملخص — أعد المحاولة.") +
        "</p>";
    } else {
      for (var i = 0; i < sections.length; i++) {
        html += renderSection(sections[i]);
      }
    }
    html +=
      "</div>" +
      '<footer class="hes-ownership">' +
      "<p>الرئيسية تقدّم ما يهم أولاً · مساحة القرار تشرح القرار · المنتجات والسلال والتواصل للتفاصيل التشغيلية.</p>" +
      "</footer></section>";

    root.className = "ma-home-experience hes-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    hideOrvSibling();
  }

  window.maApplyHomeExecutiveSummaryV1 = function (summary) {
    var root =
      document.getElementById("ma-home-experience-root") ||
      document.getElementById("home-executive-summary-root");
    if (!root) return false;
    var pkg =
      summary &&
      summary.home_executive_summary_v1 &&
      typeof summary.home_executive_summary_v1 === "object"
        ? summary.home_executive_summary_v1
        : null;
    if (!pkg || pkg.enabled === false) return false;
    try {
      paintShell(root, pkg);
      return true;
    } catch (e) {
      return false;
    }
  };
})();
