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
    var measuring = arc === "under_measurement";
    var recheck = arc === "recheck_due";
    var active = arc === "action_chosen";
    var stroke = open ? 0.28 : measuring ? 0.42 : 0.5;
    var dash = open ? "4 5" : "0";
    var html =
      '<svg class="cf-cda__org-svg" viewBox="0 0 24 200" preserveAspectRatio="none" aria-hidden="true">';
    html +=
      '<line class="cf-cda__rail" x1="12" y1="10" x2="12" y2="190" stroke="rgba(8,32,72,' +
      stroke +
      ')" stroke-width="2" stroke-linecap="round" stroke-dasharray="' +
      dash +
      '"/>';
    if (!open) {
      var fill = active ? 0.72 : measuring || recheck ? 0.45 : 0.28;
      html +=
        '<circle class="cf-cda__mass" cx="12" cy="16" r="4" fill="rgba(8,32,72,' +
        fill +
        ')"/>';
    }
    if (recheck) {
      html +=
        '<circle class="cf-cda__recheck-node" cx="12" cy="184" r="3.5" fill="none" stroke="rgba(8,32,72,0.55)" stroke-width="1.6"/>';
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
    var f = fieldsFromOpp(opp, true);

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
      html +=
        '<p class="cf-cda__move"><span class="cf-cda__move-k">القرار</span> ' +
        esc(f.action) +
        "</p>";
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
