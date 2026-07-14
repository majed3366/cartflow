/**
 * Dashboard Home UI V1 — production preview renderer.
 * Approved IA order: Hero → Metric Grid → Attention → Knowledge → Performance → Timeline.
 * Presentation only — consumes existing summary + merchant_home_experience_v1.
 * Never invents KPIs or fake activity.
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

  function confidenceBadgeClass(raw) {
    var c = String(raw || "")
      .trim()
      .toLowerCase();
    if (c === "high" || c === "confirmed") return "";
    if (c === "medium") return "ma-dh-badge--attention";
    if (c === "low") return "ma-dh-badge--attention";
    return "ma-dh-badge--neutral";
  }

  function severityClass(item) {
    var s = String((item && item.severity) || "").trim().toLowerCase();
    var cls = String((item && item.decision_class) || "").trim().toLowerCase();
    if (s === "critical" || cls === "critical_action") return "critical";
    if (s === "attention" || s === "suggested" || cls === "needs_attention" || cls === "suggested_action") {
      return "attention";
    }
    return "default";
  }

  function metricValueHtml(value, hint) {
    var v = String(value == null ? "" : value).trim();
    if (!v || v === EMPTY_VALUE) {
      return (
        '<p class="ma-dh-metric__value ma-dh-metric__value--empty">' +
        esc(EMPTY_VALUE) +
        "</p>" +
        (hint
          ? '<p class="ma-dh-metric__hint">' + esc(hint) + "</p>"
          : '<p class="ma-dh-metric__hint">لا بيانات كافية بعد</p>')
      );
    }
    return (
      '<p class="ma-dh-metric__value">' +
      esc(v) +
      "</p>" +
      (hint ? '<p class="ma-dh-metric__hint">' + esc(hint) + "</p>" : "")
    );
  }

  function buildExecutiveSummary(home) {
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
      "CartFlow يتابع متجرك — سنُظهر الملخص هنا عند توفر نشاط اليوم."
    );
  }

  function primaryAttention(home) {
    var att = (home && home.attention_today) || {};
    var items = att.items || [];
    return items.length ? items[0] : null;
  }

  function goCartsOnclick() {
    return ' onclick="if(window.goToSection){goToSection(\'carts\');}else if(window.goTo){goTo(\'carts\');}return false;"';
  }

  function renderLoading() {
    return (
      '<div class="ma-dh-skeleton" aria-busy="true" aria-live="polite">' +
      '<div class="ma-dh-skel-block ma-dh-skel-block--hero"></div>' +
      '<div class="ma-dh-skel-grid">' +
      '<div class="ma-dh-skel-block"></div>' +
      '<div class="ma-dh-skel-block"></div>' +
      '<div class="ma-dh-skel-block"></div>' +
      '<div class="ma-dh-skel-block"></div>' +
      "</div>" +
      '<div class="ma-dh-skel-block"></div>' +
      '<div class="ma-dh-skel-block"></div>' +
      '<p class="ma-dh-meta">CartFlow يجهّز ملخص يومك…</p>' +
      "</div>"
    );
  }

  function renderError(message) {
    return (
      '<section class="ma-dh-section" aria-label="خطأ">' +
      '<div class="ma-dh-card ma-dh-card--error ma-dh-error">' +
      '<p class="ma-dh-error__title">تعذّر تحميل الرئيسية</p>' +
      '<p class="ma-dh-body">' +
      esc(message || "جرّب تحديث الصفحة. CartFlow ما زال يتابع متجرك.") +
      "</p>" +
      '<button type="button" class="ma-dh-btn ma-dh-btn--ghost" onclick="location.reload()">' +
      "تحديث الصفحة" +
      "</button>" +
      "</div></section>"
    );
  }

  function renderHero(home, summary) {
    var greeting = (home && home.greeting) || {};
    var greet = String(greeting.greeting_ar || greetingArFallback()).trim();
    var name = String(greeting.merchant_name_ar || "متجرك").trim();
    var date =
      String(greeting.date_ar || "").trim() ||
      String((summary && summary.merchant_ar_date_header) || "").trim();
    var exec = buildExecutiveSummary(home);
    var priority = primaryAttention(home);

    var priorityHtml;
    if (priority) {
      var actionLabel = String(priority.action_ar || "عرض السلال").trim();
      priorityHtml =
        '<div class="ma-dh-hero__priority">' +
        '<p class="ma-dh-hero__label">أولوية اليوم</p>' +
        '<h2 class="ma-dh-headline">' +
        esc(priority.headline_ar || "—") +
        "</h2>" +
        (priority.why_ar
          ? '<p class="ma-dh-body">' + esc(priority.why_ar) + "</p>"
          : "") +
        '<a class="ma-dh-btn ma-dh-btn--on-dark" href="#carts" role="button"' +
        goCartsOnclick() +
        ">" +
        esc(actionLabel) +
        "</a>" +
        "</div>";
    } else {
      priorityHtml =
        '<div class="ma-dh-hero__priority">' +
        '<p class="ma-dh-hero__label">أولوية اليوم</p>' +
        '<p class="ma-dh-body">' +
        esc(
          ((home && home.attention_today) || {}).empty_message_ar ||
            "لا أمور تتطلب انتباهك الآن — CartFlow يتابع الحالات الروتينية."
        ) +
        "</p>" +
        "</div>";
    }

    return (
      '<section class="ma-dh-section ma-dh-hero-wrap" aria-label="اليوم في متجرك">' +
      '<div class="ma-dh-hero">' +
      '<div class="ma-dh-hero__glow" aria-hidden="true"></div>' +
      '<p class="ma-dh-hero__greet">' +
      esc(greet) +
      "، " +
      esc(name) +
      (date ? " · " + esc(date) : "") +
      "</p>" +
      '<h1 class="ma-dh-hero__title">اليوم في متجرك</h1>' +
      '<div class="ma-dh-hero__block">' +
      '<p class="ma-dh-hero__label">ملخص تنفيذي</p>' +
      '<p class="ma-dh-hero__exec">' +
      esc(exec) +
      "</p>" +
      "</div>" +
      priorityHtml +
      "</div></section>"
    );
  }

  function renderMetricGrid(summary, home) {
    var revenue = String((summary && summary.merchant_kpi_revenue_fmt) || "").trim();
    var purchased = String((summary && summary.merchant_kpi_recovered_fmt) || "").trim();
    var understanding = (((home && home.store_understanding) || {}).items) || [];
    var klValue = understanding.length ? String(understanding.length) : "";
    var klHint = understanding.length
      ? understanding.length === 1
        ? "ملاحظة واحدة متاحة"
        : understanding.length + " ملاحظات متاحة"
      : "لا ملاحظات كافية بعد";

    // Customers returned: no governed today-KPI on summary — never invent.
    var returnedValue = "";
    var returnedHint = "لا بيانات كافية بعد";

    function cell(label, valueHtml) {
      return (
        '<article class="ma-dh-card ma-dh-metric" aria-label="' +
        esc(label) +
        '">' +
        '<p class="ma-dh-metric__label">' +
        esc(label) +
        "</p>" +
        valueHtml +
        "</article>"
      );
    }

    return (
      '<section class="ma-dh-section" aria-labelledby="ma-dh-metrics-title">' +
      '<header class="ma-dh-section__head">' +
      '<h2 class="ma-dh-section__title" id="ma-dh-metrics-title">مؤشرات سريعة</h2>' +
      '<p class="ma-dh-section__purpose">أرقام اليوم من بيانات متجرك — بدون تقدير.</p>' +
      "</header>" +
      '<div class="ma-dh-metric-grid">' +
      cell("الإيرادات المستعادة", metricValueHtml(revenue, "اليوم · ريال")) +
      cell("العملاء المشترون", metricValueHtml(purchased, "اليوم")) +
      cell("العملاء العائدون", metricValueHtml(returnedValue, returnedHint)) +
      cell("طبقة المعرفة", metricValueHtml(klValue, klHint)) +
      "</div></section>"
    );
  }

  function renderAttention(home) {
    var att = (home && home.attention_today) || {};
    var items = att.items || [];
    var head =
      '<header class="ma-dh-section__head">' +
      '<h2 class="ma-dh-section__title" id="ma-dh-attention-title">' +
      esc(att.title_ar || "ما يحتاج انتباهك") +
      "</h2>" +
      '<p class="ma-dh-section__purpose">الحالات التي تستحق تدخلك الآن.</p>' +
      "</header>";

    if (!items.length) {
      return (
        '<section class="ma-dh-section" aria-labelledby="ma-dh-attention-title">' +
        head +
        '<div class="ma-dh-card ma-dh-card--empty ma-dh-empty">' +
        '<p class="ma-dh-empty__title">كل شيء هادئ</p>' +
        '<p class="ma-dh-body">' +
        esc(
          att.empty_message_ar ||
            "لا أمور تتطلب انتباهك الآن — CartFlow يتابع الحالات الروتينية."
        ) +
        "</p></div></section>"
      );
    }

    var stack = '<div class="ma-dh-attention-stack">';
    items.forEach(function (item, idx) {
      var sev = severityClass(item);
      var cardMod =
        sev === "critical"
          ? " ma-dh-card--critical"
          : sev === "attention"
            ? " ma-dh-card--warning"
            : " ma-dh-card--attention";
      var badgeMod =
        sev === "critical"
          ? " ma-dh-badge--critical"
          : sev === "attention"
            ? " ma-dh-badge--attention"
            : "";
      var badgeText =
        String(item.decision_class_label_ar || "").trim() ||
        (sev === "critical" ? "حرج" : sev === "attention" ? "يحتاج انتباهك" : "مهم");
      var action = String(item.action_ar || "").trim();
      stack +=
        '<article class="ma-dh-card' +
        cardMod +
        '">' +
        '<span class="ma-dh-badge' +
        badgeMod +
        '">' +
        esc(badgeText) +
        "</span>" +
        '<h3 class="ma-dh-headline">' +
        esc(item.headline_ar || "—") +
        "</h3>" +
        (item.why_ar
          ? '<p class="ma-dh-body">' + esc(item.why_ar) + "</p>"
          : "") +
        (action
          ? '<a class="ma-dh-btn" href="#carts" role="button"' +
            goCartsOnclick() +
            ">" +
            esc(action) +
            "</a>"
          : idx === 0
            ? '<a class="ma-dh-btn" href="#carts" role="button"' +
              goCartsOnclick() +
              ">عرض السلال</a>"
            : "") +
        "</article>";
    });
    stack += "</div>";

    return (
      '<section class="ma-dh-section" aria-labelledby="ma-dh-attention-title">' +
      head +
      stack +
      "</section>"
    );
  }

  function renderKnowledge(home) {
    var section = (home && home.store_understanding) || {};
    var items = section.items || [];
    var head =
      '<header class="ma-dh-section__head">' +
      '<h2 class="ma-dh-section__title" id="ma-dh-knowledge-title">طبقة المعرفة</h2>' +
      '<p class="ma-dh-section__purpose">ملاحظة · تردد · توصية · ثقة — من قرار المنظومة.</p>' +
      "</header>";

    if (!items.length) {
      return (
        '<section class="ma-dh-section" id="ma-home-understanding" aria-labelledby="ma-dh-knowledge-title">' +
        head +
        '<div class="ma-dh-card ma-dh-card--elevated ma-dh-card--empty ma-dh-empty">' +
        '<p class="ma-dh-empty__title">لا ملاحظات كافية بعد</p>' +
        '<p class="ma-dh-body">' +
        esc(
          section.empty_message_ar ||
            "لا توجد استنتاجات كافية بعد — استمر في جمع النشاط."
        ) +
        "</p></div></section>"
      );
    }

    var item = items[0];
    var observation =
      String(item.observation_ar || item.title_ar || "").trim() || "—";
    var hesitation = String(item.impact_ar || "").trim();
    var recommendation = String(item.action_ar || "").trim();
    var conf = confidenceLabelAr(item.confidence);
    var confClass = confidenceBadgeClass(item.confidence);
    var evidence = String(item.evidence_label_ar || "").trim();

    return (
      '<section class="ma-dh-section" id="ma-home-understanding" aria-labelledby="ma-dh-knowledge-title">' +
      head +
      '<div class="ma-dh-card ma-dh-card--elevated">' +
      '<div class="ma-dh-kl-grid">' +
      '<div class="ma-dh-kl-block ma-dh-kl-block--full">' +
      '<p class="ma-dh-kl-block__label">أهم ملاحظة</p>' +
      '<h3 class="ma-dh-headline">' +
      esc(observation) +
      "</h3>" +
      (evidence
        ? '<p class="ma-dh-meta">المصدر: ' + esc(evidence) + "</p>"
        : "") +
      "</div>" +
      '<div class="ma-dh-kl-block">' +
      '<p class="ma-dh-kl-block__label">سبب التردد</p>' +
      '<p class="ma-dh-body">' +
      esc(hesitation || "لا سبب تردد واضح بعد.") +
      "</p></div>" +
      '<div class="ma-dh-kl-block">' +
      '<p class="ma-dh-kl-block__label">توصية واحدة</p>' +
      '<p class="ma-dh-body">' +
      esc(recommendation || "لا توصية جاهزة بعد.") +
      "</p>" +
      (recommendation
        ? '<a class="ma-dh-btn" href="#carts" role="button" style="margin-top:10px;"' +
          goCartsOnclick() +
          ">" +
          esc(recommendation) +
          "</a>"
        : "") +
      "</div>" +
      '<div class="ma-dh-kl-block ma-dh-kl-block--full">' +
      '<p class="ma-dh-kl-block__label">مستوى الثقة</p>' +
      '<span class="ma-dh-badge ' +
      esc(confClass) +
      '">' +
      esc(conf) +
      "</span>" +
      "</div>" +
      "</div></div></section>"
    );
  }

  function renderPerformance(summary) {
    var abandoned = String((summary && summary.merchant_kpi_abandoned_fmt) || "").trim();
    var wa = String((summary && summary.merchant_kpi_wa_sent_fmt) || "").trim();
    var pctRaw = summary && summary.merchant_kpi_recovered_pct_vs_abandoned;
    var pct =
      pctRaw === 0 || pctRaw === "0"
        ? "0"
        : pctRaw != null && String(pctRaw).trim() !== ""
          ? String(pctRaw).trim()
          : "";

    function row(label, value, detail) {
      var v = String(value || "").trim();
      return (
        '<article class="ma-dh-card ma-dh-perf-row">' +
        '<p class="ma-dh-perf-row__label">' +
        esc(label) +
        "</p>" +
        '<p class="ma-dh-perf-row__value">' +
        esc(v || EMPTY_VALUE) +
        "</p>" +
        '<p class="ma-dh-perf-row__detail">' +
        esc(detail) +
        "</p></article>"
      );
    }

    return (
      '<section class="ma-dh-section" aria-labelledby="ma-dh-perf-title">' +
      '<header class="ma-dh-section__head">' +
      '<h2 class="ma-dh-section__title" id="ma-dh-perf-title">ملخص الأداء</h2>' +
      '<p class="ma-dh-section__purpose">تشغيل اليوم فقط — بدون تكرار مؤشرات الشبكة.</p>' +
      "</header>" +
      '<div class="ma-dh-perf-list">' +
      row(
        "سلال اليوم",
        abandoned || EMPTY_VALUE,
        abandoned ? "سلال متروكة رُصدت اليوم" : "لا سلال متروكة اليوم بعد"
      ) +
      row(
        "رسائل واتساب",
        wa || EMPTY_VALUE,
        wa ? "سجلات إرسال اليوم" : "لا رسائل مُرسلة اليوم بعد"
      ) +
      row(
        "معدل التحويل",
        pct !== "" ? pct + "٪" : EMPTY_VALUE,
        pct !== ""
          ? "مسترد مقابل متروك · اليوم"
          : "لا بيانات كافية لحساب النسبة"
      ) +
      "</div></section>"
    );
  }

  function renderTimeline(home) {
    // No governed Home activity feed yet — honest empty state (never invent events).
    var whileAway = (((home && home.while_away) || {}).items) || [];
    var head =
      '<header class="ma-dh-section__head">' +
      '<h2 class="ma-dh-section__title" id="ma-dh-timeline-title">آخر النشاطات</h2>' +
      '<p class="ma-dh-section__purpose">شراء · عودة · رسالة · رد · حدث مهم.</p>' +
      "</header>";

    if (!whileAway.length) {
      return (
        '<section class="ma-dh-section" aria-labelledby="ma-dh-timeline-title">' +
        head +
        '<div class="ma-dh-card ma-dh-card--empty ma-dh-empty">' +
        '<p class="ma-dh-empty__title">لا نشاطات لعرضها بعد</p>' +
        '<p class="ma-dh-body">ستظهر هنا أحداث المتجر الحقيقية عند توفرها.</p>' +
        "</div></section>"
      );
    }

    // Surface governed while-away achievements as timeline rows (real headlines only).
    var list = '<ul class="ma-dh-timeline">';
    whileAway.slice(0, 5).forEach(function (item) {
      var headline = String((item && item.headline_ar) || "").trim();
      if (!headline) return;
      var detail = String((item && item.detail_ar) || "").trim();
      list +=
        '<li class="ma-dh-timeline__item">' +
        '<div class="ma-dh-timeline__main">' +
        '<p class="ma-dh-headline" style="margin:0;font-size:var(--pds-type-body,14px);">' +
        esc(headline) +
        "</p>" +
        (detail ? '<p class="ma-dh-meta" style="margin:0;">' + esc(detail) + "</p>" : "") +
        "</div>" +
        '<span class="ma-dh-badge">إنجاز</span>' +
        "</li>";
    });
    list += "</ul>";

    return (
      '<section class="ma-dh-section" aria-labelledby="ma-dh-timeline-title">' +
      head +
      '<div class="ma-dh-card">' +
      list +
      "</div></section>"
    );
  }

  function renderHome(summary) {
    var home = (summary && summary.merchant_home_experience_v1) || {};
    if (!home || home.ok === false) {
      // Activation may omit ok; treat missing version as soft-empty still renderable.
      if (!home.greeting && !home.while_away && !home.attention_today) {
        home = {};
      }
    }

    return (
      renderHero(home, summary) +
      renderMetricGrid(summary, home) +
      renderAttention(home) +
      renderKnowledge(home) +
      renderPerformance(summary) +
      renderTimeline(home)
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
    root.classList.add("ma-dash-home-v1", "ma-pe-v2-home");

    if (!summary || summary.ok === false) {
      root.innerHTML = renderError(
        "تعذّر جلب ملخص المتجر. تحقّق من الاتصال ثم حدّث الصفحة."
      );
      return true;
    }

    try {
      root.innerHTML = renderHome(summary);
      if (summary.merchant_home_experience_v1 && summary.merchant_home_experience_v1.empty_calm) {
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
    root.classList.add("ma-dash-home-v1", "ma-home-experience--loading");
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
