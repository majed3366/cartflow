/**
 * CartFlow Merchant UI V2 — Decision Workspace as Decision Objects.
 * Evidence → Understanding → Decision → Action via living route geometry.
 */
(function (global) {
  "use strict";

  function L() {
    return global.CartFlowUiV2Lang || null;
  }

  function esc(s) {
    return L() ? L().esc(s) : String(s == null ? "" : s);
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
      lines = card.evidence_lines_ar
        .map(function (l) {
          return safeAr(l);
        })
        .filter(Boolean);
    }
    if (!lines.length) {
      var one = safeAr(
        card.evidence_ar || card.observation_ar || card.diagnosis_ar || ""
      );
      if (one) lines = [one];
    }
    if (!lines.length) lines = ["ظهرت إشارة تشغيلية تحتاج قرارك الآن."];
    return lines;
  }

  function understanding(card) {
    var ex =
      card.explanation && typeof card.explanation === "object"
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

  function renderDecisionObject(card, isPrimary) {
    var lang = L();
    var lines = evidenceLines(card);
    var density = lang
      ? lang.densityFromCount(lines.length)
      : lines.length >= 3
        ? "dense"
        : "sparse";
    var tension = lang ? lang.tensionFromCard(card) : "low";
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

    var objs = [];
    if (tension === "open" || tension === "high") {
      objs = ["evidence", "insufficient", "uncertainty"];
    } else if (tension === "resolved") {
      objs = ["convergence", "decision", "momentum"];
    } else {
      objs = ["evidence", "attention", "decision"];
    }
    if (!actionReady) objs.push("blocked");
    else objs.push("recovery");

    var html =
      '<article class="cf2-dobj' +
      (isPrimary ? " cf2-dobj--primary" : " cf2-dobj--next") +
      '" data-cf2-tension="' +
      esc(tension) +
      '" data-cf2-evidence="' +
      esc(density) +
      '" data-decision-id="' +
      esc(card.decision_id || "") +
      '">';

    html += '<p class="cf2-dobj__rank">' + esc(rank) + "</p>";
    if (lang) {
      html += '<div class="cf2-co-row">';
      objs.slice(0, 4).forEach(function (k) {
        html += lang.commerceObject(k);
      });
      html += "</div>";
    }

    html +=
      '<div class="cf2-route" data-cf2-tension="' +
      esc(tension) +
      '" data-cf2-grammar="living-route">';

    /* Evidence */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--evidence" data-cf2-node="evidence">';
    html += '<p class="cf2-beat__label">الملاحظة · كثافة الدليل</p>';
    html += '<div class="cf2-dobj__ev-row">';
    if (lang) html += lang.evidenceField(lines.length, density);
    html += '<ul class="cf2-beat__list">';
    lines.forEach(function (line) {
      html += "<li>" + esc(line) + "</li>";
    });
    html += "</ul></div></section>";

    /* Understanding */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--understanding" data-cf2-node="understanding">';
    html += '<p class="cf2-beat__label">ما يعنيه ذلك · توطيد المعنى</p>';
    html +=
      '<p class="cf2-beat__body">' + esc(understanding(card)) + "</p></section>";

    /* Decision mass */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--decision" data-cf2-node="decision">';
    html += '<p class="cf2-beat__label">القرار الآن · كتلة القرار</p>';
    html +=
      '<div class="cf2-dmass" data-cf2-tension="' +
      esc(tension) +
      '"><p class="cf2-dmass__text">' +
      esc(decision) +
      "</p></div></section>";

    /* Action terminus */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--action" data-cf2-node="action">';
    html += '<p class="cf2-beat__label">خطوتك · نهاية المسار</p>';
    html += '<div class="cf2-beat__action">';
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
        '<div class="cf2-reason__wait" data-cf2-grammar="recovery-wait"><p>' +
        esc(safeAr(wait[0], "لا يوجد إجراء حالياً.")) +
        "</p><p>" +
        esc(safeAr(wait[1], "سيخبرك CartFlow عندما يصبح القرار جاهزاً.")) +
        "</p></div>";
    }
    html += "</div></section>";

    html += "</div>";
    html += "</article>";
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
    var html =
      '<div class="cf2-ws cf2-ws--lang" data-cf2="workspace-scene">';
    if (!split.primary) {
      html +=
        '<article class="cf2-dobj cf2-dobj--quiet"><div class="cf2-co-row">';
      if (L()) {
        html += L().commerceObject("attention");
        html += L().commerceObject("uncertainty");
      }
      html +=
        '</div><p class="cf2-dobj__rank">هدوء تشغيلي</p><h3 class="cf2-dmass__text" style="font-size:1.2rem">لا يوجد قرار يحتاج انتباهك الآن.</h3></article>';
      html += '<hr class="cf2-taper" /></div>';
      return html;
    }
    html +=
      '<section class="cf2-ws__primary" aria-label="الأولوية الآن">' +
      renderDecisionObject(split.primary, true) +
      "</section>";
    if (split.next.length) {
      html +=
        '<section class="cf2-ws__next" aria-label="بعده"><p class="cf2-ws__next-label">بعده · مسارات أخف</p><div class="cf2-ws__next-list">';
      split.next.forEach(function (c) {
        html += renderDecisionObject(c, false);
      });
      html += "</div></section>";
    }
    html += '<hr class="cf2-taper" /></div>';
    return html;
  }

  async function loadAndPaint(root) {
    if (!root) return;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل بيئة القرار…</p>';
    try {
      var res = await fetch("/api/cart-workspace/v1/projection", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("projection_http_" + res.status);
      root.innerHTML = render(await res.json());
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
