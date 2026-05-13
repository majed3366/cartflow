/**
 * DOM-only presenters for the storefront bubble (flows supply copy + handlers).
 */
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime || {};
  var WIDGET_BODY_SELECTOR = ".cartflow-widget-body";
  var rowStyleCol =
    "display:flex;flex-direction:column;gap:10px;margin-top:4px;width:100%;box-sizing:border-box;";

  function bubbleRoot() {
    return document.querySelector("[data-cartflow-bubble]");
  }

  function stripChromeKeep(w) {
    var body = w.querySelector(WIDGET_BODY_SELECTOR);
    if (body) {
      while (body.firstChild) {
        body.removeChild(body.firstChild);
      }
      return body;
    }
    return null;
  }

  function ensureBubble(primaryHex) {
    var w =
      bubbleRoot() ||
      (function () {
        var el = document.createElement("div");
        el.setAttribute("data-cartflow-bubble", "1");
        el.setAttribute("data-cf-reason-entry", "v2");
        document.body.appendChild(el);
        return el;
      })();

    var fill = primaryHex || "#6C5CE7";
    w.style.cssText =
      "position:fixed;z-index:2147483640;max-width:min(340px,calc(100vw - 24px));" +
      "right:max(14px,env(safe-area-inset-right));bottom:max(14px,env(safe-area-inset-bottom));" +
      "box-sizing:border-box;padding:14px;border-radius:16px;background:rgba(249,247,254,1);" +
      "color:#17202a;box-shadow:0 24px 64px rgba(15,23,42,.48), 0 4px 12px rgba(15,23,42,.08);" +
      "font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;font-size:15px;line-height:1.45;";
    if (!w.querySelector('[data-cf-chrome="1"]')) {
      var bar = document.createElement("div");
      bar.setAttribute("data-cf-chrome", "1");
      bar.style.cssText =
        "height:4px;border-radius:999px;margin:0 0 10px 0;background:" + fill + ";";
      w.appendChild(bar);
    }
    if (!w.querySelector(WIDGET_BODY_SELECTOR)) {
      var inner = document.createElement("div");
      inner.className = "cartflow-widget-body";
      inner.style.cssText = "display:block;";
      w.appendChild(inner);
    }
    try {
      w.style.display = "block";
      w.style.visibility = "visible";
    } catch (eVis) {}
    return w;
  }

  function stampPrimary(btn, primaryHex) {
    var hex = primaryHex || "#6C5CE7";
    btn.style.cssText =
      "border:1px solid rgba(148,163,184,.58);cursor:pointer;display:inline-flex;align-items:center;" +
      "justify-content:flex-start;text-align:start;border-radius:10px;background:" +
      hex +
      ";color:#fff;width:100%;box-sizing:border-box;padding:11px 12px;line-height:1.45;" +
      "font-weight:600;";
  }

  function clear(primaryHex) {
    var w = ensureBubble(primaryHex);
    stripChromeKeep(w);
  }

  function renderYesNo(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 12px;font-size:14px;line-height:1.5;";
    p.textContent = opts.question || "";
    body.appendChild(p);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    var by = document.createElement("button");
    by.type = "button";
    by.textContent = opts.yes || "نعم";
    stampPrimary(by, ph);
    by.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      opts.onYes();
    });
    var bn = document.createElement("button");
    bn.type = "button";
    bn.textContent = opts.no || "لا";
    bn.style.cssText =
      by.style.cssText.replace(/background[^;]+;/, "background:transparent;color:#4338CA;");
    bn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      opts.onNo();
    });
    row.appendChild(by);
    row.appendChild(bn);
    body.appendChild(row);
  }

  function btnGhostStyle(primaryHex) {
    return (
      "border:1px solid rgba(148,163,184,.52);cursor:pointer;border-radius:10px;background:transparent;color:" +
      primaryHex +
      ";width:auto;padding:8px 12px;"
    );
  }

  function renderReasonGrid(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 12px;";
    p.textContent = opts.title || "وش أكثر شيء مخليك متردد؟ تبيني أساعدك";
    body.appendChild(p);
    var row = document.createElement("div");
    row.setAttribute("data-cf-reason-row-v2", "1");
    row.style.cssText =
      "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;";
    opts.rows.forEach(function (item) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = item.label;
      stampPrimary(b, ph);
      b.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        opts.onPick(item);
      });
      row.appendChild(b);
    });
    body.appendChild(row);
    if (opts.onBack) {
      var back = document.createElement("button");
      back.type = "button";
      back.style.cssText = "margin-top:10px;" + btnGhostStyle(ph);
      back.textContent = "رجوع";
      back.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        opts.onBack();
      });
      body.appendChild(back);
    }
  }

  function renderBrowsingChoices(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 12px;font-size:14px;line-height:1.5;";
    p.textContent = opts.title || "";
    body.appendChild(p);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    (opts.buttons || []).forEach(function (b) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = b.label;
      stampPrimary(btn, ph);
      btn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        b.onActivate();
      });
      row.appendChild(btn);
    });
    body.appendChild(row);
  }

  function renderPhoneStep(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var t = document.createElement("p");
    t.style.cssText = "margin:0 0 10px;font-size:14px;line-height:1.4;font-weight:700;";
    t.textContent = "رقم الجوال لإكمال المتابعة";
    body.appendChild(t);
    var s = document.createElement("p");
    s.style.cssText = "margin:0 0 10px;font-size:13px;opacity:.9;";
    s.textContent = "نستخدمه فقط لمتابعة طلبك إذا احتجت مساعدة.";
    body.appendChild(s);
    var inp = document.createElement("input");
    inp.type = "tel";
    inp.placeholder = "05xxxxxxxx";
    inp.setAttribute("dir", "ltr");
    inp.style.cssText =
      "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:10px;margin-bottom:8px;font:inherit;";
    try {
      var norm = Cf.State ? Cf.State.getStoredPhoneNorm() : "";
      if (norm && norm.slice(0, 3) === "966") {
        inp.value = "0" + norm.slice(3);
      }
    } catch (eLs) {}
    body.appendChild(inp);
    var err = document.createElement("p");
    err.style.cssText = "margin:0 0 10px;color:#b91c1c;font-size:13px;";
    err.textContent = "";
    body.appendChild(err);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    var save = document.createElement("button");
    save.type = "button";
    save.textContent = "حفظ الرقم";
    stampPrimary(save, ph);
    var back = document.createElement("button");
    back.type = "button";
    back.textContent = "رجوع";
    back.style.opacity = "0.85";
    back.style.cssText = save.style.cssText + "opacity:0.92;background:#e0e7ff;color:#312e81;";
    back.addEventListener("click", function (e) {
      e.preventDefault();
      opts.onBack();
    });
    save.addEventListener("click", function (e) {
      e.preventDefault();
      err.textContent = "";
      var pn = Cf.State.normalizePhoneDigits(inp.value);
      if (!pn) {
        err.textContent = "رقم غير صحيح";
        return;
      }
      save.setAttribute("disabled", "true");
      opts
        .onSave(pn)
        .then(function () {
          save.removeAttribute("disabled");
        })
        .catch(function () {
          save.removeAttribute("disabled");
          err.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
        });
    });
    row.appendChild(save);
    row.appendChild(back);
    body.appendChild(row);
  }

  function renderContinuation(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var msgs = opts.messages || {};
    var rk = String(opts.reasonKey || "other").toLowerCase();
    var txt =
      msgs[rk] ||
      "تمام 👍\nأنا معك إذا احتجت أي توضيح قبل تكمل الطلب.";
    var p = document.createElement("p");
    p.style.cssText = "margin:0 0 16px;font-size:14px;line-height:1.65;white-space:pre-line;";
    p.textContent = txt;
    body.appendChild(p);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    function add(label, fn) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      stampPrimary(b, ph);
      b.addEventListener("click", function (e) {
        e.preventDefault();
        fn();
      });
      row.appendChild(b);
    }
    add("أكمل الطلب", opts.onContinueCart);
    add("أحتاج مساعدة الآن", opts.onAssist);
    add("رجوع للأسباب", opts.onBackReasons);
    body.appendChild(row);
  }

  function hideBubble() {
    var w = bubbleRoot();
    if (!w) {
      return;
    }
    try {
      w.style.display = "none";
    } catch (eH) {}
  }

  /** “سبب آخر” ملاحظة قصيرة ثم تنفيذ onSubmit(note). */
  function renderOtherDraftForm(opts) {
    var w = ensureBubble(opts.primaryColor);
    var body = stripChromeKeep(w);
    if (!body) {
      return;
    }
    var ph = opts.primaryColor || "#6C5CE7";
    var hi = document.createElement("p");
    hi.style.cssText = "margin:0 0 10px;font-size:13px;line-height:1.5;";
    hi.textContent = "اكتب ملاحظتك باختصار 👇";
    body.appendChild(hi);
    var ta = document.createElement("textarea");
    ta.rows = 3;
    ta.style.cssText =
      "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;resize:vertical;";
    body.appendChild(ta);
    var err = document.createElement("p");
    err.style.cssText = "color:#b91c1c;font-size:13px;margin:4px 0;";
    err.textContent = "";
    body.appendChild(err);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    var send = document.createElement("button");
    send.type = "button";
    send.textContent = "إرسال";
    stampPrimary(send, ph);
    var back = document.createElement("button");
    back.type = "button";
    back.style.cssText = send.style.cssText + "opacity:0.92;background:#e0e7ff;color:#312e81;";
    back.textContent = "رجوع";
    back.addEventListener("click", function (e) {
      e.preventDefault();
      opts.onBack();
    });
    send.addEventListener("click", function (e) {
      e.preventDefault();
      var note = String(ta.value || "").trim();
      if (!note) {
        err.textContent = "اكتب ملاحظة قصيرة";
        return;
      }
      err.textContent = "";
      opts.onSubmit(note);
    });
    row.appendChild(send);
    row.appendChild(back);
    body.appendChild(row);
  }

  /** خيارات فرعية للسبب ”السعر”. */
  function renderPriceBranches(opts) {
    var rows = opts.options || [];
    renderReasonGrid({
      primaryColor: opts.primaryColor,
      title: "وش يناسب وضعك بالنسبة للسعر؟",
      rows: rows,
      onPick: opts.onPick,
      onBack: opts.onBack,
    });
  }

  function showBubble() {
    try {
      var F = Cf.Flows;
      if (F && typeof F.showBubbleCartRecovery === "function") {
        F.showBubbleCartRecovery("__cfV2ShowNow");
        return true;
      }
    } catch (eSb) {}
    try {
      console.warn("[CF V2] Ui.showBubble: Flows.showBubbleCartRecovery not available");
    } catch (eW) {}
    return false;
  }

  window.CartflowWidgetRuntime = Cf;
  window.CartflowWidgetRuntime.Ui = {
    showBubble: showBubble,
    ensureBubble: ensureBubble,
    clearBody: clear,
    renderYesNo: renderYesNo,
    renderReasonGrid: renderReasonGrid,
    renderBrowsingChoices: renderBrowsingChoices,
    renderPhoneStep: renderPhoneStep,
    renderContinuation: renderContinuation,
    renderOtherDraftForm: renderOtherDraftForm,
    renderPriceBranches: renderPriceBranches,
    hideBubble: hideBubble,
    bubbleRoot: bubbleRoot,
  };
})();
