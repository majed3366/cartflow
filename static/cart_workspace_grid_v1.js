/**
 * Cart Workspace Grid — Visual Rebuild V3 (Production Candidate).
 * Cards ARE the page. No section wrappers. Hide empty categories.
 * Header = title + decision counter only.
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
      return '<div class="cw-grid cw-grid--empty" data-cw-empty="1"></div>';
    }

    var zoneA = Array.isArray(projection.zone_a) ? projection.zone_a : [];
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var zoneC = projection.zone_c || {};
    var zoneD = projection.zone_d || {};
    var following = followingVipCards();
    var openCount = zoneA.length + zoneB.length;

    var html = [];
    html.push(
      '<div class="cw-ops" dir="rtl" data-open-count="' + esc(openCount) + '">'
    );

    /* Compact header — title only (counter follows) */
    html.push(
      '<header class="cw-ops__hdr">' +
        '<p class="cw-ops__name">مساحة القرار</p>' +
        "</header>"
    );

    /* Counter */
    html.push(
      '<div class="cw-ops__count" role="status" aria-live="polite">' +
        '<span class="cw-ops__count-label">يحتاج قرارك</span>' +
        '<span class="cw-ops__count-n">' +
        esc(openCount) +
        "</span></div>"
    );

    /* Flat grid — cards only, order: VIP → decisions → following → status */
    html.push('<div class="cw-grid">');

    zoneA.forEach(function (c) {
      html.push(renderCard(c, "decision"));
    });
    zoneB.forEach(function (c) {
      html.push(renderCard(c, "decision"));
    });
    following.forEach(function (c) {
      html.push(renderCard(c, "following"));
    });

    if (zoneC && zoneC.visible !== false && zoneC.active_recovery_indicator) {
      html.push(
        renderCard(
          {
            kind: "auto",
            icon: "🤖",
            title: "CartFlow يعمل",
            sentence: "يتابع الاسترداد تلقائياً",
          },
          "status"
        )
      );
    }

    var done = Number(zoneD.completed_count || 0);
    if (done > 0) {
      html.push(
        renderCard(
          {
            kind: "done",
            icon: "✅",
            title: "النتائج",
            sentence: "تم استرداد",
            metric: done + " · آخر فترة",
          },
          "status"
        )
      );
    }

    html.push("</div>"); /* .cw-grid */
    html.push("</div>"); /* .cw-ops */
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
