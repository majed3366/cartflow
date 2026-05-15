(function () {
  "use strict";

  var PRESET_Q = "ما الذي منعك من إكمال الطلب؟";

  function byId(id) {
    return document.getElementById(id);
  }

  function readBootstrap() {
    var el = byId("ma-widget-bootstrap");
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function writeBootstrap(obj) {
    var el = byId("ma-widget-bootstrap");
    if (!el || !obj) return;
    el.textContent = JSON.stringify(obj);
  }

  function reasonOrderKeys() {
    var tb = byId("mw-reason-tbody");
    if (!tb) return [];
    var out = [];
    tb.querySelectorAll(".mw-reason-key").forEach(function (inp) {
      var k = (inp.value || "").trim().toLowerCase();
      if (k) out.push(k);
    });
    return out;
  }

  function collectReasonTemplates() {
    var tb = byId("mw-reason-tbody");
    if (!tb) return {};
    var o = {};
    tb.querySelectorAll("tr[data-mw-reason-row]").forEach(function (tr) {
      var keyInp = tr.querySelector(".mw-reason-key");
      var labInp = tr.querySelector(".mw-reason-label");
      var onInp = tr.querySelector(".mw-reason-on");
      if (!keyInp || !labInp) return;
      var k = (keyInp.value || "").trim().toLowerCase();
      if (!k) return;
      o[k] = {
        enabled: onInp ? !!onInp.checked : true,
        message: (labInp.value || "").trim(),
      };
    });
    return o;
  }

  function collectTrigger(base) {
    var t = Object.assign({}, (base && base.trigger) || {});
    var ge = byId("mw-exit-enabled");
    var gd = byId("mw-exit-delay");
    var gs = byId("mw-exit-sens");
    var gf = byId("mw-exit-freq");
    var he = byId("mw-hes-enabled");
    var hs = byId("mw-hes-sec");
    var hsc = byId("mw-hes-sec-custom");
    var hc = byId("mw-hes-cond");
    var sc = byId("mw-scope");
    var sd = byId("mw-sup-dismiss");
    var sp = byId("mw-sup-purchase");
    var scx = byId("mw-sup-checkout");
    var phoneEl = document.querySelector('input[name="mw-phone"]:checked');
    if (ge) t.exit_intent_enabled = !!ge.checked;
    if (gd) t.exit_intent_delay_seconds = parseInt(gd.value, 10) || 0;
    if (gs) t.exit_intent_sensitivity = gs.value || "medium";
    if (gf) t.exit_intent_frequency = gf.value || "per_session";
    if (he) t.hesitation_trigger_enabled = !!he.checked;
    if (hs) {
      var hv = String(hs.value || "").trim();
      if (hv === "custom" && hsc) {
        var cn = parseInt(String(hsc.value || "").trim(), 10);
        t.hesitation_after_seconds =
          isFinite(cn) && cn >= 1 && cn <= 600 ? cn : 20;
      } else {
        var sn = parseInt(hv, 10);
        t.hesitation_after_seconds = isFinite(sn) ? sn : 20;
      }
    }
    if (hc) t.hesitation_condition = hc.value || "after_cart_add";
    if (sc) t.visibility_page_scope = sc.value || "all";
    t.widget_brand_line_ar = "";
    if (phoneEl) t.widget_phone_capture_mode = phoneEl.value;
    if (sd) t.suppress_after_widget_dismiss = !!sd.checked;
    if (sp) t.suppress_after_purchase = !!sp.checked;
    if (scx) t.suppress_when_checkout_started = !!scx.checked;
    t.reason_display_order = reasonOrderKeys();
    return t;
  }

  function collectPayload() {
    var b = readBootstrap() || {};
    var wn = byId("mw-widget-name");
    var rawName = wn ? String(wn.value || "").trim() : "";
    var body = {
      widget_name: rawName,
      widget_primary_color: byId("mw-widget-color") ? byId("mw-widget-color").value : b.widget_primary_color,
      cartflow_widget_enabled: byId("mw-widget-enabled") ? !!byId("mw-widget-enabled").checked : true,
      reason_templates: collectReasonTemplates(),
      widget_trigger_config: collectTrigger(b),
    };
    return body;
  }

  function titleFromBootstrap(b) {
    if (!b) return "مساعد المتجر";
    var n = String(b.widget_name || "").trim();
    return n || "مساعد المتجر";
  }

  function questionFromBootstrap(b) {
    if (!b) return PRESET_Q;
    var mode = String(b.exit_intent_template_mode || "preset").toLowerCase();
    var ct = String(b.exit_intent_custom_text || "").trim();
    if (mode === "custom" && ct) return ct.length > 500 ? ct.slice(0, 500) : ct;
    return PRESET_Q;
  }

  function fillPreviewPair(suffix, title, sub, color, optsHtml) {
    var box = byId("mw-" + suffix + "-box");
    var bt = byId("mw-" + suffix + "-title");
    var bs = byId("mw-" + suffix + "-sub");
    var bo = byId("mw-" + suffix + "-opts");
    if (!box || !bt || !bs || !bo) return;
    box.style.borderRight = "4px solid " + (color || "#6C5CE7");
    bt.textContent = title || "مساعد المتجر";
    bs.textContent = sub || PRESET_Q;
    bo.innerHTML = optsHtml;
  }

  function refreshPreview() {
    var b = readBootstrap() || {};
    var wn = byId("mw-widget-name");
    var title =
      (wn && (wn.value || "").trim()) ||
      titleFromBootstrap(b);
    var sub = questionFromBootstrap(b);
    var color = byId("mw-widget-color") ? byId("mw-widget-color").value : "#6C5CE7";
    var tb = byId("mw-reason-tbody");
    var parts = [];
    if (tb) {
      tb.querySelectorAll("tr[data-mw-reason-row]").forEach(function (tr) {
        var onInp = tr.querySelector(".mw-reason-on");
        var labInp = tr.querySelector(".mw-reason-label");
        if (!labInp || !onInp || !onInp.checked) return;
        var lab = (labInp.value || "").trim() || "—";
        parts.push(
          '<span class="wb-opt selected">' +
            lab.replace(/</g, "&lt;").replace(/>/g, "&gt;") +
            "</span>"
        );
      });
    }
    var optsHtml = parts.join("");
    fillPreviewPair("desk", title, sub, color, optsHtml);
    fillPreviewPair("mob", title, sub, color, optsHtml);
  }

  function bindReasonReorder() {
    var tb = byId("mw-reason-tbody");
    if (!tb || tb.getAttribute("data-mw-bound") === "1") return;
    tb.setAttribute("data-mw-bound", "1");
    tb.addEventListener("click", function (ev) {
      var btn = ev.target.closest("[data-mw-reason-up],[data-mw-reason-down]");
      if (!btn || !tb.contains(btn)) return;
      var tr = btn.closest("tr[data-mw-reason-row]");
      if (!tr) return;
      if (btn.hasAttribute("data-mw-reason-up")) {
        var prev = tr.previousElementSibling;
        if (prev) tb.insertBefore(tr, prev);
      } else {
        var next = tr.nextElementSibling;
        if (next) tb.insertBefore(next, tr);
      }
      refreshPreview();
    });
  }

  function showSaveMsg(text, ok) {
    var el = byId("mw-save-msg");
    if (!el) return;
    el.textContent = text || "";
    el.hidden = !text;
    el.classList.toggle("ma-widget-ok", !!ok);
    el.classList.toggle("ma-widget-err", !ok);
  }

  function wireSave() {
    var btn = byId("mw-save-btn");
    if (!btn || btn.getAttribute("data-mw-bound") === "1") return;
    btn.setAttribute("data-mw-bound", "1");
    btn.addEventListener("click", function () {
      showSaveMsg("", true);
      var payload = collectPayload();
      btn.disabled = true;
      fetch("/api/dashboard/merchant-widget-settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(function (r) {
          return r.json().then(function (j) {
            return { ok: r.ok, j: j };
          });
        })
        .then(function (x) {
          btn.disabled = false;
          if (!x.j || !x.j.ok) {
            showSaveMsg((x.j && x.j.error) || "تعذّر الحفظ", false);
            return;
          }
          if (x.j.merchant_widget_panel) {
            writeBootstrap(x.j.merchant_widget_panel);
          }
          showSaveMsg("تم حفظ الإعدادات بنجاح", true);
          refreshPreview();
        })
        .catch(function () {
          btn.disabled = false;
          showSaveMsg("تعذّر الاتصال بالخادم", false);
        });
    });
  }

  function wireLive() {
    ["mw-widget-name", "mw-widget-color"].forEach(function (id) {
      var el = byId(id);
      if (!el) return;
      el.addEventListener("input", refreshPreview);
      el.addEventListener("change", refreshPreview);
    });
    var tb = byId("mw-reason-tbody");
    if (tb) {
      tb.addEventListener("input", refreshPreview);
      tb.addEventListener("change", refreshPreview);
    }
  }

  function wireHesitationDelayUi() {
    var hs = byId("mw-hes-sec");
    var hsc = byId("mw-hes-sec-custom");
    var lbl = byId("mw-hes-sec-custom-label");
    if (!hs) return;
    function sync() {
      var isC = hs.value === "custom";
      if (hsc) {
        hsc.style.display = isC ? "" : "none";
      }
      if (lbl) {
        lbl.style.display = isC ? "" : "none";
      }
    }
    hs.addEventListener("change", sync);
    sync();
  }

  function init() {
    if (!byId("page-widget")) return;
    bindReasonReorder();
    wireLive();
    wireHesitationDelayUi();
    wireSave();
    refreshPreview();
  }

  window.cartflowMerchantWidgetPanelRefresh = refreshPreview;

  window.cartflowMerchantWidgetPanelRebindReasons = function () {
    var tb = byId("mw-reason-tbody");
    if (tb) {
      tb.removeAttribute("data-mw-bound");
    }
    bindReasonReorder();
    refreshPreview();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
