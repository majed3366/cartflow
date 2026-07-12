/**
 * Cart Workspace Decision Card — Visual Rebuild V1 (paint only).
 * Control-center action tile. No report layout.
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
        sentence: "متابعة يدوية",
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
        icon: "↩",
        title: "إعادة للمتابعة",
        sentence: "أعد لـ CartFlow",
        actionLabel: "إعادة المتابعة لـ CartFlow",
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

  function detailsHtml(card, id) {
    var ex = explanationOf(card);
    var rows = [];
    if (ex.why_here) {
      rows.push("<dt>لماذا ظهرت؟</dt><dd>" + esc(ex.why_here) + "</dd>");
    }
    if (ex.cartflow_did) {
      rows.push("<dt>ماذا فعل CartFlow؟</dt><dd>" + esc(ex.cartflow_did) + "</dd>");
    }
    if (ex.why_stopped) {
      rows.push("<dt>لماذا توقفت الأتمتة؟</dt><dd>" + esc(ex.why_stopped) + "</dd>");
    }
    if (ex.expected_after) {
      rows.push("<dt>ماذا بعد قرارك؟</dt><dd>" + esc(ex.expected_after) + "</dd>");
    }
    if (
      String((card && card.required_action) || "") === "approve_discount" ||
      String((card && card.required_action) || "") === "approve_or_deny_discount"
    ) {
      rows.push(
        '<dt></dt><dd><button type="button" class="cw-tile__ghost" data-cw-command="reject_exception" data-decision-id="' +
          id +
          '">رفض العرض</button></dd>'
      );
    }
    if (!rows.length) return "";
    return (
      '<details class="cw-tile__details">' +
      "<summary>عرض التفاصيل</summary>" +
      '<dl class="cw-tile__detail-list">' +
      rows.join("") +
      "</dl></details>"
    );
  }

  function renderDecisionCardHtml(card, opts) {
    if (!card || typeof card !== "object") return "";
    opts = opts || {};
    var mode = opts.mode || "decision";
    var id = esc(card.decision_id || "");
    var action = esc(card.required_action || "");
    var p = presentCard(card);
    var mods = [];
    if (p.isVip) mods.push("cw-tile--vip");
    if (mode === "following") mods.push("cw-tile--following");

    var actions;
    if (mode === "following") {
      actions =
        '<button type="button" class="cw-tile__action" data-cw-command="return_to_cartflow" data-decision-id="' +
        id +
        '" data-cw-following="1">إعادة المتابعة لـ CartFlow</button>';
    } else {
      actions =
        '<button type="button" class="cw-tile__action" data-cw-command="' +
        action +
        '" data-decision-id="' +
        id +
        '">' +
        esc(p.actionLabel) +
        "</button>";
    }

    return (
      '<article class="cw-tile ' +
      mods.join(" ") +
      '" data-decision-id="' +
      id +
      '" data-decision-class="' +
      esc(card.decision_class || "") +
      '" data-required-action="' +
      action +
      '">' +
      '<div class="cw-tile__head">' +
      '<span class="cw-tile__icon" aria-hidden="true">' +
      esc(p.icon) +
      "</span>" +
      '<h3 class="cw-tile__title">' +
      esc(p.title) +
      "</h3>" +
      "</div>" +
      '<p class="cw-tile__line">' +
      esc(p.sentence) +
      "</p>" +
      '<div class="cw-tile__foot">' +
      actions +
      (mode === "following" ? "" : detailsHtml(card, id)) +
      "</div>" +
      "</article>"
    );
  }

  global.CartWorkspaceDecisionCardV1 = {
    renderDecisionCardHtml: renderDecisionCardHtml,
    presentCard: presentCard,
  };
})(typeof window !== "undefined" ? window : globalThis);
