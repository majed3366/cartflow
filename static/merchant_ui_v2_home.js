/**
 * CartFlow Merchant UI V2 — Home executive composition V1.3
 * + Page-Specific Semantic Composition V1: gravity well + satellites.
 * + Priority Surface Contract V1: two explicit lanes (ops vs commercial).
 * Board gravity encodes attention. No repeated attention glyph / CO clause.
 * Current HES truth. semantic-visual-model-v1 drivers unchanged.
 * No frontend ranking — Catalog / OGL / HES owners unchanged.
 */
(function (global) {
  "use strict";

  /* Priority Surface Contract V1 — merchant-facing lane labels (no internal jargon). */
  var PSC_OPS_LANE_AR = "إجراء تشغيلي مطلوب";
  var PSC_OPS_EYEBROW_AR = "ما يلزم تشغيلًا الآن";
  var PSC_COMMERCIAL_QUESTION_AR = "المهمة التجارية الحالية";
  var PSC_COMMERCIAL_EYEBROW_AR = "المهمة التجارية الحالية";
  var PSC_COMMERCIAL_EMPTY_AR = "لا توجد مهمة تجارية جاهزة من أدلة متجرك الآن.";
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

  function escAttr(s) {
    return esc(s).replace(/"/g, "&quot;");
  }

  var LDH_KEY = "cf2_ldh_v1";

  function storeLdh(pkg) {
    try {
      if (pkg && pkg.enabled) {
        sessionStorage.setItem(LDH_KEY, JSON.stringify(pkg));
      } else {
        sessionStorage.removeItem(LDH_KEY);
      }
    } catch (e) {}
    if (
      global.CartFlowUiV2 &&
      typeof global.CartFlowUiV2.refreshContextualSidebar === "function"
    ) {
      global.CartFlowUiV2.refreshContextualSidebar();
    }
  }

  function hierarchyFromSummary(summary) {
    var pkg = summary && summary.live_decision_hierarchy_v1;
    if (pkg && pkg.enabled === true) return pkg;
    return null;
  }

  function ldhBlock(label, body, extraClass) {
    if (!body) return "";
    return (
      '<div class="cf2-ldh__block' +
      (extraClass ? " " + extraClass : "") +
      '">' +
      '<p class="cf2-ldh__label">' +
      esc(label) +
      "</p>" +
      '<p class="cf2-ldh__body">' +
      esc(body) +
      "</p></div>"
    );
  }

  function renderHierarchyHome(ldh, summary) {
    var home = (ldh && ldh.home) || {};
    var now = home.now || null;
    var monitor = Array.isArray(home.monitoring) ? home.monitoring : [];
    var nextM = home.next_mission || null;
    var later = Array.isArray(home.later) ? home.later : [];
    var html =
      '<section class="cf2-home cf2-ldh" data-cf2="live-decision-hierarchy-v1" data-cf2-ldh="1" data-cf2-commercial-status-owner="' +
      escAttr(ldh.commercial_status_owner || "catalog_cdc_portfolio") +
      '" data-cf2-frontend-ranking="0">';
    html +=
      '<header class="cf2-ldh__spine"><p class="cf2-ldh__kicker">' +
      esc(home.question_ar || "ما الذي يستحق انتباهي الآن؟") +
      "</p></header>";
    if (now) {
      html +=
        '<section class="cf2-ldh__group cf2-ldh__group--now" data-cf2-ldh-group="now" data-cf2-mission-family="' +
        escAttr(now.family || "") +
        '">';
      html +=
        '<p class="cf2-ldh__label">' +
        esc(now.group_label_ar || "مهمتك الآن") +
        "</p>";
      html +=
        '<h2 class="cf2-ldh__title">' + esc(now.title_ar || "") + "</h2>";
      if (now.evidence_ar) {
        html +=
          '<p class="cf2-ldh__body cf2-ldh__body--quiet">' +
          esc(now.evidence_ar) +
          "</p>";
      }
      if (now.decision_ar) {
        html +=
          '<p class="cf2-ldh__label">' +
          esc("القرار") +
          "</p>";
        html +=
          '<p class="cf2-ldh__decision">' + esc(now.decision_ar) + "</p>";
      }
      html +=
        '<div class="cf2-ldh__action"><a class="cf2-btn" href="#workspace" data-cf2-col-open="' +
        escAttr(now.opportunity_id || "") +
        '">' +
        esc(now.cta_ar || "افتح القرار") +
        "</a></div>";
      html += "</section>";
    }
    if (monitor.length) {
      html +=
        '<section class="cf2-ldh__group cf2-ldh__group--monitor" data-cf2-ldh-group="monitoring">';
      html +=
        '<p class="cf2-ldh__label">' +
        esc(monitor[0].group_label_ar || "تحت المراقبة") +
        "</p>";
      monitor.forEach(function (row) {
        html +=
          '<p class="cf2-ldh__body" data-cf2-ldh-secondary="' +
          escAttr(row.family || "") +
          '" data-cf2-ldh-portfolio="' +
          escAttr(row.portfolio_state || "") +
          '">' +
          esc(row.body_ar || "") +
          "</p>";
      });
      html += "</section>";
    }
    if (nextM && nextM.family) {
      html +=
        '<section class="cf2-ldh__group cf2-ldh__group--next" data-cf2-ldh-group="next">';
      html +=
        '<p class="cf2-ldh__label">' +
        esc(nextM.group_label_ar || "المهمة التجارية التالية") +
        "</p>";
      if (nextM.title_ar) {
        html += '<p class="cf2-ldh__body">' + esc(nextM.title_ar) + "</p>";
      }
      html += "</section>";
    }
    if (later.length) {
      html +=
        '<section class="cf2-ldh__group cf2-ldh__group--later" data-cf2-ldh-group="later">';
      html +=
        '<p class="cf2-ldh__label">' + esc("لاحقاً") + "</p>";
      later.forEach(function (row) {
        html +=
          '<p class="cf2-ldh__body" data-cf2-ldh-deferred="1">' +
          esc(row.title_ar || row.family || "") +
          "</p>";
      });
      html += "</section>";
    }
    html += "</section>";
    return html;
  }

  /* Mission Catalog Product Projection V1 — consume server catalog only (no rerank). */
  function phaseStatusAr(phase) {
    var p = String(phase || "");
    if (p === "ACTION_CHOSEN") return ACCEPTED_STATE_AR;
    if (p === "UNDER_MEASUREMENT") return "تحت القياس";
    if (p === "RECHECK_DUE") return "حان وقت المراجعة";
    return "جاهزة للتنفيذ";
  }

  function isCompetingMostImportantAr(t) {
    var s = String(t || "").trim();
    if (!s) return false;
    /* Suppress legacy competing “most important” titles if upstream still emits them. */
    if (/^أهم قرار اليوم$/.test(s)) return true;
    if (/^ما أهم/.test(s)) return true;
    if (/^أين توجد أهم/.test(s)) return true;
    if (/^أهم (مهمة|فرصة) تجارية الآن$/.test(s)) return true;
    return false;
  }

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
      eyebrow_ar: PSC_COMMERCIAL_EYEBROW_AR,
      commitment: c,
      cdc_phase: phase || null,
      mission_ar: card.mission_ar || "",
      diagnosis_ar: card.diagnosis_ar || "",
      workspace_href: card.workspace_href || "#workspace",
      mission_ready: !!card.mission_ready,
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

  function missionCatalogToColLayer(cat) {
    if (!cat || typeof cat !== "object" || cat.ok === false) return null;
    var primaryCard = cat.primary || (cat.home && cat.home.primary) || null;
    var secs = Array.isArray(cat.secondaries)
      ? cat.secondaries
      : cat.home && Array.isArray(cat.home.secondaries)
        ? cat.home.secondaries
        : [];
    var primary = catalogCardToOpp(primaryCard);
    /* Priority Surface Contract: col_only must not masquerade as commercial mission. */
    if (primary && !primary.mission_ready) {
      primary = null;
    }
    var secondaries = secs
      .map(catalogCardToOpp)
      .filter(function (s) {
        return s && s.mission_ready;
      })
      .slice(0, 2);
    /* Presence of primary wins — never paint insufficient when catalog selected one. */
    var isEmpty = !primary;
    return {
      ok: true,
      enabled: true,
      empty: isEmpty,
      question_ar: PSC_COMMERCIAL_QUESTION_AR,
      empty_state_ar: isEmpty
        ? (cat.explain && cat.explain.why_this_one_now_ar) ||
          PSC_COMMERCIAL_EMPTY_AR
        : "",
      primary: primary,
      secondaries: isEmpty ? [] : secondaries,
      explain: cat.explain || null,
      suppressed_count: Number(cat.suppressed_count || 0) || 0,
      source: "mission_catalog_v1",
    };
  }

  function resolveCommercialLayer(summary) {
    var cat =
      summary &&
      summary.mission_catalog_v1 &&
      typeof summary.mission_catalog_v1 === "object"
        ? summary.mission_catalog_v1
        : null;
    var projected = missionCatalogToColLayer(cat);
    if (projected) return projected;
    var legacy =
      summary &&
      summary.commercial_opportunity_layer_v1 &&
      typeof summary.commercial_opportunity_layer_v1 === "object"
        ? summary.commercial_opportunity_layer_v1
        : null;
    if (!legacy) return null;
    /* Fallback COL paint — still enforce commercial-lane contract (no ops masquerade). */
    var blocked = {
      communication_followup: 1,
      recovery_hesitation: 1,
      cart_behavior: 1,
    };
    var primary = legacy.primary;
    if (primary && blocked[String(primary.family || "")]) {
      primary = null;
    }
    var secs = Array.isArray(legacy.secondaries) ? legacy.secondaries : [];
    secs = secs.filter(function (s) {
      return s && !blocked[String(s.family || "")];
    });
    return {
      ok: legacy.ok !== false,
      enabled: legacy.enabled !== false,
      empty: !primary,
      question_ar: PSC_COMMERCIAL_QUESTION_AR,
      empty_state_ar: legacy.empty_state_ar || PSC_COMMERCIAL_EMPTY_AR,
      primary: primary
        ? Object.assign({}, primary, { eyebrow_ar: PSC_COMMERCIAL_EYEBROW_AR })
        : null,
      secondaries: primary ? secs.slice(0, 2) : [],
      explain: legacy.explain || null,
      suppressed_count: Number(legacy.suppressed_count || 0) || 0,
      source: "commercial_opportunity_layer_v1",
    };
  }

  var currentView = "overview";
  var lastSummaryPayload = null;
  var lastSummaryRoot = null;

  function laneOf(sec) {
    var id = String((sec && sec.id) || "");
    if (id === "decisions") return "decision";
    if (id === "health") return "condition";
    if (id === "observations" || id === "situations") return "evidence";
    if (id === "carts") return "momentum";
    if (id === "communication") return "recovery";
    return "knowledge";
  }

  function statusNeedsFollow(status) {
    var s = String(status || "").trim();
    return s === "يتطلب متابعة" || s === "يحتاج تدخلاً عاجلاً";
  }

  function truthText(sec) {
    return String(
      (sec && (sec.diagnosis_ar || sec.summary_ar || sec.recommendation_ar)) || ""
    )
      .replace(/\s+/g, " ")
      .trim();
  }

  function isDuplicateTruth(primaryText, secText) {
    var a = String(primaryText || "")
      .replace(/\s+/g, " ")
      .trim();
    var b = String(secText || "")
      .replace(/\s+/g, " ")
      .trim();
    if (!a || !b) return false;
    if (a === b) return true;
    var short = a.length <= b.length ? a : b;
    var long = a.length <= b.length ? b : a;
    if (short.length < 28) return false;
    var needle = short.slice(0, Math.min(56, short.length));
    return long.indexOf(needle) !== -1;
  }

  function split(sections) {
    var list = (sections || []).slice().sort(function (a, b) {
      return (
        parseInt((a && a.executive_rank) || 99, 10) -
        parseInt((b && b.executive_rank) || 99, 10)
      );
    });
    var primary = null;
    var i;
    for (i = 0; i < list.length; i++) {
      if (list[i] && (list[i].dominant || list[i].id === "decisions")) {
        primary = list[i];
        break;
      }
    }
    if (!primary && list.length) primary = list[0];
    var primaryTruth = truthText(primary);
    var rest = list.filter(function (s) {
      return s && s !== primary && !isDuplicateTruth(primaryTruth, truthText(s));
    });
    var know = [];
    var watch = [];
    var learning = [];
    rest.forEach(function (sec) {
      var lane = laneOf(sec);
      var diag = truthText(sec);
      var status = String(sec.status_ar || "");
      if (lane === "condition" || statusNeedsFollow(status)) {
        know.push(sec);
      } else if (lane === "evidence" || sec.empty) {
        learning.push(sec);
      } else {
        watch.push(sec);
      }
    });
    return {
      primary: primary,
      know: know.slice(0, 2),
      watch: watch.slice(0, 2),
      learning: learning.slice(0, 2),
    };
  }

  function confidenceCopy(density) {
    if (density === "LOW") return "الأدلة ما زالت محدودة";
    if (density === "PRESENT") return "توجد أدلة كافية لاتخاذ قرار";
    return "";
  }

  function actionCopy(meaning, sufficiency) {
    if (sufficiency === "INSUFFICIENT") {
      return "لا يلزم تغيير تجاري الآن — واصل المراقبة حتى تتضح الإشارة.";
    }
    if (meaning) return meaning;
    return "راجع التفاصيل عندما تكون جاهزًا لاتخاذ قرار.";
  }

  function sceneSpine() {
    return (
      '<header class="cf2-home__spine">' +
      '<p class="cf2-home__kicker">مشهد تنفيذي</p>' +
      '<p class="cf2-home__spine-line">الحالة · الدليل · المعنى · القرار</p>' +
      "</header>"
    );
  }

  /** Momentum is NOT_CURRENTLY_SUPPORTED — never emit a semantic journey. */
  /** Page-specific composition: no shared CO clause / attention glyph as page badge. */

  function roleLabelForSection(sec) {
    var id = String((sec && sec.id) || "");
    if (id === "health") return "الحالة";
    if (id === "decisions") return "ما يحتاج انتباهًا";
    if (id === "situations" || id === "observations") return "الأثر";
    if (id === "carts") return "ما تغيّر";
    if (id === "communication") return "الخطوة التالية";
    return "ما تغيّر";
  }

  function satelliteDistance(tier) {
    if (tier === "know") return "near";
    if (tier === "watch") return "mid";
    return "far";
  }

  function monitorItem(sec, tier) {
    var diagnosis = truthText(sec);
    var html =
      '<article class="cf2-home__monitor-item cf2-home__satellite" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '" data-cf2-lane="' +
      esc(laneOf(sec)) +
      '" data-cf2-satellite="1" data-cf2-distance="' +
      esc(satelliteDistance(tier)) +
      '">';
    html +=
      '<p class="cf2-home__tier">' + esc(roleLabelForSection(sec)) + "</p>";
    html +=
      '<h3 class="cf2-home__monitor-title">' +
      esc(sec.title_ar || "") +
      "</h3>";
    if (diagnosis) {
      html +=
        '<p class="cf2-home__monitor-body">' + esc(diagnosis) + "</p>";
    }
    html += "</article>";
    return html;
  }

  function floorItem(sec, tier) {
    var diagnosis = truthText(sec);
    var html =
      '<article class="cf2-home__item" data-hes-section="' +
      esc(sec.id || "") +
      '" data-cf2-tier="' +
      esc(tier) +
      '">';
    html +=
      '<p class="cf2-home__tier">' + esc(roleLabelForSection(sec)) + "</p>";
    html +=
      '<h3 class="cf2-home__item-title">' + esc(sec.title_ar || "") + "</h3>";
    if (diagnosis) {
      html +=
        '<p class="cf2-home__item-body">' + esc(diagnosis) + "</p>";
    }
    html += "</article>";
    return html;
  }

  /**
   * Recovery outcome summary — operational AbandonedCart recovered + cart_value only.
   * Not purchase-attribution SAR. No invented metrics.
   */
  function recoveryOutcomeHtml(summary) {
    if (!summary || typeof summary !== "object") return "";
    var countRaw = summary.merchant_kpi_recovered_fmt;
    var valueRaw = summary.merchant_kpi_revenue_fmt;
    var countOk = countRaw != null && String(countRaw).trim() !== "";
    var valueOk = valueRaw != null && String(valueRaw).trim() !== "";
    if (!countOk && !valueOk) return "";
    var countLine = countOk
      ? esc(String(countRaw)) + " سلة مسترجعة"
      : "عدد السلال المسترجعة غير متاح";
    var valueLine = valueOk
      ? esc(String(valueRaw)) + " قيمة السلال المسترجعة"
      : "قيمة الاسترجاع المنسوبة غير متاحة من عقد الإسناد";
    return (
      '<aside class="cf2-home__recovery" data-cf2-recovery="operational-kpi-v1" aria-label="خلاصة نتيجة الاسترجاع">' +
      '<p class="cf2-home__recovery-label">نتيجة الاسترجاع · اليوم</p>' +
      '<p class="cf2-home__recovery-line">' +
      countLine +
      " · " +
      valueLine +
      "</p>" +
      '<p class="cf2-home__recovery-note">حسب حالة السلة المسترجعة وقيمتها التشغيلية — وليس إسناد شراء منسوباً.</p>' +
      "</aside>"
    );
  }

  /** Dedicated الملخص destination — operational outcomes only. */
  function renderSummaryView(summary) {
    if (!summary || typeof summary !== "object") {
      return (
        '<section class="cf2-home cf2-home--summary" data-cf2="home-summary-v1" data-cf2-view="summary">' +
        '<p class="cf2-empty">تعذّر تحميل ملخص النتائج.</p></section>'
      );
    }
    var recovery = recoveryOutcomeHtml(summary);
    var waSent = summary.merchant_kpi_wa_sent_fmt;
    var abandoned = summary.merchant_kpi_abandoned_fmt;
    var html =
      '<section class="cf2-home cf2-home--summary" data-cf2="home-summary-v1" data-cf2-view="summary" data-cf2-truth="operational-kpi-v1">';
    html += sceneSpine();
    html += '<header class="cf2-home__summary-head">';
    html += '<p class="cf2-home__kicker">الملخص</p>';
    html += '<h2 class="cf2-home__title">نتائج تشغيلية · اليوم</h2>';
    html +=
      '<p class="cf2-home__summary-period">الفترة: اليوم (تشغيل CartFlow — وليس تحليلات متجر)</p>';
    html += "</header>";
    html += recovery || '<p class="cf2-empty">لا توجد نتائج استرجاع مسجّلة لليوم.</p>';
    html += '<div class="cf2-home__summary-grid">';
    if (abandoned != null && String(abandoned).trim() !== "") {
      html +=
        '<article class="cf2-home__summary-item"><p class="cf2-home__summary-label">سلال مهجورة · اليوم</p><p class="cf2-home__summary-value">' +
        esc(String(abandoned)) +
        "</p></article>";
    }
    if (waSent != null && String(waSent).trim() !== "") {
      html +=
        '<article class="cf2-home__summary-item"><p class="cf2-home__summary-label">رسائل واتساب · اليوم</p><p class="cf2-home__summary-value">' +
        esc(String(waSent)) +
        "</p></article>";
    }
    html += "</div>";
    html += '<hr class="cf2-taper" /></section>';
    return html;
  }

  function isStaleMerchantCopy(t) {
    var s = String(t || "");
    if (!s) return false;
    if (s.indexOf("لا يستطيع CartFlow") >= 0) return true;
    if (s.indexOf("واصل جمع الأدلة") >= 0) return true;
    if (s.indexOf("راجع نصوص سبب") >= 0) return true;
    if (s.indexOf("الودجت") >= 0 || s.indexOf("الودجيت") >= 0) return true;
    if (s.indexOf("تحديد السبب التشغيلي") >= 0) return true;
    if (s.indexOf("غير كافية لتحديد") >= 0) return true;
    return false;
  }

  function sectionHasStaleMerchantCopy(sec) {
    if (!sec) return false;
    return (
      isStaleMerchantCopy(sec.summary_ar) ||
      isStaleMerchantCopy(sec.title_ar) ||
      isStaleMerchantCopy(sec.diagnosis_ar) ||
      isStaleMerchantCopy(sec.recommendation_ar)
    );
  }

  function isReadyCommercialFamily(fam) {
    var f = String(fam || "");
    return (
      f === "shipping_friction" ||
      f === "price_hesitation" ||
      f === "product_confidence"
    );
  }

  function commercialContractGuide(col) {
    var p = col && col.primary;
    if (!p || !p.mission_ready || !isReadyCommercialFamily(p.family)) return null;
    var dc = p.decision_contract_ar && typeof p.decision_contract_ar === "object"
      ? p.decision_contract_ar
      : {};
    var see = String(dc.why_now_ar || p.why_ar || "").trim();
    var means = String(dc.diagnosis_ar || p.diagnosis_ar || "").trim();
    var doNow = String(p.action_ar || "").trim();
    var recheck = String(dc.recheck_ar || p.recheck_ar || "").trim();
    if (!see && !means && !doNow) return null;
    return { see: see, means: means, doNow: doNow, recheck: recheck };
  }

  function guidanceHomeSurface(pkg, col) {
    var contract = commercialContractGuide(col);
    var g =
      pkg && pkg.operational_guidance_v1 && typeof pkg.operational_guidance_v1 === "object"
        ? pkg.operational_guidance_v1
        : null;
    var hs = g && g.ok && g.home_surface && typeof g.home_surface === "object"
      ? g.home_surface
      : null;
    var ogl = hs
      ? {
          see: String(hs.what_we_see_ar || "").trim(),
          means: String(hs.what_it_means_ar || "").trim(),
          doNow: String(hs.what_to_do_now_ar || "").trim(),
          recheck: String(hs.when_to_recheck_ar || "").trim(),
        }
      : { see: "", means: "", doNow: "", recheck: "" };
    if (isStaleMerchantCopy(ogl.see)) ogl.see = "";
    if (isStaleMerchantCopy(ogl.means)) ogl.means = "";
    if (isStaleMerchantCopy(ogl.doNow)) ogl.doNow = "";
    if (contract) {
      return {
        see: contract.see || ogl.see,
        means: contract.means || ogl.means,
        doNow: contract.doNow || ogl.doNow,
        recheck: contract.recheck || ogl.recheck,
      };
    }
    if (!ogl.see && !ogl.means && !ogl.doNow) return null;
    return ogl;
  }

  function storeColFocus(opp) {
    try {
      if (opp && typeof sessionStorage !== "undefined") {
        sessionStorage.setItem("cf2_col_focus_v1", JSON.stringify(opp));
      }
    } catch (e) {}
  }

  function colUnit(kind, label, body) {
    var t = String(body || "").trim();
    if (!t) return "";
    return (
      '<div class="cf2-col__unit" data-cf2-col-unit="' +
      escAttr(kind) +
      '">' +
      '<p class="cf2-col__k">' +
      esc(label) +
      "</p>" +
      '<p class="cf2-col__v">' +
      esc(t) +
      "</p></div>"
    );
  }

  function renderColLayer(col, paintOpts) {
    paintOpts = paintOpts || {};
    if (!col || col.enabled === false || !col.ok) return "";
    var CDA =
      typeof global.CartFlowCommercialDecisionArcV1 !== "undefined"
        ? global.CartFlowCommercialDecisionArcV1
        : null;
    var fromCatalog = col.source === "mission_catalog_v1";
    var html =
      '<section class="cf2-col" data-cf2="commercial-opportunity-layer-v1" data-cf2-col="v1" data-cf2-col-refine="v1" data-cf2-cda="production-v1" data-cf2-model="semantic-visual-model-v1" data-cf2-priority-contract="v1" data-cf2-priority-lane="commercial"';
    if (fromCatalog) {
      html += ' data-cf2-mission-catalog="v1"';
    }
    html += ' aria-label="' + escAttr(PSC_COMMERCIAL_QUESTION_AR) + '">';
    html +=
      '<p class="cf2-col__question">' +
      esc(PSC_COMMERCIAL_QUESTION_AR) +
      "</p>";
    if (!col.primary) {
      if (CDA && CDA.renderOrganism) {
        html += CDA.renderOrganism(null, {
          arc: "insufficient_evidence",
          surface: "home",
          emptyCopy: col.empty_state_ar || PSC_COMMERCIAL_EMPTY_AR,
        });
      } else {
        html +=
          '<p class="cf2-col__empty">' +
          esc(col.empty_state_ar || PSC_COMMERCIAL_EMPTY_AR) +
          "</p>";
      }
      html += "</section>";
      return html;
    }
    var p = col.primary;
    var phase =
      (p.commitment && p.commitment.phase) || p.cdc_phase || "";
    var arc = paintOpts.homeArc || null;
    if (!arc) {
      var c =
        p.commitment && typeof p.commitment === "object" ? p.commitment : null;
      var cm = c && c.console_mode ? String(c.console_mode) : "";
      var ph = String(phase || "");
      if (cm === "measuring" || ph === "UNDER_MEASUREMENT") {
        arc = "under_measurement";
      } else if (cm === "recheck" || ph === "RECHECK_DUE") {
        arc = "recheck_due";
      } else if (cm === "accepted" || ph === "ACTION_CHOSEN") {
        arc = "action_chosen";
      } else {
        arc = "action_chosen";
      }
    }
    html +=
      '<div class="cf2-col__primary" data-cf2-col-role="primary" data-cf2-col-mass="decision"';
    if (phase) {
      html +=
        ' data-cf2-commitment-phase="' +
        escAttr(String(phase)) +
        '" data-cf2-commercial-continuity="open"';
    }
    if (p.family) {
      html += ' data-cf2-mission-family="' + escAttr(String(p.family)) + '"';
    }
    html += ">";
    html +=
      '<p class="cf2-col__phase" data-cf2-mission-phase-label="1">' +
      esc(phaseStatusAr(phase)) +
      "</p>";
    if (CDA && CDA.renderOrganism) {
      html += CDA.renderOrganism(p, {
        arc: arc,
        surface: "home",
        eyebrow: PSC_COMMERCIAL_EYEBROW_AR,
        openId: p.opportunity_id || "",
      });
    } else {
      html +=
        '<p class="cf2-col__eyebrow">' +
        esc(PSC_COMMERCIAL_EYEBROW_AR) +
        "</p>";
      html += '<h2 class="cf2-col__title">' + esc(p.title_ar || "") + "</h2>";
      html += colUnit("why", "لماذا الآن؟", p.why_ar);
      html += colUnit("move", "الحركة الآن", p.action_ar);
      html += colUnit("measure", "سنقيس", p.measure_ar);
      html += colUnit("recheck", "نعيد النظر", p.recheck_ar);
      html +=
        '<div class="cf2-col__action"><a class="cf2-btn" href="#workspace" data-cf2-col-open="' +
        escAttr(p.opportunity_id || "") +
        '">افتح القرار</a></div>';
    }
    if (col.explain && col.explain.why_this_one_now_ar) {
      html +=
        '<div class="cf2-col__why-now" data-cf2-catalog-explain="1">' +
        '<p class="cf2-col__k">لماذا هذه المهمة الآن؟</p>' +
        '<p class="cf2-col__v">' +
        esc(col.explain.why_this_one_now_ar) +
        "</p></div>";
    }
    html += "</div>";

    var secs = Array.isArray(col.secondaries) ? col.secondaries.slice(0, 2) : [];
    if (secs.length) {
      html +=
        '<div class="cf2-col__secondaries" data-cf2-col-tier="secondary" data-cf2-col-compress="v1_1" aria-label="مهام تالية">';
      secs.forEach(function (s) {
        var why =
          String(s.priority_why_ar || "").trim() ||
          String(s.why_ar || "").trim();
        var act = String(s.action_ar || "").trim();
        var line = why;
        if (act) {
          line = why ? why + " · " + act : act;
        }
        var title = String(s.title_ar || "").trim();
        html +=
          '<article class="cf2-col__secondary cf2-col__secondary--signal" data-cf2-col-role="secondary">';
        html +=
          '<h3 class="cf2-col__sec-title">' + esc(title) + "</h3>";
        if (line) {
          html += '<p class="cf2-col__sec-line">' + esc(line) + "</p>";
        }
        /* Secondaries stay lighter — no Decision Console handoff (primary owns Workspace). */
        html += "</article>";
      });
      html += "</div>";
    }
    if (fromCatalog && Number(col.suppressed_count || 0) > 0) {
      html +=
        '<p class="cf2-col__deferred" data-cf2-catalog-deferred="1">' +
        esc(
          "هناك فرص أخرى مؤجلة لأن مهمة أعلى أولوية جارية."
        ) +
        "</p>";
    }
    html += "</section>";
    return html;
  }

  function bindColActions(root, col) {
    if (!root || !col) return;
    var map = {};
    /* Workspace continuity: only primary may become focus. */
    if (col.primary) map[String(col.primary.opportunity_id || "")] = col.primary;
    root.querySelectorAll("[data-cf2-col-open]").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-cf2-col-open") || "";
        if (map[id]) storeColFocus(map[id]);
        else if (col.primary) storeColFocus(col.primary);
      });
    });
  }

  function resolveOperationalLeadTitle(sec, guide, col) {
    var p = col && col.primary;
    if (p && p.mission_ready && isReadyCommercialFamily(p.family)) {
      var contractTitle = String(p.title_ar || "").replace(/\s+/g, " ").trim();
      if (contractTitle && !isStaleMerchantCopy(contractTitle)) return contractTitle;
    }
    var candidates = [
      sec && sec.summary_ar,
      guide && guide.doNow,
      guide && guide.see,
      sec && sec.recommendation_ar,
      sec && sec.diagnosis_ar,
      sec && sec.title_ar,
    ];
    var i;
    for (i = 0; i < candidates.length; i++) {
      var t = String(candidates[i] || "")
        .replace(/\s+/g, " ")
        .trim();
      if (!t || isCompetingMostImportantAr(t) || isStaleMerchantCopy(t)) continue;
      return t;
    }
    return PSC_OPS_LANE_AR;
  }

  function render(pkg, summary, paintOpts) {
    var ldh = hierarchyFromSummary(summary);
    if (ldh) {
      storeLdh(ldh);
      return renderHierarchyHome(ldh, summary);
    }
    storeLdh(null);
    var col = resolveCommercialLayer(summary);
    var colHtml = renderColLayer(col, paintOpts);
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    if (!sections.length) {
      return (
        '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-truth="empty" data-cf2-silence="quiet" data-cf2-priority-contract="v1">' +
        sceneSpine() +
        '<p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        "</p>" +
        '<hr class="cf2-taper" /></section>' +
        colHtml
      );
    }
    var parts = split(sections);
    var lang = L();
    var guide = guidanceHomeSurface(pkg, col);
    var html =
      '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-model="semantic-visual-model-v1" data-cf2-organism="gravity-well" data-cf2-composition="page-specific-v1" data-cf2-ogl="v1" data-cf2-priority-contract="v1">';
    html += sceneSpine();

    if (!parts.primary) {
      html +=
        '<p class="cf2-empty">' +
        esc(pkg.lede_ar || "لا تتوفر معرفة كافية الآن.") +
        "</p>" +
        '<hr class="cf2-taper" /></section>';
      return html + colHtml;
    }

    var p = parts.primary;
    var why = truthText(p);
    var meaning = String(p.recommendation_ar || "").trim();
    var href = String(p.view_details_href || "").trim();
    var sem = S() ? S().projectHomeSurface(pkg, p) : null;
    var silence = sem ? sem.core_silence : "ACTIVE";
    var density = sem ? sem.density : "NEUTRAL";
    var attention = sem ? sem.attention_intensity : "NONE";
    var confidence = confidenceCopy(density);
    var action = actionCopy(meaning, sem ? sem.evidence_sufficiency : "UNKNOWN");
    var boardEdge =
      silence === "QUIET"
        ? "quiet"
        : attention === "PRIMARY"
          ? "attention"
          : "neutral";
    var gravity =
      silence === "QUIET" || attention === "NONE"
        ? "none"
        : attention === "PRIMARY"
          ? "primary"
          : "secondary";

    var hideStaleMonitor = !!commercialContractGuide(col);
    var monitor = [];
    function pushMonitor(sec, tier) {
      if (hideStaleMonitor && sectionHasStaleMerchantCopy(sec)) return;
      monitor.push({ sec: sec, tier: tier });
    }
    parts.know.forEach(function (sec) {
      pushMonitor(sec, "know");
    });
    parts.watch.forEach(function (sec) {
      pushMonitor(sec, "watch");
    });
    parts.learning.forEach(function (sec) {
      pushMonitor(sec, "learning");
    });
    monitor = monitor.slice(0, 3);
    var monitorIds = {};
    monitor.forEach(function (r) {
      if (r.sec && r.sec.id) monitorIds[r.sec.id] = true;
    });

    html +=
      '<div class="cf2-home__board" data-cf2-edge="' +
      esc(boardEdge) +
      '" data-cf2-gravity="' +
      esc(gravity) +
      '" data-cf2-attention="' +
      esc(String(attention || "NONE").toLowerCase()) +
      '" data-cf2-silence="' +
      esc(silence.toLowerCase()) +
      '" data-cf2-monitor="' +
      (monitor.length ? "on" : "empty") +
      '">';

    /* ——— Operational obligation lane (Priority Surface Contract V1) ——— */
    html +=
      '<div class="cf2-home__scene" data-cf2-priority-lane="operational" aria-label="' +
      escAttr(PSC_OPS_LANE_AR) +
      '">';
    html += '<div class="cf2-home__lead">';
    html += '<div class="cf2-home__lead-text">';
    html +=
      '<p class="cf2-home__lane">' + esc(PSC_OPS_LANE_AR) + "</p>";
    html +=
      '<p class="cf2-home__eyebrow">' + esc(PSC_OPS_EYEBROW_AR) + "</p>";
    html +=
      '<h2 class="cf2-home__title">' +
      esc(resolveOperationalLeadTitle(p, guide, col)) +
      "</h2>";
    html += "</div></div>";

    if (guide) {
      html +=
        '<div class="cf2-home__ogl" data-cf2-ogl-home="1">';
      if (guide.see) {
        html +=
          '<p class="cf2-home__ogl-row"><span class="cf2-home__ogl-k">ما نراه</span> ' +
          esc(guide.see) +
          "</p>";
      }
      if (guide.means) {
        html +=
          '<p class="cf2-home__ogl-row"><span class="cf2-home__ogl-k">ماذا يعني</span> ' +
          esc(guide.means) +
          "</p>";
      }
      if (guide.doNow) {
        html +=
          '<p class="cf2-home__ogl-row"><span class="cf2-home__ogl-k">ماذا تفعل الآن</span> ' +
          esc(guide.doNow) +
          "</p>";
      }
      if (guide.recheck) {
        html +=
          '<p class="cf2-home__ogl-row"><span class="cf2-home__ogl-k">متى تعيد الفحص</span> ' +
          esc(guide.recheck) +
          "</p>";
      }
      html += "</div>";
    } else {
      if (why) {
        html += '<p class="cf2-home__why">' + esc(why) + "</p>";
      }

      html +=
        '<div class="cf2-home__evidence" data-cf2-density="' +
        esc(String(density || "NEUTRAL").toLowerCase()) +
        '">';
      if (confidence) {
        html +=
          '<p class="cf2-home__confidence">' + esc(confidence) + "</p>";
      }
      if (
        silence !== "QUIET" &&
        lang &&
        lang.evidenceFieldFromSufficiency &&
        density !== "NEUTRAL"
      ) {
        html +=
          '<div class="cf2-home__field" aria-hidden="true">' +
          lang.evidenceFieldFromSufficiency(density) +
          "</div>";
      }
      html += "</div>";

      html +=
        '<div class="cf2-home__stance cf2-terminus" data-cf2-wait="' +
        esc(sem ? String(sem.wait_kind || "UNKNOWN").toLowerCase() : "unknown") +
        '">';
      html +=
        '<p class="cf2-home__stance-label">' +
        esc(
          sem && sem.evidence_sufficiency === "INSUFFICIENT"
            ? "الوضع الآن"
            : "ماذا تفعل؟"
        ) +
        "</p>";
      html +=
        '<p class="cf2-home__stance-body">' + esc(action) + "</p>";
      html += "</div>";
    }

    if (href) {
      var btnClass =
        sem && sem.evidence_sufficiency === "INSUFFICIENT"
          ? "cf2-btn cf2-btn--quiet"
          : "cf2-btn";
      var btnLabel =
        sem && sem.evidence_sufficiency === "INSUFFICIENT"
          ? "عرض الأساس"
          : "افتح القرار";
      html +=
        '<div class="cf2-home__action"><a class="' +
        btnClass +
        '" href="' +
        esc(href) +
        '">' +
        esc(btnLabel) +
        "</a></div>";
    }
    html += "</div>";

    /* ——— Monitoring: embedded continuation, not a sidebar column ——— */
    if (monitor.length) {
      html += '<div class="cf2-home__orbit-axis" aria-hidden="true"></div>';
      html +=
        '<aside class="cf2-home__monitor" data-cf2-orbit="satellites" aria-label="ما يراقبه CartFlow أيضًا">';
      html +=
        '<p class="cf2-home__monitor-label">ما يراقبه CartFlow أيضًا</p>';
      html += '<div class="cf2-home__monitor-row" data-cf2-orbit-row="1">';
      monitor.forEach(function (r) {
        html += monitorItem(r.sec, r.tier);
      });
      html += "</div></aside>";
    }

    html += "</div>";

    function notInMonitor(sec) {
      return !(sec && sec.id && monitorIds[sec.id]);
    }
    function floorKeep(sec) {
      return notInMonitor(sec) && !(hideStaleMonitor && sectionHasStaleMerchantCopy(sec));
    }
    var floorKnow = parts.know.filter(floorKeep);
    var floorWatch = parts.watch.filter(floorKeep);
    var floorLearn = parts.learning.filter(floorKeep);
    if (floorKnow.length || floorWatch.length || floorLearn.length) {
      html +=
        '<div class="cf2-home__floor" aria-label="معرفة إضافية">';
      floorKnow.forEach(function (sec) {
        html += floorItem(sec, "know");
      });
      floorWatch.forEach(function (sec) {
        html += floorItem(sec, "watch");
      });
      floorLearn.forEach(function (sec) {
        html += floorItem(sec, "learning");
      });
      html += "</div>";
    }

    html += '<hr class="cf2-taper" />';
    html += "</section>";
    return html + colHtml;
  }

  function paint(root, summary, paintOpts) {
    if (!root) return false;
    lastSummaryPayload = summary;
    lastSummaryRoot = root;
    if (currentView === "summary") {
      root.innerHTML = renderSummaryView(summary);
      return true;
    }
    var pkg =
      summary &&
      summary.home_executive_summary_v1 &&
      typeof summary.home_executive_summary_v1 === "object"
        ? summary.home_executive_summary_v1
        : null;
    if (!pkg || pkg.enabled === false) {
      root.innerHTML =
        '<p class="cf2-empty">تعذّر تحميل معرفة المتجر.</p>';
      return false;
    }
    /* Prefer overlaid top-level OGL — HES nested home_surface is a pre-overlay snapshot. */
    if (
      summary &&
      summary.operational_guidance_v1 &&
      summary.operational_guidance_v1.ok
    ) {
      pkg = Object.assign({}, pkg, {
        operational_guidance_v1: summary.operational_guidance_v1,
      });
    }
    root.innerHTML = render(pkg, summary, paintOpts || {});
    var ldhPaint = hierarchyFromSummary(summary);
    if (!ldhPaint) {
      bindColActions(root, resolveCommercialLayer(summary));
    } else {
      bindColActions(root, resolveCommercialLayer(summary));
    }
    return true;
  }

  function showView(viewId) {
    var next = viewId === "summary" ? "summary" : "overview";
    currentView = next;
    if (!lastSummaryRoot) return;
    if (next === "summary") {
      lastSummaryRoot.innerHTML = renderSummaryView(lastSummaryPayload);
      return;
    }
    paint(lastSummaryRoot, lastSummaryPayload);
  }

  async function loadAndPaint(root) {
    if (!root) return;
    root.innerHTML = '<p class="cf2-loading">جاري تحميل معرفة متجرك…</p>';
    try {
      var res = await fetch("/api/dashboard/summary", {
        credentials: "same-origin",
        cache: "no-store",
      });
      if (!res.ok) throw new Error("summary_http_" + res.status);
      paint(root, await res.json());
    } catch (e) {
      root.innerHTML =
        '<p class="cf2-error">تعذّر تحميل معرفة المتجر. أعد المحاولة.</p>';
    }
  }

  global.CartFlowUiV2Home = {
    loadAndPaint: loadAndPaint,
    paint: paint,
    render: render,
    renderSummaryView: renderSummaryView,
    showView: showView,
    currentView: function () {
      return currentView;
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
