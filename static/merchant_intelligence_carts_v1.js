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

  var CONF_LABEL_AR = {
    high: "ثقة عالية",
    medium: "ثقة متوسطة",
    low: "ثقة منخفضة",
    insufficient: "ثقة محدودة",
  };

  var REC_TYPE_LABEL_AR = {
    required_action: "إجراء مطلوب",
    suggested_action: "مقترح",
    watch_only: "مراقبة",
    informational: "معلومة",
    no_action: "لا يلزم إجراء",
    blocked: "محظور",
  };

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

  function confidenceLabelAr(conf) {
    return CONF_LABEL_AR[norm(conf).toLowerCase()] || "—";
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
    var valueStr =
      value > 0 ? Math.round(value).toLocaleString("en-US") + " ر.س" : "";
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
      decisionRowHtml("ماذا يحدث؟", what, esc) +
      decisionRowHtml("لماذا يهم؟", meaning, esc) +
      decisionRowHtml("ماذا فعل CartFlow؟", did, esc) +
      decisionRowHtml(
        "هل يلزم إجراء؟",
        actionLine,
        esc,
        recType === "required_action" ? "ma-mi-decision-row--action" : ""
      ) +
      '<div class="ma-mi-group-card__meta">' +
      (valueStr
        ? '<span class="ma-mi-group-card__value">' + esc(valueStr) + "</span>"
        : "") +
      '<span class="ma-mi-group-card__conf">' +
      esc(confidenceLabelAr(group.confidence)) +
      "</span>" +
      "</div>" +
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
          "</p>" +
          (deps.primaryActionHtml && repRow
            ? '<div class="ma-mi-group-section__cta">' +
              deps.primaryActionHtml(repRow) +
              "</div>"
            : "") +
          "</section>"
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
    return (
      '<button type="button" class="v2-queue-item' +
      (selected ? " is-selected" : "") +
      '" data-recovery-key="' +
      esc(rk) +
      '">' +
      '<div class="v2-queue-body">' +
      '<div class="v2-queue-amount">' +
      v.toLocaleString("en-US") +
      " ر</div>" +
      '<p class="v2-queue-scan">' +
      esc(scan) +
      "</p></div></button>"
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
      var gid = norm(el.getAttribute("data-ma-group"));
      if (!gid) return;
      if (openGroupState[gid]) el.open = true;
      var summary = el.querySelector("summary.ma-mi-group-card");
      if (summary && !summary._miOpenBound) {
        summary._miOpenBound = true;
        summary.addEventListener("mousedown", function (ev) {
          if (ev.button !== 0) return;
          openGroupState[gid] = !el.open;
        });
      }
      if (el._miToggleBound) return;
      el._miToggleBound = true;
      el.addEventListener("toggle", function () {
        if (el.open) openGroupState[gid] = true;
        else delete openGroupState[gid];
      });
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
      var gid = norm(el.getAttribute("data-ma-group"));
      if (!gid) return;
      if (el.open) openGroupState[gid] = true;
      else delete openGroupState[gid];
    });
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
      return true;
    }
    if (deps.emptyEl) deps.emptyEl.hidden = true;
    var html = groups
      .map(function (group) {
        var rowsInGroup = rowsForGroup(group, rows, deps.cartRecoveryKey);
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
    bindMiGroupDetails(root);
    if (deps.bindQueue) deps.bindQueue(root);
    if (deps.updateSubtitle) {
      deps.updateSubtitle(workspaceSubtitle(store, rows));
    }
    return true;
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
    recommendationForGroup: recommendationForGroup,
    workspaceSubtitle: workspaceSubtitle,
    merchantFacingText: merchantFacingText,
    localizedGroupTitle: localizedGroupTitle,
    bindMiGroupDetails: bindMiGroupDetails,
    updateGroupSelection: updateGroupSelection,
    resetOpenGroupState: resetOpenGroupState,
    renderGroups: renderGroups,
    hasStorePayload: hasStorePayload,
  };
})(typeof window !== "undefined" ? window : this);
