/**
 * Cart Workspace Grid — Merchant Experience Rebuild V1.
 * One Primary reasoning object + ≤3 Next. Presentation only.
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
        mission_question: "ما الذي يحتاج انتباهك الآن؟",
      };
    }

    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var split = splitPrimaryNext(zoneB);
    var hasDecisions = !!(split.primary || (split.next && split.next.length));

    var routeCount = hasDecisions ? Math.min(1 + split.next.length, 4) : 0;
    var html = [];
    html.push(
      '<div class="cx-ws cw-ops cw-ops--decisions-only" dir="rtl" data-cx="workspace" data-cf-sig="workspace" data-cf-quiet="' +
        (hasDecisions ? "0" : "1") +
        '" data-cf-route-count="' +
        esc(routeCount) +
        '" data-cf-breathing="' +
        (hasDecisions ? (routeCount === 1 ? "focused" : "active") : "open") +
        '" data-open-count="' +
        esc(hasDecisions ? 1 + split.next.length : 0) +
        '" data-dw-v2="1" data-dw-simplification="1">'
    );

    html.push('<div class="cx-ws__route" data-cf-grammar="living-route">');

    if (!hasDecisions) {
      html.push('<div class="cx-ws__primary">');
      html.push(renderCard({ quiet: true }, "quiet"));
      html.push("</div>");
    } else {
      html.push('<section class="cx-ws__primary cw-primary-slot" aria-label="الأولوية الآن">');
      if (split.primary) {
        html.push(renderCard(split.primary, "decision"));
      }
      html.push("</section>");

      if (split.next.length) {
        html.push(
          '<section class="cx-ws__next cw-next-slot" aria-label="بعده">' +
            '<p class="cx-ws__next-label">بعده</p>' +
            '<div class="cx-ws__next-list cw-grid cw-grid--next">'
        );
        split.next.forEach(function (c) {
          html.push(renderCard(c, "decision"));
        });
        html.push("</div></section>");
      }
    }

    html.push("</div>");
    html.push('<div class="cf-grammar-taper" aria-hidden="true"></div>');
    html.push("</div>");
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
