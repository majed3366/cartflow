/**
 * Home Executive Summary — Home Constitution V2 + Diagnosis Language V1.
 * Merchant-safe: no identity diagnostics, no situation_id, no run stamps.
 * Question appears once in #pagePurpose — not duplicated here.
 * Card body: Diagnosis → Recommendation (never Observation → Recommendation).
 */
(function () {
  "use strict";

  var HOME_QUESTION_AR = "ماذا يجب أن أعرف الآن عن متجري؟";

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

  function renderDiagnosisBody(sec) {
    var diagnosis = String(sec.diagnosis_ar || "").trim();
    var recommendation = String(sec.recommendation_ar || "").trim();
    if (diagnosis || recommendation) {
      var html = "";
      if (diagnosis) {
        html +=
          '<p class="hes-section__diagnosis" data-hes-diagnosis="1">' +
          esc(diagnosis) +
          "</p>";
      }
      if (recommendation) {
        html +=
          '<p class="hes-section__recommendation" data-hes-recommendation="1">' +
          esc(recommendation) +
          "</p>";
      }
      return html;
    }
    return (
      '<p class="hes-section__summary" data-hes-summary="1">' +
      esc(sec.summary_ar || "") +
      "</p>"
    );
  }

  function renderSection(sec) {
    if (!sec) return "";
    // Constitution: never paint bare count badges.
    var statusHtml = sec.status_ar
      ? '<span class="hes-status" data-hes-status="1">' +
        esc(sec.status_ar) +
        "</span>"
      : "";
    var body = renderDiagnosisBody(sec);
    if (sec.id === "carts" && sec.cart_level_action_ar && !sec.empty) {
      // Cart ops note only when it is not a duplicate recommendation.
      var note = String(sec.cart_level_action_ar || "").trim();
      var rec = String(sec.recommendation_ar || "").trim();
      if (note && note !== rec) {
        body +=
          '<p class="hes-section__note">' + esc(note) + "</p>";
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
      ' data-diagnosis="home_diagnosis_language_v1">' +
      '<div class="hes-section__head">' +
      "<h3>" +
      esc(sec.title_ar || "") +
      "</h3>" +
      '<div class="hes-section__meta">' +
      statusHtml +
      "</div></div>" +
      body +
      '<p class="hes-section__cta"><a href="' +
      esc(sec.view_details_href || "#") +
      '" data-hes-view-details="' +
      esc(sec.id || "") +
      '">عرض التفاصيل ←</a></p>' +
      "</section>"
    );
  }

  function paintShell(root, pkg) {
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    sections = sections.slice().sort(function (a, b) {
      var ra = parseInt((a && a.executive_rank) || 99, 10);
      var rb = parseInt((b && b.executive_rank) || 99, 10);
      return ra - rb;
    });
    var errLede = pkg.error || (!sections.length && pkg.lede_ar)
      ? String(pkg.lede_ar || "تعذّر تحميل الملخص — أعد المحاولة.")
      : "";
    var html =
      '<section class="hes-surface" data-hes="1" data-hes-stabilization="1" data-executive-control="1" data-constitution="home_constitution_v2" data-diagnosis-language="home_diagnosis_language_v1" aria-label="' +
      esc(pkg.title_ar || HOME_QUESTION_AR) +
      '">';
    if (errLede && !sections.length) {
      html +=
        '<p class="hes-empty" data-hes-attach-empty="1">' +
        esc(errLede) +
        "</p>";
    } else {
      html += '<div class="hes-sections">';
      for (var i = 0; i < sections.length; i++) {
        html += renderSection(sections[i]);
      }
      html += "</div>";
    }
    html += "</section>";

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
