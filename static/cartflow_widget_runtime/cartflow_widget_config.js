/**
 * Normalize merchant + trigger config once per ready/public-config payload.
 * No DOM. No timers.
 */
(function () {
  "use strict";

  var CRT = {
    defaults: {
      exit_intent_enabled: true,
      exit_intent_sensitivity: "medium",
      exit_intent_delay_seconds: 0,
      exit_intent_frequency: "per_session",
      hesitation_trigger_enabled: true,
      hesitation_after_seconds: 20,
      hesitation_condition: "after_cart_add",
      visibility_widget_globally_enabled: true,
      visibility_temporarily_disabled: false,
      visibility_page_scope: "all",
      widget_phone_capture_mode: "after_reason",
      suppress_after_widget_dismiss: true,
      suppress_after_purchase: true,
      suppress_when_checkout_started: true,
      reason_display_order: [
        "price",
        "shipping",
        "delivery",
        "quality",
        "warranty",
        "thinking",
        "other",
      ],
    },
    _trigger: null,
    _templates: {},
    merchant: {
      widget_enabled: true,
      prompt_not_before_ms: 0,
      vip_cart_threshold: null,
      widget_brand_name: "مساعد المتجر",
      widget_primary_color: "#6C5CE7",
      widget_chrome_style: "modern",
    },
    gate_scheduled_once: false,
  };

  function normalizeToken(raw, allowed, fb) {
    var map = {};
    var i;
    for (i = 0; i < allowed.length; i++) {
      map[allowed[i]] = 1;
    }
    var s = String(raw == null ? "" : raw)
      .trim()
      .toLowerCase()
      .replace(/[\s\-]+/g, "_");
    return map[s] ? s : fb;
  }

  function mergeTrigger(patch) {
    var o = {};
    var k;
    for (k in CRT.defaults) {
      if (Object.prototype.hasOwnProperty.call(CRT.defaults, k)) {
        o[k] = CRT.defaults[k];
      }
    }
    if (patch && typeof patch === "object") {
      for (k in patch) {
        if (Object.prototype.hasOwnProperty.call(patch, k)) {
          o[k] = patch[k];
        }
      }
    }
    return o;
  }

  function merchantDelayMs(value, unit) {
    var v = typeof value === "number" ? value : parseInt(String(value || 0), 10);
    if (!isFinite(v) || v < 0) {
      v = 0;
    }
    var u = String(unit || "minutes").toLowerCase();
    if (u === "hours") {
      return v * 3600000;
    }
    if (u === "days") {
      return v * 86400000;
    }
    return v * 60000;
  }

  function applyMerchantGate(j) {
    if (!j || typeof j !== "object") {
      return;
    }
    if ("cartflow_widget_enabled" in j) {
      CRT.merchant.widget_enabled = !!(
        j.cartflow_widget_enabled !== false &&
        j.cartflow_widget_enabled !== 0 &&
        j.cartflow_widget_enabled !== "0"
      );
    }
    if (!CRT.gate_scheduled_once) {
      CRT.gate_scheduled_once = true;
      var dv = 0;
      if (
        "cartflow_widget_delay_value" in j &&
        j.cartflow_widget_delay_value != null &&
        j.cartflow_widget_delay_value !== ""
      ) {
        var pn = parseInt(String(j.cartflow_widget_delay_value), 10);
        if (isFinite(pn) && pn >= 0) {
          dv = pn;
        }
      }
      var du = "minutes";
      if (
        typeof j.cartflow_widget_delay_unit === "string" &&
        j.cartflow_widget_delay_unit.trim()
      ) {
        var ux = j.cartflow_widget_delay_unit.trim().toLowerCase();
        if (ux === "hours" || ux === "days" || ux === "minutes") {
          du = ux;
        }
      }
      CRT.merchant.prompt_not_before_ms = Date.now() + merchantDelayMs(dv, du);
    }
    if ("vip_cart_threshold" in j && j.vip_cart_threshold != null) {
      var t = Number(j.vip_cart_threshold);
      CRT.merchant.vip_cart_threshold = isFinite(t) && t >= 1 ? t : null;
    }
    try {
      window.cartflowVipCartThreshold = CRT.merchant.vip_cart_threshold;
      window.CARTFLOW_VIP_CART_THRESHOLD = CRT.merchant.vip_cart_threshold;
    } catch (eW) {}
  }

  function applyVisual(j) {
    if (!j || typeof j !== "object") {
      return;
    }
    if ("widget_name" in j && typeof j.widget_name === "string" && j.widget_name.trim()) {
      CRT.merchant.widget_brand_name = String(j.widget_name).trim().slice(0, 120);
    }
    if (
      "widget_primary_color" in j &&
      j.widget_primary_color != null &&
      String(j.widget_primary_color).trim()
    ) {
      var raw = String(j.widget_primary_color).trim();
      if (/^#[0-9A-Fa-f]{6}$/.test(raw)) {
        CRT.merchant.widget_primary_color = "#" + raw.slice(1).toUpperCase();
      }
    }
    if ("widget_style" in j && typeof j.widget_style === "string") {
      var st = String(j.widget_style).toLowerCase();
      if (st === "minimal" || st === "modern" || st === "bold") {
        CRT.merchant.widget_chrome_style = st;
      }
    }
  }

  function templates() {
    return CRT._templates && typeof CRT._templates === "object" ? CRT._templates : {};
  }

  function templateEnabled(slug) {
    var rt = templates();
    var e = rt[String(slug || "").toLowerCase()];
    if (!e || typeof e !== "object") {
      return true;
    }
    return e.enabled !== false;
  }

  function defaultLabels() {
    return {
      price: "السعر",
      quality: "الجودة",
      warranty: "الضمان",
      shipping: "الشحن",
      delivery: "التوصيل",
      thinking: "أفكر",
      other: "سبب آخر",
    };
  }

  function surfaceLabel(reasonKey, defLabel) {
    var k = String(reasonKey || "").toLowerCase();
    var ent = templates()[k];
    if (ent && typeof ent === "object") {
      var m = String(ent.message || "").trim();
      if (m) {
        var line = String(m.split(/\r?\n/)[0] || "").trim();
        if (line.length > 80) {
          return line.slice(0, 77) + "…";
        }
        return line;
      }
    }
    return defLabel != null ? String(defLabel) : k;
  }

  function widgetTrigger() {
    return CRT._trigger || CRT.defaults;
  }

  function applyPayload(j, sourceNote) {
    if (!j || typeof j !== "object") {
      return;
    }
    if (j.widget_trigger_config && typeof j.widget_trigger_config === "object") {
      CRT._trigger = mergeTrigger(j.widget_trigger_config);
      try {
        window.__cfWidgetTriggerRuntime = CRT._trigger;
      } catch (eWx) {}
    }
    if (j.reason_templates && typeof j.reason_templates === "object") {
      CRT._templates = j.reason_templates;
      try {
        window.__cfReasonTemplatesRuntime = CRT._templates;
      } catch (eR) {}
    }
    applyMerchantGate(j);
    applyVisual(j);
    try {
      console.log("[WIDGET CONFIG LOADED V2]", {
        source: sourceNote || "?",
        phone_capture_mode: phoneCaptureMode(),
        hesitation_seconds: hesitationDelaySeconds(),
      });
    } catch (eLo) {}
  }

  function phoneCaptureMode() {
    var tr = widgetTrigger();
    return normalizeToken(
      tr.widget_phone_capture_mode != null ? tr.widget_phone_capture_mode : "",
      ["after_reason", "immediate", "none"],
      "after_reason"
    );
  }

  function hesitationDelaySeconds() {
    var tr = widgetTrigger();
    var sec =
      tr &&
      typeof tr.hesitation_after_seconds === "number" &&
      isFinite(tr.hesitation_after_seconds)
        ? tr.hesitation_after_seconds
        : 20;
    return Math.max(0, Math.min(600, sec));
  }

  function hesitationCondition() {
    var tr = widgetTrigger();
    return normalizeToken(
      tr && tr.hesitation_condition != null ? tr.hesitation_condition : "",
      ["after_cart_add", "inactivity", "repeated_view", "cart_interaction"],
      "after_cart_add"
    );
  }

  function buildVisibleReasonRows() {
    var tr = widgetTrigger();
    var order = Array.isArray(tr.reason_display_order)
      ? tr.reason_display_order
      : CRT.defaults.reason_display_order;
    var defs = defaultLabels();
    var out = [];
    var i;
    for (i = 0; i < order.length; i++) {
      var r = String(order[i] || "").toLowerCase();
      if (!r || !templateEnabled(r)) {
        continue;
      }
      var dl = defs[r] != null ? defs[r] : r;
      out.push({ r: r, label: surfaceLabel(r, dl) });
    }
    return out;
  }

  window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
  window.CartflowWidgetRuntime.Config = {
    applyPayload: applyPayload,
    widgetTrigger: widgetTrigger,
    phoneCaptureMode: phoneCaptureMode,
    hesitationDelaySeconds: hesitationDelaySeconds,
    hesitationCondition: hesitationCondition,
    merchant: function () {
      return CRT.merchant;
    },
    buildVisibleReasonRows: buildVisibleReasonRows,
    templateEnabled: templateEnabled,
    normalizeToken: normalizeToken,
    exitIntentSensitivity: function () {
      return normalizeToken(
        widgetTrigger().exit_intent_sensitivity,
        ["low", "medium", "high"],
        "medium"
      );
    },
    exitIntentDelaySeconds: function () {
      var tr = widgetTrigger();
      var d = 0;
      try {
        if (
          typeof tr.exit_intent_delay_seconds === "number" &&
          isFinite(tr.exit_intent_delay_seconds)
        ) {
          d = Math.max(0, Math.min(60, Math.floor(tr.exit_intent_delay_seconds)));
        }
      } catch (eD) {}
      return d;
    },
    widgetGloballyAllowed: function () {
      var tr = widgetTrigger();
      try {
        if (tr.visibility_widget_globally_enabled === false) {
          return false;
        }
        if (tr.visibility_temporarily_disabled === true) {
          return false;
        }
      } catch (eVs) {}
      return true;
    },
  };
})();
