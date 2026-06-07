/**
 * Lazy-load قسم «قوالب حسب سبب التردد» — لا يُحمّل حتى الدخول للصفحة (#trigger-templates).
 */
(function () {
  "use strict";

  var FETCH_URL_GET = "/api/dashboard/trigger-templates";
  var FETCH_URL_POST = "/api/dashboard/trigger-templates";
  var lastPayload = null;

  /** حالة تحميل عالمية لتفادي سباق الطلبات / إعادة الجلب بين التنقل. */
  var MAX_DOM_READY_ATTEMPTS = 48;
  var DOM_POLL_MS = 50;

  if (typeof window.__trigger_templates_loading === "undefined") {
    window.__trigger_templates_loading = false;
  }
  if (typeof window.__trigger_templates_loaded === "undefined") {
    window.__trigger_templates_loaded = null;
  }
  if (typeof window.__trigger_templates_load_gen === "undefined") {
    window.__trigger_templates_load_gen = 0;
  }
  if (typeof window.__trigger_templates_apply_gen === "undefined") {
    window.__trigger_templates_apply_gen = 0;
  }
  if (typeof window.__trigger_templates_dom_ready === "undefined") {
    window.__trigger_templates_dom_ready = false;
  }

  /** طلب GET نشط — يُلغى عند بدء جلب أحدث (لا تكديس طلبات). */
  var tplGetAbort = null;
  /** مفتاح السبب → حفظ قيد التنفيذ (نقرة واحدة = POST واحد). */
  var tplSaveInFlight = {};
  var tplMetrics = {
    save_clicks: 0,
    save_handler_invokes: 0,
    save_posts_started: 0,
    save_in_flight_keys: 0,
    get_fetches_started: 0,
    get_in_flight: 0,
    render_applied: 0,
    render_stale_skipped: 0,
    save_click_handlers: 0,
  };

  /** معرّفات ثابتة لمسار الحفظ الوحيد — للتشخيص في وحدة التحكم. */
  var TPL_SAVE_HANDLER = {
    name: "onMaTplRootClick",
    id: "ma_tpl_root_delegate_v1",
  };

  /** ترتيب ثابت يطابق الخادم عند الحاجة لبطاقات احتياطية. */
  var TRIGGER_KEYS_ORDER = [
    "price",
    "quality",
    "shipping",
    "delivery",
    "warranty",
    "other",
  ];

  var LABEL_BY_KEY = {
    price: "السعر",
    quality: "الجودة",
    shipping: "الشحن",
    delivery: "مدة التوصيل",
    warranty: "الضمان",
    other: "سبب آخر",
  };

  /**
   * Recovery Trigger Templates — مسودات واجهة ‎#/trigger-templates‎ فقط.
   * Independent recovery/WhatsApp templates (تُحفظ في ‎reason_templates.message‎ / ‎messages‎).
   * Future hook: Product Intelligence / Offer Control — استبدال نصي حسب القواعد.
   * Do NOT connect to CartFlow Widget hesitation labels — الودجيت يعرض كتالوجًا ثابتًا من لوحة المتجر؛ لا حقول تنصيط.
   * التنفيذ الحالي نص ثابت فقط؛ صفر استعلامات إضافية.
   */
  var PRESET_SUGGESTIONS_BY_REASON = {
    price: [
      {
        type: "reassurance",
        label: "طمأنة",
        text: "نعرف إن السعر قرار مهم 👍 إذا عندك استفسار عن السعر أو الدفع نوضحه بسرعة.",
      },
      {
        type: "offer",
        label: "عرض / كود خصم",
        text: "عندنا عرض ممكن يساعدك تكمل الطلب، تحب نرسل لك التفاصيل؟",
      },
      {
        type: "alternative",
        label: "بديل / باكج",
        text: "عندنا خيارات بديلة أو باكج قد يفيدك أكثر 👍 نقدر نلخّصها لك بسرعة إذا حاب.",
      },
    ],
    quality: [
      {
        type: "reassurance",
        label: "طمأنة",
        text: "نحب نطمنك 👍 إذا عندك أي سؤال عن جودة المنتج أو تفاصيله نوضحها لك باختصار.",
      },
      {
        type: "specs",
        label: "شرح المواصفات",
        text: "نقدر نشرح لك أهم المواصفات بجمل بسيطة تسهّل القرار بدون تعقيد.",
      },
      {
        type: "social_proof",
        label: "تجارب العملاء",
        text: "كثير من عملائنا اختاروا نفس المنتج برضا 👍 إذا حاب نعطيك فكرة سريعة عن التجارب.",
      },
    ],
    shipping: [
      {
        type: "shipping_info",
        label: "توضيح المدة",
        text: "نوضح لك خيارات الشحن والتكلفة بكل اختصار 👍",
      },
      {
        type: "shipping_offer",
        label: "شحن مجاني / عرض شحن",
        text: "إذا يتوفر شحن مجاني أو عرض شحن يناسبك، نشرح لك الشروط باختصار بدون التزام منك الآن.",
      },
      {
        type: "shipping_update",
        label: "تحديث الشحن",
        text: "إذا حاب، نوضح لك آخر تحديثات الشحن أو الخيارات المتاحة بسرعة 👍",
      },
    ],
    delivery: [
      {
        type: "shipping_info",
        label: "توضيح الموعد",
        text: "نقدر نوضح لك مدة التوصيل المتوقعة قبل ما تكمل الطلب 👍",
      },
      {
        type: "offer",
        label: "تسريع إن أمكن",
        text: "إذا فيه خيار أسرع أو أقرب لموعدك، نوضح لك المتاح باختصار.",
      },
      {
        type: "delivery_update",
        label: "تحديث الموعد",
        text: "إذا حاب، نوضح لك آخر موعد متوقع أو أي تحديث يفيد قرارك 👍",
      },
    ],
    warranty: [
      {
        type: "reassurance",
        label: "طمأنة",
        text: "نوضح لك تفاصيل الضمان أو الاستبدال بكل بساطة 👍",
      },
      {
        type: "warranty_info",
        label: "شرح الضمان",
        text: "نلخّصلك أهم بنود الضمان بجمل قصيرة تفيدك قبل إكمال الطلب.",
      },
      {
        type: "alternative",
        label: "استبدال / إرجاع",
        text: "إذا تحتاج خيار استبدال أو إرجاع، نوضّح لك الخطوات ببساطة بدون إرباك.",
      },
    ],
    other: [
      {
        type: "reassurance",
        label: "مساعدة عامة",
        text: "نقدر نساعدك بأي استفسار قبل إكمال الطلب 👍",
      },
      {
        type: "specs",
        label: "سؤال مفتوح",
        text: "وش اللي يوقفك الآن؟ اكتب لنا باختصار ونجاوبك بطريقة مفتوحة وواضحة.",
      },
      {
        type: "special_followup",
        label: "متابعة خاصة",
        text: "نقدر متابعة خاصة معك لين ترتاح وتكمّل براحة.",
      },
    ],
  };

  /** مقترحات تأخير المراحل — للعرض والبذر فقط (minute | hour | day). */
  var RECOMMENDED_STAGE_DELAYS = {
    price: [
      { value: 60, unit: "minute" },
      { value: 5, unit: "hour" },
      { value: 5, unit: "day" },
    ],
    quality: [
      { value: 90, unit: "minute" },
      { value: 8, unit: "hour" },
      { value: 5, unit: "day" },
    ],
    shipping: [
      { value: 30, unit: "minute" },
      { value: 4, unit: "hour" },
      { value: 2, unit: "day" },
    ],
    delivery: [
      { value: 30, unit: "minute" },
      { value: 6, unit: "hour" },
      { value: 3, unit: "day" },
    ],
    warranty: [
      { value: 2, unit: "hour" },
      { value: 12, unit: "hour" },
      { value: 5, unit: "day" },
    ],
    other: [
      { value: 3, unit: "hour" },
      { value: 1, unit: "day" },
      { value: 5, unit: "day" },
    ],
  };

  function recommendedDelayForStage(reasonKey, index) {
    var row = RECOMMENDED_STAGE_DELAYS[reasonKey] || [];
    var rec = row[index];
    if (rec && rec.value > 0) {
      return { value: rec.value, unit: rec.unit || "minute" };
    }
    return { value: 60, unit: "minute" };
  }

  function recommendedDelayEncodedForApi(reasonKey, index) {
    var rec = recommendedDelayForStage(reasonKey, index);
    return persistFirstSlotDelay(rec.value, rec.unit);
  }

  function isGenericLegacyDelay(index, delay, unit) {
    var u = unit || "minute";
    var d = parseFloat(delay);
    if (!(d > 0)) return false;
    if (u === "minute") {
      if (index === 0 && (d === 1 || d === 2)) return true;
      if (index > 0 && (d === 1 || d === 2 || d === 120)) return true;
    }
    if (u === "hour" && index === 0 && d === 1) return true;
    return false;
  }

  function textIsDefaultishForDelay(reasonKey, index, text, rowMessage) {
    var t = String(text || "").trim();
    if (!t && index === 0) {
      t = String(rowMessage || "").trim();
    }
    if (!t) return true;
    if (isLoadtestPlaceholder(t)) return true;
    var preset = presetTextForStage(reasonKey, index);
    if (preset && t === preset) return true;
    var offer = presetTextForStage(reasonKey, 1);
    if (offer && t === offer) return true;
    return false;
  }

  function stage1NeedsRepair(reasonKey, text) {
    var t = String(text || "").trim();
    if (!t) return false;
    if (isLoadtestPlaceholder(t)) return true;
    var offer = presetTextForStage(reasonKey, 1);
    if (offer && t === offer) return true;
    var stage2 = presetTextForStage(reasonKey, 2);
    if (stage2 && t === stage2) return true;
    return false;
  }

  function shouldApplyRecommendedDelay(reasonKey, index, had, txt, d, u, rowMessage) {
    if (!had) return true;
    if (isLoadtestPlaceholder(txt)) return true;
    if (index === 0) {
      return (
        stage1NeedsRepair(reasonKey, txt || rowMessage) &&
        isGenericLegacyDelay(index, d, u)
      );
    }
    return (
      isGenericLegacyDelay(index, d, u) &&
      textIsDefaultishForDelay(reasonKey, index, txt, rowMessage)
    );
  }

  function applyRecommendedDelaysToRow(reasonKey, row) {
    if (!row || !reasonKey) return row;
    var mc = parseInt(row.message_count, 10) || 1;
    mc = Math.max(1, Math.min(3, mc));
    var msgs = Array.isArray(row.messages) ? row.messages.slice() : [];
    var i;
    for (i = 0; i < mc; i++) {
      var had = i < msgs.length && msgs[i] && typeof msgs[i] === "object";
      var slot = had ? msgs[i] : {};
      var txt = String(slot.text || (i === 0 ? row.message : "") || "").trim();
      var d =
        typeof slot.delay === "number" ? slot.delay : parseFloat(slot.delay);
      var u = slot.unit || "minute";
      var apply = shouldApplyRecommendedDelay(
        reasonKey,
        i,
        had,
        txt,
        d,
        u,
        row.message
      );
      if (apply) {
        var enc = recommendedDelayEncodedForApi(reasonKey, i);
        var fillTxt = txt || presetTextForStage(reasonKey, i);
        msgs[i] = { delay: enc.delay, unit: enc.unit, text: fillTxt };
      }
    }
    row.messages = msgs;
    if (msgs[0]) {
      row.delay_value = msgs[0].delay;
      row.delay_unit = msgs[0].unit;
    }
    return row;
  }

  function normalizeReasonKey(key) {
    return String(key == null ? "" : key).trim().toLowerCase();
  }

  function displayDelayForStage(reasonKey, index) {
    var row = findRow(reasonKey);
    if (row && Array.isArray(row.messages) && row.messages[index]) {
      var slot = row.messages[index];
      var d =
        typeof slot.delay === "number" ? slot.delay : parseFloat(slot.delay);
      if (d > 0) {
        return displayDelayFromApi(d, normalizeApiDelayUnit(slot.unit));
      }
    }
    if (row && index === 0) {
      var topDv =
        typeof row.delay_value === "number"
          ? row.delay_value
          : parseFloat(row.delay_value);
      if (topDv > 0) {
        return displayDelayFromApi(topDv, normalizeApiDelayUnit(row.delay_unit));
      }
    }
    var rec = recommendedDelayForStage(reasonKey, index);
    return { value: rec.value, unit: rec.unit };
  }

  /** يحفظ تأخير/نص المرحلة النشطة في الذاكرة فقط (قبل التبديل أو الحفظ). */
  function patchActiveStageInLastPayload(cardShell, reasonKey) {
    if (!cardShell || !reasonKey) return;
    reasonKey = normalizeReasonKey(reasonKey);
    ensureLastPayloadShell();
    var row = findRow(reasonKey);
    if (!row) return;
    var ix = parseInt(cardShell.getAttribute("data-ma-tpl-active-stage") || "0", 10);
    if (!(ix >= 0)) ix = 0;
    var mc = getCardEnabledStageCount(cardShell);
    ix = Math.max(0, Math.min(mc - 1, ix));

    var dvi = cardShell.querySelector("[data-ma-tpl-delay]");
    var dsi = cardShell.querySelector("[data-ma-tpl-unit]");
    var ta = cardShell.querySelector("[data-ma-tpl-msg]");
    var dv = parseFloat(dvi && dvi.value ? dvi.value : "1") || 1;
    if (dv <= 0) dv = 1;
    var unit = normalizeUiDelayUnit(dsi && dsi.value ? dsi.value : "minute");
    var enc = persistFirstSlotDelay(dv, unit);
    var text = ta ? ta.value.trim() : "";
    if (!Array.isArray(row.messages)) row.messages = [];
    while (row.messages.length < mc) {
      row.messages.push({ delay: 60, unit: "minute", text: "" });
    }
    var prev =
      row.messages[ix] && typeof row.messages[ix] === "object"
        ? row.messages[ix]
        : {};
    row.messages[ix] = {
      delay: enc.delay,
      unit: enc.unit,
      text:
        text ||
        String(prev.text || "").trim() ||
        presetTextForStage(reasonKey, ix),
    };
    if (ix === 0) {
      row.delay_value = enc.delay;
      row.delay_unit = enc.unit;
      row.message = row.messages[0].text;
    }
  }

  /** استعادة التوقيت المقترح للمرحلة المحددة فقط — دون حفظ تلقائي. */
  function restoreRecommendedTimingForActiveStage(cardShell, reasonKey) {
    if (!cardShell || !reasonKey) return;
    var ix = parseInt(cardShell.getAttribute("data-ma-tpl-active-stage") || "0", 10);
    if (!(ix >= 0)) ix = 0;
    var mc = getCardEnabledStageCount(cardShell);
    ix = Math.max(0, Math.min(mc - 1, ix));

    var rec = recommendedDelayForStage(reasonKey, ix);
    var dvi = cardShell.querySelector("[data-ma-tpl-delay]");
    var dsi = cardShell.querySelector("[data-ma-tpl-unit]");
    if (dvi) dvi.value = String(rec.value);
    if (dsi) {
      dsi.value =
        rec.unit === "day" ? "day" : rec.unit === "hour" ? "hour" : "minute";
    }

    var row = findRow(reasonKey);
    if (row) {
      var enc = persistFirstSlotDelay(rec.value, rec.unit);
      if (!Array.isArray(row.messages)) row.messages = [];
      while (row.messages.length <= ix) {
        row.messages.push({ delay: enc.delay, unit: enc.unit, text: "" });
      }
      var prev =
        row.messages[ix] && typeof row.messages[ix] === "object"
          ? row.messages[ix]
          : {};
      var ta = cardShell.querySelector("[data-ma-tpl-msg]");
      var txt =
        (ta && ta.value.trim()) ||
        String(prev.text || "").trim() ||
        presetTextForStage(reasonKey, ix);
      row.messages[ix] = {
        delay: enc.delay,
        unit: enc.unit,
        text: txt,
      };
      if (ix === 0) {
        row.delay_value = enc.delay;
        row.delay_unit = enc.unit;
      }
    }
  }

  function stageLabelForIndex(p, index) {
    var n = index + 1;
    return "الرسالة " + n + " — " + (p && p.label ? p.label : "");
  }

  function stageRowTitle(p, index) {
    var n = index + 1;
    return "مرحلة " + n + " — " + (p && p.label ? p.label : "");
  }

  function stageTimingHintAr(index, enabledInRoute) {
    if (!enabledInRoute) {
      return "غير مفعلة — لن يستلمها العميل";
    }
    if (index === 0) {
      return "ترسل أولاً";
    }
    return "بعد تجاهل المرحلة السابقة";
  }

  function getCardEnabledStageCount(cardEl) {
    if (!cardEl) return 1;
    var mcSel = cardEl.querySelector("[data-ma-tpl-msg-count]");
    var n = parseInt(mcSel && mcSel.value ? mcSel.value : "1", 10) || 1;
    return Math.max(1, Math.min(3, n));
  }

  function buildStageCountHelpHtml(rowKey) {
    var list = PRESET_SUGGESTIONS_BY_REASON[rowKey] || [];
    if (!list.length) {
      return (
        '<p class="ma-tpl-stage-help">1 = مرحلة واحدة · 2 = مرحلتان متتابعتان · 3 = ثلاث مراحل — وليس تكراراً لنفس الرسالة.</p>'
      );
    }
    var lines = [];
    var i;
    for (i = 0; i < Math.min(3, list.length); i++) {
      var chain = [];
      var j;
      for (j = 0; j <= i; j++) {
        chain.push(list[j].label);
      }
      lines.push(i + 1 + " = " + chain.join(" → "));
    }
    return (
      '<p class="ma-tpl-stage-help" data-ma-tpl-stage-help>' +
      lines.join("<br>") +
      "</p>"
    );
  }

  function customerExperienceSummaryHtml(rowKey, enabledCount) {
    var list = PRESET_SUGGESTIONS_BY_REASON[rowKey] || [];
    if (!list.length) return "";
    var n = Math.max(1, Math.min(3, enabledCount || 1));
    var chain = [];
    var i;
    for (i = 0; i < n && i < list.length; i++) {
      chain.push(list[i].label);
    }
    return (
      '<p class="ma-tpl-customer-path" data-ma-tpl-customer-path dir="rtl">' +
      "<strong>ما يستلمه العميل:</strong> " +
      esc(chain.join(" ← ")) +
      (n < list.length
        ? ' <span class="ma-tpl-customer-path-muted">(المراحل التالية غير مفعّلة)</span>'
        : "") +
      "</p>"
    );
  }

  function stageWorkflowHtml(rowKey, enabledCount) {
    var list = PRESET_SUGGESTIONS_BY_REASON[rowKey] || [];
    if (!list.length) return "";
    var n = Math.max(1, Math.min(3, enabledCount || 1));
    var rows = [];
    var i;
    for (i = 0; i < list.length; i++) {
      var en = i < n;
      var timing = stageTimingHintAr(i, en);
      var sym = en ? "✓" : "—";
      rows.push(
        '<button type="button" class="ma-tpl-stage-row' +
        (en ? "" : " ma-tpl-stage-row--route-disabled") +
        '" data-ma-tpl-stage-select data-ma-tpl-reason="' +
        esc(rowKey) +
        '" data-ma-tpl-preset-i="' +
        i +
        '" data-ma-tpl-stage-route-enabled="' +
        (en ? "1" : "0") +
        '">' +
        '<span class="ma-tpl-stage-status" data-ma-tpl-stage-status aria-hidden="true">' +
        sym +
        "</span>" +
        '<span class="ma-tpl-stage-body">' +
        '<span class="ma-tpl-stage-title">' +
        esc(stageRowTitle(list[i], i)) +
        "</span>" +
        '<span class="ma-tpl-stage-timing">(' +
        esc(timing) +
        ")</span>" +
        "</span></button>"
      );
      if (i < list.length - 1) {
        rows.push('<span class="ma-tpl-stage-connector" aria-hidden="true">↓</span>');
      }
    }
    return (
      '<div class="ma-tpl-stage-workflow" data-ma-tpl-stage-workflow dir="rtl" aria-label="مسار المراحل بالترتيب">' +
      '<p class="ma-tpl-stage-workflow-title">مسار الإرسال (بالترتيب)</p>' +
      rows.join("") +
      "</div>"
    );
  }

  function sectionIntroHtml() {
    return (
      '<div class="ma-tpl-ownership-banner" dir="rtl">' +
      '<p class="ma-tpl-ownership-title">محتوى الاسترجاع</p>' +
      '<p class="ma-tpl-ownership-body">حدد محتوى رسائل الاسترجاع لكل سبب — وقم بإدارة مراحل المتابعة.</p>' +
      '<p class="ma-tpl-ownership-note">واتساب = قناة الإرسال · هذه الصفحة = محتوى الرسائل</p>' +
      "</div>" +
      '<div class="ma-tpl-seq-intro" dir="rtl">' +
      '<p class="ma-tpl-seq-intro-title">مسار الاسترجاع = سلسلة مراحل</p>' +
      '<p class="ma-tpl-seq-intro-body">كل رقم يفعّل مرحلة جديدة في التسلسل — <strong>وليس</strong> إرسال نفس الرسالة أكثر من مرة.</p>' +
      '<p class="ma-tpl-seq-intro-note">يتم الإرسال تدريجياً حسب تفاعل العميل. إذا عاد العميل أو اشترى، تتوقف الرسائل تلقائياً.</p>' +
      '<div class="ma-tpl-seq-chip-row" aria-hidden="true"><span class="ma-tpl-seq-chip">1</span><span class="ma-tpl-seq-chip-arrow">→</span><span class="ma-tpl-seq-chip">2</span><span class="ma-tpl-seq-chip-arrow">→</span><span class="ma-tpl-seq-chip">3</span></div>' +
      "</div>"
    );
  }

  function syncCardStageWorkflow(cardEl) {
    if (!cardEl) return;
    var n = getCardEnabledStageCount(cardEl);
    var rk = cardEl.getAttribute("data-ma-tpl-key") || "";
    var editIx = parseInt(cardEl.getAttribute("data-ma-tpl-active-stage") || "0", 10);
    if (!(editIx >= 0)) editIx = 0;

    var rows = cardEl.querySelectorAll("[data-ma-tpl-stage-select]");
    var i;
    for (i = 0; i < rows.length; i++) {
      var ix = parseInt(rows[i].getAttribute("data-ma-tpl-preset-i"), 10);
      var en = ix < n;
      rows[i].setAttribute("data-ma-tpl-stage-route-enabled", en ? "1" : "0");
      rows[i].classList.toggle("ma-tpl-stage-row--route-disabled", !en);
      rows[i].classList.toggle("ma-tpl-stage-row--route-active", en);
      rows[i].classList.toggle("ma-tpl-stage-row--editing", ix === editIx);
      var st = rows[i].querySelector("[data-ma-tpl-stage-status]");
      if (st) {
        st.textContent = en ? (ix === editIx ? "✓" : "○") : "—";
      }
      var timingEl = rows[i].querySelector(".ma-tpl-stage-timing");
      if (timingEl) {
        timingEl.textContent = "(" + stageTimingHintAr(ix, en) + ")";
      }
    }

    var pathEl = cardEl.querySelector("[data-ma-tpl-customer-path]");
    if (pathEl && rk) {
      var list = PRESET_SUGGESTIONS_BY_REASON[rk] || [];
      var chain = [];
      for (i = 0; i < n && i < list.length; i++) {
        chain.push(list[i].label);
      }
      var muted =
        n < list.length
          ? ' <span class="ma-tpl-customer-path-muted">(المراحل التالية غير مفعّلة)</span>'
          : "";
      pathEl.innerHTML =
        "<strong>ما يستلمه العميل:</strong> " +
        esc(chain.join(" ← ")) +
        muted;
    }

    var panel = cardEl.querySelector("[data-ma-tpl-editor-panel]");
    var banner = cardEl.querySelector("[data-ma-tpl-inactive-banner]");
    var ta = cardEl.querySelector("[data-ma-tpl-msg]");
    var editingDisabled = editIx >= n;
    if (panel) {
      panel.classList.toggle("ma-tpl-editor-panel--inactive-stage", editingDisabled);
    }
    if (banner) {
      banner.hidden = !editingDisabled;
    }
    if (ta) {
      ta.readOnly = editingDisabled;
      ta.setAttribute("aria-readonly", editingDisabled ? "true" : "false");
    }
  }

  function stageLabelForReasonIndex(reasonKey, index) {
    var list = PRESET_SUGGESTIONS_BY_REASON[reasonKey] || [];
    var p = list[index];
    if (p) return stageLabelForIndex(p, index);
    return "الرسالة " + (index + 1);
  }

  function isLoadtestPlaceholder(text) {
    return /LOADTEST_STORE_\d+/i.test(String(text == null ? "" : text).trim());
  }

  function presetTextForStage(reasonKey, index) {
    var presets = PRESET_SUGGESTIONS_BY_REASON[reasonKey] || [];
    if (presets[index] && presets[index].text) {
      return String(presets[index].text);
    }
    return "";
  }

  function messageTextForStage(reasonKey, index) {
    var row = findRow(reasonKey);
    var hasMsgs = row && Array.isArray(row.messages) && row.messages.length > 0;
    if (hasMsgs) {
      var slot = row.messages[index];
      if (slot && typeof slot === "object" && String(slot.text || "").trim()) {
        var fromSlot = String(slot.text).trim();
        if (isLoadtestPlaceholder(fromSlot)) {
          return presetTextForStage(reasonKey, index);
        }
        return fromSlot;
      }
    } else if (row && index === 0) {
      var legacy = String(row.message || "").trim();
      if (legacy && !isLoadtestPlaceholder(legacy)) {
        return legacy;
      }
    }
    return presetTextForStage(reasonKey, index);
  }

  /** Sync textarea + editor title for the selected stage (all reasons). */
  function setCardEditorStage(cardShell, reasonKey, index) {
    if (!cardShell || !reasonKey) return;
    var ix = parseInt(index, 10);
    if (!(ix >= 0)) ix = 0;
    ix = Math.max(0, Math.min(2, ix));
    cardShell.setAttribute("data-ma-tpl-active-stage", String(ix));

    var lbl = cardShell.querySelector("[data-ma-tpl-msg-label]");
    if (lbl) {
      lbl.textContent = stageLabelForReasonIndex(reasonKey, ix);
    }

    var ta = cardShell.querySelector("[data-ma-tpl-msg]");
    if (ta) {
      ta.value = messageTextForStage(reasonKey, ix);
      if (ix < getCardEnabledStageCount(cardShell)) {
        try {
          if (typeof ta.focus === "function") {
            ta.focus({ preventScroll: true });
          }
        } catch (_focusErr) {
          try {
            ta.focus();
          } catch (_focusErr2) {
            /* ignore */
          }
        }
      }
    }

    var dvi = cardShell.querySelector("[data-ma-tpl-delay]");
    var dsi = cardShell.querySelector("[data-ma-tpl-unit]");
    var dispDelay = displayDelayForStage(reasonKey, ix);
    if (dvi) {
      dvi.value = String(dispDelay.value);
    }
    if (dsi) {
      var u = dispDelay.unit;
      dsi.value =
        u === "day" ? "day" : u === "hour" ? "hour" : "minute";
    }

    syncCardStageWorkflow(cardShell);
  }

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function normalizeApiDelayUnit(u) {
    var s = String(u == null ? "" : u).trim().toLowerCase();
    if (s === "hour" || s === "hours") return "hour";
    return "minute";
  }

  function normalizeUiDelayUnit(u) {
    var s = String(u == null ? "" : u).trim();
    if (s === "hour") return "hour";
    if (s === "day") return "day";
    return "minute";
  }

  /**
   * عرض أيام في الواجهة دون تغيير الخادم: نخزّن التعادل كساعات على الـ API (ساعات = أيام×٢٤).
   */
  function displayDelayFromApi(delayVal, apiUnitNorm) {
    var dv =
      typeof delayVal === "number"
        ? delayVal
        : parseFloat(delayVal);
    if (!(dv > 0) || typeof dv !== "number") {
      dv = 1;
    }
    var u = apiUnitNorm;
    if (u === "hour" && dv >= 24) {
      var days = dv / 24;
      var rnd = Math.round(days);
      if (rnd >= 1 && Math.abs(days - rnd) < 1e-6) {
        return { value: rnd, unit: "day" };
      }
    }
    return { value: dv, unit: u };
  }

  function persistFirstSlotDelay(dv, uiUnit) {
    if (uiUnit === "day") {
      return { delay: dv * 24, unit: "hour" };
    }
    return { delay: dv, unit: uiUnit };
  }

  function buildRowFromTemplateEntry(key, ent, options) {
    options = options && typeof options === "object" ? options : {};
    ent = ent && typeof ent === "object" ? ent : {};
    var msgs = Array.isArray(ent.messages) ? ent.messages.slice(0, 3) : [];
    var first = msgs[0] && typeof msgs[0] === "object" ? msgs[0] : {};
    var dv = typeof first.delay === "number" ? first.delay : parseFloat(first.delay);
    if (!(dv > 0)) dv = typeof ent.delay_value === "number" ? ent.delay_value : parseFloat(ent.delay_value);
    var unitRaw = first.unit != null ? first.unit : ent.delay_unit;
    var u = normalizeApiDelayUnit(unitRaw) === "hour" ? "hour" : "minute";
    if (!(dv > 0)) dv = 1;
    var msgText = "";
    if (msgs.length && msgs[0] && String(msgs[0].text || "").trim()) {
      msgText = String(msgs[0].text).trim();
    } else if (String(ent.message || "").trim()) {
      msgText = String(ent.message).trim();
    }
    var mc = parseInt(ent.message_count, 10);
    if (!(mc >= 1)) mc = 1;
    mc = Math.max(1, Math.min(3, mc));
    var built = {
      key: normalizeReasonKey(key) || key,
      label_ar: String(ent.label_ar || LABEL_BY_KEY[key] || key),
      enabled: ent.enabled !== false,
      message: msgText,
      delay_value: dv,
      delay_unit: u,
      message_count: mc,
      messages: msgs,
    };
    if (options.applyRecommended) {
      return safeApplyRecommendedDelaysToRow(key, built);
    }
    return built;
  }

  function safeApplyRecommendedDelaysToRow(reasonKey, row) {
    try {
      return applyRecommendedDelaysToRow(reasonKey, row);
    } catch (rowErr) {
      trigLog("[TRIGGER ROW DELAY APPLY ERROR]", {
        reason: reasonKey,
        err: String(rowErr && rowErr.message ? rowErr.message : rowErr),
      });
      return row;
    }
  }

  function buildClientFallbackPayload() {
    var rows = TRIGGER_KEYS_ORDER.map(function (k) {
      return buildRowFromTemplateEntry(k, {}, { applyRecommended: true });
    });
    return {
      ok: true,
      section_title_ar: "قوالب حسب سبب التردد",
      reason_rows: rows,
      display_fallback: true,
    };
  }

  function ensureSixRows(rowsIn) {
    var byKey = {};
    var i;
    var r;
    var ks;
    if (Array.isArray(rowsIn)) {
      for (i = 0; i < rowsIn.length; i++) {
        r = rowsIn[i];
        if (!r || typeof r !== "object") continue;
        ks = String(r.key || r.slug || r.id || "").trim().toLowerCase();
        if (ks) byKey[ks] = r;
      }
    }
    var out = [];
    for (i = 0; i < TRIGGER_KEYS_ORDER.length; i++) {
      var k0 = TRIGGER_KEYS_ORDER[i];
      try {
        var ent0 = byKey[k0] || {};
        var hasStored =
          ent0 &&
          ((Array.isArray(ent0.messages) && ent0.messages.length > 0) ||
            ent0.delay_value != null ||
            ent0.delay_unit != null);
        out.push(
          buildRowFromTemplateEntry(k0, ent0, {
            applyRecommended: !hasStored,
          })
        );
      } catch (rowBuildErr) {
        trigLog("[TRIGGER ROW BUILD ERROR]", {
          reason: k0,
          err: String(
            rowBuildErr && rowBuildErr.message ? rowBuildErr.message : rowBuildErr
          ),
        });
        out.push(
          buildRowFromTemplateEntry(k0, {}, { applyRecommended: true })
        );
      }
    }
    return out;
  }

  /**
   * يدمج أشكال الاستجابة المختلفة (حقل آخر اسم، غلاف data/) دون افتراض شكل واحد.
   * @param {number} [httpStatus]  رمز ‎HTTP‎ لـ ‎GET‎ عند التوفّر — ‎٢٠٠‎ مع صفوف صالحة يُعتبر نجاحاً حتى لو ‎ok‎ ناقص.
   */
  function normalizeTriggerTemplatesPayload(raw, httpStatus) {
    var base = raw && typeof raw === "object" ? raw : {};
    var data = base;
    if (base.data && typeof base.data === "object") data = base.data;
    else if (base.payload && typeof base.payload === "object") data = base.payload;

    var rows = null;
    if (Array.isArray(data.reason_rows)) rows = data.reason_rows;
    else if (Array.isArray(data.cards)) rows = data.cards;
    else if (Array.isArray(data.reasons)) rows = data.reasons;
    else if (Array.isArray(base.reason_rows)) rows = base.reason_rows;

    if (
      (!rows || rows.length === 0) &&
      data.reason_templates &&
      typeof data.reason_templates === "object"
    ) {
      rows = TRIGGER_KEYS_ORDER.map(function (k) {
        return buildRowFromTemplateEntry(k, data.reason_templates[k]);
      });
    }

    rows = ensureSixRows(rows || []);

    var jsonOk = base.ok === true || data.ok === true;
    var jsonFail = base.ok === false || data.ok === false;
    var httpOk =
      typeof httpStatus === "number" && httpStatus >= 200 && httpStatus < 300;

    var ok = false;
    if (jsonOk) ok = true;
    else if (!jsonFail && rows.length > 0) ok = true;
    else if (httpOk && rows.length > 0) ok = true;

    return {
      ok: ok,
      section_title_ar: data.section_title_ar || base.section_title_ar,
      section_subtitle_ar: data.section_subtitle_ar || base.section_subtitle_ar,
      guided_defaults: data.guided_defaults || base.guided_defaults,
      reason_rows: rows,
    };
  }

  function payloadKeys(raw) {
    try {
      if (!raw || typeof raw !== "object") return "(none)";
      return Object.keys(raw).slice(0, 56).join(",");
    } catch (unused) {
      return "(keys_error)";
    }
  }

  function trigLog(tag, meta) {
    try {
      console.log(tag, meta && typeof meta === "object" ? meta : {});
    } catch (_trigLogErr) {
      /* ignore */
    }
  }

  function logSaveHandler(handlerName, handlerId, reason, eventType) {
    try {
      console.log(
        "[SAVE HANDLER]",
        handlerName,
        handlerId,
        reason || "",
        eventType || ""
      );
    } catch (_handlerLogErr) {
      /* ignore */
    }
  }

  function tplMerchantStoreSlug() {
    try {
      if (
        typeof window.CARTFLOW_STORE_SLUG === "string" &&
        window.CARTFLOW_STORE_SLUG.trim()
      ) {
        return window.CARTFLOW_STORE_SLUG.trim();
      }
      var el = document.querySelector("[data-ma-store-slug]");
      if (el) {
        var a = el.getAttribute("data-ma-store-slug");
        if (a && String(a).trim()) return String(a).trim();
      }
    } catch (_slugErr) {
      /* ignore */
    }
    return "demo";
  }

  function tplStoreSlugForDebug() {
    return tplMerchantStoreSlug();
  }

  function tplTriggerTemplatesGetUrl() {
    var slug = tplMerchantStoreSlug();
    return (
      FETCH_URL_GET +
      "?store_slug=" +
      encodeURIComponent(slug)
    );
  }

  function tplTriggerTemplatesPostUrl() {
    return tplTriggerTemplatesGetUrl().replace(FETCH_URL_GET, FETCH_URL_POST);
  }

  function tplSaveRequestHeaders() {
    var slug = tplMerchantStoreSlug();
    return {
      "Content-Type": "application/json",
      "X-Store-Slug": slug,
    };
  }

  function bumpTplApplyGen() {
    var g = (window.__trigger_templates_apply_gen || 0) + 1;
    window.__trigger_templates_apply_gen = g;
    window.__trigger_templates_load_gen = g;
    return g;
  }

  function applyGenIsCurrent(gen) {
    return typeof gen !== "number" || gen === window.__trigger_templates_apply_gen;
  }

  function cancelTplGetInFlight() {
    if (!tplGetAbort) return;
    try {
      tplGetAbort.abort();
    } catch (_abortErr) {
      /* ignore */
    }
    tplGetAbort = null;
  }

  function countTplSaveInFlight() {
    var n = 0;
    var k;
    for (k in tplSaveInFlight) {
      if (Object.prototype.hasOwnProperty.call(tplSaveInFlight, k) && tplSaveInFlight[k]) {
        n++;
      }
    }
    return n;
  }

  /** عدادات تشخيص — `window.__maTplDebug()` في وحدة التحكم. */
  function refreshMaTplDebugCounters() {
    var root = byId("ma-tpl-root");
    var cards = root ? root.querySelectorAll("[data-ma-tpl-key]") : [];
    tplMetrics.save_in_flight_keys = countTplSaveInFlight();
    tplMetrics.save_click_handlers = root && root._maTplDelegatesBound ? 1 : 0;
    window.__maTplDebug = {
      mounted_cards: cards ? cards.length : 0,
      save_click_handlers: tplMetrics.save_click_handlers,
      active_save_requests: tplMetrics.save_in_flight_keys,
      active_get_requests: tplMetrics.get_in_flight,
      save_clicks: tplMetrics.save_clicks,
      save_handler_invokes: tplMetrics.save_handler_invokes,
      save_posts_started: tplMetrics.save_posts_started,
      last_save_invocation: window.__maTplSaveInvocation || 0,
      get_fetches_started: tplMetrics.get_fetches_started,
      render_applied: tplMetrics.render_applied,
      render_stale_skipped: tplMetrics.render_stale_skipped,
      apply_gen: window.__trigger_templates_apply_gen,
      dom_ready: !!window.__trigger_templates_dom_ready,
      templates_loading: !!window.__trigger_templates_loading,
      current_reason_key: window.__maTplDebugLastReason || "",
      current_stage: window.__maTplDebugLastStage,
      last_payload_bytes: window.__maTplDebugLastPayloadBytes || 0,
      last_save_ms: window.__maTplDebugLastSaveMs || 0,
    };
    return window.__maTplDebug;
  }

  /** سجلات تحقيق — مسار console واحد (لا استدعاء trigLog مكرر). */
  function tplDbg(tag, meta) {
    var out = { store_slug: tplStoreSlugForDebug() };
    if (meta && typeof meta === "object") {
      var mk;
      for (mk in meta) {
        if (Object.prototype.hasOwnProperty.call(meta, mk)) {
          out[mk] = meta[mk];
        }
      }
    }
    out.debug = refreshMaTplDebugCounters();
    try {
      console.log(tag, out);
    } catch (_logErr) {
      /* ignore */
    }
  }

  function onMaTplRootClick(ev) {
    var root = byId("ma-tpl-root");
    if (!root) return;
    var tg = ev.target;
    var stageBtn =
      tg && tg.closest ? tg.closest("[data-ma-tpl-stage-select]") : null;
    if (stageBtn && root.contains(stageBtn)) {
      ev.preventDefault();
      var rkChip = stageBtn.getAttribute("data-ma-tpl-reason");
      var ixChip = parseInt(stageBtn.getAttribute("data-ma-tpl-preset-i"), 10);
      var cardChip = stageBtn.closest("[data-ma-tpl-key]");
      if (!cardChip || !rkChip || !(ixChip >= 0)) return;
      patchActiveStageInLastPayload(cardChip, rkChip);
      setCardEditorStage(cardChip, rkChip, ixChip);
      return;
    }
    var restoreB =
      tg && tg.closest ? tg.closest("[data-ma-tpl-restore-timing]") : null;
    if (restoreB && root.contains(restoreB)) {
      ev.preventDefault();
      var cardR = restoreB.closest("[data-ma-tpl-key]");
      var rkR = cardR && cardR.getAttribute("data-ma-tpl-key");
      if (cardR && rkR) {
        restoreRecommendedTimingForActiveStage(cardR, rkR);
      }
      return;
    }
    var saveB = tg && tg.closest ? tg.closest("[data-ma-tpl-save]") : null;
    if (saveB && root.contains(saveB)) {
      ev.preventDefault();
      ev.stopPropagation();
      tplMetrics.save_clicks++;
      var cardS = saveB.closest("[data-ma-tpl-key]");
      var rkSave = cardS && cardS.getAttribute("data-ma-tpl-key");
      if (cardS && rkSave) {
        logSaveHandler(
          TPL_SAVE_HANDLER.name,
          TPL_SAVE_HANDLER.id,
          normalizeReasonKey(rkSave),
          ev.type
        );
        saveOne(rkSave, cardS, TPL_SAVE_HANDLER);
      }
    }
  }

  function onMaTplRootChange(ev) {
    var root = byId("ma-tpl-root");
    if (!root) return;
    var mcSel =
      ev.target && ev.target.closest
        ? ev.target.closest("[data-ma-tpl-msg-count]")
        : null;
    if (!mcSel || !root.contains(mcSel)) return;
    var cardEl = mcSel.closest("[data-ma-tpl-key]");
    if (!cardEl) return;
    var rk = cardEl.getAttribute("data-ma-tpl-key");
    var n = getCardEnabledStageCount(cardEl);
    var editIx = parseInt(
      cardEl.getAttribute("data-ma-tpl-active-stage") || "0",
      10
    );
    if (editIx >= n && rk) {
      setCardEditorStage(cardEl, rk, n - 1);
    } else {
      syncCardStageWorkflow(cardEl);
    }
  }

  /** ربط مرة واحدة — لا إعادة ربط عند كل render. */
  function ensureMaTplRootDelegates() {
    var root = byId("ma-tpl-root");
    if (!root) return;
    if (root._maTplDelegatesBound) {
      tplMetrics.save_click_handlers = 1;
      return;
    }
    if (typeof root._maTplOnClick === "function") {
      root.removeEventListener("click", root._maTplOnClick);
    }
    if (typeof root._maTplOnChange === "function") {
      root.removeEventListener("change", root._maTplOnChange);
    }
    root._maTplOnClick = onMaTplRootClick;
    root._maTplOnChange = onMaTplRootChange;
    root._maTplDelegatesBound = true;
    root.addEventListener("click", root._maTplOnClick);
    root.addEventListener("change", root._maTplOnChange);
    tplMetrics.save_click_handlers = 1;
    refreshMaTplDebugCounters();
  }

  function snapshotCacheOk(snap) {
    if (
      !snap ||
      typeof snap !== "object" ||
      snap.json == null ||
      typeof snap.json !== "object"
    ) {
      return false;
    }
    try {
      var probe = normalizeTriggerTemplatesPayload(
        snap.json,
        snap.httpStatus
      );
      return !!(
        probe &&
        probe.ok &&
        probe.reason_rows &&
        probe.reason_rows.length
      );
    } catch (snapErr) {
      return false;
    }
  }

  function cardHtml(row) {
    var keyRaw = row.key != null ? String(row.key) : "";
    var k = esc(keyRaw);
    var lbl = esc(row.label_ar || LABEL_BY_KEY[row.key] || row.key || "");
    var en = row.enabled !== false ? " checked" : "";
    var msg = esc(row.message || "");
    var rawDv =
      typeof row.delay_value === "number"
        ? row.delay_value
        : parseFloat(row.delay_value) || 1;
    var disp = displayDelayFromApi(rawDv, normalizeApiDelayUnit(row.delay_unit));
    var dv = disp.value;
    var duNorm = disp.unit;
    var mc = parseInt(row.message_count, 10) || 1;
    mc = Math.max(1, Math.min(3, mc));
    var minSel = duNorm === "minute" ? " selected" : "";
    var hourSel = duNorm === "hour" ? " selected" : "";
    var daySel = duNorm === "day" ? " selected" : "";
    var stageHelp = buildStageCountHelpHtml(keyRaw || row.key || "");
    var workflow = stageWorkflowHtml(keyRaw || row.key || "", mc);
    var customerPath = customerExperienceSummaryHtml(keyRaw || row.key || "", mc);
    var presets0 = (PRESET_SUGGESTIONS_BY_REASON[keyRaw || row.key || ""] || [])[0];
    var msg1Lbl = presets0
      ? esc(stageLabelForIndex(presets0, 0))
      : "الرسالة 1 — نص المرحلة الأولى";

    var mcOpts = [1, 2, 3]
      .map(function (n) {
        var sel = n === mc ? " selected" : "";
        return '<option value="' + n + '"' + sel + ">" + n + "</option>";
      })
      .join("");

    return (
      '<div class="ma-tpl-card" data-ma-tpl-key="' +
      k +
      '" data-ma-tpl-active-stage="0">' +
      '<div class="ma-tpl-card-head">' +
      '<span class="ma-tpl-chip">' +
      lbl +
      "</span>" +
      "</div>" +
      '<label class="ma-tpl-check"><input type="checkbox" data-ma-tpl-enabled' +
      en +
      "> تفعيل قالب الاسترجاع لهذا السبب</label>" +
      '<div class="ma-tpl-stage-config">' +
      '<label class="ma-tpl-lbl" for="ma-tpl-mc-' +
      k +
      '">كم مرحلة تريد تفعيلها؟</label>' +
      '<select class="ma-tpl-input" id="ma-tpl-mc-' +
      k +
      '" data-ma-tpl-msg-count>' +
      mcOpts +
      "</select>" +
      stageHelp +
      "</div>" +
      customerPath +
      workflow +
      '<div class="ma-tpl-editor-panel" data-ma-tpl-editor-panel>' +
      '<p class="ma-tpl-editor-inactive-banner" data-ma-tpl-inactive-banner hidden dir="rtl">' +
      "هذه المرحلة غير مفعّلة في المسار — العميل لن يستلمها. المعاينة للاطلاع فقط." +
      "</p>" +
      '<p class="ma-tpl-editor-hint" dir="rtl">تحرير نص المرحلة المحددة (✓ = تُرسل · ○ = لاحقاً في المسار · — = غير مفعّلة)</p>' +
      '<label class="ma-tpl-lbl" data-ma-tpl-msg-label for="ma-tpl-msg-' +
      k +
      '">' +
      msg1Lbl +
      "</label>" +
      '<textarea class="ma-tpl-input ma-tpl-ta" id="ma-tpl-msg-' +
      k +
      '" rows="5" maxlength="65535" data-ma-tpl-msg dir="rtl" placeholder="النص الموجّه للعميل عبر مسار الاسترجاع…">' +
      msg +
      "</textarea>" +
      "</div>" +
      '<div class="ma-tpl-row2">' +
      '<div><label class="ma-tpl-lbl" for="ma-tpl-dv-' +
      k +
      '">تأخير قبل الإرسال (قيمة)</label>' +
      '<input class="ma-tpl-input" type="number" id="ma-tpl-dv-' +
      k +
      '" min="0.1" step="any" data-ma-tpl-delay value="' +
      esc(String(dv)) +
      '" /></div>' +
      '<div><label class="ma-tpl-lbl" for="ma-tpl-du-' +
      k +
      '">الوحدة</label>' +
      '<select class="ma-tpl-input" id="ma-tpl-du-' +
      k +
      '" data-ma-tpl-unit>' +
      '<option value="minute"' +
      minSel +
      ">دقائق</option>" +
      '<option value="hour"' +
      hourSel +
      ">ساعات</option>" +
      '<option value="day"' +
      daySel +
      ">أيام</option>" +
      "</select></div>" +
      "</div>" +
      '<p class="ma-tpl-delay-restore-wrap" dir="rtl">' +
      '<button type="button" class="ma-tpl-restore-timing" data-ma-tpl-restore-timing title="استعادة التوقيت المقترح لهذه المرحلة فقط (بدون حفظ تلقائي)">↺ استعادة المقترح</button>' +
      "</p>" +
      '<p class="ma-tpl-timing-note" dir="rtl">💡 التوقيت المقترح مبني على ممارسات شائعة لاستعادة السلال ويمكن تعديله.</p>' +
      '<p class="ma-tpl-hint">المراحل تُرسل بالترتيب فقط عند عدم عودة العميل أو إتمام الشراء.</p>' +
      '<div class="ma-tpl-actions">' +
      '<button type="button" class="ma-fw-save" data-ma-tpl-save>حفظ</button>' +
      '<span class="ma-tpl-status" data-ma-tpl-status aria-live="polite"></span>' +
      "</div>" +
      "</div>"
    );
  }

  function render(raw, httpStatus, applyGen) {
    if (!applyGenIsCurrent(applyGen)) {
      tplMetrics.render_stale_skipped++;
      tplDbg("[TRIGGER RENDER STALE SKIP]", {
        apply_gen: applyGen,
        current_gen: window.__trigger_templates_apply_gen,
      });
      return;
    }
    ensureMaTplRootDelegates();
    var root = byId("ma-tpl-root");
    var sub = byId("ma-tpl-sub");
    var err = byId("ma-tpl-load-err");
    if (!root) return;

    var payload;
    try {
      payload = normalizeTriggerTemplatesPayload(raw, httpStatus);
    } catch (normErr) {
      trigLog("[TRIGGER LOAD ERROR]", {
        phase: "normalize_render",
        err: String(normErr && normErr.message ? normErr.message : normErr),
        payload_keys: payloadKeys(raw),
        status: httpStatus,
      });
      render(buildClientFallbackPayload(), 200, applyGen);
      return;
    }

    /* Page subtitle stays from merchant_app.html (sequence stages — not API overwrite). */

    if (!payload.ok || !payload.reason_rows || payload.reason_rows.length === 0) {
      trigLog("[TRIGGER LOAD ERROR]", {
        phase: "unusable_payload",
        payload_keys: payloadKeys(raw),
        status: httpStatus,
      });
      render(buildClientFallbackPayload(), 200, applyGen);
      return;
    }

    if (err) err.hidden = true;

    try {
      root.innerHTML =
        sectionIntroHtml() +
        '<div class="ma-tpl-grid">' +
        payload.reason_rows.map(cardHtml).join("") +
        "</div>";
    } catch (renderErr) {
      trigLog("[TRIGGER LOAD ERROR]", {
        phase: "render_cards",
        err: String(
          renderErr && renderErr.message ? renderErr.message : renderErr
        ),
        payload_keys: payloadKeys(raw),
        status: httpStatus,
      });
      render(buildClientFallbackPayload(), 200, applyGen);
      return;
    }

    lastPayload = payload;
    tplMetrics.render_applied++;
    window.__trigger_templates_dom_ready = true;

    var cards = root.querySelectorAll("[data-ma-tpl-key]");
    var ci;
    for (ci = 0; ci < cards.length; ci++) {
      (function (cardEl) {
        var rkInit = cardEl.getAttribute("data-ma-tpl-key");
        if (rkInit) {
          setCardEditorStage(cardEl, rkInit, 0);
        } else {
          syncCardStageWorkflow(cardEl);
        }
      })(cards[ci]);
    }
    refreshMaTplDebugCounters();
  }

  /** يرسم بعد توفر الحاوية (تجنّب فشل ‎SPA‎ عند تفعيل الصفحة قبل بناء DOM). */
  function renderWhenRootReady(raw, httpStatus, domAttempt, onDone, applyGen) {
    if (!applyGenIsCurrent(applyGen)) {
      tplMetrics.render_stale_skipped++;
      if (onDone) onDone(false);
      return;
    }
    var root = byId("ma-tpl-root");
    if (root && root.isConnected) {
      render(raw, httpStatus, applyGen);
      var ok =
        !!(lastPayload && lastPayload.ok && lastPayload.reason_rows &&
          lastPayload.reason_rows.length);
      if (onDone) onDone(ok);
      return;
    }
    if (domAttempt >= MAX_DOM_READY_ATTEMPTS) {
      window.__trigger_templates_loading = false;
      if (onDone) onDone(false);
      return;
    }
    window.setTimeout(function () {
      renderWhenRootReady(raw, httpStatus, domAttempt + 1, onDone, applyGen);
    }, DOM_POLL_MS);
  }

  function findRow(key) {
    if (!lastPayload || !lastPayload.reason_rows) return null;
    var nk = normalizeReasonKey(key);
    if (!nk) return null;
    for (var i = 0; i < lastPayload.reason_rows.length; i++) {
      if (normalizeReasonKey(lastPayload.reason_rows[i].key) === nk) {
        return lastPayload.reason_rows[i];
      }
    }
    return null;
  }

  function ensureLastPayloadShell() {
    if (
      lastPayload &&
      Array.isArray(lastPayload.reason_rows) &&
      lastPayload.reason_rows.length >= TRIGGER_KEYS_ORDER.length
    ) {
      return;
    }
    var probe = null;
    var snap = window.__trigger_templates_loaded;
    if (snapshotCacheOk(snap)) {
      try {
        probe = normalizeTriggerTemplatesPayload(snap.json, snap.httpStatus);
      } catch (_shellNormErr) {
        probe = null;
      }
    }
    if (probe && probe.reason_rows && probe.reason_rows.length) {
      lastPayload = probe;
      return;
    }
    lastPayload = buildClientFallbackPayload();
  }

  function applySavedMessagesToLocalState(reasonKey, messages, mc) {
    ensureLastPayloadShell();
    var nk = normalizeReasonKey(reasonKey);
    if (!nk || !Array.isArray(messages) || !messages.length) return;
    mc = Math.max(1, Math.min(3, parseInt(mc, 10) || 1));
    var row = findRow(nk);
    if (!row) {
      row = buildRowFromTemplateEntry(nk, {}, { applyRecommended: false });
      if (!Array.isArray(lastPayload.reason_rows)) {
        lastPayload.reason_rows = [];
      }
      lastPayload.reason_rows.push(row);
    }
    row.messages = messages.slice(0, mc);
    row.message_count = mc;
    if (row.messages[0]) {
      row.delay_value = row.messages[0].delay;
      row.delay_unit = row.messages[0].unit;
      row.message = String(row.messages[0].text || row.message || "").trim();
    }
  }

  function syncCardDelayFieldsFromRow(card, reasonKey, stageIx) {
    if (!card || !reasonKey) return;
    var ix = parseInt(stageIx, 10);
    if (!(ix >= 0)) ix = 0;
    var disp = displayDelayForStage(reasonKey, ix);
    var dvi = card.querySelector("[data-ma-tpl-delay]");
    var dsi = card.querySelector("[data-ma-tpl-unit]");
    if (dvi) dvi.value = String(disp.value);
    if (dsi) {
      dsi.value =
        disp.unit === "day"
          ? "day"
          : disp.unit === "hour"
            ? "hour"
            : "minute";
    }
    var ta = card.querySelector("[data-ma-tpl-msg]");
    var row = findRow(reasonKey);
    if (ta && row && row.messages && row.messages[ix]) {
      ta.value = String(row.messages[ix].text || row.message || "");
    }
  }

  function syncAllCardsFromLastPayload() {
    if (!lastPayload || !lastPayload.reason_rows) return;
    var root = byId("ma-tpl-root");
    if (!root || !root.isConnected) return;
    var cards = root.querySelectorAll("[data-ma-tpl-key]");
    var ci;
    for (ci = 0; ci < cards.length; ci++) {
      var rk = normalizeReasonKey(cards[ci].getAttribute("data-ma-tpl-key"));
      if (!rk) continue;
      var editIx = parseInt(
        cards[ci].getAttribute("data-ma-tpl-active-stage") || "0",
        10
      );
      if (!(editIx >= 0)) editIx = 0;
      syncCardDelayFieldsFromRow(cards[ci], rk, editIx);
      syncCardStageWorkflow(cards[ci]);
    }
  }

  function captureTplScrollAnchor() {
    var anchor = {
      windowY:
        typeof window.scrollY === "number"
          ? window.scrollY
          : window.pageYOffset || 0,
      rootTop: 0,
    };
    var root = byId("ma-tpl-root");
    if (root && root.getBoundingClientRect) {
      anchor.rootTop = root.getBoundingClientRect().top;
    }
    return anchor;
  }

  function restoreTplScrollAnchor(anchor) {
    if (!anchor || typeof anchor !== "object") return;
    window.requestAnimationFrame(function () {
      window.scrollTo(0, anchor.windowY);
      window.requestAnimationFrame(function () {
        var root = byId("ma-tpl-root");
        if (!root || !root.getBoundingClientRect) return;
        var delta = root.getBoundingClientRect().top - anchor.rootTop;
        if (Math.abs(delta) > 1) {
          window.scrollBy(0, delta);
        }
      });
    });
  }

  function buildMessagesSlice(key, text, dv, unit, mc, activeStageIndex) {
    var prevRow = findRow(key);
    var prevMsgs = prevRow && Array.isArray(prevRow.messages) ? prevRow.messages.slice() : [];
    var editIx = parseInt(activeStageIndex, 10);
    if (!(editIx >= 0)) editIx = 0;
    editIx = Math.max(0, Math.min(mc - 1, editIx));

    function slot(i) {
      if (prevMsgs[i] && typeof prevMsgs[i] === "object") {
        var o = {
          delay:
            typeof prevMsgs[i].delay === "number"
              ? prevMsgs[i].delay
              : parseFloat(prevMsgs[i].delay) || 60,
          unit: prevMsgs[i].unit || "minute",
          text: String(prevMsgs[i].text || "").trim(),
        };
        if (!o.unit || (o.unit !== "minute" && o.unit !== "hour")) {
          o.unit = "minute";
        }
        if (o.delay <= 0) o.delay = 1;
        return o;
      }
      var recEnc = recommendedDelayEncodedForApi(key, i);
      var fillText = i === editIx ? text : presetTextForStage(key, i);
      return {
        delay: recEnc.delay,
        unit: recEnc.unit,
        text: fillText,
      };
    }

    var out = [];
    for (var j = 0; j < mc; j++) {
      var sl = slot(j);
      if (j === editIx) {
        sl.text = text;
        var encEdit = persistFirstSlotDelay(dv, unit);
        sl.delay = encEdit.delay;
        sl.unit = encEdit.unit;
      }
      out.push(sl);
    }
    return out;
  }

  function mergeReasonRowsIntoLastPayload(patchRows) {
    ensureLastPayloadShell();
    if (!lastPayload || !Array.isArray(patchRows) || !patchRows.length) return;
    if (!Array.isArray(lastPayload.reason_rows)) {
      lastPayload.reason_rows = [];
    }
    var byKey = {};
    var i;
    for (i = 0; i < lastPayload.reason_rows.length; i++) {
      var rk = normalizeReasonKey(
        lastPayload.reason_rows[i] && lastPayload.reason_rows[i].key
      );
      if (rk) byKey[rk] = lastPayload.reason_rows[i];
    }
    for (i = 0; i < patchRows.length; i++) {
      var pr = patchRows[i];
      if (!pr || !pr.key) continue;
      var pk = normalizeReasonKey(pr.key);
      if (!pk) continue;
      byKey[pk] = buildRowFromTemplateEntry(pk, pr, {
        applyRecommended: false,
      });
    }
    var merged = [];
    for (i = 0; i < TRIGGER_KEYS_ORDER.length; i++) {
      var k = TRIGGER_KEYS_ORDER[i];
      merged.push(byKey[k] || buildRowFromTemplateEntry(k, {}, { applyRecommended: true }));
    }
    lastPayload.reason_rows = merged;
    lastPayload.ok = true;
  }

  /** بعد الحفظ: تحديث الذاكرة دون إعادة رسم الشبكة (يحافظ على التمرير والمرحلة). */
  function absorbSaveResponseWithoutRerender(pack, savedKey, savedCard, saveCtx) {
    if (!pack || !pack.payload) return;
    var scrollAnchor = captureTplScrollAnchor();
    var httpSt =
      typeof pack.httpStatus === "number" ? pack.httpStatus : 200;
    var p = pack.payload;
    var nk = normalizeReasonKey(savedKey);

    if (
      saveCtx &&
      Array.isArray(saveCtx.messages) &&
      saveCtx.messages.length &&
      nk
    ) {
      applySavedMessagesToLocalState(nk, saveCtx.messages, saveCtx.mc);
    }

    if (p.save_ack && (!p.reason_rows || p.reason_rows.length <= 2)) {
      mergeReasonRowsIntoLastPayload(p.reason_rows || []);
      if (
        saveCtx &&
        Array.isArray(saveCtx.messages) &&
        saveCtx.messages.length &&
        nk
      ) {
        applySavedMessagesToLocalState(nk, saveCtx.messages, saveCtx.mc);
      }
      window.__trigger_templates_loaded = {
        json: {
          ok: true,
          save_ack: true,
          reason_rows: lastPayload ? lastPayload.reason_rows : p.reason_rows,
        },
        httpStatus: httpSt,
      };
    } else {
      var norm = normalizeTriggerTemplatesPayload(p, httpSt);
      lastPayload = norm;
      if (
        saveCtx &&
        Array.isArray(saveCtx.messages) &&
        saveCtx.messages.length &&
        nk
      ) {
        applySavedMessagesToLocalState(nk, saveCtx.messages, saveCtx.mc);
      }
      window.__trigger_templates_loaded = {
        json: p,
        httpStatus: httpSt,
      };
    }

    if (savedCard && nk) {
      var ix = parseInt(
        savedCard.getAttribute("data-ma-tpl-active-stage") || "0",
        10
      );
      if (!(ix >= 0)) ix = 0;
      syncCardDelayFieldsFromRow(savedCard, nk, ix);
    }
    restoreTplScrollAnchor(scrollAnchor);
  }

  function parseSaveResponse(resp) {
    return resp.text().then(function (text) {
      var j = null;
      var parseErr = null;
      try {
        j = text ? JSON.parse(text) : null;
      } catch (pe) {
        parseErr = String(pe && pe.message ? pe.message : pe);
      }
      var ok =
        resp.ok &&
        j &&
        typeof j === "object" &&
        j.ok === true;
      return {
        ok: ok,
        payload: j,
        httpStatus: resp.status,
        parseErr: parseErr,
        raw_bytes: text ? text.length : 0,
      };
    });
  }

  function saveOne(key, card, handlerRef) {
    key = normalizeReasonKey(key);
    if (!key || !card) return;
    handlerRef = handlerRef || TPL_SAVE_HANDLER;
    if (handlerRef.id !== TPL_SAVE_HANDLER.id) {
      tplDbg("[SAVE TEMPLATE SKIP]", {
        reason: key,
        cause: "unknown_handler",
        handler_id: handlerRef.id,
      });
      return;
    }
    if (tplSaveInFlight[key]) {
      tplDbg("[SAVE TEMPLATE SKIP]", {
        reason: key,
        cause: "save_in_flight",
        handler_id: handlerRef.id,
      });
      return;
    }
    tplSaveInFlight[key] = true;
    tplMetrics.save_handler_invokes++;
    var saveInvocation = (window.__maTplSaveInvocation || 0) + 1;
    window.__maTplSaveInvocation = saveInvocation;
    ensureMaTplRootDelegates();
    ensureLastPayloadShell();
    patchActiveStageInLastPayload(card, key);
    var st = card.querySelector("[data-ma-tpl-status]");
    var ena = card.querySelector("[data-ma-tpl-enabled]");
    var ta = card.querySelector("[data-ma-tpl-msg]");
    var dvi = card.querySelector("[data-ma-tpl-delay]");
    var dsi = card.querySelector("[data-ma-tpl-unit]");
    var mci = card.querySelector("[data-ma-tpl-msg-count]");

    var text = ta ? ta.value.trim() : "";
    var dv = parseFloat(dvi && dvi.value ? dvi.value : "1") || 1;
    if (dv <= 0) dv = 1;
    var unit = normalizeUiDelayUnit(dsi && dsi.value ? dsi.value : "minute");
    var mc = parseInt(mci && mci.value ? mci.value : "1", 10) || 1;
    mc = Math.max(1, Math.min(3, mc));

    var activeIx = parseInt(card.getAttribute("data-ma-tpl-active-stage") || "0", 10);
    if (!(activeIx >= 0)) activeIx = 0;
    activeIx = Math.max(0, Math.min(mc - 1, activeIx));

    var messages = buildMessagesSlice(key, text, dv, unit, mc, activeIx);

    var body = {
      reason_templates: {},
    };
    var stage1Text =
      messages[0] && messages[0].text
        ? String(messages[0].text).trim()
        : text;
    body.reason_templates[key] = {
      enabled: !!(ena && ena.checked),
      message: stage1Text,
      message_count: mc,
      messages: messages,
    };
    body.selected_stage = activeIx;
    body.store_slug = tplMerchantStoreSlug();

    var bodyStr = JSON.stringify(body);
    window.__maTplDebugLastReason = key;
    window.__maTplDebugLastStage = activeIx;
    window.__maTplDebugLastPayloadBytes = bodyStr.length;
    bumpTplApplyGen();

    var perfNow =
      typeof performance !== "undefined" && performance.now
        ? function () {
            return performance.now();
          }
        : function () {
            return Date.now();
          };
    var tSave0 = perfNow();

    tplMetrics.save_posts_started++;
    tplDbg("[SAVE TEMPLATE START]", {
      invocation: saveInvocation,
      handler_name: handlerRef.name,
      handler_id: handlerRef.id,
      reason: key,
      stage: activeIx,
      delay: dv,
      unit: unit,
      payload_bytes: bodyStr.length,
      apply_gen: window.__trigger_templates_apply_gen,
      endpoint: tplTriggerTemplatesPostUrl(),
    });

    if (st) st.textContent = "جاري الحفظ…";

    fetch(tplTriggerTemplatesPostUrl(), {
      method: "POST",
      credentials: "same-origin",
      headers: tplSaveRequestHeaders(),
      body: bodyStr,
    })
      .then(function (r) {
        return parseSaveResponse(r).then(function (pack) {
          pack.duration_ms = Math.round(perfNow() - tSave0);
          return pack;
        });
      })
      .then(function (pack) {
        if (pack.ok && pack.payload) {
          try {
            absorbSaveResponseWithoutRerender(pack, key, card, {
              messages: messages,
              mc: mc,
              activeIx: activeIx,
            });
          } catch (absorbErr) {
            tplDbg("[SAVE TEMPLATE FAIL]", {
              reason: key,
              stage: activeIx,
              delay: dv,
              unit: unit,
              duration_ms: pack.duration_ms,
              http_status: pack.httpStatus,
              failure_class: "absorb_response",
              err: String(
                absorbErr && absorbErr.message ? absorbErr.message : absorbErr
              ),
            });
            if (st) st.textContent = "تعذر الحفظ";
            return;
          }
          var rowAfter = findRow(key);
          var savedDelay =
            rowAfter &&
            rowAfter.messages &&
            rowAfter.messages[activeIx] &&
            rowAfter.messages[activeIx].delay;
          window.__maTplDebugLastSaveMs = pack.duration_ms;
          tplDbg("[SAVE TEMPLATE SUCCESS]", {
            invocation: saveInvocation,
            handler_id: handlerRef.id,
            reason: key,
            stage: activeIx,
            delay: dv,
            unit: unit,
            duration_ms: pack.duration_ms,
            http_status: pack.httpStatus,
            persisted_delay: savedDelay,
            apply_gen: window.__trigger_templates_apply_gen,
          });
          if (st) st.textContent = "تم الحفظ";
          window.setTimeout(function () {
            if (st && st.textContent === "تم الحفظ") st.textContent = "";
          }, 3500);
          return;
        }
        tplDbg("[SAVE TEMPLATE FAIL]", {
          reason: key,
          stage: activeIx,
          delay: dv,
          unit: unit,
          duration_ms: pack.duration_ms,
          http_status: pack.httpStatus,
          api_error:
            pack.payload && pack.payload.error
              ? pack.payload.error
              : "(none)",
          parse_error: pack.parseErr || "(none)",
          raw_bytes: pack.raw_bytes,
          failure_class:
            pack.parseErr
              ? "json_parse"
              : pack.httpStatus >= 500
                ? "server_5xx"
                : pack.httpStatus === 404
                  ? "no_store"
                  : "api_ok_false",
        });
        if (st) st.textContent = "تعذر الحفظ";
      })
      .catch(function (netErr) {
        tplDbg("[SAVE TEMPLATE FAIL]", {
          reason: key,
          stage: activeIx,
          delay: dv,
          unit: unit,
          duration_ms: Math.round(perfNow() - tSave0),
          failure_class: "network_or_timeout",
          err: String(netErr && netErr.message ? netErr.message : netErr),
        });
        if (st) st.textContent = "تعذر الحفظ";
      })
      .then(function () {
        delete tplSaveInFlight[key];
        refreshMaTplDebugCounters();
      });
  }

  function loadTemplates(forceRefresh) {
    forceRefresh = !!forceRefresh;
    ensureMaTplRootDelegates();
    var perfNow =
      typeof performance !== "undefined" && performance.now
        ? function () {
            return performance.now();
          }
        : function () {
            return Date.now();
          };

    var wall0 = perfNow();

    function wallMs() {
      return Math.round(perfNow() - wall0);
    }

    if (!forceRefresh && window.__trigger_templates_dom_ready) {
      var rReady = byId("ma-tpl-root");
      if (
        rReady &&
        rReady.isConnected &&
        rReady.querySelector("[data-ma-tpl-key]")
      ) {
        refreshMaTplDebugCounters();
        tplDbg("[TEMPLATE RELOAD SKIP]", {
          duration_ms: wallMs(),
          source: "dom_already_ready",
        });
        return;
      }
      window.__trigger_templates_dom_ready = false;
    }

    if (!forceRefresh && window.__trigger_templates_loading) {
      trigLog("[TRIGGER LOAD SKIP ALREADY_LOADING]", {
        duration_ms: wallMs(),
        status: "(in_flight)",
        payload_keys: window.__trigger_templates_loaded
          ? payloadKeys(window.__trigger_templates_loaded.json)
          : "(none)",
      });
      return;
    }

    var cached = window.__trigger_templates_loaded;
    if (!forceRefresh && snapshotCacheOk(cached)) {
      tplDbg("[TEMPLATE RELOAD START]", {
        duration_ms: 0,
        source: "memory_cache",
        status: cached.httpStatus,
        payload_keys: payloadKeys(cached.json),
      });
      trigLog("[TRIGGER LOAD START]", {
        duration_ms: 0,
        source: "memory_cache",
        status: cached.httpStatus,
        payload_keys: payloadKeys(cached.json),
      });
      var rCache = byId("ma-tpl-root");
      var cacheHasCards =
        rCache &&
        rCache.isConnected &&
        rCache.querySelector("[data-ma-tpl-key]");
      if (!cacheHasCards && rCache && rCache.isConnected) {
        rCache.innerHTML =
          '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري عرض القوالب…</div>';
      }
      if (cacheHasCards) {
        window.__trigger_templates_dom_ready = true;
        try {
          lastPayload = normalizeTriggerTemplatesPayload(
            cached.json,
            cached.httpStatus
          );
        } catch (_cacheNormErr) {
          /* fall through to render */
        }
        tplDbg("[TEMPLATE RELOAD SUCCESS]", {
          duration_ms: wallMs(),
          status: cached.httpStatus,
          source: "memory_cache_skip_render",
        });
        refreshMaTplDebugCounters();
        return;
      }
      renderWhenRootReady(
        cached.json,
        cached.httpStatus,
        0,
        function (okDom) {
          if (okDom) {
            tplDbg("[TEMPLATE RELOAD SUCCESS]", {
              duration_ms: wallMs(),
              status: cached.httpStatus,
              payload_keys: payloadKeys(cached.json),
              source: "memory_cache",
            });
            trigLog("[TRIGGER LOAD SUCCESS]", {
              duration_ms: wallMs(),
              status: cached.httpStatus,
              payload_keys: payloadKeys(cached.json),
              source: "memory_cache",
            });
          } else {
            tplDbg("[TEMPLATE RELOAD FAIL]", {
              duration_ms: wallMs(),
              status: cached.httpStatus,
              payload_keys: payloadKeys(cached.json),
              source: "memory_cache_dom",
              failure_class: "dom_render",
            });
            trigLog("[TRIGGER LOAD ERROR]", {
              duration_ms: wallMs(),
              status: cached.httpStatus,
              payload_keys: payloadKeys(cached.json),
              source: "memory_cache_dom",
            });
          }
        },
        window.__trigger_templates_apply_gen
      );
      return;
    }

    cancelTplGetInFlight();
    var fetchGen = bumpTplApplyGen();
    var fetchAbort =
      typeof AbortController !== "undefined" ? new AbortController() : null;
    tplGetAbort = fetchAbort;

    window.__trigger_templates_loading = true;
    tplMetrics.get_fetches_started++;
    tplMetrics.get_in_flight++;
    tplDbg("[TEMPLATE RELOAD START]", {
      duration_ms: 0,
      source: "network_fetch",
      status: "(pending)",
      payload_keys: "(request)",
      apply_gen: fetchGen,
      endpoint: FETCH_URL_GET,
    });
    trigLog("[TRIGGER LOAD START]", {
      duration_ms: 0,
      source: "network_fetch",
      status: "(pending)",
      payload_keys: "(request)",
      apply_gen: fetchGen,
    });

    var shell = byId("ma-tpl-root");
    if (shell && shell.isConnected && !shell.querySelector("[data-ma-tpl-key]")) {
      shell.innerHTML =
        '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري تحميل القوالب…</div>';
    }

    var sawRetry = false;

    function runFetch(isRetry) {
      var t0 = perfNow();
      var fetchOpts = { credentials: "same-origin" };
      if (fetchAbort && fetchAbort.signal) {
        fetchOpts.signal = fetchAbort.signal;
      }

      fetch(tplTriggerTemplatesGetUrl(), fetchOpts)
        .then(function (resp) {
          var st = resp.status;
          return resp.json().then(
            function (json) {
              return {
                status: st,
                json: json,
                parse_failed: false,
              };
            },
            function () {
              return { status: st, json: null, parse_failed: true };
            }
          );
        })
        .then(function (pack) {
          if (!applyGenIsCurrent(fetchGen)) {
            tplDbg("[TEMPLATE RELOAD FAIL]", {
              duration_ms: wallMs(),
              status:
                typeof pack.status === "number" ? pack.status : "(unknown)",
              apply_gen: fetchGen,
              current_gen: window.__trigger_templates_apply_gen,
              failure_class: "stale_response_after_save",
              fetch_ms: Math.round(perfNow() - t0),
            });
            window.__trigger_templates_loading = false;
            tplMetrics.get_in_flight = Math.max(0, tplMetrics.get_in_flight - 1);
            return;
          }
          var fetchMs = Math.round(perfNow() - t0);
          var httpOk =
            typeof pack.status === "number" &&
            pack.status >= 200 &&
            pack.status < 300;
          var gotJson =
            pack.json != null &&
            typeof pack.json === "object" &&
            !pack.parse_failed;

          var normProbe = null;
          if (httpOk && gotJson) {
            try {
              normProbe = normalizeTriggerTemplatesPayload(
                pack.json,
                pack.status
              );
            } catch (probErrUnused) {
              normProbe = null;
            }
          }

          var dataUsable =
            !!(
              normProbe &&
              normProbe.ok &&
              normProbe.reason_rows &&
              normProbe.reason_rows.length
            );

          var shouldRetryFetch =
            !isRetry &&
            !sawRetry &&
            (!httpOk || !gotJson || pack.parse_failed || !dataUsable);

          if (shouldRetryFetch) {
            sawRetry = true;
            trigLog("[TRIGGER LOAD RETRY]", {
              duration_ms: fetchMs,
              status:
                typeof pack.status === "number" ? pack.status : "(unknown)",
              payload_keys: payloadKeys(pack.json || {}),
              after_ms: 500,
            });
            window.setTimeout(function () {
              runFetch(true);
            }, 500);
            return;
          }

          if (!httpOk || !gotJson || !dataUsable) {
            tplDbg("[TEMPLATE RELOAD FAIL]", {
              duration_ms: wallMs(),
              status:
                typeof pack.status === "number" ? pack.status : "(unknown)",
              payload_keys: payloadKeys(pack.json || {}),
              phase: isRetry ? "after_retry" : "immediate",
              fetch_ms: fetchMs,
              apply_gen: fetchGen,
              failure_class: !httpOk
                ? "http_error"
                : !gotJson
                  ? "json_parse"
                  : "payload_unusable",
            });
            trigLog("[TRIGGER LOAD ERROR]", {
              duration_ms: wallMs(),
              status:
                typeof pack.status === "number" ? pack.status : "(unknown)",
              payload_keys: payloadKeys(pack.json || {}),
              phase: isRetry ? "after_retry" : "immediate",
              fetch_ms: fetchMs,
            });
            window.__trigger_templates_loading = false;
            var fallbackPayload = buildClientFallbackPayload();
            window.__trigger_templates_loaded = {
              json: fallbackPayload,
              httpStatus: 200,
            };
            renderWhenRootReady(
              fallbackPayload,
              200,
              0,
              function (okFb) {
                var errBanner = byId("ma-tpl-load-err");
                if (errBanner) {
                  errBanner.hidden = !!okFb;
                }
              },
              fetchGen
            );
            tplMetrics.get_in_flight = Math.max(0, tplMetrics.get_in_flight - 1);
            return;
          }

          window.__trigger_templates_loaded = {
            json: pack.json,
            httpStatus: pack.status,
          };

          renderWhenRootReady(
            pack.json,
            pack.status,
            0,
            function (okDom) {
              window.__trigger_templates_loading = false;
              tplMetrics.get_in_flight = Math.max(
                0,
                tplMetrics.get_in_flight - 1
              );
              var meta = {
                duration_ms: wallMs(),
                status: pack.status,
                payload_keys: payloadKeys(pack.json),
                fetch_ms: fetchMs,
                apply_gen: fetchGen,
              };
              if (okDom) {
                tplDbg("[TEMPLATE RELOAD SUCCESS]", meta);
                trigLog("[TRIGGER LOAD SUCCESS]", meta);
              } else {
                meta.phase = "dom_timeout_or_render";
                meta.failure_class = "dom_render";
                tplDbg("[TEMPLATE RELOAD FAIL]", meta);
                trigLog("[TRIGGER LOAD ERROR]", meta);
              }
            },
            fetchGen
          );
        })
        .catch(function (netErr) {
          if (netErr && netErr.name === "AbortError") {
            window.__trigger_templates_loading = false;
            tplMetrics.get_in_flight = Math.max(0, tplMetrics.get_in_flight - 1);
            tplDbg("[TEMPLATE RELOAD ABORT]", {
              apply_gen: fetchGen,
              current_gen: window.__trigger_templates_apply_gen,
            });
            return;
          }
          if (!applyGenIsCurrent(fetchGen)) {
            window.__trigger_templates_loading = false;
            tplMetrics.get_in_flight = Math.max(0, tplMetrics.get_in_flight - 1);
            return;
          }
          var fetchMsCatch = Math.round(perfNow() - t0);
          if (!isRetry && !sawRetry) {
            sawRetry = true;
            trigLog("[TRIGGER LOAD RETRY]", {
              duration_ms: fetchMsCatch,
              status: "(network)",
              payload_keys: "(none)",
              after_ms: 500,
              err: String(netErr && netErr.message ? netErr.message : netErr),
            });
            window.setTimeout(function () {
              runFetch(true);
            }, 500);
            return;
          }
          tplDbg("[TEMPLATE RELOAD FAIL]", {
            duration_ms: wallMs(),
            status: "(network)",
            payload_keys: "(none)",
            phase: "fetch_catch_final",
            fetch_ms: fetchMsCatch,
            apply_gen: fetchGen,
            failure_class: "network_or_timeout",
            err: String(netErr && netErr.message ? netErr.message : netErr),
          });
          trigLog("[TRIGGER LOAD ERROR]", {
            duration_ms: wallMs(),
            status: "(network)",
            payload_keys: "(none)",
            phase: "fetch_catch_final",
            fetch_ms: fetchMsCatch,
            err: String(netErr && netErr.message ? netErr.message : netErr),
          });
          window.__trigger_templates_loading = false;
          tplMetrics.get_in_flight = Math.max(0, tplMetrics.get_in_flight - 1);
          var fallbackNet = buildClientFallbackPayload();
          window.__trigger_templates_loaded = {
            json: fallbackNet,
            httpStatus: 200,
          };
          renderWhenRootReady(
            fallbackNet,
            200,
            0,
            function (okNet) {
              var errBanner = byId("ma-tpl-load-err");
              if (errBanner) {
                errBanner.hidden = !!okNet;
              }
            },
            fetchGen
          );
        });
    }

    runFetch(false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureMaTplRootDelegates);
  } else {
    ensureMaTplRootDelegates();
  }

  window.maEnsureTriggerTemplatesLoaded = loadTemplates;
})();
