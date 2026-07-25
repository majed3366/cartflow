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
    if (card.gate_commerce_situations || situationId) {
      var sitTitle = String(
        card.decision_ar || card.title_ar || card.merchant_decision || "موقف تجاري"
      );
      var sitWhy = String(card.why_ar || ex.why_here || "");
      var sitQ = String(card.why_now_ar || "");
      var sitEvidence = String(card.evidence_summary || "");
      if (
        !sitEvidence &&
        Array.isArray(card.supporting_facts_ar) &&
        card.supporting_facts_ar.length
      ) {
        sitEvidence = card.supporting_facts_ar.join(" · ");
      }
      var sitAction = String(
        card.required_merchant_action ||
          card.action_label_ar ||
          card.recommended_action ||
          ""
      );
      var sitImpact = String(
        card.expected_outcome_ar ||
          card.expected_business_impact ||
          card.business_impact_ar ||
          ""
      );
      var sitConf = String(card.decision_confidence_ar || "").trim();
      var href = String(card.view_details_href || "").trim();
      if (!href && situationId) {
        href = "#products?situation_id=" + encodeURIComponent(situationId);
      }
      var rowsSit = [];
      rowsSit.push(
        '<p class="cw-card__band">موقف تجاري</p>'
      );
      rowsSit.push(
        '<p class="cw-card__situation-id" data-situation-id="' +
          esc(situationId) +
          '"><code>' +
          esc(situationId) +
          "</code></p>"
      );
      rowsSit.push(
        fieldRow("الموقف", sitTitle, "cw-card__field-value--decision")
      );
      rowsSit.push(fieldRow("لماذا يهم؟", sitWhy));
      rowsSit.push(fieldRow("سؤال العمل", sitQ));
      rowsSit.push(fieldRow("الأدلة", sitEvidence || INSUFFICIENT_EVIDENCE_AR));
      rowsSit.push(fieldRow("إجراء التاجر", sitAction));
      rowsSit.push(fieldRow("الأثر المتوقع", sitImpact));
      rowsSit.push(fieldRow("الثقة", sitConf));
      if (href) {
        rowsSit.push(
          '<p class="cw-card__dest"><a class="cw-card__dest-link" href="' +
            esc(href) +
            '">المنتجات المشاركة ←</a> · ' +
            '<a class="cw-card__dest-link" href="#carts?situation_id=' +
            encodeURIComponent(situationId) +
            '">السلال</a> · ' +
            '<a class="cw-card__dest-link" href="#communication?situation_id=' +
            encodeURIComponent(situationId) +
            '">التواصل</a></p>'
        );
      }
      return rowsSit.join("");
    }

    var decision = String(
      card.decision_ar || card.title_ar || "قرار يحتاج مراجعتك"
    );
    var why = String(card.why_ar || ex.why_here || "");
    var whyNow = String(card.why_now_ar || "");
    var evidence = String(card.evidence_summary || "");
    if (!evidence && card.has_decision === false) {
      evidence = INSUFFICIENT_EVIDENCE_AR;
    }
    var ignore = String(card.ignore_consequence_ar || "");
    var conf = String(card.decision_confidence_ar || "").trim();
    var confRaw = String(card.decision_confidence || "").trim().toLowerCase();
    if (!conf && confRaw && confRaw !== "none" && confRaw !== "unknown") {
      if (confRaw === "high") conf = "مرتفع";
      else if (confRaw === "medium") conf = "متوسط";
      else if (confRaw === "low") conf = "منخفض";
    }
    var action = String(
      card.required_merchant_action ||
        card.action_label_ar ||
        "لا إجراء مطلوب حالياً"
    );
    var firstStep = String(card.first_step_ar || "");
    var outcome = String(
      card.expected_outcome_ar || card.expected_business_impact || ex.expected_after || ""
    );
    var href2 = String(card.view_details_href || "").trim();
    var detailsLabel = String(card.view_details_ar || "عرض التفاصيل");
    var band = String(card.priority_band || "");
    var bandLabel = "";
    if (band === "needs_action_now") bandLabel = "يحتاج إجراء الآن";
    else if (band === "monitor") bandLabel = "راقب";
    var rank = parseInt(card.portfolio_rank || 0, 10);
    var cat = String(card.decision_category_ar || "").trim();

    var rows = [];
    if (rank > 0) {
      rows.push(
        '<p class="cw-card__rank">الأولوية ' + esc(String(rank)) + "</p>"
      );
    }
    if (cat) {
      rows.push('<p class="cw-card__category">' + esc(cat) + "</p>");
    }
    if (bandLabel) {
      rows.push(
        '<p class="cw-card__band cw-card__band--' +
          esc(band) +
          '">' +
          esc(bandLabel) +
          "</p>"
      );
    }
    rows.push(fieldRow("القرار", decision, "cw-card__field-value--decision"));
    rows.push(fieldRow("لماذا؟", why));
    rows.push(fieldRow("لماذا الآن؟", whyNow));
    rows.push(fieldRow("الأدلة", evidence || INSUFFICIENT_EVIDENCE_AR));
    rows.push(fieldRow("ماذا يحدث إذا تجاهلته؟", ignore));
    rows.push(fieldRow("الإجراء الموصى به", action));
    rows.push(fieldRow("ابدأ بهذه الخطوة", firstStep));
    rows.push(fieldRow("الأثر المتوقع", outcome));
    rows.push(fieldRow("الثقة", conf));

    var dest = "";
    if (href2) {
      dest =
        '<p class="cw-card__dest"><a class="cw-card__dest-link" href="' +
        esc(href2) +
        '">' +
        esc(detailsLabel) +
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
        (sitAttr
          ? ' data-situation-id="' + esc(sitAttr) + '" data-commerce-situation="1"'
          : "") +
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
