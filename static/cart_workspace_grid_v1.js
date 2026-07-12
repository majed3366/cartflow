/**
 * Cart Workspace Grid Presenter V1 — paints zones A–E from projection only.
 * No ownership/admission/VIP inference. No counter derivation.
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

  function renderZoneCards(cards) {
    var render = cardRenderer();
    if (!render || !Array.isArray(cards) || !cards.length) return "";
    return cards.map(render).join("");
  }

  function label(projection, key, fallback) {
    var zl = (projection && projection.zone_labels) || {};
    return esc(zl[key] || fallback);
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
    var mission = esc(
      projection.mission_question || "ما الذي يحتاج قرارك الآن؟"
    );

    var html = [];
    html.push(
      '<div class="cw-grid" dir="rtl" data-projection-version="' +
        esc(projection.projection_version) +
        '" data-quiet="' +
        (quiet ? "1" : "0") +
        '" data-phase="' +
        esc(projection.workspace_phase || "") +
        '">'
    );

    html.push('<p class="cw-mission" data-from-projection="1">' + mission + "</p>");

    if (zoneA.length) {
      html.push('<section class="cw-zone cw-zone-a" data-zone="A">');
      html.push(
        '<h2 class="cw-zone__title">' + label(projection, "A", "أولوية قصوى (VIP)") + "</h2>"
      );
      html.push(
        '<p class="cw-zone__hint">يحتاج قرارك فوراً — CartFlow يستمر في التنفيذ.</p>'
      );
      html.push('<div class="cw-zone__cards cw-grid-cards">' + renderZoneCards(zoneA) + "</div>");
      html.push("</section>");
    }

    html.push('<section class="cw-zone cw-zone-b" data-zone="B">');
    html.push(
      '<h2 class="cw-zone__title">' + label(projection, "B", "ما يحتاج قرارك") + "</h2>"
    );
    if (zoneB.length) {
      html.push('<div class="cw-zone__cards cw-grid-cards">' + renderZoneCards(zoneB) + "</div>");
    } else if (quiet) {
      html.push(
        '<p class="cw-zone__quiet" data-from-projection="1">' +
          esc((zoneC && zoneC.summary) || "") +
          "</p>"
      );
    } else {
      html.push('<p class="cw-zone__empty">لا توجد قرارات عادية الآن.</p>');
    }
    html.push("</section>");

    if (zoneC && zoneC.visible !== false) {
      html.push('<section class="cw-zone cw-zone-c" data-zone="C">');
      html.push(
        '<h2 class="cw-zone__title">' + label(projection, "C", "CartFlow يعمل الآن") + "</h2>"
      );
      html.push("<p class=\"cw-zone__reassure\">" + esc(zoneC.summary || "") + "</p>");
      html.push("</section>");
    }

    html.push('<section class="cw-zone cw-zone-d" data-zone="D">');
    html.push(
      '<h2 class="cw-zone__title">' + label(projection, "D", "النتائج المكتملة") + "</h2>"
    );
    html.push(
      '<p class="cw-zone__rollup" data-completed-count="' +
        esc(zoneD.completed_count) +
        '">اكتمل مؤخراً: <strong>' +
        esc(zoneD.completed_count == null ? 0 : zoneD.completed_count) +
        "</strong></p>"
    );
    html.push("</section>");

    if (zoneE && typeof zoneE === "object") {
      html.push('<section class="cw-zone cw-zone-e" data-zone="E">');
      html.push(
        '<h2 class="cw-zone__title">' + label(projection, "E", "الصحة التشغيلية") + "</h2>"
      );
      html.push("<p>" + esc(zoneE.summary || "") + "</p>");
      html.push("</section>");
    }

    if (projection.attention_focus_decision_id) {
      html.push(
        '<div class="cw-attention" data-focus-decision-id="' +
          esc(projection.attention_focus_decision_id) +
          '" hidden></div>'
      );
    }

    html.push("</div>");
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
