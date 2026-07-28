/**
 * Cart Workspace Decision Card — Decision Workspace V2 / Decision Cards Constitution V1.
 * Diagnosis → Reasoning → Evidence → Consequence → Commitment → Expected Outcome.
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
    var compact = !isPrimary || card.face_mode === "next_compact";
    var primaryLabel = String(card.priority_rank_label_ar || "").trim();
    if (isPrimary) {
      primaryLabel = primaryLabel || "القرار الذي تلتزم به الآن";
    } else {
      primaryLabel = primaryLabel || "بعده مباشرة";
    }

    var diagnosis = String(
      card.diagnosis_ar ||
        card.business_meaning_ar ||
        card.decision_ar ||
        card.title_ar ||
        "هناك موقف تجاري يحتاج قراراً الآن."
    );
    var why = String(
      card.why_believe_ar || card.reasoning_ar || card.why_ar || ""
    );
    if (!why) {
      why = "لأن ملاحظات المتجر الحالية تدعم هذا التشخيص.";
    }
    var confidence = String(
      card.confidence_ar || "لذلك يمكن البناء على التشخيص بحذر مناسب."
    );
    var readiness = String(
      card.execution_readiness_ar ||
        "جاهزية التنفيذ تُحدد قبل أي توجيه للتنفيذ."
    );
    var consequence = String(
      card.business_consequence_ar ||
        card.ignore_consequence_ar ||
        "إذا بقي الأمر معلّقاً، يستمر ضغط الإيراد دون قرار واضح."
    );
    var cartflowRole = String(
      card.cartflow_responsibility_ar ||
        "CartFlow يتولى الملاحظة والأدلة والتشخيص وجاهزية التنفيذ."
    );
    var whereExec = String(
      card.execution_where_ar || "وجهة التنفيذ تُحدد حسب مجال التنفيذ."
    );
    var howExec = String(
      card.execution_how_ar || "خطوات التنفيذ تتبع مجال التنفيذ وجاهزيته."
    );
    var avoid = String(
      card.execution_avoid_ar ||
        "تجنّب إعادة التشخيص وتنفيذ عدة تغييرات دفعة واحدة."
    );
    var commitment = String(
      card.commitment_ar ||
        "اتخذ قراراً تجارياً واحداً — أو أرجئه بوعي."
    );
    var verify = String(
      card.execution_verify_ar ||
        card.expected_outcome_ar ||
        "بعد التنفيذ يقارن CartFlow قبل/بعد ويحدّث حالة القرار."
    );
    var href2 = String(card.view_details_href || "").trim();
    var detailsLabel = String(card.view_details_ar || "متابعة التنفيذ");
    var execDomain = String(card.execution_domain || "").trim();

    var rows = [];
    rows.push(
      '<p class="cw-card__rank' +
        (isPrimary ? " cw-card__rank--primary" : " cw-card__rank--next") +
        '" data-exec-domain="' +
        esc(execDomain) +
        '">' +
        esc(primaryLabel) +
        "</p>"
    );

    if (compact && !isPrimary) {
      // Compact next — continues the meeting, not a second report.
      rows.push(
        fieldRow("ثم هذا", diagnosis, "cw-card__field-value--decision")
      );
      rows.push(
        fieldRow("التزامك التالي", commitment, "cw-card__field-value--commitment")
      );
    } else {
      // Refinement V2 — one executive conversation (methodology integrated).
      rows.push(
        fieldRow("ما يحدث الآن", diagnosis, "cw-card__field-value--decision")
      );
      rows.push(fieldRow("لماذا هذا التشخيص", why));
      rows.push(fieldRow("ولذلك", confidence));
      rows.push(fieldRow("جاهزية التنفيذ", readiness));
      rows.push(fieldRow("إن لم تحسم الآن", consequence));
      rows.push(fieldRow("ما أنجزه CartFlow", cartflowRole));
      rows.push(fieldRow("أين تنفّذ", whereExec));
      rows.push(fieldRow("كيف تنفّذ", howExec));
      rows.push(fieldRow("ما يجب تجنّبه", avoid));
      rows.push(
        fieldRow("قرارك التجاري", commitment, "cw-card__field-value--commitment")
      );
      rows.push(fieldRow("كيف يتحقق CartFlow", verify));
    }

    var dest = "";
    if (href2) {
      dest =
        '<p class="cw-card__dest"><a class="cw-card__dest-link cw-card__commit-link" href="' +
        esc(href2) +
        '">' +
        esc(detailsLabel) +
        "</a></p>";
    } else if (detailsLabel) {
      // Business / no-nav commitments — no circular empty link.
      dest =
        '<p class="cw-card__dest cw-card__dest--note">' +
        esc(detailsLabel) +
        "</p>";
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
        '<p class="cw-card__band cw-card__band--none">لا التزام مطلوب الآن</p>' +
        '<div class="cw-card__head">' +
        '<h3 class="cw-card__title">لا يوجد قرار تنفيذي جاهز في هذه اللحظة.</h3></div>' +
        '<p class="cw-card__line">CartFlow يواصل الملاحظة — عد عند ظهور التزام واضح.</p>' +
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
