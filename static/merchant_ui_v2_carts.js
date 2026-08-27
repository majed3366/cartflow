/**
 * CartFlow Merchant UI V2 — Carts Product Composition V1.
 * Operations workspace inside PageStage. Consumes V1 cart truth contracts.
 * Does not own Decision Workspace reasoning, VIP policy, or analytics.
 */
(function (global) {
  "use strict";

  var MARKER = "carts-product-composition-v1";

  var FILTERS = [
    { key: "all", label: "الكل", intent: "كل السلال" },
    { key: "attention", label: "يحتاجني", intent: "ماذا يحتاجني؟" },
    { key: "nophone", label: "بانتظار رقم العميل", intent: "ماذا ينتظر؟" },
    { key: "sent", label: "بانتظار الرد", intent: "ماذا ينتظر؟" },
    { key: "recovered", label: "اكتمل", intent: "ماذا اكتمل؟" },
  ];

  var PRIMARY_KEYS = {
    wait: true,
    contact_customer: true,
    follow_up_manually: true,
    review_cart: true,
    no_action_required: true,
    reopen: true,
    archive: true,
  };

  var PRIMARY_LABEL_AR = {
    no_action_required: "لا يلزم إجراء",
    wait: "انتظر — CartFlow يتابع",
    contact_customer: "تواصل مع العميل",
    review_cart: "راجع السلة",
    follow_up_manually: "متابعة يدوية",
    archive: "نقل للأرشيف",
    reopen: "إعادة فتح",
  };

  var PROOF_STEP_STATE_AR = {
    done: "تم",
    active: "جاري",
    pending: "بانتظار",
    skipped: "—",
    unknown: "غير معروف",
    failed: "تعذّر",
  };

  var ACTIONABLE = {
    contact_customer: true,
    follow_up_manually: true,
    review_cart: true,
  };

  var state = {
    root: null,
    payload: null,
    rows: [],
    archived: [],
    filter: "attention",
    selectedKey: "",
    detailOpen: false,
    loading: false,
    error: "",
    lastFilterBeforeEmpty: "attention",
    filterTouched: false,
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function recoveryKey(mc) {
    return String((mc && (mc.recovery_key || mc.recovery_session_id)) || "").trim();
  }

  function isArchivedVisual(mc) {
    if (!mc) return false;
    if (mc.customer_lifecycle_is_archived_visual === true) return true;
    return String(mc.customer_lifecycle_state || "").trim() === "archived";
  }

  function isPurchased(mc) {
    if (!mc) return false;
    if (String(mc.customer_lifecycle_completed_variant || "").trim() === "purchased") {
      return true;
    }
    if (String(mc.merchant_coarse_status || "").trim().toLowerCase() === "converted") {
      return true;
    }
    return false;
  }

  function isCompleted(mc) {
    if (!mc) return false;
    if (isPurchased(mc)) return true;
    if (String(mc.customer_lifecycle_state || "").trim().toLowerCase() === "completed") {
      return true;
    }
    return false;
  }

  function visibleTabs(mc) {
    var tabs = mc && mc.merchant_cart_visible_tabs;
    if (Array.isArray(tabs) && tabs.length) {
      return tabs.map(function (t) {
        return String(t || "").trim().toLowerCase();
      });
    }
    var b = String(
      (mc && (mc.merchant_cart_bucket || mc.merchant_cart_primary_bucket)) || ""
    )
      .trim()
      .toLowerCase();
    return b ? [b] : [];
  }

  function rowMatchesFilter(mc, filter) {
    if (!mc) return false;
    if (filter === "all") return !isArchivedVisual(mc);
    if (filter === "recovered") {
      return isCompleted(mc) || isArchivedVisual(mc);
    }
    var tabs = visibleTabs(mc);
    return tabs.indexOf(filter) >= 0;
  }

  function resolvePrimary(mc) {
    if (!mc || typeof mc !== "object") {
      return {
        key: "review_cart",
        label: PRIMARY_LABEL_AR.review_cart,
        secondary_key: "",
        secondary_demoted: false,
      };
    }
    if (isArchivedVisual(mc)) {
      if (isPurchased(mc) || isCompleted(mc)) {
        return {
          key: "no_action_required",
          label: PRIMARY_LABEL_AR.no_action_required,
          secondary_key: "",
          secondary_demoted: false,
        };
      }
      return {
        key: "reopen",
        label: PRIMARY_LABEL_AR.reopen,
        secondary_key: "",
        secondary_demoted: false,
      };
    }
    var pa = mc.cart_page_primary_action_v1;
    var key = "";
    var label = "";
    var secondaryKey = "";
    var demoted = false;
    if (pa && typeof pa === "object") {
      key = String(pa.key || "").trim().toLowerCase();
      label = String(pa.label || "").trim();
      secondaryKey = String(pa.secondary_key || "").trim().toLowerCase();
      demoted = pa.secondary_demoted === true;
    }
    if (key === "reopen") {
      key = "";
      label = "";
    }
    if (key === "archive") {
      secondaryKey = "archive";
      demoted = true;
      key = "";
      label = "";
    }
    if (isPurchased(mc) || isCompleted(mc)) {
      return {
        key: "no_action_required",
        label: PRIMARY_LABEL_AR.no_action_required,
        secondary_key: secondaryKey === "archive" ? "archive" : "",
        secondary_demoted: secondaryKey === "archive",
      };
    }
    if (!key || !PRIMARY_KEYS[key]) {
      key = "review_cart";
      label = PRIMARY_LABEL_AR.review_cart;
      if (!secondaryKey) {
        var dash = String(mc.customer_lifecycle_dashboard_action || "").trim();
        if (dash === "archive") {
          secondaryKey = "archive";
          demoted = true;
        }
      }
    }
    if (!label) label = PRIMARY_LABEL_AR[key] || key;
    return {
      key: key,
      label: label,
      secondary_key: secondaryKey,
      secondary_demoted: demoted,
    };
  }

  function contactHref(mc) {
    if (!mc) return "";
    var pa = resolvePrimary(mc);
    if (pa.key !== "contact_customer" && pa.key !== "follow_up_manually") return "";
    if (isPurchased(mc) || isCompleted(mc)) return "";
    var proj = mc.cart_detail_projection_v1;
    var contact = proj && proj.contact_action;
    if (contact && contact.visible && contact.href) {
      return String(contact.href || "").trim();
    }
    if (mc.merchant_intervention_executable) {
      return String(mc.merchant_intervention_contact_href || "").trim();
    }
    return String(mc.merchant_intervention_contact_href || "").trim();
  }

  function attentionLabel(mc) {
    if (!mc) return "";
    if (isArchivedVisual(mc)) return "مؤرشفة";
    if (isPurchased(mc)) return "تم الشراء";
    if (isCompleted(mc)) return "مكتملة";
    var expl = mc.merchant_explanation_v1;
    var fromExpl = expl && expl.status_label_ar;
    var raw =
      fromExpl ||
      mc.customer_lifecycle_label_ar ||
      mc.merchant_attention_label_ar ||
      mc.dashboard_attention_label_ar ||
      "";
    return String(raw || "").trim();
  }

  function whyInQueue(mc) {
    var label = attentionLabel(mc);
    if (label) return label;
    var pa = resolvePrimary(mc);
    return pa.label || "";
  }

  function cartTitle(mc) {
    var name =
      (mc && mc.merchant_customer_name) ||
      (mc && mc.customer_name) ||
      "";
    name = String(name || "").trim();
    if (name) return name;
    var product =
      (mc && mc.merchant_product_name) ||
      (mc && mc.product_identity_v1 && mc.product_identity_v1.display_name_ar) ||
      "";
    product = String(product || "").trim();
    if (product) return product;
    return "سلة";
  }

  function productLine(mc) {
    return String(
      (mc &&
        (mc.merchant_product_name ||
          (mc.product_identity_v1 && mc.product_identity_v1.display_name_ar))) ||
        ""
    ).trim();
  }

  function money(mc) {
    var v = Math.round(parseFloat(mc && mc.merchant_cart_value) || 0);
    if (!v) return "";
    if (typeof global.formatMerchantSar === "function") {
      return global.formatMerchantSar(v);
    }
    return v.toLocaleString("en-US") + " ر.س";
  }

  function timeLine(mc) {
    return String((mc && mc.merchant_time_relative_ar) || "").trim();
  }

  function isVipOperational(mc) {
    if (!mc) return false;
    var tabs = visibleTabs(mc);
    if (tabs.indexOf("vip") >= 0) return true;
    var bucket = String(
      mc.merchant_cart_primary_bucket || mc.merchant_cart_bucket || ""
    )
      .trim()
      .toLowerCase();
    return bucket === "vip";
  }

  function phoneAvailable(mc) {
    return !!(mc && mc.merchant_has_customer_phone);
  }

  function attentionWeight(mc) {
    if (isArchivedVisual(mc)) return 40;
    var pa = resolvePrimary(mc);
    if (ACTIONABLE[pa.key]) return 10;
    if (pa.key === "wait") return 20;
    if (pa.key === "no_action_required") return 30;
    if (pa.key === "reopen") return 40;
    return 25;
  }

  function sortQueue(rows) {
    return (rows || []).slice().sort(function (a, b) {
      var wa = attentionWeight(a);
      var wb = attentionWeight(b);
      if (wa !== wb) return wa - wb;
      var ta = String((a && a.merchant_time_relative_ar) || "");
      var tb = String((b && b.merchant_time_relative_ar) || "");
      return ta.localeCompare(tb, "ar");
    });
  }

  function allVisibleRows() {
    return (state.rows || []).concat(state.archived || []);
  }

  function filteredRows() {
    var pool = allVisibleRows();
    var out = [];
    for (var i = 0; i < pool.length; i++) {
      if (rowMatchesFilter(pool[i], state.filter)) out.push(pool[i]);
    }
    return sortQueue(out);
  }

  function findRow(key) {
    var k = String(key || "").trim();
    if (!k) return null;
    var pool = allVisibleRows();
    for (var i = 0; i < pool.length; i++) {
      if (recoveryKey(pool[i]) === k) return pool[i];
    }
    return null;
  }

  function countPrimary(rows) {
    var counts = {
      contact_customer: 0,
      follow_up_manually: 0,
      review_cart: 0,
      wait: 0,
      no_action_required: 0,
      reopen: 0,
      archive: 0,
      other: 0,
      total_active: 0,
    };
    (rows || []).forEach(function (mc) {
      if (!mc || isArchivedVisual(mc)) return;
      counts.total_active += 1;
      var key = String(resolvePrimary(mc).key || "").trim();
      if (Object.prototype.hasOwnProperty.call(counts, key)) counts[key] += 1;
      else counts.other += 1;
    });
    counts.needs_you =
      counts.contact_customer + counts.follow_up_manually + counts.review_cart;
    return counts;
  }

  function filterCounts() {
    var counts = { all: 0, attention: 0, nophone: 0, sent: 0, recovered: 0 };
    var rows = state.rows || [];
    counts.all = rows.filter(function (mc) {
      return !isArchivedVisual(mc);
    }).length;
    rows.forEach(function (mc) {
      var tabs = visibleTabs(mc);
      if (tabs.indexOf("attention") >= 0) counts.attention += 1;
      if (tabs.indexOf("nophone") >= 0) counts.nophone += 1;
      if (tabs.indexOf("sent") >= 0) counts.sent += 1;
      if (tabs.indexOf("recovered") >= 0 || isCompleted(mc)) counts.recovered += 1;
    });
    (state.archived || []).forEach(function () {
      counts.recovered += 1;
    });
    var payloadFc =
      (state.payload && state.payload.merchant_cart_filter_counts) || {};
    ["all", "attention", "nophone", "sent", "recovered"].forEach(function (k) {
      if (payloadFc[k] != null && isFinite(Number(payloadFc[k]))) {
        counts[k] = Number(payloadFc[k]);
      }
    });
    return counts;
  }

  function storeHasNoCarts(counts) {
    return (
      !state.loading &&
      !state.error &&
      !(counts && counts.total_active) &&
      !(state.archived || []).length
    );
  }

  function orientationCopy(counts) {
    if (state.error) {
      return {
        mode: "failure",
        headline: "تعذّر تحميل السلال",
        detail: "أعد المحاولة. لم نُنشئ سلالاً بديلة.",
      };
    }
    if (state.loading && !counts.total_active) {
      return {
        mode: "loading",
        headline: "جاري تحميل السلال…",
        detail: "",
      };
    }
    if (storeHasNoCarts(counts)) {
      return {
        mode: "empty",
        headline: "لا يوجد عمل تشغيلي الآن",
        detail: "",
      };
    }
    if (counts.needs_you > 0) {
      return {
        mode: "needs_you",
        headline:
          counts.needs_you === 1
            ? "سلة واحدة تحتاج تدخلك الآن"
            : counts.needs_you + " سلال تحتاج تدخلك الآن",
        detail: "",
      };
    }
    if (counts.wait > 0) {
      return {
        mode: "waiting",
        headline: "لا توجد سلال تحتاج تدخلك الآن",
        detail:
          "CartFlow يتابع " +
          counts.wait +
          (counts.wait === 1 ? " سلة." : " سلال."),
      };
    }
    if (counts.no_action_required > 0 || (state.archived || []).length) {
      return {
        mode: "completed",
        headline: "لا توجد سلال تحتاج تدخلك الآن",
        detail: "السلال الحالية مكتملة أو مؤرشفة.",
      };
    }
    return {
      mode: "calm",
      headline: "لا توجد سلال تحتاج تدخلك الآن",
      detail: "",
    };
  }

  function emptyCopy(list, counts) {
    if (state.error) {
      return {
        title: "تعذّر تحميل الطابور",
        body: "فشل جزئي — أعد المحاولة. لا بيانات مخترعة.",
      };
    }
    if (state.loading) {
      return { title: "جاري تحميل السلال…", body: "" };
    }
    if (storeHasNoCarts(counts)) {
      return null;
    }
    if (state.filter === "attention" && counts.needs_you === 0) {
      return {
        title: "لا توجد سلال تحتاج تدخلك الآن",
        body: "السلال الموجودة بانتظار النظام أو مكتملة.",
      };
    }
    if (state.filter === "nophone" || state.filter === "sent") {
      return {
        title: "لا توجد سلال في حالة الانتظار هذه",
        body: "بدّل التصفية لرؤية ما يحتاجك أو ما اكتمل.",
      };
    }
    if (state.filter === "recovered") {
      return {
        title: "لا توجد سلال مكتملة",
        body: "لا شراء مؤكد أو أرشيف للعرض الآن.",
      };
    }
    if (list.length === 0) {
      return { title: "لا سلال في هذه التصفية", body: "" };
    }
    return null;
  }

  function queueWeightClass(mc) {
    var pa = resolvePrimary(mc);
    if (isArchivedVisual(mc)) return "is-archived";
    if (isPurchased(mc) || pa.key === "no_action_required") return "is-terminal";
    if (ACTIONABLE[pa.key]) return "is-actionable";
    if (pa.key === "wait") return "is-waiting";
    return "is-quiet";
  }

  function primaryActionHtml(mc) {
    var pa = resolvePrimary(mc);
    var key = pa.key;
    var label = pa.label;
    var rk = recoveryKey(mc);
    var href = contactHref(mc);

    if (key === "contact_customer" || key === "follow_up_manually") {
      if (href) {
        return (
          '<a class="cf2-btn cf2-carts__primary" href="' +
          esc(href) +
          '" target="_blank" rel="noopener noreferrer" data-cf-primary-action="' +
          esc(key) +
          '">' +
          esc(label) +
          "</a>"
        );
      }
      return (
        '<span class="cf2-btn cf2-btn--secondary cf2-carts__primary" data-cf-primary-action="' +
        esc(key) +
        '" aria-disabled="true">' +
        esc(label) +
        "</span>"
      );
    }
    if (key === "reopen") {
      if (!rk) return "";
      return (
        '<button type="button" class="cf2-btn cf2-carts__primary" data-lc-reopen data-recovery-key="' +
        esc(rk) +
        '" data-cf-primary-action="reopen">' +
        esc(label) +
        "</button>"
      );
    }
    return (
      '<span class="cf2-btn cf2-btn--secondary cf2-carts__primary" data-cf-primary-action="' +
      esc(key) +
      '">' +
      esc(label) +
      "</span>"
    );
  }

  function secondaryActionHtml(mc) {
    var pa = resolvePrimary(mc);
    var rk = recoveryKey(mc);
    if (!rk) return "";
    if (isPurchased(mc) || isCompleted(mc)) return "";
    if (
      pa.key !== "archive" &&
      pa.key !== "reopen" &&
      pa.secondary_demoted &&
      pa.secondary_key === "archive"
    ) {
      return (
        '<button type="button" class="cf2-btn cf2-btn--quiet cf2-carts__secondary" data-lc-archive data-recovery-key="' +
        esc(rk) +
        '" data-cf-lifecycle-secondary="archive">إغلاق الحالة</button>'
      );
    }
    return "";
  }

  function timelineHtml(mc) {
    var events = [];
    var ps = mc && mc.merchant_proof_surface_v1;
    if (ps && ps.version === "v1") {
      if (ps.why_we_know_ar) {
        events.push({
          kicker: "حالة",
          label: String(ps.why_we_know_ar),
          meta: "",
        });
      }
      var steps = ps.recovery_steps || [];
      for (var i = steps.length - 1; i >= 0; i--) {
        var st = steps[i];
        if (!st || !st.label_ar) continue;
        var stLabel =
          PROOF_STEP_STATE_AR[String(st.state || "").trim()] || st.state || "";
        events.push({
          kicker: "",
          label: String(st.label_ar),
          meta: stLabel + (st.note_ar ? " · " + st.note_ar : ""),
        });
      }
    }
    if (mc && mc.customer_movement_line_ar) {
      events.push({
        kicker: mc.customer_movement_heading_ar || "حركة العميل",
        label: String(mc.customer_movement_line_ar),
        meta: "",
      });
    }
    var life =
      (mc &&
        (mc.customer_lifecycle_continuation_explanation_ar ||
          mc.normal_recovery_continuation_explanation_ar)) ||
      "";
    if (String(life).trim()) {
      events.push({ kicker: "", label: String(life).trim(), meta: "" });
    }
    if (!events.length) {
      return '<p class="cf2-carts__timeline-empty">لا يوجد سجل تشغيلي إضافي لهذه السلة.</p>';
    }
    return events
      .map(function (ev) {
        return (
          '<li class="cf2-carts__tl-item">' +
          (ev.kicker
            ? '<span class="cf2-carts__tl-kicker">' + esc(ev.kicker) + "</span>"
            : "") +
          '<span class="cf2-carts__tl-label">' +
          esc(ev.label) +
          "</span>" +
          (ev.meta
            ? '<span class="cf2-carts__tl-meta">' + esc(ev.meta) + "</span>"
            : "") +
          "</li>"
        );
      })
      .join("");
  }

  function queueItemHtml(mc, selected) {
    var rk = recoveryKey(mc);
    var pa = resolvePrimary(mc);
    var weight = queueWeightClass(mc);
    var value = money(mc);
    var when = timeLine(mc);
    var title = cartTitle(mc);
    var product = productLine(mc);
    var stateText = attentionLabel(mc) || pa.label;
    var whyText = whyInQueue(mc);
    var phoneBit = "";
    if (!phoneAvailable(mc) && (pa.key === "follow_up_manually" || rowMatchesFilter(mc, "nophone"))) {
      phoneBit = '<span class="cf2-carts__chip cf2-carts__chip--wait">لا يوجد رقم</span>';
    }
    var vipBit = isVipOperational(mc)
      ? '<span class="cf2-carts__chip cf2-carts__chip--vip">VIP</span>'
      : "";
    return (
      '<button type="button" class="cf2-carts__row ' +
      weight +
      (selected ? " is-selected" : "") +
      '" data-recovery-key="' +
      esc(rk) +
      '" data-cf-primary-action="' +
      esc(pa.key) +
      '">' +
      '<span class="cf2-carts__row-main">' +
      '<span class="cf2-carts__who">' +
      esc(title) +
      "</span>" +
      (product && product !== title
        ? '<span class="cf2-carts__product">' + esc(product) + "</span>"
        : "") +
      (whyText && whyText !== stateText
        ? '<span class="cf2-carts__why">' + esc(whyText) + "</span>"
        : "") +
      "</span>" +
      '<span class="cf2-carts__row-meta">' +
      '<span class="cf2-carts__state">' +
      esc(stateText) +
      "</span>" +
      (when ? '<span class="cf2-carts__time">' + esc(when) + "</span>" : "") +
      (value ? '<span class="cf2-carts__value">' + esc(value) + "</span>" : "") +
      vipBit +
      phoneBit +
      '<span class="cf2-carts__next">' +
      esc(pa.label) +
      "</span>" +
      "</span></button>"
    );
  }

  function filtersHtml(fc) {
    return FILTERS.map(function (f) {
      var n = fc[f.key];
      var count =
        n != null && isFinite(Number(n)) ? '<span class="cf2-carts__fc">' + Number(n) + "</span>" : "";
      return (
        '<button type="button" class="cf2-carts__filter' +
        (state.filter === f.key ? " is-active" : "") +
        '" data-carts-filter="' +
        esc(f.key) +
        '" aria-pressed="' +
        (state.filter === f.key ? "true" : "false") +
        '">' +
        esc(f.label) +
        count +
        "</button>"
      );
    }).join("");
  }

  function detailHtml(mc) {
    if (!mc) {
      return (
        '<div class="cf2-carts__detail-empty">' +
        "<p>اختر سلة من الطابور.</p>" +
        "</div>"
      );
    }
    var pa = resolvePrimary(mc);
    var title = cartTitle(mc);
    var product = productLine(mc);
    var value = money(mc);
    var when = timeLine(mc);
    var purchased = isPurchased(mc);
    var vip = isVipOperational(mc)
      ? '<span class="cf2-carts__chip cf2-carts__chip--vip">VIP — تعامل تشغيلي</span>'
      : "";
    var phone = phoneAvailable(mc)
      ? ""
      : '<p class="cf2-carts__ctx-line">رقم العميل غير متوفر</p>';
    return (
      '<div class="cf2-carts__detail-inner" data-recovery-key="' +
      esc(recoveryKey(mc)) +
      '">' +
      '<button type="button" class="cf2-btn cf2-btn--quiet cf2-carts__back" data-carts-back>العودة للطابور</button>' +
      '<p class="cf2-carts__detail-state' +
      (purchased ? " is-purchased" : "") +
      '">' +
      esc(attentionLabel(mc) || pa.label) +
      "</p>" +
      '<div class="cf2-carts__action-block">' +
      primaryActionHtml(mc) +
      secondaryActionHtml(mc) +
      "</div>" +
      '<div class="cf2-carts__ctx">' +
      "<h3>" +
      esc(title) +
      "</h3>" +
      (product && product !== title
        ? '<p class="cf2-carts__ctx-line">' + esc(product) + "</p>"
        : "") +
      (value ? '<p class="cf2-carts__ctx-line">' + esc(value) + "</p>" : "") +
      (when ? '<p class="cf2-carts__ctx-line">' + esc(when) + "</p>" : "") +
      phone +
      vip +
      "</div>" +
      '<details class="cf2-carts__timeline">' +
      "<summary>ماذا حدث لهذه السلة؟</summary>" +
      '<ol class="cf2-carts__tl">' +
      timelineHtml(mc) +
      "</ol></details>" +
      "</div>"
    );
  }

  function paint() {
    var root = state.root;
    if (!root) return;
    var counts = countPrimary(state.rows);
    var fc = filterCounts();
    var orient = orientationCopy(counts);
    var list = filteredRows();
    if (
      state.filter === "attention" &&
      counts.needs_you === 0 &&
      counts.total_active > 0 &&
      !state.detailOpen
    ) {
      /* keep filter; empty attention is a valid calm queue */
    }
    var selected = findRow(state.selectedKey);
    if (!selected && list.length && !isMobile()) {
      selected = list[0];
      state.selectedKey = recoveryKey(selected);
    }
    if (selected && list.indexOf(selected) < 0 && state.filter !== "all") {
      /* keep selected even if filtered out on desktop? no — stay truthful to filter */
      if (!rowMatchesFilter(selected, state.filter)) {
        selected = list[0] || null;
        state.selectedKey = selected ? recoveryKey(selected) : "";
      }
    }
    if (storeHasNoCarts(counts)) {
      root.setAttribute("data-cf2", MARKER);
      root.setAttribute("data-carts-empty", "store");
      root.className = "cf2-carts is-empty";
      root.innerHTML =
        '<div class="cf2-carts__orient">' +
        '<p class="cf2-carts__orient-h">' +
        esc(orient.headline) +
        "</p></div>";
      bind(root);
      return;
    }

    var empty = emptyCopy(list, counts);
    var queueInner = empty
      ? '<div class="cf2-carts__empty" data-carts-empty="' +
        esc(orient.mode) +
        '"><p class="cf2-carts__empty-title">' +
        esc(empty.title) +
        '</p><p class="cf2-carts__empty-body">' +
        esc(empty.body) +
        "</p></div>"
      : list
          .map(function (mc) {
            return queueItemHtml(mc, selected && recoveryKey(mc) === recoveryKey(selected));
          })
          .join("");

    root.setAttribute("data-cf2", MARKER);
    root.removeAttribute("data-carts-empty");
    root.className =
      "cf2-carts" +
      (state.detailOpen ? " is-detail-open" : "") +
      (orient.mode ? " is-" + orient.mode : "");
    root.innerHTML =
      '<div class="cf2-carts__orient">' +
      '<p class="cf2-carts__orient-h">' +
      esc(orient.headline) +
      "</p>" +
      (orient.detail
        ? '<p class="cf2-carts__orient-d">' + esc(orient.detail) + "</p>"
        : "") +
      '<div class="cf2-carts__filters" role="toolbar" aria-label="تصفية تشغيلية">' +
      filtersHtml(fc) +
      "</div></div>" +
      '<div class="cf2-carts__workspace">' +
      '<div class="cf2-carts__queue" aria-label="طابور السلال">' +
      queueInner +
      "</div>" +
      '<div class="cf2-carts__detail" aria-label="تفاصيل السلة">' +
      detailHtml(selected) +
      "</div></div>";
    bind(root);
  }

  function isMobile() {
    return window.matchMedia && window.matchMedia("(max-width: 1023px)").matches;
  }

  function selectCart(key) {
    state.selectedKey = String(key || "").trim();
    if (isMobile()) state.detailOpen = true;
    paint();
  }

  function closeDetail() {
    state.detailOpen = false;
    paint();
  }

  function setFilter(key) {
    var next = String(key || "all").trim();
    var known = FILTERS.some(function (f) {
      return f.key === next;
    });
    if (!known) next = "all";
    state.filter = next;
    state.filterTouched = true;
    state.detailOpen = false;
    paint();
  }

  function lifecyclePayload(mc, rk) {
    var slug = mc && mc.store_slug ? String(mc.store_slug).trim() : "";
    if (!slug && rk.indexOf(":") >= 0) slug = rk.split(":")[0].trim();
    var rowId = mc && (mc.merchant_case_row_id || mc.id);
    return {
      recovery_key: rk,
      store_slug: slug,
      abandoned_cart_id: rowId != null ? rowId : null,
      session_id: mc && mc.session_id ? String(mc.session_id).trim() : "",
      cart_id: mc && mc.cart_id ? String(mc.cart_id).trim() : "",
    };
  }

  function postLifecycle(path, mc, rk, btn) {
    if (btn) btn.disabled = true;
    fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(lifecyclePayload(mc, rk)),
    })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (btn) btn.disabled = false;
        if (d && d.ok) {
          loadAndPaint(state.root);
        }
      })
      .catch(function () {
        if (btn) btn.disabled = false;
      });
  }

  function bind(root) {
    root.querySelectorAll("[data-carts-filter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setFilter(btn.getAttribute("data-carts-filter"));
      });
    });
    root.querySelectorAll(".cf2-carts__row").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectCart(btn.getAttribute("data-recovery-key"));
      });
    });
    root.querySelectorAll("[data-carts-back]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        closeDetail();
      });
    });
    root.querySelectorAll("[data-lc-archive]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var rk = btn.getAttribute("data-recovery-key") || "";
        var mc = findRow(rk);
        if (!rk || !mc) return;
        postLifecycle("/api/dashboard/cart-lifecycle/archive", mc, rk, btn);
      });
    });
    root.querySelectorAll("[data-lc-reopen]").forEach(function (btn) {
      btn.addEventListener("click", function (e) {
        e.stopPropagation();
        var rk = btn.getAttribute("data-recovery-key") || "";
        var mc = findRow(rk);
        if (!rk || !mc) return;
        postLifecycle("/api/dashboard/cart-lifecycle/reopen", mc, rk, btn);
      });
    });
  }

  function extractRows(d) {
    if (!d || typeof d !== "object") return [];
    return d.merchant_carts_page_rows || d.rows || [];
  }

  function extractArchived(d) {
    if (!d || typeof d !== "object") return [];
    return d.merchant_archived_carts_page_rows || [];
  }

  function ingest(d) {
    state.payload = d || {};
    state.rows = extractRows(d);
    state.archived = extractArchived(d);
    var counts = countPrimary(state.rows);
    if (!state.filterTouched) {
      if (counts.needs_you > 0) state.filter = "attention";
      else if (counts.total_active === 0 && (state.archived || []).length) {
        state.filter = "recovered";
      } else {
        state.filter = "all";
      }
    }
  }

  function loadAndPaint(root) {
    if (!root) return Promise.resolve();
    state.root = root;
    state.loading = true;
    state.error = "";
    paint();
    return fetch("/api/dashboard/normal-carts", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(function (r) {
        if (!r.ok) throw new Error("http_" + r.status);
        return r.json();
      })
      .then(function (d) {
        state.loading = false;
        ingest(d);
        paint();
      })
      .catch(function () {
        state.loading = false;
        state.error = "load_failed";
        paint();
      });
  }

  global.CartFlowUiV2Carts = {
    loadAndPaint: loadAndPaint,
    marker: MARKER,
    resolvePrimary: resolvePrimary,
    filters: FILTERS,
  };
})(window);
