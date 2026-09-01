/**
 * CartFlow Merchant UI V2 — Communication Product Composition V1.
 * Answers: ماذا حدث في التواصل مع العملاء، وما الذي يحتاج متابعتي الآن؟
 * Runtime truth only: send log + delivery + inbound-by-phone + needs_merchant_followup.
 * Page-Specific Semantic Composition V1: lifecycle continuum.
 * Not an inbox. Not a thread. Carts owns execution. Settings owns configuration.
 */
(function (global) {
  "use strict";

  var MARKER = "communication-product-composition-v1";
  var COMPOSITION = "page-specific-v1";
  var ORGANISM = "lifecycle-continuum";

  var FILTERS = [
    { key: "needs", label: "يحتاج متابعتي" },
    { key: "active", label: "جاري" },
    { key: "all", label: "السجل" },
  ];

  var CAT = {
    NEEDS_MERCHANT_RESPONSE: "NEEDS_MERCHANT_RESPONSE",
    AUTOMATED_BY_CARTFLOW: "AUTOMATED_BY_CARTFLOW",
    WAITING_FOR_CUSTOMER: "WAITING_FOR_CUSTOMER",
    BLOCKED_BY_CONFIGURATION: "BLOCKED_BY_CONFIGURATION",
    COMPLETED_OR_TERMINAL: "COMPLETED_OR_TERMINAL",
  };

  var CAT_RANK = {
    NEEDS_MERCHANT_RESPONSE: 0,
    BLOCKED_BY_CONFIGURATION: 1,
    AUTOMATED_BY_CARTFLOW: 2,
    WAITING_FOR_CUSTOMER: 3,
    COMPLETED_OR_TERMINAL: 4,
  };

  var CAT_LABEL = {
    NEEDS_MERCHANT_RESPONSE: "يحتاج متابعتي",
    AUTOMATED_BY_CARTFLOW: "CartFlow يتابع",
    WAITING_FOR_CUSTOMER: "بانتظار العميل",
    BLOCKED_BY_CONFIGURATION: "التواصل غير جاهز",
    COMPLETED_OR_TERMINAL: "مكتمل",
  };

  var state = {
    root: null,
    messages: [],
    followups: [],
    summary: null,
    items: [],
    filter: "all",
    selectedId: "",
    detailOpen: false,
    loading: false,
    error: "",
    filterTouched: false,
    fetchGen: 0,
  };

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function digits(s) {
    return String(s == null ? "" : s).replace(/\D/g, "");
  }

  function maskPhone(raw) {
    var d = digits(raw);
    if (d.length >= 4) return "•••• " + d.slice(-4);
    var shown = String(raw || "").trim();
    return shown || "—";
  }

  function phoneTail(raw) {
    var d = digits(raw);
    return d.length >= 4 ? d.slice(-4) : "";
  }

  function isPurchasedMessage(mr) {
    if (!mr) return false;
    var st = String(mr.customer_lifecycle_state || "").trim().toLowerCase();
    if (st === "completed" || st === "purchased") return true;
    var label = String(mr.customer_lifecycle_label_ar || "").trim();
    return /شراء|اشترى|مكتمل/.test(label);
  }

  function isFailedMessage(mr) {
    if (!mr) return false;
    var cls = String(mr.delivery_status_class || mr.status_row_class || "");
    if (cls.indexOf("failed") >= 0) return true;
    var out = String(mr.delivery_outcome_ar || mr.delivery_status_ar || "");
    return /تعذّر|فشل/.test(out);
  }

  function isDeliveredMessage(mr) {
    if (!mr) return false;
    var out = String(mr.delivery_outcome_ar || mr.delivery_status_ar || "");
    if (/تم التسليم|وصلت/.test(out)) return true;
    var steps = mr.delivery_timeline || [];
    var i;
    for (i = 0; i < steps.length; i++) {
      if (
        steps[i] &&
        steps[i].state === "reached" &&
        /تم التسليم|تم الاطلاع/.test(String(steps[i].label_ar || ""))
      ) {
        return true;
      }
    }
    return false;
  }

  function publicationCondition(summary) {
    var pub = summary && summary.merchant_publication_v1;
    return (pub && pub.communication_condition) || {};
  }

  function operationalTruth(summary) {
    var meif =
      summary &&
      summary.merchant_experience_integration_v1 &&
      summary.merchant_experience_integration_v1.pages &&
      summary.merchant_experience_integration_v1.pages.communication
        ? summary.merchant_experience_integration_v1.pages.communication
        : {};
    return meif.operational_truth || {};
  }

  function isConstrained(summary) {
    var cc = publicationCondition(summary);
    return !!(cc.constrained || cc.normal_forbidden);
  }

  function scheduleCount(summary) {
    return Number(operationalTruth(summary).recovery_schedules || 0) || 0;
  }

  function noPhoneCount(summary) {
    var ops = operationalTruth(summary);
    var n = Number(ops.no_phone_total || ops.missing_phone || 0) || 0;
    if (n) return n;
    var ht = summary && summary.home_teaser_inputs_v1;
    if (ht && ht.communication) {
      return Number(ht.communication.no_phone || 0) || 0;
    }
    return 0;
  }

  function matchFollowup(mr, followups) {
    var tail = phoneTail(mr && mr.phone_masked);
    if (!tail) return null;
    var i;
    for (i = 0; i < followups.length; i++) {
      if (phoneTail(followups[i].customer_phone) === tail) return followups[i];
    }
    return null;
  }

  function classifyMessage(mr, fu) {
    if (fu && String(fu.status || "") === "needs_merchant_followup") {
      return CAT.NEEDS_MERCHANT_RESPONSE;
    }
    if (isPurchasedMessage(mr)) return CAT.COMPLETED_OR_TERMINAL;
    if (isFailedMessage(mr)) return CAT.AUTOMATED_BY_CARTFLOW;
    if (mr && mr.customer_reply_ar) return CAT.WAITING_FOR_CUSTOMER;
    if (isDeliveredMessage(mr)) return CAT.WAITING_FOR_CUSTOMER;
    return CAT.AUTOMATED_BY_CARTFLOW;
  }

  function messageEvents(mr) {
    var ev = mr && Array.isArray(mr.communication_timeline) ? mr.communication_timeline : [];
    if (ev.length) return ev;
    var out = [];
    if (mr && (mr.sent_full_ar || mr.time_ar)) {
      out.push({
        label_ar: "تم إرسال " + (mr.message_type_ar || "رسالة استرداد"),
        at_ar: mr.sent_full_ar || mr.time_ar || "",
      });
    }
    if (mr && mr.delivery_outcome_ar) {
      out.push({ label_ar: String(mr.delivery_outcome_ar), at_ar: mr.time_ar || "" });
    }
    if (mr && mr.customer_reply_ar) {
      out.push({
        label_ar: "رد العميل",
        at_ar: mr.customer_reply_at_ar || "",
      });
    }
    return out;
  }

  function itemFromMessage(mr, fu) {
    var cat = classifyMessage(mr, fu);
    var failed = isFailedMessage(mr);
    var purchased = isPurchasedMessage(mr);
    var status =
      cat === CAT.NEEDS_MERCHANT_RESPONSE
        ? "يحتاج متابعتك"
        : purchased
          ? "التواصل توقف بعد اكتمال الشراء"
          : failed
            ? mr.delivery_outcome_ar || "تعذّر الإرسال"
            : mr.delivery_outcome_ar || mr.delivery_status_ar || CAT_LABEL[cat];
    return {
      id: "msg-" + String(mr.log_id || mr.recovery_key || mr.phone_masked || "row"),
      kind: "message",
      category: cat,
      titleAr: mr.message_type_ar || mr.title_ar || "رسالة استرداد",
      statusAr: status,
      whenAr: mr.time_ar || mr.sent_full_ar || "",
      phoneMasked: mr.phone_masked || "—",
      cartRef: mr.cart_reference_ar || mr.cart_id || "",
      recoveryKey: mr.recovery_key || "",
      needsMerchant: cat === CAT.NEEDS_MERCHANT_RESPONSE,
      automated: cat === CAT.AUTOMATED_BY_CARTFLOW,
      failed: failed,
      purchased: purchased,
      noPhone: false,
      events: messageEvents(mr),
      outboundText: mr.full_message_ar || mr.preview_ar || "",
      inboundText: (fu && fu.inbound_message) || mr.customer_reply_ar || "",
      deliveryAr: mr.delivery_outcome_ar || mr.delivery_status_ar || "",
      followupId: fu && fu.id,
    };
  }

  function itemFromFollowup(fr) {
    return {
      id: "fu-" + String(fr.id || fr.customer_phone || ""),
      kind: "followup",
      category: CAT.NEEDS_MERCHANT_RESPONSE,
      titleAr: "رد العميل",
      statusAr: "يحتاج متابعتك",
      whenAr: fr.replied_at || "",
      phoneMasked: maskPhone(fr.customer_phone),
      cartRef: "",
      recoveryKey: "",
      needsMerchant: true,
      automated: false,
      failed: false,
      purchased: false,
      noPhone: false,
      events: [
        {
          label_ar: fr.inbound_message
            ? "رد وارد من العميل"
            : "تفاعل العميل",
          at_ar: fr.replied_at || "",
        },
      ],
      outboundText: "",
      inboundText: fr.inbound_message || fr.last_message_line_ar || "",
      deliveryAr: "",
      followupId: fr.id,
    };
  }

  function buildItems(messages, followups) {
    var usedFu = {};
    var items = [];
    var i;
    for (i = 0; i < messages.length; i++) {
      var mr = messages[i];
      var fu = matchFollowup(mr, followups);
      if (fu && fu.id != null) usedFu[String(fu.id)] = true;
      var built = itemFromMessage(mr, fu);
      if (!mr.log_id) built.id = built.id + "-" + i;
      items.push(built);
    }
    for (i = 0; i < followups.length; i++) {
      var fr = followups[i];
      if (fr && fr.id != null && usedFu[String(fr.id)]) continue;
      items.push(itemFromFollowup(fr));
    }
    items.sort(function (a, b) {
      var ra = CAT_RANK[a.category] != null ? CAT_RANK[a.category] : 9;
      var rb = CAT_RANK[b.category] != null ? CAT_RANK[b.category] : 9;
      if (ra !== rb) return ra - rb;
      return 0;
    });
    return items;
  }

  function needsCount() {
    return (state.followups || []).length;
  }

  function filteredItems() {
    return state.items.filter(function (it) {
      if (state.filter === "needs") return it.category === CAT.NEEDS_MERCHANT_RESPONSE;
      if (state.filter === "active") {
        return (
          it.category === CAT.AUTOMATED_BY_CARTFLOW ||
          it.category === CAT.WAITING_FOR_CUSTOMER ||
          it.category === CAT.BLOCKED_BY_CONFIGURATION
        );
      }
      return true;
    });
  }

  function findItem(id) {
    var key = String(id || "");
    var i;
    for (i = 0; i < state.items.length; i++) {
      if (state.items[i].id === key) return state.items[i];
    }
    return null;
  }

  function orientationCopy() {
    if (state.error === "load_failed") {
      return {
        mode: "degraded",
        headline: "تعذّر تأكيد حالة التواصل",
        detail: "لا نعرض هدوءاً افتراضياً.",
      };
    }
    var n = needsCount();
    var constrained = isConstrained(state.summary);
    var schedules = scheduleCount(state.summary);
    var noPhone = noPhoneCount(state.summary);
    if (n > 0) {
      return {
        mode: "needs",
        headline:
          n === 1
            ? "توجد حالة واحدة تحتاج متابعتك الآن"
            : "توجد " + n + " حالات تحتاج متابعتك الآن",
        detail: "Communication يوضح الحاجة. التنفيذ في السلال.",
      };
    }
    if (constrained) {
      return {
        mode: "blocked",
        headline: "التواصل غير جاهز",
        detail: publicationCondition(state.summary).summary_ar || "يلزم ضبط القناة قبل الإرسال.",
      };
    }
    if (!state.items.length) {
      return {
        mode: "empty",
        headline: "لا توجد أحداث تواصل بعد",
        detail: "عندما يُرسل CartFlow رسالة استرداد ستظهر هنا.",
      };
    }
    if (schedules > 0) {
      return {
        mode: "automated",
        headline: "لا يوجد ما يحتاج متابعتك الآن",
        detail: "CartFlow يتابع الإرسال تلقائياً.",
      };
    }
    if (noPhone > 0) {
      return {
        mode: "calm",
        headline: "لا يوجد ما يحتاج متابعتك الآن",
        detail: "بعض السلال بلا رقم — هذا ليس متابعة تجارية.",
      };
    }
    return {
      mode: "calm",
      headline: "لا يوجد ما يحتاج متابعتك الآن",
      detail: "",
    };
  }

  function emptyCopy(list, orient) {
    if (state.loading) {
      return { title: "جاري تحميل أحداث التواصل…", body: "" };
    }
    if (state.error === "load_failed") {
      return { title: "تعذّر تحميل سجل التواصل", body: "أعد المحاولة بعد قليل." };
    }
    if (list.length) return null;
    if (state.filter === "needs") {
      return {
        title: "لا يوجد ما يحتاج متابعتك",
        body: "CartFlow يتابع الحالات الآلية. السجل يبقى متاحاً.",
      };
    }
    if (orient.mode === "empty") {
      return { title: orient.headline, body: orient.detail };
    }
    return { title: "لا توجد عناصر في هذا العرض", body: orient.detail || "" };
  }

  function isMobile() {
    return window.matchMedia && window.matchMedia("(max-width: 1023px)").matches;
  }

  function rowTone(it) {
    if (it.needsMerchant) return "is-needs";
    if (it.purchased || it.category === CAT.COMPLETED_OR_TERMINAL) return "is-terminal";
    if (it.failed) return "is-failed";
    return "is-quiet";
  }

  /** Lifecycle stage from existing truth only — no invented events. */
  function lifecycleStage(it) {
    if (it.purchased || it.category === CAT.COMPLETED_OR_TERMINAL) return "closed";
    if (it.needsMerchant) return "followup";
    if (it.failed) return "broken";
    if (it.category === CAT.WAITING_FOR_CUSTOMER) return "wait";
    if (it.inboundText) return "response";
    if (it.deliveryAr || isDeliveredLike(it)) return "delivery";
    return "send";
  }

  function isDeliveredLike(it) {
    var d = String((it && it.deliveryAr) || "").toLowerCase();
    return d.indexOf("deliver") >= 0 || d.indexOf("وصل") >= 0 || d.indexOf("تسليم") >= 0;
  }

  /** Lifecycle marks from existing truth only — no invented future steps. */
  function lifecycleTicksHtml(stage) {
    var steps = ["send", "delivery", "response", "wait", "followup"];
    var active = steps.indexOf(stage);
    if (stage === "closed") active = steps.length - 1;
    if (stage === "broken") active = 1;
    var end = stage === "closed" ? steps.length : Math.max(active + 1, 1);
    var html =
      '<span class="cf2-comms__life" data-cf2-lifecycle="' +
      esc(stage) +
      '" data-cf2-life-count="' +
      end +
      '" aria-hidden="true">';
    steps.slice(0, end).forEach(function (step, i) {
      var cls = "cf2-comms__tick";
      if (stage === "broken" && i === 1) cls += " is-broken";
      else if (stage === "closed") cls += " is-complete";
      else if (i < active) cls += " is-complete";
      else if (i === active) cls += stage === "followup" ? " is-held" : " is-active";
      html +=
        '<span class="' +
        cls +
        '" data-cf2-tick="' +
        esc(step) +
        '"></span>';
    });
    html += "</span>";
    return html;
  }

  function continuumScaffoldHtml() {
    var steps = ["send", "delivery", "response", "wait", "followup"];
    return (
      '<div class="cf2-comms__continuum-scaffold" data-cf2-continuum="dormant" aria-hidden="true">' +
      steps
        .map(function (step) {
          return (
            '<span class="cf2-comms__tick" data-cf2-tick="' + esc(step) + '"></span>'
          );
        })
        .join("") +
      "</div>"
    );
  }

  function itemHtml(it, selected) {
    var stage = lifecycleStage(it);
    return (
      '<button type="button" class="cf2-comms__row cf2-comms__life-row ' +
      rowTone(it) +
      (selected ? " is-selected" : "") +
      '" data-comms-id="' +
      esc(it.id) +
      '" data-cf2-lifecycle="' +
      esc(stage) +
      '">' +
      lifecycleTicksHtml(stage) +
      '<span class="cf2-comms__row-main">' +
      '<span class="cf2-comms__who">' +
      esc(it.phoneMasked) +
      "</span>" +
      '<span class="cf2-comms__what">' +
      esc(it.titleAr) +
      "</span></span>" +
      '<span class="cf2-comms__row-meta">' +
      '<span class="cf2-comms__state">' +
      esc(it.statusAr) +
      "</span>" +
      (it.whenAr ? '<span class="cf2-comms__time">' + esc(it.whenAr) + "</span>" : "") +
      (it.automated
        ? '<span class="cf2-comms__chip cf2-comms__chip--own">CartFlow يتابع</span>'
        : "") +
      (it.needsMerchant
        ? '<span class="cf2-comms__chip cf2-comms__chip--needs">يحتاج متابعتي</span>'
        : "") +
      "</span>" +
      (it.cartRef
        ? '<span class="cf2-comms__ctx cf2-comms__ctx--ref">' + esc(it.cartRef) + "</span>"
        : "") +
      "</button>"
    );
  }

  function filtersHtml() {
    var n = needsCount();
    return FILTERS.map(function (f) {
      var count = "";
      if (f.key === "needs" && n) {
        count = '<span class="cf2-comms__fc">' + n + "</span>";
      }
      return (
        '<button type="button" class="cf2-comms__filter' +
        (state.filter === f.key ? " is-active" : "") +
        '" data-comms-filter="' +
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

  function eventsHtml(it) {
    var ev = it.events || [];
    if (!ev.length) {
      return '<p class="cf2-comms__muted">لا توجد أحداث تواصل مسجّلة لهذه الحالة.</p>';
    }
    return (
      '<ol class="cf2-comms__tl">' +
      ev
        .map(function (e) {
          return (
            '<li class="cf2-comms__tl-item">' +
            '<span class="cf2-comms__tl-label">' +
            esc(e.label_ar || "") +
            "</span>" +
            (e.at_ar
              ? '<span class="cf2-comms__tl-at">' + esc(e.at_ar) + "</span>"
              : "") +
            "</li>"
          );
        })
        .join("") +
      "</ol>"
    );
  }

  function handoffHtml(it) {
    if (it.purchased) {
      return '<p class="cf2-comms__terminal">لا إجراء استرداد بعد تأكيد الشراء.</p>';
    }
    if (it.needsMerchant) {
      return (
        '<div class="cf2-comms__handoff-terminus cf2-terminus is-held" data-cf2-wait="followup">' +
        '<p class="cf2-comms__handoff">هذه الحالة تحتاج متابعتك.</p>' +
        '<a class="cf2-btn" href="#carts">افتح المتابعة في السلال</a>' +
        "</div>"
      );
    }
    return "";
  }

  function detailHtml(it) {
    if (!it) {
      return (
        '<div class="cf2-comms__detail-empty"><p>اختر حدث تواصل من السجل.</p></div>'
      );
    }
    var inbound = it.inboundText
      ? '<div class="cf2-comms__fact"><h3>آخر رد وارد</h3><p>' +
        esc(it.inboundText) +
        "</p></div>"
      : "";
    var outbound =
      it.outboundText && it.outboundText !== "—"
        ? '<div class="cf2-comms__fact"><h3>نص أُرسل</h3><p>' +
          esc(it.outboundText) +
          "</p></div>"
        : "";
    return (
      '<div class="cf2-comms__detail-inner" data-comms-detail="' +
      esc(it.id) +
      '">' +
      '<button type="button" class="cf2-btn cf2-btn--quiet cf2-comms__back" data-comms-back>العودة للسجل</button>' +
      '<p class="cf2-comms__detail-state' +
      (it.needsMerchant ? " is-needs" : "") +
      (it.purchased ? " is-terminal" : "") +
      '">' +
      esc(it.statusAr) +
      "</p>" +
      '<p class="cf2-comms__detail-who">' +
      esc(it.phoneMasked) +
      (it.titleAr ? " · " + esc(it.titleAr) : "") +
      "</p>" +
      (it.deliveryAr
        ? '<p class="cf2-comms__ctx-line">حالة التسليم: ' +
          esc(it.deliveryAr) +
          "</p>"
        : "") +
      '<div class="cf2-comms__handoff-block">' +
      handoffHtml(it) +
      "</div>" +
      inbound +
      outbound +
      '<div class="cf2-comms__history"><h3>أحداث التواصل</h3>' +
      eventsHtml(it) +
      "</div></div>"
    );
  }

  function paint() {
    var root = state.root;
    if (!root) return;
    var orient = orientationCopy();
    var list = filteredItems();
    var selected = findItem(state.selectedId);
    if (!selected && list.length && !isMobile()) {
      selected = list[0];
      state.selectedId = selected.id;
    }
    if (selected && list.indexOf(selected) < 0 && state.filter !== "all") {
      selected = list[0] || null;
      state.selectedId = selected ? selected.id : "";
    }
    var empty = emptyCopy(list, orient);
    var listInner = empty
      ? continuumScaffoldHtml() +
        '<div class="cf2-comms__empty" data-comms-empty="' +
        esc(orient.mode) +
        '"><p class="cf2-comms__empty-title">' +
        esc(empty.title) +
        '</p><p class="cf2-comms__empty-body">' +
        esc(empty.body) +
        "</p></div>"
      : list
          .map(function (it) {
            return itemHtml(it, selected && it.id === selected.id);
          })
          .join("");

    var constraintLink = "";
    if (orient.mode === "blocked") {
      constraintLink =
        '<a class="cf2-comms__setup" href="#settings">ضبط التواصل</a>';
    }
    var nophoneLink = "";
    if (orient.mode === "calm" && noPhoneCount(state.summary) > 0 && needsCount() === 0) {
      nophoneLink =
        '<a class="cf2-comms__setup" href="#carts">عرض السلال بلا رقم</a>';
    }

    root.setAttribute("data-cf2", MARKER);
    root.setAttribute("data-cf2-organism", ORGANISM);
    root.setAttribute("data-cf2-composition", COMPOSITION);
    root.setAttribute("data-cf-needs-merchant-response", needsCount() > 0 ? "1" : "0");
    root.className =
      "cf2-comms" +
      (state.detailOpen ? " is-detail-open" : "") +
      (orient.mode ? " is-" + orient.mode : "");
    root.innerHTML =
      '<div class="cf2-comms__orient">' +
      '<p class="cf2-comms__orient-h">' +
      esc(orient.headline) +
      "</p>" +
      (orient.detail
        ? '<p class="cf2-comms__orient-d">' + esc(orient.detail) + "</p>"
        : "") +
      constraintLink +
      nophoneLink +
      '<div class="cf2-comms__filters" role="toolbar" aria-label="تصفية أحداث التواصل">' +
      filtersHtml() +
      "</div></div>" +
      '<div class="cf2-comms__workspace">' +
      '<div class="cf2-comms__list" aria-label="سجل التواصل">' +
      listInner +
      "</div>" +
      '<div class="cf2-comms__detail" aria-label="تاريخ التواصل">' +
      detailHtml(selected) +
      "</div></div>";
    bind(root);
  }

  function bind(root) {
    root.querySelectorAll("[data-comms-filter]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setFilter(btn.getAttribute("data-comms-filter"));
      });
    });
    root.querySelectorAll("[data-comms-id]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        selectItem(btn.getAttribute("data-comms-id"));
      });
    });
    root.querySelectorAll("[data-comms-back]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        closeDetail();
      });
    });
  }

  function selectItem(id) {
    state.selectedId = String(id || "").trim();
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

  function ingest(bundle) {
    state.messages = (bundle.messages && bundle.messages.merchant_message_history_rows) || [];
    state.followups = (bundle.followups && bundle.followups.merchant_followup_rows) || [];
    state.summary = bundle.summary || null;
    state.items = buildItems(state.messages, state.followups);
    if (!state.filterTouched) {
      state.filter = needsCount() > 0 ? "needs" : "all";
    }
  }

  function fetchJson(url) {
    return fetch(url, { credentials: "same-origin", cache: "no-store" }).then(
      function (r) {
        if (!r.ok) throw new Error("http_" + r.status);
        return r.json();
      }
    );
  }

  function loadAndPaint(root) {
    if (!root) return Promise.resolve();
    state.root = root;
    state.loading = true;
    state.error = "";
    paint();
    var gen = ++state.fetchGen;
    return Promise.all([
      fetchJson("/api/dashboard/messages"),
      fetchJson("/api/dashboard/followups"),
      fetchJson("/api/dashboard/summary"),
    ])
      .then(function (parts) {
        if (gen !== state.fetchGen) return;
        state.loading = false;
        ingest({
          messages: parts[0],
          followups: parts[1],
          summary: parts[2],
        });
        paint();
      })
      .catch(function () {
        if (gen !== state.fetchGen) return;
        state.loading = false;
        state.error = "load_failed";
        paint();
      });
  }

  function applyPayloadAndPaint(root, bundle) {
    if (!root) return;
    state.root = root;
    state.loading = false;
    state.error = "";
    ingest(bundle || {});
    paint();
  }

  global.CartFlowUiV2Comms = {
    loadAndPaint: loadAndPaint,
    applyPayloadAndPaint: applyPayloadAndPaint,
    marker: MARKER,
    classifyMessage: classifyMessage,
    buildItems: buildItems,
    matchFollowup: matchFollowup,
    categories: CAT,
    filters: FILTERS,
  };
})(window);
