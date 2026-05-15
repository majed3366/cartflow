/**
 * Lazy-load قسم «قوالب حسب سبب التردد» — لا يُحمّل حتى الدخول للصفحة (#trigger-templates).
 */
(function () {
  "use strict";

  var FETCH_URL_GET = "/api/dashboard/trigger-templates";
  var FETCH_URL_POST = "/api/dashboard/trigger-templates";
  var lastPayload = null;
  var loadInFlight = false;

  function byId(id) {
    return document.getElementById(id);
  }

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
  }

  function cardHtml(row) {
    var k = esc(row.key);
    var lbl = esc(row.label_ar);
    var en = row.enabled !== false ? " checked" : "";
    var msg = esc(row.message || "");
    var dv = typeof row.delay_value === "number" ? row.delay_value : parseFloat(row.delay_value) || 1;
    var du = esc(String(row.delay_unit || "minute"));
    var mc = parseInt(row.message_count, 10) || 1;
    mc = Math.max(1, Math.min(3, mc));
    var minSel = du === "hour" ? "" : " selected";
    var hourSel = du === "hour" ? " selected" : "";

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
      ">دقيقة / دقائق</option>" +
      '<option value="hour"' +
      hourSel +
      ">ساعة / ساعات</option>" +
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

  function render(payload) {
    lastPayload = payload;
    var root = byId("ma-tpl-root");
    var sub = byId("ma-tpl-sub");
    var err = byId("ma-tpl-load-err");
    if (!root) return;

    if (sub && payload && payload.section_subtitle_ar) {
      sub.textContent = payload.section_subtitle_ar;
    }

    if (!payload || !payload.ok || !payload.reason_rows) {
      if (err) err.hidden = false;
      root.innerHTML =
        '<div class="empty-text" style="padding:24px;text-align:center;">تعذر تحميل القوالب</div>';
      return;
    }
    if (err) err.hidden = true;

    root.innerHTML =
      '<div class="ma-tpl-grid">' +
      payload.reason_rows.map(cardHtml).join("") +
      "</div>";

    root.querySelectorAll("[data-ma-tpl-save]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var card = btn.closest("[data-ma-tpl-key]");
        if (card) saveOne(card.getAttribute("data-ma-tpl-key"), card);
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
        sl.delay = dv;
        sl.unit = unit;
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
    var unit = dsi && dsi.value === "hour" ? "hour" : "minute";
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
          return { ok: r.ok && j.ok, payload: j };
        });
      })
      .then(function (pack) {
        if (pack.ok && pack.payload) {
          render(pack.payload);
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
    root.innerHTML =
      '<div class="ma-tpl-loading ma-dash-skel" style="padding:32px;text-align:center;color:var(--muted);">جاري تحميل القوالب…</div>';

    fetch(FETCH_URL_GET, { credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        render(d);
      })
      .catch(function () {
        render({ ok: false });
      })
      .finally(function () {
        loadInFlight = false;
      });
  }

  window.maEnsureTriggerTemplatesLoaded = loadTemplates;
})();
