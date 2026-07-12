/**
 * Cart Workspace Decision Card Presenter V1 — paint only (Decision-First).
 * Consumes DecisionRecord-shaped objects from WorkspaceProjection.
 * Must not evaluate admission, ownership, or provider state.
 *
 * Presentation mapping (title / one-liner / action label) is UI-only.
 * Projection payload fields are unchanged.
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
      return {
        why_here: "",
        cartflow_did: "",
        why_stopped: "",
        expected_after: "",
      };
    }
    return ex;
  }

  /**
   * Merchant-facing presentation copy — never expose engineering terms.
   * @returns {{ title: string, sentence: string, actionLabel: string, isVip: boolean }}
   */
  function presentCard(card) {
    var action = String((card && card.required_action) || "");
    var klass = String((card && card.decision_class) || "");
    var isVip =
      klass === "override" ||
      String((card && card.override_mode) || "") === "active";

    if (isVip || action === "take_over_conversation" || action === "override_decision_action") {
      if (isVip) {
        return {
          title: "VIP",
          sentence: "عميل مهم يحتاج متابعتك الآن.",
          actionLabel: "بدء المتابعة اليدوية",
          isVip: true,
        };
      }
      return {
        title: "رد العميل",
        sentence: "العميل رد ويحتاج متابعة.",
        actionLabel: "متابعة المحادثة",
        isVip: false,
      };
    }

    if (
      action === "approve_discount" ||
      action === "approve_or_deny_discount"
    ) {
      return {
        title: "طلب خصم",
        sentence: "العميل ينتظر عرضاً منك.",
        actionLabel: "عرض خصم",
        isVip: false,
      };
    }

    if (action === "fix_channel_configuration") {
      return {
        title: "يحتاج إعداد",
        sentence: "واتساب المتجر يحتاج إكمال الإعداد.",
        actionLabel: "إكمال الإعداد",
        isVip: false,
      };
    }

    if (
      action === "provide_information" ||
      action === "provide_confirm_phone"
    ) {
      return {
        title: "بانتظار رقم العميل",
        sentence: "أكمل البيانات المطلوبة للمتابعة.",
        actionLabel:
          action === "provide_confirm_phone" ? "تأكيد الرقم" : "إكمال البيانات",
        isVip: false,
      };
    }

    if (action === "return_to_cartflow" || action === "approve_next_step") {
      return {
        title: "إعادة للمتابعة",
        sentence: "يمكنك إعادة المتابعة لـ CartFlow.",
        actionLabel: "إعادة المتابعة لـ CartFlow",
        isVip: false,
      };
    }

    if (action === "dismiss_with_reason") {
      return {
        title: "يحتاج قرارك",
        sentence: "أغلق هذه الحالة إن لم تعد تحتاج تدخلاً.",
        actionLabel: "إغلاق الحالة",
        isVip: false,
      };
    }

    return {
      title: "يحتاج قرارك",
      sentence: "يحتاج قراراً منك الآن.",
      actionLabel: "تنفيذ القرار",
      isVip: false,
    };
  }

  function detailsHtml(card, id) {
    var ex = explanationOf(card);
    var rows = [];
    if (ex.why_here) {
      rows.push(
        "<dt>لماذا ظهرت؟</dt><dd>" + esc(ex.why_here) + "</dd>"
      );
    }
    if (ex.cartflow_did) {
      rows.push(
        "<dt>ماذا فعل CartFlow؟</dt><dd>" + esc(ex.cartflow_did) + "</dd>"
      );
    }
    if (ex.why_stopped) {
      rows.push(
        "<dt>لماذا توقفت الأتمتة؟</dt><dd>" + esc(ex.why_stopped) + "</dd>"
      );
    }
    if (ex.expected_after) {
      rows.push(
        "<dt>ماذا بعد قرارك؟</dt><dd>" + esc(ex.expected_after) + "</dd>"
      );
    }
    if (
      String((card && card.required_action) || "") === "approve_discount" ||
      String((card && card.required_action) || "") === "approve_or_deny_discount"
    ) {
      rows.push(
        '<dt>خيارات إضافية</dt><dd><button type="button" class="cw-decision-card__secondary" data-cw-command="reject_exception" data-decision-id="' +
          id +
          '">رفض العرض</button></dd>'
      );
    }
    if (!rows.length) return "";
    return (
      '<details class="cw-decision-card__details">' +
      "<summary>عرض التفاصيل</summary>" +
      '<dl class="cw-decision-card__fields">' +
      rows.join("") +
      "</dl>" +
      "</details>"
    );
  }

  /**
   * @param {object} card Decision card from projection zone_a|zone_b
   * @param {{ mode?: string }} opts mode: "decision" | "following"
   * @returns {string} HTML
   */
  function renderDecisionCardHtml(card, opts) {
    if (!card || typeof card !== "object") return "";
    opts = opts || {};
    var mode = opts.mode || "decision";
    var id = esc(card.decision_id || "");
    var action = esc(card.required_action || "");
    var p = presentCard(card);
    var vipClass = p.isVip ? " cw-decision-card--vip" : "";
    var followClass = mode === "following" ? " cw-decision-card--following" : "";

    var actions = "";
    if (mode === "following") {
      actions =
        '<div class="cw-decision-card__actions">' +
        '<button type="button" class="cw-decision-card__primary" data-cw-command="return_to_cartflow" data-decision-id="' +
        id +
        '" data-cw-following="1">إعادة المتابعة لـ CartFlow</button>' +
        "</div>";
    } else {
      actions =
        '<div class="cw-decision-card__actions">' +
        '<button type="button" class="cw-decision-card__primary" data-cw-command="' +
        action +
        '" data-decision-id="' +
        id +
        '">' +
        esc(p.actionLabel) +
        "</button>" +
        "</div>";
    }

    return (
      '<article class="cw-decision-card' +
      vipClass +
      followClass +
      '" data-decision-id="' +
      id +
      '" data-decision-class="' +
      esc(card.decision_class || "") +
      '" data-required-action="' +
      action +
      '" data-cw-card-mode="' +
      esc(mode) +
      '">' +
      '<h3 class="cw-decision-card__title">' +
      esc(p.title) +
      "</h3>" +
      '<p class="cw-decision-card__sentence">' +
      esc(p.sentence) +
      "</p>" +
      actions +
      (mode === "following" ? "" : detailsHtml(card, id)) +
      "</article>"
    );
  }

  global.CartWorkspaceDecisionCardV1 = {
    renderDecisionCardHtml: renderDecisionCardHtml,
    presentCard: presentCard,
  };
})(typeof window !== "undefined" ? window : globalThis);
