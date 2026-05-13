/**
 * DOM presenters — all views mount through CartflowWidgetRuntime.Shell (single bubble).
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var rowStyleCol =
    "display:flex;flex-direction:column;gap:6px;margin-top:2px;width:100%;box-sizing:border-box;";
  var textPrimary = "margin:0;color:rgba(241,245,249,.95);";
  var textMuted = "margin:0;color:rgba(226,232,240,.82);";

  function bubbleRoot() {
    if (Cf.Shell && typeof Cf.Shell.getRoot === "function") {
      return Cf.Shell.getRoot();
    }
    return document.querySelector("[data-cartflow-bubble]");
  }

  function ensureBubble(primaryHex) {
    if (!Cf.Shell) {
      return null;
    }
    Cf.Shell.open({ primaryColor: primaryHex });
    return Cf.Shell.getRoot();
  }

  function stampPrimary(btn, primaryHex) {
    var hex = primaryHex || "#6366f1";
    btn.style.cssText =
      "cursor:pointer;display:inline-flex;align-items:center;justify-content:center;text-align:center;border-radius:9px;" +
      "background:linear-gradient(180deg," +
      hex +
      " 0%,#4f46e5 100%);color:#fafafa;width:100%;box-sizing:border-box;" +
      "padding:9px 10px;line-height:1.35;font-weight:600;font-size:13px;" +
      "border:1px solid rgba(255,255,255,.12);box-shadow:0 1px 0 rgba(255,255,255,.12) inset;";
  }

  function stampSecondaryOutline(btn) {
    btn.style.cssText =
      "cursor:pointer;display:inline-flex;align-items:center;justify-content:center;text-align:center;border-radius:9px;" +
      "background:rgba(255,255,255,.07);color:#e2e8f0;width:100%;box-sizing:border-box;" +
      "padding:9px 10px;line-height:1.35;font-weight:600;font-size:13px;" +
      "border:1px solid rgba(226,232,240,.25);";
  }

  function clear(primaryHex) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: primaryHex });
    Cf.Shell.setContent(null, null);
    Cf.Shell.setStep(null);
  }

  function renderYesNo(opts) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("yes_no");
    var ph = opts.primaryColor || "#6366f1";
    var frag = document.createDocumentFragment();
    var p = document.createElement("p");
    p.style.cssText =
      textPrimary + "margin-bottom:10px;font-size:14px;line-height:1.5;font-weight:500;";
    p.textContent = opts.question || "";
    frag.appendChild(p);
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
    stampSecondaryOutline(bn);
    bn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      opts.onNo();
    });
    row.appendChild(by);
    row.appendChild(bn);
    frag.appendChild(row);
    Cf.Shell.setContent(frag, "yes_no");
    try {
      console.log("[CF V2 SHOW YESNO]");
    } catch (eLog) {}
  }

  function btnGhostStyle() {
    return (
      "margin-top:6px;border:1px solid rgba(226,232,240,.26);cursor:pointer;border-radius:9px;" +
      "background:rgba(255,255,255,.06);color:rgba(241,245,249,.9);width:100%;padding:8px 10px;font-weight:600;font-size:12px;"
    );
  }

  function renderReasonGrid(opts) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("reason");
    var ph = opts.primaryColor || "#6366f1";
    var frag = document.createDocumentFragment();
    var p = document.createElement("p");
    p.style.cssText =
      textPrimary + "margin-bottom:8px;font-size:13px;line-height:1.45;font-weight:600;";
    p.textContent = opts.title || "وش أكثر شيء مخليك متردد؟ تبيني أساعدك";
    frag.appendChild(p);
    var row = document.createElement("div");
    row.setAttribute("data-cf-reason-row-v2", "1");
    row.style.cssText =
      "display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:2px;width:100%;";
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
    frag.appendChild(row);
    if (opts.onBack) {
      var back = document.createElement("button");
      back.type = "button";
      back.style.cssText = btnGhostStyle();
      back.textContent = "رجوع";
      back.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        opts.onBack();
      });
      frag.appendChild(back);
    }
    Cf.Shell.setContent(frag, "reason_grid");
    try {
      console.log("[CF V2 SHOW REASONS]");
    } catch (eR) {}
  }

  function renderBrowsingChoices(opts) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("exit_browsing");
    var ph = opts.primaryColor || "#6366f1";
    var frag = document.createDocumentFragment();
    var p = document.createElement("p");
    p.style.cssText = textPrimary + "margin-bottom:10px;font-size:14px;line-height:1.5;";
    p.textContent = opts.title || "";
    frag.appendChild(p);
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
    frag.appendChild(row);
    Cf.Shell.setContent(frag, "browsing_choices");
  }

  function renderPhoneStep(opts) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("phone");
    var ph = opts.primaryColor || "#6366f1";
    var frag = document.createDocumentFragment();
    var t = document.createElement("p");
    t.style.cssText =
      textPrimary + "margin-bottom:6px;font-size:13px;line-height:1.4;font-weight:700;";
    t.textContent = "رقم الجوال لإكمال المتابعة";
    frag.appendChild(t);
    var s = document.createElement("p");
    s.style.cssText = textMuted + "margin-bottom:8px;font-size:12px;line-height:1.4;";
    s.textContent = "نستخدمه فقط لمتابعة طلبك إذا احتجت مساعدة.";
    frag.appendChild(s);
    var inp = document.createElement("input");
    inp.type = "tel";
    inp.placeholder = "05xxxxxxxx";
    inp.setAttribute("dir", "ltr");
    inp.style.cssText =
      "width:100%;box-sizing:border-box;border-radius:9px;border:1px solid rgba(99,102,241,.38);" +
      "background:rgba(15,23,42,.65);padding:9px 10px;margin-bottom:6px;font:inherit;font-size:14px;color:#f8fafc;" +
      "outline:none;";
    try {
      var norm = Cf.State ? Cf.State.getStoredPhoneNorm() : "";
      if (norm && norm.slice(0, 3) === "966") {
        inp.value = "0" + norm.slice(3);
      }
    } catch (eLs) {}
    frag.appendChild(inp);
    var err = document.createElement("p");
    err.style.cssText = "margin:0 0 8px;color:#fecaca;font-size:12px;line-height:1.35;";
    err.textContent = "";
    frag.appendChild(err);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    var save = document.createElement("button");
    save.type = "button";
    save.textContent = "حفظ الرقم";
    stampPrimary(save, ph);
    var back = document.createElement("button");
    back.type = "button";
    back.textContent = "رجوع";
    stampSecondaryOutline(back);
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
      if (opts.optimisticSave && opts.onSave) {
        var ret = opts.onSave(pn);
        if (ret && typeof ret.then === "function") {
          ret.catch(function () {});
        }
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
    frag.appendChild(row);
    Cf.Shell.setContent(frag, "phone_capture");
    try {
      console.log("[CF V2 SHOW PHONE]");
    } catch (eP) {}
  }

  function renderContinuation(opts) {
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("continuation");
    var ph = opts.primaryColor || "#6366f1";
    var msgs = opts.messages || {};
    var rk = String(opts.reasonKey || "other").toLowerCase();
    var txt =
      msgs[rk] ||
      "تمام 👍\nأنا معك إذا احتجت أي توضيح قبل تكمل الطلب.";
    var frag = document.createDocumentFragment();
    var p = document.createElement("p");
    p.style.cssText =
      textPrimary + "margin-bottom:10px;font-size:13px;line-height:1.55;white-space:pre-line;";
    p.textContent = txt;
    frag.appendChild(p);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    function addPrimary(label, fn) {
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
    function addSecondary(label, fn) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      stampSecondaryOutline(b);
      b.addEventListener("click", function (e) {
        e.preventDefault();
        fn();
      });
      row.appendChild(b);
    }
    addPrimary("أكمل الطلب", opts.onContinueCart);
    addSecondary("أحتاج مساعدة الآن", opts.onAssist);
    addSecondary("رجوع للأسباب", opts.onBackReasons);
    if (opts.onRetryBackgroundSave && typeof opts.onRetryBackgroundSave === "function") {
      var rz = document.createElement("button");
      rz.type = "button";
      rz.textContent = opts.retryLabel || "إعادة إرسال";
      rz.style.cssText =
        "border:1px solid rgba(251,191,36,.45);cursor:pointer;border-radius:9px;background:rgba(120,53,15,.35);" +
        "color:#fde68a;width:100%;box-sizing:border-box;padding:9px 10px;font:inherit;font-weight:600;";
      rz.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        opts.onRetryBackgroundSave();
      });
      row.appendChild(rz);
    }
    frag.appendChild(row);
    Cf.Shell.setContent(frag, "continuation");
    try {
      console.log("[CF V2 SHOW CONTINUATION]");
    } catch (eCo) {}
  }

  function hideBubble() {
    if (Cf.Shell && typeof Cf.Shell.close === "function") {
      Cf.Shell.close({ syncDismiss: false });
      return;
    }
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
    if (!Cf.Shell) {
      return;
    }
    Cf.Shell.open({ primaryColor: opts.primaryColor });
    Cf.Shell.setStep("other_draft");
    var ph = opts.primaryColor || "#6366f1";
    var frag = document.createDocumentFragment();
    var hi = document.createElement("p");
    hi.style.cssText = textPrimary + "margin-bottom:8px;font-size:13px;line-height:1.5;";
    hi.textContent = "اكتب ملاحظتك باختصار 👇";
    frag.appendChild(hi);
    var ta = document.createElement("textarea");
    ta.rows = 3;
    ta.style.cssText =
      "width:100%;box-sizing:border-box;border-radius:9px;border:1px solid rgba(99,102,241,.38);" +
      "background:rgba(15,23,42,.65);padding:8px;margin-bottom:6px;font:inherit;resize:vertical;color:#f8fafc;";
    frag.appendChild(ta);
    var err = document.createElement("p");
    err.style.cssText = "color:#fecaca;font-size:12px;margin:4px 0;";
    err.textContent = "";
    frag.appendChild(err);
    var row = document.createElement("div");
    row.style.cssText = rowStyleCol;
    var send = document.createElement("button");
    send.type = "button";
    send.textContent = "إرسال";
    stampPrimary(send, ph);
    var back = document.createElement("button");
    back.type = "button";
    stampSecondaryOutline(back);
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
    frag.appendChild(row);
    Cf.Shell.setContent(frag, "other_draft");
  }

  /** خيارات فرعية للسبب ”السعر“. */
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
      if (Cf.Triggers && typeof Cf.Triggers.receiveTrigger === "function") {
        var r = Cf.Triggers.receiveTrigger("manual_debug", { entry: "ui_show_bubble" });
        if (r === true) {
          return true;
        }
        if (r === false) {
          return false;
        }
      }
    } catch (eT) {}
    try {
      var F = Cf.Flows;
      if (F && typeof F.showBubbleCartRecovery === "function") {
        F.showBubbleCartRecovery("manual_debug");
        return true;
      }
    } catch (eSb) {}
    try {
      console.warn("[CF V2] Ui.showBubble: Flows.showBubbleCartRecovery not available");
    } catch (eW) {}
    return false;
  }

  var Ui = {
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
  window.CartflowWidgetRuntime.Ui = Ui;
})();
