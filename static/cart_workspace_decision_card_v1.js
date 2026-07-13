/**
 * Cart Workspace Decision Card — Wireframe Contract V1.
 * Independent action tiles. No section chrome. Details gated.
 */
(function (global) {
  "use strict";

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

  function presentCard(card) {
    var action = String((card && card.required_action) || "");
    var klass = String((card && card.decision_class) || "");
    var isVip =
      klass === "override" ||
      String((card && card.override_mode) || "") === "active";

    if (isVip || action === "override_decision_action") {
      return {
        icon: "🔴",
        title: "VIP",
        sentence: "عميل عالي القيمة",
        actionLabel: "بدء المتابعة اليدوية",
        isVip: true,
      };
    }
    if (action === "take_over_conversation") {
      return {
        icon: "💬",
        title: "رد العميل",
        sentence: "يحتاج متابعة",
        actionLabel: "متابعة المحادثة",
        isVip: false,
      };
    }
    if (action === "approve_discount" || action === "approve_or_deny_discount") {
      return {
        icon: "💰",
        title: "طلب خصم",
        sentence: "العميل ينتظر عرضاً",
        actionLabel: "عرض خصم",
        isVip: false,
      };
    }
    if (action === "fix_channel_configuration") {
      return {
        icon: "⚙",
        title: "يحتاج إعداد",
        sentence: "أكمل إعداد واتساب",
        actionLabel: "إكمال الإعداد",
        isVip: false,
      };
    }
    if (action === "provide_information" || action === "provide_confirm_phone") {
      return {
        icon: "📱",
        title: "بانتظار رقم العميل",
        sentence: "بيانات ناقصة",
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
        title: "يحتاج قرارك",
        sentence: "أغلق إن انتهت الحاجة",
        actionLabel: "إغلاق الحالة",
        isVip: false,
      };
    }
    return {
      icon: "●",
      title: "يحتاج قرارك",
      sentence: "قرار مطلوب",
      actionLabel: "تنفيذ القرار",
      isVip: false,
    };
  }

  function detailsHtml(card, id, extraRows) {
    var ex = explanationOf(card);
    var rows = [];
    if (ex.why_here) {
      rows.push("<dt>لماذا ظهرت؟</dt><dd>" + esc(ex.why_here) + "</dd>");
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

  /**
   * @param {object} card
   * @param {{ mode?: string }} opts decision | following | status | quiet
   */
  function renderDecisionCardHtml(card, opts) {
    if (!card || typeof card !== "object") return "";
    opts = opts || {};
    var mode = opts.mode || "decision";

    if (mode === "quiet") {
      return (
        '<article class="cw-card cw-card--quiet" data-cw-quiet="1">' +
        '<div class="cw-card__head">' +
        '<span class="cw-card__icon" aria-hidden="true">✅</span>' +
        '<h3 class="cw-card__title">لا يوجد ما يحتاج قرارك الآن</h3></div>' +
        '<p class="cw-card__line">CartFlow يتابع متجرك تلقائياً</p>' +
        "</article>"
      );
    }

    if (mode === "status") {
      var statusFoot = "";
      if (card.actionLabel) {
        if (card.actionAsDetails) {
          statusFoot =
            '<div class="cw-card__foot">' +
            '<details class="cw-card__details">' +
            "<summary>" +
            esc(card.actionLabel) +
            "</summary>" +
            (card.detailsBody
              ? '<div class="cw-card__detail-list"><p>' +
                esc(card.detailsBody) +
                "</p></div>"
              : "") +
            "</details></div>";
        } else {
          statusFoot =
            '<div class="cw-card__foot">' +
            '<button type="button" class="cw-card__action" data-cw-command="' +
            esc(card.actionCommand || "") +
            '">' +
            esc(card.actionLabel) +
            "</button></div>";
        }
      }
      return (
        '<article class="cw-card cw-card--status' +
        (card.kind ? " cw-card--" + esc(card.kind) : "") +
        '">' +
        '<div class="cw-card__head">' +
        '<span class="cw-card__icon" aria-hidden="true">' +
        esc(card.icon || "") +
        "</span>" +
        '<h3 class="cw-card__title">' +
        esc(card.title || "") +
        "</h3></div>" +
        '<p class="cw-card__line">' +
        esc(card.sentence || "") +
        "</p>" +
        (card.subline
          ? '<p class="cw-card__sub">' + esc(card.subline) + "</p>"
          : "") +
        statusFoot +
        "</article>"
      );
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

    var actionBtn;
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

    return (
      '<article class="' +
      mods.join(" ") +
      '" data-decision-id="' +
      id +
      '" data-decision-class="' +
      esc(card.decision_class || "") +
      '" data-required-action="' +
      action +
      '">' +
      '<div class="cw-card__head">' +
      '<span class="cw-card__icon" aria-hidden="true">' +
      esc(p.icon) +
      "</span>" +
      '<h3 class="cw-card__title">' +
      esc(p.title) +
      "</h3></div>" +
      '<p class="cw-card__line">' +
      esc(p.sentence) +
      "</p>" +
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
