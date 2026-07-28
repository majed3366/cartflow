/**
 * Cart Workspace Grid — Reality UX V1.
 * One Primary (What/Why/Now/Where) + ≤3 Next. No KPI walls.
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
        mission_question: "ما الذي يجب أن أفعله الآن؟",
      };
    }

    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var split = splitPrimaryNext(zoneB);
    var hasDecisions = !!(split.primary || (split.next && split.next.length));

    var html = [];
    html.push(
      '<div class="cw-ops cw-ops--decisions-only cw-ops--v2 cw-ops--refinement cw-ops--r2 cw-ops--reality-ux" dir="rtl" data-open-count="' +
        esc(hasDecisions ? 1 + split.next.length : 0) +
        '" data-dw-v2="1" data-dw-refinement="1" data-dw-r2="1" data-dw-reality-ux="1">'
    );

    if (!hasDecisions) {
      html.push('<div class="cw-grid cw-grid--decisions cw-grid--v2">');
      html.push(renderCard({ quiet: true }, "quiet"));
      html.push("</div>");
    } else {
      html.push('<section class="cw-primary-slot" aria-label="قرارك الآن">');
      if (split.primary) {
        html.push(renderCard(split.primary, "decision"));
      }
      html.push("</section>");

      if (split.next.length) {
        html.push(
          '<section class="cw-next-slot" aria-label="بعده">' +
            '<p class="cw-next-slot__label">بعده</p>' +
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
