/**
 * Observation Reality Validation — entity-bound findings only.
 * Used when Home Executive Summary is off; otherwise HES owns Home paint.
 */
(function () {
  "use strict";

  var EMPTY_AR = "لا توجد أدلة كافية لإصدار ملاحظة مرتبطة بمنتج محدد.";

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function confClass(level) {
    var l = String(level || "").toLowerCase();
    if (l === "high" || l === "very_high") return "orv-conf--high";
    if (l === "medium") return "orv-conf--medium";
    return "orv-conf--low";
  }

  function renderFinding(f) {
    if (!f || !f.product_name_ar || !f.statement_ar) return "";
    var confAr = String(f.confidence_ar || "").trim();
    var action = String(f.recommended_action_ar || "").trim();
    return (
      '<article class="orv-card" data-orv-finding="1">' +
      '<p class="orv-card__product" data-orv-product="1">' +
      esc(f.product_name_ar) +
      "</p>" +
      '<h4 class="orv-card__title" data-orv-title="1">' +
      esc(f.title_ar || "") +
      "</h4>" +
      '<p class="orv-card__statement" data-orv-statement="1">' +
      esc(f.statement_ar) +
      "</p>" +
      (confAr
        ? '<span class="orv-conf ' +
          confClass(f.confidence_level) +
          '" data-orv-confidence="1">الثقة: ' +
          esc(confAr) +
          "</span>"
        : "") +
      (action
        ? '<p class="orv-card__action" data-orv-action="1"><strong>الخطوة المقترحة:</strong> ' +
          esc(action) +
          "</p>"
        : "") +
      "</article>"
    );
  }

  window.maApplyObservationRealityValidationV1 = function (summary) {
    // Home Stabilization — executive surface owns Home; never stack ORV.
    if (summary && summary.home_surface_mode === "executive_summary_v1") {
      var skip = document.getElementById("observation-reality-validation-root");
      if (skip) {
        skip.innerHTML = "";
        skip.hidden = true;
      }
      return false;
    }

    var root = document.getElementById("observation-reality-validation-root");
    if (!root) return false;
    var pkg =
      (summary && summary.observation_reality_validation_v1) || null;
    if (!pkg || !pkg.enabled || !pkg.ok) {
      root.innerHTML = "";
      root.hidden = true;
      return false;
    }
    var findings = Array.isArray(pkg.findings) ? pkg.findings : [];
    findings = findings.filter(function (f) {
      return f && f.product_name_ar && f.statement_ar;
    });
    if (!findings.length) {
      root.innerHTML =
        '<section class="orv-surface" data-orv="1">' +
        '<p class="orv-eyebrow">' +
        esc(pkg.eyebrow_ar || "معرفة من الملاحظة") +
        "</p>" +
        "<h3>" +
        esc(pkg.title_ar || "ملاحظات المنتجات") +
        "</h3>" +
        '<p class="orv-empty" data-orv-empty="1">' +
        esc(pkg.empty_state_ar || EMPTY_AR) +
        "</p></section>";
      root.hidden = false;
      return true;
    }
    var cards = "";
    for (var i = 0; i < findings.length; i++) {
      cards += renderFinding(findings[i]);
    }
    root.innerHTML =
      '<section class="orv-surface" data-orv="1" aria-label="ملاحظات المنتجات">' +
      '<p class="orv-eyebrow">' +
      esc(pkg.eyebrow_ar || "معرفة من الملاحظة") +
      "</p>" +
      "<h3>" +
      esc(pkg.title_ar || "ملاحظات المنتجات") +
      "</h3>" +
      '<p class="orv-lede">' +
      esc(pkg.lede_ar || "") +
      "</p>" +
      '<div class="orv-cards">' +
      cards +
      "</div></section>";
    root.hidden = false;
    return true;
  };
})();
