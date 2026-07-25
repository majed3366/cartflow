/**
 * Home Executive Summary V1 — Situation portfolio when Commerce Situations present.
 * Summaries + status + View Details. Single Home paint path.
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
      var sid = String(it.situation_id || "").trim();
      var href = String(it.href || (sid ? "#workspace?situation_id=" + sid : "#workspace"));
      html +=
        '<li class="hes-situation-card" data-situation-id="' +
        esc(sid) +
        '" data-situation-kind="' +
        esc(it.situation_kind || "") +
        '">' +
        '<p class="hes-situation-card__title">' +
        esc(it.title_ar || "") +
        "</p>" +
        '<p class="hes-situation-card__statement">' +
        esc(it.statement_ar || "") +
        "</p>" +
        '<p class="hes-situation-card__meta">' +
        '<span class="hes-situation-id" title="situation_id">' +
        esc(sid) +
        "</span>" +
        ' · <a href="' +
        esc(href) +
        '" data-hes-situation-open="' +
        esc(sid) +
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
    if (countOk) {
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
    }
    return (
      '<section class="hes-section" data-hes-section="' +
      esc(sec.id || "") +
      '"' +
      (sec.id === "situations" ? ' data-hes-portfolio="1"' : "") +
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

  function renderIdentityAudit(identity) {
    if (!identity || typeof identity !== "object") return "";
    var status = String(identity.status || "UNKNOWN");
    var safe =
      identity.CEO_REVIEW_SAFE === true ||
      identity.CEO_REVIEW_SAFE === "TRUE" ||
      identity.CEO_REVIEW_SAFE === "true";
    return (
      '<aside class="hes-rv-audit" data-rv-audit="1" data-rv-status="' +
      esc(status) +
      '" data-ceo-review-safe="' +
      (safe ? "TRUE" : "FALSE") +
      '">' +
      '<p class="hes-rv-audit__status">Status = ' +
      esc(status) +
      "</p>" +
      '<p class="hes-rv-audit__status">CEO_REVIEW_SAFE = ' +
      (safe ? "TRUE" : "FALSE") +
      "</p>" +
      '<p class="hes-rv-audit__line">store=<code>' +
      esc(identity.store_slug || "") +
      "</code> · merchant=<code>" +
      esc(identity.merchant_id || "—") +
      "</code> · run=<code>" +
      esc(identity.simulation_run_id || "—") +
      "</code></p>" +
      '<p class="hes-rv-audit__line">obs=' +
      esc(String(identity.observation_count ?? "—")) +
      " · facts=" +
      esc(String(identity.business_fact_count ?? "—")) +
      " · situations=" +
      esc(String(identity.situation_count ?? "—")) +
      " · home=" +
      esc(String(identity.home_projection ?? "—")) +
      "</p>" +
      (identity.divergence_begins_at
        ? '<p class="hes-rv-audit__div">begins_at: <code>' +
          esc(identity.divergence_begins_at) +
          "</code></p>"
        : "") +
      '<p class="hes-rv-audit__probe"><a href="/dev/reality-validation-context?store=demo&format=html" target="_blank" rel="noopener">شهادة الهوية (CEO) ←</a></p>' +
      "</aside>"
    );
  }

  function paintShell(root, pkg, identity) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    var html =
      '<section class="hes-surface" data-hes="1" data-hes-stabilization="1" aria-label="ملخص تنفيذي">' +
      renderIdentityAudit(identity) +
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
      "<p>الصفحة الرئيسية تقدّم مواقف العمل · مساحة القرار توسّع نفس الموقف · المنتجات/السلال/التواصل تعرض المشاركة فقط.</p>" +
      "</footer></section>";

    root.className = "ma-home-experience hes-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    hideOrvSibling();
  }

  /**
   * Owns Home whenever executive surface mode is claimed.
   * Returns true when this painter claimed the root (blocks legacy painters).
   */
  window.maApplyHomeExecutiveSummaryV1 = function (summary) {
    var mode = summary && summary.home_surface_mode;
    var pkg = (summary && summary.home_executive_summary_v1) || null;
    var claimed =
      mode === "executive_summary_v1" ||
      (pkg && pkg.enabled);
    if (!claimed) return false;

    var root = document.getElementById("ma-home-experience-root");
    if (!root) return false;

    paintShell(
      root,
      pkg && typeof pkg === "object"
        ? pkg
        : {
            ok: false,
            enabled: true,
            sections: [],
            eyebrow_ar: "ملخص تنفيذي",
            title_ar: "ماذا يجب أن تعرف الآن؟",
            lede_ar: "تعذّر تحميل الملخص — أعد المحاولة.",
          },
      summary && summary.reality_validation_identity_v1
    );
    return true;
  };
})();
