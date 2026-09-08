/**
 * CartFlow Merchant UI V2 — Decision Workspace
 * Composition Closure + Mobile Hierarchy Refinement V1
 * + Page-Specific Semantic Composition V1: formation body.
 * + Priority Surface Contract V1: commercial Console ≠ operational cards.
 * Meaning lives in evidence → void → mass → terminus.
 * No three-icon semantic clause. READY = zero semantic icons.
 */
(function (global) {
  "use strict";

  var PSC_OPS_LANE_AR = "إجراء تشغيلي مطلوب";
  var PSC_COMMERCIAL_LANE_AR = "المهمة التجارية الحالية";
  var ACCEPTED_STATE_AR = "هذه مهمتك الحالية حتى تُنفَّذ أو تتغير الأدلة.";

  function L() {
    return global.CartFlowUiV2Lang || null;
  }

  function S() {
    return global.CartFlowSemanticVisualV1 || null;
  }

  function esc(s) {
    return L() ? L().esc(s) : String(s == null ? "" : s);
  }

  /* Mission Catalog Product Projection V1 — Workspace binds to catalog primary. */
  function catalogCardToOpp(card) {
    if (!card || typeof card !== "object") return null;
    var c =
      card.commitment && typeof card.commitment === "object"
        ? Object.assign({}, card.commitment)
        : null;
    var phase = String(card.cdc_phase || (c && c.phase) || "");
    if (phase && c && !c.phase) c.phase = phase;
    if (phase && !c) {
      c = { phase: phase };
      if (phase === "UNDER_MEASUREMENT") c.console_mode = "measuring";
      else if (phase === "RECHECK_DUE") c.console_mode = "recheck";
      else if (phase === "ACTION_CHOSEN") c.console_mode = "accepted";
    }
    return {
      opportunity_id: card.opportunity_id,
      family: card.family,
      truth_class: card.truth_class,
      title_ar: card.title_ar,
      why_ar: card.why_ar,
      action_ar: card.action_ar,
      measure_ar: card.measure_ar,
      recheck_ar: card.recheck_ar,
      commitment: c,
      cdc_phase: phase || null,
      mission_ready: !!card.mission_ready,
      mission_ar: card.mission_ar || "",
      diagnosis_ar: card.diagnosis_ar || "",
      catalog_explain_ar: null,
      decision_contract_ar: {
        decision_ar: card.title_ar || "",
        why_now_ar: card.why_ar || "",
        do_this_ar: card.mission_ar || card.action_ar || "",
        dont_ar: card.dont_ar || "",
        measure_ar: card.measure_ar || "",
        recheck_ar: card.recheck_ar || "",
        diagnosis_ar: card.diagnosis_ar || "",
      },
    };
  }

  function catalogPrimaryFromSummary(sum) {
    var cat = sum && sum.mission_catalog_v1;
    if (!cat || typeof cat !== "object" || cat.ok === false) return null;
    var card =
      cat.primary ||
      (cat.workspace && cat.workspace.active_mission) ||
      null;
    var opp = catalogCardToOpp(card);
    /* Priority Surface Contract: only mission-ready may own commercial Console. */
    if (!opp || !opp.mission_ready) return null;
    if (opp && cat.explain && cat.explain.why_this_one_now_ar) {
      opp.catalog_explain_ar = cat.explain.why_this_one_now_ar;
    }
    return opp;
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
      '<article class="cf2-dobj cf2-dobj--primary" data-cf2-organism="formation" data-cf2-priority-contract="v1" data-cf2-priority-lane="operational" data-cf2-tension="' +
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
    html +=
      '<p class="cf2-ws__lane" data-cf2-priority-lane="operational">' +
      esc(PSC_OPS_LANE_AR) +
      "</p>";
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
      '<section class="cf2-col-ws" data-cf2="commercial-opportunity-workspace-v1" data-cf2-col-ws="v1" data-cf2-col-refine="v1" data-cf2-cda="production-v1" data-cf2-priority-contract="v1" data-cf2-priority-lane="commercial"';
    if (opp.commitment && opp.commitment.phase) {
      html +=
        ' data-cf2-commitment-phase="' +
        esc(String(opp.commitment.phase)) +
        '" data-cf2-commercial-continuity="open"';
    }
    html +=
      ' data-cf2-mission="v1" data-cf2-mission-family="' +
      esc(String(opp.family || "")) +
      '" aria-label="' +
      esc(PSC_COMMERCIAL_LANE_AR) +
      '">';
    html +=
      '<p class="cf2-col-ws__lane">' + esc(PSC_COMMERCIAL_LANE_AR) + "</p>";
    if (opp.catalog_explain_ar) {
      html +=
        '<div class="cf2-col-ws__why-now" data-cf2-catalog-explain="1">' +
        '<p class="cf2-col-ws__k">لماذا هذه المهمة الآن؟</p>' +
        '<p class="cf2-col-ws__v">' +
        esc(opp.catalog_explain_ar) +
        "</p></div>";
    }
    if (CDA && CDA.renderOrganism) {
      html += CDA.renderOrganism(opp, {
        arc: arc,
        surface: "workspace",
        eyebrow: PSC_COMMERCIAL_LANE_AR,
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
    html += renderMissionActions(opp);
    html += "</section>";
    return html;
  }

  /* Commercial Mission — CTAs on existing Console. Family copy maps only (B);
     lifecycle phases are server-derived CDC. No new page / visual grammar. */
  var CF2_MISSION_CONFIRM_AR = "أكد إتمام الضبط";
  var CF2_MISSION_CONFIRM_HINT_AR =
    "بعد التأكيد يبدأ CartFlow قياس أثر المهمة.";

  var CF2_MISSION_EXEC = {
    shipping_friction: {
      cta: "اضبط أسباب التردد",
      href: "#settings?area=recovery&focus=shipping-hesitation",
      hint: "يفتح سياسة الاسترجاع عند سببي الشحن ومدة التوصيل. فتح الإعدادات لا يبدأ القياس.",
    },
  };

  var CF2_MISSION_FAMILIES = {
    shipping_friction: {
      confirm: CF2_MISSION_CONFIRM_AR,
      measuring: "تحت القياس — نافذة 7 أيام على حصة أسباب الشحن.",
    },
    price_hesitation: {
      confirm: CF2_MISSION_CONFIRM_AR,
      measuring: "تحت القياس — نافذة 7 أيام على حصة سبب السعر.",
    },
    product_confidence: {
      confirm: CF2_MISSION_CONFIRM_AR,
      measuring: "تحت القياس — نافذة 7 أيام على حصة أسباب ثقة المنتج.",
    },
    product_opportunity_focus: {
      confirm: CF2_MISSION_CONFIRM_AR,
      measuring: "تحت القياس — نافذة 7 أيام على حصة أسباب ثقة المنتج المجمّعة.",
    },
  };

  function renderMissionActions(opp) {
    var family = opp ? String(opp.family || "") : "";
    var copy = CF2_MISSION_FAMILIES[family];
    if (!opp || !copy) return "";
    var c =
      opp.commitment && typeof opp.commitment === "object" ? opp.commitment : null;
    var phase = c && c.phase ? String(c.phase) : "";
    var cid = c && c.commitment_id ? String(c.commitment_id) : "";
    var oid = String(opp.opportunity_id || "");
    var html =
      '<div class="cf2-mission" data-cf2-mission-actions="v1" data-cf2-mission-family="' +
      esc(family) +
      '" data-opportunity-id="' +
      esc(oid) +
      '">';
    var exec = CF2_MISSION_EXEC[family];
    function execLinkHtml() {
      if (!exec || !exec.href) return "";
      return (
        '<a class="cf2-mission__btn cf2-mission__btn--exec" href="' +
        esc(exec.href) +
        '" data-cf2-mission-exec="settings">' +
        esc(exec.cta) +
        '<span class="cf2-mission__btn-cue" data-cf2-mission-cue="gear" aria-hidden="true">' +
        '<svg class="cf2-mission__btn-cue-svg" viewBox="0 0 16 16" width="14" height="14" focusable="false">' +
        '<path fill="currentColor" d="M6.6 1.35h2.8l.32 1.38c.4.11.78.28 1.12.5l1.22-.76 1.98 1.98-.76 1.22c.22.34.39.72.5 1.12l1.38.32v2.8l-1.38.32c-.11.4-.28.78-.5 1.12l.76 1.22-1.98 1.98-1.22-.76a5.2 5.2 0 0 1-1.12.5l-.32 1.38H6.6l-.32-1.38a5.2 5.2 0 0 1-1.12-.5l-1.22.76-1.98-1.98.76-1.22a5.2 5.2 0 0 1-.5-1.12L.85 9.4v-2.8l1.38-.32c.11-.4.28-.78.5-1.12l-.76-1.22L3.95 1.96l1.22.76c.34-.22.72-.39 1.12-.5L6.6 1.35zM8 5.55A2.45 2.45 0 1 0 8 10.45 2.45 2.45 0 0 0 8 5.55z"/>' +
        "</svg></span></a>"
      );
    }
    if (!c || !phase) {
      html +=
        '<button type="button" class="cf2-mission__btn" data-cf2-mission-act="accept">اعتمد هذه المهمة</button>';
      html +=
        '<p class="cf2-mission__hint">القبول يسجّل القرار فقط — لا يبدأ القياس.</p>';
      html += execLinkHtml();
    } else if (phase === "ACTION_CHOSEN") {
      html +=
        '<p class="cf2-mission__status">' +
        esc(ACCEPTED_STATE_AR) +
        "</p>";
      html += execLinkHtml();
      if (exec && exec.hint) {
        html += '<p class="cf2-mission__hint">' + esc(exec.hint) + "</p>";
      }
      html +=
        '<button type="button" class="cf2-mission__btn cf2-mission__btn--quiet" data-cf2-mission-act="confirm" data-commitment-id="' +
        esc(cid) +
        '">' +
        esc(copy.confirm) +
        "</button>";
      html +=
        '<p class="cf2-mission__hint">' +
        esc(CF2_MISSION_CONFIRM_HINT_AR) +
        "</p>";
    } else if (phase === "UNDER_MEASUREMENT") {
      html +=
        '<p class="cf2-mission__status">' + esc(copy.measuring) + "</p>";
    } else if (phase === "RECHECK_DUE") {
      html +=
        '<p class="cf2-mission__status">حان وقت المراجعة — سنعيد قراءة أدلة الفرصة.</p>';
      html +=
        '<button type="button" class="cf2-mission__btn" data-cf2-mission-act="recheck" data-commitment-id="' +
        esc(cid) +
        '">أعد قراءة الأدلة الآن</button>';
    }
    if (c && cid && phase && phase !== "RECHECK_DUE") {
      html +=
        '<button type="button" class="cf2-mission__btn cf2-mission__btn--quiet" data-cf2-mission-act="abandon" data-commitment-id="' +
        esc(cid) +
        '">تراجع عن المهمة</button>';
    }
    html += "</div>";
    return html;
  }

  async function missionPost(path, body) {
    var res = await fetch("/api/commercial-mission/v1/" + path, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : "{}",
      cache: "no-store",
    });
    var data = {};
    try {
      data = await res.json();
    } catch (e) {
      data = {};
    }
    if (!res.ok || data.ok === false) {
      throw new Error((data && data.error) || "mission_http_" + res.status);
    }
    return data;
  }

  async function refreshColFocusFromSummary() {
    var res = await fetch("/api/dashboard/summary", {
      credentials: "same-origin",
      cache: "no-store",
    });
    if (!res.ok) return null;
    var sum = await res.json();
    /* Catalog primary owns commercial Console (Home ↔ Workspace match). */
    var primary = catalogPrimaryFromSummary(sum);
    if (!primary) {
      var col = sum && sum.commercial_opportunity_layer_v1;
      var legacy = col && col.primary;
      var blocked = {
        communication_followup: 1,
        recovery_hesitation: 1,
        cart_behavior: 1,
      };
      if (legacy && !blocked[String(legacy.family || "")]) {
        primary = legacy;
      }
    }
    if (primary && typeof primary === "object") {
      try {
        sessionStorage.setItem("cf2_col_focus_v1", JSON.stringify(primary));
      } catch (e) {}
      return primary;
    }
    return null;
  }

  function bindMissionActions(root) {
    if (!root || root.getAttribute("data-cf2-mission-bound") === "1") return;
    root.setAttribute("data-cf2-mission-bound", "1");
    root.addEventListener("click", function (ev) {
      var t = ev.target;
      if (!t || !t.getAttribute) return;
      var act = t.getAttribute("data-cf2-mission-act");
      if (!act) return;
      if (t.getAttribute("data-cf2-mission-exec")) return;
      ev.preventDefault();
      var cid = t.getAttribute("data-commitment-id") || "";
      t.disabled = true;
      var run = Promise.resolve();
      if (act === "accept") {
        run = missionPost("accept", {});
      } else if (act === "confirm") {
        run = missionPost("confirm-execution", { commitment_id: cid });
      } else if (act === "recheck") {
        run = missionPost("recheck", { commitment_id: cid });
      } else if (act === "abandon") {
        run = missionPost("abandon", { commitment_id: cid });
      } else {
        t.disabled = false;
        return;
      }
      run
        .then(function () {
          return refreshColFocusFromSummary();
        })
        .then(function () {
          return loadAndPaint(root);
        })
        .catch(function (err) {
          t.disabled = false;
          var msg =
            (err && err.message) || "تعذّر إكمال خطوة المهمة.";
          var box = root.querySelector("[data-cf2-mission-actions]");
          if (box) {
            var p = document.createElement("p");
            p.className = "cf2-mission__err";
            p.textContent = msg;
            box.appendChild(p);
          }
        });
    });
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
      '<section class="cf2-ws__primary" aria-label="' +
      esc(PSC_OPS_LANE_AR) +
      '">' +
      renderDecisionObject(split.primary, true, projection) +
      "</section>";
    if (split.next.length) {
      html +=
        '<section class="cf2-ws__next" aria-label="إجراءات تشغيلية تالية"><p class="cf2-ws__next-label">بعده</p><div class="cf2-ws__next-list">';
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
      await refreshColFocusFromSummary();
      var res = await fetch("/api/cart-workspace/v1/projection", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("projection_http_" + res.status);
      root.innerHTML = render(await res.json());
      bindMissionActions(root);
    } catch (e) {
      root.innerHTML =
        '<p class="cf2-error">تعذّر تحميل مساحة القرار. أعد المحاولة.</p>';
    }
  }

  global.CartFlowUiV2Workspace = {
    loadAndPaint: loadAndPaint,
    render: render,
    unwrapProjection: unwrapProjection,
    bindMissionActions: bindMissionActions,
    refreshColFocusFromSummary: refreshColFocusFromSummary,
    catalogPrimaryFromSummary: catalogPrimaryFromSummary,
  };
})(typeof window !== "undefined" ? window : globalThis);
