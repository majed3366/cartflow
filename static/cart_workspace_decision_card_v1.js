/**
 * Cart Workspace Decision Card — Decision Storytelling face (DIF V1).
 * Face: Priority → Observation → Decision → Action (READY only).
 */
(function (global) {
  "use strict";

  var INSUFFICIENT_EVIDENCE_AR = "لا توجد أدلة كافية لإصدار قرار.";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function explanationOf(card) {
    var ex = card && card.explanation;
    if (!ex || typeof ex !== "object") {
      return { why_here: "", cartflow_did: "", why_stopped: "", expected_after: "" };
    }
    return ex;
  }

  function isConstitutionCard(card) {
    if (!card) return false;
    if (
      card.constitution_v1 ||
      card.gate_2b_composition ||
      card.gate_commerce_situations
    ) {
      return true;
    }
    var kind = String(card.card_kind || "");
    return (
      kind === "business_finding" ||
      kind === "operational_truth" ||
      kind === "composed_decision" ||
      kind === "commerce_situation"
    );
  }

  function presentCard(card) {
    var action = String((card && card.required_action) || "");
    var klass = String((card && card.decision_class) || "");
    var isVip =
      klass === "override" ||
      String((card && card.override_mode) || "") === "active";

    if (isConstitutionCard(card)) {
      var hasDec = card.has_decision !== false;
      return {
        icon: hasDec ? "◎" : "○",
        title: String(
          card.decision_ar || card.title_ar || (hasDec ? "قرار" : "لا قرار بعد")
        ),
        isVip: false,
        isBusiness: true,
        hasDecision: hasDec,
        isConstitution: true,
      };
    }

    if (isVip || action === "override_decision_action") {
      return {
        icon: "🔴",
        title: "VIP — ابدأ المتابعة اليدوية",
        sentence: "عميل عالي القيمة يحتاج قرارك",
        actionLabel: "بدء المتابعة اليدوية",
        isVip: true,
        isConstitution: false,
      };
    }
    if (action === "take_over_conversation") {
      return {
        icon: "💬",
        title: "تابع المحادثة",
        sentence: "العميل يحتاج متابعة",
        actionLabel: "متابعة المحادثة",
        isVip: false,
      };
    }
    if (action === "approve_discount" || action === "approve_or_deny_discount") {
      return {
        icon: "💰",
        title: "راجع طلب الخصم",
        sentence: "العميل ينتظر عرضاً",
        actionLabel: "عرض خصم",
        isVip: false,
      };
    }
    if (action === "fix_channel_configuration") {
      return {
        icon: "⚙",
        title: "أكمل إعداد واتساب",
        sentence: "القناة غير جاهزة",
        actionLabel: "إكمال الإعداد",
        isVip: false,
      };
    }
    if (action === "provide_information" || action === "provide_confirm_phone") {
      return {
        icon: "📱",
        title: "أكد بيانات العميل",
        sentence: "بيانات ناقصة تمنع المتابعة",
        actionLabel:
          action === "provide_confirm_phone" ? "تأكيد الرقم" : "إكمال البيانات",
        isVip: false,
      };
    }
    if (action === "return_to_cartflow" || action === "approve_next_step") {
      return {
        icon: "⭐",
        title: "تتابعه أنت الآن",
        sentence: "متابعة يدوية نشطة",
        actionLabel: "فتح المحادثة",
        isVip: false,
      };
    }
    if (action === "dismiss_with_reason") {
      return {
        icon: "✓",
        title: "أغلق الحالة إن انتهت الحاجة",
        sentence: "يحتاج قرار إغلاق",
        actionLabel: "إغلاق الحالة",
        isVip: false,
      };
    }
    return {
      icon: "●",
      title: String((card && card.title_ar) || "يحتاج قرارك"),
      sentence: String((card && (card.why_ar || explanationOf(card).why_here)) || "قرار مطلوب"),
      actionLabel: String((card && card.action_label_ar) || "تنفيذ القرار"),
      isVip: false,
    };
  }

  function fieldRow(label, value, extraClass) {
    if (!value) return "";
    return (
      '<div class="cw-card__field"><span class="cw-card__field-label">' +
      esc(label) +
      "</span>" +
      '<p class="cw-card__field-value' +
      (extraClass ? " " + extraClass : "") +
      '">' +
      esc(value) +
      "</p></div>"
    );
  }

  function constitutionFaceHtml(card) {
    var isPrimary = !!card.is_primary_decision;
    var rankLabel = String(card.priority_rank_label_ar || "").trim();
    if (!rankLabel) {
      rankLabel = isPrimary ? "الأولوية الأولى" : "بعدها";
    }

    var observation = String(
      card.observation_ar ||
        card.diagnosis_ar ||
        card.business_meaning_ar ||
        ""
    ).trim();
    var decision = String(
      card.decision_sentence_ar ||
        card.operational_guidance_ar ||
        card.commitment_ar ||
        ""
    ).trim();
    var priority = String(card.priority_reason_ar || "").trim();
    var actionReady =
      card.execution_available === true ||
      String(card.execution_readiness || "") === "READY";
    var href2 = String(card.view_details_href || "").trim();
    var detailsLabel = String(card.view_details_ar || "").trim();
    var execDomain = String(card.execution_domain || "").trim();

    // Never paint engine crumbs
    if (/^cs:/i.test(observation) || /diagnostic:/i.test(observation)) {
      observation = observation
        .replace(/\bcs:[A-Za-z0-9_\-:.]+/gi, "")
        .replace(/\bdiagnostic:[A-Za-z0-9_\-:.]+/gi, "")
        .replace(/\s{2,}/g, " ")
        .trim();
    }

    var rows = [];
    rows.push(
      '<p class="cw-card__rank' +
        (isPrimary ? " cw-card__rank--primary" : " cw-card__rank--next") +
        '" data-exec-domain="' +
        esc(execDomain) +
        '" data-storytelling-face="1">' +
        esc(rankLabel) +
        "</p>"
    );

    // 1. Priority (Primary) — no report headings
    if (isPrimary && priority) {
      rows.push(
        '<p class="cw-card__priority" data-story-beat="priority">' +
          esc(priority) +
          "</p>"
      );
    }

    // 2. Observation — plain story line (never label "ملاحظة")
    if (observation) {
      rows.push(
        '<p class="cw-card__field-value cw-card__field-value--decision cw-card__story-observation" data-story-beat="observation">' +
          esc(observation) +
          "</p>"
      );
    }

    // 3. Decision — one sentence (never "المعنى التشغيلي" / "التوجيه")
    if (decision) {
      rows.push(
        '<p class="cw-card__field-value cw-card__field-value--commitment cw-card__story-decision" data-story-beat="decision">' +
          esc(decision) +
          "</p>"
      );
    }

    // 4. Action — READY only; otherwise nothing
    var dest = "";
    if (actionReady && href2) {
      dest =
        '<p class="cw-card__dest" data-story-beat="action"><a class="cw-card__dest-link cw-card__commit-link" href="' +
        esc(href2) +
        '">' +
        esc(detailsLabel || "ابدأ") +
        "</a></p>";
    }

    return rows.join("") + dest;
  }

  function detailsHtml(card, id, extraRows) {
    var ex = explanationOf(card);
    var rows = [];
    if (isConstitutionCard(card)) {
      if (card.expected_business_impact || ex.expected_after) {
        rows.push(
          "<dt>الأثر المتوقع</dt><dd>" +
            esc(card.expected_business_impact || ex.expected_after) +
            "</dd>"
        );
      }
      if (card.missing_evidence) {
        rows.push(
          "<dt>ما ينقص</dt><dd>" + esc(card.missing_evidence) + "</dd>"
        );
      }
      if (Array.isArray(extraRows) && extraRows.length) {
        rows = rows.concat(extraRows);
      }
      if (!rows.length) return "";
      return (
        '<details class="cw-card__details">' +
        "<summary>مزيد</summary>" +
        '<dl class="cw-card__detail-list">' +
        rows.join("") +
        "</dl></details>"
      );
    }
    if (ex.why_here) {
      rows.push("<dt>لماذا؟</dt><dd>" + esc(ex.why_here) + "</dd>");
    }
    if (ex.cartflow_did) {
      rows.push("<dt>ماذا فعل CartFlow؟</dt><dd>" + esc(ex.cartflow_did) + "</dd>");
    }
    if (ex.why_stopped) {
      rows.push("<dt>لماذا توقفت؟</dt><dd>" + esc(ex.why_stopped) + "</dd>");
    }
    if (ex.expected_after) {
      rows.push("<dt>ماذا بعد قرارك؟</dt><dd>" + esc(ex.expected_after) + "</dd>");
    }
    if (
      String((card && card.required_action) || "") === "approve_discount" ||
      String((card && card.required_action) || "") === "approve_or_deny_discount"
    ) {
      rows.push(
        '<dt></dt><dd><button type="button" class="cw-card__ghost" data-cw-command="reject_exception" data-decision-id="' +
          id +
          '">رفض العرض</button></dd>'
      );
    }
    if (Array.isArray(extraRows) && extraRows.length) {
      rows = rows.concat(extraRows);
    }
    if (!rows.length) return "";
    return (
      '<details class="cw-card__details">' +
      "<summary>عرض التفاصيل</summary>" +
      '<dl class="cw-card__detail-list">' +
      rows.join("") +
      "</dl></details>"
    );
  }

  function renderDecisionCardHtml(card, opts) {
    if (!card || typeof card !== "object") return "";
    opts = opts || {};
    var mode = opts.mode || "decision";

    if (mode === "quiet") {
      return (
        '<article class="cw-card cw-card--quiet" data-cw-quiet="1" data-band="no_decision_supported" data-storytelling-face="1">' +
        '<p class="cw-card__band cw-card__band--none">راقب</p>' +
        '<div class="cw-card__head">' +
        '<h3 class="cw-card__title">لا يوجد قرار يحتاج انتباهك الآن.</h3></div>' +
        "</article>"
      );
    }

    /* Gate 2A — status chrome removed from Workspace; keep renderer no-op. */
    if (mode === "status") {
      return "";
    }

    var id = esc(card.decision_id || "");
    var action = esc(card.required_action || "");
    var p = presentCard(card);
    var extraDetails = [];
    if (mode === "following") {
      p = {
        icon: "⭐",
        title: "تتابعه أنت الآن",
        sentence: "متابعة يدوية نشطة",
        actionLabel: "فتح المحادثة",
        isVip: !!p.isVip,
        isConstitution: false,
      };
      extraDetails.push(
        '<dt></dt><dd><button type="button" class="cw-card__ghost" data-cw-command="return_to_cartflow" data-decision-id="' +
          id +
          '" data-cw-following="1">إعادة المتابعة لـ CartFlow</button></dd>'
      );
    }

    var mods = ["cw-card"];
    if (p.isVip && mode !== "following") mods.push("cw-card--vip");
    if (mode === "following") mods.push("cw-card--following");
    if (p.isBusiness || p.isConstitution) mods.push("cw-card--business");
    if (p.isConstitution || isConstitutionCard(card)) mods.push("cw-card--constitution");

    if (p.isConstitution || isConstitutionCard(card)) {
      var sitAttr = String(card.situation_id || "").trim();
      var primaryAttr = card.is_primary_decision ? ' data-primary-decision="1"' : "";
      if (card.is_primary_decision) mods.push("cw-card--primary");
      else mods.push("cw-card--next");
      // V2: full constitutional face only — no duplicate "مزيد" report drawer.
      return (
        '<article class="' +
        mods.join(" ") +
        '" data-decision-id="' +
        id +
        '" data-decision-class="' +
        esc(card.decision_class || "") +
        '" data-card-kind="' +
        esc(card.card_kind || "ops") +
        '" data-decision-status="' +
        esc(card.decision_status || "") +
        '" data-constitution="1"' +
        ' data-dw-v2="1"' +
        ' data-storytelling-face="1"' +
        primaryAttr +
        (sitAttr ? ' data-commerce-situation="1"' : "") +
        ">" +
        constitutionFaceHtml(card) +
        "</article>"
      );
    }

    var actionBtn = "";
    if (mode === "following") {
      actionBtn =
        '<button type="button" class="cw-card__action" data-cw-command="take_over_conversation" data-decision-id="' +
        id +
        '" data-cw-following="1">' +
        esc(p.actionLabel) +
        "</button>";
    } else {
      actionBtn =
        '<button type="button" class="cw-card__action" data-cw-command="' +
        action +
        '" data-decision-id="' +
        id +
        '">' +
        esc(p.actionLabel) +
        "</button>";
    }

    var whyLine = String(
      (card && card.why_ar) || explanationOf(card).why_here || p.sentence || ""
    );

    return (
      '<article class="' +
      mods.join(" ") +
      '" data-decision-id="' +
      id +
      '" data-decision-class="' +
      esc(card.decision_class || "") +
      '" data-required-action="' +
      action +
      '" data-card-kind="' +
      esc(card.card_kind || "ops") +
      '">' +
      '<div class="cw-card__head">' +
      '<span class="cw-card__icon" aria-hidden="true">' +
      esc(p.icon) +
      "</span>" +
      '<h3 class="cw-card__title">' +
      esc(p.title) +
      "</h3></div>" +
      (whyLine
        ? '<p class="cw-card__line">' + esc(whyLine) + "</p>"
        : "") +
      '<div class="cw-card__foot">' +
      actionBtn +
      detailsHtml(card, id, extraDetails) +
      "</div></article>"
    );
  }

  global.CartWorkspaceDecisionCardV1 = {
    renderDecisionCardHtml: renderDecisionCardHtml,
    presentCard: presentCard,
  };
})(typeof window !== "undefined" ? window : globalThis);
