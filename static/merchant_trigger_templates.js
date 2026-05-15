/**
 * Lazy-load قسم «قوالب حسب سبب التردد» — لا يُحمّل حتى الدخول للصفحة (#trigger-templates).
 */
(function () {
  "use strict";

  var FETCH_URL_GET = "/api/dashboard/trigger-templates";
  var FETCH_URL_POST = "/api/dashboard/trigger-templates";
  var lastPayload = null;
  var loadInFlight = false;

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

  /** نصوص مساعدة ثابتة في الواجهة فقط — لا تُفرض على الحقل ولا تستبدل المحفوظ. */
  var SUGGESTED_BY_KEY = {
    price:
      "واضح إن السعر مهم لك 👍 إذا تحب نساعدك بخيار أنسب أو نوضح القيمة أكثر",
    quality:
      "الجودة تهمنا مثلك 👍 أي استفسار عن المواصفات أو المطابقة نقدر نلخصلك بسرعة",
    shipping: "إذا عندك استفسار عن الشحن أو المدة، نقدر نوضحها لك",
    delivery:
      "بخصوص مدة التوصيل، نقدر نعطيك وقت تقريبي يناسب منطقتك 👍",
    warranty:
      "إذا عندك سؤال عن الضمان أو التغطية، نوضّح لك النقاط المهمة باختصار",
    other:
      "لاحظنا ما كمّلت الطلب 👍 إذا في شي وقفك، قولنا ونشوف لك حل بسيط",
  };

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
    var sugRaw = String(SUGGESTED_BY_KEY[row.key] || "").trim();
    var sug = esc(sugRaw);
    var sugBlock =
      sugRaw.length > 0
        ? '<div class="ma-tpl-suggest">' +
          '<p class="ma-tpl-suggest-lbl">اقتراح:</p>' +
          '<div class="ma-tpl-suggest-row">' +
          '<p class="ma-tpl-suggest-txt" data-ma-tpl-suggest-txt dir="rtl">' +
          sug +
          "</p>" +
          '<button type="button" class="ma-tpl-copy" data-ma-tpl-copy-suggest>نسخ</button>' +
          "</div></div>"
        : "";

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
      sugBlock +
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
      console.log("[TRIGGER TEMPLATES LOAD ERROR] normalize", normErr);
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
      console.log("[TRIGGER TEMPLATES LOAD ERROR] unusable payload", raw);
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
      console.log("[TRIGGER TEMPLATES LOAD ERROR] render", renderErr);
      lastPayload = null;
      if (err) err.hidden = false;
      root.innerHTML =
        '<div class="empty-text" style="padding:24px;text-align:center;">تعذر تحميل القوالب</div>';
      return;
    }

    lastPayload = payload;

    root.querySelectorAll("[data-ma-tpl-save]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var card = btn.closest("[data-ma-tpl-key]");
        if (card) saveOne(card.getAttribute("data-ma-tpl-key"), card);
      });
    });

    root.querySelectorAll("[data-ma-tpl-copy-suggest]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var card = btn.closest("[data-ma-tpl-key]");
        if (!card) return;
        var el = card.querySelector("[data-ma-tpl-suggest-txt]");
        var ta = card.querySelector("[data-ma-tpl-msg]");
        var rawTxt = el ? el.textContent || "" : "";
        if (!rawTxt.trim()) return;
        function done(copyOk) {
          var st = card.querySelector("[data-ma-tpl-status]");
          if (st) st.textContent = copyOk ? "تم النسخ" : "تعذر النسخ";
          if (copyOk && ta) {
            ta.focus();
          }
          window.setTimeout(function () {
            if (st && (st.textContent === "تم النسخ" || st.textContent === "تعذر النسخ")) {
              st.textContent = "";
            }
          }, 2500);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(rawTxt.trim()).then(
            function () {
              done(true);
            },
            function () {
              done(false);
            }
          );
        } else {
          done(false);
        }
      });
    });
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
          render(pack.payload, pack.httpStatus);
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

  function loadTemplates() {
    if (loadInFlight) return;
    var root = byId("ma-tpl-root");
    if (!root) return;

    loadInFlight = true;
    console.log("[TRIGGER TEMPLATES LOAD START]");
    root.innerHTML =
      '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري تحميل القوالب…</div>';

    fetch(FETCH_URL_GET, { credentials: "same-origin" })
      .then(function (r) {
        var status = r.status;
        return r.json().then(
          function (json) {
            return { status: status, json: json };
          },
          function (parseErr) {
            console.log("[TRIGGER TEMPLATES LOAD ERROR] json parse", parseErr);
            return { status: status, json: null };
          }
        );
      })
      .then(function (pack) {
        if (!pack.json) {
          console.log("[TRIGGER TEMPLATES LOAD ERROR] empty body");
          render({}, pack.status);
          return;
        }
        render(pack.json, pack.status);
        var norm = lastPayload;
        if (norm && norm.ok && norm.reason_rows && norm.reason_rows.length) {
          console.log(
            "[TRIGGER TEMPLATES LOAD SUCCESS]",
            norm.reason_rows.length
          );
        } else {
          console.log("[TRIGGER TEMPLATES LOAD ERROR]", "not ok or no rows");
        }
      })
      .catch(function (e) {
        console.log("[TRIGGER TEMPLATES LOAD ERROR]", e);
        render({}, 0);
      })
      .finally(function () {
        loadInFlight = false;
      });
  }

  window.maEnsureTriggerTemplatesLoaded = loadTemplates;
})();
