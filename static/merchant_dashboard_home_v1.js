/**
 * Dashboard Home — Daily Business Brief V1 (Constitution V3).
 * Adaptive Cognition V2: path focus + section order are merchant-visible.
 * Experience Reality Fix V1: layout integrity + intelligence on the surface.
 */
(function () {
  "use strict";

  var EMPTY_VALUE = "—";
  var ACF_SESSION_KEY = "cf_acf_home_session_v1";
  var ACF_LOCK_KEY = "cf_acf_home_lock_v1";
  var DEFAULT_SECTION_ORDER = [
    "business_health",
    "biggest_revenue_risk",
    "biggest_opportunity",
    "todays_priority",
    "business_understanding",
    "learning_progress",
    "business_timeline",
  ];

  /** Merchant-facing path copy — never expose route letters as product UI. */
  var PATH_FOCUS_AR = {
    A: {
      kicker: "وضع اليوم",
      title: "عملك في مسار مستقر",
      hint: "نبدأ بصورة الصحة، ثم بما نفهمه عن متجرك، ثم الاتجاه.",
      spotlight: "business_understanding",
    },
    B: {
      kicker: "يحتاج قرارك الآن",
      title: "هناك أمر يستحق انتباهك فوراً",
      hint: "نضع أولوية اليوم أولاً — ثم نوضح الخطر والسبب.",
      spotlight: "todays_priority",
    },
    C: {
      kicker: "عميل مهم",
      title: "عميل VIP بانتظار تواصلك",
      hint: "التواصل اليدوي هو الخطوة الأولى — التفاصيل تأتي بعده.",
      spotlight: "todays_priority",
    },
    D: {
      kicker: "أثر تشغيلي",
      title: "إعداد أو قناة يؤثر على استرجاعك",
      hint: "نبدأ بما يؤثر على عمل القنوات — قبل تفسير أوسع للأرقام.",
      spotlight: "todays_priority",
    },
    E: {
      kicker: "أدلة محدودة",
      title: "نعرض فقط ما نملك عليه أدلة كافية",
      hint: "لا قرار مبكر. نغلق بما نعرفه بصراحة حتى تكتمل الصورة.",
      spotlight: "business_timeline",
    },
    F: {
      kicker: "الفهم قيد التشكيل",
      title: "ما زلنا نبني فهماً واضحاً لمتجرك",
      hint: "نوضح أين وصل الفهم — بدون دفعك لقرار غير ناضج.",
      spotlight: "business_understanding",
    },
  };

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

  /** E1 — Business Health (Executive Home Constitution V1 · Sprint 1 only). */
  function renderBusinessHealth(home, summary) {
    var greeting = (home && home.greeting) || {};
    var health = (home && home.business_health) || {};
    var disclosure = health.disclosure || {};
    var greet = String(greeting.greeting_ar || greetingArFallback()).trim();
    var name = String(greeting.merchant_name_ar || "متجرك").trim();
    var date =
      String(greeting.date_ar || "").trim() ||
      String((summary && summary.merchant_ar_date_header) || "").trim();
    var status = String(health.status_ar || "").trim() || "قيد التقييم";
    var summaryText =
      String(health.summary_ar || "").trim() ||
      String(health.empty_message_ar || "").trim() ||
      "نجمع صورة أوضح لصحة عملك.";
    var confTone = confidenceTone(health.confidence);
    var conf =
      String(health.confidence_ar || "").trim() ||
      confidenceLabelAr(health.confidence);
    var attentionNeeded = !!health.attention_required;
    var question = String(
      health.section_question_ar ||
        health.lead_ar ||
        "هل عملي بصحة جيدة اليوم؟"
    ).trim();
    var trend = String(
      disclosure.trend_ar || health.direction_ar || ""
    ).trim();
    var evidence = String(
      disclosure.evidence_ar || health.evidence_summary_ar || ""
    ).trim();
    // Never paint engineering / counter-style proof on L0 or disclosure body
    if (/[=_]/.test(evidence) || /\d+\s*سلة/.test(evidence)) {
      evidence = "";
    }
    var discLabel = String(
      disclosure.label_ar || "كيف وصلنا لهذه الصورة؟"
    ).trim();
    var hasDisclosure = !!(trend || evidence);
    var statusTone = attentionNeeded
      ? "attention"
      : status.indexOf("جيدة") >= 0 || status.indexOf("مستقر") >= 0
        ? "ok"
        : "neutral";

    return (
      '<section class="ma-ecc-hero ma-ecc-hero--e1" aria-label="صحة العمل" data-ecc-section="health" data-executive-band="E1">' +
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
      esc(question) +
      "</p>" +
      '<p class="ma-ecc-hero__exec-text">' +
      '<span class="ma-ecc-chip ma-ecc-chip--' +
      statusTone +
      '">' +
      esc(status) +
      "</span> " +
      esc(summaryText) +
      "</p>" +
      '<p class="ma-ecc-copy ma-ecc-hero__confidence" data-e1-confidence="1">' +
      '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
      confTone +
      '">' +
      esc(conf) +
      "</span></p>" +
      (hasDisclosure
        ? '<details class="ma-ecc-e1-disclosure">' +
          "<summary>" +
          esc(discLabel) +
          "</summary>" +
          (trend
            ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الاتجاه:</span> ' +
              esc(trend) +
              "</p>"
            : "") +
          (evidence
            ? '<p class="ma-ecc-copy ma-ecc-copy--muted">' + esc(evidence) + "</p>"
            : "") +
          "</details>"
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

    var riskDetail = "";
    if (item.evidence_ar) {
      riskDetail +=
        '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الدليل:</span> ' +
        esc(item.evidence_ar) +
        "</p>";
    }
    if (item.commercial_impact_ar) {
      riskDetail +=
        '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الأثر التجاري:</span> ' +
        esc(item.commercial_impact_ar) +
        "</p>";
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
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الثقة:</span> ' +
      '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
      confidenceTone(item.confidence) +
      '">' +
      esc(confidenceLabelAr(item.confidence)) +
      "</span></p>" +
      (riskDetail
        ? '<details class="ma-ecc-details"><summary>التفاصيل والأثر</summary><div class="ma-ecc-details__body">' +
          riskDetail +
          "</div></details>"
        : "") +
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
    var lead =
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">المرحلة الآن:</span> ' +
      esc(stage) +
      (channel ? " · " + esc(channel) : "") +
      "</p>" +
      (nextMerchant
        ? '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">' +
          (merchantRequired ? "دورك الآن:" : "دورك:") +
          "</span> " +
          esc(nextMerchant) +
          "</p>"
        : "");
    var extras = "";
    if (why) {
      extras +=
        '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">لماذا هنا:</span> ' +
        esc(why) +
        "</p>";
    }
    if (blocker) {
      extras +=
        '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الحاجز:</span> ' +
        esc(blocker) +
        "</p>";
    }
    if (nextPlatform) {
      extras +=
        '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">المنصة الآن:</span> ' +
        esc(nextPlatform) +
        "</p>";
    }
    if (completion) {
      extras +=
        '<p class="ma-ecc-copy ma-ecc-copy--muted"><span class="ma-ecc-why-k">يكتمل عندما:</span> ' +
        esc(completion) +
        "</p>";
    }
    return (
      '<div class="ma-ecc-journey" data-recovery-stage="' +
      esc(
        (journey && journey.recovery_stage_key) || item.recovery_stage_key || ""
      ) +
      '">' +
      '<p class="ma-ecc-journey__title">مسار الاسترجاع</p>' +
      lead +
      (extras
        ? '<details class="ma-ecc-details"><summary>تفاصيل المسار</summary><div class="ma-ecc-details__body">' +
          extras +
          "</div></details>"
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
      (ifIgnored
        ? '<details class="ma-ecc-details"><summary>إذا تجاهلت هذا</summary><div class="ma-ecc-details__body">' +
          '<p class="ma-ecc-copy ma-ecc-copy--muted">' +
          esc(ifIgnored) +
          "</p></div></details>"
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
    var leadItem = items[0] || null;
    var commercialQ = String(
      (leadItem && leadItem.commercial_question_ar) ||
        section.section_question_ar ||
        section.lead_ar ||
        "ماذا نفهم عن عملك الآن؟"
    ).trim();
    var head =
      '<header class="ma-ecc-kl__head">' +
      '<p class="ma-ecc-kicker">' +
      esc(commercialQ) +
      "</p>" +
      '<h2 class="ma-ecc-kl__title" id="ma-ecc-understanding-title">' +
      esc(section.title_ar || "فهم العمل") +
      "</h2>" +
      '<p class="ma-ecc-kl__purpose">' +
      esc(
        section.purpose_ar ||
          "سؤال تجاري → إجابة → دليل → ثقة → معنى للتاجر"
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

    var oneLiner = commercial || meaning || direction || "";
    var detailFlow =
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

    var lead =
      '<p class="ma-ecc-insight-lead">' +
      esc(observation) +
      "</p>" +
      (oneLiner
        ? '<p class="ma-ecc-insight-one">' + esc(oneLiner) + "</p>"
        : "") +
      '<p class="ma-ecc-copy"><span class="ma-ecc-why-k">الثقة:</span> ' +
      '<span class="ma-ecc-chip ma-ecc-chip--conf-' +
      confTone +
      '">' +
      esc(conf) +
      "</span></p>" +
      '<details class="ma-ecc-details"><summary>كيف وصلنا لهذا الفهم</summary><div class="ma-ecc-details__body">' +
      detailFlow +
      "</div></details>";

    return (
      '<section class="ma-ecc-band ma-ecc-band--knowledge" id="ma-home-understanding" data-ecc-section="understanding" aria-labelledby="ma-ecc-understanding-title">' +
      head +
      lead +
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

  function readAcfQuery() {
    try {
      var q = new URLSearchParams(window.location.search || "");
      return {
        fixture: String(q.get("acf_fixture") || "").trim(),
        trigger: String(q.get("acf_trigger") || "").trim(),
        session: String(q.get("acf_session") || "").trim(),
      };
    } catch (e) {
      return { fixture: "", trigger: "", session: "" };
    }
  }

  function sectionAdmitted(home, key) {
    if (!home) return true;
    var section = null;
    if (key === "business_health") section = home.business_health;
    else if (key === "todays_priority")
      section = home.todays_priority || home.attention_today;
    else if (key === "biggest_revenue_risk") section = home.biggest_revenue_risk;
    else if (key === "biggest_opportunity") section = home.biggest_opportunity;
    else if (key === "business_understanding")
      section = home.business_understanding || home.store_understanding;
    else if (key === "learning_progress") section = home.learning_progress;
    else if (key === "business_timeline")
      section = home.business_timeline || home.while_away;
    if (!section) return false;
    if (key === "business_health") return true;
    var adm = section.home_admission_v1;
    if (adm && typeof adm.admitted === "boolean") return !!adm.admitted;
    if (section.suppressed === true) return false;
    return true;
  }

  function resolveSectionOrder(home) {
    var acf = (home && home.adaptive_cognition_v1) || {};
    var order = acf.section_order;
    if (!order || !order.length) {
      try {
        var locked = sessionStorage.getItem(ACF_LOCK_KEY);
        if (locked) {
          var parsed = JSON.parse(locked);
          if (parsed && parsed.section_order && parsed.section_order.length) {
            order = parsed.section_order;
          }
        }
      } catch (e2) {
        order = null;
      }
    }
    if (!order || !order.length) order = DEFAULT_SECTION_ORDER.slice();
    var seen = {};
    var out = [];
    for (var i = 0; i < order.length; i++) {
      var key = String(order[i] || "");
      if (!key || seen[key]) continue;
      if (!sectionAdmitted(home, key)) continue;
      seen[key] = 1;
      out.push(key);
    }
    // Do NOT re-append suppressed sections. Composition owns admission.
    if (!seen.business_health) out.unshift("business_health");
    return out.length ? out : ["business_health"];
  }

  function renderSectionByKey(key, home, summary) {
    if (key === "business_health") return renderBusinessHealth(home, summary);
    if (key === "biggest_revenue_risk") return renderRevenueRisk(home);
    if (key === "biggest_opportunity") return renderOpportunity(home);
    if (key === "todays_priority") return renderTodaysPriority(home);
    if (key === "business_understanding") return renderBusinessUnderstanding(home);
    if (key === "learning_progress") return renderLearningProgress(home);
    if (key === "business_timeline") return renderBusinessTimeline(home);
    return "";
  }

  function pathFocusMeta(path) {
    var key = String(path || "A").trim().toUpperCase();
    return PATH_FOCUS_AR[key] || PATH_FOCUS_AR.A;
  }

  function renderPathFocus(acf) {
    var path = String((acf && acf.selected_path) || "").trim().toUpperCase();
    if (!path || !PATH_FOCUS_AR[path]) return "";
    var meta = pathFocusMeta(path);
    return (
      '<aside class="ma-ecc-focus" data-ecc-section="path-focus" aria-label="تركيز اليوم">' +
      '<p class="ma-ecc-focus__kicker">' +
      esc(meta.kicker) +
      "</p>" +
      '<p class="ma-ecc-focus__title">' +
      esc(meta.title) +
      "</p>" +
      '<p class="ma-ecc-focus__hint">' +
      esc(meta.hint) +
      "</p>" +
      "</aside>"
    );
  }

  function markBandModifier(html, modClass) {
    if (!html) return html;
    return html.replace(
      /class="ma-ecc-band([^"]*)"/,
      'class="ma-ecc-band$1 ' + modClass + '"'
    ).replace(
      /class="ma-ecc-hero"/,
      'class="ma-ecc-hero ' + modClass + '"'
    );
  }

  function renderHome(summary) {
    var home = (summary && summary.merchant_home_experience_v1) || {};
    if (!home || home.ok === false) {
      if (!home.greeting && !home.while_away && !home.attention_today) {
        home = {};
      }
    }

    var acf = home.adaptive_cognition_v1 || {};
    var path = String(acf.selected_path || "").trim().toUpperCase();
    var focusMeta = pathFocusMeta(path || "A");
    var spotlightKey = focusMeta.spotlight;
    var order = resolveSectionOrder(home);
    var html = "";
    var sawHealth = false;
    for (var i = 0; i < order.length; i++) {
      var key = order[i];
      var chunk = renderSectionByKey(key, home, summary);
      if (!chunk) continue;
      if (key === "business_health") {
        html += chunk;
        sawHealth = true;
        html += renderPathFocus(acf);
        continue;
      }
      if (!sawHealth && i === 0) {
        html += renderPathFocus(acf);
      }
      if (key === spotlightKey) {
        chunk = markBandModifier(chunk, "ma-ecc-band--spotlight");
      } else if (
        key === "learning_progress" ||
        key === "business_timeline" ||
        (spotlightKey === "todays_priority" &&
          (key === "biggest_opportunity" || key === "business_understanding"))
      ) {
        chunk = markBandModifier(chunk, "ma-ecc-band--secondary");
      }
      html += chunk;
    }
    if (html.indexOf("ma-ecc-focus") === -1) {
      html = renderPathFocus(acf) + html;
    }

    var pathAttr = path
      ? ' data-acf-path="' + esc(path) + '"'
      : "";
    var labelAttr = acf.path_label
      ? ' data-acf-label="' + esc(String(acf.path_label)) + '"'
      : "";
    var pathClass = path ? " ma-ecc--path-" + path : "";

    return (
      '<div class="ma-ecc ma-ecc--intel-v3 ma-ecc--daily-brief-v1 ma-ecc--acf-v2 ma-ecc--reality-v1' +
      pathClass +
      '"' +
      pathAttr +
      labelAttr +
      ">" +
      html +
      "</div>"
    );
  }

  function persistAcfSession(home) {
    var acf = (home && home.adaptive_cognition_v1) || {};
    if (!acf || !acf.session_id) return;
    try {
      sessionStorage.setItem(ACF_SESSION_KEY, String(acf.session_id));
      sessionStorage.setItem(
        ACF_LOCK_KEY,
        JSON.stringify({
          session_id: acf.session_id,
          selected_path: acf.selected_path,
          section_order: acf.section_order || [],
          locked_at: Date.now(),
        })
      );
    } catch (e) {
      /* ignore */
    }
    try {
      document.cookie =
        "cf_acf_session=" +
        encodeURIComponent(String(acf.session_id)) +
        "; path=/; SameSite=Lax";
    } catch (e2) {
      /* ignore */
    }
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
      persistAcfSession(summary.merchant_home_experience_v1 || {});
      return true;
    } catch (err) {
      root.innerHTML = renderError("حدث خطأ أثناء عرض الرئيسية.");
      return true;
    }
  }

  /** Build /api/dashboard/summary query for Adaptive Cognition session stability. */
  function maAcfSummaryQuery() {
    var q = readAcfQuery();
    var params = [];
    var trigger = q.trigger;
    if (!trigger) {
      try {
        var nav = performance.getEntriesByType && performance.getEntriesByType("navigation");
        if (nav && nav[0] && nav[0].type === "reload") {
          trigger = "full_page_refresh";
        }
      } catch (e) {
        /* ignore */
      }
    }
    if (!trigger) {
      try {
        if (!sessionStorage.getItem(ACF_SESSION_KEY)) trigger = "session_start";
        else trigger = "view_stable";
      } catch (e2) {
        trigger = "session_start";
      }
    }
    var sid = q.session;
    if (!sid) {
      try {
        sid = sessionStorage.getItem(ACF_SESSION_KEY) || "";
      } catch (e3) {
        sid = "";
      }
    }
    if (trigger) params.push("acf_trigger=" + encodeURIComponent(trigger));
    if (sid) params.push("acf_session=" + encodeURIComponent(sid));
    if (q.fixture) params.push("acf_fixture=" + encodeURIComponent(q.fixture));
    return params.length ? params.join("&") : "";
  }

  window.maAcfSummaryQuery = maAcfSummaryQuery;
  window.maAcfMarkReturnFromSurface = function () {
    try {
      sessionStorage.setItem("cf_acf_pending_trigger", "return_from_surface");
    } catch (e) {
      /* ignore */
    }
  };

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
