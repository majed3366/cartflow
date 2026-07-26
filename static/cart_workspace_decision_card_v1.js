/**
 * Cart Workspace Decision Card — Gate 2A Constitution.
 * Decision · Why · Evidence · Confidence · Action · View Details.
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
    var ex = explanationOf(card);
    var situationId = String(card.situation_id || "").trim();
    var isPrimary = !!card.is_primary_decision;
    var primaryLabel = String(card.priority_rank_label_ar || "").trim();
    if (isPrimary) primaryLabel = primaryLabel || "القرار الأهم";
    else if (!primaryLabel && (card.gate_commerce_situations || situationId)) {
      primaryLabel = "قرار ثانوي";
    }

    var decision = String(
      card.decision_ar ||
        card.title_ar ||
        card.merchant_decision ||
        "قرار يحتاج مراجعتك"
    );
    var why = String(card.why_ar || ex.why_here || "");
    var whyNow = String(card.why_now_ar || "");
    var subject = String(
      card.subject_ar ||
        card.affected_area_ar ||
        card.product_name_ar ||
        card.affected_area ||
        ""
    ).trim();
    var evidence = String(card.evidence_summary || "");
    if (
      !evidence &&
      Array.isArray(card.supporting_facts_ar) &&
      card.supporting_facts_ar.length
    ) {
      evidence = card.supporting_facts_ar.join(" · ");
    }
    if (!evidence && card.has_decision === false) {
      evidence = INSUFFICIENT_EVIDENCE_AR;
    }
    var action = String(
      card.required_merchant_action ||
        card.action_label_ar ||
        card.recommended_action ||
        "لا إجراء مطلوب حالياً"
    );
    var firstStep = String(card.first_step_ar || action || "");
    var outcome = String(
      card.expected_outcome_ar ||
        card.expected_business_impact ||
        card.business_impact_ar ||
        ex.expected_after ||
        ""
    );
    var href2 = String(card.view_details_href || "").trim();
    if (!href2 && card.gate_commerce_situations) {
      href2 = "#products";
    }
    var detailsLabel = String(card.view_details_ar || "عرض التفاصيل التشغيلية");

    var rows = [];
    if (primaryLabel) {
      rows.push(
        '<p class="cw-card__rank' +
          (isPrimary ? " cw-card__rank--primary" : "") +
          '">' +
          esc(primaryLabel) +
          "</p>"
      );
    }
    // Executive Control order: decision → why priority → subject → evidence → action → impact
    rows.push(
      fieldRow(
        isPrimary ? "القرار الأهم" : "القرار",
        decision,
        "cw-card__field-value--decision"
      )
    );
    rows.push(
      fieldRow(
        "لماذا هو الأولوية؟",
        whyNow || why || "هذا القرار يقود انتباه المتجر اليوم."
      )
    );
    if (subject) {
      rows.push(fieldRow("المنتج / المجال المتأثر", subject));
    }
    rows.push(fieldRow("الأدلة", evidence || INSUFFICIENT_EVIDENCE_AR));
    rows.push(fieldRow("الإجراء الأول", firstStep || action));
    rows.push(fieldRow("الأثر المتوقع", outcome));

    var dest = "";
    if (href2) {
      dest =
        '<p class="cw-card__dest"><a class="cw-card__dest-link" href="' +
        esc(href2) +
        '">' +
        esc(detailsLabel) +
        "</a>" +
        ' · <a class="cw-card__dest-link" href="#carts">السلال</a>' +
        ' · <a class="cw-card__dest-link" href="#communication">التواصل</a></p>';
    } else {
      dest =
        '<p class="cw-card__dest">' +
        '<a class="cw-card__dest-link" href="#products">المنتجات</a> · ' +
        '<a class="cw-card__dest-link" href="#carts">السلال</a> · ' +
        '<a class="cw-card__dest-link" href="#communication">التواصل</a></p>';
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
        '<article class="cw-card cw-card--quiet" data-cw-quiet="1" data-band="no_decision_supported">' +
        '<p class="cw-card__band cw-card__band--none">لا قرار مدعوم حالياً</p>' +
        '<div class="cw-card__head">' +
        '<h3 class="cw-card__title">لا توجد أدلة كافية لإصدار قرار.</h3></div>' +
        '<p class="cw-card__line">لا يوجد قرار يحتاج مراجعتك الآن.</p>' +
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
        primaryAttr +
        (sitAttr ? ' data-commerce-situation="1"' : "") +
        ">" +
        constitutionFaceHtml(card) +
        detailsHtml(card, id, extraDetails) +
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
