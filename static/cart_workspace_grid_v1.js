/**
 * Cart Workspace Grid — Visual Rebuild V1.
 * Control center: counter → VIP → decisions → following → auto/completed status.
 * No report sections. No mission paragraphs. No hero.
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

  function renderTiles(cards, mode) {
    var render = cardRenderer();
    if (!render || !Array.isArray(cards) || !cards.length) return "";
    return cards
      .map(function (c) {
        return render(c, { mode: mode || "decision" });
      })
      .join("");
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
      return '<div class="cw-console cw-console--empty" data-cw-empty="1"></div>';
    }

    var zoneA = Array.isArray(projection.zone_a) ? projection.zone_a : [];
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var zoneC = projection.zone_c || {};
    var zoneD = projection.zone_d || {};
    var following = followingVipCards();
    var openCount = zoneA.length + zoneB.length;

    var html = [];
    html.push(
      '<div class="cw-console" dir="rtl" data-open-count="' +
        esc(openCount) +
        '">'
    );

    /* TOP: decision counter only */
    html.push(
      '<div class="cw-counter" role="status" aria-live="polite">' +
        '<span class="cw-counter__label">يحتاج قرارك</span>' +
        '<span class="cw-counter__n">' +
        esc(openCount) +
        "</span>" +
        "</div>"
    );

    /* VIP lane — always first, always visible */
    html.push('<section class="cw-lane cw-lane--vip" data-zone="A">');
    html.push('<div class="cw-lane__bar"><span class="cw-lane__tag">VIP</span></div>');
    if (zoneA.length) {
      html.push(
        '<div class="cw-board">' + renderTiles(zoneA) + "</div>"
      );
    } else {
      html.push('<div class="cw-lane__none">لا يوجد VIP</div>');
    }
    html.push("</section>");

    /* Decisions board */
    html.push('<section class="cw-lane cw-lane--decisions" data-zone="B">');
    if (zoneB.length) {
      html.push(
        '<div class="cw-board">' + renderTiles(zoneB) + "</div>"
      );
    } else if (!zoneA.length) {
      html.push(
        '<div class="cw-lane__none cw-lane__none--calm">لا قرارات الآن</div>'
      );
    }
    html.push("</section>");

    /* Manual follow-through */
    html.push('<section class="cw-lane cw-lane--follow" data-zone="FOLLOWING">');
    html.push(
      '<div class="cw-lane__bar"><span class="cw-lane__tag">تتابعه أنت الآن</span></div>'
    );
    if (following.length) {
      html.push(
        '<div class="cw-board">' +
          renderTiles(following, "following") +
          "</div>"
      );
    } else {
      html.push('<div class="cw-lane__none">—</div>');
    }
    html.push("</section>");

    /* Status row: auto + completed — non-action tiles */
    html.push('<div class="cw-status-row">');
    html.push(
      '<div class="cw-status-tile cw-status-tile--auto" data-zone="C">' +
        '<span class="cw-status-tile__k">CartFlow يعمل الآن</span>' +
        '<span class="cw-status-tile__v">' +
        esc(
          zoneC && zoneC.active_recovery_indicator
            ? "يتابع الاسترداد تلقائياً"
            : "يعمل"
        ) +
        "</span></div>"
    );
    html.push(
      '<div class="cw-status-tile cw-status-tile--done" data-zone="D">' +
        '<span class="cw-status-tile__k">النتائج المكتملة</span>' +
        '<span class="cw-status-tile__v">' +
        esc(zoneD.completed_count == null ? 0 : zoneD.completed_count) +
        "</span></div>"
    );
    html.push("</div>");

    html.push("</div>");
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
