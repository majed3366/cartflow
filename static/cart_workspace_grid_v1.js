/**
 * Cart Workspace Grid — Gate 2A Constitution.
 * Decisions only. No operational status chrome.
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

  function cardRenderer() {
    return (
      global.CartWorkspaceDecisionCardV1 &&
      global.CartWorkspaceDecisionCardV1.renderDecisionCardHtml
    );
  }

  function renderCard(card, mode) {
    var render = cardRenderer();
    if (!render || !card) return "";
    return render(card, { mode: mode || "decision" });
  }

  function followingVipCards() {
    try {
      if (
        global.CartWorkspaceMerchantV1 &&
        typeof global.CartWorkspaceMerchantV1.getFollowingVip === "function"
      ) {
        return global.CartWorkspaceMerchantV1.getFollowingVip() || [];
      }
    } catch (e) {
      /* ignore */
    }
    return [];
  }

  function renderGridHtml(projection) {
    if (!projection || typeof projection !== "object") {
      projection = {
        zone_a: [],
        zone_b: [],
        quiet: true,
        mission_question: "ماذا يجب أن أقرر الآن، ولماذا؟",
      };
    }

    var zoneA = Array.isArray(projection.zone_a) ? projection.zone_a : [];
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var following = followingVipCards();
    var openCount = zoneA.length + zoneB.length;
    var hasDecisions = openCount > 0;
    var mission = String(
      projection.mission_question || "ماذا يجب أن أقرر الآن، ولماذا؟"
    );

    var html = [];
    var comp = projection.decision_composition_v1 || {};
    var needsN = Number(comp.needs_action_now || 0);
    var monitorN = Number(comp.monitor || 0);
    var landscape = Array.isArray(comp.category_landscape)
      ? comp.category_landscape
      : [];

    html.push(
      '<div class="cw-ops cw-ops--decisions-only cw-ops--portfolio" dir="rtl" data-open-count="' +
        esc(openCount) +
        '" data-gate2a="1" data-gate2b="1" data-gate2c="1">'
    );

    html.push(
      '<header class="cw-ops__hdr">' +
        '<div class="cw-ops__hdr-main">' +
        '<p class="cw-ops__name">مساحة القرار</p>' +
        '<h2 class="cw-ops__mission">' +
        esc(mission) +
        "</h2>" +
        '<p class="cw-ops__subtitle">محفظة القرارات — أولوية مرتبة عبر فئات العمل</p>' +
        (hasDecisions
          ? '<p class="cw-ops__bands">' +
            "يحتاج إجراء الآن: <strong>" +
            esc(needsN || openCount) +
            "</strong>" +
            (monitorN
              ? " · راقب: <strong>" + esc(monitorN) + "</strong>"
              : "") +
            "</p>"
          : '<p class="cw-ops__bands">لا قرار مدعوم حالياً</p>') +
        "</div>" +
        '<p class="cw-ops__count" role="status" aria-live="polite">' +
        "يحتاج قرارك: <strong class=\"cw-ops__count-n\">" +
        esc(openCount) +
        "</strong></p>" +
        "</header>"
    );

    if (landscape.length) {
      html.push('<section class="cw-landscape" aria-label="فئات القرارات">');
      landscape.forEach(function (row) {
        if (!row || typeof row !== "object") return;
        var healthy = !!row.no_action_required;
        html.push(
          '<div class="cw-landscape__item' +
            (healthy ? " cw-landscape__item--healthy" : "") +
            '">' +
            '<span class="cw-landscape__cat">' +
            esc(row.category_ar || row.category || "") +
            "</span>" +
            '<span class="cw-landscape__status">' +
            esc(row.status_ar || row.summary_ar || "") +
            "</span></div>"
        );
      });
      html.push("</section>");
    }

    html.push('<div class="cw-grid cw-grid--decisions">');

    if (!hasDecisions && !following.length) {
      html.push(renderCard({ quiet: true }, "quiet"));
    } else {
      zoneA.forEach(function (c) {
        html.push(renderCard(c, "decision"));
      });
      zoneB.forEach(function (c) {
        html.push(renderCard(c, "decision"));
      });
      following.forEach(function (c) {
        html.push(renderCard(c, "following"));
      });
    }

    html.push("</div>"); /* .cw-grid */
    html.push("</div>"); /* .cw-ops */
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
