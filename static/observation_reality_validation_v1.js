/**
 * Observation Reality Validation V1 — temporary merchant surface.
 * Renders evidence-backed observation findings only. Not Product Intelligence.
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

  function renderFinding(f) {
    if (!f || !f.statement_ar) return "";
    return (
      '<article class="orv-card" data-orv-finding="1" data-capability="' +
      esc(f.capability_id || "") +
      '">' +
      '<p class="orv-card__eyebrow">ملاحظة مرتبطة بأدلة</p>' +
      '<h4 class="orv-card__title" data-orv-title="1">' +
      esc(f.title_ar || "") +
      "</h4>" +
      '<p class="orv-card__statement" data-orv-statement="1">' +
      esc(f.statement_ar || "") +
      "</p>" +
      (f.evidence_summary
        ? '<p class="orv-card__evidence"><strong>الأدلة:</strong> ' +
          esc(f.evidence_summary) +
          "</p>"
        : "") +
      "</article>"
    );
  }

  window.maApplyObservationRealityValidationV1 = function (summary) {
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
    if (!findings.length) {
      root.innerHTML =
        '<section class="orv-surface" data-orv="1">' +
        '<p class="orv-eyebrow">' +
        esc(pkg.eyebrow_ar || "معرفة من الملاحظة") +
        "</p>" +
        "<h3>" +
        esc(pkg.title_ar || "ماذا نلاحظ؟") +
        "</h3>" +
        '<p class="orv-empty">لا ملاحظات مدعومة بأدلة بعد.</p></section>';
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
      esc(pkg.eyebrow_ar || "معرفة من الملاحظة (تجريبي)") +
      "</p>" +
      "<h3>" +
      esc(pkg.title_ar || "ماذا نلاحظ في منتجاتك الآن؟") +
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
