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
   * مسودات جاهزة لكل سبب — نص ثابت فقط؛ بدون أي استعلام إضافي أو ذكاء منتج بعد.
   * لاحقاً: يمكن أن يستبدل ‎Product Intelligence‎ نصاً حسب ‎SKU / مخزون / عروض‎؛
   * يبقى الحقل المعرفي `type` كمرساة لذلك دون تغيير مسار الاسترجاع الحالي.
   */
  var PRESET_SUGGESTIONS_BY_REASON = {
    price: [
      {
        type: "reassurance",
        label: "طمأنة",
        text: "نحب نطمّنك 👍 أي استفسار عن السعر أو طريقة الدفع نقدر نوضّحه باختصار.",
      },
      {
        type: "offer",
        label: "عرض",
        text: "إذا يناسبك، نقدر نشوف لك عرضاً أو خياراً يلائم ميزانيتك — قولنا ونساعدك.",
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
        text: "الجودة عندنا خط واضح 👍 أي نقطة تحتاج طمأنة نجاوبك بكل صراحة.",
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
        text: "بخصوص الشحن: نقدر نوضّح لك المدة والتكلفة والخيارات المتاحة لمنطقتك.",
      },
      {
        type: "offer",
        label: "عرض شحن",
        text: "إذا في عرض شحن أو خيار أوفر يناسبك، نراجعه معك بلطف.",
      },
      {
        type: "special_followup",
        label: "متابعة خاصة",
        text: "نقدر نتابع معك بشكل خاص لحد ما ترتاح من تفاصيل الشحن والتسليم.",
      },
    ],
    delivery: [
      {
        type: "shipping_info",
        label: "توضيح الموعد",
        text: "بخصوص موعد التوصيل: نعطيك توقيتاً تقريبياً واضحاً يناسب عنوانك.",
      },
      {
        type: "offer",
        label: "تسريع إن أمكن",
        text: "إذا أمكن تسريع التوصيل أو خيار أسرع، نبلغك بما هو متاح 👍",
      },
      {
        type: "special_followup",
        label: "متابعة خاصة",
        text: "نقدر متابعة خاصة معك لمتابعة الطلب وتوضيح الموعد خطوة بخطوة.",
      },
    ],
    warranty: [
      {
        type: "reassurance",
        label: "طمأنة",
        text: "الضمان جزء من راحتك 👍 أي سؤال نجاوبك بوضوح.",
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
        text: "نحنا هنا نساعدك 🙏 أي استفسار عام عن الطلب أو المتجر قولنا باختصار.",
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

  function presetChipsHtml(rowKey) {
    var list = PRESET_SUGGESTIONS_BY_REASON[rowKey] || [];
    if (!list.length) return "";
    var chunks = [];
    var i;
    for (i = 0; i < list.length; i++) {
      var p = list[i];
      chunks.push(
        '<button type="button" class="ma-tpl-preset-chip" data-ma-tpl-preset data-ma-tpl-reason="' +
        esc(rowKey) +
        '" data-ma-tpl-preset-type="' +
        esc(p.type) +
        '" data-ma-tpl-preset-i="' +
        i +
        '">' +
        esc(p.label) +
        "</button>"
      );
    }
    return (
      '<div class="ma-tpl-preset-wrap" dir="rtl">' +
      '<span class="ma-tpl-preset-hint">مسودات جاهزة:</span>' +
      '<div class="ma-tpl-preset-row">' +
      chunks.join("") +
      "</div></div>"
    );
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

  function buildRowFromTemplateEntry(key, ent) {
    ent = ent && typeof ent === "object" ? ent : {};
    var msgs = Array.isArray(ent.messages) ? ent.messages.slice(0, 3) : [];
    var first = msgs[0] && typeof msgs[0] === "object" ? msgs[0] : {};
    var dv = typeof first.delay === "number" ? first.delay : parseFloat(first.delay);
    if (!(dv > 0)) dv = typeof ent.delay_value === "number" ? ent.delay_value : parseFloat(ent.delay_value);
    if (!(dv > 0)) dv = 1;
    var unitRaw = first.unit != null ? first.unit : ent.delay_unit;
    var u = normalizeApiDelayUnit(unitRaw) === "hour" ? "hour" : "minute";
    var msgText = String(ent.message || first.text || "").trim();
    var mc = parseInt(ent.message_count, 10);
    if (!(mc >= 1)) mc = 1;
    mc = Math.max(1, Math.min(3, mc));
    return {
      key: key,
      label_ar: String(ent.label_ar || LABEL_BY_KEY[key] || key),
      enabled: ent.enabled !== false,
      message: msgText,
      delay_value: dv,
      delay_unit: u,
      message_count: mc,
      messages: msgs,
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
      out.push(buildRowFromTemplateEntry(k0, byKey[k0] || {}));
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
    } catch (unusedUnused) {}
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
    var presetRow = presetChipsHtml(keyRaw || row.key || "");

    var mcOpts = [1, 2, 3]
      .map(function (n) {
        var sel = n === mc ? " selected" : "";
        return '<option value="' + n + '"' + sel + ">" + n + "</option>";
      })
      .join("");

    return (
      '<div class="ma-tpl-card" data-ma-tpl-key="' +
      k +
      '">' +
      '<div class="ma-tpl-card-head">' +
      '<span class="ma-tpl-chip">' +
      lbl +
      "</span>" +
      "</div>" +
      '<label class="ma-tpl-check"><input type="checkbox" data-ma-tpl-enabled' +
      en +
      "> تفعيل قالب الاسترجاع لهذا السبب</label>" +
      '<label class="ma-tpl-lbl" for="ma-tpl-msg-' +
      k +
      '">نص الرسالة (المحاولة الأولى في السلسلة)</label>' +
      '<textarea class="ma-tpl-input ma-tpl-ta" id="ma-tpl-msg-' +
      k +
      '" rows="5" maxlength="65535" data-ma-tpl-msg dir="rtl" placeholder="النص الموجّه للعميل عبر مسار الاسترجاع…">' +
      msg +
      "</textarea>" +
      presetRow +
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
      '<div><label class="ma-tpl-lbl" for="ma-tpl-mc-' +
      k +
      '">عدد رسائل السلسلة</label>' +
      '<select class="ma-tpl-input" id="ma-tpl-mc-' +
      k +
      '" data-ma-tpl-msg-count>' +
      mcOpts +
      "</select></div>" +
      "</div>" +
      '<p class="ma-tpl-hint">محاولات إضافية (٢–٣) تُكمَل من المحتوى المحفوظ مسبقاً أو من النصوص الافتراضية المرشدة عند عدم وجودها.</p>' +
      '<div class="ma-tpl-actions">' +
      '<button type="button" class="ma-fw-save" data-ma-tpl-save>حفظ</button>' +
      '<span class="ma-tpl-status" data-ma-tpl-status aria-live="polite"></span>' +
      "</div>" +
      "</div>"
    );
  }

  function render(raw, httpStatus) {
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
      lastPayload = null;
      if (err) err.hidden = false;
      root.innerHTML =
        '<div class="empty-text" style="padding:24px;text-align:center;">تعذر تحميل القوالب</div>';
      return;
    }

    if (sub && payload.section_subtitle_ar) {
      sub.textContent = payload.section_subtitle_ar;
    }

    if (!payload.ok || !payload.reason_rows || payload.reason_rows.length === 0) {
      trigLog("[TRIGGER LOAD ERROR]", {
        phase: "unusable_payload",
        payload_keys: payloadKeys(raw),
        status: httpStatus,
      });
      lastPayload = null;
      if (err) err.hidden = false;
      root.innerHTML =
        '<div class="empty-text" style="padding:24px;text-align:center;">تعذر تحميل القوالب</div>';
      return;
    }

    if (err) err.hidden = true;

    try {
      root.innerHTML =
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
      lastPayload = null;
      if (err) err.hidden = false;
      root.innerHTML =
        '<div class="empty-text" style="padding:24px;text-align:center;">تعذر تحميل القوالب</div>';
      return;
    }

    lastPayload = payload;

    if (typeof root._maTplClickDelegate === "function") {
      root.removeEventListener("click", root._maTplClickDelegate);
    }
    root._maTplClickDelegate = function (ev) {
      var tg = ev.target;
      var chip =
        tg && tg.closest ? tg.closest("[data-ma-tpl-preset]") : null;
      if (chip && root.contains(chip)) {
        ev.preventDefault();
        var rk = chip.getAttribute("data-ma-tpl-reason");
        var ix = parseInt(chip.getAttribute("data-ma-tpl-preset-i"), 10);
        var arr = PRESET_SUGGESTIONS_BY_REASON[rk];
        if (!arr || !(ix >= 0) || !arr[ix]) return;
        var cardShell = chip.closest("[data-ma-tpl-key]");
        var taPick =
          cardShell && cardShell.querySelector("[data-ma-tpl-msg]");
        if (taPick) {
          taPick.value = arr[ix].text || "";
          taPick.focus();
        }
        return;
      }
      var saveB =
        tg && tg.closest ? tg.closest("[data-ma-tpl-save]") : null;
      if (saveB && root.contains(saveB)) {
        ev.preventDefault();
        var cardS = saveB.closest("[data-ma-tpl-key]");
        if (cardS) saveOne(cardS.getAttribute("data-ma-tpl-key"), cardS);
      }
    };
    root.addEventListener("click", root._maTplClickDelegate);
  }

  /** يرسم بعد توفر الحاوية (تجنّب فشل ‎SPA‎ عند تفعيل الصفحة قبل بناء DOM). */
  function renderWhenRootReady(raw, httpStatus, domAttempt, onDone) {
    var root = byId("ma-tpl-root");
    if (root && root.isConnected) {
      render(raw, httpStatus);
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
      renderWhenRootReady(raw, httpStatus, domAttempt + 1, onDone);
    }, DOM_POLL_MS);
  }

  function findRow(key) {
    if (!lastPayload || !lastPayload.reason_rows) return null;
    for (var i = 0; i < lastPayload.reason_rows.length; i++) {
      if (lastPayload.reason_rows[i].key === key) return lastPayload.reason_rows[i];
    }
    return null;
  }

  function buildMessagesSlice(key, text, dv, unit, mc) {
    var prevRow = findRow(key);
    var prevMsgs = prevRow && Array.isArray(prevRow.messages) ? prevRow.messages.slice() : [];

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
      var baseDly = i === 0 ? dv : 120;
      var baseUnit = i === 0 ? unit : "minute";
      return { delay: baseDly, unit: baseUnit, text: i === 0 ? text : text };
    }

    var out = [];
    for (var j = 0; j < mc; j++) {
      var sl = slot(j);
      if (j === 0) {
        sl.text = text;
        var enc = persistFirstSlotDelay(dv, unit);
        sl.delay = enc.delay;
        sl.unit = enc.unit;
      }
      out.push(sl);
    }
    return out;
  }

  function saveOne(key, card) {
    if (!key || !card) return;
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

    var messages = buildMessagesSlice(key, text, dv, unit, mc);

    var body = {
      reason_templates: {},
    };
    body.reason_templates[key] = {
      enabled: !!(ena && ena.checked),
      message: text,
      message_count: mc,
      messages: messages,
    };

    if (st) st.textContent = "جاري الحفظ…";

    fetch(FETCH_URL_POST, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok && j.ok, payload: j, httpStatus: r.status };
        });
      })
      .then(function (pack) {
        if (pack.ok && pack.payload) {
          window.__trigger_templates_loaded = {
            json: pack.payload,
            httpStatus:
              typeof pack.httpStatus === "number" ? pack.httpStatus : 200,
          };
          renderWhenRootReady(
            pack.payload,
            typeof pack.httpStatus === "number" ? pack.httpStatus : 200,
            0,
            function () {}
          );
          var newCard = document.querySelector('[data-ma-tpl-key="' + key + '"]');
          var st2 =
            newCard && newCard.querySelector("[data-ma-tpl-status]");
          if (st2) st2.textContent = "تم الحفظ";
          window.setTimeout(function () {
            if (st2 && st2.textContent === "تم الحفظ") st2.textContent = "";
          }, 3500);
        } else if (st) {
          st.textContent = "تعذر الحفظ";
        }
      })
      .catch(function () {
        if (st) st.textContent = "تعذر الحفظ";
      });
  }

  function loadTemplates(forceRefresh) {
    forceRefresh = !!forceRefresh;
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
      trigLog("[TRIGGER LOAD START]", {
        duration_ms: 0,
        source: "memory_cache",
        status: cached.httpStatus,
        payload_keys: payloadKeys(cached.json),
      });
      var rCache = byId("ma-tpl-root");
      if (rCache && rCache.isConnected) {
        rCache.innerHTML =
          '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري عرض القوالب…</div>';
      }
      renderWhenRootReady(cached.json, cached.httpStatus, 0, function (okDom) {
        if (okDom) {
          trigLog("[TRIGGER LOAD SUCCESS]", {
            duration_ms: wallMs(),
            status: cached.httpStatus,
            payload_keys: payloadKeys(cached.json),
            source: "memory_cache",
          });
        } else {
          trigLog("[TRIGGER LOAD ERROR]", {
            duration_ms: wallMs(),
            status: cached.httpStatus,
            payload_keys: payloadKeys(cached.json),
            source: "memory_cache_dom",
          });
        }
      });
      return;
    }

    window.__trigger_templates_loading = true;
    trigLog("[TRIGGER LOAD START]", {
      duration_ms: 0,
      source: "network_fetch",
      status: "(pending)",
      payload_keys: "(request)",
    });

    var shell = byId("ma-tpl-root");
    if (shell && shell.isConnected) {
      shell.innerHTML =
        '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري تحميل القوالب…</div>';
    }

    var sawRetry = false;

    function runFetch(isRetry) {
      var t0 = perfNow();

      fetch(FETCH_URL_GET, { credentials: "same-origin" })
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
            trigLog("[TRIGGER LOAD ERROR]", {
              duration_ms: wallMs(),
              status:
                typeof pack.status === "number" ? pack.status : "(unknown)",
              payload_keys: payloadKeys(pack.json || {}),
              phase: isRetry ? "after_retry" : "immediate",
              fetch_ms: fetchMs,
            });
            window.__trigger_templates_loading = false;
            renderWhenRootReady(
              pack.json || {},
              typeof pack.status === "number" ? pack.status : 0,
              0,
              function () {}
            );
            return;
          }

          window.__trigger_templates_loaded = {
            json: pack.json,
            httpStatus: pack.status,
          };

          renderWhenRootReady(pack.json, pack.status, 0, function (okDom) {
            window.__trigger_templates_loading = false;
            var meta = {
              duration_ms: wallMs(),
              status: pack.status,
              payload_keys: payloadKeys(pack.json),
              fetch_ms: fetchMs,
            };
            if (okDom) {
              trigLog("[TRIGGER LOAD SUCCESS]", meta);
            } else {
              meta.phase = "dom_timeout_or_render";
              trigLog("[TRIGGER LOAD ERROR]", meta);
            }
          });
        })
        .catch(function (netErr) {
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
          trigLog("[TRIGGER LOAD ERROR]", {
            duration_ms: wallMs(),
            status: "(network)",
            payload_keys: "(none)",
            phase: "fetch_catch_final",
            fetch_ms: fetchMsCatch,
            err: String(netErr && netErr.message ? netErr.message : netErr),
          });
          window.__trigger_templates_loading = false;
          renderWhenRootReady({}, 0, 0, function () {});
        });
    }

    runFetch(false);
  }

  window.maEnsureTriggerTemplatesLoaded = loadTemplates;
})();
