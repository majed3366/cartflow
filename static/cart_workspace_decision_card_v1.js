/**
 * Cart Workspace Decision Card — Simplification V1 + Assimilation V1.1 face.
 * Face: Priority → Evidence → Understanding → Decision → Action (or wait).
 * Presentation only — no command / ownership / projection logic changes.
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

  function scrubEngineText(s) {
    return String(s || "")
      .replace(/\bcs:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bdiagnostic:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bdce:[A-Za-z0-9_\-:.]+/gi, "")
      .replace(/\bDEMO-[A-Za-z0-9_-]+/g, "")
      .replace(/\s{2,}/g, " ")
      .trim();
  }

  function isMostlyLatinLeak(s) {
    var t = String(s || "").replace(/\s+/g, "");
    if (!t) return false;
    var latin = (t.match(/[A-Za-z]/g) || []).length;
    return latin / t.length > 0.42;
  }

  function merchantSafeAr(s, fallback) {
    var t = scrubEngineText(s);
    if (!t || isMostlyLatinLeak(t)) return fallback || "";
    return t;
  }

  function evidenceFallbackAr(card) {
    var action = String((card && card.required_action) || "");
    if (action === "approve_discount" || action === "approve_or_deny_discount") {
      return "العميل يطلب خصماً قبل إتمام الشراء.";
    }
    if (action === "take_over_conversation" || action === "override_decision_action") {
      return "عميل مهم ينتظر متابعة مباشرة منك.";
    }
    if (action === "provide_confirm_phone" || action === "provide_information") {
      return "بيانات التواصل ناقصة وتمنع متابعة الاسترداد.";
    }
    if (action === "fix_channel_configuration") {
      return "قناة واتساب غير جاهزة لإرسال المتابعة.";
    }
    return "ظهرت إشارة تشغيلية تحتاج قرارك الآن.";
  }

  function understandingFromCard(card) {
    var ex = explanationOf(card);
    return (
      merchantSafeAr(card.ignore_consequence_ar) ||
      merchantSafeAr(card.business_consequence_ar) ||
      merchantSafeAr(card.next_stake_ar) ||
      merchantSafeAr(ex.why_stopped) ||
      merchantSafeAr(ex.cartflow_did) ||
      "تركه معلّقاً يبقي ضغط الإيراد دون معالجة واضحة."
    );
  }

  function constitutionFaceHtml(card) {
    var isPrimary = !!card.is_primary_decision;
    var rankLabel = merchantSafeAr(
      card.priority_rank_label_ar,
      isPrimary ? "الأولوية الأولى" : "الأولوية الثانية"
    );

    var evidenceLines = [];
    if (Array.isArray(card.evidence_lines_ar) && card.evidence_lines_ar.length) {
      evidenceLines = card.evidence_lines_ar
        .map(function (line) {
          return merchantSafeAr(line);
        })
        .filter(Boolean);
    }
    if (!evidenceLines.length) {
      var fallback = merchantSafeAr(
        card.evidence_ar || card.observation_ar || card.diagnosis_ar || ""
      );
      if (fallback) evidenceLines = [fallback];
    }
    if (!evidenceLines.length) {
      evidenceLines = [evidenceFallbackAr(card)];
    }

    var understanding = understandingFromCard(card);
    var decision = merchantSafeAr(
      card.decision_sentence_ar ||
        card.operational_guidance_ar ||
        card.commitment_ar ||
        card.required_merchant_action ||
        "",
      "راجع القرار المطلوب الآن"
    );
    var actionReady =
      card.execution_available === true ||
      String(card.execution_readiness || "") === "READY" ||
      String(card.execution_readiness || "") === "EXTERNAL_DEPENDENCY";
    var href2 = String(card.view_details_href || "").trim();
    var detailsLabel = merchantSafeAr(card.view_details_ar || "", "افتح");
    var execDomain = String(card.execution_domain || "").trim();
    var waitLines = Array.isArray(card.action_wait_lines_ar)
      ? card.action_wait_lines_ar
      : ["لا يوجد إجراء حالياً.", "سيخبرك CartFlow عندما يصبح القرار جاهزاً."];

    var rows = [];
    rows.push(
      '<p class="cw-card__rank' +
        (isPrimary ? " cw-card__rank--primary" : " cw-card__rank--next") +
        '" data-exec-domain="' +
        esc(execDomain) +
        '" data-simplification="1" data-story-beat="priority">' +
        esc(rankLabel) +
        "</p>"
    );

    rows.push('<div class="cw-card__stack" data-hierarchy="evidence-understanding-decision-action">');

    rows.push(
      '<section class="cw-beat cw-beat--evidence" data-story-beat="evidence">' +
        '<p class="cw-beat__label">الملاحظة</p>' +
        '<ul class="cw-beat__list cw-card__evidence-list">'
    );
    evidenceLines.forEach(function (line) {
      rows.push("<li>" + esc(line) + "</li>");
    });
    rows.push("</ul></section>");

    rows.push(
      '<section class="cw-beat cw-beat--understanding" data-story-beat="understanding">' +
        '<p class="cw-beat__label">ما يعنيه ذلك</p>' +
        '<p class="cw-beat__body">' +
        esc(understanding) +
        "</p></section>"
    );

    rows.push(
      '<section class="cw-beat cw-beat--decision" data-story-beat="decision">' +
        '<p class="cw-beat__label">القرار الآن</p>' +
        '<p class="cw-beat__decision cw-card__field-value cw-card__field-value--commitment cw-card__story-decision">' +
        esc(decision) +
        "</p></section>"
    );

    var actionInner = "";
    if (actionReady && href2) {
      actionInner =
        '<a class="cw-card__dest-link cw-card__commit-link" href="' +
        esc(href2) +
        '">' +
        esc(detailsLabel || "افتح") +
        "</a>";
    } else if (actionReady && detailsLabel) {
      actionInner =
        '<p class="cw-card__dest cw-card__dest--plain">' + esc(detailsLabel) + "</p>";
    } else if (!actionReady) {
      actionInner =
        '<div class="cw-card__action-wait">' +
        "<p>" +
        esc(merchantSafeAr(waitLines[0], "لا يوجد إجراء حالياً.")) +
        "</p>" +
        "<p>" +
        esc(
          merchantSafeAr(
            waitLines[1],
            "سيخبرك CartFlow عندما يصبح القرار جاهزاً."
          )
        ) +
        "</p></div>";
    }

    if (actionInner) {
      rows.push(
        '<section class="cw-beat cw-beat--action" data-story-beat="action">' +
          '<p class="cw-beat__label">خطوتك</p>' +
          '<div class="cw-beat__action">' +
          actionInner +
          "</div></section>"
      );
    }

    rows.push("</div>");
    return rows.join("");
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
      var quietSig =
        global.CFSignature && global.CFSignature.attrsForCard
          ? global.CFSignature.attrsForCard({ quiet: true })
          : {
              "data-cf-sig": "decision-card",
              "data-cf-role": "quiet",
              "data-cf-density": "1",
              "data-cf-gravity": "quiet",
              "data-cf-momentum": "calm",
              "data-cf-breathing": "open",
            };
      var quietAttrs = Object.keys(quietSig)
        .map(function (k) {
          return k + '="' + esc(quietSig[k]) + '"';
        })
        .join(" ");
      return (
        '<article class="cw-card cw-card--quiet" data-cw-quiet="1" data-band="no_decision_supported" data-storytelling-face="1" ' +
        quietAttrs +
        ">" +
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
      var sigMap =
        global.CFSignature && global.CFSignature.attrsForCard
          ? global.CFSignature.attrsForCard(card)
          : {};
      var sigAttrs = Object.keys(sigMap)
        .map(function (k) {
          return k + '="' + esc(sigMap[k]) + '"';
        })
        .join(" ");
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
        ' data-simplification="1"' +
        primaryAttr +
        (sitAttr ? ' data-commerce-situation="1"' : "") +
        (sigAttrs ? " " + sigAttrs : "") +
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

    var whyLine = merchantSafeAr(
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
