/**
 * CartFlow Merchant UI V2 — Decision Workspace
 * Composition Closure + Mobile Hierarchy Refinement V1
 * + Page-Specific Semantic Composition V1: formation body.
 * Meaning lives in evidence → void → mass → terminus.
 * No three-icon semantic clause. READY = zero semantic icons.
 */
(function (global) {
  "use strict";

  function L() {
    return global.CartFlowUiV2Lang || null;
  }

  function S() {
    return global.CartFlowSemanticVisualV1 || null;
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
    /* Confidence strength is owned by .cf2-ws__confidence — drop redundant bullets. */
    lines = lines.filter(function (l) {
      return !/مستوى\s*الثقة/i.test(l) && !/^الثقة\s*:/i.test(l);
    });
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

  function confidenceCopy(density) {
    if (density === "LOW") return "الأدلة ما زالت محدودة";
    if (density === "PRESENT") return "توجد أدلة كافية لاتخاذ قرار";
    return "";
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

  function routeProgress(readiness) {
    if (readiness === "READY") return "action";
    if (readiness === "EXTERNAL_DEPENDENCY" || readiness === "BLOCKED") {
      return "decision";
    }
    if (readiness === "NEEDS_MORE_EVIDENCE") return "evidence";
    return "understanding";
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

  /** Page-specific: no shared CO clause — formation relationships carry meaning. */

  function renderDecisionObject(card, isPrimary, projection) {
    var lang = L();
    var sem = S() ? S().projectWorkspace(projection, card) : null;
    var lines = evidenceLines(card);
    var density = sem ? sem.density : "NEUTRAL";
    var readiness = sem ? sem.decision_readiness : "UNKNOWN";
    var waitKind = sem ? sem.wait_kind : "UNKNOWN";
    var tension = sem ? sem.tension : "UNKNOWN";
    var mass = sem ? sem.mass : "OPEN";
    var sufficiency = sem ? sem.evidence_sufficiency : "UNKNOWN";
    var uncertainty = sem ? sem.uncertainty_level : "UNKNOWN";
    var conflict = sem ? sem.evidence_conflict : "UNKNOWN";
    var decision = safeAr(
      card.decision_sentence_ar ||
        card.operational_guidance_ar ||
        card.commitment_ar ||
        "",
      "راجع القرار المطلوب الآن"
    );
    var actionReady = waitKind === "ACTION_REQUIRED";
    var waitingExt = waitKind === "WAITING_EXTERNAL";
    var href = String(card.view_details_href || "").trim();
    var label = safeAr(card.view_details_ar || "", "افتح القرار");
    var wait = Array.isArray(card.action_wait_lines_ar)
      ? card.action_wait_lines_ar
      : ["لا يوجد إجراء حالياً.", "سيخبرك CartFlow عندما يصبح القرار جاهزاً."];
    var conf = confidenceCopy(density);
    var eyebrow = stanceEyebrow(
      readiness === "READY"
        ? "ready"
        : waitKind === "WAITING_EXTERNAL"
          ? "waiting"
          : waitKind === "BLOCKED"
            ? "high"
            : readiness === "NEEDS_MORE_EVIDENCE"
              ? "open"
              : "forming",
      actionReady
    );
    var progress = routeProgress(readiness);
    var showLines = isPrimary ? lines.slice(0, 3) : lines.slice(0, 1);
    var tensionAttr = tension === "HIGH" ? "high" : "none";
    var openness =
      sufficiency === "INSUFFICIENT"
        ? "open"
        : sufficiency === "SUFFICIENT"
          ? "closed"
          : "identity";
    var voidSize =
      uncertainty === "HIGH"
        ? "large"
        : uncertainty === "MEDIUM"
          ? "standard"
          : uncertainty === "NONE"
            ? "remnant"
            : "identity";

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
      '<article class="cf2-dobj cf2-dobj--primary" data-cf2-organism="formation" data-cf2-tension="' +
      esc(tensionAttr) +
      '" data-cf2-mass="' +
      esc(String(mass || "OPEN").toLowerCase()) +
      '" data-cf2-evidence="' +
      esc(String(density || "NEUTRAL").toLowerCase()) +
      '" data-cf2-sufficiency="' +
      esc(String(sufficiency || "UNKNOWN").toLowerCase()) +
      '" data-cf2-uncertainty="' +
      esc(String(uncertainty || "UNKNOWN").toLowerCase()) +
      '" data-cf2-conflict="' +
      esc(String(conflict || "UNKNOWN").toLowerCase()) +
      '" data-cf2-readiness="' +
      esc(readiness) +
      '" data-cf2-wait="' +
      esc(String(waitKind).toLowerCase()) +
      '" data-cf2-progress="' +
      esc(progress) +
      '" data-decision-id="' +
      esc(card.decision_id || "") +
      '">';

    html += '<header class="cf2-ws__head">';
    html += '<div class="cf2-ws__head-text">';
    html += '<p class="cf2-ws__eyebrow">' + esc(eyebrow) + "</p>";
    html +=
      '<h2 class="cf2-ws__title">' + esc(decision) + "</h2>";
    html += "</div></header>";

    html +=
      '<div class="cf2-route" data-cf2-tension="' +
      esc(tensionAttr) +
      '" data-cf2-grammar="living-route-scaffold" data-cf2-progress="' +
      esc(progress) +
      '">';

    /* Evidence — sufficiency lives here, not in a badge */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--evidence' +
      nodeState(progress, "evidence") +
      '" data-cf2-node="evidence" data-cf2-openness="' +
      esc(openness) +
      '">';
    html += '<p class="cf2-beat__label">ما يظهر الآن</p>';
    if (conf) {
      html +=
        '<p class="cf2-ws__confidence">' + esc(conf) + "</p>";
    }
    html += '<div class="cf2-dobj__ev-row">';
    if (lang && lang.evidenceFieldFromSufficiency && density !== "NEUTRAL") {
      html += lang.evidenceFieldFromSufficiency(density);
    }
    html += '<ul class="cf2-beat__list">';
    showLines.forEach(function (line) {
      html += "<li>" + esc(line) + "</li>";
    });
    html += "</ul></div></section>";

    /* Uncertainty / insufficiency void — relationship between evidence and mass */
    if (
      uncertainty === "MEDIUM" ||
      uncertainty === "HIGH" ||
      sufficiency === "INSUFFICIENT" ||
      tensionAttr === "high"
    ) {
      html +=
        '<div class="cf2-ws__void" data-cf2-void="' +
        esc(voidSize === "remnant" || voidSize === "identity" ? "standard" : voidSize) +
        '" data-cf2-tension="' +
        esc(tensionAttr) +
        '" aria-hidden="true"></div>';
    }

    var ogl =
      card.operational_guidance_v1 &&
      typeof card.operational_guidance_v1 === "object"
        ? card.operational_guidance_v1
        : null;
    var oglWs =
      ogl && ogl.workspace_surface && typeof ogl.workspace_surface === "object"
        ? ogl.workspace_surface
        : null;
    var diagnosisAr = safeAr(
      (oglWs && oglWs.diagnosis_ar) || card.diagnosis_ar || ""
    );
    var whyAr = safeAr((oglWs && oglWs.why_ar) || card.why_ar || "");
    var recheckAr = safeAr(
      (oglWs && oglWs.recheck_condition_ar) || card.recheck_condition_ar || ""
    );
    var recAr = safeAr(
      (oglWs && oglWs.recommendation_ar) ||
        card.operational_guidance_ar ||
        ""
    );

    /* Meaning / Diagnosis */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--understanding' +
      nodeState(progress, "understanding") +
      '" data-cf2-node="understanding">';
    html +=
      '<p class="cf2-beat__label">' +
      esc(oglWs ? "التشخيص" : "ماذا يعني") +
      "</p>";
    html +=
      '<p class="cf2-beat__body">' +
      esc(diagnosisAr || understanding(card)) +
      "</p>";
    if (whyAr) {
      html +=
        '<p class="cf2-beat__why"><span class="cf2-beat__why-k">لماذا</span> ' +
        esc(whyAr) +
        "</p>";
    }
    html += "</section>";

    /* Decision mass — recommendation */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--decision' +
      nodeState(progress, "decision") +
      '" data-cf2-node="decision">';
    html +=
      '<p class="cf2-beat__label">' +
      esc(oglWs ? "التوصية" : "ما يقرره CartFlow") +
      "</p>";
    var massClass = "cf2-dmass";
    if (mass === "READY") massClass += " is-ready";
    else massClass += " is-forming";
    if (mass === "HELD") massClass += " is-held";
    html +=
      '<div class="' +
      massClass +
      ' cf2-dmass--echo" data-cf2-mass="' +
      esc(String(mass).toLowerCase()) +
      '" data-cf2-tension="' +
      esc(tensionAttr) +
      '"><p class="cf2-dmass__text">' +
      esc(recAr || decision) +
      "</p></div></section>";

    /* Action terminus + recheck */
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--action' +
      nodeState(progress, "action") +
      '" data-cf2-node="action">';
    html += '<p class="cf2-beat__label">خطوتك الآن</p>';
    html +=
      '<div class="cf2-beat__action cf2-terminus' +
      (actionReady ? " is-armed" : "") +
      '" data-cf2-wait="' +
      esc(String(waitKind).toLowerCase()) +
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
        '<div class="cf2-reason__wait" data-cf2-grammar="recovery-wait">' +
        '<p class="cf2-ws__wait-lead">' +
        esc(
          safeAr(
            (oglWs && oglWs.action_ar) || wait[0],
            "لا يلزم إجراء الآن — واصل المراقبة."
          )
        ) +
        "</p>" +
        '<p class="cf2-ws__wait-note">' +
        esc(
          safeAr(
            recheckAr || wait[1],
            "سيخبرك CartFlow عندما يصبح القرار جاهزاً."
          )
        ) +
        "</p></div>";
    }
    if (recheckAr && (actionReady || waitingExt)) {
      html +=
        '<p class="cf2-ws__recheck" data-cf2-ogl-recheck="1"><span class="cf2-ws__recheck-k">شرط إعادة الفحص</span> ' +
        esc(recheckAr) +
        "</p>";
    }
    html += "</div></section>";

    html += "</div></article>";
    return html;
  }

  function renderQuietEnvironment() {
    var html =
      '<article class="cf2-dobj cf2-dobj--primary cf2-dobj--quiet" data-cf2-organism="formation" data-cf2-composition="page-specific-v1" data-cf2-tension="none" data-cf2-mass="open" data-cf2-readiness="QUIET" data-cf2-evidence="neutral" data-cf2-wait="no_action" data-cf2-progress="evidence" data-cf2-silence="quiet" data-cf2-grammar="core-silence">';
    html += '<header class="cf2-ws__head">';
    html += '<div class="cf2-ws__head-text">';
    html += '<p class="cf2-ws__eyebrow">لا قرار عاجل</p>';
    html +=
      '<h2 class="cf2-ws__title">لا يوجد قرار يحتاج انتباهك الآن</h2>';
    html += "</div></header>";
    html +=
      '<div class="cf2-route" data-cf2-tension="none" data-cf2-grammar="living-route-scaffold" data-cf2-progress="evidence">';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--evidence is-active" data-cf2-node="evidence" data-cf2-openness="identity">';
    html += '<p class="cf2-beat__label">ما يظهر الآن</p>';
    html += '<div class="cf2-dobj__ev-row">';
    html +=
      '<ul class="cf2-beat__list"><li>لا توجد سلة أو إشارة تشغيلية جاهزة للتحوّل إلى قرار الآن.</li></ul>';
    html += "</div></section>";
    /* Quiet remnant void keeps formation relationship readable */
    html +=
      '<div class="cf2-ws__void" data-cf2-void="remnant" data-cf2-tension="none" aria-hidden="true"></div>';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--understanding" data-cf2-node="understanding">';
    html += '<p class="cf2-beat__label">ماذا يعني</p>';
    html +=
      '<p class="cf2-beat__body">هذا صمت تشغيلي صادق — CartFlow يراقب، ولم يتكثّف دليل كافٍ لقرار.</p></section>';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--decision" data-cf2-node="decision">';
    html += '<p class="cf2-beat__label">ما يقرره CartFlow</p>';
    html +=
      '<div class="cf2-dmass is-forming cf2-dmass--echo" data-cf2-mass="open" data-cf2-tension="none"><p class="cf2-dmass__text">واصل المراقبة — لا إجراء مطلوب الآن.</p></div></section>';
    html +=
      '<section class="cf2-route__node cf2-beat cf2-beat--action" data-cf2-node="action">';
    html += '<p class="cf2-beat__label">خطوتك الآن</p>';
    html +=
      '<div class="cf2-beat__action cf2-terminus"><div class="cf2-reason__wait" data-cf2-grammar="recovery-wait"><p class="cf2-ws__wait-lead">لا يوجد إجراء حالياً.</p><p class="cf2-ws__wait-note">سيظهر القرار هنا عندما تتكثّف الإشارة.</p></div></div></section>';
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

  function readColFocus() {
    try {
      if (typeof sessionStorage === "undefined") return null;
      var raw = sessionStorage.getItem("cf2_col_focus_v1");
      if (!raw) return null;
      var opp = JSON.parse(raw);
      return opp && typeof opp === "object" ? opp : null;
    } catch (e) {
      return null;
    }
  }

  function colWsUnit(kind, label, body, mass) {
    var t = String(body || "").trim();
    if (!t) return "";
    return (
      '<div class="cf2-col-ws__unit' +
      (mass ? " cf2-col-ws__unit--mass" : "") +
      '" data-cf2-col-ws-unit="' +
      esc(kind) +
      '">' +
      '<p class="cf2-col-ws__k">' +
      esc(label) +
      "</p>" +
      '<p class="cf2-col-ws__v">' +
      esc(t) +
      "</p></div>"
    );
  }

  function renderColDecision(opp, paintOpts) {
    paintOpts = paintOpts || {};
    if (!opp) return "";
    var CDA =
      typeof global.CartFlowCommercialDecisionArcV1 !== "undefined"
        ? global.CartFlowCommercialDecisionArcV1
        : null;
    /* CDC V1: server-derived commitment.console_mode / phase → CDA arc.
       Without commitment, keep live default arc (recheck_due). */
    var arc = paintOpts.workspaceArc || null;
    if (!arc) {
      var c =
        opp.commitment && typeof opp.commitment === "object"
          ? opp.commitment
          : null;
      var cm = c && c.console_mode ? String(c.console_mode) : "";
      var ph = c && c.phase ? String(c.phase) : "";
      if (cm === "measuring" || ph === "UNDER_MEASUREMENT") {
        arc = "under_measurement";
      } else if (cm === "recheck" || ph === "RECHECK_DUE") {
        arc = "recheck_due";
      } else if (
        cm === "accepted" ||
        ph === "ACTION_CHOSEN"
      ) {
        arc = "action_chosen";
      } else {
        arc = "recheck_due";
      }
    }
    var html =
      '<section class="cf2-col-ws" data-cf2="commercial-opportunity-workspace-v1" data-cf2-col-ws="v1" data-cf2-col-refine="v1" data-cf2-cda="production-v1"';
    if (opp.commitment && opp.commitment.phase) {
      html +=
        ' data-cf2-commitment-phase="' +
        esc(String(opp.commitment.phase)) +
        '"';
    }
    html += ' aria-label="قرار الفرصة التجارية">';
    html += '<p class="cf2-col-ws__lane">قرار تجاري</p>';
    if (CDA && CDA.renderOrganism) {
      html += CDA.renderOrganism(opp, {
        arc: arc,
        surface: "workspace",
        eyebrow: "القرار التجاري",
      });
    } else {
      var dc =
        opp.decision_contract_ar && typeof opp.decision_contract_ar === "object"
          ? opp.decision_contract_ar
          : {};
      html += colWsUnit(
        "decision",
        "القرار",
        dc.decision_ar || opp.title_ar || "",
        true
      );
      html += colWsUnit(
        "why",
        "لماذا الآن؟",
        dc.why_now_ar || opp.why_ar || ""
      );
      html += colWsUnit(
        "do",
        "نفّذ هذا",
        dc.do_this_ar || opp.action_ar || "",
        true
      );
      if (dc.dont_ar) {
        html += colWsUnit("dont", "لا تفعل هذا", dc.dont_ar);
      }
      html += colWsUnit(
        "measure",
        "سنقيس",
        dc.measure_ar || opp.measure_ar || ""
      );
      html += colWsUnit(
        "recheck",
        "سنغير رأينا إذا...",
        dc.recheck_ar || opp.recheck_ar || ""
      );
      var ev =
        opp.evidence && Array.isArray(opp.evidence.lines_ar)
          ? opp.evidence.lines_ar
          : [];
      if (ev.length) {
        html +=
          '<details class="cf2-col-ws__evidence"><summary>عرض الدليل</summary><ul>';
        ev.forEach(function (line) {
          html += "<li>" + esc(line) + "</li>";
        });
        html += "</ul></details>";
      }
    }
    html += "</section>";
    return html;
  }

  function render(payload, paintOpts) {
    var projection = unwrapProjection(payload);
    var zoneB = Array.isArray(projection.zone_b) ? projection.zone_b : [];
    var split = splitPrimary(zoneB);
    var colHtml = renderColDecision(readColFocus(), paintOpts || {});
    var html =
      '<div class="cf2-ws cf2-ws--lang cf2-ws--mobile-hierarchy-v1" data-cf2="workspace-composition-closure-v1" data-cf2-mobile-hierarchy="v1" data-cf2-model="semantic-visual-model-v1" data-cf2-composition="page-specific-v1">';
    if (colHtml) {
      html += colHtml;
    }
    if (!split.primary) {
      if (!colHtml) {
        html +=
          '<section class="cf2-ws__primary" aria-label="هدوء القرار">' +
          renderQuietEnvironment() +
          "</section>";
      }
      html += "</div>";
      return html;
    }
    html +=
      '<section class="cf2-ws__primary" aria-label="القرار الأساسي">' +
      renderDecisionObject(split.primary, true, projection) +
      "</section>";
    if (split.next.length) {
      html +=
        '<section class="cf2-ws__next" aria-label="قرارات تالية"><p class="cf2-ws__next-label">بعده</p><div class="cf2-ws__next-list">';
      split.next.forEach(function (c) {
        html += renderDecisionObject(c, false, projection);
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
