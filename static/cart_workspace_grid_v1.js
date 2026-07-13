/**
 * Cart Workspace Grid — Wireframe Contract V1.
 * Cards ARE the page. No section wrappers.
 * Empty decisions: quiet card + working/results/achievements (never blank).
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

  function achievementLabel(zoneD) {
    var raw =
      (zoneD && (zoneD.achievement_amount_ar || zoneD.achievement_label)) || "";
    raw = String(raw).trim();
    return raw || "—";
  }

  function renderGridHtml(projection) {
    if (!projection || typeof projection !== "object") {
      projection = {
        zone_a: [],
        zone_b: [],
        zone_c: { visible: true, active_recovery_indicator: true, summary: "" },
        zone_d: { completed_count: 0 },
      };
    }

    var zoneA = Array.isArray(projection.zone_a) ? projection.zone_a : [];
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var zoneC = projection.zone_c || {};
    var zoneD = projection.zone_d || {};
    var following = followingVipCards();
    var openCount = zoneA.length + zoneB.length;
    var hasDecisions = openCount > 0;

    var html = [];
    html.push(
      '<div class="cw-ops" dir="rtl" data-open-count="' + esc(openCount) + '">'
    );

    /* Compact header — wireframe literal */
    html.push(
      '<header class="cw-ops__hdr">' +
        '<div class="cw-ops__hdr-main">' +
        '<p class="cw-ops__name">مساحة القرار</p>' +
        '<p class="cw-ops__tag">تشغيل متجرك عندما يحتاج قراراً بشرياً.</p>' +
        "</div>" +
        '<p class="cw-ops__count" role="status" aria-live="polite">' +
        "يحتاج قرارك: <strong class=\"cw-ops__count-n\">" +
        esc(openCount) +
        "</strong></p>" +
        "</header>"
    );

    /* Flat grid — cards only */
    html.push('<div class="cw-grid">');

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

    /* CartFlow Working — always present (wireframe + empty-state) */
    html.push(
      renderCard(
        {
          kind: "auto",
          icon: "🤖",
          title: "CartFlow يعمل",
          sentence: "يتابع السلال تلقائياً",
          actionLabel: "عرض التفاصيل",
          actionAsDetails: true,
          detailsBody: String(zoneC.summary || "CartFlow يتابع الاسترداد تلقائياً"),
        },
        "status"
      )
    );

    /* Results — always present */
    var done = Number(zoneD.completed_count || 0);
    html.push(
      renderCard(
        {
          kind: "done",
          icon: "✅",
          title: "النتائج",
          sentence: "تم استرداد " + done + " سلال",
          subline: "آخر 24 ساعة",
        },
        "status"
      )
    );

    /* Achievements — wireframe confidence card (not Home revenue report) */
    html.push(
      renderCard(
        {
          kind: "achieve",
          icon: "📊",
          title: "آخر الإنجازات",
          sentence: achievementLabel(zoneD),
          subline: "اليوم",
        },
        "status"
      )
    );

    html.push("</div>"); /* .cw-grid */
    html.push("</div>"); /* .cw-ops */
    return html.join("");
  }

  global.CartWorkspaceGridV1 = {
    renderGridHtml: renderGridHtml,
  };
})(typeof window !== "undefined" ? window : globalThis);
