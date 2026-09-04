/**
 * CartFlow Merchant UI V2 — Home executive composition V1.3
 * + Page-Specific Semantic Composition V1: gravity well + satellites.
 * Board gravity encodes attention. No repeated attention glyph / CO clause.
 * Current HES truth. semantic-visual-model-v1 drivers unchanged.
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

  function guidanceHomeSurface(pkg) {
    var g =
      pkg && pkg.operational_guidance_v1 && typeof pkg.operational_guidance_v1 === "object"
        ? pkg.operational_guidance_v1
        : null;
    if (!g || !g.ok) return null;
    var hs = g.home_surface && typeof g.home_surface === "object" ? g.home_surface : null;
    if (!hs) return null;
    var see = String(hs.what_we_see_ar || "").trim();
    var means = String(hs.what_it_means_ar || "").trim();
    var doNow = String(hs.what_to_do_now_ar || "").trim();
    var recheck = String(hs.when_to_recheck_ar || "").trim();
    if (!see && !means && !doNow) return null;
    return { see: see, means: means, doNow: doNow, recheck: recheck };
  }

  function escAttr(s) {
    return esc(s).replace(/"/g, "&quot;");
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
    var html =
      '<section class="cf2-col" data-cf2="commercial-opportunity-layer-v1" data-cf2-col="v1" data-cf2-col-refine="v1" data-cf2-cda="production-v1" data-cf2-model="semantic-visual-model-v1" aria-label="الفرصة التجارية">';
    html +=
      '<p class="cf2-col__question">' +
      esc(col.question_ar || "أين توجد أهم فرصة تجارية الآن؟") +
      "</p>";
    if (col.empty || !col.primary) {
      if (CDA && CDA.renderOrganism) {
        html += CDA.renderOrganism(null, {
          arc: "insufficient_evidence",
          surface: "home",
          emptyCopy:
            col.empty_state_ar ||
            "لا توجد فرصة تجارية جاهزة من أدلة متجرك الآن.",
        });
      } else {
        html +=
          '<p class="cf2-col__empty">' +
          esc(
            col.empty_state_ar ||
              "لا توجد فرصة تجارية جاهزة من أدلة متجرك الآن."
          ) +
          "</p>";
      }
      html += "</section>";
      return html;
    }
    var p = col.primary;
    var arc = paintOpts.homeArc || "action_chosen";
    html +=
      '<div class="cf2-col__primary" data-cf2-col-role="primary" data-cf2-col-mass="decision">';
    if (CDA && CDA.renderOrganism) {
      html += CDA.renderOrganism(p, {
        arc: arc,
        surface: "home",
        eyebrow: p.eyebrow_ar || "أهم فرصة تجارية الآن",
        openId: p.opportunity_id || "",
      });
    } else {
      html +=
        '<p class="cf2-col__eyebrow">' +
        esc(p.eyebrow_ar || "أهم فرصة تجارية الآن") +
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
    html += "</div>";

    var secs = Array.isArray(col.secondaries) ? col.secondaries.slice(0, 2) : [];
    if (secs.length) {
      html +=
        '<div class="cf2-col__secondaries" data-cf2-col-tier="secondary" data-cf2-col-compress="v1_1" aria-label="فرص تالية">';
      secs.forEach(function (s) {
        var why =
          String(s.priority_why_ar || "").trim() ||
          String(s.why_ar || "").trim();
        var act = String(s.action_ar || "").trim();
        var line = why;
        if (act) {
          line = why ? why + " · " + act : act;
        }
        /* One-line commercial signal — no article stack */
        if (line.length > 110) line = line.slice(0, 107) + "…";
        var title = String(s.title_ar || "").trim();
        if (title.length > 72) title = title.slice(0, 69) + "…";
        html +=
          '<article class="cf2-col__secondary cf2-col__secondary--signal" data-cf2-col-role="secondary">';
        html +=
          '<h3 class="cf2-col__sec-title">' + esc(title) + "</h3>";
        if (line) {
          html += '<p class="cf2-col__sec-line">' + esc(line) + "</p>";
        }
        html +=
          '<a class="cf2-col__sec-link" href="#workspace" data-cf2-col-open="' +
          escAttr(s.opportunity_id || "") +
          '">افتح</a>';
        html += "</article>";
      });
      html += "</div>";
    }
    html += "</section>";
    return html;
  }

  function bindColActions(root, col) {
    if (!root || !col) return;
    var map = {};
    if (col.primary) map[String(col.primary.opportunity_id || "")] = col.primary;
    (col.secondaries || []).forEach(function (s) {
      if (s) map[String(s.opportunity_id || "")] = s;
    });
    root.querySelectorAll("[data-cf2-col-open]").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-cf2-col-open") || "";
        if (map[id]) storeColFocus(map[id]);
      });
    });
  }

  function render(pkg, summary, paintOpts) {
    var col =
      summary &&
      summary.commercial_opportunity_layer_v1 &&
      typeof summary.commercial_opportunity_layer_v1 === "object"
        ? summary.commercial_opportunity_layer_v1
        : null;
    var colHtml = renderColLayer(col, paintOpts);
    var sections = Array.isArray(pkg.sections) ? pkg.sections : [];
    if (!sections.length) {
      return (
        '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-truth="empty" data-cf2-silence="quiet">' +
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
    var guide = guidanceHomeSurface(pkg);
    var html =
      '<section class="cf2-home" data-cf2="home-stage-closure-v1" data-cf2-grammar="attention-gravity" data-cf2-model="semantic-visual-model-v1" data-cf2-organism="gravity-well" data-cf2-composition="page-specific-v1" data-cf2-ogl="v1">';
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

    var monitor = [];
    parts.know.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "know" });
    });
    parts.watch.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "watch" });
    });
    parts.learning.forEach(function (sec) {
      monitor.push({ sec: sec, tier: "learning" });
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

    /* ——— Primary reading path (gravity well — no CO clause) ——— */
    html += '<div class="cf2-home__scene">';
    html += '<div class="cf2-home__lead">';
    html += '<div class="cf2-home__lead-text">';
    html += '<p class="cf2-home__lane">مركز الجاذبية</p>';
    html += '<p class="cf2-home__eyebrow">ما الذي أحتاج فعله الآن؟</p>';
    html +=
      '<h2 class="cf2-home__title">' + esc(p.title_ar || "") + "</h2>";
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
    var floorKnow = parts.know.filter(notInMonitor);
    var floorWatch = parts.watch.filter(notInMonitor);
    var floorLearn = parts.learning.filter(notInMonitor);
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
    /* Prefer top-level guidance when HES nested copy is slim. */
    if (
      summary &&
      summary.operational_guidance_v1 &&
      summary.operational_guidance_v1.ok &&
      (!pkg.operational_guidance_v1 || !pkg.operational_guidance_v1.ok)
    ) {
      pkg = Object.assign({}, pkg, {
        operational_guidance_v1: {
          ok: true,
          home_surface:
            (summary.operational_guidance_v1.home_surface) || {},
        },
      });
    }
    root.innerHTML = render(pkg, summary, paintOpts || {});
    bindColActions(
      root,
      summary && summary.commercial_opportunity_layer_v1
        ? summary.commercial_opportunity_layer_v1
        : null
    );
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
