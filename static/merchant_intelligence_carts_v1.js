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

  function norm(value) {
    return String(value == null ? "" : value).trim();
  }

  function groupRank(groupId, priorities) {
    var gid = norm(groupId);
    var pri = priorities || [];
    for (var i = 0; i < pri.length; i++) {
      var band = norm(pri[i].priority_band);
      var msg = norm(pri[i].merchant_message_ar);
      if (band === "highest" || band === "today") {
        /* priorities are cart-level; use static order */
      }
    }
    var idx = GROUP_ORDER.indexOf(gid);
    return idx >= 0 ? idx : GROUP_ORDER.length + 1;
  }

  function sortGroups(groups, priorities) {
    return (groups || [])
      .slice()
      .sort(function (a, b) {
        var ra = groupRank(a.group_id, priorities);
        var rb = groupRank(b.group_id, priorities);
        if (ra !== rb) return ra - rb;
        return (
          parseInt(b.priority || 0, 10) - parseInt(a.priority || 0, 10)
        );
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
    return CONF_LABEL_AR[norm(conf).toLowerCase()] || norm(conf) || "—";
  }

  function recTypeLabelAr(recType) {
    return REC_TYPE_LABEL_AR[norm(recType)] || norm(recType) || "";
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

  function groupCardHtml(group, rec, deps) {
    var esc = deps.esc;
    var gid = norm(group.group_id);
    var title = esc(group.title_ar || gid);
    var meaning = esc(group.meaning_ar || "");
    var summary = esc(group.merchant_summary_ar || "");
    var count = parseInt(group.affected_carts || 0, 10);
    var value = parseFloat(group.total_cart_value || 0);
    var valueStr =
      value > 0
        ? Math.round(value).toLocaleString("en-US") + " ر.س"
        : "";
    var conf = esc(confidenceLabelAr(group.confidence));
    var pri = parseInt(group.priority || 0, 10);
    var recMsg = rec ? esc(rec.merchant_message_ar || "") : "";
    var recType = rec ? norm(rec.recommendation_type) : norm(group.recommended_action_type);
    var recTypeLbl = esc(recTypeLabelAr(recType));
    var ctaClass =
      recType === "required_action"
        ? " v2-btn--attention"
        : recType === "suggested_action"
          ? " v2-btn--primary"
          : "";

    return (
      '<summary class="ma-mi-group-card" data-mi-group-id="' +
      esc(gid) +
      '">' +
      '<div class="ma-mi-group-card__head">' +
      '<h2 class="ma-mi-group-card__title">' +
      title +
      "</h2>" +
      '<span class="ma-mi-group-card__badge">' +
      String(count) +
      "</span>" +
      "</div>" +
      (meaning
        ? '<p class="ma-mi-group-card__meaning">' + meaning + "</p>"
        : "") +
      (summary
        ? '<p class="ma-mi-group-card__summary">' + summary + "</p>"
        : "") +
      '<div class="ma-mi-group-card__meta">' +
      (valueStr
        ? '<span class="ma-mi-group-card__value">' + esc(valueStr) + "</span>"
        : "") +
      '<span class="ma-mi-group-card__conf">' +
      conf +
      "</span>" +
      (pri
        ? '<span class="ma-mi-group-card__pri">أولوية ' + String(pri) + "</span>"
        : "") +
      (recTypeLbl
        ? '<span class="ma-mi-group-card__rec-type">' + recTypeLbl + "</span>"
        : "") +
      "</div>" +
      (recMsg
        ? '<p class="ma-mi-group-card__rec">' + recMsg + "</p>"
        : "") +
      '<span class="ma-mi-group-card__cta v2-btn' +
      ctaClass +
      '">عرض التفاصيل</span>' +
      "</summary>"
    );
  }

  function groupExpandedHtml(group, rec, rowsInGroup, deps) {
    var esc = deps.esc;
    var parts = [];
    var reason = norm(group.reason);
    if (reason) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">لماذا هذه المجموعة</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(group.meaning_ar || reason) +
          "</p></section>"
      );
    }
    var repSplit = splitRepresentative(
      group,
      rowsInGroup,
      deps.cartRecoveryKey
    );
    var repRow = repSplit.representative[0];
    var expl = repRow ? explanationFromRow(repRow) : null;
    if (expl && expl.system_did_ar) {
      parts.push(
        '<section class="ma-mi-group-section">' +
          '<h3 class="ma-mi-group-section__label">ما أنجزه CartFlow</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(expl.system_did_ar) +
          "</p></section>"
      );
    }
    if (rec && rec.merchant_message_ar) {
      parts.push(
        '<section class="ma-mi-group-section ma-mi-group-section--rec">' +
          '<h3 class="ma-mi-group-section__label">التوصية</h3>' +
          '<p class="ma-mi-group-section__text">' +
          esc(rec.merchant_message_ar) +
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
          '<h3 class="ma-mi-group-section__label">أمثلة ممثّلة</h3>' +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.representative.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected =
          deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(deps.cartQueueItemHtml(row, selected));
      });
      parts.push("</div></section>");
    }
    if (repSplit.remaining.length) {
      parts.push(
        '<details class="ma-mi-group-more">' +
          '<summary class="ma-mi-group-more__summary">سلات أخرى (' +
          String(repSplit.remaining.length) +
          ")</summary>" +
          '<div class="ma-mi-group-section__queue v2-queue-list">'
      );
      repSplit.remaining.forEach(function (row) {
        var rk = recoveryKey(row, deps.cartRecoveryKey);
        var selected =
          deps.selectedKey && norm(deps.selectedKey) === rk;
        parts.push(deps.cartQueueItemHtml(row, selected));
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

  function renderGroups(root, store, rows, deps) {
    if (!root) return false;
    var groups = sortGroups(
      (store && store.groups) || [],
      (store && store.priorities) || []
    );
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
        return (
          '<details class="ma-mi-group ma-cart-group" data-ma-group="' +
          deps.esc(norm(group.group_id)) +
          '">' +
          groupCardHtml(group, rec, deps) +
          groupExpandedHtml(group, rec, rowsInGroup, deps) +
          "</details>"
        );
      })
      .join("");
    root.innerHTML = html;
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

  global.maIntelligenceCartsV1 = {
    GROUP_ORDER: GROUP_ORDER,
    sortGroups: sortGroups,
    rowsForGroup: rowsForGroup,
    recommendationForGroup: recommendationForGroup,
    workspaceSubtitle: workspaceSubtitle,
    renderGroups: renderGroups,
    hasStorePayload: hasStorePayload,
  };
})(typeof window !== "undefined" ? window : this);
