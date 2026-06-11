/**
 * Normalize merchant + trigger config once per ready/public-config payload.
 * No DOM. No timers.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
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
        "quality",
        "shipping",
        "delivery",
        "warranty",
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
      exit_intent_template_mode: "preset",
      exit_intent_template_tone: "friendly",
      exit_intent_custom_text: "",
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
      CRT.merchant.delay_value_applied = dv;
      CRT.merchant.delay_unit_applied = du;
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

  function logTitleTruth(tag, extra) {
    try {
      var payload = {
        tag: tag || "?",
        payload_widget_name:
          extra && extra.payload_widget_name != null ? extra.payload_widget_name : null,
        payload_widget_display_name:
          extra && extra.payload_widget_display_name != null
            ? extra.payload_widget_display_name
            : null,
        resolved_brand_name: CRT.merchant.widget_brand_name,
        merchant_fn: CRT.merchant,
      };
      console.log("[CF WIDGET TITLE TRUTH]", payload);
    } catch (eLt) {}
  }

  function resolveBrandNameFromPayload(j) {
    if (!j || typeof j !== "object") {
      return null;
    }
    var def = "مساعد المتجر";
    var nm =
      "widget_name" in j && typeof j.widget_name === "string" ? j.widget_name.trim() : "";
    var disp =
      "widget_display_name" in j && typeof j.widget_display_name === "string"
        ? j.widget_display_name.trim()
        : "";
    if (nm && nm !== def) {
      return nm.slice(0, 120);
    }
    if (disp) {
      return disp.slice(0, 120);
    }
    if (nm) {
      return nm.slice(0, 120);
    }
    return null;
  }

  function isRealStorefrontEmbed() {
    try {
      if (window.CARTFLOW_RECOVERY_WIDGET_MODE === true) {
        return true;
      }
      var apiBase = window.CARTFLOW_API_BASE;
      var pageOrigin = String(window.location.origin || "").replace(/\/+$/, "");
      var loaderOrigin = String(apiBase || "").replace(/\/+$/, "");
      if (loaderOrigin && pageOrigin && loaderOrigin !== pageOrigin) {
        return true;
      }
    } catch (eEmb) {}
    return false;
  }

  function merchantConfigInternals() {
    try {
      return window.CartflowWidgetRuntime.State.internals;
    } catch (eSt) {
      return null;
    }
  }

  function merchantConfigResolved() {
    var st = merchantConfigInternals();
    return !!(st && st.v2MerchantConfigResolved);
  }

  function isPublicConfigSource(sourceNote) {
    var s = String(sourceNote || "");
    return s === "public_config_first" || s === "public_config";
  }

  function shouldApplyVisualForSource(sourceNote) {
    if (!isRealStorefrontEmbed()) {
      return true;
    }
    return isPublicConfigSource(sourceNote);
  }

  function normalizePrimaryHex(raw) {
    if (raw == null) {
      return null;
    }
    var s = String(raw).trim();
    if (/^#[0-9A-Fa-f]{6}$/i.test(s)) {
      return "#" + s.slice(1).toUpperCase();
    }
    if (/^#[0-9A-Fa-f]{3}$/i.test(s)) {
      var h = s.slice(1);
      return (
        "#" +
        (h.charAt(0) +
          h.charAt(0) +
          h.charAt(1) +
          h.charAt(1) +
          h.charAt(2) +
          h.charAt(2))
      ).toUpperCase();
    }
    var bare = s.replace(/^#/, "");
    if (/^[0-9A-Fa-f]{6}$/i.test(bare)) {
      return "#" + bare.toUpperCase();
    }
    return null;
  }

  var domBeaconTimer = null;
  var domBeaconAttempts = 0;
  var DOM_BEACON_MAX_ATTEMPTS = 60;

  function cartflowRuntimeVersion() {
    try {
      if (typeof window.__cartflow_loader_build === "string" && window.__cartflow_loader_build.trim()) {
        return String(window.__cartflow_loader_build).trim();
      }
    } catch (eRv) {}
    return "v2-merchant-theme-tokens-1";
  }

  function cartflowBeaconApiOrigin() {
    try {
      if (typeof window.CARTFLOW_API_BASE === "string" && window.CARTFLOW_API_BASE.trim()) {
        return String(window.CARTFLOW_API_BASE).replace(/\/+$/, "");
      }
      var Cf = window.CartflowWidgetRuntime;
      if (Cf && Cf.Api && typeof Cf.Api.apiBase === "function") {
        var b = Cf.Api.apiBase();
        if (b) return b;
      }
      var loaderNode = document.querySelector('script[src*="widget_loader"]');
      if (loaderNode && loaderNode.src) {
        return new URL(loaderNode.src, window.location.href).origin;
      }
    } catch (eBo) {}
    return "";
  }

  function cartflowBeaconStoreSlug() {
    try {
      var Cf = window.CartflowWidgetRuntime;
      if (Cf && Cf.Api && typeof Cf.Api.storeSlug === "function") {
        var s = Cf.Api.storeSlug();
        if (s) return String(s).trim();
      }
    } catch (eSs) {}
    try {
      if (window.CARTFLOW_STORE_SLUG) return String(window.CARTFLOW_STORE_SLUG).trim();
    } catch (eS1) {}
    return "";
  }

  function computedStyleColor(el) {
    if (!el || !window.getComputedStyle) {
      return null;
    }
    try {
      var cs = window.getComputedStyle(el);
      var bg = (cs && (cs.backgroundColor || cs.background)) || "";
      if (bg && bg !== "transparent" && bg !== "rgba(0, 0, 0, 0)") {
        return String(bg).trim();
      }
    } catch (eCs) {}
    return null;
  }

  function CfShellRenderedVisuals() {
    try {
      var Sh = window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Shell;
      if (!Sh || typeof Sh.getRoot !== "function") {
        return null;
      }
      var w = Sh.getRoot();
      if (!w) {
        return null;
      }
      var title = null;
      var color = null;
      var tEl = w.querySelector("[data-cf-shell-title]");
      if (tEl) {
        title = String(tEl.textContent || "").trim();
      }
      var bar = w.querySelector('[data-cf-chrome="1"]');
      color = computedStyleColor(bar);
      if (!color) {
        var btn = w.querySelector("[data-cf-btn-primary]");
        color = computedStyleColor(btn);
      }
      if (!color && bar && bar.style && bar.style.background) {
        color = String(bar.style.background).trim();
      }
      return { title: title, color: color };
    } catch (eVis) {
      return null;
    }
  }

  function readShellDomTruth() {
    var vis = CfShellRenderedVisuals();
    if (!vis) {
      return null;
    }
    return {
      rendered_title_text: vis.title || null,
      rendered_primary_color_computed: vis.color || null,
    };
  }

  function storefrontWidgetSeenUrl(origin) {
    return String(origin || "").replace(/\/+$/, "") + "/api/storefront/widget-seen";
  }

  function widgetShellRendered() {
    try {
      var Sh = window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Shell;
      return !!(Sh && typeof Sh.getRoot === "function" && Sh.getRoot());
    } catch (eWr) {
      return false;
    }
  }

  function postStorefrontRuntimeTruthBeacon(tag, dom) {
    try {
      var p = window.location.pathname || "";
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        return;
      }
      var slug = cartflowBeaconStoreSlug();
      if (!slug || slug === "demo") {
        return;
      }
      var origin = cartflowBeaconApiOrigin();
      if (!origin) {
        return;
      }
      dom = dom || readShellDomTruth() || {};
      var runtimeTruth = collectRuntimeTruthSnapshot();
      var payload = JSON.stringify({
        store: slug,
        store_slug: slug,
        rendered_title_text: dom.rendered_title_text,
        rendered_primary_color_computed: dom.rendered_primary_color_computed,
        runtime_truth: runtimeTruth,
        runtime_version: cartflowRuntimeVersion(),
        page_url: String(window.location.href || "").slice(0, 2048),
        timestamp: new Date().toISOString(),
        beacon_tag: tag || "runtime_truth",
      });
      var url = storefrontWidgetSeenUrl(origin);
      if (navigator.sendBeacon) {
        try {
          navigator.sendBeacon(url, new Blob([payload], { type: "application/json" }));
        } catch (eSb) {
          console.warn("[CF WIDGET SEEN BEACON WARN]", "sendBeacon_failed", eSb);
        }
      } else {
        fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: payload,
          credentials: "omit",
          keepalive: true,
        }).catch(function (eFetch) {
          console.warn("[CF WIDGET SEEN BEACON WARN]", "fetch_failed", eFetch);
        });
      }
    } catch (ePost) {
      try {
        console.warn("[CF WIDGET SEEN BEACON WARN]", "beacon_crash", ePost);
      } catch (eWp) {}
    }
  }

  function postStorefrontDomTruthBeacon(tag, dom) {
    postStorefrontRuntimeTruthBeacon(tag || "dom_truth", dom);
  }

  function scheduleStorefrontRuntimeTruthBeacon(tag) {
    var waitAttempts = 0;
    function tick() {
      waitAttempts += 1;
      if (isRealStorefrontEmbed() && !merchantConfigResolved()) {
        if (waitAttempts < 80) {
          setTimeout(tick, 50);
          return;
        }
      }
      var snap = collectRuntimeTruthSnapshot();
      var disabled =
        snap.widget_disabled_effective === true || snap.disabled_effective === true;
      if (disabled || !widgetShellRendered()) {
        postStorefrontRuntimeTruthBeacon(tag || "config_runtime", {});
        if (!disabled && widgetShellRendered()) {
          scheduleStorefrontDomTruthBeacon(tag);
        }
        return;
      }
      scheduleStorefrontDomTruthBeacon(tag);
    }
    setTimeout(tick, 0);
  }

  function scheduleStorefrontDomTruthBeacon(tag) {
    if (isRealStorefrontEmbed() && !merchantConfigResolved()) {
      return;
    }
    setTimeout(function () {
      try {
        domBeaconAttempts = 0;
        if (domBeaconTimer) {
          try {
            clearTimeout(domBeaconTimer);
          } catch (eCt) {}
          domBeaconTimer = null;
        }
        function attempt() {
          domBeaconAttempts += 1;
          var dom = readShellDomTruth();
          var hasTitle = dom && dom.rendered_title_text;
          var hasColor = dom && dom.rendered_primary_color_computed;
          if (hasTitle && hasColor) {
            postStorefrontRuntimeTruthBeacon(tag, dom);
            return;
          }
          var hasRoot = widgetShellRendered();
          if (hasRoot && domBeaconAttempts < DOM_BEACON_MAX_ATTEMPTS) {
            domBeaconTimer = setTimeout(attempt, 250);
            return;
          }
          if (hasRoot || domBeaconAttempts >= DOM_BEACON_MAX_ATTEMPTS) {
            postStorefrontRuntimeTruthBeacon(tag, dom || {});
          }
        }
        domBeaconTimer = setTimeout(attempt, 0);
      } catch (eSched) {
        try {
          console.warn("[CF WIDGET SEEN BEACON WARN]", "schedule_crash", eSched);
        } catch (eSw) {}
      }
    }, 0);
  }

  function logWidgetSettingsTruth(tag, extra) {
    try {
      var Cf = window.CartflowWidgetRuntime;
      var slug = "";
      if (Cf.Api && typeof Cf.Api.storeSlug === "function") {
        slug = Cf.Api.storeSlug();
      }
      var renderedTitle = null;
      var renderedColor = null;
      if (Cf.Shell && typeof Cf.Shell.getRoot === "function") {
        var w = Cf.Shell.getRoot();
        if (w) {
          var tEl = w.querySelector("[data-cf-shell-title]");
          if (tEl) {
            renderedTitle = tEl.textContent;
          }
          var bar = w.querySelector('[data-cf-chrome="1"]');
          if (bar && bar.style) {
            renderedColor = bar.style.background || null;
          }
        }
      }
      console.log("[WIDGET SETTINGS TRUTH]", {
        tag: tag || "?",
        store_slug: slug,
        api_widget_name: extra && extra.api_widget_name != null ? extra.api_widget_name : null,
        api_widget_primary_color:
          extra && extra.api_widget_primary_color != null
            ? extra.api_widget_primary_color
            : null,
        runtime_widget_name: CRT.merchant.widget_brand_name,
        runtime_widget_primary_color: CRT.merchant.widget_primary_color,
        rendered_widget_title: renderedTitle,
        rendered_widget_color: renderedColor,
      });
    } catch (eWt) {}
  }

  function applyVisual(j) {
    if (!j || typeof j !== "object") {
      return;
    }
    var resolved = resolveBrandNameFromPayload(j);
    if (resolved) {
      CRT.merchant.widget_brand_name = resolved;
    }
    if ("widget_primary_color" in j && j.widget_primary_color != null) {
      var hex = normalizePrimaryHex(j.widget_primary_color);
      if (hex) {
        CRT.merchant.widget_primary_color = hex;
      }
    }
    if ("widget_style" in j && typeof j.widget_style === "string") {
      var st = String(j.widget_style).toLowerCase();
      if (st === "minimal" || st === "modern" || st === "bold") {
        CRT.merchant.widget_chrome_style = st;
      }
    }
    if ("exit_intent_template_mode" in j) {
      var em = String(j.exit_intent_template_mode || "preset")
        .trim()
        .toLowerCase();
      if (em === "preset" || em === "custom") {
        CRT.merchant.exit_intent_template_mode = em;
      }
    }
    if ("exit_intent_template_tone" in j) {
      var et = String(j.exit_intent_template_tone || "friendly")
        .trim()
        .toLowerCase();
      if (et === "friendly" || et === "formal" || et === "sales") {
        CRT.merchant.exit_intent_template_tone = et;
      }
    }
    if (typeof j.exit_intent_custom_text === "string") {
      CRT.merchant.exit_intent_custom_text = j.exit_intent_custom_text;
    }
    logTitleTruth("applyVisual", {
      payload_widget_name: j.widget_name,
      payload_widget_display_name: j.widget_display_name,
    });
    try {
      var Th = window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Theme;
      if (Th && typeof Th.refresh === "function") {
        Th.refresh(CRT.merchant.widget_primary_color);
      }
    } catch (eTh) {}
    try {
      var Sh = window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.Shell;
      if (Sh && typeof Sh.refreshShellVisuals === "function") {
        Sh.refreshShellVisuals();
      } else if (Sh && typeof Sh.refreshTitle === "function") {
        Sh.refreshTitle();
      }
    } catch (eTi) {}
    logWidgetSettingsTruth("applyVisual", {
      api_widget_name: j.widget_name,
      api_widget_primary_color: j.widget_primary_color,
    });
    scheduleStorefrontDomTruthBeacon("applyVisual");
  }

  function applyVisualIfAllowed(j, sourceNote) {
    if (!shouldApplyVisualForSource(sourceNote)) {
      return;
    }
    applyVisual(j);
    logWidgetSettingsRuntimeTruth("applyVisual");
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

  /** تسميات أسباب الودجيت — كتالوج ثابت؛ لا تقرأ من ‎templates()[k].message‎ (قوالب الاسترجاع). */
  function defaultLabels() {
    return {
      price: "السعر",
      quality: "الجودة",
      warranty: "الضمان",
      shipping: "الشحن",
      delivery: "التوصيل",
      other: "سبب آخر",
    };
  }

  function surfaceLabel(reasonKey, defLabel) {
    var k = String(reasonKey || "").toLowerCase();
    var defs = defaultLabels();
    if (defs[k] != null) {
      return defs[k];
    }
    return defLabel != null ? String(defLabel) : k;
  }

  function widgetTrigger() {
    return CRT._trigger || CRT.defaults;
  }

  function widgetGloballyAllowed() {
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
  }

  function collectRuntimeTruthSnapshot() {
    var tr = widgetTrigger();
    var M = CRT.merchant;
    var enabled = M.widget_enabled !== false;
    var configLoaded = merchantConfigResolved();
    if (!isRealStorefrontEmbed()) {
      configLoaded = true;
    }
    var shellRendered = widgetShellRendered();
    var delayBlocked = false;
    try {
      delayBlocked =
        typeof M.prompt_not_before_ms === "number" &&
        isFinite(M.prompt_not_before_ms) &&
        Date.now() < M.prompt_not_before_ms;
    } catch (eDb) {}
    var delayRemaining = 0;
    try {
      if (typeof M.prompt_not_before_ms === "number" && isFinite(M.prompt_not_before_ms)) {
        delayRemaining = Math.max(0, M.prompt_not_before_ms - Date.now());
      }
    } catch (eDr) {}
    var disabledEffective = !enabled || delayBlocked || !widgetGloballyAllowed();
    var cartBridge = null;
    try {
      var CB = window.CartflowWidgetRuntime && window.CartflowWidgetRuntime.CartBridge;
      if (CB && typeof CB.getState === "function") {
        cartBridge = CB.getState();
      }
    } catch (eCb) {}
    var widgetHealth = null;
    try {
      var WH = window.__cartflowWidgetHealth;
      if (WH && typeof WH === "object") {
        widgetHealth = {
          module_load_status: WH.module_load_status || null,
          failed_modules: WH.failed_modules || [],
          bootstrap_ready: WH.bootstrap_ready === true,
          bootstrap_blocked: WH.bootstrap_blocked === true,
          missing_runtime_objects: WH.missing_runtime_objects || [],
          runtime_version: WH.runtime_version || cartflowRuntimeVersion(),
          widget_shown: shellRendered,
          last_cart_event_type: cartBridge ? cartBridge.last_event_type : null,
          last_cart_event_at: cartBridge ? cartBridge.last_event_at : null,
          hesitation_armed: cartBridge
            ? cartBridge.hesitation_armed_from_cart_event === true
            : false,
          last_runtime_error: WH.last_runtime_error || null,
        };
      }
    } catch (eWh) {}
    return {
      widget_enabled: enabled,
      config_loaded: configLoaded,
      widget_rendered: shellRendered,
      cart_bridge: cartBridge,
      widget_health: widgetHealth,
      disabled_effective: disabledEffective,
      widget_disabled_effective: disabledEffective,
      exit_intent_enabled: !(tr && tr.exit_intent_enabled === false),
      hesitation_trigger_enabled: !(tr && tr.hesitation_trigger_enabled === false),
      exit_intent_frequency: normalizeToken(
        tr.exit_intent_frequency,
        ["per_session", "per_24h", "no_rapid_repeat"],
        "per_session"
      ),
      hesitation_after_seconds: hesitationDelaySeconds(),
      delay_remaining_ms: delayRemaining,
      delay_configured_value:
        M.delay_value_applied != null ? M.delay_value_applied : 0,
      delay_configured_unit: M.delay_unit_applied || "minutes",
      delay_configured_ms: merchantDelayMs(
        M.delay_value_applied != null ? M.delay_value_applied : 0,
        M.delay_unit_applied || "minutes"
      ),
      prompt_not_before_ms: M.prompt_not_before_ms,
      widget_globally_allowed: widgetGloballyAllowed(),
      visibility_page_scope: tr.visibility_page_scope || "all",
    };
  }

  function logWidgetSettingsRuntimeTruth(sourceNote) {
    var snap = collectRuntimeTruthSnapshot();
    try {
      window.__cfWidgetRuntimeTruth = snap;
    } catch (eMem) {}
    try {
      console.log("[CF ENABLE TRUTH]", {
        source: sourceNote || "?",
        widget_enabled: snap.widget_enabled,
        config_loaded: snap.config_loaded,
        widget_rendered: snap.widget_rendered,
        disabled_effective: snap.disabled_effective,
        widget_disabled_effective: snap.widget_disabled_effective,
        widget_globally_allowed: snap.widget_globally_allowed,
        delay_remaining_ms: snap.delay_remaining_ms,
      });
      console.log("[CF EXIT INTENT TRUTH]", {
        source: sourceNote || "?",
        exit_intent_enabled: snap.exit_intent_enabled,
        exit_intent_frequency: snap.exit_intent_frequency,
      });
      console.log("[CF HESITATION TRUTH]", {
        source: sourceNote || "?",
        hesitation_trigger_enabled: snap.hesitation_trigger_enabled,
        hesitation_after_seconds: snap.hesitation_after_seconds,
      });
      console.log("[CF DELAY TRUTH]", {
        source: sourceNote || "?",
        delay_remaining_ms: snap.delay_remaining_ms,
        prompt_not_before_ms: snap.prompt_not_before_ms,
      });
      console.log("[CF FREQUENCY TRUTH]", {
        source: sourceNote || "?",
        exit_intent_frequency: snap.exit_intent_frequency,
      });
    } catch (eLog) {}
    return snap;
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
    applyVisualIfAllowed(j, sourceNote);
    logWidgetSettingsRuntimeTruth(sourceNote || "applyPayload");
    logTitleTruth("applyPayload", {
      payload_widget_name: j.widget_name,
      payload_widget_display_name: j.widget_display_name,
      source: sourceNote || "?",
    });
    try {
      console.log("[WIDGET CONFIG LOADED V2]", {
        source: sourceNote || "?",
        phone_capture_mode: phoneCaptureMode(),
        hesitation_seconds: hesitationDelaySeconds(),
        widget_name: j.widget_name,
        widget_brand_name: CRT.merchant.widget_brand_name,
      });
    } catch (eLo) {}
    scheduleStorefrontRuntimeTruthBeacon(sourceNote || "applyPayload");
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

  var Config = {
    applyPayload: applyPayload,
    isRealStorefrontEmbed: isRealStorefrontEmbed,
    merchantConfigResolved: merchantConfigResolved,
    shouldApplyVisualForSource: shouldApplyVisualForSource,
    scheduleStorefrontDomTruthBeacon: scheduleStorefrontDomTruthBeacon,
    scheduleStorefrontRuntimeTruthBeacon: scheduleStorefrontRuntimeTruthBeacon,
    postStorefrontRuntimeTruthBeacon: postStorefrontRuntimeTruthBeacon,
    readShellDomTruth: readShellDomTruth,
    logWidgetSettingsTruth: logWidgetSettingsTruth,
    collectRuntimeTruthSnapshot: collectRuntimeTruthSnapshot,
    logWidgetSettingsRuntimeTruth: logWidgetSettingsRuntimeTruth,
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
    widgetGloballyAllowed: widgetGloballyAllowed,
  };
  window.CartflowWidgetRuntime.Config = Config;
})();
