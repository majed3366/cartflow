/**
 * Merchant Intelligence Consumption V1 — Carts Workspace.
 * Read-only projection of merchant_intelligence_store_v1 + row bundles.
 * No local grouping, recommendations, or intelligence derivation.
 */
(function (global) {
  "use strict";

  var GROUP_ORDER = [
    "needs_merchant",
    "waiting_reply",
    "waiting_phone",
    "returned",
    "waiting_purchase",
    "repeated_hesitation",
    "product_hesitation",
    "vip",
    "completed",
    "risk_pattern",
    "no_contact",
  ];

  var REC_TYPE_LABEL_AR = {
    required_action: "إجراء مطلوب",
    suggested_action: "مقترح",
    watch_only: "مراقبة",
    informational: "معلومة",
    no_action: "لا يلزم إجراء",
    blocked: "محظور",
  };

  function merchantCurrencyText(value) {
    var v = Math.round(parseFloat(value) || 0);
    if (!v || isNaN(v)) return "";
    if (typeof global.formatMerchantSar === "function") {
      return global.formatMerchantSar(v);
    }
    return "";
  }

  function queueAmountHtml(value, esc) {
    var text = merchantCurrencyText(value);
    if (!text) {
      return '<div class="v2-queue-amount">—</div>';
    }
    return (
      '<div class="v2-queue-amount cf-currency-atom cftyp-currency" data-cf-currency="1" dir="ltr">' +
      esc(text) +
      "</div>"
    );
  }

  function queueAccentClass(row) {
    var bucket = norm(row && row.merchant_cart_primary_bucket);
    if (bucket === "intervention" || bucket === "attention") return "v2-queue-accent--attention";
    if (bucket === "waiting" || bucket === "abandoned") return "v2-queue-accent--waiting";
    return "v2-queue-accent--calm";
  }

  var REASON_TAG_AR = {
    price: "تردد بسبب السعر",
    shipping: "تردد بسبب الشحن",
    delivery: "تردد بسبب التوصيل",
    quality: "تردد بسبب الجودة",
    size: "تردد بسبب المقاس",
    payment: "تردد بسبب الدفع",
    trust: "تردد بسبب الثقة",
    other: "أسباب أخرى",
  };

  var INTERNAL_TOKEN_AR = {
    waiting_first_send: "بانتظار إرسال الرسالة الأولى",
    waiting_customer_reply: "بانتظار رد العميل",
    waiting_phone: "بانتظار رقم الجوال",
    waiting_purchase: "بانتظار إكمال الشراء",
    returned_to_site: "عاد للموقع",
    needs_merchant: "يحتاج تدخلك",
    completed: "مكتملة",
    archived: "مؤرشفة",
    sent: "تم الإرسال",
    waiting: "قيد المتابعة",
    attention: "تحتاج انتباه",
    no_phone: "بدون رقم جوال",
    recovered: "تم الاسترداد",
    price: "تردد بسبب السعر",
    shipping: "تردد بسبب الشحن",
    other: "أسباب أخرى",
  };

  var GROUP_TITLE_AR = {
    needs_merchant: "يحتاج تدخلك",
    waiting_reply: "بانتظار رد العميل",
    waiting_phone: "بانتظار رقم الجوال",
    returned: "عاد للمتجر",
    waiting_purchase: "بانتظار إكمال الشراء",
    repeated_hesitation: "تردد متكرر",
    product_hesitation: "تردد على منتج",
    vip: "سلة VIP",
    completed: "مكتملة",
    risk_pattern: "نمط يستحق المراقبة",
    no_contact: "لا يمكن التواصل",
  };

  var openGroupState = {};

  function norm(value) {
    return String(value == null ? "" : value).trim();
  }

  function merchantFacingText(text) {
    var s = norm(text);
    if (!s) return "";
    if (typeof window.sanitizeMerchantLanguage === "function") {
      s = window.sanitizeMerchantLanguage(s);
    }
    var lower = s.toLowerCase();
    if (INTERNAL_TOKEN_AR[lower]) return INTERNAL_TOKEN_AR[lower];
    if (REASON_TAG_AR[lower]) return REASON_TAG_AR[lower];
    if (GROUP_TITLE_AR[lower]) return GROUP_TITLE_AR[lower];
    if (lower.indexOf("reason:") === 0) {
      var reasonTag = lower.slice(7);
      return REASON_TAG_AR[reasonTag] || "";
    }
    if (lower.indexOf("product:") === 0) {
      return "تردد على منتج";
    }
    s = s.replace(/reason_tag:([a-z0-9_]+)/gi, function (_m, tag) {
      return REASON_TAG_AR[norm(tag).toLowerCase()] || "";
    });
    s = s.replace(
      /(?:^|[\s—\-·]+)(price|shipping|delivery|quality|size|payment|trust|other)(?:[\s—\-·]|$)/gi,
      function (match, tag) {
        var mapped = REASON_TAG_AR[norm(tag).toLowerCase()];
        return mapped ? match.replace(tag, mapped) : match;
      }
    );
    s = s.replace(/\b([a-z][a-z0-9_]{2,})\b/gi, function (match) {
      var k = match.toLowerCase();
      if (INTERNAL_TOKEN_AR[k]) return INTERNAL_TOKEN_AR[k];
      if (REASON_TAG_AR[k]) return REASON_TAG_AR[k];
      if (GROUP_TITLE_AR[k]) return GROUP_TITLE_AR[k];
      return match;
    });
    return s.replace(/\s{2,}/g, " ").trim();
  }

  function localizedGroupTitle(group) {
    var gid = norm(group.group_id);
    var title = merchantFacingText(group.title_ar || "");
    if (title && !/^[a-z0-9_]+$/i.test(title)) return title;
    return GROUP_TITLE_AR[gid] || title || "مجموعة سلال";
  }

  function groupRank(groupId) {
    var gid = norm(groupId);
    var idx = GROUP_ORDER.indexOf(gid);
    return idx >= 0 ? idx : GROUP_ORDER.length + 1;
  }

  function sortGroups(groups) {
    return (groups || [])
      .slice()
      .sort(function (a, b) {
        var ra = groupRank(a.group_id);
        var rb = groupRank(b.group_id);
        if (ra !== rb) return ra - rb;
        return parseInt(b.priority || 0, 10) - parseInt(a.priority || 0, 10);
      });
  }

  function rowGroupKey(row) {
    if (!row) return "";
    if (row.intelligence_group_key) return norm(row.intelligence_group_key);
    var mi = row.merchant_intelligence_v1;
    if (mi && mi.intelligence_group_key) return norm(mi.intelligence_group_key);
    if (mi && mi.group_assignment && mi.group_assignment.group_id) {
      return norm(mi.group_assignment.group_id);
    }
    return "";
  }

  function recoveryKey(row, cartRecoveryKeyFn) {
    if (typeof cartRecoveryKeyFn === "function") {
      return norm(cartRecoveryKeyFn(row));
    }
    return norm(row.recovery_key || row.proof_source);
  }

  function rowsForGroup(group, rows, cartRecoveryKeyFn) {
    var gid = norm(group.group_id);
    var keys = group.affected_cart_keys;
    if (Array.isArray(keys) && keys.length) {
      var set = {};
      keys.forEach(function (k) {
        set[norm(k)] = true;
      });
      return (rows || []).filter(function (r) {
        return set[recoveryKey(r, cartRecoveryKeyFn)];
      });
    }
    var pk = norm(group.pattern_key);
    if (pk.indexOf("reason:") === 0) {
      var tag = pk.slice(7).toLowerCase();
      return (rows || []).filter(function (r) {
        return norm(r.reason_tag).toLowerCase() === tag;
      });
    }
    if (pk.indexOf("product:") === 0) {
      var pid = pk.slice(8);
      return (rows || []).filter(function (r) {
        return norm(r.product_id || r.zid_product_id) === pid;
      });
    }
    return (rows || []).filter(function (r) {
      return rowGroupKey(r) === gid;
    });
  }

  function rowsForStory(story, rows, cartRecoveryKeyFn) {
    var keys = story.affected_cart_keys;
    if (Array.isArray(keys) && keys.length) {
      var set = {};
      keys.forEach(function (k) {
        set[norm(k)] = true;
      });
      return (rows || []).filter(function (r) {
        return set[recoveryKey(r, cartRecoveryKeyFn)];
      });
    }
    return [];
  }

  function storyCardHtml(story, rowsInStory, deps) {
    var esc = deps.esc;
    var sid = norm(story.story_id);
    var title = esc(merchantFacingText(story.title_ar || ""));
    var what = esc(merchantFacingText(story.headline_ar || ""));
    var meaning = esc(merchantFacingText(story.merchant_meaning_ar || ""));
    var did = esc(merchantFacingText(story.cartflow_action_ar || ""));
    var count = parseInt(story.affected_carts || rowsInStory.length || 0, 10);
    var actionLine = esc(
      merchantFacingText(
        story.merchant_action_line_ar ||
          story.recommendation_ar ||
          (story.action_required ? "نعم — يلزم تدخلك" : "لا — CartFlow يتابع تلقائياً")
      )
    );
    var actionClass = story.action_required ? "ma-mi-decision-row--action" : "";

    return (
      '<summary class="ma-mi-group-card" data-mi-story-id="' +
      esc(sid) +
      '">' +
      '<div class="ma-mi-group-card__head">' +
      '<h2 class="ma-mi-group-card__title">' +
      title +
      "</h2>" +
      '<span class="ma-mi-group-card__badge" aria-label="عدد السلال">' +
      String(count) +
      " سلة</span>" +
      "</div>" +
      summaryPreviewBlock(
        decisionRowHtml("ماذا حدث؟", what, esc) +
          decisionRowHtml("لماذا يهم؟", meaning, esc) +
          decisionRowHtml("ماذا فعل CartFlow؟", did, esc) +
          decisionRowHtml("هل تحتاج أن تتدخل؟", actionLine, esc, actionClass)
      ) +
      '<span class="ma-mi-group-card__cta v2-btn" aria-hidden="true">عرض التفاصيل</span>' +
      "</summary>"
    );
  }

  function storyExpandedHtml(story, rowsInStory, deps) {
    var esc = deps.esc;
    var parts = [];
    var meaning = merchantFacingText(story.merchant_meaning_ar || "");
    if (meaning) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">لماذا يهم؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(meaning) +
          "</p></section>"
      );
    }
    var observed = merchantFacingText(story.observed_result_ar || "");
    if (observed) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">ماذا تغيّر؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(observed) +
          "</p></section>"
      );
    }
    var did = merchantFacingText(story.cartflow_action_ar || "");
    if (did) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">ماذا فعل CartFlow؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(did) +
          "</p></section>"
      );
    }
    var rec = merchantFacingText(story.recommendation_ar || "");
    if (rec) {
      parts.push(
        '<section class="ma-mi-group-section ma-mi-group-section--rec">' +
          '<h3 class="ma-mi-group-section__label">ما الذي يستحق النظر؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(rec) +
          "</p></section>"
      );
    }
    var repSplit = splitRepresentative(
      { representative_item: { recovery_key: (rowsInStory[0] && recoveryKey(rowsInStory[0], deps.cartRecoveryKey)) || "" } },
      rowsInStory,
      deps.cartRecoveryKey
    );
    if (repSplit.representative.length) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">أمثلة من السلال</h3>' +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.representative.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected = deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(miCartQueueItemHtml(row, selected, deps));
      });
      parts.push("</div></section>");
    }
    if (repSplit.remaining.length) {
      parts.push(
        '<details class="ma-mi-group-more">' +
          '<summary class="ma-mi-group-more__summary">باقي السلال (' +
          String(repSplit.remaining.length) +
          ")</summary>" +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.remaining.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected = deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(miCartQueueItemHtml(row, selected, deps));
      });
      parts.push("</div></details>");
    }
    return (
      '<div class="ma-mi-group-body" data-mi-story-id="' +
      esc(norm(story.story_id)) +
      '">' +
      parts.join("") +
      "</div>"
    );
  }

  function recommendationForGroup(group, rowsInGroup, storeRecommendations) {
    var gid = norm(group.group_id);
    var best = null;
    (storeRecommendations || []).forEach(function (rec) {
      if (norm(rec.group_id) === gid) {
        if (
          !best ||
          parseInt(rec.priority || 0, 10) > parseInt(best.priority || 0, 10)
        ) {
          best = rec;
        }
      }
    });
    (rowsInGroup || []).forEach(function (row) {
      var mi = row.merchant_intelligence_v1;
      var rec = mi && mi.recommendation;
      if (!rec) return;
      if (
        !best ||
        parseInt(rec.priority || 0, 10) > parseInt(best.priority || 0, 10)
      ) {
        best = rec;
      }
    });
    return best;
  }

  function recTypeLabelAr(recType) {
    return REC_TYPE_LABEL_AR[norm(recType)] || "—";
  }

  function splitRepresentative(group, rowsInGroup, cartRecoveryKeyFn) {
    var repKey =
      group.representative_item && group.representative_item.recovery_key
        ? norm(group.representative_item.recovery_key)
        : "";
    var reps = [];
    var rest = [];
    (rowsInGroup || []).forEach(function (row) {
      var rk = recoveryKey(row, cartRecoveryKeyFn);
      if (repKey && rk === repKey) {
        reps.push(row);
      } else if (!repKey && !reps.length) {
        reps.push(row);
      } else {
        rest.push(row);
      }
    });
    if (!reps.length && rowsInGroup && rowsInGroup.length) {
      reps = [rowsInGroup[0]];
      rest = rowsInGroup.slice(1);
    }
    return { representative: reps, remaining: rest };
  }

  function explanationFromRow(row) {
    var expl = row && row.merchant_explanation_v1;
    if (expl && typeof expl === "object") return expl;
    return null;
  }

  function cartFlowDidPreview(rowsInGroup) {
    var rep = rowsInGroup && rowsInGroup[0];
    var expl = rep ? explanationFromRow(rep) : null;
    if (expl && expl.system_did_ar) {
      return merchantFacingText(expl.system_did_ar);
    }
    return "";
  }

  function cartFlowObservedPreview(group, rowsInGroup) {
    var summary = merchantFacingText(group.merchant_summary_ar || "");
    if (summary) return summary;
    var rep = rowsInGroup && rowsInGroup[0];
    var expl = rep ? explanationFromRow(rep) : null;
    if (expl && expl.what_happened_ar) {
      return merchantFacingText(expl.what_happened_ar);
    }
    return "";
  }

  function decisionRowHtml(label, value, esc, extraClass) {
    if (!value) return "";
    return (
      '<div class="ma-mi-decision-row' +
      (extraClass ? " " + extraClass : "") +
      '">' +
      '<p class="ma-mi-decision-row__k">' +
      esc(label) +
      "</p>" +
      '<p class="ma-mi-decision-row__v">' +
      esc(value) +
      "</p></div>"
    );
  }

  function summaryPreviewBlock(innerHtml) {
    if (!innerHtml) return "";
    return (
      '<div class="ma-mi-group-card__preview" data-mi-summary-preview="1">' +
      innerHtml +
      "</div>"
    );
  }

  function ensureSummaryPreview(summary) {
    var preview = summary.querySelector("[data-mi-summary-preview]");
    if (preview) return preview;
    var cta = summary.querySelector(".ma-mi-group-card__cta");
    var head = summary.querySelector(".ma-mi-group-card__head");
    var node = head ? head.nextSibling : summary.firstChild;
    var movable = [];
    while (node && node !== cta) {
      var next = node.nextSibling;
      if (
        node.nodeType === 1 &&
        (node.classList.contains("ma-mi-decision-row") ||
          node.classList.contains("ma-mi-group-card__meta"))
      ) {
        movable.push(node);
      }
      node = next;
    }
    if (!movable.length) return null;
    preview = document.createElement("div");
    preview.className = "ma-mi-group-card__preview";
    preview.setAttribute("data-mi-summary-preview", "1");
    summary.insertBefore(preview, movable[0]);
    movable.forEach(function (n) {
      preview.appendChild(n);
    });
    return preview;
  }

  function syncMiGroupSummaryPreview(el) {
    if (!el) return;
    var summary = el.querySelector("summary.ma-mi-group-card");
    if (!summary) return;
    var preview = summary.querySelector("[data-mi-summary-preview]");
    if (!preview) preview = ensureSummaryPreview(summary);
    if (el.open) {
      if (preview) {
        el._miSummaryPreviewHtml = preview.outerHTML;
        preview.parentNode.removeChild(preview);
      }
      summary.querySelectorAll(".ma-mi-decision-row, .ma-mi-group-card__meta").forEach(
        function (node) {
          if (node.parentNode === summary) node.parentNode.removeChild(node);
        }
      );
      return;
    }
    if (el._miSummaryPreviewHtml && !summary.querySelector("[data-mi-summary-preview]")) {
      var wrap = document.createElement("div");
      wrap.innerHTML = el._miSummaryPreviewHtml;
      var node = wrap.firstElementChild;
      if (node) {
        var anchor = summary.querySelector(".ma-mi-group-card__cta");
        if (anchor) summary.insertBefore(node, anchor);
        else summary.appendChild(node);
      }
    }
  }

  function syncOpenMiGroupSummaryPreviews(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("details.ma-mi-group[open]").forEach(function (el) {
      syncMiGroupSummaryPreview(el);
    });
  }

  function groupCardHtml(group, rec, rowsInGroup, deps) {
    var esc = deps.esc;
    var gid = norm(group.group_id);
    var title = esc(localizedGroupTitle(group));
    var meaning = esc(
      merchantFacingText(group.meaning_ar || group.reason || "")
    );
    var what = esc(
      merchantFacingText(
        group.merchant_summary_ar ||
          group.meaning_ar ||
          cartFlowObservedPreview(group, rowsInGroup)
      )
    );
    var did = esc(cartFlowDidPreview(rowsInGroup));
    var count = parseInt(group.affected_carts || 0, 10);
    if (!what && count) {
      what = esc(String(count) + " سلة في هذه المجموعة");
    }
    if (!meaning && count) {
      meaning = esc("مجموعة تستحق انتباهك لفهم حالة المتجر");
    }
    if (!did && count) {
      did = esc("CartFlow يتابع هذه السلال ويسجّل ما يحدث");
    }
    var value = parseFloat(group.total_cart_value || 0);
    var recType = rec ? norm(rec.recommendation_type) : norm(group.recommended_action_type);
    var recTypeLbl = esc(recTypeLabelAr(recType));
    var recMsg = rec ? esc(merchantFacingText(rec.merchant_message_ar || "")) : "";
    var actionLine =
      recType === "required_action" || recType === "suggested_action"
        ? recTypeLbl + (recMsg ? " — " + recMsg : "")
        : recTypeLbl;

    return (
      '<summary class="ma-mi-group-card" data-mi-group-id="' +
      esc(gid) +
      '">' +
      '<div class="ma-mi-group-card__head">' +
      '<h2 class="ma-mi-group-card__title">' +
      title +
      "</h2>" +
      '<span class="ma-mi-group-card__badge" aria-label="عدد السلال">' +
      String(count) +
      " سلة</span>" +
      "</div>" +
      summaryPreviewBlock(
        decisionRowHtml("ماذا يحدث؟", what, esc) +
          decisionRowHtml("لماذا يهم؟", meaning, esc) +
          decisionRowHtml("ماذا فعل CartFlow؟", did, esc) +
          decisionRowHtml(
            "هل يلزم إجراء؟",
            actionLine,
            esc,
            recType === "required_action" ? "ma-mi-decision-row--action" : ""
          ) +
          (value > 0
            ? '<div class="ma-mi-group-card__meta">' +
              '<span class="ma-mi-group-card__value cf-currency-atom cftyp-currency" data-cf-currency="1" dir="ltr">' +
              esc(merchantCurrencyText(value)) +
              "</span>" +
              "</div>"
            : "")
      ) +
      '<span class="ma-mi-group-card__cta v2-btn" aria-hidden="true">عرض التفاصيل</span>' +
      "</summary>"
    );
  }

  function groupExpandedHtml(group, rec, rowsInGroup, deps) {
    var esc = deps.esc;
    var parts = [];
    var meaning = merchantFacingText(group.meaning_ar || "");
    if (meaning) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">لماذا هذه المجموعة؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(meaning) +
          "</p></section>"
      );
    }
    var observed = cartFlowObservedPreview(group, rowsInGroup);
    if (observed) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">ماذا لاحظ CartFlow؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(observed) +
          "</p></section>"
      );
    }
    var repSplit = splitRepresentative(group, rowsInGroup, deps.cartRecoveryKey);
    var repRow = repSplit.representative[0];
    var expl = repRow ? explanationFromRow(repRow) : null;
    if (expl && expl.system_did_ar) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">ماذا فعل CartFlow؟</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(merchantFacingText(expl.system_did_ar)) +
          "</p></section>"
      );
    }
    if (rec && rec.merchant_message_ar) {
      parts.push(
        '<section class="ma-mi-group-section ma-mi-group-section--rec">' +
          '<h3 class="ma-mi-group-section__label">التوصية</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(merchantFacingText(rec.merchant_message_ar)) +
          "</p></section>"
      );
    }
    if (repSplit.representative.length) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">أمثلة من السلال</h3>' +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.representative.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected = deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(miCartQueueItemHtml(row, selected, deps));
      });
      parts.push("</div></section>");
    }
    if (repSplit.remaining.length) {
      parts.push(
        '<details class="ma-mi-group-more">' +
          '<summary class="ma-mi-group-more__summary">باقي السلال (' +
          String(repSplit.remaining.length) +
          ")</summary>" +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.remaining.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected = deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(miCartQueueItemHtml(row, selected, deps));
      });
      parts.push("</div></details>");
    }
    if (deps.primaryActionHtml && repRow) {
      parts.push(
        '<footer class="ma-mi-group-footer">' +
          deps.primaryActionHtml(repRow) +
          "</footer>"
      );
    }
    return (
      '<div class="ma-mi-group-body" data-mi-group-id="' +
      esc(norm(group.group_id)) +
      '">' +
      parts.join("") +
      "</div>"
    );
  }

  function miCartQueueItemHtml(row, selected, deps) {
    var esc = deps.esc;
    var v = Math.round(parseFloat(row.merchant_cart_value) || 0);
    var expl = explanationFromRow(row);
    var scan =
      merchantFacingText(
        (expl && expl.status_label_ar) ||
          row.customer_lifecycle_label_ar ||
          row.merchant_status_label_ar ||
          ""
      ) || "—";
    var rk = recoveryKey(row, deps.cartRecoveryKey);
    var time = esc(row.merchant_time_relative_ar || "—");
    var filter = esc(row.merchant_cart_bucket || "other");
    var primary = esc(row.merchant_cart_primary_bucket || filter);
    var tabsJson = "[]";
    try {
      tabsJson = esc(JSON.stringify(row.merchant_cart_visible_tabs || []));
    } catch (_tabsErr) {
      tabsJson = "[]";
    }
    return (
      '<button type="button" class="v2-queue-item' +
      (selected ? " is-selected" : "") +
      '" data-ma-filter="' +
      filter +
      '" data-ma-primary-bucket="' +
      primary +
      '" data-ma-visible-tabs="' +
      tabsJson +
      '" data-recovery-key="' +
      esc(rk) +
      '">' +
      '<span class="v2-queue-accent ' +
      queueAccentClass(row) +
      '" aria-hidden="true"></span>' +
      '<div class="v2-queue-body">' +
      queueAmountHtml(v, esc) +
      '<p class="v2-queue-scan ma-cart-product-identity" data-pi-status="' +
      esc(row.merchant_product_identity_status || "unresolved") +
      '">' +
      esc(
        row.merchant_product_name ||
          (row.product_identity_v1 && row.product_identity_v1.display_name_ar) ||
          "اسم المنتج غير متوفر"
      ) +
      "</p>" +
      '<p class="v2-queue-scan">' +
      esc(scan) +
      "</p></div>" +
      '<span class="v2-queue-time">' +
      time +
      "</span></button>"
    );
  }

  function workspaceSubtitle(store, rows) {
    var groups = (store && store.groups) || [];
    if (!groups.length && !(rows && rows.length)) {
      return "لا توجد سلات تحتاج انتباهك — CartFlow يتابع المتجر.";
    }
    if (!groups.length) {
      return "CartFlow يتابع سلات متجرك — لا يلزم تدخلك الآن.";
    }
    var needs = 0;
    var total = 0;
    groups.forEach(function (g) {
      var c = parseInt(g.affected_carts || 0, 10);
      total += c;
      if (norm(g.group_id) === "needs_merchant") needs = c;
    });
    if (needs) {
      return needs + " سلة تحتاج تدخلك · " + groups.length + " مجموعات";
    }
    return groups.length + " مجموعات · CartFlow يتابع " + total + " سلة";
  }

  function bindMiGroupDetails(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll("details.ma-mi-group").forEach(function (el) {
      var gid = norm(el.getAttribute("data-ma-story") || el.getAttribute("data-ma-group"));
      if (!gid) return;
      if (openGroupState[gid]) el.open = true;
      var summary = el.querySelector("summary.ma-mi-group-card");
      if (summary && !summary._miOpenBound) {
        summary._miOpenBound = true;
        summary.addEventListener("mousedown", function (ev) {
          if (ev.button !== 0) return;
          openGroupState[gid] = !el.open;
        });
        summary.addEventListener("click", function () {
          requestAnimationFrame(function () {
            syncMiGroupSummaryPreview(el);
          });
        });
      }
      if (!el._miToggleBound) {
        el._miToggleBound = true;
        el.addEventListener("toggle", function () {
          if (el.open) openGroupState[gid] = true;
          else delete openGroupState[gid];
          syncMiGroupSummaryPreview(el);
        });
      }
      syncMiGroupSummaryPreview(el);
    });
    root.querySelectorAll(".v2-queue-item").forEach(function (btn) {
      if (btn._miStopBound) return;
      btn._miStopBound = true;
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
      });
    });
  }

  function updateGroupSelection(root, selectedKey) {
    if (!root) return;
    var sel = norm(selectedKey);
    root.querySelectorAll(".v2-queue-item").forEach(function (btn) {
      btn.classList.toggle(
        "is-selected",
        norm(btn.getAttribute("data-recovery-key")) === sel
      );
    });
  }

  function captureOpenGroups(root) {
    if (!root) return;
    root.querySelectorAll("details.ma-mi-group").forEach(function (el) {
      var gid = norm(el.getAttribute("data-ma-story") || el.getAttribute("data-ma-group"));
      if (!gid) return;
      if (el.open) openGroupState[gid] = true;
      else delete openGroupState[gid];
    });
  }

  function workspaceSubtitleFromStories(bundle, rows) {
    var stories = (bundle && bundle.stories) || [];
    if (!stories.length && !(rows && rows.length)) {
      return "لا توجد سلات تحتاج انتباهك — CartFlow يتابع المتجر.";
    }
    if (!stories.length) {
      return "CartFlow يتابع سلات متجرك — لا يلزم تدخلك الآن.";
    }
    var needs = 0;
    var total = 0;
    stories.forEach(function (s) {
      var c = parseInt(s.affected_carts || 0, 10);
      total += c;
      if (norm(s.story_type) === "needs_merchant_story") needs = c;
    });
    if (needs) {
      return needs + " سلة تحتاج تدخلك · " + stories.length + " قصص";
    }
    return stories.length + " قصص · CartFlow يتابع " + total + " سلة";
  }

  function workspaceSubtitleFromPayload(d, rows) {
    if (hasValueStories(d)) {
      return workspaceSubtitleFromStories(d.merchant_value_stories_v1, rows);
    }
    return workspaceSubtitle(d && d.merchant_intelligence_store_v1, rows);
  }

  function workspaceKey(d, rows) {
    var rowSig = (rows || [])
      .map(function (r) {
        return norm(recoveryKey(r, null) || r.zid_cart_id || r.cart_id || "");
      })
      .filter(Boolean)
      .slice(0, 60)
      .join(",");
    var stories = (d && d.merchant_value_stories_v1 && d.merchant_value_stories_v1.stories) || [];
    if (stories.length) {
      var sig = stories
        .map(function (s) {
          return [
            String(s.story_id || ""),
            String(s.affected_carts != null ? s.affected_carts : ""),
            String(s.display_priority != null ? s.display_priority : ""),
          ].join(":");
        })
        .join("|");
      return "stories:" + sig + "::" + String(rows.length) + "::" + rowSig;
    }
    var store = d && d.merchant_intelligence_store_v1;
    var gsig = ((store && store.groups) || [])
      .map(function (g) {
        return [
          String(g.group_id || ""),
          String(g.affected_carts != null ? g.affected_carts : ""),
          String(g.total_cart_value != null ? g.total_cart_value : ""),
          String(g.priority != null ? g.priority : ""),
        ].join(":");
      })
      .join("|");
    return "groups:" + gsig + "::" + String(rows.length) + "::" + rowSig;
  }

  function renderStories(root, bundle, rows, deps) {
    if (!root) return false;
    captureOpenGroups(root);
    var stories = (bundle && bundle.stories) || [];
    if (!stories.length) {
      root.innerHTML = "";
      if (deps.emptyEl) {
        deps.emptyEl.hidden = false;
        var p = deps.emptyEl.querySelector(".v2-whisper-text");
        if (p) {
          p.textContent =
            rows && rows.length
              ? "CartFlow يتابع سلات متجرك — لا يلزم تدخلك الآن."
              : "لا توجد سلات نشطة — CartFlow يراقب المتجر.";
        }
      }
      if (deps.onSelectCart) deps.onSelectCart("");
      try {
        if (typeof window.__maCartsRowTrace !== "undefined") {
          (window.__maCartsRowTrace = window.__maCartsRowTrace || []).push({
            ts: Date.now(),
            stage: "5b_mi_render_stories",
            outcome: "no_stories",
            page_rows: (rows || []).length,
          });
        }
      } catch (_t) {
        /* ignore */
      }
      return true;
    }
    if (deps.emptyEl) deps.emptyEl.hidden = true;
    var matchAudit = [];
    var html = stories
      .map(function (story) {
        var rowsInStory = rowsForStory(story, rows, deps.cartRecoveryKey);
        matchAudit.push({
          story_id: String((story && story.story_id) || ""),
          keys_len: Array.isArray(story && story.affected_cart_keys)
            ? story.affected_cart_keys.length
            : 0,
          matched_rows: rowsInStory.length,
        });
        var sid = norm(story.story_id);
        var openAttr = openGroupState[sid] ? " open" : "";
        return (
          '<details class="ma-mi-group ma-cart-group ma-mi-story"' +
          openAttr +
          ' data-ma-story="' +
          deps.esc(sid) +
          '">' +
          storyCardHtml(story, rowsInStory, deps) +
          storyExpandedHtml(story, rowsInStory, deps) +
          "</details>"
        );
      })
      .join("");
    root.innerHTML = html;
    try {
      if (typeof window.__maCartsRowTrace !== "undefined") {
        (window.__maCartsRowTrace = window.__maCartsRowTrace || []).push({
          ts: Date.now(),
          stage: "5b_mi_render_stories",
          outcome: "rendered",
          page_rows: (rows || []).length,
          stories: stories.length,
          match_audit: matchAudit.slice(0, 20),
          queue_items_in_dom: root.querySelectorAll(".v2-queue-item").length,
        });
      }
    } catch (_t2) {
      /* ignore */
    }
    bindMiGroupDetails(root);
    if (deps.bindQueue) deps.bindQueue(root);
    if (deps.updateSubtitle) {
      deps.updateSubtitle(workspaceSubtitleFromStories(bundle, rows));
    }
    return true;
  }

  function renderGroups(root, store, rows, deps) {
    if (!root) return false;
    captureOpenGroups(root);
    var groups = sortGroups((store && store.groups) || []);
    var recs = (store && store.recommendations) || [];
    if (!groups.length) {
      root.innerHTML = "";
      if (deps.emptyEl) {
        deps.emptyEl.hidden = false;
        var p = deps.emptyEl.querySelector(".v2-whisper-text");
        if (p) {
          p.textContent =
            rows && rows.length
              ? "CartFlow يتابع سلات متجرك — لا يلزم تدخلك الآن."
              : "لا توجد سلات نشطة — CartFlow يراقب المتجر.";
        }
      }
      if (deps.onSelectCart) deps.onSelectCart("");
      try {
        if (typeof window.__maCartsRowTrace !== "undefined") {
          (window.__maCartsRowTrace = window.__maCartsRowTrace || []).push({
            ts: Date.now(),
            stage: "5b_mi_render_groups",
            outcome: "no_groups",
            page_rows: (rows || []).length,
          });
        }
      } catch (_tg) {
        /* ignore */
      }
      return true;
    }
    if (deps.emptyEl) deps.emptyEl.hidden = true;
    var matchAudit = [];
    var html = groups
      .map(function (group) {
        var rowsInGroup = rowsForGroup(group, rows, deps.cartRecoveryKey);
        matchAudit.push({
          group_id: String((group && group.group_id) || ""),
          matched_rows: rowsInGroup.length,
        });
        var rec = recommendationForGroup(group, rowsInGroup, recs);
        var openAttr = openGroupState[norm(group.group_id)] ? " open" : "";
        return (
          '<details class="ma-mi-group ma-cart-group"' +
          openAttr +
          ' data-ma-group="' +
          deps.esc(norm(group.group_id)) +
          '">' +
          groupCardHtml(group, rec, rowsInGroup, deps) +
          groupExpandedHtml(group, rec, rowsInGroup, deps) +
          "</details>"
        );
      })
      .join("");
    root.innerHTML = html;
    try {
      if (typeof window.__maCartsRowTrace !== "undefined") {
        (window.__maCartsRowTrace = window.__maCartsRowTrace || []).push({
          ts: Date.now(),
          stage: "5b_mi_render_groups",
          outcome: "rendered",
          page_rows: (rows || []).length,
          groups: groups.length,
          match_audit: matchAudit.slice(0, 20),
          queue_items_in_dom: root.querySelectorAll(".v2-queue-item").length,
        });
      }
    } catch (_tg2) {
      /* ignore */
    }
    bindMiGroupDetails(root);
    if (deps.bindQueue) deps.bindQueue(root);
    if (deps.updateSubtitle) {
      deps.updateSubtitle(workspaceSubtitle(store, rows));
    }
    return true;
  }

  function hasValueStories(d) {
    return !!(
      d &&
      d.merchant_value_stories_v1 &&
      Array.isArray(d.merchant_value_stories_v1.stories) &&
      d.merchant_value_stories_v1.stories.length
    );
  }

  function hasRenderablePayload(d) {
    if (hasValueStories(d)) return true;
    return hasStorePayload(d);
  }

  function hasStorePayload(d) {
    return !!(
      d &&
      d.merchant_intelligence_store_v1 &&
      Array.isArray(d.merchant_intelligence_store_v1.groups)
    );
  }

  function resetOpenGroupState() {
    openGroupState = {};
  }

  global.maIntelligenceCartsV1 = {
    GROUP_ORDER: GROUP_ORDER,
    REASON_TAG_AR: REASON_TAG_AR,
    sortGroups: sortGroups,
    rowsForGroup: rowsForGroup,
    rowsForStory: rowsForStory,
    recommendationForGroup: recommendationForGroup,
    workspaceSubtitle: workspaceSubtitle,
    workspaceSubtitleFromStories: workspaceSubtitleFromStories,
    workspaceSubtitleFromPayload: workspaceSubtitleFromPayload,
    workspaceKey: workspaceKey,
    merchantFacingText: merchantFacingText,
    localizedGroupTitle: localizedGroupTitle,
    bindMiGroupDetails: bindMiGroupDetails,
    syncMiGroupSummaryPreview: syncMiGroupSummaryPreview,
    syncOpenMiGroupSummaryPreviews: syncOpenMiGroupSummaryPreviews,
    updateGroupSelection: updateGroupSelection,
    resetOpenGroupState: resetOpenGroupState,
    renderGroups: renderGroups,
    renderStories: renderStories,
    hasStorePayload: hasStorePayload,
    hasValueStories: hasValueStories,
    hasRenderablePayload: hasRenderablePayload,
  };
})(typeof window !== "undefined" ? window : this);
