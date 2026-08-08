/**
 * CartFlow Merchant UI V2 — Decision Workspace painter.
 * Consumes GET /api/cart-workspace/v1/projection → zone_b.
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

  function scrub(s) {
    return String(s || "")
      .replace(/\bcs:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bdiagnostic:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bdce:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bDEMO-[A-Za-z0-9_-]+/g, "")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  function safeAr(s, fallback) {
    var t = scrub(s);
    if (!t) return fallback || "";
    var latin = (t.replace(/\s+/g, "").match(/[A-Za-z]/g) || []).length;
    var total = t.replace(/\s+/g, "").length || 1;
    if (latin / total > 0.42) return fallback || "";
    return t;
  }

  function evidenceLines(card) {
    var lines = [];
    if (Array.isArray(card.evidence_lines_ar)) {
      lines = card.evidence_lines_ar.map(function (l) {
        return safeAr(l);
      }).filter(Boolean);
    }
    if (!lines.length) {
      var one = safeAr(
        card.evidence_ar || card.observation_ar || card.diagnosis_ar || ""
      );
      if (one) lines = [one];
    }
    if (!lines.length) {
      lines = ["ظهرت إشارة تشغيلية تحتاج قرارك الآن."];
    }
    return lines;
  }

  function understanding(card) {
    var ex = card.explanation && typeof card.explanation === "object"
      ? card.explanation
      : {};
    return (
      safeAr(card.ignore_consequence_ar) ||
      safeAr(card.business_consequence_ar) ||
      safeAr(card.next_stake_ar) ||
      safeAr(ex.why_stopped) ||
      safeAr(ex.cartflow_did) ||
      "تركه معلّقاً يبقي ضغط الإيراد دون معالجة واضحة."
    );
  }

  function tensionOf(card) {
    var ready = String(card.execution_readiness || "");
    if (ready === "NEEDS_MORE_EVIDENCE" || ready === "BLOCKED") return "high";
    if (ready === "EXTERNAL_DEPENDENCY") return "open";
    if (
      (ready === "READY" || card.execution_available === true) &&
      card.is_primary_decision
    ) {
      return "resolved";
    }
    return "low";
  }

  function renderCard(card, isPrimary) {
    if (!card) return "";
    var lines = evidenceLines(card);
    var density =
      lines.length >= 3 ? "dense" : lines.length <= 1 ? "sparse" : "mid";
    var tension = tensionOf(card);
    var decision = safeAr(
      card.decision_sentence_ar ||
        card.operational_guidance_ar ||
        card.commitment_ar ||
        "",
      "راجع القرار المطلوب الآن"
    );
    var rank = safeAr(
      card.priority_rank_label_ar,
      isPrimary ? "الأولوية الأولى" : "الأولوية الثانية"
    );
    var actionReady =
      card.execution_available === true ||
      String(card.execution_readiness || "") === "READY" ||
      String(card.execution_readiness || "") === "EXTERNAL_DEPENDENCY";
    var href = String(card.view_details_href || "").trim();
    var label = safeAr(card.view_details_ar || "", "افتح");
    var wait = Array.isArray(card.action_wait_lines_ar)
      ? card.action_wait_lines_ar
      : ["لا يوجد إجراء حالياً.", "سيخبرك CartFlow عندما يصبح القرار جاهزاً."];

    var html =
      '<article class="cf2-reason ' +
      (isPrimary ? "cf2-reason--primary" : "cf2-reason--next") +
      '" data-cf2-evidence="' +
      esc(density) +
      '" data-cf2-tension="' +
      esc(tension) +
      '" data-decision-id="' +
      esc(card.decision_id || "") +
      '">';
    html += '<p class="cf2-reason__rank">' + esc(rank) + "</p>";
    html += '<div class="cf2-reason__flow">';

    html +=
      '<section class="cf2-beat cf2-beat--evidence cf2-evidence"><p class="cf2-beat__label">الملاحظة</p><ul class="cf2-beat__list">';
    lines.forEach(function (line) {
      html += "<li>" + esc(line) + "</li>";
    });
    html += "</ul></section>";

    html +=
      '<section class="cf2-beat cf2-beat--understanding cf2-knowledge"><p class="cf2-beat__label">ما يعنيه ذلك</p><p class="cf2-beat__body">' +
      esc(understanding(card)) +
      "</p></section>";

    html +=
      '<section class="cf2-beat cf2-beat--decision cf2-decision"><p class="cf2-beat__label">القرار الآن</p><p class="cf2-beat__decision">' +
      esc(decision) +
      "</p></section>";

    html +=
      '<section class="cf2-beat cf2-beat--action cf2-recovery"><p class="cf2-beat__label">خطوتك</p><div class="cf2-beat__action">';
    if (actionReady && href) {
      html +=
        '<a class="cf2-btn' +
        (isPrimary ? "" : " cf2-btn--secondary") +
        '" href="' +
        esc(href) +
        '">' +
        esc(label || "افتح") +
        "</a>";
    } else if (!actionReady) {
      html +=
        '<div class="cf2-reason__wait"><p>' +
        esc(safeAr(wait[0], "لا يوجد إجراء حالياً.")) +
        "</p><p>" +
        esc(
          safeAr(wait[1], "سيخبرك CartFlow عندما يصبح القرار جاهزاً.")
        ) +
        "</p></div>";
    }
    html += "</div></section>";

    html += "</div></article>";
    return html;
  }

  function splitPrimary(zoneB) {
    var primary = null;
    var next = [];
    (zoneB || []).forEach(function (c) {
      if (!c) return;
      if (c.is_primary_decision && !primary) primary = c;
      else next.push(c);
    });
    if (!primary && zoneB && zoneB.length) {
      primary = zoneB[0];
      next = zoneB.slice(1);
    }
    return { primary: primary, next: next.slice(0, 3) };
  }

  function render(projection) {
    var zoneB = Array.isArray(projection && projection.zone_b)
      ? projection.zone_b
      : [];
    var split = splitPrimary(zoneB);
    var html = '<div class="cf2-ws" data-cf2="workspace">';
    if (!split.primary) {
      html +=
        '<article class="cf2-reason cf2-reason--quiet"><p class="cf2-reason__rank">هدوء تشغيلي</p><h3>لا يوجد قرار يحتاج انتباهك الآن.</h3></article>';
      html += "</div>";
      return html;
    }
    html +=
      '<section class="cf2-ws__primary" aria-label="الأولوية الآن">' +
      renderCard(split.primary, true) +
      "</section>";
    if (split.next.length) {
      html +=
        '<section class="cf2-ws__next" aria-label="بعده"><p class="cf2-ws__next-label">بعده</p><div class="cf2-ws__next-list">';
      split.next.forEach(function (c) {
        html += renderCard(c, false);
      });
      html += "</div></section>";
    }
    html += '<hr class="cf2-divider" />';
    html += "</div>";
    return html;
  }

  async function loadAndPaint(root) {
    if (!root) return;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل مساحة القرار…</p>';
    try {
      var res = await fetch("/api/cart-workspace/v1/projection", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("projection_http_" + res.status);
      var data = await res.json();
      root.innerHTML = render(data);
    } catch (e) {
      root.innerHTML =
        '<p class="cf2-error">تعذّر تحميل مساحة القرار. أعد المحاولة.</p>';
    }
  }

  global.CartFlowUiV2Workspace = {
    loadAndPaint: loadAndPaint,
    render: render,
  };
})(typeof window !== "undefined" ? window : globalThis);
