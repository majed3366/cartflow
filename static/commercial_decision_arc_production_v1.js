/**
 * Commercial Decision Arc — production V1 (Merchant UI V2).
 * Signature: cf-cda. No intelligence. Presentation only.
 */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function organismSvg(arc) {
    var open = arc === "insufficient_evidence";
    var measuring = arc === "under_measurement" || arc === "recheck_due";
    var recheck = arc === "recheck_due";
    var active = arc === "action_chosen";
    var stroke = open ? 0.4 : measuring ? 0.72 : 0.88;
    var fill = open ? 0.02 : measuring ? 0.04 : 0.055;
    var weight = open ? 1.8 : 2.4;
    var dash = open ? "5 7" : "0";
    var mFill =
      arc === "under_measurement"
        ? 0.55
        : arc === "recheck_due"
          ? 0.72
          : active
            ? 0.12
            : 0;

    var scoop = open
      ? "M 78 22 C 94 22, 104 36, 104 56 L 104 210 C 104 250, 88 275, 58 278 C 32 280, 18 260, 18 235 L 18 56 C 18 34, 34 22, 54 22"
      : "M 78 18 C 92 18, 102 28, 102 48 L 102 200 C 102 248, 92 268, 70 278 C 48 288, 28 278, 22 255 L 22 48 C 22 28, 36 18, 54 18";

    var html =
      '<svg class="cf-cda__org-svg" viewBox="0 0 120 300" preserveAspectRatio="none" aria-hidden="true">';
    html +=
      '<path class="cf-cda__scoop" d="' +
      scoop +
      '" fill="rgba(26,35,50,' +
      fill +
      ')" stroke="rgba(26,35,50,' +
      stroke +
      ')" stroke-width="' +
      weight +
      '" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="' +
      dash +
      '"/>';

    if (!open) {
      var mop = arc === "under_measurement" ? 0.7 : 0.95;
      var mr = arc === "under_measurement" ? 7 : 9;
      html +=
        '<circle class="cf-cda__mass" cx="62" cy="52" r="' +
        mr +
        '" fill="rgba(26,35,50,' +
        mop +
        ')"/>';
    } else {
      html +=
        '<path d="M 40 70 C 55 55, 80 55, 95 70" fill="none" stroke="rgba(26,35,50,0.28)" stroke-width="1.4" stroke-dasharray="3 5"/>';
    }

    if (active || measuring || recheck) {
      var top = active ? 0.85 : measuring ? 0.45 : 0.35;
      html +=
        '<path class="cf-cda__taper" d="M 8 78 L 42 68 L 42 88 Z" fill="rgba(26,35,50,' +
        top +
        ')"/>';
    }

    html +=
      '<path class="cf-cda__measure-track" d="M 102 120 C 108 150, 108 200, 98 240" fill="none" stroke="rgba(26,35,50,0.16)" stroke-width="2.6" stroke-linecap="round"/>';
    if (mFill > 0.08) {
      var len = Math.round(120 * mFill);
      html +=
        '<path class="cf-cda__measure-flow" d="M 102 120 C 108 150, 108 200, 98 240" fill="none" stroke="rgba(26,35,50,0.78)" stroke-width="2.8" stroke-linecap="round" stroke-dasharray="' +
        len +
        ' 160"/>';
      var n = Math.max(1, Math.round(mFill * 4));
      for (var i = 0; i < n; i++) {
        var y = 130 + i * 28;
        html +=
          '<path d="M 92 ' +
          y +
          " L 112 " +
          (y + 8) +
          '" stroke="rgba(26,35,50,0.5)" stroke-width="1.5" stroke-linecap="round"/>';
      }
    }

    if (recheck) {
      html +=
        '<path class="cf-cda__hinge-arm" d="M 98 240 C 110 252, 112 268, 96 278 L 70 278" fill="none" stroke="rgba(26,35,50,0.92)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>';
      html +=
        '<circle cx="96" cy="268" r="3.2" fill="rgba(26,35,50,0.9)"/>';
    } else if (active || measuring) {
      html +=
        '<path class="cf-cda__hinge-arm" d="M 100 250 C 106 258, 106 266, 100 272" fill="none" stroke="rgba(26,35,50,0.22)" stroke-width="1.5" stroke-linecap="round"/>';
    }

    html += "</svg>";
    return html;
  }

  function fieldsFromOpp(opp, useContract) {
    var o = {
      title: "",
      why: "",
      action: "",
      dont: "",
      measure: "",
      recheck: "",
      eyebrow: "",
      evidence: [],
    };
    if (!opp) return o;
    o.title = opp.title_ar || "";
    o.why = opp.why_ar || "";
    o.action = opp.action_ar || "";
    o.measure = opp.measure_ar || "";
    o.recheck = opp.recheck_ar || "";
    o.eyebrow = opp.eyebrow_ar || "";
    if (useContract && opp.decision_contract_ar) {
      var dc = opp.decision_contract_ar;
      o.title = dc.decision_ar || o.title;
      o.why = dc.why_now_ar || o.why;
      o.action = dc.do_this_ar || o.action;
      o.dont = dc.dont_ar || "";
      o.measure = dc.measure_ar || o.measure;
      o.recheck = dc.recheck_ar || o.recheck;
    }
    if (opp.evidence && Array.isArray(opp.evidence.lines_ar)) {
      o.evidence = opp.evidence.lines_ar;
    }
    return o;
  }

  /**
   * @param {object|null} opp
   * @param {{arc?:string, surface?:string, eyebrow?:string, openId?:string}} opts
   */
  function renderOrganism(opp, opts) {
    opts = opts || {};
    var arc = opts.arc || "action_chosen";
    var surface = opts.surface || "home";
    var empty = arc === "insufficient_evidence" || !opp;
    var f = fieldsFromOpp(opp, surface === "workspace");

    var html =
      '<article class="cf-cda" data-cf2="commercial-decision-arc-v1" data-cavi-arc="' +
      esc(arc) +
      '" data-cavi-surface="' +
      esc(surface) +
      '" data-cavi-cohesion="production-v1">';
    html += '<div class="cf-cda__organism">';
    html +=
      '<div class="cf-cda__spine" aria-hidden="true">' +
      organismSvg(arc) +
      "</div>";
    html += '<div class="cf-cda__core">';

    if (empty) {
      html += '<p class="cf-cda__eyebrow">حالة التوصية التجارية</p>';
      html +=
        '<h2 class="cf-cda__decision">لا توصية — الدليل غير كافٍ</h2>';
      html +=
        '<p class="cf-cda__void">' +
        esc(
          opts.emptyCopy ||
            "لا توجد فرصة تجارية جاهزة من أدلة متجرك الآن. CartFlow يمتنع عن التوصية بلا عيّنة كافية."
        ) +
        "</p>";
      html += "</div></div></article>";
      return html;
    }

    html +=
      '<p class="cf-cda__eyebrow">' +
      esc(opts.eyebrow || f.eyebrow || "أهم فرصة تجارية الآن") +
      "</p>";
    html += '<h2 class="cf-cda__decision">' + esc(f.title) + "</h2>";

    if (f.why) {
      html += '<p class="cf-cda__chord">' + esc(f.why) + "</p>";
    }
    if (f.action) {
      html += '<p class="cf-cda__move">' + esc(f.action) + "</p>";
    }
    if (surface === "workspace" && f.dont) {
      html +=
        '<p class="cf-cda__dont"><span class="cf-cda__dont-k">لا تفعل هذا</span> ' +
        esc(f.dont) +
        "</p>";
    }

    if (
      arc === "under_measurement" ||
      arc === "recheck_due" ||
      surface === "workspace"
    ) {
      if (f.measure) {
        html +=
          '<p class="cf-cda__measure"><span class="cf-cda__measure-k">تحت المراقبة</span> ' +
          esc(f.measure) +
          "</p>";
      }
    } else if (arc === "action_chosen" && f.measure) {
      html +=
        '<p class="cf-cda__measure cf-cda__measure--quiet"><span class="cf-cda__measure-k">سنقيس</span> ' +
        esc(f.measure) +
        "</p>";
    }

    if (arc === "recheck_due" || surface === "workspace") {
      if (f.recheck) {
        html += '<div class="cf-cda__hinge-pocket">';
        html +=
          '<p class="cf-cda__hinge-k">سنغير رأينا إذا...</p>';
        html += '<p class="cf-cda__hinge-v">' + esc(f.recheck) + "</p>";
        html += "</div>";
      }
    } else if (arc === "action_chosen" && f.recheck) {
      html +=
        '<p class="cf-cda__recheck-quiet"><span class="cf-cda__measure-k">نعيد النظر</span> ' +
        esc(f.recheck) +
        "</p>";
    }

    if (f.evidence.length) {
      html +=
        '<details class="cf-cda__evidence"><summary>عرض الدليل</summary><ul>';
      f.evidence.forEach(function (line) {
        html += "<li>" + esc(line) + "</li>";
      });
      html += "</ul></details>";
    }

    if (surface === "home" && opts.openId != null) {
      html +=
        '<div class="cf-cda__action"><a class="cf2-btn" href="#workspace" data-cf2-col-open="' +
        esc(opts.openId) +
        '">افتح القرار</a></div>';
    }

    html += "</div></div></article>";
    return html;
  }

  global.CartFlowCommercialDecisionArcV1 = {
    renderOrganism: renderOrganism,
    organismSvg: organismSvg,
    version: "production-v1",
  };
})(typeof window !== "undefined" ? window : globalThis);
