/**
 * CartFlow Merchant UI V2 — Decision Workspace Final Product Composition V1
 * Merchant meaning first. Living route + one state object. Home frozen.
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

  function unwrapProjection(payload) {
    if (!payload || typeof payload !== "object") return {};
    if (payload.projection && typeof payload.projection === "object") {
      return payload.projection;
    }
    return payload;
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

  function confidenceCopy(density, tension) {
    if (tension === "open" || density === "insufficient" || density === "sparse") {
      return "الأدلة ما زالت محدودة";
    }
    if (density === "gathering") return "بدأت الإشارة تتكرر";
    if (density === "aligned" || density === "mixed") {
      return "الأدلة أصبحت أكثر اتساقًا";
    }
    if (density === "converging" || tension === "ready" || tension === "resolved") {
      return "توجد أدلة كافية لاتخاذ قرار";
    }
    return "الأدلة ما زالت محدودة";
  }

  function stanceEyebrow(tension, actionReady) {
    if (actionReady || tension === "ready" || tension === "resolved") {
      return "جاهز للقرار";
    }
    if (tension === "waiting") return "بانتظار إشارة";
    if (tension === "high") return "يتطلب انتباهك";
    if (tension === "open") return "يحتاج مزيدًا من الأدلة";
    return "يتشكّل القرار";
  }

  /** One dominant Commerce Object — merchant state, not a gallery. */
  function primaryObjectKind(tension, actionReady) {
    if (actionReady || tension === "ready" || tension === "resolved") {
      return "decision-ready";
    }
    if (tension === "waiting") return "waiting";
    if (tension === "high") return "blocked";
    if (tension === "open") return "insufficient";
    return "decision-forming";
  }

  function routeProgress(tension, actionReady) {
    if (actionReady || tension === "ready" || tension === "resolved") {
      return "action";
    }
    if (tension === "waiting" || tension === "forming") return "decision";
    if (tension === "high") return "understanding";
    return "evidence";
  }

  function nodeState(progress, name) {
    var order = ["evidence", "understanding", "decision", "action"];
    var pi = order.indexOf(progress);
    var ni = order.indexOf(name);
    if (ni < 0) return "";
    if (ni < pi) return " is-complete";
    if (ni === pi) return " is-active";
    return "";
  }

  function silentMark(kind) {
    if (!L()) return "";
    return (
      '<div class="cf2-ws__mark" aria-hidden="true">' +
      L().commerceObject(kind, " ") +
      "</div>"
    );
  }

  function renderDecisionObject(card, isPrimary) {
    var lang = L();
    var lines = evidenceLines(card);
    var density = lang
      ? lang.densityFromCount(lines.length)
      : lines.length >= 3
        ? "converging"
        : lines.length <= 1
          ? "sparse"
          : "gathering";
    var tension = lang ? lang.tensionFromCard(card) : "forming";
    var decision = safeAr(
      card.decision_sentence_ar ||
        card.operational_guidance_ar ||
        card.commitment_ar ||
        "",
      "راجع القرار المطلوب الآن"
    );
    var actionReady =
      card.execution_available === true ||
      String(card.execution_readiness || "") === "READY";
    var waitingExt =
      String(card.execution_readiness || "") === "EXTERNAL_DEPENDENCY";
    var href = String(card.view_details_href || "").trim();
    var label = safeAr(card.view_details_ar || "", "افتح القرار");
    var wait = Array.isArray(card.action_wait_lines_ar)
      ? card.action_wait_lines_ar
      : ["لا يوجد إجراء حالياً.", "سيخبرك CartFlow عندما يصبح القرار جاهزاً."];
    var conf = confidenceCopy(density, tension);
    var eyebrow = stanceEyebrow(tension, actionReady);
    var kind = primaryObjectKind(tension, actionReady || waitingExt);
    var progress = routeProgress(tension, actionReady);
    var showLines = isPrimary ? lines.slice(0, 3) : lines.slice(0, 1);
    var tensionAttr = tension === "ready" ? "resolved" : tension;

    if (!isPrimary) {
      var nextHtml =
        '<article class="cf2-dobj cf2-dobj--next" data-cf2-tension="' +
        esc(tensionAttr) +
        '" data-decision-id="' +
        esc(card.decision_id || "") +
        '">';
      nextHtml +=
        '<p class="cf2-ws__next-title">' + esc(decision) + "</p>";
      if (actionReady && href) {
        nextHtml +=
          '<a class="cf2-btn cf2-btn--quiet" href="' +
          esc(href) +
          '">' +
          esc(label) +
          "</a>";
      } else {
        nextHtml +=
          '<p class="cf2-ws__next-note">' +
          esc(safeAr(wait[0], "انتظر الإشارة.")) +
          "</p>";
      }
      nextHtml += "</article>";
      return nextHtml;
    }

    var html =
      '<article class="cf2-dobj cf2-dobj--primary" data-cf2-tension="' +
      esc(tensionAttr) +
      '" data-cf2-evidence="' +
      esc(density) +
      '" data-cf2-progress="' +
      esc(progress) +
      '" data-decision-id="' +
      esc(card.decision_id || "") +
      '">';

    html += '<header class="cf2-ws__head">';
    html += silentMark(kind);
    html += '<div class="cf2-ws__head-text">';
    html += '<p class="cf2-ws__eyebrow">' + esc(eyebrow) + "</p>";
    html +=
      '<h2 class="cf2-ws__title">' + esc(decision) + "</h2>";
    html += "</div></header>";

    html +=
      '<div class="cf2-route" data-cf2-tension="' +
      esc(tension) +
      '" data-cf2-grammar="living-route" data-cf2-progress="' +
      esc(progress) +
      '">';

    /* Evidence — feeds the decision */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--evidence' +
      nodeState(progress, "evidence") +
      '" data-cf2-node="evidence">';
    html += '<p class="cf2-beat__label">ما يظهر الآن</p>';
    html +=
      '<p class="cf2-ws__confidence">' + esc(conf) + "</p>";
    html += '<div class="cf2-dobj__ev-row">';
    if (lang) {
      html += lang
        .evidenceField(lines.length, density)
        .replace(
          'class="cf2-evfield"',
          'class="cf2-evfield is-arriving"'
        );
    }
    html += '<ul class="cf2-beat__list">';
    showLines.forEach(function (line) {
      html += "<li>" + esc(line) + "</li>";
    });
    html += "</ul></div></section>";

    /* Meaning */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--understanding' +
      nodeState(progress, "understanding") +
      '" data-cf2-node="understanding">';
    html += '<p class="cf2-beat__label">ماذا يعني</p>';
    html +=
      '<p class="cf2-beat__body">' + esc(understanding(card)) + "</p></section>";

    /* Decision mass — dominant */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--decision' +
      nodeState(progress, "decision") +
      '" data-cf2-node="decision">';
    html += '<p class="cf2-beat__label">ما يقرره CartFlow</p>';
    var massClass = "cf2-dmass";
    if (actionReady) massClass += " is-ready";
    else massClass += " is-forming";
    html +=
      '<div class="' +
      massClass +
      '" data-cf2-tension="' +
      esc(tensionAttr) +
      '"><p class="cf2-dmass__text">' +
      esc(decision) +
      "</p></div></section>";

    /* Action terminus */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--action' +
      nodeState(progress, "action") +
      '" data-cf2-node="action">';
    html += '<p class="cf2-beat__label">خطوتك الآن</p>';
    html +=
      '<div class="cf2-beat__action cf2-terminus' +
      (actionReady ? " is-armed" : "") +
      '">';
    if (actionReady && href) {
      html +=
        '<a class="cf2-btn" href="' +
        esc(href) +
        '">' +
        esc(label || "افتح القرار") +
        "</a>";
    } else if (waitingExt && href) {
      html +=
        '<a class="cf2-btn cf2-btn--secondary" href="' +
        esc(href) +
        '">' +
        esc(label || "راجع التفاصيل") +
        "</a>";
      html +=
        '<p class="cf2-ws__wait-note">' +
        esc(safeAr(wait[0], "بانتظار اكتمال شرط خارجي.")) +
        "</p>";
    } else {
      html +=
        '<div class="cf2-reason__wait" data-cf2-grammar="recovery-wait"><p>' +
        esc(safeAr(wait[0], "لا يلزم إجراء الآن — واصل المراقبة.")) +
        "</p><p>" +
        esc(safeAr(wait[1], "سيخبرك CartFlow عندما يصبح القرار جاهزاً.")) +
        "</p></div>";
    }
    html += "</div></section>";

    html += "</div></article>";
    return html;
  }

  function renderQuietEnvironment() {
    var lang = L();
    var html =
      '<article class="cf2-dobj cf2-dobj--primary cf2-dobj--quiet" data-cf2-tension="open" data-cf2-evidence="sparse" data-cf2-progress="evidence" data-cf2-grammar="core-silence">';
    html += '<header class="cf2-ws__head">';
    html += silentMark("waiting");
    html += '<div class="cf2-ws__head-text">';
    html += '<p class="cf2-ws__eyebrow">لا قرار عاجل</p>';
    html +=
      '<h2 class="cf2-ws__title">لا يوجد قرار يحتاج انتباهك الآن</h2>';
    html += "</div></header>";
    html +=
      '<div class="cf2-route" data-cf2-tension="open" data-cf2-grammar="living-route" data-cf2-progress="evidence">';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--evidence is-active" data-cf2-node="evidence">';
    html += '<p class="cf2-beat__label">ما يظهر الآن</p>';
    html +=
      '<p class="cf2-ws__confidence">الأدلة ما زالت محدودة</p>';
    html += '<div class="cf2-dobj__ev-row">';
    if (lang) {
      html += lang
        .evidenceField(1, "sparse")
        .replace(
          'class="cf2-evfield"',
          'class="cf2-evfield is-arriving"'
        );
    }
    html +=
      '<ul class="cf2-beat__list"><li>لا توجد سلة أو إشارة تشغيلية جاهزة للتحوّل إلى قرار الآن.</li></ul>';
    html += "</div></section>";
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--understanding" data-cf2-node="understanding">';
    html += '<p class="cf2-beat__label">ماذا يعني</p>';
    html +=
      '<p class="cf2-beat__body">هذا صمت تشغيلي صادق — CartFlow يراقب، ولم يتكثّف دليل كافٍ لقرار.</p></section>';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--decision" data-cf2-node="decision">';
    html += '<p class="cf2-beat__label">ما يقرره CartFlow</p>';
    html +=
      '<div class="cf2-dmass is-forming" data-cf2-tension="open"><p class="cf2-dmass__text">واصل المراقبة — لا إجراء مطلوب الآن.</p></div></section>';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--action" data-cf2-node="action">';
    html += '<p class="cf2-beat__label">خطوتك الآن</p>';
    html +=
      '<div class="cf2-beat__action cf2-terminus"><div class="cf2-reason__wait"><p>لا يوجد إجراء حالياً.</p><p>سيظهر القرار هنا عندما تتكثّف الإشارة.</p></div></div></section>';
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
    return { primary: primary, next: next.slice(0, 2) };
  }

  function render(payload) {
    var projection = unwrapProjection(payload);
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var split = splitPrimary(zoneB);
    var html =
      '<div class="cf2-ws cf2-ws--lang" data-cf2="workspace-final-v1">';
    if (!split.primary) {
      html +=
        '<section class="cf2-ws__primary" aria-label="هدوء القرار">' +
        renderQuietEnvironment() +
        "</section>";
      html += "</div>";
      return html;
    }
    html +=
      '<section class="cf2-ws__primary" aria-label="القرار الأساسي">' +
      renderDecisionObject(split.primary, true) +
      "</section>";
    if (split.next.length) {
      html +=
        '<section class="cf2-ws__next" aria-label="قرارات تالية"><p class="cf2-ws__next-label">بعده</p><div class="cf2-ws__next-list">';
      split.next.forEach(function (c) {
        html += renderDecisionObject(c, false);
      });
      html += "</div></section>";
    }
    html += "</div>";
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
    unwrapProjection: unwrapProjection,
  };
})(typeof window !== "undefined" ? window : globalThis);
