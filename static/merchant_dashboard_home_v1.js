/**
 * Dashboard Home — Daily Business Brief V1 (Constitution V3).
 * Story: Health → Risk → Opportunity → Priority → Understanding → Learning → Timeline.
 * One section · one business question · merchant value only. Presentation only.
 */
(function () {
  "use strict";

  var EMPTY_VALUE = "—";

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    if (window.maEscHtml) return window.maEscHtml(s);
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function greetingArFallback() {
    var h = new Date().getHours();
    if (h >= 5 && h < 12) return "صباح الخير";
    return "مساء الخير";
  }

  function confidenceLabelAr(raw) {
    var c = String(raw || "")
      .trim()
      .toLowerCase();
    if (c === "high" || c === "confirmed") return "عالية";
    if (c === "medium") return "متوسطة";
    if (c === "low") return "منخفضة";
    if (c === "insufficient" || c === "unknown" || !c) return "أدلة غير كافية";
    return "أدلة غير كافية";
  }

  function confidenceTone(raw) {
    var c = String(raw || "")
      .trim()
      .toLowerCase();
    if (c === "high" || c === "confirmed") return "high";
    if (c === "medium") return "medium";
    if (c === "low") return "low";
    return "insufficient";
  }

  function severityTone(item) {
    var s = String((item && item.severity) || "").trim().toLowerCase();
    var cls = String((item && item.decision_class) || "").trim().toLowerCase();
    if (s === "critical" || cls === "critical_action") return "critical";
    if (
      s === "attention" ||
      s === "suggested" ||
      cls === "needs_attention" ||
      cls === "suggested_action"
    ) {
      return "attention";
    }
    return "default";
  }

  function goCartsOnclick() {
    return ' onclick="if(window.goToSection){goToSection(\'carts\');}else if(window.goTo){goTo(\'carts\');}return false;"';
  }

  function drilldownHref(item) {
    var href = String((item && item.drilldown_href) || "").trim();
    if (href) return href;
    return "#carts";
  }

  function goDrilldownOnclick(item) {
    var href = drilldownHref(item);
    if (href.indexOf("tab=nophone") !== -1 || href.indexOf("tab=no_phone") !== -1) {
      return (
        ' onclick="if(window.goToCartTab){goToCartTab(\'nophone\');}else{location.hash=' +
        JSON.stringify(href) +
        ';}return false;"'
      );
    }
    if (href.indexOf("tab=waiting") !== -1) {
      return (
        ' onclick="if(window.goToCartTab){goToCartTab(\'waiting\');}else{location.hash=' +
        JSON.stringify(href) +
        ';}return false;"'
      );
    }
    return goCartsOnclick();
  }

  function sectionHead(titleId, title, question) {
    return (
      '<header class="ma-ecc-band__head">' +
      '<h2 class="ma-ecc-band__title" id="' +
      esc(titleId) +
      '">' +
      esc(title) +
      "</h2>" +
      '<p class="ma-ecc-band__purpose">' +
      esc(question) +
      "</p>" +
      "</header>"
    );
  }

  function renderLoading() {
    return (
      '<div class="ma-ecc-skel" aria-busy="true" aria-live="polite">' +
      '<div class="ma-ecc-skel__hero"></div>' +
      '<div class="ma-ecc-skel__block ma-ecc-skel__block--tall"></div>' +
      '<div class="ma-ecc-skel__metrics">' +
      "<span></span><span></span><span></span><span></span>" +
      "</div>" +
      '<p class="ma-ecc-whisper">نجهّز ملخص عملك اليومي…</p>' +
      "</div>"
    );
  }

  function renderError(message) {
    return (
      '<section class="ma-ecc-band" aria-label="خطأ">' +
      '<div class="ma-ecc-panel ma-ecc-panel--error">' +
      '<p class="ma-ecc-panel__title">تعذّر تحميل الرئيسية</p>' +
      '<p class="ma-ecc-copy">' +
      esc(message || "جرّب تحديث الصفحة.") +
      "</p>" +
      '<button type="button" class="ma-ecc-btn ma-ecc-btn--ghost" onclick="location.reload()">' +
      "تحديث الصفحة" +
      "</button>" +
      "</div></section>"
    );
  }

  /** Section 1 — Business Health */
  function renderBusinessHealth(home, summary) {
    var greeting = (home && home.greeting) || {};
    var health = (home && home.business_health) || {};
    var greet = String(greeting.greeting_ar || greetingArFallback()).trim();
    var name = String(greeting.merchant_name_ar || "متجرك").trim();
    var date =
      String(greeting.date_ar || "").trim() ||
      String((summary && summary.merchant_ar_date_header) || "").trim();
    var status = String(health.status_ar || "").trim() || "قيد التقييم";
    var summaryText =
      String(health.summary_ar || "").trim() ||
      String(health.empty_message_ar || "").trim() ||
      "نجمع صورة أوضح لصحة العمل.";
    var direction = String(health.direction_ar || "").trim();
    var confTone = confidenceTone(health.confidence);
    var conf =
      String(health.confidence_ar || "").trim() ||
      confidenceLabelAr(health.confidence);
    var evidence = String(health.evidence_summary_ar || "").trim();
    var attentionNeeded = !!health.attention_required;

    return (
      '<section class="ma-ecc-hero" aria-label="صحة العمل" data-ecc-section="health">' +
      '<div class="ma-ecc-hero__atmosphere" aria-hidden="true"></div>' +
      '<div class="ma-ecc-hero__grid">' +
      '<div class="ma-ecc-hero__main">' +
      '<p class="ma-ecc-hero__greet">' +
      esc(greet) +
      "، " +
      esc(name) +
      (date ? " · " + esc(date) : "") +
      "</p>" +
      '<h1 class="ma-ecc-hero__title">' +
      esc(health.title_ar || "صحة العمل") +
      "</h1>" +
      '<p class="ma-ecc-hero__exec-label">' +
      esc(health.section_question_ar || health.lead_ar || "كيف حال عملي اليوم؟") +
      "</p>" +
      '<p class="ma-ecc-hero__exec-text">' +
      '<span class="ma-ecc-chip ma-ecc-chip--' +
      (attentionNeeded ? "attention" : "neutral") +
      '">' +
      esc(status) +
      "</span> " +
      esc(summaryText) +
      "</p>" +
      (direction
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الاتجاه:</span> ' +
          esc(direction) +
          "</p>"
        : "") +
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الثقة:</span> ' +
      '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
      confTone +
      '">' +
      esc(conf) +
      "</span></p>" +
      (evidence
        ? '<p class="ma-ecc-copy ma-ecc-copy--muted">' + esc(evidence) + "</p>"
        : "") +
      "</div></div></section>"
    );
  }

  /** Section 2 — Biggest Revenue Risk */
  function renderRevenueRisk(home) {
    var section = (home && home.biggest_revenue_risk) || {};
    var item = section.item || (section.items && section.items[0]) || null;
    var head = sectionHead(
      "ma-ecc-risk-title",
      section.title_ar || "أكبر خطر على الإيراد",
      section.section_question_ar || section.lead_ar || "أين أخسر أكثر الآن؟"
    );

    if (!item) {
      return (
        '<section class="ma-ecc-band" data-ecc-section="risk" aria-labelledby="ma-ecc-risk-title">' +
        head +
        '<p class="ma-ecc-copy">' +
        esc(section.empty_message_ar || "لا خطر إيراد مؤكد بأدلة كافية الآن.") +
        "</p></section>"
      );
    }

    return (
      '<section class="ma-ecc-band ma-ecc-band--attention" data-ecc-section="risk" aria-labelledby="ma-ecc-risk-title">' +
      head +
      '<div class="ma-ecc-attention__item ma-ecc-attention__item--attention">' +
      '<div class="ma-ecc-attention__body">' +
      '<span class="ma-ecc-chip ma-ecc-chip--attention">خطر إيراد</span>' +
      '<h3 class="ma-ecc-attention__headline">' +
      esc(item.headline_ar || "—") +
      "</h3>" +
      (item.why_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا يهم:</span> ' +
          esc(item.why_ar) +
          "</p>"
        : "") +
      (item.evidence_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الدليل:</span> ' +
          esc(item.evidence_ar) +
          "</p>"
        : "") +
      (item.commercial_impact_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الأثر التجاري:</span> ' +
          esc(item.commercial_impact_ar) +
          "</p>"
        : "") +
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الثقة:</span> ' +
      '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
      confidenceTone(item.confidence) +
      '">' +
      esc(confidenceLabelAr(item.confidence)) +
      "</span></p>" +
      "</div></div></section>"
    );
  }

  /** Section 3 — Biggest Opportunity */
  function renderOpportunity(home) {
    var section = (home && home.biggest_opportunity) || {};
    var item = section.item || (section.items && section.items[0]) || null;
    if (item && !String(item.headline_ar || "").trim()) item = null;
    var head = sectionHead(
      "ma-ecc-opportunity-title",
      section.title_ar || "أكبر فرصة اليوم",
      section.section_question_ar || section.lead_ar || "أين أفضل فرصة اليوم؟"
    );

    if (!item) {
      return (
        '<section class="ma-ecc-band" data-ecc-section="opportunity" aria-labelledby="ma-ecc-opportunity-title">' +
        head +
        '<p class="ma-ecc-copy">' +
        esc(section.empty_message_ar || "لا فرصة تجارية مؤكدة بأدلة كافية اليوم.") +
        "</p></section>"
      );
    }

    var action = String(item.cta_label_ar || "").trim();
    return (
      '<section class="ma-ecc-band" data-ecc-section="opportunity" aria-labelledby="ma-ecc-opportunity-title">' +
      head +
      '<div class="ma-ecc-panel">' +
      '<span class="ma-ecc-chip ma-ecc-chip--neutral">فرصة</span>' +
      '<h3 class="ma-ecc-attention__headline">' +
      esc(String(item.headline_ar || "").trim()) +
      "</h3>" +
      (item.why_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا الآن:</span> ' +
          esc(item.why_ar) +
          "</p>"
        : "") +
      (item.evidence_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الدليل:</span> ' +
          esc(item.evidence_ar) +
          "</p>"
        : "") +
      (item.commercial_value_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">القيمة التجارية:</span> ' +
          esc(item.commercial_value_ar) +
          "</p>"
        : "") +
      (action
        ? '<a class="ma-ecc-btn" href="' +
          esc(drilldownHref(item)) +
          '" role="button"' +
          goDrilldownOnclick(item) +
          ">" +
          esc(action) +
          "</a>"
        : "") +
      "</div></section>"
    );
  }

  function renderRecoveryJourney(item) {
    var journey = (item && item.recovery_journey_v1) || null;
    var stage = String(
      (journey && journey.recovery_stage_ar) || item.recovery_stage_ar || ""
    ).trim();
    if (!stage) return "";
    var channel = String(
      (journey && journey.recovery_channel_ar) || item.recovery_channel_ar || ""
    ).trim();
    var why = String(
      (journey && journey.recovery_stage_why_ar) || item.recovery_stage_why_ar || ""
    ).trim();
    var blocker = String(
      (journey && journey.recovery_blocker_ar) || item.recovery_blocker_ar || ""
    ).trim();
    var nextPlatform = String(
      (journey && journey.recovery_next_platform_ar) ||
        item.recovery_next_platform_ar ||
        ""
    ).trim();
    var nextMerchant = String(
      (journey && journey.recovery_next_merchant_ar) ||
        item.recovery_next_merchant_ar ||
        ""
    ).trim();
    var completion = String(
      (journey && journey.recovery_completion_condition_ar) ||
        item.recovery_completion_condition_ar ||
        ""
    ).trim();
    var merchantRequired =
      (journey && journey.recovery_merchant_required) ||
      item.recovery_merchant_required;
    return (
      '<div class="ma-ecc-journey" data-recovery-stage="' +
      esc(
        (journey && journey.recovery_stage_key) || item.recovery_stage_key || ""
      ) +
      '">' +
      '<p class="ma-ecc-journey__title">مسار الاسترجاع</p>' +
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">المرحلة الآن:</span> ' +
      esc(stage) +
      "</p>" +
      (channel
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">القناة:</span> ' +
          esc(channel) +
          "</p>"
        : "") +
      (why
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا هنا:</span> ' +
          esc(why) +
          "</p>"
        : "") +
      (blocker
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الحاجز:</span> ' +
          esc(blocker) +
          "</p>"
        : "") +
      (nextPlatform
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">المنصة الآن:</span> ' +
          esc(nextPlatform) +
          "</p>"
        : "") +
      (nextMerchant
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">' +
          (merchantRequired ? "دورك الآن:" : "دورك:") +
          "</span> " +
          esc(nextMerchant) +
          "</p>"
        : "") +
      (completion
        ? '<p class="ma-ecc-copy ma-ecc-copy--muted"><span class="ma-ecc-why-k">يكتمل عندما:</span> ' +
          esc(completion) +
          "</p>"
        : "") +
      "</div>"
    );
  }

  /** Section 4 — Today's Priority (exactly one) */
  function renderTodaysPriority(home) {
    var att =
      (home && home.todays_priority) || (home && home.attention_today) || {};
    var items = att.items || [];
    var head = sectionHead(
      "ma-ecc-priority-title",
      att.title_ar || "أولوية اليوم",
      att.section_question_ar || att.lead_ar || "ما أهم شيء أفعله اليوم؟"
    );

    if (!items.length) {
      return (
        '<section class="ma-ecc-band ma-ecc-band--attention" data-ecc-section="priority" aria-labelledby="ma-ecc-priority-title">' +
        head +
        '<div class="ma-ecc-attention-empty">' +
        '<span class="ma-ecc-attention-empty__mark" aria-hidden="true">✓</span>' +
        "<div>" +
        '<p class="ma-ecc-attention-empty__title">لا أولوية واحدة مطلوبة الآن</p>' +
        '<p class="ma-ecc-copy">' +
        esc(att.empty_message_ar || "لا أولوية تجارية واحدة مطلوبة منك الآن.") +
        "</p></div></div></section>"
      );
    }

    var item = items[0];
    var tone = severityTone(item);
    var badge =
      String(item.decision_class_label_ar || "").trim() || "أولوية اليوم";
    var action =
      String(item.action_ar || item.cta_label_ar || "").trim() ||
      "عرض السلال المتأثرة";
    var outcome = String(item.expected_outcome_ar || "").trim();
    var ifIgnored = String(item.if_ignored_ar || "").trim();

    return (
      '<section class="ma-ecc-band ma-ecc-band--attention" data-ecc-section="priority" aria-labelledby="ma-ecc-priority-title">' +
      head +
      '<div class="ma-ecc-attention__item ma-ecc-attention__item--' +
      tone +
      '" data-decision-key="' +
      esc(item.operational_decision_key || "") +
      '">' +
      '<div class="ma-ecc-attention__body">' +
      '<span class="ma-ecc-chip ma-ecc-chip--' +
      tone +
      '">' +
      esc(badge) +
      "</span>" +
      '<h3 class="ma-ecc-attention__headline">' +
      esc(item.headline_ar || "—") +
      "</h3>" +
      (item.why_ar
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا الآن:</span> ' +
          esc(item.why_ar) +
          "</p>"
        : "") +
      (outcome
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا مهم:</span> ' +
          esc(outcome) +
          "</p>"
        : "") +
      (ifIgnored
        ? '<p class="ma-ecc-copy ma-ecc-copy--muted"><span class="ma-ecc-why-k">إذا تجاهلت:</span> ' +
          esc(ifIgnored) +
          "</p>"
        : "") +
      renderRecoveryJourney(item) +
      (action
        ? '<a class="ma-ecc-btn" href="' +
          esc(drilldownHref(item)) +
          '" role="button"' +
          goDrilldownOnclick(item) +
          ">" +
          esc(action) +
          "</a>"
        : "") +
      "</div></div></section>"
    );
  }

  function klStep(label, body, mod) {
    return (
      '<div class="ma-ecc-kl__step' +
      (mod ? " " + mod : "") +
      '" role="listitem">' +
      '<div class="ma-ecc-kl__marker" aria-hidden="true"></div>' +
      '<div class="ma-ecc-kl__step-body">' +
      '<p class="ma-ecc-kl__step-label">' +
      esc(label) +
      "</p>" +
      '<div class="ma-ecc-kl__step-content">' +
      body +
      "</div></div></div>"
    );
  }

  /** Section 5 — Business Understanding */
  function renderBusinessUnderstanding(home) {
    var section =
      (home && home.business_understanding) ||
      (home && home.store_understanding) ||
      {};
    var items = section.items || [];
    var head =
      '<header class="ma-ecc-kl__head">' +
      '<p class="ma-ecc-kicker">' +
      esc(section.section_question_ar || section.lead_ar || "ماذا نفهم عن عملك الآن؟") +
      "</p>" +
      '<h2 class="ma-ecc-kl__title" id="ma-ecc-understanding-title">' +
      esc(section.title_ar || "فهم العمل") +
      "</h2>" +
      '<p class="ma-ecc-kl__purpose">' +
      esc(
        section.purpose_ar ||
          "ملاحظة → دليل → معنى تجاري → أثر تجاري → اتجاه موصى به → ثقة"
      ) +
      "</p>" +
      "</header>";

    if (!items.length) {
      return (
        '<section class="ma-ecc-band ma-ecc-band--knowledge" id="ma-home-understanding" data-ecc-section="understanding" aria-labelledby="ma-ecc-understanding-title">' +
        head +
        '<div class="ma-ecc-kl ma-ecc-kl--empty">' +
        '<div class="ma-ecc-kl" role="list">' +
        klStep(
          "الملاحظة",
          '<p class="ma-ecc-kl__observation">لا ملاحظة مؤكدة بعد</p>',
          "ma-ecc-kl__step--lead"
        ) +
        klStep("الدليل", '<p class="ma-ecc-copy">نجمع أدلة نشاط المتجر.</p>') +
        klStep(
          "المعنى التجاري",
          '<p class="ma-ecc-copy">' +
            esc(section.empty_message_ar || "لا فهم تجاري مؤكد بعد.") +
            "</p>"
        ) +
        klStep(
          "الثقة",
          '<span class="ma-ecc-chip ma-ecc-chip--conf-insufficient">أدلة غير كافية</span>'
        ) +
        "</div></div></section>"
      );
    }

    var item = items[0];
    var observation =
      String(item.observation_ar || item.title_ar || "").trim() || EMPTY_VALUE;
    var evidence = String(item.evidence_label_ar || "").trim();
    var meaning = String(
      item.business_meaning_ar || item.impact_ar || ""
    ).trim();
    var commercial = String(item.commercial_impact_ar || "").trim();
    var direction = String(item.recommended_direction_ar || "").trim();
    var confTone = confidenceTone(item.confidence);
    var conf = confidenceLabelAr(item.confidence);
    var confReason = String(item.confidence_reason_ar || "").trim();

    var flow =
      '<div class="ma-ecc-kl" role="list">' +
      klStep(
        "الملاحظة",
        '<p class="ma-ecc-kl__observation">' + esc(observation) + "</p>",
        "ma-ecc-kl__step--lead"
      ) +
      klStep(
        "الدليل",
        '<p class="ma-ecc-copy">' +
          esc(evidence || "مصدر الدليل غير مكتمل بعد.") +
          "</p>"
      ) +
      klStep(
        "المعنى التجاري",
        '<p class="ma-ecc-copy">' +
          esc(meaning || "لا معنى تجاري كافٍ بعد.") +
          "</p>"
      ) +
      klStep(
        "الأثر التجاري",
        '<p class="ma-ecc-copy">' +
          esc(commercial || meaning || "لا أثر تجاري مؤكد بعد.") +
          "</p>"
      ) +
      klStep(
        "الاتجاه الموصى به",
        '<p class="ma-ecc-copy">' +
          esc(direction || "راقب هذا النمط في قراراتك القادمة.") +
          "</p>"
      ) +
      klStep(
        "الثقة",
        '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
          confTone +
          '">' +
          esc(conf) +
          "</span>" +
          (confReason
            ? '<p class="ma-ecc-copy ma-ecc-copy--muted">' +
              esc(confReason) +
              "</p>"
            : "")
      ) +
      "</div>";

    return (
      '<section class="ma-ecc-band ma-ecc-band--knowledge" id="ma-home-understanding" data-ecc-section="understanding" aria-labelledby="ma-ecc-understanding-title">' +
      head +
      flow +
      "</section>"
    );
  }

  /** Section 6 — Learning Progress */
  function renderLearningProgress(home) {
    var section = (home && home.learning_progress) || {};
    var items = section.items || [];
    var head = sectionHead(
      "ma-ecc-learning-title",
      section.title_ar || "تقدّم الفهم",
      section.section_question_ar ||
        section.lead_ar ||
        "كيف يتطوّر فهمنا للعمل؟"
    );

    if (!items.length) {
      return (
        '<section class="ma-ecc-band" data-ecc-section="learning" aria-labelledby="ma-ecc-learning-title">' +
        head +
        '<p class="ma-ecc-copy">' +
        esc(section.empty_message_ar || "ما زال فهم العمل في طور البناء.") +
        "</p></section>"
      );
    }

    var list = '<ul class="ma-ecc-timeline">';
    items.slice(0, 3).forEach(function (item, idx) {
      var progress = String((item && item.progress_ar) || "").trim();
      if (!progress) return;
      var detail = String((item && item.detail_ar) || "").trim();
      list +=
        '<li class="ma-ecc-timeline__item">' +
        '<div class="ma-ecc-timeline__spine" aria-hidden="true">' +
        '<span class="ma-ecc-timeline__dot' +
        (idx === 0 ? " ma-ecc-timeline__dot--now" : "") +
        '"></span></div>' +
        '<div class="ma-ecc-timeline__main">' +
        '<p class="ma-ecc-timeline__type">تقدّم فهم</p>' +
        '<p class="ma-ecc-timeline__headline">' +
        esc(progress) +
        "</p>" +
        (detail
          ? '<p class="ma-ecc-copy ma-ecc-copy--muted">' + esc(detail) + "</p>"
          : "") +
        "</div>" +
        '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
        confidenceTone(item.confidence) +
        '">' +
        esc(confidenceLabelAr(item.confidence)) +
        "</span>" +
        "</li>";
    });
    list += "</ul>";

    return (
      '<section class="ma-ecc-band" data-ecc-section="learning" aria-labelledby="ma-ecc-learning-title">' +
      head +
      list +
      "</section>"
    );
  }

  /** Section 7 — Business Timeline */
  function renderBusinessTimeline(home) {
    var timeline =
      (home && home.business_timeline) || (home && home.while_away) || {};
    var items = timeline.items || [];
    var head = sectionHead(
      "ma-ecc-timeline-title",
      timeline.title_ar || "سجل العمل",
      timeline.section_question_ar ||
        timeline.lead_ar ||
        "ما الذي حدث — ولماذا يهم؟"
    );

    if (!items.length) {
      return (
        '<section class="ma-ecc-band" data-ecc-section="timeline" aria-labelledby="ma-ecc-timeline-title">' +
        head +
        '<p class="ma-ecc-timeline__empty-note">' +
        esc(timeline.empty_message_ar || "لا أحداث بارزة مسجّلة بعد.") +
        "</p></section>"
      );
    }

    var list = '<ul class="ma-ecc-timeline">';
    items.slice(0, 6).forEach(function (item, idx) {
      var headline = String((item && item.headline_ar) || "").trim();
      if (!headline) return;
      var why = String(
        (item && (item.why_it_matters_ar || item.detail_ar)) || ""
      ).trim();
      list +=
        '<li class="ma-ecc-timeline__item">' +
        '<div class="ma-ecc-timeline__spine" aria-hidden="true">' +
        '<span class="ma-ecc-timeline__dot' +
        (idx === 0 ? " ma-ecc-timeline__dot--now" : "") +
        '"></span></div>' +
        '<div class="ma-ecc-timeline__main">' +
        '<p class="ma-ecc-timeline__type">حدث</p>' +
        '<p class="ma-ecc-timeline__headline">' +
        esc(headline) +
        "</p>" +
        (why
          ? '<p class="ma-ecc-copy ma-ecc-copy--muted"><span class="ma-ecc-why-k">لماذا يهم:</span> ' +
            esc(why) +
            "</p>"
          : "") +
        "</div>" +
        '<span class="ma-ecc-chip ma-ecc-chip--neutral">مسجّل</span>' +
        "</li>";
    });
    list += "</ul>";

    return (
      '<section class="ma-ecc-band" data-ecc-section="timeline" aria-labelledby="ma-ecc-timeline-title">' +
      head +
      list +
      "</section>"
    );
  }

  function renderHome(summary) {
    var home = (summary && summary.merchant_home_experience_v1) || {};
    if (!home || home.ok === false) {
      if (!home.greeting && !home.while_away && !home.attention_today) {
        home = {};
      }
    }

    // Daily Business Brief story (Constitution V3).
    return (
      '<div class="ma-ecc ma-ecc--intel-v3 ma-ecc--daily-brief-v1">' +
      renderBusinessHealth(home, summary) +
      renderRevenueRisk(home) +
      renderOpportunity(home) +
      renderTodaysPriority(home) +
      renderBusinessUnderstanding(home) +
      renderLearningProgress(home) +
      renderBusinessTimeline(home) +
      "</div>"
    );
  }

  function applyDashboardHomeV1(summary) {
    var root = byId("ma-home-experience-root");
    if (!root) return false;

    root.classList.remove(
      "ma-home-experience--loading",
      "ma-home-experience--calm",
      "ma-home-experience--legacy",
      "ma-pe-v2-home"
    );
    root.classList.add(
      "ma-dash-home-v1",
      "ma-dash-home-v3",
      "ma-dash-home-intel-v3",
      "ma-pe-v2-home"
    );

    if (!summary || summary.ok === false) {
      root.innerHTML = renderError(
        "تعذّر جلب ملخص المتجر. تحقّق من الاتصال ثم حدّث الصفحة."
      );
      return true;
    }

    try {
      root.innerHTML = renderHome(summary);
      if (
        summary.merchant_home_experience_v1 &&
        summary.merchant_home_experience_v1.empty_calm
      ) {
        root.classList.add("ma-home-experience--calm");
      }
      return true;
    } catch (err) {
      root.innerHTML = renderError("حدث خطأ أثناء عرض الرئيسية.");
      return true;
    }
  }

  function paintLoadingShell() {
    var root = byId("ma-home-experience-root");
    if (!root) return;
    if (root.getAttribute("data-ma-dh-boot") === "1") return;
    root.setAttribute("data-ma-dh-boot", "1");
    root.classList.add(
      "ma-dash-home-v1",
      "ma-dash-home-v3",
      "ma-dash-home-intel-v3",
      "ma-home-experience--loading"
    );
    root.innerHTML = renderLoading();
  }

  window.maApplyDashboardHomeV1 = applyDashboardHomeV1;
  window.maDashboardHomeV1Loading = paintLoadingShell;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", paintLoadingShell);
  } else {
    paintLoadingShell();
  }
})();
