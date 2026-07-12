/**
 * Cart Workspace Grid Presenter V1 — Decision-First operational grid.
 * Paints zones from projection only. No ownership/admission inference.
 * VIP follow-through list is presentation state from merchant UI (optional).
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

  function renderZoneCards(cards, mode) {
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

  function decisionCount(zoneA, zoneB) {
    return (zoneA.length || 0) + (zoneB.length || 0);
  }

  /**
   * @param {object} projection WorkspaceProjection
   * @returns {string} HTML for all zones
   */
  function renderGridHtml(projection) {
    if (!projection || typeof projection !== "object") {
      return '<div class="cw-grid cw-grid--empty" data-cw-empty="1"></div>';
    }
    var zoneA = Array.isArray(projection.zone_a) ? projection.zone_a : [];
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var zoneC = projection.zone_c || {};
    var zoneD = projection.zone_d || {};
    var zoneE = projection.zone_e || null;
    var quiet = !!projection.quiet;
    var following = followingVipCards();
    var openCount = decisionCount(zoneA, zoneB);

    var html = [];
    html.push(
      '<div class="cw-grid" dir="rtl" data-quiet="' +
        (quiet ? "1" : "0") +
        '" data-open-count="' +
        esc(openCount) +
        '">'
    );

    html.push(
      '<div class="cw-grid__scan" aria-live="polite">' +
        '<span class="cw-grid__scan-label">يحتاج قرارك</span>' +
        '<strong class="cw-grid__scan-count">' +
        esc(openCount) +
        "</strong>" +
        "</div>"
    );

    /* Zone A — VIP always visible */
    html.push('<section class="cw-zone cw-zone-a" data-zone="A">');
    html.push('<h2 class="cw-zone__title">VIP</h2>');
    html.push(
      '<p class="cw-zone__hint">أولوية قصوى — المتابعة اليدوية فقط. CartFlow يبقى مسؤولاً عن التنفيذ.</p>'
    );
    if (zoneA.length) {
      html.push(
        '<div class="cw-zone__cards cw-grid-cards">' +
          renderZoneCards(zoneA) +
          "</div>"
      );
    } else {
      html.push(
        '<p class="cw-zone__empty">لا يوجد عملاء VIP يحتاجون قرارك الآن.</p>'
      );
    }
    html.push("</section>");

    /* Presentation: VIP cards merchant is manually following */
    html.push('<section class="cw-zone cw-zone-following" data-zone="FOLLOWING">');
    html.push('<h2 class="cw-zone__title">تتابعه أنت الآن</h2>');
    if (following.length) {
      html.push(
        '<p class="cw-zone__hint">هذه الحالات لم تختفِ — أنت تتابعها يدوياً، وCartFlow يراقب التنفيذ.</p>'
      );
      html.push(
        '<div class="cw-zone__cards cw-grid-cards">' +
          renderZoneCards(following, "following") +
          "</div>"
      );
    } else {
      html.push(
        '<p class="cw-zone__empty">لا توجد حالات تتابعها يدوياً الآن.</p>'
      );
    }
    html.push("</section>");

    /* Zone B — decision grid */
    html.push('<section class="cw-zone cw-zone-b" data-zone="B">');
    html.push('<h2 class="cw-zone__title">ما يحتاج قرارك</h2>');
    if (zoneB.length) {
      html.push(
        '<div class="cw-zone__cards cw-grid-cards">' +
          renderZoneCards(zoneB) +
          "</div>"
      );
    } else if (quiet && !zoneA.length) {
      html.push(
        '<p class="cw-zone__quiet">' +
          esc(
            (zoneC && zoneC.summary) ||
              "لا يوجد ما يحتاج قرارك الآن. CartFlow يتابع الاسترداد."
          ) +
          "</p>"
      );
    } else {
      html.push('<p class="cw-zone__empty">لا توجد قرارات بانتظارك الآن.</p>');
    }
    html.push("</section>");

    /* Zone C — reassurance, not a queue */
    if (zoneC && zoneC.visible !== false) {
      html.push('<section class="cw-zone cw-zone-c" data-zone="C">');
      html.push('<h2 class="cw-zone__title">CartFlow يتابع</h2>');
      html.push(
        '<p class="cw-zone__reassure">' +
          esc(
            zoneC.summary ||
              "CartFlow يعمل على استرداد السلال — لا تحتاج مراجعة كل سلة."
          ) +
          "</p>"
      );
      html.push("</section>");
    }

    /* Zone D — completed rollup, calm */
    html.push('<section class="cw-zone cw-zone-d" data-zone="D">');
    html.push('<h2 class="cw-zone__title">اكتمل مؤخراً</h2>');
    html.push(
      '<p class="cw-zone__rollup">نتائج هادئة: <strong>' +
        esc(zoneD.completed_count == null ? 0 : zoneD.completed_count) +
        "</strong></p>"
    );
    html.push("</section>");

    if (zoneE && typeof zoneE === "object" && (zoneE.summary || zoneE.status)) {
      var eText = zoneE.summary || "";
      /* Skip English/engineering health blobs */
      if (eText && !/[A-Za-z]{4,}/.test(eText)) {
        html.push('<section class="cw-zone cw-zone-e" data-zone="E">');
        html.push('<h2 class="cw-zone__title">حالة التشغيل</h2>');
        html.push("<p>" + esc(eText) + "</p>");
        html.push("</section>");
      }
    }

    html.push("</div>");
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
