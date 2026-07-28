/**
 * Cart Workspace Grid — Decision Workspace V2.
 * One Primary Decision + ≤3 Next. No KPI walls. No Home repeat.
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

  function isV2(projection) {
    if (projection && projection.decision_workspace_v2) return true;
    try {
      if (global.CARTFLOW_DECISION_WORKSPACE_V2 === false) return false;
    } catch (e) {
      /* ignore */
    }
    return true;
  }

  function splitPrimaryNext(zoneB) {
    var primary = null;
    var next = [];
    (zoneB || []).forEach(function (c) {
      if (!c || typeof c !== "object") return;
      if (c.is_primary_decision && !primary) {
        primary = c;
      } else {
        next.push(c);
      }
    });
    if (!primary && zoneB && zoneB.length) {
      primary = zoneB[0];
      next = zoneB.slice(1);
    }
    return { primary: primary, next: next.slice(0, 3) };
  }

  function renderGridHtml(projection) {
    if (!projection || typeof projection !== "object") {
      projection = {
        zone_a: [],
        zone_b: [],
        quiet: true,
        mission_question: "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟",
      };
    }

    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var mission = String(
      projection.mission_question || "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟"
    );
    var v2 = isV2(projection);
    var split = splitPrimaryNext(zoneB);
    var hasDecisions = !!(split.primary || (split.next && split.next.length));

    var html = [];
    html.push(
      '<div class="cw-ops cw-ops--decisions-only cw-ops--v2" dir="rtl" data-open-count="' +
        esc(hasDecisions ? 1 + split.next.length : 0) +
        '" data-dw-v2="' +
        (v2 ? "1" : "0") +
        '">'
    );

    // Page question lives once in #cw-constitution-question (no duplicate mission header).
    void mission;

    if (!hasDecisions) {
      html.push('<div class="cw-grid cw-grid--decisions cw-grid--v2">');
      html.push(renderCard({ quiet: true }, "quiet"));
      html.push("</div>");
    } else {
      html.push('<section class="cw-primary-slot" aria-label="القرار الأساسي">');
      if (split.primary) {
        html.push(renderCard(split.primary, "decision"));
      }
      html.push("</section>");

      if (split.next.length) {
        html.push(
          '<section class="cw-next-slot" aria-label="القرارات التالية">' +
            '<p class="cw-next-slot__label">بعد الالتزام — القرارات التالية</p>' +
            '<div class="cw-grid cw-grid--next">'
        );
        split.next.forEach(function (c) {
          html.push(renderCard(c, "decision"));
        });
        html.push("</div></section>");
      }
    }

    html.push("</div>");
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
