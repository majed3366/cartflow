/**
 * Home Executive Summary V1 — Home Stabilization Sprint V1.
 * Summaries + status + counts + View Details only. Single Home paint path.
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

  function renderObsDetails(findings, emptyAr) {
    if (!findings || !findings.length) {
      return (
        '<p class="hes-empty" data-hes-obs-empty="1">' +
        esc(emptyAr || "لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد.") +
        "</p>"
      );
    }
    var html = '<div class="hes-obs-cards">';
    for (var i = 0; i < findings.length; i++) {
      var f = findings[i] || {};
      if (!f.product_name_ar) continue;
      html +=
        '<article class="hes-obs-card" data-hes-obs-card="1">' +
        '<p class="hes-obs-product" data-hes-product="1">' +
        esc(f.product_name_ar || "") +
        "</p>" +
        '<p class="hes-obs-statement" data-hes-statement="1">' +
        esc(f.statement_ar || "") +
        "</p>" +
        (f.confidence_ar
          ? '<span class="hes-conf" data-hes-confidence="1">الثقة: ' +
            esc(f.confidence_ar) +
            "</span>"
          : "") +
        (f.recommended_action_ar
          ? '<p class="hes-obs-action" data-hes-action="1"><strong>الخطوة المقترحة:</strong> ' +
            esc(f.recommended_action_ar) +
            "</p>"
          : "") +
        "</article>";
    }
    return html + "</div>";
  }

  function renderSection(sec, pkg) {
    if (!sec) return "";
    var countHtml = "";
    if (sec.count !== null && sec.count !== undefined && sec.count !== "") {
      countHtml =
        '<span class="hes-count" data-hes-count="1">' +
        esc(String(sec.count)) +
        "</span>";
    }
    var statusHtml = sec.status_ar
      ? '<span class="hes-status" data-hes-status="1">' +
        esc(sec.status_ar) +
        "</span>"
      : "";
    var detailsId = "hes-details-" + esc(sec.id || "x");
    var isObs = sec.id === "observations";
    var detailsBody = "";
    if (isObs) {
      detailsBody = renderObsDetails(
        sec.findings_preview || [],
        sec.empty_state_ar || pkg.empty_state_ar
      );
    } else {
      detailsBody =
        '<p class="hes-details-note">التفاصيل الكاملة في الصفحة المختصة.</p>';
    }
    return (
      '<section class="hes-section" data-hes-section="' +
      esc(sec.id || "") +
      '">' +
      '<div class="hes-section__head">' +
      "<h3>" +
      esc(sec.title_ar || "") +
      "</h3>" +
      '<div class="hes-section__meta">' +
      statusHtml +
      countHtml +
      "</div></div>" +
      '<p class="hes-section__summary" data-hes-summary="1">' +
      esc(sec.summary_ar || "") +
      "</p>" +
      '<p class="hes-section__cta"><a href="' +
      esc(sec.view_details_href || "#") +
      '" data-hes-view-details="' +
      esc(sec.id || "") +
      '" data-hes-details-target="' +
      detailsId +
      '">' +
      esc(sec.view_details_ar || "عرض التفاصيل") +
      " ←</a></p>" +
      '<div id="' +
      detailsId +
      '" class="hes-details" hidden data-hes-details="1">' +
      detailsBody +
      "</div>" +
      "</section>"
    );
  }

  function bindDetails(root) {
    if (!root) return;
    var links = root.querySelectorAll("[data-hes-view-details]");
    for (var i = 0; i < links.length; i++) {
      (function (a) {
        a.addEventListener("click", function (ev) {
          var id = a.getAttribute("data-hes-details-target");
          var href = a.getAttribute("href") || "";
          // Observation expands in-place; other sections navigate.
          if (id && href.indexOf("#home-obs") === 0) {
            ev.preventDefault();
            var panel = document.getElementById(id);
            if (panel) panel.hidden = !panel.hidden;
          }
        });
      })(links[i]);
    }
  }

  function paintShell(root, pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    var html =
      '<section class="hes-surface" data-hes="1" data-hes-stabilization="1" aria-label="ملخص تنفيذي">' +
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
        html += renderSection(sections[i], pkg);
      }
    }
    html +=
      "</div>" +
      '<footer class="hes-ownership">' +
      "<p>الصفحة الرئيسية = ملخص تنفيذي · القرارات في مساحة القرار · السلال للتشغيل · التواصل للمتابعة · الإعدادات للضبط.</p>" +
      "</footer></section>";

    root.className = "ma-home-experience hes-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    bindDetails(root);
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
          }
    );
    return true;
  };
})();
