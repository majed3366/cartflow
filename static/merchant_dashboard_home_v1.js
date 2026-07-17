/**
 * Dashboard Home — Knowledge Redistribution V1.
 * Story order: Today → Knowledge → Attention → Quick Indicators → Recent Activity.
 * One section · one question · no duplicated cognition. Presentation only.
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
    return goCartsOnclick();
  }

  function buildTodayChanges(home) {
    var whileAway = (home && home.while_away) || {};
    var items = whileAway.items || [];
    var parts = [];
    items.forEach(function (item) {
      var h = String((item && item.headline_ar) || "").trim();
      if (h) parts.push(h);
    });
    if (parts.length) return parts.slice(0, 3).join(" · ");
    return (
      String(whileAway.empty_message_ar || "").trim() ||
      "لا تغيّرات تشغيلية بارزة اليوم بعد."
    );
  }

  function renderLoading() {
    return (
      '<div class="ma-ecc-skel" aria-busy="true" aria-live="polite">' +
      '<div class="ma-ecc-skel__hero"></div>' +
      '<div class="ma-ecc-skel__block ma-ecc-skel__block--tall"></div>' +
      '<div class="ma-ecc-skel__metrics">' +
      '<span></span><span></span><span></span><span></span>' +
      "</div>" +
      '<p class="ma-ecc-whisper">نجهّز صورة متجرك…</p>' +
      "</div>"
    );
  }

  function renderError(message) {
    return (
      '<section class="ma-ecc-band" aria-label="خطأ">' +
      '<div class="ma-ecc-panel ma-ecc-panel--error">' +
      '<p class="ma-ecc-panel__title">تعذّر تحميل الرئيسية</p>' +
      '<p class="ma-ecc-copy">' +
      esc(message || "جرّب تحديث الصفحة. ما زلنا نتابع متجرك.") +
      "</p>" +
      '<button type="button" class="ma-ecc-btn ma-ecc-btn--ghost" onclick="location.reload()">' +
      "تحديث الصفحة" +
      "</button>" +
      "</div></section>"
    );
  }

  function renderHero(home, summary) {
    // Today = what changed (one summary). Event list belongs to Timeline only.
    var greeting = (home && home.greeting) || {};
    var greet = String(greeting.greeting_ar || greetingArFallback()).trim();
    var name = String(greeting.merchant_name_ar || "متجرك").trim();
    var date =
      String(greeting.date_ar || "").trim() ||
      String((summary && summary.merchant_ar_date_header) || "").trim();
    var today = buildTodayChanges(home);

    return (
      '<section class="ma-ecc-hero" aria-label="اليوم في متجرك" data-ecc-section="hero">' +
      '<div class="ma-ecc-hero__atmosphere" aria-hidden="true"></div>' +
      '<div class="ma-ecc-hero__grid">' +
      '<div class="ma-ecc-hero__main">' +
      '<p class="ma-ecc-hero__greet">' +
      esc(greet) +
      "، " +
      esc(name) +
      (date ? " · " + esc(date) : "") +
      "</p>" +
      '<h1 class="ma-ecc-hero__title">اليوم في متجرك</h1>' +
      '<p class="ma-ecc-hero__exec-label">ما الذي تغيّر اليوم؟</p>' +
      '<p class="ma-ecc-hero__exec-text">' +
      esc(today) +
      "</p>" +
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

  function renderKnowledge(home) {
    var section = (home && home.store_understanding) || {};
    var items = section.items || [];
    var head =
      '<header class="ma-ecc-kl__head">' +
      '<p class="ma-ecc-kicker">ماذا تعلّمنا؟</p>' +
      '<h2 class="ma-ecc-kl__title" id="ma-ecc-knowledge-title">' +
      esc(section.title_ar || "طبقة المعرفة") +
      "</h2>" +
      '<p class="ma-ecc-kl__purpose">ملاحظة → دليل → تفسير → ثقة</p>' +
      "</header>";

    if (!items.length) {
      return (
        '<section class="ma-ecc-band ma-ecc-band--knowledge" id="ma-home-understanding" data-ecc-section="knowledge" aria-labelledby="ma-ecc-knowledge-title">' +
        head +
        '<div class="ma-ecc-kl ma-ecc-kl--empty">' +
        '<div class="ma-ecc-kl" role="list">' +
        klStep(
          "الملاحظة",
          '<p class="ma-ecc-kl__observation">لا ملاحظة مؤكدة بعد</p>',
          "ma-ecc-kl__step--lead"
        ) +
        klStep(
          "الدليل",
          '<p class="ma-ecc-copy">نجمع أدلة نشاط المتجر.</p>'
        ) +
        klStep(
          "التفسير",
          '<p class="ma-ecc-copy">' +
            esc(
              section.empty_message_ar ||
                "لا فهم تجاري مؤكد بعد."
            ) +
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
      String(item.observation_ar || item.title_ar || "").trim() || "—";
    var evidence = String(item.evidence_label_ar || "").trim();
    var explanation = String(item.impact_ar || "").trim();
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
        "التفسير",
        '<p class="ma-ecc-copy">' +
          esc(explanation || "لا تفسير كافٍ بعد.") +
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
      '<section class="ma-ecc-band ma-ecc-band--knowledge" id="ma-home-understanding" data-ecc-section="knowledge" aria-labelledby="ma-ecc-knowledge-title">' +
      head +
      flow +
      "</section>"
    );
  }

  function metricCell(label, value, hint) {
    var v = String(value == null ? "" : value).trim();
    var empty = !v || v === EMPTY_VALUE;
    return (
      '<div class="ma-ecc-metric" role="group" aria-label="' +
      esc(label) +
      '">' +
      '<p class="ma-ecc-metric__label">' +
      esc(label) +
      "</p>" +
      '<p class="ma-ecc-metric__value' +
      (empty ? " ma-ecc-metric__value--empty" : "") +
      '">' +
      esc(empty ? EMPTY_VALUE : v) +
      "</p>" +
      '<p class="ma-ecc-metric__hint">' +
      esc(hint || (empty ? "لا بيانات كافية بعد" : "")) +
      "</p></div>"
    );
  }

  function renderMetrics(summary) {
    var revenue = String((summary && summary.merchant_kpi_revenue_fmt) || "").trim();
    var purchased = String((summary && summary.merchant_kpi_recovered_fmt) || "").trim();
    var abandoned = String((summary && summary.merchant_kpi_abandoned_fmt) || "").trim();
    var pctRaw = summary && summary.merchant_kpi_recovered_pct_vs_abandoned;
    var pct =
      pctRaw === 0 || pctRaw === "0"
        ? "0٪"
        : pctRaw != null && String(pctRaw).trim() !== ""
          ? String(pctRaw).trim() + "٪"
          : "";

    return (
      '<section class="ma-ecc-band" data-ecc-section="metrics" aria-labelledby="ma-ecc-metrics-title">' +
      '<header class="ma-ecc-band__head">' +
      '<h2 class="ma-ecc-band__title" id="ma-ecc-metrics-title">مؤشرات سريعة</h2>' +
      '<p class="ma-ecc-band__purpose">هل المتجر يتحسّن أم يتراجع؟</p>' +
      "</header>" +
      '<div class="ma-ecc-metrics" role="list">' +
      metricCell(
        "اتجاه الاسترجاع",
        abandoned,
        abandoned ? "سلال متروكة اليوم" : "لا اتجاه كافٍ بعد"
      ) +
      metricCell(
        "اتجاه التحويل",
        pct,
        pct ? "مسترد مقابل متروك · اليوم" : "لا اتجاه كافٍ بعد"
      ) +
      metricCell(
        "الإيرادات المستعادة",
        revenue,
        revenue ? "اليوم · ريال" : "لا اتجاه كافٍ بعد"
      ) +
      metricCell(
        "العملاء المشترون",
        purchased,
        purchased ? "اليوم" : "لا اتجاه كافٍ بعد"
      ) +
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

  function renderAttention(home) {
    var att = (home && home.attention_today) || {};
    var items = att.items || [];
    var head =
      '<header class="ma-ecc-band__head">' +
      '<h2 class="ma-ecc-band__title" id="ma-ecc-attention-title">' +
      esc(att.title_ar || "مركز الانتباه") +
      "</h2>" +
      '<p class="ma-ecc-band__purpose">' +
      esc(att.lead_ar || "ما الذي يحتاج قرارك الآن؟") +
      "</p>" +
      "</header>";

    if (!items.length) {
      return (
        '<section class="ma-ecc-band ma-ecc-band--attention" data-ecc-section="attention" aria-labelledby="ma-ecc-attention-title">' +
        head +
        '<div class="ma-ecc-attention-empty">' +
        '<span class="ma-ecc-attention-empty__mark" aria-hidden="true">✓</span>' +
        '<div>' +
        '<p class="ma-ecc-attention-empty__title">لا قرار مطلوب الآن</p>' +
        '<p class="ma-ecc-copy">' +
        esc(att.empty_message_ar || "لا قرار مطلوب منك الآن.") +
        "</p></div></div></section>"
      );
    }

    var list = '<ol class="ma-ecc-attention">';
    items.forEach(function (item, idx) {
      var tone = severityTone(item);
      var badge =
        String(item.decision_class_label_ar || "").trim() ||
        (tone === "critical"
          ? "حرج"
          : tone === "attention"
            ? "يحتاج انتباهك"
            : "مهم");
      var action =
        String(item.action_ar || item.cta_label_ar || "").trim() ||
        (idx === 0 ? "عرض السلال المتأثرة" : "");
      var outcome = String(item.expected_outcome_ar || "").trim();
      var ifIgnored = String(item.if_ignored_ar || "").trim();
      list +=
        '<li class="ma-ecc-attention__item ma-ecc-attention__item--' +
        tone +
        '" data-decision-key="' +
        esc(item.operational_decision_key || "") +
        '" data-queue-position="' +
        (item.queue_position || idx + 1) +
        '">' +
        '<div class="ma-ecc-attention__rail" aria-hidden="true">' +
        '<span class="ma-ecc-attention__index">' +
        (item.queue_position || idx + 1) +
        "</span></div>" +
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
        "</div></li>";
    });
    list += "</ol>";

    return (
      '<section class="ma-ecc-band ma-ecc-band--attention" data-ecc-section="attention" aria-labelledby="ma-ecc-attention-title">' +
      head +
      list +
      "</section>"
    );
  }

  function renderTimeline(home) {
    // Pure timeline — what happened. Never invents interpretation.
    var whileAway = (((home && home.while_away) || {}).items) || [];
    var head =
      '<header class="ma-ecc-band__head">' +
      '<h2 class="ma-ecc-band__title" id="ma-ecc-timeline-title">آخر النشاطات</h2>' +
      '<p class="ma-ecc-band__purpose">ما الذي حدث فعلياً؟</p>' +
      "</header>";

    if (!whileAway.length) {
      return (
        '<section class="ma-ecc-band" data-ecc-section="timeline" aria-labelledby="ma-ecc-timeline-title">' +
        head +
        '<p class="ma-ecc-timeline__empty-note">لا أحداث مسجّلة بعد.</p>' +
        "</section>"
      );
    }

    var list = '<ul class="ma-ecc-timeline">';
    whileAway.slice(0, 6).forEach(function (item, idx) {
      var headline = String((item && item.headline_ar) || "").trim();
      if (!headline) return;
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

    // Home story: Today → Knowledge → Attention → Direction → Timeline.
    return (
      '<div class="ma-ecc ma-ecc--intel-v3 ma-ecc--redistribution-v1">' +
      renderHero(home, summary) +
      renderKnowledge(home) +
      renderAttention(home) +
      renderMetrics(summary) +
      renderTimeline(home) +
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
