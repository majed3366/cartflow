/**
 * MSR V1 — Merchant Surface Realization (MEIF consumer).
 * Reveals existing packages only. No business logic. No new intelligence.
 */
(function () {
  "use strict";

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function meif(summary) {
    return (summary && summary.merchant_experience_integration_v1) || null;
  }

  function lineage(it) {
    return (it && it.source_lineage) || {};
  }

  function explainOf(it) {
    var lin = lineage(it);
    return lin.explainability || it.explainability || {};
  }

  function trustBadge(it) {
    var label = it.trust_class_ar || it.trust_class || "";
    if (!label) return "";
    return (
      '<span class="meif-trust meif-trust--' +
      esc(it.trust_class || "observation") +
      '">' +
      esc(label) +
      "</span>"
    );
  }

  function confidenceLabel(it) {
    var c =
      it.confidence_label ||
      it.confidence_level ||
      it.confidence ||
      lineage(it).confidence ||
      "";
    if (!c || c === "n/a" || c === "none") return "";
    var ar = {
      high: "ثقة عالية",
      medium: "ثقة متوسطة",
      low: "ثقة منخفضة",
      very_high: "ثقة مرتفعة جداً",
      insufficient: "أدلة غير كافية",
      unknown: "ثقة غير محددة",
    };
    return ar[String(c).toLowerCase()] || String(c);
  }

  function titleOf(it) {
    var ex = explainOf(it);
    return (
      it.merchant_statement_ar ||
      ex.what_happened_ar ||
      it.merchant_value ||
      it.information_class ||
      "ملاحظة"
    );
  }

  function suggestedAction(it) {
    var ex = explainOf(it);
    if (ex.next_step_ar) return ex.next_step_ar;
    if (ex.suggested_action_ar) return ex.suggested_action_ar;
    var cls = String(it.information_class || "");
    var trust = String(it.trust_class || "");
    var src = String(it.source_type || "");
    if (trust === "recommendation" || cls === "commercial_guidance") {
      return "راجع التوصية في مساحة القرار قبل التنفيذ.";
    }
    if (src === "operational_truth" && cls === "critical_attention") {
      return "ابدأ من السلال أو مساحة القرار — هذه أولوية تشغيلية.";
    }
    if (src === "operational_truth" && cls === "operational_health") {
      return "راقب الإيقاع التشغيلي؛ لا إجراء فوري إن لم يتصاعد الانتباه.";
    }
    if (cls === "knowledge" || trust === "interpretation") {
      return "اعتبرها سياقاً — ليست أمراً بالتنفيذ.";
    }
    if (trust === "observation") {
      return "للمراقبة فقط — ليست توصية تشغيل.";
    }
    return "";
  }

  function renderDecisionCard(it) {
    var ex = explainOf(it);
    var why = ex.why_true_ar || "";
    var evidence = ex.evidence_ar || "";
    var conf = confidenceLabel(it);
    var action = suggestedAction(it);
    var gkey = lineage(it).guidance_key || "";
    if (!why && gkey) {
      why = "مرتبط بتوجيه تشغيلي محكوم («" + gkey + "»).";
    }
    if (!evidence && lineage(it).truth_id) {
      evidence =
        "حقيقة تشغيلية: " +
        String(lineage(it).truth_id) +
        (lineage(it).count != null ? " · العدد " + lineage(it).count : "");
    }
    if (!evidence && it.source_type) {
      evidence = "مصدر محكوم: " + String(it.source_type);
    }
    var parts = [];
    parts.push(
      '<article class="meif-card meif-card--decision" data-trust="' +
        esc(it.trust_class || "") +
        '">'
    );
    parts.push('<div class="meif-card__head">' + trustBadge(it));
    if (conf) {
      parts.push('<span class="meif-chip">' + esc(conf) + "</span>");
    }
    if (it.freshness_state) {
      parts.push(
        '<span class="meif-chip meif-chip--mute">' +
          esc(String(it.freshness_state)) +
          "</span>"
      );
    }
    parts.push("</div>");
    parts.push(
      '<h4 class="meif-card__title">' + esc(titleOf(it)) + "</h4>"
    );
    if (why) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">لماذا</span> ' +
          esc(why) +
          "</p>"
      );
    }
    if (evidence) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">الدليل</span> ' +
          esc(evidence) +
          "</p>"
      );
    }
    if (conf) {
      parts.push(
        '<p class="meif-card__row"><span class="meif-k">الثقة</span> ' +
          esc(conf) +
          "</p>"
      );
    }
    if (action) {
      parts.push(
        '<p class="meif-card__action"><span class="meif-k">الخطوة المقترحة</span> ' +
          esc(action) +
          "</p>"
      );
    }
    parts.push("</article>");
    return parts.join("");
  }

  function renderBriefCard(it, opts) {
    opts = opts || {};
    var action = opts.withAction ? suggestedAction(it) : "";
    var conf = confidenceLabel(it);
    return (
      '<article class="meif-card" data-trust="' +
      esc(it.trust_class || "") +
      '">' +
      '<div class="meif-card__head">' +
      trustBadge(it) +
      (conf ? '<span class="meif-chip">' + esc(conf) + "</span>" : "") +
      "</div>" +
      '<div class="meif-card__title">' +
      esc(titleOf(it)) +
      "</div>" +
      (action
        ? '<p class="meif-card__action">' + esc(action) + "</p>"
        : "") +
      "</article>"
    );
  }

  function renderCardList(items, emptyAr, mode) {
    var list = Array.isArray(items) ? items : [];
    if (!list.length) {
      return '<p class="meif-empty">' + esc(emptyAr || "لا عناصر محكومة الآن.") + "</p>";
    }
    return (
      '<div class="meif-cards">' +
      list
        .map(function (it) {
          return mode === "decision"
            ? renderDecisionCard(it)
            : renderBriefCard(it, { withAction: mode === "action" });
        })
        .join("") +
      "</div>"
    );
  }

  function healthVerdict(ops, home) {
    var carts = Number(ops.abandoned_carts || 0);
    var purchases = Number(ops.purchase_truth || 0);
    var critical = ((home.sections || {}).critical_attention || []).length;
    if (!ops.has_durable_carts && carts === 0) {
      return {
        tone: "quiet",
        title: "لا نشاط سلات مسجّل بعد",
        body: "CartFlow جاهز للمراقبة — لم تُسجَّل سلات في حقيقة المتجر حتى الآن.",
      };
    }
    if (critical > 0 || carts >= 5) {
      return {
        tone: "attention",
        title: "متجرك يحتاج انتباهك اليوم",
        body:
          "هناك أولويات تشغيلية ظاهرة. ابدأ من «ما يستحق الانتباه» قبل فتح التفاصيل.",
      };
    }
    if (purchases > 0) {
      return {
        tone: "stable",
        title: "الإيقاع التشغيلي مستقر نسبياً",
        body:
          "توجد سلات ومشتريات موثّقة. راجع الملخص ثم انتقل للتفاصيل عند الحاجة فقط.",
      };
    }
    return {
      tone: "watch",
      title: "CartFlow يراقب متجرك",
      body: "هناك نشاط مسجّل. ركّز على الانتباه الحرج قبل أي صفحة تفصيلية.",
    };
  }

  function suppressSetupTheatre(home) {
    if (!home || !home.suppress_setup_theatre) return;
    [
      "#ma-setup-readiness-panel",
      "#ma-activation-journey",
      ".ma-setup-experience",
      "[data-ma-setup-theatre]",
    ].forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        el.hidden = true;
        el.setAttribute("data-meh-suppressed", "1");
      });
    });
  }

  function applyHome(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.ok || !pkg.pages || !pkg.pages.home) return false;
    var home = pkg.pages.home;
    var root = document.getElementById("ma-home-experience-root");
    if (!root) return false;
    var ops = home.operational_truth || {};
    var sections = home.sections || {};
    var cue = home.chronology_cue || {};
    var verdict = healthVerdict(ops, home);
    var watching = ops.has_durable_carts || Number(ops.abandoned_carts || 0) > 0;

    var html = "";
    html +=
      '<section class="meif-surface meif-home" data-meif="1" data-msr="1">' +
      '<header class="meif-brief">' +
      '<p class="meif-eyebrow">إحاطة تنفيذية</p>' +
      "<h2>" +
      esc(verdict.title) +
      "</h2>" +
      '<p class="meif-lede">' +
      esc(verdict.body) +
      "</p>" +
      '<div class="meif-watch meif-watch--' +
      esc(verdict.tone) +
      '">' +
      '<span class="meif-trust meif-trust--fact">حقيقة</span> ' +
      (watching
        ? "CartFlow يراقب متجرك الآن ضمن نافذة المراجعة الحالية."
        : "CartFlow جاهز للمراقبة — بانتظار تسجيل نشاط.") +
      "</div>" +
      "</header>";

    html +=
      '<section class="meif-block meif-block--facts" aria-label="صحة المتجر">' +
      "<h3>هل متجري بصحة جيدة اليوم؟</h3>" +
      '<ul class="meif-facts">' +
      "<li><strong>" +
      esc(String(ops.abandoned_carts != null ? ops.abandoned_carts : "—")) +
      "</strong><span>سلات مسجّلة</span></li>" +
      "<li><strong>" +
      esc(String(ops.purchase_truth != null ? ops.purchase_truth : "—")) +
      "</strong><span>مشتريات موثّقة</span></li>" +
      "<li><strong>" +
      esc(String(ops.hesitation_reasons != null ? ops.hesitation_reasons : "—")) +
      "</strong><span>أسباب تردد</span></li>" +
      "</ul></section>";

    html +=
      '<section class="meif-block meif-block--priority" aria-label="الانتباه">' +
      "<h3>ما الذي يستحق انتباهك أولاً؟</h3>" +
      renderCardList(
        sections.critical_attention,
        ops.has_durable_carts
          ? "هناك سلات مسجّلة — افتح السلال أو مساحة القرار."
          : "لا انتباه حرج محكوم الآن.",
        "action"
      ) +
      "</section>";

    html +=
      '<section class="meif-block" aria-label="الملخص التنفيذي">' +
      "<h3>ماذا يجب أن تعرف قبل أي صفحة تفصيلية؟</h3>" +
      renderCardList(
        sections.executive_summary,
        "لا ملخص تنفيذي محكوم بعد.",
        "brief"
      ) +
      "</section>";

    html +=
      '<div class="meif-split">' +
      '<section class="meif-block" aria-label="تحسّن">' +
      "<h3>ماذا تحسّن أو ظهر حديثاً؟</h3>" +
      renderCardList(
        sections.knowledge_highlights,
        "لا إشارات معرفة مترجمة بعد.",
        "brief"
      ) +
      "</section>" +
      '<section class="meif-block" aria-label="تشغيل">' +
      "<h3>الصحة التشغيلية</h3>" +
      renderCardList(
        sections.operational_health,
        "لا حالة تشغيلية محكومة بعد.",
        "brief"
      ) +
      "</section>" +
      "</div>";

    html +=
      '<section class="meif-block" aria-label="إرشاد">' +
      "<h3>ما الذي يستحق قراراً؟</h3>" +
      renderCardList(
        sections.commercial_guidance_highlights,
        "لا توصية تشغيلية موجّهة الآن.",
        "action"
      ) +
      '<p class="meif-next"><a href="#workspace">افتح مساحة القرار للتفسير الكامل ←</a></p>' +
      "</section>";

    if (
      sections.monitoring_observations &&
      sections.monitoring_observations.length
    ) {
      html +=
        '<section class="meif-block meif-block--muted" aria-label="مراقبة">' +
        "<h3>ملاحظات مراقبة (ليست توصيات)</h3>" +
        renderCardList(sections.monitoring_observations, "", "brief") +
        "</section>";
    }

    if (cue.as_of) {
      html +=
        '<footer class="meif-chrono">' +
        '<span class="meif-trust meif-trust--fact">حقيقة زمنية</span> ' +
        esc(cue.label_ar || "نافذة المراجعة") +
        " · " +
        esc(String(cue.assembly_window || "")) +
        " · " +
        esc(String(cue.as_of)) +
        (cue.note_ar ? "<br>" + esc(cue.note_ar) : "") +
        "</footer>";
    }

    html += "</section>";
    root.className = "ma-home-experience meif-home-root";
    root.innerHTML = html;
    root.removeAttribute("aria-busy");
    var loading = document.getElementById("ma-home-experience-loading");
    if (loading) loading.hidden = true;
    suppressSetupTheatre(home);
    return true;
  }

  function applyCarts(summary) {
    var pkg = meif(summary);
    if (!pkg || !pkg.pages || !pkg.pages.carts) return;
    var carts = pkg.pages.carts;
    var loading = document.getElementById("ma-carts-unified-loading");
    var banner = document.getElementById("meif-carts-truth-banner");
    var focus = document.getElementById("meif-carts-focus-root");
    var ops = carts.operational_truth || {};
    var items = (carts.sections && carts.sections.composition_items) || [];

    if (banner) {
      banner.hidden = false;
      banner.className = "meif-carts-truth-banner meif-banner";
      banner.innerHTML =
        '<span class="meif-trust meif-trust--fact">حقيقة</span> ' +
        esc(carts.status_message_ar || "") +
        (carts.merchant_question
          ? '<span class="meif-banner__q">' +
            esc(
              "أي سلات تهمّك الآن، ولماذا؟"
            ) +
            "</span>"
          : "");
    }
    if (carts.forbid_please_wait && loading) {
      loading.hidden = true;
      loading.setAttribute("aria-busy", "false");
    }

    var header = document.querySelector("#page-carts .page-h1");
    var sub = document.querySelector("#page-carts .page-sub");
    if (header && ops.has_durable_carts) {
      header.textContent = "السلال التي تستحق الانتباه";
    }
    if (sub && ops.has_durable_carts) {
      sub.textContent =
        "رتّبنا الإشارات التشغيلية أولاً — القائمة التفصيلية تحتها مباشرة.";
    }

    if (focus) {
      focus.hidden = false;
      focus.innerHTML =
        '<section class="meif-surface meif-carts-focus" data-msr="1">' +
        "<h3>لماذا تهمّ هذه السلال؟</h3>" +
        renderCardList(
          items,
          ops.has_durable_carts
            ? "السلات مسجّلة في الحقيقة التشغيلية — راجع الجدول أدناه للتفاصيل."
            : "لا إشارات سلال محكومة بعد.",
          "action"
        ) +
        "</section>";
    }
  }

  function applyCommunication(summary) {
    var pkg = meif(summary);
    var root = document.getElementById("meif-communication-root");
    if (!root || !pkg || !pkg.pages || !pkg.pages.communication) return false;
    var comm = pkg.pages.communication;
    var ops = comm.operational_truth || {};
    var sent = Number(ops.mock_whatsapp_sent || 0);
    var schedules = Number(ops.recovery_schedules || 0);
    var waiting = schedules;
    var needs =
      ops.has_communication_activity && (sent === 0 || schedules > 0)
        ? "راجع ما بانتظار الإرسال أو المتابعة."
        : "لا تدخل فوري مطلوب من هذه الصفحة.";

    root.className = "meif-communication-root";
    root.innerHTML =
      '<section class="meif-surface meif-comms" data-meif="1" data-msr="1">' +
      '<p class="meif-eyebrow">حالة التواصل</p>' +
      "<h2>ماذا يحدث في التواصل الآن؟</h2>" +
      '<p class="meif-lede">' +
      esc(comm.status_message_ar || "") +
      "</p>" +
      '<ul class="meif-facts meif-facts--3">' +
      "<li><strong>" +
      esc(String(sent)) +
      "</strong><span>ما حدث (إرسال مسجّل)</span></li>" +
      "<li><strong>" +
      esc(String(waiting)) +
      "</strong><span>ما ينتظر (جداول)</span></li>" +
      "<li><strong>" +
      esc(ops.has_communication_activity ? "متابعة" : "هدوء") +
      "</strong><span>هل تحتاج تدخلاً؟</span></li>" +
      "</ul>" +
      '<p class="meif-watch">' +
      esc(needs) +
      "</p>" +
      '<section class="meif-block"><h3>إشارات التواصل المحكومة</h3>' +
      renderCardList(
        (comm.sections && comm.sections.composition_items) || [],
        "لا عناصر تواصل محكومة بعد — هذه ليست صفحة إعدادات واتساب.",
        "action"
      ) +
      "</section>" +
      '<p class="meif-next">' +
      '<a href="#messages">سجل الرسائل</a> · ' +
      '<a href="#whatsapp">إعدادات واتساب</a>' +
      "</p></section>";
    return true;
  }

  function applyDecision(summary) {
    var pkg = meif(summary);
    var root = document.getElementById("meif-decision-root");
    if (!root || !pkg || !pkg.pages || !pkg.pages.decision_workspace) {
      return false;
    }
    var dw = pkg.pages.decision_workspace;
    var sections = dw.sections || {};
    root.innerHTML =
      '<section class="meif-surface meif-decision" data-meif="1" data-msr="1">' +
      '<p class="meif-eyebrow">مساحة القرار</p>' +
      "<h2>لماذا يحدث هذا، وما القرار المطلوب؟</h2>" +
      '<p class="meif-lede">كل عنصر أدناه يوضّح السبب والدليل ومستوى الثقة والخطوة المقترحة — دون اختراع توصيات جديدة.</p>' +
      '<section class="meif-block"><h3>عناصر تحتاج قراراً</h3>' +
      renderCardList(
        sections.review_items,
        "لا عناصر مراجعة محكومة بعد.",
        "decision"
      ) +
      "</section>" +
      '<section class="meif-block meif-block--muted"><h3>سياق المعرفة (للتفسير لا للتنفيذ الأعمى)</h3>' +
      renderCardList(
        sections.knowledge_context,
        "لا سياق معرفة مترجم بعد.",
        "brief"
      ) +
      "</section>" +
      '<p class="meif-next"><a href="#carts">انتقل للسلال ذات الأولوية ←</a></p>' +
      "</section>";
    return true;
  }

  window.maApplyMerchantExperienceIntegrationV1 = function (summary) {
    if (!window.CARTFLOW_MERCHANT_EXPERIENCE_INTEGRATION_V1) return false;
    var pkg = meif(summary);
    if (!pkg || !pkg.enabled) return false;
    var homeOk = applyHome(summary);
    applyCarts(summary);
    applyCommunication(summary);
    applyDecision(summary);
    return homeOk;
  };
})();
