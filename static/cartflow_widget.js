/**
 * CartFlow — عرض سبب التردد بعد ‎step1‎ استرجاع (بلا مزوّد واتساب في الودجت).
 * ‎/demo/‎: يتخطّى انتظار ‎step1‎ (تجارب). باقي المسارات: حتى ‎GET /api/cartflow/ready‎.
 */
/** حالة VIP من مسار ‎cart_state_sync‎ فقط — بدون ‎window.cart_total‎. */
const cartflowState = {
  cartTotal: 0,
  itemsCount: 0,
  vipThreshold: 500,
  isVip: false,
};
try {
  window.cartflowState = cartflowState;
} catch (eCfsGlobal) {}

(function () {
  "use strict";

  function cfPerfDemoDevLog(line) {
    try {
      var p = window.location.pathname || "";
      if (/\/demo\b/i.test(p) || /^\/dev(\/|$)/i.test(p)) {
        console.log(line);
      }
    } catch (ePd) {}
  }

  try {
    if (window.__CARTFLOW_WIDGET_ACTIVE__ === true) {
      cfPerfDemoDevLog("[CF PERF] widget execution skipped duplicate");
      return;
    }
    window.__CARTFLOW_WIDGET_ACTIVE__ = true;
  } catch (eWd) {}

  if (
    window.CARTFLOW_WIDGET_RUNTIME_V2 === true &&
    window.__CF_LOAD_LEGACY_CARTFLOW_WIDGET !== true
  ) {
    cfPerfDemoDevLog("[CF PERF] widget execution skipped (layered runtime v2)");
    return;
  }

  /** هدوء بعد التحميل قبل مهام ثقيلَة لتقليل أثر Performance — لا يغيّر المنطق بعد التشغيل. */
  var CF_PAGESPEED_QUIET_AFTER_LOAD_MS = 3000;
  var cartflowMerchantEarlyInteract = false;

  (function cfBindMerchantInteractUnlockOnce() {
    try {
      if (window.__cfMerchantInteractUnlockBound === true) {
        return;
      }
      window.__cfMerchantInteractUnlockBound = true;
      var unlock = function () {
        cartflowMerchantEarlyInteract = true;
        try {
          var evNames = ["pointerdown", "touchstart", "keydown"];
          var o = { passive: true, capture: true };
          var ei;
          for (ei = 0; ei < evNames.length; ei++) {
            document.removeEventListener(evNames[ei], unlock, o);
            window.removeEventListener(evNames[ei], unlock, o);
          }
        } catch (eRm) {}
      };
      var evNamesIU = ["pointerdown", "touchstart", "keydown"];
      var oListen = { passive: true, capture: true };
      var ej;
      for (ej = 0; ej < evNamesIU.length; ej++) {
        document.addEventListener(evNamesIU[ej], unlock, oListen);
        window.addEventListener(evNamesIU[ej], unlock, oListen);
      }
    } catch (eBk) {}
  })();

  function cfScheduleMerchantHeavyAfterLoadIdle(done) {
    function runDeferred() {
      cfPerfDemoDevLog("[CF PERF] idle start enabled");
      try {
        if (typeof done === "function") {
          done();
        }
      } catch (ecb) {}
    }

    function afterQuietGate() {
      var loadTs = Date.now();
      function tickQuiet() {
        if (
          cartflowMerchantEarlyInteract ||
          Date.now() - loadTs >= CF_PAGESPEED_QUIET_AFTER_LOAD_MS
        ) {
          if (typeof window.requestIdleCallback === "function") {
            window.requestIdleCallback(runDeferred, { timeout: 5000 });
          } else {
            window.setTimeout(runDeferred, 16);
          }
        } else {
          window.setTimeout(
            tickQuiet,
            Math.min(
              200,
              Math.max(
                0,
                loadTs +
                  CF_PAGESPEED_QUIET_AFTER_LOAD_MS -
                  Date.now()
              )
            )
          );
        }
      }
      tickQuiet();
    }

    try {
      if (document.readyState === "complete") {
        afterQuietGate();
      } else {
        window.addEventListener("load", afterQuietGate, false);
      }
    } catch (eSch) {}
  }

  window.__cartflow_widget_build = "vip-runtime-state-v1";
  try {
    console.log("[CARTFLOW WIDGET BUILD]", window.__cartflow_widget_build);
  } catch (eBl) {}

  function setCartflowRuntimeState(cartTotal, vipThreshold, suppressReadyLog) {
    var total = Number(cartTotal || 0);
    var threshold = Number(vipThreshold || 0);
    if (isNaN(total)) {
      total = 0;
    }
    if (isNaN(threshold)) {
      threshold = 0;
    }
    window.cart_total = total;
    window.vip_threshold = threshold;
    window.is_vip = threshold > 0 && total >= threshold;
    if (!suppressReadyLog) {
      console.log("[VIP DATA READY]", {
        cart_total: window.cart_total,
        vip_threshold: window.vip_threshold,
        is_vip: window.is_vip,
      });
    }
  }
  try {
    window.setCartflowRuntimeState = setCartflowRuntimeState;
  } catch (eScr) {}

  window.CartFlowState =
    window.CartFlowState ||
    {
      hasCart: false,
      widgetShown: false,
      userRejectedHelp: false,
      rejectionTimestamp: null,
      lastIntentAt: null,
    };

  /** جمع رقم VIP داخل الفقاعة فقط؛ تعطيل اللوحة المنفصلة و‎vipImmediate‎ التلقائي. */
  var CARTFLOW_VIP_INLINE_FLOW_ONLY = true;

  var ARM_DELAY_MS = 3000;
  var IDLE_MS = 8000;
  /** على ‎/demo/store‎ عند تفعيل الودجت: عرض أسرع (ثانية تقريباً) */
  var DEMO_ARMED_IDLE_MS = 1600;
  /**
   * وقت السكون قبل إظهار الفقاعة بعد نشاط السلة — واجهة فقط؛ لا يُستخدم لتأخير واتساب.
   * يمكن تجاوزه: window.CARTFLOW_WIDGET_UI_IDLE_MS (بالمللي ثانية).
   */
  var WIDGET_CART_UI_IDLE_MS = 120000;
  var REASON_TAG_KEY = "cartflow_reason_tag";
  var REASON_SUB_TAG_KEY = "cartflow_reason_sub_tag";
  /** Layer D: سبب متروك السلة (مفاتيح منفصلة عن سبب الخطّة الأساسية) */
  var SESSION_ABANDON_REASON_TAG_KEY = "cartflow_abandon_reason_tag";
  var SESSION_ABANDON_CUSTOM_REASON_KEY = "cartflow_abandon_custom_reason";
  var DEMO_STORE_WIDGET_ARMED_KEY = "cartflow_demo_store_widget_armed";
  var DEMO_STORE_EXIT_INTENT_SHOWN_KEY = "cartflow_demo_store_exit_intent_shown";
  var DEMO_STORE_EXIT_PROMPT_RESOLVED_KEY = "cartflow_demo_store_exit_prompt_resolved";
  /** زائر بدون سلة رفض فقاعة الخروج — لا تعيد الإظهار هذه الجلسة. */
  var EXIT_INTENT_PRE_CART_DECLINED_KEY = "cartflow_exit_intent_pre_cart_declined";
  var shown = false;
  var idleTimer = null;
  /** مؤقّت مرتبط بحدث إضافة للسلة (شرط ‎after_cart_add‎ / ‎cart_interaction‎) وليس بإعادة ضبط النشاط. */
  var cfHesitationAnchorTimer = null;
  var cfHesitationScheduledAtMs = 0;
  var cfHesitationExpectedFireAtMs = 0;
  var cfHesitationScheduleGen = 0;
  var step1Ready = false;
  /** على مسارات ‎/demo/‎: بعد أول طلب ‎public-config‎ يُعتمد التخصيص لتجنّب فتح الفقاعة بلون افتراضي. */
  var demoCustomizationLoaded = false;
  var step1Poll = null;
  var armListenersAttached = false;
  var demoStoreBubbleDismissed = false;
  /** خروج ذكي مع سلة: إرفاق بعد تأكيد وجود أصناف فقط؛ لا يغيّر مؤقّت الدقيقتين. */
  var cartSmartExitAttached = false;
  var cartSmartExitPollInterval = null;
  var cartSmartExitLastMouseY = null;
  var cartSmartExitScrollLastY = 0;
  var cartSmartExitInactivityTimer = null;
  var cartSmartExitLastFireTs = 0;
  /** فتح تأخّر خروج الصفحة — يستهلك إعداد الخروج الموحّد. */
  var cfExitIntentScheduledOpenTimer = null;
  /** مصدر فتح الودجت — نص الترحيب فقط */
  var TRIGGER_SOURCE_CART = "cart";
  var TRIGGER_SOURCE_EXIT_INTENT = "exit_intent";
  var events = ["mousemove", "keydown", "scroll", "click", "touchstart"];

  var BTN_BACK = "رجوع";
  var BTN_HANDOFF = "تحويل لصاحب المتجر";
  var BTN_RETURN_CART = "العودة للسلة";

  /**
   * ترتيب أزرار الاستجابة (قابل لاحقاً لربط لوحة/‏JSON دون بثّق أزرار مبعثرة).
   * price: تضم ‎discount_offer‎ ثم الباقي. باقي الأسباب: من ‎alternatives‎ (نص مرتبط بالمنتج).
   */
  var CARTFLOW_REASON_ACTION_ORDER = {
    price: [
      "discount_offer",
      "alternatives",
      "merchant_handoff",
      "back",
      "return_to_cart",
    ],
    quality: ["alternatives", "merchant_handoff", "back", "return_to_cart"],
    warranty: ["alternatives", "merchant_handoff", "back", "return_to_cart"],
    shipping: ["alternatives", "merchant_handoff", "back", "return_to_cart"],
    thinking: ["alternatives", "merchant_handoff", "back", "return_to_cart"],
  };

  var CARTFLOW_ACTIONS = {
    discount_offer: {
      label: "🎁 عرض / خصم",
      discountMessage:
        "حالياً ما فيه عرض ظاهر، لكن أقدر أتحقق لك أو أحولك للمتجر 👍",
    },
    alternatives: { useFlowA1: true, label: "خيارات أخرى" },
    merchant_handoff: { useStaticLabel: "handoff" },
    back: { useStaticLabel: "back" },
    return_to_cart: { useStaticLabel: "return_to_cart" },
  };

  var CARTFLOW_PRICE_SUB_OPTIONS = [
    { sub: "price_discount_request", label: "أبحث عن كود خصم" },
    { sub: "price_budget_issue", label: "السعر أعلى من ميزانيتي" },
    { sub: "price_cheaper_alternative", label: "أريد خيار أرخص" },
  ];

  var CARTFLOW_REASON_PERSONALIZE_DEFAULT =
    "تم تجهيز رسالة متابعة مناسبة بناءً على سبب التردد";

  var DESC_KEYS = [
    "description",
    "desc",
    "body",
    "long_description",
    "details",
    "summary",
  ];
  var CAT_KEYS = [
    "category",
    "category_name",
    "product_category",
    "cat",
  ];
  var WARR_KEYS = ["warranty", "warranty_info", "guarantee", "warrantyText"];
  var SHIP_KEYS = [
    "shipping",
    "shipping_info",
    "delivery_info",
    "shipping_text",
  ];

  function strTrim(s) {
    if (s == null) {
      return "";
    }
    return String(s).replace(/\s+/g, " ").trim();
  }

  /** من لوحة الاسترجاع: نمط نص المساعدة القصير (اكتشاف ما قبل السلة). */
  var widgetTemplateMode = "preset";
  var widgetTemplateTone = "friendly";
  var widgetTemplateCustomText = "";
  /** رسالة الخروج قبل السلة — منفصلة عن نص اكتشاف المنتجات. */
  var widgetExitIntentMode = "preset";
  var widgetExitIntentTone = "friendly";
  var widgetExitIntentCustomText = "";
  /** تخصيص مظهر الودجيت (من لوحة الاسترجاع / جاهزية / public-config). */
  var widgetBrandName = "مساعد المتجر";
  var widgetPrimaryColor = "#6C5CE7";
  var widgetChromeStyle = "modern";
  /** للودجت: عتبة السلة المميزة من الخادم (‎vip_cart_threshold‎)، ‎null‎ = معطّل. */
  var widgetVipCartThreshold = null;
  /** تحكم التاجر (‎cartflow_widget_*‎): إظهار محتوى الاستعادة للعميل فقط */
  var cfWgEnabled = true;
  var cfWgPromptNotBefore = 0;
  var cfWgGateScheduled = false;
  /** لوحة مصغّرة لجمع رقم العميل عند سلّة VIP بلا رقم (لا تُغلق الواجهة تلقائياً بعد الحفظ). */
  var vipPhoneCapturePanel = null;
  var vipPhoneCaptureShowingSuccess = false;
  var CF_SS_VIP_PHONE_DISMISS = "cartflow_vip_phone_capture_dismissed";
  var EXIT_INTENT_PRESET_BY_TONE = {
    friendly:
      "هلا 👋\nفيه خيارات ممكن تعجبك 👍\nتحب أشوفها لك بسرعة؟",
    formal:
      "مرحباً 👋\nيمكنني مساعدتك في استعراض خيارات مناسبة لك\nهل ترغب بالاطلاع عليها؟",
    sales:
      "قبل ما تطلع 👋\nعندي خيارات ممكن تناسبك أكثر 👌\nخلني أوريك الأفضل الآن",
  };
  var DISCOVERY_HELPER_SECOND_LINE =
    "تقدر تختار اللي يناسبك وتضيفه للسلة بسهولة 👍";
  var TONE_DISCOVERY_FIRST_LINE = {
    friendly: "جبت لك خيارات مناسبة 👇",
    formal: "تم توفير خيارات مناسبة لك 👇",
    sales: "هذه أفضل الخيارات لك الآن 👇",
  };

  var CF_WIDGET_TRIGGER_DEFAULTS = {
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
    widget_brand_line_ar: "",
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
  };
  var cfWidgetTriggerRuntime = null;
  var cfReasonTemplatesRuntime = null;
  var CF_LS_WIDGET_LAST_SHOWN = "cartflow_cf_widget_last_shown_ts";
  var CF_SS_WIDGET_SHOWN = "cartflow_cf_widget_shown_session";
  var CF_SS_WIDGET_DISMISS = "cartflow_cf_suppress_after_dismiss";

  function mergeCfWidgetTrigger(patch) {
    var o = {};
    var k;
    for (k in CF_WIDGET_TRIGGER_DEFAULTS) {
      if (Object.prototype.hasOwnProperty.call(CF_WIDGET_TRIGGER_DEFAULTS, k)) {
        o[k] = CF_WIDGET_TRIGGER_DEFAULTS[k];
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

  function getCfWidgetTrigger() {
    return cfWidgetTriggerRuntime || CF_WIDGET_TRIGGER_DEFAULTS;
  }

  function cfCheckoutPathActive() {
    try {
      var p = String(window.location.pathname || "") + String(window.location.search || "");
      return /\/checkout\b/i.test(p);
    } catch (eCh) {
      return false;
    }
  }

  function cfReadDismissSuppressFlag() {
    try {
      return window.sessionStorage.getItem(CF_SS_WIDGET_DISMISS) === "1";
    } catch (e1) {
      return false;
    }
  }

  function cfMarkDismissSuppressFlag() {
    try {
      window.sessionStorage.setItem(CF_SS_WIDGET_DISMISS, "1");
    } catch (e2) {
      /* ignore */
    }
  }

  function cfPageScopeAllowsCartUi() {
    var tr = getCfWidgetTrigger();
    var sc = String(tr.visibility_page_scope || "all").toLowerCase();
    var path = String(window.location.pathname || "");
    var full = path + String(window.location.search || "");
    if (sc === "all") {
      return true;
    }
    if (sc === "cart") {
      return (
        /\/cart\b/i.test(full) ||
        /\/checkout\b/i.test(full) ||
        /\/demo\/store\/cart/i.test(full) ||
        path === "/demo/store" ||
        path.indexOf("/demo/store/") === 0
      );
    }
    if (sc === "product") {
      if (/\/cart\b|\/checkout\b/i.test(full)) {
        return false;
      }
      return /\/products?\b|\/collections?\b|\/demo\/store\b/i.test(full) || path.length > 1;
    }
    return true;
  }

  function cfExitIntentSurfaceAllowed() {
    var tr = getCfWidgetTrigger();
    if (!tr.exit_intent_enabled) {
      return false;
    }
    var sc = String(tr.visibility_page_scope || "all").toLowerCase();
    var path = String(window.location.pathname || "");
    var full = path + String(window.location.search || "");
    if (sc === "all") {
      return true;
    }
    if (sc === "cart") {
      return /\/cart\b|\/checkout\b|\/demo\/store\/cart/i.test(full) || path === "/demo/store";
    }
    if (sc === "product") {
      return (
        !/\/cart\b|\/checkout\b/i.test(full) &&
        (path === "/demo/store" || /\/product/i.test(full) || path.indexOf("/demo/store/") === 0)
      );
    }
    return true;
  }

  function cfFrequencyAllowsShow(openSource) {
    void openSource;
    var tr = getCfWidgetTrigger();
    var mode = String(tr.exit_intent_frequency || "per_session").toLowerCase();
    var now = Date.now();
    try {
      if (mode === "per_session") {
        if (window.sessionStorage.getItem(CF_SS_WIDGET_SHOWN) === "1") {
          return false;
        }
      } else if (mode === "per_24h") {
        var raw = window.localStorage.getItem(CF_LS_WIDGET_LAST_SHOWN);
        var last = raw ? parseInt(String(raw), 10) : 0;
        if (isFinite(last) && last > 0 && now - last < 86400000) {
          return false;
        }
      } else if (mode === "no_rapid_repeat") {
        var raw2 = window.localStorage.getItem(CF_LS_WIDGET_LAST_SHOWN);
        var last2 = raw2 ? parseInt(String(raw2), 10) : 0;
        if (isFinite(last2) && last2 > 0 && now - last2 < 120000) {
          return false;
        }
      }
    } catch (eFq) {
      return true;
    }
    return true;
  }

  function cfMarkWidgetShownForFrequency() {
    var now = Date.now();
    try {
      window.sessionStorage.setItem(CF_SS_WIDGET_SHOWN, "1");
    } catch (eS) {
      /* ignore */
    }
    try {
      window.localStorage.setItem(CF_LS_WIDGET_LAST_SHOWN, String(now));
    } catch (eL) {
      /* ignore */
    }
  }

  function cfPhoneCaptureMode() {
    var allowed = { after_reason: 1, immediate: 1, none: 1 };
    var raw = getCfWidgetTrigger().widget_phone_capture_mode;
    var s = String(raw == null || raw === "" ? "after_reason" : raw)
      .trim()
      .toLowerCase()
      .replace(/[\s\-]+/g, "_");
    if (allowed[s]) {
      return s;
    }
    return "after_reason";
  }

  function cfCustomerPhoneSaved() {
    try {
      var p = localStorage.getItem(CARTFLOW_LS_CUSTOMER_PHONE);
      return !!(p && String(p).trim());
    } catch (ePh) {
      return false;
    }
  }

  function getCfReasonTemplates() {
    return cfReasonTemplatesRuntime && typeof cfReasonTemplatesRuntime === "object"
      ? cfReasonTemplatesRuntime
      : {};
  }

  function cfReasonTemplateEnabled(slug) {
    var rt = getCfReasonTemplates();
    var e = rt[String(slug || "").toLowerCase()];
    if (!e || typeof e !== "object") {
      return true;
    }
    return e.enabled !== false;
  }

  /** تسميات أسباب Layer D المعروضة للعميل — كتالوج ثابت؛ لا تعتمد على ‎reason_templates.message‎ (استرجاع). */
  function cfDefaultReasonLabels() {
    return {
      price: "السعر",
      quality: "الجودة",
      warranty: "الضمان",
      shipping: "الشحن",
      delivery: "مدة التوصيل",
      other: "سبب آخر",
    };
  }

  function cfReasonSurfaceLabel(reasonKey, defaultLabel) {
    var k = String(reasonKey || "").toLowerCase();
    var defs = cfDefaultReasonLabels();
    if (defs[k] != null) {
      return defs[k];
    }
    return defaultLabel != null ? String(defaultLabel) : k;
  }

  function cfReasonTemplatesLogSnapshot() {
    var keys = [
      "price",
      "quality",
      "shipping",
      "delivery",
      "warranty",
      "other",
    ];
    var rt = getCfReasonTemplates();
    var out = [];
    var i;
    for (i = 0; i < keys.length; i++) {
      var kk = keys[i];
      var ent = rt[kk];
      var en = true;
      if (ent && typeof ent === "object" && ent.enabled === false) {
        en = false;
      }
      var defL = cfDefaultReasonLabels()[kk] != null ? cfDefaultReasonLabels()[kk] : kk;
      out.push({
        key: kk,
        enabled: en,
        label: cfReasonSurfaceLabel(kk, defL),
      });
    }
    return out;
  }

  /**
   * وحدة وقت تشغيل موحدة: إعداد مهيّأ، مهيّلي التردّد بعد الإضافة، وبوابات الخروج.
   * المصدر المعتمد لقرارات هذه الدوال هو ‎cfRuntimeConfig()‎ فقط.
   */
  var CartFlowRuntimeController = {};
  var cfRuntimeTrigger = { timer: null, expectedAt: null, source: null };
  try {
    window.__cfRuntimeTriggerRef = cfRuntimeTrigger;
    window.__cfRuntimeConfigSnap = null;
  } catch (eRf) {}

  function cfNormalizeToken(raw, allowed, fallback) {
    var map = {};
    var i;
    for (i = 0; i < allowed.length; i++) {
      map[allowed[i]] = 1;
    }
    var s = String(raw == null ? "" : raw)
      .trim()
      .toLowerCase()
      .replace(/[\s\-]+/g, "_");
    return map[s] ? s : fallback;
  }

  function cfExitIntentFreqNorm(raw) {
    var s = cfNormalizeToken(
      raw,
      ["per_session", "per_24h", "no_rapid_repeat"],
      "per_session"
    );
    return s || "per_session";
  }

  function cfExitIntentSensNorm(raw) {
    return cfNormalizeToken(raw, ["low", "medium", "high"], "medium");
  }

  /**
   * @returns {{
   *   widget_enabled:boolean,
   *   hesitation_enabled:boolean,
   *   hesitation_condition:string,
   *   hesitation_delay_seconds:number,
   *   exit_intent_enabled:boolean,
   *   exit_intent_delay_seconds:number,
   *   exit_intent_sensitivity:string,
   *   exit_intent_frequency:string,
   *   page_scope:string,
   *   phone_capture_mode:string,
   *   visible_reasons:{key:string,label:string}[]
   * }}
   */
  function cfRuntimeConfig(silentLog) {
    var tr = getCfWidgetTrigger();
    var hesitationCondRaw = cfNormalizeToken(
      tr && tr.hesitation_condition != null ? tr.hesitation_condition : "",
      ["after_cart_add", "inactivity", "repeated_view", "cart_interaction"],
      "after_cart_add"
    );
    var hesitationSecRaw =
      tr &&
      typeof tr.hesitation_after_seconds === "number" &&
      isFinite(tr.hesitation_after_seconds)
        ? tr.hesitation_after_seconds
        : 20;
    if (hesitationSecRaw < 0) {
      hesitationSecRaw = 0;
    }
    if (hesitationSecRaw > 600) {
      hesitationSecRaw = 600;
    }
    var exitDly = 0;
    try {
      if (
        tr &&
        typeof tr.exit_intent_delay_seconds === "number" &&
        isFinite(tr.exit_intent_delay_seconds)
      ) {
        exitDly = Math.max(
          0,
          Math.min(60, Math.floor(tr.exit_intent_delay_seconds))
        );
      }
    } catch (eExD) {}

    var visRows = cfBuildVisibleReasonRows();

    /**
     * ‎visibility_widget_globally_enabled‎ و ‎visibility_temporarily_disabled‎ يحددان إن كان
     * عرض الويدجت مسموحاً للزائر (طبقة ظهور ويدجيت الاسترداد؛ لا علاقة لمحرك دورة الحياة).
     */
    var wgOn = true;
    try {
      if (tr.visibility_widget_globally_enabled === false) {
        wgOn = false;
      }
      if (tr.visibility_temporarily_disabled === true) {
        wgOn = false;
      }
    } catch (eVs) {}

    var cfg = {
      widget_enabled: !!wgOn,
      hesitation_enabled: !!(tr && tr.hesitation_trigger_enabled !== false),
      hesitation_condition: hesitationCondRaw,
      hesitation_delay_seconds: hesitationSecRaw,
      exit_intent_enabled: !!(tr && tr.exit_intent_enabled !== false),
      exit_intent_delay_seconds: exitDly,
      exit_intent_sensitivity: cfExitIntentSensNorm(
        tr ? tr.exit_intent_sensitivity : "medium"
      ),
      exit_intent_frequency: cfExitIntentFreqNorm(
        tr ? tr.exit_intent_frequency : "per_session"
      ),
      page_scope: cfNormalizeToken(
        tr && tr.visibility_page_scope != null ? tr.visibility_page_scope : "",
        ["product", "cart", "all"],
        "all"
      ),
      phone_capture_mode: cfNormalizeToken(
        tr && tr.widget_phone_capture_mode != null
          ? tr.widget_phone_capture_mode
          : "after_reason",
        ["after_reason", "immediate", "none"],
        "after_reason"
      ),
      visible_reasons: visRows.map(function (row) {
        return { key: row.r, label: row.label };
      }),
    };

    CartFlowRuntimeController.lastConfig = cfg;
    CartFlowRuntimeController.trigger = cfRuntimeTrigger;
    try {
      window.__cfRuntimeConfigSnap = cfg;
    } catch (eSn) {}

    if (!silentLog) {
      try {
        console.log("[CF RUNTIME CONFIG]", cfg);
      } catch (eLc) {}
    }

    return cfg;
  }

  function cfHasValidStoredPhone() {
    return !!getCartflowStoredCustomerPhoneNorm();
  }

  function cfDeferAfterReasonPhoneCapture() {
    if (cfRuntimeConfig(true).phone_capture_mode !== "after_reason") {
      return false;
    }
    if (cartflowState.isVip === true) {
      return false;
    }
    if (cfHasValidStoredPhone()) {
      return false;
    }
    return true;
  }

  function cfRuntimeClearHesitationTimer(reasonNote, silentLogClear) {
    try {
      if (cfRuntimeTrigger.timer != null) {
        clearTimeout(cfRuntimeTrigger.timer);
      }
      if (cfHesitationAnchorTimer != null && cfHesitationAnchorTimer !== cfRuntimeTrigger.timer) {
        clearTimeout(cfHesitationAnchorTimer);
      }
    } catch (eClr) {}
    cfRuntimeTrigger.timer = null;
    cfRuntimeTrigger.expectedAt = null;
    cfRuntimeTrigger.source = null;
    cfHesitationAnchorTimer = null;
    cfHesitationScheduledAtMs = 0;
    cfHesitationExpectedFireAtMs = 0;
    if (!silentLogClear) {
      try {
        console.log("[CF TIMER CLEAR]", { reason: String(reasonNote || "") });
      } catch (eLg0) {}
    }
  }

  function cfRuntimeClearHesitationTimeoutOnlyNoFlags() {
    try {
      if (cfRuntimeTrigger.timer != null) {
        clearTimeout(cfRuntimeTrigger.timer);
      }
      if (cfHesitationAnchorTimer != null && cfHesitationAnchorTimer !== cfRuntimeTrigger.timer) {
        clearTimeout(cfHesitationAnchorTimer);
      }
    } catch (eTmo) {}
    cfRuntimeTrigger.timer = null;
    cfHesitationAnchorTimer = null;
  }

  function cfLayerDChipSpecForReason(reasonKey) {
    var k = String(reasonKey || "").toLowerCase();
    var map = {
      price: { tag: "price_high", defaultLabel: "السعر مرتفع" },
      quality: { tag: "quality_uncertainty", defaultLabel: "غير متأكد من الجودة" },
      shipping: { tag: "shipping_cost", defaultLabel: "تكلفة الشحن" },
      delivery: { tag: "delivery_time", defaultLabel: "مدة التوصيل" },
      warranty: { tag: "warranty", defaultLabel: "الضمان" },
      other: { tag: "_other", defaultLabel: "سبب آخر / أحتاج أتحدث معك" },
    };
    return map[k] || null;
  }

  function cfLayerDChipsFromConfig() {
    var tr = getCfWidgetTrigger();
    var order = Array.isArray(tr.reason_display_order)
      ? tr.reason_display_order
      : CF_WIDGET_TRIGGER_DEFAULTS.reason_display_order;
    var out = [];
    var i;
    for (i = 0; i < order.length; i++) {
      var rk = String(order[i] || "").toLowerCase();
      if (!rk || !cfReasonTemplateEnabled(rk)) {
        continue;
      }
      var spec = cfLayerDChipSpecForReason(rk);
      if (!spec) {
        continue;
      }
      out.push({
        tag: spec.tag,
        label: cfReasonSurfaceLabel(rk, spec.defaultLabel),
        reasonKey: rk,
      });
    }
    out.push({
      tag: "no_help",
      label: "ما أحتاج مساعدة الآن",
      reasonKey: null,
    });
    return out;
  }

  function cfBuildVisibleReasonRows() {
    var tr = getCfWidgetTrigger();
    var order = Array.isArray(tr.reason_display_order)
      ? tr.reason_display_order
      : CF_WIDGET_TRIGGER_DEFAULTS.reason_display_order;
    var labels = cfDefaultReasonLabels();
    var out = [];
    var i;
    for (i = 0; i < order.length; i++) {
      var r = String(order[i] || "").toLowerCase();
      if (!r || !cfReasonTemplateEnabled(r)) {
        continue;
      }
      var defLab = labels[r] != null ? labels[r] : r;
      var lab = cfReasonSurfaceLabel(r, defLab);
      out.push({ r: r, label: lab });
    }
    return out;
  }

  function cfExitIntentInactivityMs() {
    var tr = getCfWidgetTrigger();
    var base = 10000;
    try {
      var sens = String(tr.exit_intent_sensitivity || "medium").toLowerCase();
      if (sens === "low") {
        base = 16000;
      } else if (sens === "high") {
        base = 6500;
      }
    } catch (eSens) {
      base = 10000;
    }
    var d = 0;
    try {
      if (typeof tr.exit_intent_delay_seconds === "number" && isFinite(tr.exit_intent_delay_seconds)) {
        d = Math.max(0, Math.min(60, tr.exit_intent_delay_seconds));
      }
    } catch (eDel) {
      d = 0;
    }
    return base + d * 1000;
  }

  function cfExitIntentScrollDelta() {
    try {
      var sens = String(getCfWidgetTrigger().exit_intent_sensitivity || "medium").toLowerCase();
      if (sens === "low") {
        return 180;
      }
      if (sens === "high") {
        return 80;
      }
    } catch (eSd) {
      /* ignore */
    }
    return 120;
  }

  function cfMaybeMarkDismissSuppress() {
    try {
      if (getCfWidgetTrigger().suppress_after_widget_dismiss) {
        cfMarkDismissSuppressFlag();
      }
    } catch (eMs) {
      /* ignore */
    }
  }

  function cfLogWidgetTriggerBlocked(reasonCode, extra) {
    try {
      console.log(
        "[WIDGET TRIGGER BLOCKED] reason=" +
          String(reasonCode || "") +
          (extra != null ? " " + String(extra) : "")
      );
    } catch (eLb) {
      /* ignore */
    }
  }

  function cfLogWidgetTriggerFired(source) {
    try {
      console.log("[WIDGET TRIGGER FIRED] source=" + String(source || ""));
    } catch (eLf) {
      /* ignore */
    }
  }

  function applyWidgetRuntimeConfigFromPayload(j, configSource) {
    if (!j || typeof j !== "object") {
      return;
    }
    var cfgSrc = configSource != null ? String(configSource) : "unknown";
    if (j.widget_trigger_config && typeof j.widget_trigger_config === "object") {
      cfWidgetTriggerRuntime = mergeCfWidgetTrigger(j.widget_trigger_config);
      try {
        var trAp = getCfWidgetTrigger();
        console.log("[WIDGET TRIGGER CONFIG APPLIED]", {
          hesitation_trigger_enabled: !!trAp.hesitation_trigger_enabled,
          hesitation_condition: trAp.hesitation_condition,
          hesitation_after_seconds: trAp.hesitation_after_seconds,
          visibility_page_scope: trAp.visibility_page_scope,
          widget_phone_capture_mode_raw: trAp.widget_phone_capture_mode,
          widget_phone_capture_mode: cfPhoneCaptureMode(),
        });
      } catch (eTrAp) {
        /* ignore */
      }
    }
    if (j.reason_templates && typeof j.reason_templates === "object") {
      cfReasonTemplatesRuntime = j.reason_templates;
    } else {
      cfReasonTemplatesRuntime = null;
    }
    try {
      var ord = getCfWidgetTrigger().reason_display_order || [];
      var trigForPhone = getCfWidgetTrigger();
      console.log("[WIDGET CONFIG LOADED]", {
        store_slug: getStoreSlug(),
        config_source: cfgSrc,
        reason_display_order: ord.slice(),
        reason_templates: cfReasonTemplatesLogSnapshot(),
        exit_intent_enabled: getCfWidgetTrigger().exit_intent_enabled,
        exit_intent_sensitivity: getCfWidgetTrigger().exit_intent_sensitivity,
        exit_intent_delay_seconds: getCfWidgetTrigger().exit_intent_delay_seconds,
        exit_intent_frequency: getCfWidgetTrigger().exit_intent_frequency,
        hesitation_trigger_enabled: getCfWidgetTrigger().hesitation_trigger_enabled,
        hesitation_after_seconds: getCfWidgetTrigger().hesitation_after_seconds,
        hesitation_condition: getCfWidgetTrigger().hesitation_condition,
        visibility_page_scope: getCfWidgetTrigger().visibility_page_scope,
        widget_phone_capture_mode_raw: trigForPhone.widget_phone_capture_mode,
        widget_phone_capture_mode: cfPhoneCaptureMode(),
        suppress_after_widget_dismiss: getCfWidgetTrigger().suppress_after_widget_dismiss,
        suppress_after_purchase: getCfWidgetTrigger().suppress_after_purchase,
        suppress_when_checkout_started: getCfWidgetTrigger().suppress_when_checkout_started,
      });
      var visRows = cfBuildVisibleReasonRows();
      var ALL_R = [
        "price",
        "quality",
        "shipping",
        "delivery",
        "warranty",
        "other",
      ];
      var disabledKeys = [];
      var dk;
      for (dk = 0; dk < ALL_R.length; dk++) {
        if (!cfReasonTemplateEnabled(ALL_R[dk])) {
          disabledKeys.push(ALL_R[dk]);
        }
      }
      var layerChips = cfLayerDChipsFromConfig();
      console.log("[WIDGET CONFIG APPLIED]", {
        visible_reason_keys: visRows.map(function (x) {
          return x.r;
        }),
        visible_reason_labels: visRows.map(function (x) {
          return x.label;
        }),
        disabled_reason_keys: disabledKeys,
        layer_d_chip_tags: layerChips.map(function (c) {
          return c.tag;
        }),
        layer_d_chip_count: layerChips.length,
      });
    } catch (eCfg) {
      /* ignore */
    }
    try {
      window.__cfWidgetTriggerRuntime = getCfWidgetTrigger();
      window.__cfReasonTemplatesRuntime = cfReasonTemplatesRuntime;
    } catch (eW) {
      /* ignore */
    }
    try {
      cfRuntimeConfig(false);
    } catch (eRfSnap) {}
  }

  function normalizeWidgetPrimaryHexClient(raw) {
    var def = "#6C5CE7";
    if (raw == null || raw === "") return def;
    var s = String(raw).trim();
    if (/^#[0-9A-Fa-f]{6}$/.test(s)) return "#" + s.slice(1).toUpperCase();
    if (/^#[0-9A-Fa-f]{3}$/.test(s)) {
      var h = s.slice(1);
      return ("#" + h[0] + h[0] + h[1] + h[1] + h[2] + h[2]).toUpperCase();
    }
    var nx = String(raw).replace(/^#/, "");
    if (/^[0-9A-Fa-f]{6}$/.test(nx)) return "#" + nx.toUpperCase();
    return def;
  }

  function hexToRgbTuple(hex) {
    var h = normalizeWidgetPrimaryHexClient(hex);
    var n = parseInt(h.slice(1), 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  function rgbToCssHex(r, g, b) {
    function p(x) {
      var v = Math.max(0, Math.min(255, Math.round(x)));
      var t = v.toString(16);
      return t.length === 1 ? "0" + t : t;
    }
    return "#" + p(r) + p(g) + p(b);
  }

  function shadeHex(hex, t) {
    var rgb = hexToRgbTuple(hex);
    function f(c) {
      if (t >= 0) return c + (255 - c) * t;
      return c * (1 + t);
    }
    return rgbToCssHex(f(rgb[0]), f(rgb[1]), f(rgb[2]));
  }

  function relativeLuminanceHex(hex) {
    var rgb = hexToRgbTuple(hex);
    var lin = rgb.map(function (c) {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2];
  }

  function contrastRatioAgainstWhite(bgHex) {
    var L = relativeLuminanceHex(bgHex);
    var Lw = 1;
    var hi = Math.max(Lw, L);
    var lo = Math.min(Lw, L);
    return (hi + 0.05) / (lo + 0.05);
  }

  /** يضبط لون الزر حتى يبقى النص الأبيض مقروءاً تقريباً (‎WCAG‎ تقريبي). */
  function widgetButtonFillHex(hex) {
    var h = normalizeWidgetPrimaryHexClient(hex);
    var i;
    for (i = 0; i < 18; i++) {
      if (contrastRatioAgainstWhite(h) >= 4.2) break;
      h = shadeHex(h, -0.14);
    }
    return h;
  }

  function getWidgetPrimaryButtonStyle() {
    var pcRaw = normalizeWidgetPrimaryHexClient(widgetPrimaryColor);
    var pcFill = widgetButtonFillHex(widgetPrimaryColor);
    if (widgetChromeStyle === "minimal") {
      return (
        "cursor:pointer!important;border:2px solid " +
        pcRaw +
        "!important;border-radius:6px!important;padding:10px 17px!important;font:inherit!important;font-weight:600!important;" +
        "background:#ffffff!important;color:" +
        pcRaw +
        "!important;min-height:44px!important;box-sizing:border-box!important;touch-action:manipulation!important;box-shadow:none!important;"
      );
    }
    var rad = widgetChromeStyle === "bold" ? "16px" : "11px";
    var padV = widgetChromeStyle === "bold" ? "15px" : "11px";
    var padH = widgetChromeStyle === "bold" ? "23px" : "17px";
    var fw = widgetChromeStyle === "bold" ? "800" : "600";
    var shadow =
      widgetChromeStyle === "bold"
        ? "box-shadow:0 14px 34px rgba(0,0,0,.42)!important;"
        : "box-shadow:0 8px 22px rgba(0,0,0,.18)!important;";
    return (
      "cursor:pointer!important;border:0!important;border-radius:" +
      rad +
      "!important;padding:" +
      padV +
      " " +
      padH +
      "!important;font:inherit!important;font-weight:" +
      fw +
      "!important;background:" +
      pcFill +
      "!important;color:#fff!important;min-height:44px!important;box-sizing:border-box!important;touch-action:manipulation!important;" +
      shadow
    );
  }

  function widgetShellChromeCss() {
    if (widgetChromeStyle === "minimal") {
      return {
        radius: "6px",
        shadow: "none",
        border: "1px solid #e5e7eb",
        bg: "#ffffff",
        fg: "#0f172a",
      };
    }
    if (widgetChromeStyle === "bold") {
      return {
        radius: "18px",
        shadow:
          "0 22px 52px rgba(0,0,0,.52), 0 8px 22px rgba(0,0,0,.32)",
        border: "4px solid rgba(255,255,255,.42)",
        bg: "#120d28",
        fg: "#faf5ff",
      };
    }
    return {
      radius: "16px",
      shadow: "0 10px 34px rgba(0,0,0,.13), 0 4px 12px rgba(0,0,0,.06)",
      border: "",
      bg: "#1e1b4b",
      fg: "#f5f3ff",
    };
  }

  /** أزرار تصغير/إغلاق في شريط أدوات الودجيت — يختلف الشكل حسب ‎widget_style‎. */
  function chromeToolbarBtnStyle() {
    if (widgetChromeStyle === "minimal") {
      return (
        "cursor:pointer;border:1px solid #cbd5e1;border-radius:9px;padding:0 12px;font:inherit;font-size:18px;line-height:1;" +
        "font-weight:700;background:#f1f5f9;color:#334155;min-width:44px;min-height:44px;" +
        "box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;" +
        "touch-action:manipulation;box-shadow:none;"
      );
    }
    if (widgetChromeStyle === "bold") {
      return (
        "cursor:pointer;border:2px solid rgba(255,255,255,.4);border-radius:12px;padding:0 14px;font:inherit;font-size:18px;line-height:1;" +
        "font-weight:800;background:rgba(255,255,255,.26);color:#ffffff;min-width:48px;min-height:48px;" +
        "box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;" +
        "touch-action:manipulation;box-shadow:0 5px 16px rgba(0,0,0,.32);"
      );
    }
    return (
      "cursor:pointer;border:0;border-radius:10px;padding:0 12px;font:inherit;font-size:18px;line-height:1;" +
      "font-weight:700;background:rgba(255,255,255,.14);color:#f5f3ff;min-width:44px;min-height:44px;" +
      "box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;" +
      "touch-action:manipulation;box-shadow:0 2px 10px rgba(0,0,0,.14);"
    );
  }

  var _cfWidgetDynCssInserted = false;

  function ensureWidgetCustomizationDynamicCss() {
    if (_cfWidgetDynCssInserted) {
      return;
    }
    try {
      var st = document.createElement("style");
      st.id = "cartflow-widget-customization-dynamic";
      st.textContent =
        "[data-cartflow-bubble].cf-widget-style-bold button[data-cf-widget-primary-btn]:hover {" +
        "filter:brightness(1.14)!important;transform:translateY(-2px) scale(1.03)!important;" +
        "}" +
        "[data-cartflow-bubble].cf-widget-style-modern button[data-cf-widget-primary-btn]:hover {" +
        "filter:brightness(1.08)!important;" +
        "}" +
        "[data-cartflow-bubble].cf-widget-style-minimal button[data-cf-widget-primary-btn]:hover {" +
        "background:#f8fafc!important;" +
        "}";
      document.head.appendChild(st);
      _cfWidgetDynCssInserted = true;
    } catch (eCss) {
      /* ignore */
    }
  }

  function stampPrimaryBubbleBtn(el, extraCss) {
    if (!el || el.nodeType !== 1) {
      return;
    }
    el.setAttribute("data-cf-widget-primary-btn", "1");
    if (extraCss) {
      el.setAttribute("data-cf-primary-extra", String(extraCss));
    } else {
      el.removeAttribute("data-cf-primary-extra");
    }
    el.style.cssText = getWidgetPrimaryButtonStyle() + (extraCss || "");
  }

  function syncWidgetCustomizationToWindow() {
    try {
      window.widgetBrandName = widgetBrandName || "مساعد المتجر";
      window.widgetPrimaryColor = widgetPrimaryColor || "#6C5CE7";
      window.widgetChromeStyle = widgetChromeStyle || "modern";
    } catch (eWin) {
      /* ignore */
    }
  }

  function applyWidgetStyleClass(style, bubble) {
    if (!bubble) {
      return;
    }
    bubble.classList.remove(
      "cf-widget-style-modern",
      "cf-widget-style-minimal",
      "cf-widget-style-bold"
    );
    var st =
      style === "minimal" || style === "bold" ? style : "modern";
    bubble.classList.add("cf-widget-style-" + st);
  }

  function setWidgetHeaderColor(primaryHex, bubble) {
    if (!bubble) {
      return;
    }
    var header = bubble.querySelector("[data-cf-widget-header]");
    var title = bubble.querySelector("[data-cf-widget-title]");
    if (!header || !title) {
      return;
    }
    var pcNorm = normalizeWidgetPrimaryHexClient(primaryHex);
    var bandRadius =
      widgetChromeStyle === "bold"
        ? "14px"
        : widgetChromeStyle === "minimal"
        ? "6px"
        : "16px";
    if (widgetChromeStyle === "minimal") {
      header.style.setProperty("margin", "0 0 12px 0", "important");
      header.style.setProperty("padding", "11px 13px", "important");
      header.style.setProperty("border-radius", bandRadius, "important");
      header.style.setProperty("background", "#ffffff", "important");
      header.style.setProperty("box-shadow", "none", "important");
      header.style.setProperty("border-bottom", "3px solid " + pcNorm, "important");
      header.style.setProperty("border", "0", "important");
      title.style.setProperty("color", "#0f172a", "important");
      title.style.setProperty("font-weight", "700", "important");
      title.style.setProperty("font-size", "15px", "important");
    } else if (widgetChromeStyle === "bold") {
      header.style.setProperty("margin", "0 0 12px 0", "important");
      header.style.setProperty("padding", "14px 17px", "important");
      header.style.setProperty("border-radius", bandRadius, "important");
      header.style.setProperty("background", pcNorm, "important");
      header.style.setProperty(
        "box-shadow",
        "inset 0 -4px 0 rgba(0,0,0,.22)",
        "important"
      );
      header.style.setProperty(
        "border",
        "3px solid rgba(255,255,255,.45)",
        "important"
      );
      var lumB = relativeLuminanceHex(pcNorm);
      title.style.setProperty(
        "color",
        lumB > 0.55 ? "#0f172a" : "#ffffff",
        "important"
      );
      title.style.setProperty("font-weight", "800", "important");
      title.style.setProperty("font-size", "16px", "important");
      title.style.setProperty(
        "text-shadow",
        lumB > 0.55 ? "none" : "0 2px 6px rgba(0,0,0,.35)",
        "important"
      );
    } else {
      var bandDark = shadeHex(pcNorm, -0.48);
      var bandMid = shadeHex(pcNorm, -0.22);
      header.style.setProperty("margin", "0 0 11px 0", "important");
      header.style.setProperty("padding", "12px 14px", "important");
      header.style.setProperty("border-radius", bandRadius, "important");
      header.style.setProperty(
        "background",
        "linear-gradient(135deg," + bandDark + " 0%," + bandMid + " 100%)",
        "important"
      );
      header.style.setProperty(
        "box-shadow",
        "0 4px 18px rgba(0,0,0,.15)",
        "important"
      );
      header.style.setProperty("border", "0", "important");
      var lumM = relativeLuminanceHex(bandMid);
      title.style.setProperty(
        "color",
        lumM > 0.55 ? "#1e1b4b" : "#ffffff",
        "important"
      );
      title.style.setProperty("font-weight", "700", "important");
      title.style.setProperty("font-size", "15px", "important");
    }
    title.textContent = widgetBrandName || "مساعد المتجر";
  }

  function repaintWidgetShell(bubble) {
    if (!bubble) {
      return;
    }
    var shell = widgetShellChromeCss();
    bubble.style.setProperty("border-radius", shell.radius, "important");
    var sh =
      widgetChromeStyle === "minimal" ? "none" : shell.shadow;
    bubble.style.setProperty("box-shadow", sh, "important");
    var bd = "none";
    if (widgetChromeStyle === "minimal") {
      bd = "1px solid #e5e7eb";
    } else if (shell.border) {
      bd = shell.border;
    }
    bubble.style.setProperty("border", bd, "important");
    bubble.style.setProperty("background-color", shell.bg, "important");
    bubble.style.setProperty("background", shell.bg, "important");
    bubble.style.setProperty("color", shell.fg, "important");
    var pad =
      widgetChromeStyle === "minimal"
        ? "14px 16px"
        : widgetChromeStyle === "bold"
        ? "14px 17px"
        : "13px 15px";
    bubble.style.setProperty("padding", pad, "important");
  }

  function repaintWidgetChromeBar(bubble, pcNorm) {
    if (!bubble) {
      return;
    }
    var chrome = bubble.querySelector("[data-cf-chrome]");
    if (!chrome) {
      return;
    }
    var chromeBorderW =
      widgetChromeStyle === "minimal"
        ? "1px"
        : widgetChromeStyle === "bold"
        ? "4px"
        : "2px";
    var chromeBorderCol =
      widgetChromeStyle === "minimal" ? "#e5e7eb" : pcNorm;
    chrome.style.setProperty(
      "border-bottom",
      chromeBorderW + " solid " + chromeBorderCol,
      "important"
    );
    var gap = widgetChromeStyle === "bold" ? "10px" : "8px";
    chrome.style.setProperty("gap", gap, "important");
    chrome.style.setProperty("margin-bottom", "10px", "important");
    chrome.style.setProperty("padding-bottom", "10px", "important");
    var toolBtns = chrome.querySelectorAll("button");
    var ti;
    for (ti = 0; ti < toolBtns.length; ti++) {
      toolBtns[ti].style.cssText = chromeToolbarBtnStyle();
    }
  }

  function updateAllPrimaryButtons(primaryHex) {
    void primaryHex;
    var bubble = document.querySelector("[data-cartflow-bubble]");
    if (!bubble) {
      return;
    }
    var nodes = bubble.querySelectorAll('[data-cf-widget-primary-btn="1"]');
    var idx;
    for (idx = 0; idx < nodes.length; idx++) {
      var el = nodes[idx];
      var ex = el.getAttribute("data-cf-primary-extra");
      stampPrimaryBubbleBtn(el, ex ? String(ex) : "");
    }
  }

  function updateWidgetLauncherColor(primaryHex) {
    void primaryHex;
    var fab = document.querySelector("[data-cartflow-fab]");
    if (!fab) {
      return;
    }
    var fabFill = widgetButtonFillHex(widgetPrimaryColor);
    fab.style.setProperty("background", fabFill, "important");
    fab.style.setProperty("background-color", fabFill, "important");
    var fabRad =
      widgetChromeStyle === "minimal"
        ? "16px"
        : widgetChromeStyle === "bold"
        ? "50%"
        : "50%";
    var fabShadow =
      widgetChromeStyle === "minimal"
        ? "none"
        : widgetChromeStyle === "bold"
        ? "0 18px 48px rgba(0,0,0,.55), 0 6px 18px rgba(0,0,0,.3)"
        : "0 12px 34px rgba(0,0,0,.3)";
    fab.style.setProperty("box-shadow", fabShadow, "important");
    fab.style.setProperty("border-radius", fabRad, "important");
    var fabBorder =
      widgetChromeStyle === "minimal"
        ? "2px solid rgba(15,23,42,.12)"
        : widgetChromeStyle === "bold"
        ? "5px solid rgba(255,255,255,.48)"
        : "0";
    fab.style.setProperty("border", fabBorder, "important");
    var fabMin =
      widgetChromeStyle === "bold" ? "56px" : widgetChromeStyle === "minimal" ? "50px" : "48px";
    fab.style.setProperty("min-width", fabMin, "important");
    fab.style.setProperty("min-height", fabMin, "important");
    fab.style.setProperty("width", fabMin, "important");
    fab.style.setProperty("height", fabMin, "important");
  }

  function applyWidgetCustomization() {
    try {
      console.log("[WIDGET CUSTOMIZATION APPLIED]", {
        name: widgetBrandName,
        color: widgetPrimaryColor,
        style: widgetChromeStyle,
      });
    } catch (eLog) {
      /* ignore */
    }
    syncWidgetCustomizationToWindow();
    ensureWidgetCustomizationDynamicCss();
    var bubble = document.querySelector("[data-cartflow-bubble]");
    var pcNorm = normalizeWidgetPrimaryHexClient(widgetPrimaryColor);
    if (bubble) {
      repaintWidgetShell(bubble);
      applyWidgetStyleClass(widgetChromeStyle, bubble);
      setWidgetHeaderColor(widgetPrimaryColor, bubble);
      repaintWidgetChromeBar(bubble, pcNorm);
      updateAllPrimaryButtons(widgetPrimaryColor);
    }
    updateWidgetLauncherColor(widgetPrimaryColor);
  }

  try {
    window.applyWidgetCustomization = applyWidgetCustomization;
  } catch (eExWac) {
    /* ignore */
  }

  function cartflowWidgetMerchantDelayMs(value, unit) {
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

  function applyCartflowWidgetRecoveryGateFromConfig(j) {
    if (!j || typeof j !== "object") {
      return;
    }
    if ("cartflow_widget_enabled" in j) {
      cfWgEnabled = !!(
        j.cartflow_widget_enabled !== false &&
        j.cartflow_widget_enabled !== 0 &&
        j.cartflow_widget_enabled !== "0"
      );
    }
    if (!cfWgGateScheduled) {
      cfWgGateScheduled = true;
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
      cfWgPromptNotBefore = Date.now() + cartflowWidgetMerchantDelayMs(dv, du);
    }
    if (!cfWgEnabled) {
      try {
        hideVipPhoneCapturePanel();
      } catch (ePh) {}
      try {
        shown = false;
        setCartflowWidgetShownFlag(false);
        removeFabIfAny();
        removeCartflowBubbleDom();
      } catch (eTeardown) {}
    }
  }

  function applyTemplateConfigFromReady(j, configSource) {
    try {
      if (!j || typeof j !== "object") {
        return;
      }
      applyWidgetRuntimeConfigFromPayload(j, configSource);
      var m = j.template_mode;
      if (m === "preset" || m === "custom") {
        widgetTemplateMode = m;
      }
      var t = j.template_tone;
      if (t === "friendly" || t === "formal" || t === "sales") {
        widgetTemplateTone = t;
      }
      if (typeof j.template_custom_text === "string") {
        widgetTemplateCustomText = j.template_custom_text;
      }
      var em = j.exit_intent_template_mode;
      if (em === "preset" || em === "custom") {
        widgetExitIntentMode = em;
      }
      var et = j.exit_intent_template_tone;
      if (et === "friendly" || et === "formal" || et === "sales") {
        widgetExitIntentTone = et;
      }
      if (typeof j.exit_intent_custom_text === "string") {
        widgetExitIntentCustomText = j.exit_intent_custom_text;
      }
      if ("widget_name" in j) {
        widgetBrandName =
          typeof j.widget_name === "string" && j.widget_name.trim()
            ? j.widget_name.trim().slice(0, 120)
            : "مساعد المتجر";
      }
      if (
        "widget_primary_color" in j &&
        j.widget_primary_color != null &&
        String(j.widget_primary_color).trim()
      ) {
        widgetPrimaryColor = normalizeWidgetPrimaryHexClient(
          String(j.widget_primary_color).trim()
        );
      }
      if ("widget_style" in j) {
        var ws = j.widget_style;
        widgetChromeStyle =
          ws === "modern" || ws === "minimal" || ws === "bold" ? ws : "modern";
      }
      if ("vip_cart_threshold" in j) {
        var vth = j.vip_cart_threshold;
        if (vth == null || vth === "") {
          widgetVipCartThreshold = null;
        } else {
          var vthNum = typeof vth === "number" ? vth : parseFloat(String(vth));
          widgetVipCartThreshold =
            isFinite(vthNum) && vthNum >= 1 ? Math.floor(vthNum) : null;
        }
        try {
          window.cartflowVipCartThreshold = widgetVipCartThreshold;
        } catch (eWth) {}
      }
      try {
        window.vip_threshold = Number(j.vip_cart_threshold || j.vip_threshold || 0);
        console.log("[VIP CONFIG LOADED]", {
          vip_threshold: window.vip_threshold,
        });
      } catch (eVc) {}
      syncWidgetCustomizationToWindow();
      applyWidgetCustomization();
      syncWindowCartflowVipRuntime();
      applyCartflowWidgetRecoveryGateFromConfig(j);
      scheduleVipPhoneCaptureCheck();
      maybeTryOpenBubbleForVipFromServer();
    } catch (eTpl) {
      /* ignore */
    }
  }

  function getExitIntentOpeningText() {
    try {
      if (
        widgetExitIntentMode === "custom" &&
        strTrim(widgetExitIntentCustomText) !== ""
      ) {
        return String(widgetExitIntentCustomText).replace(/\r\n/g, "\n");
      }
      var tone =
        widgetExitIntentTone in EXIT_INTENT_PRESET_BY_TONE
          ? widgetExitIntentTone
          : "friendly";
      return EXIT_INTENT_PRESET_BY_TONE[tone];
    } catch (eEi) {
      return EXIT_INTENT_PRESET_BY_TONE.friendly;
    }
  }

  function getExitDiscoveryIntroText() {
    try {
      if (
        widgetTemplateMode === "custom" &&
        strTrim(widgetTemplateCustomText) !== ""
      ) {
        return String(widgetTemplateCustomText).replace(/\r\n/g, "\n");
      }
      var tone =
        widgetTemplateTone in TONE_DISCOVERY_FIRST_LINE
          ? widgetTemplateTone
          : "friendly";
      return (
        TONE_DISCOVERY_FIRST_LINE[tone] + "\n" + DISCOVERY_HELPER_SECOND_LINE
      );
    } catch (eIntro) {
      return (
        TONE_DISCOVERY_FIRST_LINE.friendly +
        "\n" +
        DISCOVERY_HELPER_SECOND_LINE
      );
    }
  }

  /** سجلات واجهة فقط؛ لا تأثير على خوادم الاسترجاع أو التأخير. */
  function logWidgetFlow(step, reasonTag, selectedOption) {
    try {
      console.log("[WIDGET FLOW]");
      console.log("step=", step != null ? String(step) : "");
      console.log("reason_tag=", reasonTag != null ? String(reasonTag) : "");
      console.log("selected_option=", selectedOption != null ? String(selectedOption) : "");
    } catch (e) {
      /* ignore */
    }
  }

  /** مسار تحويل داخل الودجت (عرض فقط). */
  function logWidgetConversionFlow(reasonTag, selectedOption) {
    try {
      var so = selectedOption != null ? String(selectedOption) : "";
      console.log(
        "[WIDGET CONVERSION FLOW] reason_tag=" +
          String(reasonTag != null ? reasonTag : "") +
          " selected_option=" +
          so
      );
    } catch (eConv) {
      /* ignore */
    }
  }

  /** مسار اكتشاف منتجات قبل السلة (خروج ذكي / تصفّح فقط؛ لا تأثير على الاسترجاع). */
  function logWidgetDiscoveryFlow(action) {
    try {
      console.log("[WIDGET DISCOVERY FLOW]");
      console.log(
        "event=exit_intent_pre_cart action=" +
          String(action != null ? action : "")
      );
    } catch (eDisc) {
      /* ignore */
    }
  }

  function readExitIntentPreCartDeclined() {
    try {
      return window.sessionStorage.getItem(EXIT_INTENT_PRE_CART_DECLINED_KEY) === "1";
    } catch (eRd) {
      return false;
    }
  }

  function persistExitIntentPreCartDeclined() {
    try {
      window.sessionStorage.setItem(EXIT_INTENT_PRE_CART_DECLINED_KEY, "1");
    } catch (eWr) {
      /* ignore */
    }
  }

  function clearExitIntentPreCartDeclined() {
    try {
      window.sessionStorage.removeItem(EXIT_INTENT_PRE_CART_DECLINED_KEY);
    } catch (eClrD) {
      /* ignore */
    }
  }

  function firstLineOrClip(s, maxLen) {
    var t = strTrim(s);
    if (!t) {
      return "";
    }
    var one = t.split(/\n/)[0];
    var out = strTrim(one);
    if (out.length > maxLen) {
      out = out.slice(0, maxLen - 1) + "…";
    }
    return out;
  }

  function pickField(obj, keys) {
    if (!obj || typeof obj !== "object") {
      return "";
    }
    var i;
    for (i = 0; i < keys.length; i++) {
      var v = obj[keys[i]];
      if (v != null && strTrim(v) !== "") {
        return strTrim(v);
      }
    }
    return "";
  }

  function formatPriceRiyal(line) {
    if (!line || typeof line !== "object") {
      return "";
    }
    var p = line.price;
    if (p == null || p === "") {
      return "";
    }
    if (typeof p === "number" && isFinite(p)) {
      if (p % 1 === 0) {
        return String(Math.round(p)) + " ريال";
      }
      return p.toFixed(2) + " ريال";
    }
    var t = strTrim(p);
    if (t !== "") {
      if (/[٠-٩0-9]/.test(t) && !/ريال|SAR|sr\b/i.test(t)) {
        return t + " ريال";
      }
      return t;
    }
    return "";
  }

  function getCartLineItems() {
    if (typeof window.cart === "undefined" || window.cart === null) {
      return [];
    }
    if (!Array.isArray(window.cart)) {
      return [];
    }
    return window.cart;
  }

  function buildProductContext() {
    var items = getCartLineItems();
    var line = items.length && items[0] && typeof items[0] === "object"
      ? items[0]
      : null;
    var name = "هذا المنتج";
    if (line && strTrim(line.name) !== "") {
      name = strTrim(line.name);
    }
    var desc = line ? pickField(line, DESC_KEYS) : "";
    var category = line ? pickField(line, CAT_KEYS) : "";
    var warranty = line ? pickField(line, WARR_KEYS) : "";
    var shipping = line ? pickField(line, SHIP_KEYS) : "";
    var priceLabel = line ? formatPriceRiyal(line) : "";
    var descForQuote = firstLineOrClip(desc, 140);
    var descForQuality = firstLineOrClip(desc, 220);
    var multi = items.length > 1;
    return {
      line: line,
      name: name,
      priceLabel: priceLabel,
      description: desc,
      descForQuote: descForQuote,
      descForQuality: descForQuality,
      category: category,
      warranty: warranty,
      shipping: shipping,
      hasWarranty: strTrim(warranty) !== "",
      hasShipping: strTrim(shipping) !== "",
      multi: multi,
      extraItemsNote: multi
        ? " (وفي سلتك منتجات أخرى أيضاً.)"
        : "",
    };
  }

  function getProductAwareCopy(rkey) {
    var ctx = buildProductContext();
    var n = ctx.name;
    var a1s = {
      price: "خيارات أخرى",
      quality: "تفاصيل أكثر",
      warranty: "تفاصيل الضمان",
      shipping: "تفاصيل الشحن",
      thinking: "نصيحة سريعة",
    };
    var a1 = a1s[rkey] || "تفاصيل";
    if (rkey === "price") {
      if (ctx.priceLabel) {
        if (ctx.descForQuote) {
          return {
            message:
              "سعر " +
              n +
              " هو " +
              ctx.priceLabel +
              "، ومناسب لأنه " +
              ctx.descForQuote +
              " تبي أشوف لك خيار أنسب؟" +
              ctx.extraItemsNote,
            explain: buildPriceExplain(ctx),
            a1: a1,
          };
        }
        return {
          message:
            "سعر " + n + " هو " + ctx.priceLabel + ". تبي أشوف لك خيار أنسب؟" +
            ctx.extraItemsNote,
          explain: buildPriceExplain(ctx),
          a1: a1,
        };
      }
      return {
        message:
          "أفهمك، السعر مهم. " +
          (n && n !== "هذا المنتج"
            ? "نتكلّم عن " + n + " — "
            : "") +
          "نقدر نراجع لك قيمة مقابل الاستخدام 👍 تبي تفاصيل أو التحويل؟" +
          ctx.extraItemsNote,
        explain: buildPriceExplain(ctx),
        a1: a1,
      };
    }
    if (rkey === "quality") {
      if (ctx.descForQuality) {
        return {
          message:
            n +
            " موضح في وصفه: " +
            ctx.descForQuality +
            ". هذا يساعدك تتأكد من الجودة قبل الشراء." +
            ctx.extraItemsNote,
          explain: buildQualityExplain(ctx),
          a1: a1,
        };
      }
      return {
        message:
          "نأكد لك اهتمامك بالجودة. إذا مافي وصف مفصّل داخل بيانات السلة، راجع صفحة المنتج، أو اطلب التفصيل من المتجر." +
          ctx.extraItemsNote,
        explain: buildQualityExplain(ctx),
        a1: a1,
      };
    }
    if (rkey === "warranty") {
      if (ctx.hasWarranty) {
        return {
          message:
            "حسب بيانات المنتج في السلة: " +
            firstLineOrClip(ctx.warranty, 200) +
            " 👍 تبي أوضح لك أو أحولك للمتجر؟" +
            ctx.extraItemsNote,
          explain: buildWarrantyExplain(ctx),
          a1: a1,
        };
      }
      return {
        message:
          "معلومات الضمان غير موضحة هنا، أقدر أحولك لصاحب المتجر للتأكد." +
          ctx.extraItemsNote,
        explain: buildWarrantyExplain(ctx),
        a1: a1,
      };
    }
    if (rkey === "shipping") {
      if (ctx.hasShipping) {
        return {
          message:
            "حسب بيانات المنتج: " +
            firstLineOrClip(ctx.shipping, 200) +
            " تقدر تتأكد من التفاصيل قبل إتمام الطلب أيضاً." +
            ctx.extraItemsNote,
          explain: buildShippingExplain(ctx),
          a1: a1,
        };
      }
      return {
        message:
          "مدة الشحن تختلف حسب المدينة، وتقدر تتأكد منها قبل إتمام الطلب." +
          ctx.extraItemsNote,
        explain: buildShippingExplain(ctx),
        a1: a1,
      };
    }
    if (rkey === "thinking") {
      return {
        message: buildThinkingMessage(ctx),
        explain: buildThinkingExplain(ctx),
        a1: a1,
      };
    }
    return {
      message: "شكراً لملاحظتك." + ctx.extraItemsNote,
      explain: "تقدر ترجع لاحقاً أو تتواصل مع المتجر.",
      a1: a1,
    };
  }

  function buildPriceExplain(ctx) {
    var parts = [];
    if (ctx.description) {
      parts.push("من وصف المنتج في السلة: " + firstLineOrClip(ctx.description, 300));
    }
    if (ctx.category) {
      parts.push("الفئة: " + ctx.category + ".");
    }
    if (parts.length === 0) {
      return "تقدر تطلب من صاحب المتجر توضيح سعر وعروض مخصصة حسب اختيارك.";
    }
    return parts.join(" ");
  }

  function buildQualityExplain(ctx) {
    if (ctx.description) {
      return "تفصيل أطول من الوصف: " + firstLineOrClip(ctx.description, 400);
    }
    if (ctx.category) {
      return "الفئة المسجّلة: " + ctx.category + " — راجع تفاصيل المنتج على متجرك.";
    }
    return "اقرأ تقييمات وصفحات المنتج لأنسب قرار بخصوص الجودة، أو راسل المتجر.";
  }

  function buildWarrantyExplain(ctx) {
    if (ctx.hasWarranty) {
      return "بيانات الضمان الظاهرة في سلة: " + strTrim(ctx.warranty);
    }
    return "ما في حقل ضمان مرفوع ببيانات المنتج في السلة. صاحب المتجر يوضح السياسة مباشرة.";
  }

  function buildShippingExplain(ctx) {
    if (ctx.hasShipping) {
      return "تفصيل أطول: " + firstLineOrClip(ctx.shipping, 400);
    }
    return "تفاصيل الشحن والمدد غالباً تظهر عند إدخال العنوان عند إتمام الطلب. صاحب المتجر يوضح لك حسب منطقتك إذا بغيت.";
  }

  function buildThinkingMessage(ctx) {
    if (strTrim(ctx.name) !== "هذا المنتج" || strTrim(ctx.descForQuote) !== "") {
      var t =
        "خذ وقتك. إذا محتار بشأن " + ctx.name + "، أقدر أساعدك تقارنه أو أوضح لك أهم مزاياه.";
      if (ctx.descForQuote) {
        t += " من وصفه: " + ctx.descForQuote;
      }
      return t + ctx.extraItemsNote;
    }
    return (
      "خذ وقتك. إذا بغيت توضيح بخصوص منتجك في السلة، أنا حاضر. تبي نصيحة سريعة أو التحويل؟" +
      ctx.extraItemsNote
    );
  }

  function buildThinkingExplain(ctx) {
    if (ctx.description) {
      return "لخصّينا من وصف " + ctx.name + ": " + firstLineOrClip(ctx.description, 300);
    }
    return "تقدر تكمّل لاحقاً — أو اطلب من المتجر يرشّح لك أقرب خيار لاحتياجك.";
  }

  function isSessionConverted() {
    try {
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (e) {
      return false;
    }
  }

  function isCartPage() {
    var path = (window.location.pathname || "");
    var p = path + (window.location.search || "");
    if (/\/cart/i.test(p)) {
      return true;
    }
    if (/\/checkout/i.test(p)) {
      return true;
    }
    if (path === "/demo/store" || path.indexOf("/demo/store/") === 0) {
      return true;
    }
    return false;
  }

  function getScrollYForExit() {
    if (typeof window.pageYOffset === "number") {
      return window.pageYOffset;
    }
    if (document.documentElement && typeof document.documentElement.scrollTop === "number") {
      return document.documentElement.scrollTop;
    }
    if (document.body && typeof document.body.scrollTop === "number") {
      return document.body.scrollTop;
    }
    return 0;
  }

  /** صفحة المنتجات ‎/demo/store‎ فقط (ليس ‎/demo/store/cart‎). */
  function isDemoStoreProductPage() {
    var path = (window.location.pathname || "").replace(/\/+$/, "") || "/";
    return path === "/demo/store";
  }

  /**
   * بعد ‎exit_intent‎ + «نعم»: إن كانت صفحة سلّة أو دفع (أو قبلت سلة ظاهرة) نعرض أسباب التردد؛
   * وإلا نبقي مسار توصيات المنتج (‎renderExitIntentProductDiscovery‎)، مثل ‎/demo/store‎ بدون سلّة.
   */
  function shouldUseRecoveryReasonFlowAfterExitIntentYes() {
    if (haveCartForWidget()) {
      return true;
    }
    if (isDemoStoreProductPage()) {
      return false;
    }
    var pathRaw = window.location.pathname || "";
    var path = pathRaw.replace(/\/+$/, "") || "/";
    if (/\/checkout/i.test(pathRaw)) {
      return true;
    }
    if (/\/demo\/store\/cart/i.test(pathRaw)) {
      return true;
    }
    if (path.indexOf("/demo/cart") === 0) {
      return true;
    }
    if (/(?:^|\/)cart(?:\/|$)/i.test(path)) {
      return true;
    }
    try {
      if (cartflowLifecycleLastCount != null && cartflowLifecycleLastCount > 0) {
        return true;
      }
      if (
        cartflowLifecycleLastTotal != null &&
        !isNaN(cartflowLifecycleLastTotal) &&
        cartflowLifecycleLastTotal > 0
      ) {
        return true;
      }
    } catch (eLc) {}
    try {
      var hu = window.location.href || "";
      if (/#cart\b/i.test(hu)) {
        return true;
      }
    } catch (eH) {}
    return false;
  }

  function ensureMobileUxStyles() {
    if (document.getElementById("cf-widget-mobile-ux")) {
      return;
    }
    var s = document.createElement("style");
    s.id = "cf-widget-mobile-ux";
    s.textContent =
      "@keyframes cfFabPulse{0%,100%{box-shadow:0 2px 14px rgba(0,0,0,.28);}50%{box-shadow:0 6px 24px rgba(124,58,237,.5);}}@keyframes cfFabDot{0%,100%{opacity:1;transform:scale(1);}50%{opacity:.85;transform:scale(1.15);}}";
    document.head.appendChild(s);
  }

  function ensureChatBodyLayoutStyles() {
    if (document.getElementById("cf-chat-body-layout")) {
      return;
    }
    var st = document.createElement("style");
    st.id = "cf-chat-body-layout";
    st.textContent =
      ".cartflow-widget-body.chat-body,.cartflow-widget-body{position:relative;box-sizing:border-box;min-width:0;padding-bottom:60px;}" +
      "[data-cf-layer-d-return-row]{position:relative;width:100%;display:flex;justify-content:center;align-items:center;margin-top:8px;flex-shrink:0;box-sizing:border-box;z-index:2;}" +
      "[data-cf-layer-d-chat-return]{position:relative;z-index:5;max-width:100%;box-sizing:border-box;}";
    document.head.appendChild(st);
  }

  function applyBubbleLayout(el) {
    if (!el) {
      return;
    }
    if (isNarrowViewport()) {
      el.style.top = "auto";
      el.style.bottom = "max(8px, env(safe-area-inset-bottom, 0px))";
      el.style.right = "8px";
      el.style.left = "8px";
      el.style.maxWidth = "100%";
      el.style.maxHeight = "min(65vh, calc(100dvh - 16px))";
      el.style.minHeight = "0";
      el.style.width = "auto";
      el.style.display = "flex";
      el.style.flexDirection = "column";
      el.style.overflowX = "hidden";
      el.style.overflowY = "auto";
      el.style.overscrollBehavior = "contain";
      el.style.setProperty("-webkit-overflow-scrolling", "touch");
      el.style.setProperty("border-radius", "12px 12px 0 0", "");
      el.style.touchAction = "pan-y";
      if (el._cfDragY) {
        el.style.transform =
          "translate3d(0, " + String(-el._cfDragY) + "px, 0)";
      } else {
        el.style.transform = "";
      }
    } else {
      el.style.top = "auto";
      el.style.bottom = "max(12px, env(safe-area-inset-bottom, 0px))";
      el.style.right = "12px";
      el.style.left = "auto";
      el.style.maxWidth = "320px";
      el.style.maxHeight = "";
      el.style.minHeight = "";
      el.style.width = "";
      el.style.display = "";
      el.style.flexDirection = "";
      el.style.overflowX = "";
      el.style.overflowY = "visible";
      el.style.overscrollBehavior = "";
      el.style.setProperty("-webkit-overflow-scrolling", "");
      el.style.setProperty("border-radius", "12px", "");
      el.style.touchAction = "manipulation";
      el.style.transform = "";
      el._cfDragY = 0;
    }
    var c = el._cfChrome;
    if (c) {
      if (isNarrowViewport()) {
        c.style.position = "sticky";
        c.style.top = "0";
        c.style.zIndex = "4";
        c.style.flexShrink = "0";
        c.style.background = "#1e1b4b";
        c.style.margin = "0 -12px 8px -12px";
        c.style.padding = "0 12px 6px 12px";
        c.style.width = "calc(100% + 24px)";
        c.style.maxWidth = "none";
        c.style.boxShadow = "0 10px 16px -10px rgba(0,0,0,0.28)";
        c.style.alignSelf = "stretch";
      } else {
        c.style.position = "";
        c.style.top = "";
        c.style.zIndex = "";
        c.style.flexShrink = "";
        c.style.background = "";
        c.style.margin = "0 0 8px 0";
        c.style.padding = "";
        c.style.width = "100%";
        c.style.maxWidth = "";
        c.style.boxShadow = "";
        c.style.alignSelf = "";
      }
    }
  }

  function readDemoStoreWidgetArmed() {
    try {
      return window.sessionStorage.getItem(DEMO_STORE_WIDGET_ARMED_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function readDemoStoreExitIntentShown() {
    try {
      return window.sessionStorage.getItem(DEMO_STORE_EXIT_INTENT_SHOWN_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function setDemoStoreExitIntentShown() {
    try {
      window.sessionStorage.setItem(DEMO_STORE_EXIT_INTENT_SHOWN_KEY, "1");
    } catch (e) {
      /* ignore */
    }
  }

  function clearDemoStoreExitIntentShown() {
    try {
      window.sessionStorage.removeItem(DEMO_STORE_EXIT_INTENT_SHOWN_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  function readDemoStoreExitPromptResolved() {
    try {
      return window.sessionStorage.getItem(DEMO_STORE_EXIT_PROMPT_RESOLVED_KEY) === "1";
    } catch (e) {
      return false;
    }
  }

  function setDemoStoreExitPromptResolved() {
    try {
      window.sessionStorage.setItem(DEMO_STORE_EXIT_PROMPT_RESOLVED_KEY, "1");
    } catch (e) {
      /* ignore */
    }
  }

  function clearDemoStoreExitPromptResolved() {
    try {
      window.sessionStorage.removeItem(DEMO_STORE_EXIT_PROMPT_RESOLVED_KEY);
    } catch (e) {
      /* ignore */
    }
  }

  function isWidgetDomVisible() {
    return !!(
      document.querySelector("[data-cartflow-bubble]") ||
      document.querySelector("[data-cartflow-fab]")
    );
  }

  function syncCartflowExitFlags() {
    try {
      window.cartflowWidgetVisible = isWidgetDomVisible();
      window.cartflowManualClosed = isDemoStoreProductPage() && demoStoreBubbleDismissed;
    } catch (e) {
      window.cartflowWidgetVisible = false;
      window.cartflowManualClosed = false;
    }
  }

  function nudgeWidgetIdle() {
    try {
      document.documentElement.dispatchEvent(
        new MouseEvent("click", { bubbles: true, cancelable: true })
      );
    } catch (e) {
      try {
        var evn = document.createEvent("MouseEvents");
        evn.initEvent("click", true, true);
        document.documentElement.dispatchEvent(evn);
      } catch (e2) {
        /* ignore */
      }
    }
  }

  function isNarrowViewport() {
    return window.matchMedia && window.matchMedia("(max-width: 640px)").matches;
  }

  /** مطابقة كسر لوحة التحكم (‎768px‎): تأخير فقاعة ‎cart‎ على الهاتف حتى خروج/مؤقت فقط */
  function isMobileDeferCartBubbleViewport() {
    try {
      return window.matchMedia("(max-width: 767px)").matches;
    } catch (e) {
      return false;
    }
  }

  /**
   * بعد ‎add_to_cart‎ على الجوال: لا يُسمح للفقاعة بالظهور من مسار السكون قبل مرور هذا الوقت.
   * مسارات الخروج/الرجوع (‎mobileDeferredRevealOk‎ من ‎cart smart exit‎) غير مرتبطة بهذا الحاجز.
   */
  var MOBILE_POST_ADD_WIDGET_GUARD_MS = 90000;

  function mobileSecondsSinceLastAddToCartForGuard() {
    try {
      var ts = window._cartflowMobileLastAddToCartTs;
      if (typeof ts !== "number" || !isFinite(ts)) {
        return null;
      }
      return (Date.now() - ts) / 1000;
    } catch (eM) {
      return null;
    }
  }

  function logMobileWidgetDelayGuard(elapsedSec, allowed) {
    try {
      console.log("[MOBILE WIDGET DELAY GUARD]");
      console.log(
        "elapsed_seconds=" +
          (elapsedSec != null && isFinite(elapsedSec)
            ? String(Math.round(elapsedSec * 10) / 10)
            : "n/a")
      );
      console.log("allowed_to_show=" + String(allowed));
    } catch (eL) {
      /* ignore */
    }
  }

  function removeFabIfAny() {
    var existing = document.querySelector("[data-cartflow-fab]");
    if (existing && existing.parentNode) {
      existing.parentNode.removeChild(existing);
    }
  }

  function removeCartflowBubbleDom() {
    var nodes = document.querySelectorAll("[data-cartflow-bubble], [data-cartflow-fab]");
    var i;
    for (i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      if (typeof n._cfCleanup === "function") {
        try {
          n._cfCleanup();
        } catch (e) {
          /* ignore */
        }
      }
      if (n.parentNode) {
        n.parentNode.removeChild(n);
      }
    }
  }

  function detachArmListeners() {
    if (!armListenersAttached) {
      return;
    }
    armListenersAttached = false;
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });
  }

  function attachArmListenersOnce() {
    if (armListenersAttached) {
      return;
    }
    armListenersAttached = true;
    events.forEach(function (e) {
      document.addEventListener(e, resetIdle, true);
    });
  }

  function setCartflowWidgetShownFlag(on) {
    var bit = !!on;
    try {
      window._cartflowWidgetShown = bit;
      window.CartFlowState.widgetShown = bit;
    } catch (e) {
      /* ignore */
    }
  }

  /** سطح المكتب يبقى على ‎640px‎؛ الإشارات اللمسية تشمل أجهزة عريضة اللمس. */
  function isMobileSmartExitSignals() {
    if (isNarrowViewport()) {
      return true;
    }
    try {
      if (typeof navigator !== "undefined" && navigator.maxTouchPoints > 0) {
        return true;
      }
    } catch (e) {
      /* ignore */
    }
    return false;
  }

  function isMobileSmartExitClient() {
    return isMobileSmartExitSignals();
  }

  function getScrollYCartSmartExit() {
    try {
      var vv = window.visualViewport;
      if (vv && typeof vv.pageTop === "number") {
        return vv.pageTop;
      }
    } catch (eVv) {
      /* ignore */
    }
    return getScrollYForExit();
  }

  function logMobileExitIntentIfApplicable(exitSignalType) {
    var map = {
      "mobile-back": "back",
      visibility: "visibility",
      inactivity: "inactivity",
      scroll: "scroll-up",
    };
    var lt = map[exitSignalType];
    if (!lt || !isMobileSmartExitClient()) {
      return;
    }
    try {
      console.log("[MOBILE EXIT INTENT]");
      console.log("type=" + lt);
      console.log("has_cart=" + (haveCartForWidget() ? "1" : "0"));
      var ws = false;
      try {
        ws = !!window._cartflowWidgetShown;
      } catch (eWs) {
        /* ignore */
      }
      console.log("widget_shown=" + (ws ? "1" : "0"));
    } catch (eLog) {
      /* ignore */
    }
  }

  function resetCartSmartExitInactivityTimer() {
    if (!isMobileSmartExitSignals()) {
      return;
    }
    if (cartSmartExitInactivityTimer) {
      clearTimeout(cartSmartExitInactivityTimer);
      cartSmartExitInactivityTimer = null;
    }
    cartSmartExitInactivityTimer = setTimeout(function () {
      cartSmartExitInactivityTimer = null;
      fireCartSmartExitFromIntent("inactivity");
    }, 27000);
  }

  function onCartSmartExitScrollProbe() {
    if (!isMobileSmartExitSignals()) {
      return;
    }
    resetCartSmartExitInactivityTimer();
    var y = getScrollYCartSmartExit();
    if (cartSmartExitScrollLastY - y > 80 && y < 280) {
      fireCartSmartExitFromIntent("scroll");
    }
    cartSmartExitScrollLastY = y;
  }

  function onCartSmartExitMouseMove(ev) {
    if (isNarrowViewport()) {
      return;
    }
    if (typeof ev.clientY !== "number") {
      return;
    }
    var y = ev.clientY;
    if (
      cartSmartExitLastMouseY !== null &&
      cartSmartExitLastMouseY > 75 &&
      y <= 56 &&
      cartSmartExitLastMouseY - y >= 6
    ) {
      fireCartSmartExitFromIntent("desktop");
    }
    cartSmartExitLastMouseY = y;
  }

  function onCartSmartExitPopstate() {
    fireCartSmartExitFromIntent("mobile-back");
  }

  function onCartSmartExitVisibility() {
    if (document.visibilityState === "hidden") {
      fireCartSmartExitFromIntent("visibility");
    }
  }

  function fireCartSmartExitFromIntent(exitSignalType, deferDepth) {
    deferDepth = deferDepth || 0;
    if (deferDepth > 10) {
      return;
    }
    var now = Date.now();
    if (now - cartSmartExitLastFireTs < 900) {
      return;
    }
    if (!isCartPage()) {
      return;
    }
    try {
      if (!getCfWidgetTrigger().exit_intent_enabled) {
        cfLogWidgetTriggerBlocked("exit_intent_disabled", "cart_smart_exit");
        return;
      }
      if (!cfPageScopeAllowsCartUi()) {
        cfLogWidgetTriggerBlocked("page_scope_blocked", "cart_smart_exit");
        return;
      }
    } catch (eEx) {
      /* ignore */
    }
    if (!haveCartForWidget() || isSessionConverted()) {
      return;
    }
    if (!step1Ready && !isDemoPath()) {
      fetchReadyThen(function () {
        fireCartSmartExitFromIntent(exitSignalType, deferDepth + 1);
      });
      return;
    }
    if (isDemoStoreProductPage()) {
      if (!readDemoStoreWidgetArmed()) {
        return;
      }
      if (demoStoreBubbleDismissed) {
        return;
      }
    }
    syncCartflowExitFlags();
    if (shown) {
      return;
    }
    try {
      if (window._cartflowWidgetShown) {
        return;
      }
    } catch (eW) {
      /* ignore */
    }
    if (isWidgetDomVisible()) {
      return;
    }
    try {
      syncCartState("abandon");
    } catch (eAbandonSync) {}
    cartSmartExitLastFireTs = now;
    try {
      logMobileExitIntentIfApplicable(exitSignalType);
      if (exitSignalType === "desktop") {
        console.log("[EXIT INTENT TRIGGER]");
        console.log("type=desktop");
      }
    } catch (eLog) {
      /* ignore */
    }
    clearTimeout(idleTimer);
    idleTimer = null;
    showBubble(TRIGGER_SOURCE_CART, {
      mobileCartReveal: true,
      mobileDeferredRevealOk: true,
    });
  }

  function maybeAttachCartSmartExitIntent() {
    if (cartSmartExitAttached) {
      return;
    }
    if (!isCartPage()) {
      return;
    }
    try {
      if (!getCfWidgetTrigger().exit_intent_enabled) {
        return;
      }
      if (!cfPageScopeAllowsCartUi()) {
        return;
      }
    } catch (eMa) {
      /* ignore */
    }
    if (!haveCartForWidget()) {
      return;
    }
    if (isSessionConverted()) {
      return;
    }
    cartSmartExitAttached = true;
    cartSmartExitScrollLastY = getScrollYCartSmartExit();
    cartSmartExitLastMouseY = null;
    document.addEventListener(
      "mousemove",
      onCartSmartExitMouseMove,
      { passive: true, capture: true }
    );
    window.addEventListener("popstate", onCartSmartExitPopstate, true);
    window.addEventListener(
      "scroll",
      onCartSmartExitScrollProbe,
      { passive: true, capture: true }
    );
    document.addEventListener(
      "scroll",
      onCartSmartExitScrollProbe,
      { passive: true, capture: true }
    );
    try {
      if (window.visualViewport) {
        window.visualViewport.addEventListener(
          "scroll",
          onCartSmartExitScrollProbe,
          { passive: true }
        );
      }
    } catch (eVVa) {
      /* ignore */
    }
    document.addEventListener("visibilitychange", onCartSmartExitVisibility, true);
    ["touchstart", "touchmove", "keydown", "pointerdown"].forEach(function (evName) {
      document.addEventListener(
        evName,
        resetCartSmartExitInactivityTimer,
        { passive: true, capture: true }
      );
    });
    resetCartSmartExitInactivityTimer();
  }

  function scheduleCartSmartExitPollUntilCart() {
    if (cartSmartExitPollInterval !== null || cartSmartExitAttached) {
      return;
    }
    cartSmartExitPollInterval = setInterval(function () {
      if (!isCartPage() || isSessionConverted()) {
        clearInterval(cartSmartExitPollInterval);
        cartSmartExitPollInterval = null;
        return;
      }
      if (haveCartForWidget()) {
        maybeAttachCartSmartExitIntent();
        clearInterval(cartSmartExitPollInterval);
        cartSmartExitPollInterval = null;
      }
    }, 2500);
  }

  function runArmBody() {
    if (isSessionConverted() || !isCartPage()) {
      return;
    }
    if (haveCartForWidget()) {
      clearStaleRecoveryGatesOnCartActivity();
    }
    if (isDemoStoreProductPage() && !readDemoStoreWidgetArmed()) {
      if (isDemoPath() && haveCartForWidget()) {
        try {
          window.sessionStorage.setItem(DEMO_STORE_WIDGET_ARMED_KEY, "1");
        } catch (e) {
          /* ignore */
        }
        demoStoreBubbleDismissed = false;
        try {
          console.log("widget armed (auto, cart)");
        } catch (e) {
          /* ignore */
        }
      } else {
        return;
      }
    }
    if (isDemoPath()) {
      step1Ready = true;
    }
    attachArmListenersOnce();
    ensureStep1ThenStartIdle();
    prefetchDashboardPrimaryReason();
    prefetchConfigRecoveryDelay();
    if (haveCartForWidget()) {
      maybeAttachCartSmartExitIntent();
    } else if (isCartPage()) {
      scheduleCartSmartExitPollUntilCart();
    }
  }

  function getStoreSlug() {
    if (
      typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
      window.CARTFLOW_STORE_SLUG !== null &&
      String(window.CARTFLOW_STORE_SLUG).trim() !== ""
    ) {
      return String(window.CARTFLOW_STORE_SLUG).trim();
    }
    return "demo";
  }

  function getSessionId() {
    if (typeof window.cartflowGetSessionId === "function") {
      return window.cartflowGetSessionId();
    }
    return "—";
  }

  function setReasonSubTag(sub) {
    try {
      if (sub) {
        window.sessionStorage.setItem(REASON_SUB_TAG_KEY, String(sub));
      } else {
        window.sessionStorage.removeItem(REASON_SUB_TAG_KEY);
      }
    } catch (e) {
      /* ignore */
    }
  }

  function setReasonTag(tag) {
    try {
      if (tag) {
        window.sessionStorage.setItem(REASON_TAG_KEY, String(tag));
        if (String(tag) !== "price") {
          window.sessionStorage.removeItem(REASON_SUB_TAG_KEY);
        }
      } else {
        window.sessionStorage.removeItem(REASON_TAG_KEY);
        window.sessionStorage.removeItem(REASON_SUB_TAG_KEY);
      }
    } catch (e) {
      /* ignore */
    }
  }

  if (typeof window.cartflowGetReasonTag !== "function") {
    window.cartflowGetReasonTag = function () {
      try {
        return window.sessionStorage.getItem(REASON_TAG_KEY) || null;
      } catch (e) {
        return null;
      }
    };
  }
  if (typeof window.cartflowGetReasonSubTag !== "function") {
    window.cartflowGetReasonSubTag = function () {
      try {
        return window.sessionStorage.getItem(REASON_SUB_TAG_KEY) || null;
      } catch (e) {
        return null;
      }
    };
  }

  function persistCartRecoveryReasonBackend(reasonTag, customTextOptional) {
    try {
      var b = apiBase();
      var u = b ? b + "/api/cart-recovery/reason" : "/api/cart-recovery/reason";
      var payload = {
        store_slug: getStoreSlug(),
        session_id: getSessionId(),
        reason_tag: String(reasonTag),
      };
      if (customTextOptional != null && strTrim(customTextOptional) !== "") {
        payload.custom_reason = strTrim(customTextOptional);
      }
      try {
        if (typeof window.cartflowReadCfTestCustomerPhone === "function") {
          var cfT = window.cartflowReadCfTestCustomerPhone();
          if (cfT) {
            payload.cf_test_phone = String(cfT).trim().slice(0, 100);
          }
        }
      } catch (eCf) {
        /* ignore */
      }
      fetch(u, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(function (r) {
          if (!r.ok) {
            try {
              console.warn("CART_RECOVERY_REASON_SAVE_FAILED", r.status);
            } catch (ew) {
              /* ignore */
            }
          }
          return r.json().catch(function () {
            return {};
          });
        })
        .then(function (j) {
          try {
            if (j && j.ok === true && j.user_rejected_help === true) {
              if (window.CartFlowState) {
                window.CartFlowState.userRejectedHelp = true;
                window.CartFlowState.rejectionTimestamp = Date.now();
              }
              console.log("[USER REJECTED HELP]");
              if (typeof window.cartflowLogCartflowState === "function") {
                window.cartflowLogCartflowState();
              }
            }
            if (j && j.ok === true) {
              try {
                window.localStorage.setItem(
                  "cartflow_recovery_engagement_v1",
                  new Date().toISOString()
                );
              } catch (eEngLs) {
                /* ignore */
              }
              if (typeof window.cartflowRefreshDurableRecoveryContext === "function") {
                try {
                  var subRt =
                    typeof window.cartflowGetReasonSubTag === "function"
                      ? window.cartflowGetReasonSubTag()
                      : null;
                  window.cartflowRefreshDurableRecoveryContext({
                    reason_tag: String(reasonTag),
                    reason_sub_tag: subRt,
                    last_activity: new Date().toISOString(),
                  });
                } catch (eRc) {
                  /* ignore */
                }
              }
            }
          } catch (eSyncUrh) {
            /* ignore */
          }
          return j;
        })
        .catch(function (err) {
          try {
            console.warn("CART_RECOVERY_REASON_SAVE_FAILED", err);
          } catch (ec) {
            /* ignore */
          }
        });
    } catch (ex) {
      try {
        console.warn("CART_RECOVERY_REASON_SAVE_FAILED", ex);
      } catch (ez) {
        /* ignore */
      }
    }
  }

  function persistSessionAbandonReason(reasonTag, customTextOptional) {
    try {
      window.sessionStorage.setItem(
        SESSION_ABANDON_REASON_TAG_KEY,
        String(reasonTag)
      );
      if (customTextOptional != null && strTrim(customTextOptional) !== "") {
        window.sessionStorage.setItem(
          SESSION_ABANDON_CUSTOM_REASON_KEY,
          strTrim(customTextOptional)
        );
      } else if (String(reasonTag) !== "other") {
        try {
          window.sessionStorage.removeItem(SESSION_ABANDON_CUSTOM_REASON_KEY);
        } catch (eRm) {
          /* ignore */
        }
      }
    } catch (e) {
      /* ignore */
    }
    try {
      console.log("ABANDONMENT REASON:", String(reasonTag));
    } catch (eLog) {
      /* ignore */
    }
    persistCartRecoveryReasonBackend(reasonTag, customTextOptional);
  }

  function clearCartRecoverySuppressed() {
    try {
      window.sessionStorage.removeItem("cartflow_suppress_cart_recovery");
    } catch (e) {
      /* ignore */
    }
  }

  /**
   * مسح حالة رفض/قمع خروج النافذة عند امتلاك سلة فعّالة (انتقال من لا سلة → سلة).
   * silent=true: بدون سجل (مثلاً عند arm على صفحة السلة حيث قد يُستدعى مع كل تحميل).
   */
  function clearExitIntentGatesForActiveCart(silent) {
    clearExitIntentPreCartDeclined();
    clearDemoStoreExitIntentShown();
    clearDemoStoreExitPromptResolved();
    clearCartRecoverySuppressed();
    if (isDemoPath()) {
      demoStoreBubbleDismissed = false;
    }
    try {
      if (window.CartFlowState) {
        window.CartFlowState.userRejectedHelp = false;
        window.CartFlowState.rejectionTimestamp = null;
      }
    } catch (eCf) {
      /* ignore */
    }
    try {
      shown = false;
    } catch (eSh) {
      /* ignore */
    }
    try {
      setCartflowWidgetShownFlag(false);
    } catch (eFl) {
      /* ignore */
    }
    try {
      syncCartflowExitFlags();
    } catch (eEx) {
      /* ignore */
    }
    if (!silent) {
      try {
        console.log("[CARTFLOW RECOVERY] gates cleared on cart arm");
      } catch (eL) {
        /* ignore */
      }
    }
    scheduleResetIdleAfterGateClear();
  }

  function cartflowSyncHasCartFromCart() {
    try {
      window.CartFlowState.hasCart = haveCartForWidget();
    } catch (eSyn) {
      /* ignore */
    }
  }

  function cartflowSyncWidgetShownForState() {
    try {
      var domBubble = !!document.querySelector("[data-cartflow-bubble]");
      var domFab = !!document.querySelector("[data-cartflow-fab]");
      window.CartFlowState.widgetShown = domBubble || domFab;
    } catch (eWs) {
      /* ignore */
    }
  }

  function cartflowLogCartflowState() {
    var s = window.CartFlowState;
    if (!s) {
      return;
    }
    try {
      console.log("[CARTFLOW STATE]");
      console.log("hasCart=" + s.hasCart);
      console.log("widgetShown=" + s.widgetShown);
      console.log("userRejectedHelp=" + s.userRejectedHelp);
      console.log(
        "lastIntentAt=" +
          (s.lastIntentAt != null ? String(s.lastIntentAt) : "")
      );
    } catch (eLc) {
      /* ignore */
    }
  }

  try {
    window.cartflowLogCartflowState = cartflowLogCartflowState;
  } catch (eExLog) {
    /* ignore */
  }

  function cartflowCanShowWidget(triggerSource) {
    var ts =
      triggerSource === TRIGGER_SOURCE_EXIT_INTENT
        ? TRIGGER_SOURCE_EXIT_INTENT
        : TRIGGER_SOURCE_CART;
    cartflowSyncHasCartFromCart();
    cartflowSyncWidgetShownForState();
    cartflowLogCartflowState();
    var s = window.CartFlowState;
    if (!s) {
      return false;
    }
    if (s.widgetShown) {
      return false;
    }
    if (ts === TRIGGER_SOURCE_CART && s.userRejectedHelp === true) {
      try {
        console.log("[BLOCK INITIAL MESSAGE - USER REJECTED]");
      } catch (eBlk) {
        /* ignore */
      }
      var rt = s.rejectionTimestamp;
      if (typeof rt === "number" && Date.now() - rt < 30000) {
        try {
          console.log("[CF FRONT] skip showBubble: rejection cooldown");
        } catch (eCd) {
          /* ignore */
        }
      }
      return false;
    }
    if (ts === TRIGGER_SOURCE_CART) {
      return s.hasCart === true;
    }
    return s.hasCart !== true;
  }

  function cartflowRegisterNewIntent(kind) {
    var st = window.CartFlowState;
    if (!st || kind !== "add_to_cart") {
      return;
    }
    st.hasCart = true;
    st.lastIntentAt = Date.now();
    if (st.userRejectedHelp === true) {
      st.userRejectedHelp = false;
      st.rejectionTimestamp = null;
      console.log("[BEHAVIOR RESET] reason=add_to_cart");
    }
    cartflowSyncHasCartFromCart();
    cartflowLogCartflowState();
    try {
      if (kind === "add_to_cart" && isMobileDeferCartBubbleViewport()) {
        try {
          window._cartflowMobileLastAddToCartTs = Date.now();
        } catch (eTsMob) {
          /* ignore */
        }
        console.log("[ADD TO CART MONITORING STARTED]");
        console.log("device=mobile");
        console.log("show_widget=false");
      }
    } catch (eMon) {
      /* ignore */
    }
    try {
      syncCartState("add");
    } catch (eSyn) {}
    try {
      logCartflowRecoveryGateCheck();
    } catch (eGk) {
      /* ignore */
    }
    try {
      cfScheduleHesitationAfterCartIntent("add_to_cart");
    } catch (eHesSch) {
      /* ignore */
    }
  }

  try {
    window.cartflowRegisterNewIntent = cartflowRegisterNewIntent;
  } catch (eReg) {
    /* ignore */
  }

  function cartflowRejectHelp() {
    var st = window.CartFlowState;
    if (!st) {
      return;
    }
    st.userRejectedHelp = true;
    st.rejectionTimestamp = Date.now();
    console.log("[USER REJECTED HELP]");
    cartflowLogCartflowState();
    if (typeof window._cartflowApplyNoHelpUi === "function") {
      window._cartflowApplyNoHelpUi();
    }
  }

  try {
    window.cartflowRejectHelp = cartflowRejectHelp;
  } catch (eRj) {
    /* ignore */
  }

  function computeCartHesitationBlockReason() {
    if (!cfWgEnabled) {
      return "merchant_widget_disabled";
    }
    if (Date.now() < cfWgPromptNotBefore) {
      return "widget_prompt_delay";
    }
    if (isSessionConverted()) {
      return "session_converted";
    }
    if (!step1Ready) {
      return "step1_not_ready";
    }
    var hasItems = false;
    try {
      var c = window.cart;
      if (!Array.isArray(c)) {
        c = [];
      }
      hasItems = cartLifecycleSumCart(c) > 0;
    } catch (eCart) {
      return "cart_read_error";
    }
    if (!hasItems) {
      return "no_cart_items";
    }
    try {
      var trb = getCfWidgetTrigger();
      if (trb.suppress_when_checkout_started && cfCheckoutPathActive()) {
        return "checkout_started";
      }
      if (trb.suppress_after_widget_dismiss && cfReadDismissSuppressFlag()) {
        return "closed_recently";
      }
      if (!cfPageScopeAllowsCartUi()) {
        return "page_scope_blocked";
      }
    } catch (eBlk) {
      /* ignore */
    }
    if (
      isMobileDeferCartBubbleViewport()
    ) {
      return "mobile_cart_ui_deferred";
    }
    if (isDemoStoreProductPage()) {
      if (!readDemoStoreWidgetArmed()) {
        return "demo_widget_not_armed";
      }
      if (demoStoreBubbleDismissed) {
        return "demo_bubble_dismissed";
      }
    }
    try {
      cartflowSyncWidgetShownForState();
    } catch (eW) {
      /* ignore */
    }
    var s = window.CartFlowState;
    if (s && s.widgetShown) {
      return "widget_shown_flag";
    }
    if (s && s.userRejectedHelp === true) {
      return "user_rejected_help";
    }
    try {
      if (shown) {
        return "internal_shown_flag";
      }
    } catch (eSn) {
      /* ignore */
    }
    return null;
  }

  function computeRuntimeHesitationAnchorBlockReason() {
    var b = computeCartHesitationBlockReason();
    if (b === "mobile_cart_ui_deferred") {
      return null;
    }
    return b;
  }

  try {
    CartFlowRuntimeController.config = cfRuntimeConfig;
    CartFlowRuntimeController.trigger = cfRuntimeTrigger;
    CartFlowRuntimeController.hasValidPhone = cfHasValidStoredPhone;
    CartFlowRuntimeController.computeAnchorBlock = computeRuntimeHesitationAnchorBlockReason;
    window.CartFlowRuntimeController = CartFlowRuntimeController;
  } catch (eCrcGlue) {}

  function logCartflowRecoveryGateCheck() {
    var cartHasItems = false;
    try {
      var ca = window.cart;
      if (!Array.isArray(ca)) {
        ca = [];
      }
      cartHasItems = cartLifecycleSumCart(ca) > 0;
    } catch (eHc) {
      cartHasItems = false;
    }
    var dismissalParts = [];
    try {
      dismissalParts.push(
        "pre_cart_declined=" + (readExitIntentPreCartDeclined() ? "1" : "0")
      );
      dismissalParts.push(
        "demo_exit_shown=" + (readDemoStoreExitIntentShown() ? "1" : "0")
      );
      dismissalParts.push(
        "demo_prompt_resolved=" +
          (readDemoStoreExitPromptResolved() ? "1" : "0")
      );
    } catch (eD) {
      dismissalParts.push("read_error");
    }
    var dismissal_state = dismissalParts.join("|");
    var st = window.CartFlowState;
    var rejection_state =
      st != null
        ? "userRejectedHelp=" +
          String(!!st.userRejectedHelp) +
          " ts=" +
          String(st.rejectionTimestamp != null ? st.rejectionTimestamp : "")
        : "n/a";
    var exit_suppression = "";
    try {
      exit_suppression =
        window.sessionStorage.getItem("cartflow_suppress_cart_recovery") || "";
    } catch (eSs) {
      exit_suppression = "(read_error)";
    }
    var user_rejected_help =
      st != null ? String(!!st.userRejectedHelp) : "";
    try {
      syncCartflowExitFlags();
    } catch (eSf) {
      /* ignore */
    }
    var widget_closed =
      "demoBubbleDismissed=" +
      String(!!demoStoreBubbleDismissed) +
      " manualClosed=" +
      String(!!window.cartflowManualClosed);
    var reason_blocked = computeCartHesitationBlockReason();
    try {
      console.log(
        "[CARTFLOW RECOVERY GATE CHECK]\n" +
          "cart_has_items=" +
          cartHasItems +
          "\ndismissal_state=" +
          dismissal_state +
          "\nrejection_state=" +
          rejection_state +
          "\nexit_suppression=" +
          (exit_suppression || "(empty)") +
          "\nuser_rejected_help=" +
          user_rejected_help +
          "\nwidget_closed=" +
          widget_closed +
          "\nreason_blocked=" +
          (reason_blocked != null ? reason_blocked : "(none)")
      );
    } catch (eLg) {
      /* ignore */
    }
  }

  function scheduleResetIdleAfterGateClear() {
    try {
      setTimeout(function () {
        try {
          if (haveCartForWidget() && step1Ready && !isSessionConverted()) {
            resetIdle();
          }
        } catch (eRi) {
          /* ignore */
        }
      }, 0);
    } catch (eSt) {
      /* ignore */
    }
  }

  /** جاهزية الاسترجاع بعد إضافة للسلة أو جلسة جديدة (لا يعطّل المحادثة نهائياً) */
  function clearStaleRecoveryGatesOnCartActivity() {
    clearExitIntentGatesForActiveCart(true);
  }

  var cartflowLastCartStateFixedSig = "";
  var cartflowExitResetInitialized = false;
  var cartflowPrevHadCartForExitReset = false;

  /** hasCart وحيد وفق مجموع السلة ‎cartLifecycleSumCart‎ (نفس حقول ‎cart_state_sync‎). */
  function cartflowAnnounceUnifiedCartState(cart_total) {
    var t =
      typeof cart_total === "number" && !isNaN(cart_total)
        ? cart_total
        : 0;
    var hasCartNow = t > 0;

    if (!hasCartNow) {
      try {
        cfClearHesitationAnchorTimer();
      } catch (eClrA) {
        /* ignore */
      }
    }

    if (!cartflowExitResetInitialized) {
      cartflowExitResetInitialized = true;
      if (hasCartNow) {
        var blocked = false;
        try {
          blocked =
            readExitIntentPreCartDeclined() ||
            !!(
              window.CartFlowState &&
              window.CartFlowState.userRejectedHelp === true
            );
        } catch (eBl) {
          /* ignore */
        }
        try {
          if (window.sessionStorage.getItem("cartflow_suppress_cart_recovery")) {
            blocked = true;
          }
        } catch (eSs) {
          /* ignore */
        }
        try {
          if (isDemoPath() && demoStoreBubbleDismissed) {
            blocked = true;
          }
        } catch (eDm) {
          /* ignore */
        }
        if (blocked) {
          clearExitIntentGatesForActiveCart(false);
        }
      }
      cartflowPrevHadCartForExitReset = hasCartNow;
    } else {
      if (hasCartNow && !cartflowPrevHadCartForExitReset) {
        clearExitIntentGatesForActiveCart(false);
      }
      cartflowPrevHadCartForExitReset = hasCartNow;
    }

    var sig = t.toFixed(4);
    if (sig === cartflowLastCartStateFixedSig) {
      return;
    }
    cartflowLastCartStateFixedSig = sig;
    try {
      console.log("[CART STATE FIXED]", {
        hasCart: hasCartNow,
        cart_total: t,
      });
    } catch (eL) {}
  }

  function haveCartForWidget() {
    if (isSessionConverted()) {
      return false;
    }
    var cart = window.cart;
    if (!Array.isArray(cart)) {
      cart = [];
    }
    var cart_total = cartLifecycleSumCart(cart);
    cartflowAnnounceUnifiedCartState(cart_total);
    return cart_total > 0;
  }

  function apiBase() {
    return (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
  }

  function cartflowExposeVipWindowMirrors(total, opts) {
    setCartflowRuntimeState(total, widgetVipCartThreshold, !!(opts && opts.suppressReadyLog));
  }

  var cartflowLastVipRuntimeSig = "";
  function syncWindowCartflowVipRuntime() {
    try {
      var cart = window.cart;
      var currentCartTotal = cartLifecycleSumCart(Array.isArray(cart) ? cart : []);
      cartflowExposeVipWindowMirrors(currentCartTotal, { suppressReadyLog: true });
      var dbgSig =
        String(currentCartTotal) +
        "|" +
        String(window.vip_threshold) +
        "|" +
        String(window.is_vip);
      if (dbgSig !== cartflowLastVipRuntimeSig) {
        cartflowLastVipRuntimeSig = dbgSig;
        console.log("[VIP DATA]", {
          cart_total: window.cart_total,
          vip_threshold: window.vip_threshold,
          is_vip: window.is_vip,
        });
      }
    } catch (eSr) {
      /* ignore */
    }
  }

  /** مسار موحّد: ‎cart_state_sync‎ — قراءة السلة، الجلسة، و‎cart_id‎ المستقر للخلفية. */
  var CF_LIFECYCLE_CART_ID_KEY = "cartflow_cart_event_id";
  var cartflowLifecycleInstalled = false;
  var cartflowLifecyclePollIntervalId = null;
  var cartflowLifecycleVisibilityBound = false;
  var cartflowLifecycleLastSig = "";
  var cartflowLifecycleDebounce = null;
  var cartflowLifecycleLastTotal = null;
  var cartflowLifecycleLastCount = null;

  function cartLifecycleApiUrl() {
    var b = apiBase();
    return b ? b + "/api/cart-event" : "/api/cart-event";
  }

  function cartLifecycleSumCart(arr) {
    if (!arr || !Array.isArray(arr)) {
      return 0;
    }
    var sum = 0;
    var anyRow = false;
    var i;
    for (i = 0; i < arr.length; i++) {
      var row = arr[i];
      if (!row || typeof row !== "object") {
        continue;
      }
      var p =
        row.price != null ? row.price : row.unit_price != null ? row.unit_price : null;
      if (p == null) {
        p = row.amount != null ? row.amount : row.total;
      }
      if (p == null) {
        continue;
      }
      var pr = typeof p === "number" ? p : parseFloat(String(p));
      if (isNaN(pr)) {
        continue;
      }
      var qRaw =
        row.quantity != null ? row.quantity : row.qty != null ? row.qty : 1;
      var q = typeof qRaw === "number" ? qRaw : parseFloat(String(qRaw));
      if (isNaN(q) || q < 0) {
        q = 1;
      }
      sum += pr * q;
      anyRow = true;
    }
    return anyRow ? sum : 0;
  }

  function cartLifecycleStableCartId() {
    try {
      if (
        typeof window.CARTFLOW_CART_ID !== "undefined" &&
        window.CARTFLOW_CART_ID != null &&
        String(window.CARTFLOW_CART_ID).trim()
      ) {
        return String(window.CARTFLOW_CART_ID).trim().slice(0, 255);
      }
    } catch (e1) {
      /* ignore */
    }
    var existing = null;
    try {
      existing = window.sessionStorage.getItem(CF_LIFECYCLE_CART_ID_KEY);
    } catch (e2) {
      /* ignore */
    }
    if (existing && String(existing).trim()) {
      return String(existing).trim().slice(0, 255);
    }
    var nid =
      typeof window.crypto !== "undefined" && window.crypto.randomUUID
        ? "cf_cart_" + window.crypto.randomUUID()
        : "cf_cart_" + String(Date.now()) + "_" + String(Math.random());
    try {
      window.sessionStorage.setItem(CF_LIFECYCLE_CART_ID_KEY, nid);
    } catch (e3) {
      /* ignore */
    }
    return nid.slice(0, 255);
  }

  function showVipPhoneCapture() {
    try {
      hideVipPhoneCapturePanel();
    } catch (eVph) {}
  }

  try {
    window.showVipPhoneCapture = showVipPhoneCapture;
  } catch (eExVph) {}

  function syncCartState(reason) {
    var r = String(reason || "page_load").toLowerCase();
    var okReasons = { add: 1, remove: 1, clear: 1, abandon: 1, page_load: 1, checkout: 1 };
    if (!okReasons[r]) {
      r = "page_load";
    }
    var cart = window.cart;
    if (!Array.isArray(cart)) {
      cart = [];
    }
    var total = cartLifecycleSumCart(cart);
    var items_count = cart.length;
    var cart_total = total;
    var _vthRaw = widgetVipCartThreshold;
    var _vthComputed = 500;
    if (_vthRaw != null && _vthRaw !== "") {
      var _vn = Number(_vthRaw);
      if (isFinite(_vn) && _vn >= 1) {
        _vthComputed = Math.floor(_vn);
      }
    }
    cartflowState.cartTotal = Number(cart_total || 0);
    cartflowState.itemsCount = Number(items_count || 0);
    cartflowState.vipThreshold = _vthComputed;
    cartflowState.isVip =
      cartflowState.itemsCount > 0 &&
      cartflowState.cartTotal >= cartflowState.vipThreshold;
    try {
      console.log("[VIP STATE UPDATED]", {
        cartTotal: cartflowState.cartTotal,
        itemsCount: cartflowState.itemsCount,
        vipThreshold: cartflowState.vipThreshold,
        isVip: cartflowState.isVip,
      });
    } catch (eVsu) {}

    if (isSessionConverted()) {
      return;
    }

    cartflowAnnounceUnifiedCartState(total);

    var sessionId = getSessionId();
    if (!sessionId || String(sessionId).trim() === "" || sessionId === "—") {
      return;
    }
    var cartId = cartLifecycleStableCartId();
    var store = getStoreSlug();
    var body = {
      event: "cart_state_sync",
      reason: r,
      store: store,
      session_id: sessionId,
      cart_id: cartId,
      cart_total: total,
      items_count: items_count,
      cart: cart,
    };
    try {
      var sig2;
      try {
        sig2 = String(cart.length) + ":" + total.toFixed(4) + ":" + JSON.stringify(cart);
      } catch (es2) {
        sig2 = String(cart.length) + ":" + String(total);
      }
      cartflowLifecycleLastSig = sig2;
      cartflowLifecycleLastTotal = total;
      cartflowLifecycleLastCount = items_count;
    } catch (eSt) {}
    try {
      console.log(
        "[WIDGET CART SYNC SENT] reason=" +
          r +
          " cart_id=" +
          cartId +
          " session_id=" +
          sessionId +
          " cart_total=" +
          total +
          " items_count=" +
          items_count
      );
    } catch (eLog) {}
    try {
      fetch(cartLifecycleApiUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
        .then(function (r) {
          return r
            .json()
            .then(function (jj) {
              return { ok: r.ok, j: jj };
            })
            .catch(function () {
              return { ok: r.ok, j: {} };
            });
        })
        .then(function (pack) {
          var jj = pack != null ? pack.j : null;
          applyCartStateSyncVipFromResponse(jj);
          scheduleVipPhoneCaptureCheck();
          maybeTryOpenBubbleForVipFromServer();
        })
        .catch(function () {
          scheduleVipPhoneCaptureCheck();
        });
    } catch (eFetch) {
      scheduleVipPhoneCaptureCheck();
    }
  }

  try {
    window.cartflowSyncCartState = syncCartState;
  } catch (eWinSync) {}

  function cartflowCaptureInitialCartLifecycleSig() {
    try {
      var cart = window.cart;
      if (!Array.isArray(cart)) {
        cartflowLifecycleLastSig = "init";
        return;
      }
      var total = cartLifecycleSumCart(cart);
      cartflowLifecycleLastSig =
        String(cart.length) + ":" + total.toFixed(4) + ":" + JSON.stringify(cart);
    } catch (eCap) {
      cartflowLifecycleLastSig = "init";
    }
  }

  function flushCartLifecycleBackendPost() {
    if (cartflowLifecycleDebounce != null) {
      clearTimeout(cartflowLifecycleDebounce);
      cartflowLifecycleDebounce = null;
    }
    if (isSessionConverted()) {
      return;
    }
    var cart = window.cart;
    if (!Array.isArray(cart)) {
      return;
    }
    var total = cartLifecycleSumCart(cart);
    var count = cart.length;
    var sig;
    try {
      sig = String(cart.length) + ":" + total.toFixed(4) + ":" + JSON.stringify(cart);
    } catch (es) {
      sig = String(cart.length) + ":" + String(total);
    }
    if (sig === cartflowLifecycleLastSig) {
      return;
    }

    var sessionId = getSessionId();
    if (!sessionId || String(sessionId).trim() === "" || sessionId === "—") {
      return;
    }

    var prevT = cartflowLifecycleLastTotal;
    var prevC = cartflowLifecycleLastCount;
    var reason = "page_load";
    if (prevT === null && prevC === null) {
      reason = count === 0 && total <= 0 ? "clear" : "page_load";
    } else if (count === 0 || total <= 0) {
      reason = "clear";
    } else if (prevT != null && total > prevT) {
      reason = "add";
    } else if (prevT != null && total < prevT) {
      reason = "remove";
    } else if (prevC != null && count < prevC) {
      reason = "remove";
    } else if (prevC != null && count > prevC) {
      reason = "add";
    } else {
      reason = "page_load";
    }

    try {
      var onCheckoutPath =
        typeof window.location !== "undefined" &&
        window.location.pathname &&
        /checkout/i.test(String(window.location.pathname));
      if (onCheckoutPath && reason === "page_load") {
        reason = "checkout";
      }
    } catch (eChPath) {
      /* ignore */
    }

    cartflowLifecycleLastSig = sig;
    syncCartState(reason);
  }

  function cartflowInstallCartLifecycleObserver() {
    if (cartflowLifecycleInstalled) {
      return;
    }
    cartflowLifecycleInstalled = true;
    cartflowCaptureInitialCartLifecycleSig();

    cfPerfDemoDevLog("[CF PERF] cart observer started");

    function tick() {
      if (isSessionConverted()) {
        return;
      }
      try {
        if (typeof document.hidden === "boolean" && document.hidden) {
          return;
        }
      } catch (eHid) {}

      try {
        var cart = window.cart;
        if (!Array.isArray(cart)) {
          return;
        }
        var total = cartLifecycleSumCart(cart);
        var sig;
        try {
          sig = String(cart.length) + ":" + total.toFixed(4) + ":" + JSON.stringify(cart);
        } catch (et) {
          sig = String(cart.length) + ":" + String(total);
        }
        if (sig === cartflowLifecycleLastSig) {
          return;
        }
        if (cartflowLifecycleDebounce != null) {
          clearTimeout(cartflowLifecycleDebounce);
        }
        cartflowLifecycleDebounce = setTimeout(function () {
          flushCartLifecycleBackendPost();
        }, 350);
      } catch (et2) {
        /* ignore */
      }
    }

    function cartflowLifecycleStopTimedPoll() {
      if (cartflowLifecyclePollIntervalId !== null) {
        window.clearInterval(cartflowLifecyclePollIntervalId);
        cartflowLifecyclePollIntervalId = null;
      }
    }

    function cartflowLifecycleStartTimedPoll() {
      if (cartflowLifecyclePollIntervalId !== null) {
        return;
      }
      cartflowLifecyclePollIntervalId = window.setInterval(tick, 2000);
    }

    function cartflowLifecycleOnVisibilityChange() {
      if (!cartflowLifecycleInstalled) {
        return;
      }
      try {
        if (document.hidden) {
          cfPerfDemoDevLog("[CF PERF] polling paused while hidden");
          cartflowLifecycleStopTimedPoll();
        } else {
          cartflowLifecycleStartTimedPoll();
          tick();
        }
      } catch (eVis) {}
    }

    cfPerfDemoDevLog("[CF PERF] cart lifecycle observer interval: 2000ms");

    if (!cartflowLifecycleVisibilityBound) {
      cartflowLifecycleVisibilityBound = true;
      document.addEventListener(
        "visibilitychange",
        cartflowLifecycleOnVisibilityChange,
        false
      );
    }

    try {
      if (document.hidden) {
        cartflowLifecycleStopTimedPoll();
      } else {
        cartflowLifecycleStartTimedPoll();
      }
    } catch (ePol0) {}

    try {
      document.addEventListener(
        "cf-demo-cart-updated",
        function () {
          setTimeout(function () {
            try {
              if (!(typeof document.hidden === "boolean" && document.hidden)) {
                tick();
              }
            } catch (eDemoH) {}
          }, 0);
        },
        false
      );
    } catch (ed) {
      /* ignore */
    }
    window.setTimeout(function () {
      try {
        if (haveCartForWidget()) {
          if (!(typeof document.hidden === "boolean" && document.hidden)) {
            syncCartState("page_load");
          }
        }
      } catch (ePl) {}
    }, 500);
  }

  function postReason(payload) {
    var url = apiBase() ? apiBase() + "/api/cartflow/reason" : "/api/cartflow/reason";
    var body = {
      store_slug: getStoreSlug(),
      session_id: getSessionId(),
      reason: payload.reason,
    };
    if (payload.custom_text != null && String(payload.custom_text) !== "") {
      body.custom_text = String(payload.custom_text);
    }
    if (payload.customer_phone != null && String(payload.customer_phone).trim() !== "") {
      body.customer_phone = String(payload.customer_phone).trim();
    }
    if (payload.sub_category != null && String(payload.sub_category) !== "") {
      body.sub_category = String(payload.sub_category);
    }
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) {
          return { ok: false, status: r.status, body: j };
        }
        return j;
      });
    });
  }

  /** يعتبر الطلب ناجحاً إذا لم يُرجع الخادم ‎ok: false‎ أو ‎error‎ صريحة. */
  function cfCartflowReasonPostOk(j) {
    if (!j || typeof j !== "object") {
      return false;
    }
    if (j.ok === true) {
      return true;
    }
    if (j.ok === false || j.error) {
      return false;
    }
    return true;
  }

  var CARTFLOW_LS_CUSTOMER_PHONE = "cartflow_customer_phone";

  function normalizeSaPhoneForCartflow(s) {
    var d = String(s || "").replace(/\D/g, "");
    if (d.length === 10 && d.slice(0, 2) === "05") {
      d = "966" + d.slice(1);
    } else if (d.length === 9 && d.charAt(0) === "5") {
      d = "966" + d;
    }
    return /^9665\d{8}$/.test(d) ? d : "";
  }

  function vipPhoneCaptureEligibilityTotalsOk() {
    try {
      var cart = window.cart;
      if (!Array.isArray(cart)) {
        return false;
      }
      var total = cartLifecycleSumCart(cart);
      if (widgetVipCartThreshold == null) {
        return false;
      }
      var th = Number(widgetVipCartThreshold);
      if (!isFinite(th) || th < 1) {
        return false;
      }
      var tnum =
        typeof total === "number" ? total : parseFloat(String(total));
      if (isNaN(tnum)) {
        return false;
      }
      return cart.length > 0 && tnum >= th;
    } catch (ev) {
      return false;
    }
  }

  function getCartflowStoredCustomerPhoneNorm() {
    try {
      return normalizeSaPhoneForCartflow(
        window.localStorage.getItem(CARTFLOW_LS_CUSTOMER_PHONE)
      );
    } catch (eLs) {
      return "";
    }
  }

  function isVipPhoneCaptureDismissedThisSession() {
    try {
      return (
        window.sessionStorage.getItem(CF_SS_VIP_PHONE_DISMISS) === "1"
      );
    } catch (eSs) {
      return false;
    }
  }

  function dismissVipPhoneCaptureForSession() {
    try {
      window.sessionStorage.setItem(CF_SS_VIP_PHONE_DISMISS, "1");
    } catch (eD) {
      /* ignore */
    }
    vipPhoneCaptureShowingSuccess = false;
  }

  function vipPhoneCaptureInteractiveEligible() {
    if (typeof isSessionConverted === "function" && isSessionConverted()) {
      return false;
    }
    var sid = getSessionId();
    if (!sid || String(sid).trim() === "" || sid === "—") {
      return false;
    }
    if (!vipPhoneCaptureEligibilityTotalsOk()) {
      return false;
    }
    if (getCartflowStoredCustomerPhoneNorm()) {
      return false;
    }
    if (isVipPhoneCaptureDismissedThisSession()) {
      return false;
    }
    return true;
  }

  function vipPhoneCaptureShouldKeepPanelOpen() {
    var sid = getSessionId();
    if (!sid || String(sid).trim() === "" || sid === "—") {
      return false;
    }
    if (typeof isSessionConverted === "function" && isSessionConverted()) {
      return false;
    }
    if (!vipPhoneCaptureEligibilityTotalsOk()) {
      return false;
    }
    if (vipPhoneCaptureShowingSuccess) {
      return true;
    }
    return vipPhoneCaptureInteractiveEligible();
  }

  function hideVipPhoneCapturePanel() {
    if (vipPhoneCapturePanel && vipPhoneCapturePanel.style) {
      vipPhoneCapturePanel.style.display = "none";
    }
  }

  /**
   * حقل جمع الرقم لمتابعة سلّة VIP — يُستخدَم باللوحة المنفصلة وبفقاعة الودجت (بدون ازدواج المنطق).
   */
  function vipPhoneCaptureRenderFormIntoContainer(inner) {
    if (!inner) {
      return;
    }
    vipPhoneCaptureShowingSuccess = false;
    var btnStyle = getWidgetPrimaryButtonStyle();
    inner.innerHTML =
      "<div style=\"font-weight:700;font-size:16px;margin-bottom:6px;color:#17202a;\">خلنا نساعدك تكمل الطلب 👍</div>" +
      "<div style=\"font-size:13px;color:#3d4f5f;margin-bottom:10px;\">اكتب رقمك عشان نساعدك تكمل الطلب عبر واتساب</div>" +
      "<input type=\"tel\" inputmode=\"numeric\" maxlength=\"17\" autocomplete=\"tel\" placeholder=\"05XXXXXXXX\" data-vip-phone-input " +
      "style=\"width:100%!important;box-sizing:border-box!important;border:1px solid #cdd5dc!important;border-radius:8px!important;" +
      "padding:11px 12px!important;font:inherit!important;margin-bottom:10px!important;direction:ltr;text-align:start;letter-spacing:.02em;\"/>" +
      "<div data-vip-phone-error style=\"display:none;font-size:12px;color:#e74c3c;margin:-4px 0 8px 0;\"></div>" +
      "<button type=\"button\" data-vip-phone-submit data-cf-widget-primary-btn=\"1\" style=\"" +
      btnStyle +
      ";width:100%!important;text-align:center!important;\">حفظ الرقم</button>";
    var btn = inner.querySelector("[data-vip-phone-submit]");
    var inp = inner.querySelector("[data-vip-phone-input]");
    var errEl = inner.querySelector("[data-vip-phone-error]");
    if (btn && inp && errEl && !btn.getAttribute("data-vip-bound")) {
      btn.setAttribute("data-vip-bound", "1");
      btn.addEventListener(
        "click",
        function () {
          var norm = normalizeSaPhoneForCartflow(inp.value);
          if (!norm) {
            errEl.style.display = "block";
            errEl.textContent =
              "اكتب رقم سعودي صالح (مثال 05xxxxxxxx أو 9665xxxxxxxx)";
            return;
          }
          errEl.style.display = "none";
          btn.setAttribute("disabled", "true");
          postReason({
            reason: "vip_phone_capture",
            customer_phone: norm,
            custom_text: "vip_cart_phone_capture",
          }).then(function (resp) {
            btn.removeAttribute("disabled");
            if (!(resp && resp.ok)) {
              errEl.style.display = "block";
              errEl.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
              return;
            }
            try {
              window.localStorage.setItem(CARTFLOW_LS_CUSTOMER_PHONE, norm);
            } catch (eSt) {
              /* ignore */
            }
            vipPhoneCaptureShowingSuccess = true;
            inner.innerHTML =
              "<div style=\"font-size:14px;line-height:1.6;color:#237a52;text-align:center;padding:12px 6px;\">تمام 👍 بنراجع طلبك ونرجع لك</div>";
          });
        },
        false
      );
    }
  }

  function vipPhoneCaptureRenderFormInner() {
    if (!vipPhoneCapturePanel) {
      return;
    }
    var inner = vipPhoneCapturePanel.querySelector("[data-vip-phone-inner]");
    if (!inner) {
      return;
    }
    vipPhoneCaptureRenderFormIntoContainer(inner);
  }

  /** أولويّة لتجاوز أسئلة التردد داخل الفقاعة وجمع الرقم لمتابعة سلّة VIP. */
  function vipPhoneTryMountBubbleBlock(bodyEl) {
    try {
      if (CARTFLOW_VIP_INLINE_FLOW_ONLY) {
        return false;
      }
      if (!bodyEl || !vipPhoneCaptureInteractiveEligible()) {
        return false;
      }
      var wrapV = document.createElement("div");
      wrapV.setAttribute("data-cf-vip-phone-bubble", "1");
      wrapV.style.cssText =
        "display:block;width:100%;box-sizing:border-box;margin:0 0 10px 0;";
      bodyEl.appendChild(wrapV);
      vipPhoneCaptureRenderFormIntoContainer(wrapV);
      hideVipPhoneCapturePanel();
      return true;
    } catch (eVpb) {
      return false;
    }
  }

  function ensureVipPhoneCapturePanel() {
    if (vipPhoneCapturePanel && vipPhoneCapturePanel.parentNode) {
      return vipPhoneCapturePanel;
    }
    var root = document.body || document.documentElement;
    if (!root || !document.createElement) {
      return null;
    }
    var wrap = document.createElement("div");
    wrap.setAttribute("data-cartflow-vip-phone-capture", "1");
    wrap.setAttribute("dir", "rtl");
    wrap.style.cssText =
      "display:none!important;position:fixed!important;z-index:2147483630!important;" +
      "bottom:calc(76px + env(safe-area-inset-bottom))!important;right:calc(14px + env(safe-area-inset-right))!important;" +
      "max-width:min(328px,calc(100vw - 24px))!important;box-sizing:border-box!important;" +
      "font-family:inherit!important;line-height:1.45!important;" +
      "background:#ffffff!important;color:#17202a!important;padding:14px 36px 14px 14px!important;" +
      "border-radius:12px!important;box-shadow:0 12px 32px rgba(15,27,61,0.16)!important;" +
      "border:1px solid rgba(108,124,247,0.22)!important;";
    wrap.innerHTML =
      "<button type=\"button\" data-vip-phone-dismiss " +
      "aria-label=\"إغلاق\" title=\"إغلاق\" " +
      "style=\"position:absolute!important;top:8px!important;right:10px!important;width:32px!important;height:32px!important;padding:0!important;" +
      "border:none!important;background:transparent!important;color:#8895a9!important;font-size:22px!important;line-height:1!important;" +
      "cursor:pointer!important;border-radius:8px!important;\">&times;</button>" +
      "<div data-vip-phone-inner></div>";
    root.appendChild(wrap);
    vipPhoneCapturePanel = wrap;
    vipPhoneCaptureRenderFormInner();
    var dismissBtn = wrap.querySelector("[data-vip-phone-dismiss]");
    if (dismissBtn && !dismissBtn.getAttribute("data-vip-bound")) {
      dismissBtn.setAttribute("data-vip-bound", "1");
      dismissBtn.addEventListener(
        "click",
        function () {
          dismissVipPhoneCaptureForSession();
          hideVipPhoneCapturePanel();
        },
        false
      );
    }
    return vipPhoneCapturePanel;
  }

  function syncVipPhoneCapturePanel() {
    try {
      if (CARTFLOW_VIP_INLINE_FLOW_ONLY) {
        hideVipPhoneCapturePanel();
        return;
      }
      try {
        if (
          typeof document !== "undefined" &&
          (document.querySelector("[data-cf-vip-phone-bubble]") ||
            document.querySelector("[data-cartflow-bubble][data-cf-vip-immediate-open=\"1\"]"))
        ) {
          hideVipPhoneCapturePanel();
          return;
        }
      } catch (eBubGate) {
        /* ignore */
      }
      var converted =
        typeof isSessionConverted === "function" && isSessionConverted();
      if (
        vipPhoneCaptureShowingSuccess &&
        (!vipPhoneCaptureEligibilityTotalsOk() || converted)
      ) {
        vipPhoneCaptureShowingSuccess = false;
      }
      var keep = vipPhoneCaptureShouldKeepPanelOpen();
      if (!keep) {
        hideVipPhoneCapturePanel();
        return;
      }
      var el = ensureVipPhoneCapturePanel();
      if (!el) {
        return;
      }
      if (
        !vipPhoneCaptureShowingSuccess &&
        vipPhoneCaptureInteractiveEligible() &&
        vipPhoneCapturePanel
      ) {
        var hasInput = vipPhoneCapturePanel.querySelector(
          "[data-vip-phone-input]"
        );
        if (!hasInput) {
          vipPhoneCaptureRenderFormInner();
        }
      }
      el.style.display = "block";
    } catch (eSyn) {
      /* ignore */
    }
  }

  function scheduleVipPhoneCaptureCheck() {
    try {
      if (typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(function () {
          syncVipPhoneCapturePanel();
        });
      } else {
        window.setTimeout(syncVipPhoneCapturePanel, 0);
      }
    } catch (eSch) {
      syncVipPhoneCapturePanel();
    }
  }

  function applyCartStateSyncVipFromResponse(j) {
    if (!j || typeof j !== "object" || j.ok !== true) {
      syncWindowCartflowVipRuntime();
      return;
    }
    if ("vip_cart_threshold" in j) {
      var vt = j.vip_cart_threshold;
      if (vt == null || vt === "") {
        widgetVipCartThreshold = null;
      } else {
        var vtn = typeof vt === "number" ? vt : parseFloat(String(vt));
        widgetVipCartThreshold =
          isFinite(vtn) && vtn >= 1 ? Math.floor(vtn) : null;
      }
    }
    syncWindowCartflowVipRuntime();
  }

  function vipShouldForceVipBubble() {
    return false;
  }

  function maybeTryOpenBubbleForVipFromServer() {
    try {
      if (CARTFLOW_VIP_INLINE_FLOW_ONLY) {
        return;
      }
      if (shown || isSessionConverted() || !step1Ready) {
        return;
      }
      if (!haveCartForWidget()) {
        return;
      }
      if (!vipShouldForceVipBubble()) {
        return;
      }
      if (!cartflowCanShowWidget(TRIGGER_SOURCE_CART)) {
        return;
      }
      showBubble(TRIGGER_SOURCE_CART, { vipImmediate: true });
    } catch (eOb) {
      /* ignore */
    }
  }

  function buildWhatsappGeneratePayload(rkey) {
    var ctx = buildProductContext();
    if (rkey === "auto") {
      var hrefAuto = "#";
      try {
        if (typeof window.location !== "undefined" && window.location.href) {
          hrefAuto = String(window.location.href);
        }
      } catch (e) {
        hrefAuto = "#";
      }
      var autoBody = {
        store_slug: getStoreSlug(),
        session_id: getSessionId(),
        reason: "auto",
        product_name: ctx.name || "",
        product_price: ctx.priceLabel || "",
        cart_url: hrefAuto,
      };
      try {
        var ctA = Number(cartflowState.cartTotal);
        if (typeof ctA === "number" && !isNaN(ctA) && ctA > 0) {
          autoBody.cart_total = ctA;
        }
      } catch (eCtA) {
        /* ignore */
      }
      return autoBody;
    }
    var gsub =
      rkey === "price" && typeof window.cartflowGetReasonSubTag === "function"
        ? window.cartflowGetReasonSubTag()
        : null;
    var href = "#";
    try {
      if (typeof window.location !== "undefined" && window.location.href) {
        href = String(window.location.href);
      }
    } catch (e) {
      href = "#";
    }
    var body = {
      store_slug: getStoreSlug(),
      session_id: getSessionId(),
      reason: rkey,
      product_name: ctx.name || "",
      product_price: ctx.priceLabel || "",
      cart_url: href,
    };
    if (gsub) {
      body.sub_category = String(gsub);
    }
    try {
      var ctV = Number(cartflowState.cartTotal);
      if (typeof ctV === "number" && !isNaN(ctV) && ctV > 0) {
        body.cart_total = ctV;
      }
    } catch (eCt) {
      /* ignore */
    }
    return body;
  }

  /** روابط باث واتساب — لا تعتمد على ‎payload.cart_url‎ (قيمة الـ API فقط). */
  function resolveWhatsappCartUrlString() {
    var p = (window.location.pathname || "") + (window.location.search || "");
    if (p.indexOf("/demo/") >= 0) {
      try {
        return String(window.location.origin || "").replace(/\/$/, "") + "/demo/store#cart";
      } catch (e) {
        return "https://smartreplyai.net/demo/store#cart";
      }
    }
    try {
      return String(window.location.href || "#");
    } catch (e2) {
      return "#";
    }
  }

  function resolveWhatsappProductUrlString() {
    var line = buildProductContext().line;
    var base = "";
    try {
      base =
        String(window.location.origin || "") +
        String(window.location.pathname || "").replace(/\/$/, "");
    } catch (e) {
      return resolveWhatsappCartUrlString();
    }
    if (line && line.id) {
      return base + "#" + String(line.id).replace(/^#/, "");
    }
    try {
      var h = String(window.location.href || "");
      var hash = h.indexOf("#");
      return hash >= 0 ? h.slice(0, hash) : h;
    } catch (e2) {
      return base;
    }
  }

  var _cfDashPrimaryCache = null;

  /** GET /api/recovery/primary-reason — يحدّث الكاش لمفتاح المتجر (= store_slug). */
  function fetchDashboardPrimaryReasonFromApi(storeKey) {
    var sk =
      storeKey != null && String(storeKey).replace(/\s/g, "") !== ""
        ? String(storeKey).trim()
        : getStoreSlug();
    var b = (apiBase() || "").toString().replace(/\/$/, "");
    var path =
      (b ? b + "/api/recovery/primary-reason" : "/api/recovery/primary-reason") +
      "?store_id=" +
      encodeURIComponent(sk);
    return fetch(path, { method: "GET", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        var pr =
          data && data.primary_reason
            ? String(data.primary_reason).trim()
            : "price";
        _cfDashPrimaryCache = pr;
        if (!window.__cfPrimaryByStore) {
          window.__cfPrimaryByStore = {};
        }
        window.__cfPrimaryByStore[sk] = pr;
        try {
          window._cfPrimaryReason = pr;
        } catch (e) {
          /* ignore */
        }
        return pr;
      });
  }

  function prefetchDashboardPrimaryReason() {
    fetchDashboardPrimaryReasonFromApi(getStoreSlug()).catch(function () {});
  }

  /** GET /config-check — تأخير الاسترجاع بالدقائق (طبقة الإعداد)، قراءة فقط. */
  function prefetchConfigRecoveryDelay() {
    var b = (apiBase() || "").toString().replace(/\/$/, "");
    var u = (b ? b + "/config-check" : "/config-check");
    fetch(u, { method: "GET", credentials: "same-origin" })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && typeof j.recovery_delay_minutes === "number") {
          try {
            window._cfRecoveryDelayMinutes = j.recovery_delay_minutes;
          } catch (e) {
            /* ignore */
          }
        }
        try {
          if (haveCartForWidget() && step1Ready && !shown) {
            resetIdle();
          }
        } catch (e2) {
          /* ignore */
        }
      })
      .catch(function () {});
  }

  /**
   * يطابق config_system (بعد الجلب)؛ عند ‎demo‎ وقبل اكتمال الطلب نستخدم ‎2‎ د كما في الخادم حتى لا يُجدول مؤقتاً بدقيقة واحدة.
   */
  function getRecoveryDelayMinutesForSession() {
    var rm;
    try {
      if (
        typeof window._cfRecoveryDelayMinutes === "number" &&
        isFinite(window._cfRecoveryDelayMinutes)
      ) {
        rm = window._cfRecoveryDelayMinutes;
      }
    } catch (e) {
      rm = undefined;
    }
    if (typeof rm !== "number" || !isFinite(rm) || rm < 0) {
      rm = String(getStoreSlug()).toLowerCase() === "demo" ? 2 : 1;
    }
    return rm;
  }

  function getRecoveryDelayMilliseconds() {
    return getRecoveryDelayMinutesForSession() * 60 * 1000;
  }

  /** مهلة عرض الودجيت بعد آخر نشاط سلة (لا علاقة لها بتأخير الإرسال على الخادم). */
  function getWidgetCartUiIdleMs() {
    try {
      var tr = getCfWidgetTrigger();
      if (tr && tr.hesitation_trigger_enabled === false) {
        return 86400000;
      }
      if (tr && typeof tr.hesitation_after_seconds === "number") {
        var sec = tr.hesitation_after_seconds;
        if (isFinite(sec) && sec >= 0) {
          return Math.min(Math.max(sec, 0), 600) * 1000;
        }
      }
    } catch (eHes) {
      /* ignore */
    }
    try {
      var o = window.CARTFLOW_WIDGET_UI_IDLE_MS;
      if (typeof o === "number" && isFinite(o) && o >= 0) {
        return o;
      }
    } catch (e) {
      /* ignore */
    }
    return WIDGET_CART_UI_IDLE_MS;
  }

  function cfClearHesitationAnchorTimer() {
    cfRuntimeClearHesitationTimer("anchor_compat", true);
  }

  function cfHesitationAnchorDelayMs() {
    var sec = cfRuntimeConfig(true).hesitation_delay_seconds;
    if (sec < 0) {
      sec = 0;
    }
    if (sec > 600) {
      sec = 600;
    }
    return sec * 1000;
  }

  function cfTryFireWidgetHesitationTimer(sourceLabel, expectedAtMs) {
    var firedAt = Date.now();
    var driftMs =
      typeof expectedAtMs === "number" && isFinite(expectedAtMs)
        ? firedAt - expectedAtMs
        : 0;
    var rcEarly = cfRuntimeConfig(true);
    if (!rcEarly.widget_enabled || !rcEarly.hesitation_enabled) {
      try {
        console.log("[CF TIMER BLOCKED]", {
          gate: !rcEarly.widget_enabled ? "widget_disabled" : "hesitation_disabled",
          drift_ms: Math.round(driftMs),
          source_label: sourceLabel,
        });
      } catch (eBk0) {}
      cfClearHesitationAnchorTimer();
      return;
    }
    if (
      rcEarly.hesitation_condition !== "after_cart_add" &&
      rcEarly.hesitation_condition !== "cart_interaction"
    ) {
      try {
        console.log("[CF TIMER BLOCKED]", {
          gate: "hesitation_condition_not_cart",
          condition: rcEarly.hesitation_condition,
          drift_ms: Math.round(driftMs),
        });
      } catch (eBk1) {}
      cfClearHesitationAnchorTimer();
      return;
    }
    if (!step1Ready) {
      fetchReadyThen(function () {
        cfTryFireWidgetHesitationTimer(
          String(sourceLabel || "") + "_after_ready",
          expectedAtMs
        );
      });
      return;
    }
    var blocked = computeRuntimeHesitationAnchorBlockReason();
    var eligible = !blocked;
    if (!eligible) {
      try {
        console.log("[CF TIMER BLOCKED]", {
          blocked_reason: String(blocked || ""),
          drift_ms: Math.round(driftMs),
        });
      } catch (eBk2) {}
      cfClearHesitationAnchorTimer();
      return;
    }
    try {
      console.log("[CF TIMER FIRE]", {
        source_label: sourceLabel,
        drift_ms: Math.round(driftMs),
      });
    } catch (eFire) {}
    cfRuntimeClearHesitationTimer("hesitation_fire", true);
    try {
      console.log("[CF WIDGET SHOW]", {
        trace: "hesitation_anchor_timer",
        delay_seconds: cfRuntimeConfig(true).hesitation_delay_seconds,
      });
    } catch (eSh) {}
    showBubble(TRIGGER_SOURCE_CART, {
      mobileCartReveal: true,
      mobileDeferredRevealOk: true,
    });
  }

  function cfHesitationResumeAfterVisible() {
    try {
      if (cfHesitationExpectedFireAtMs <= 0) {
        return;
      }
      var now = Date.now();
      if (now + 500 < cfHesitationExpectedFireAtMs) {
        return;
      }
      if (shown || isSessionConverted()) {
        cfClearHesitationAnchorTimer();
        return;
      }
      var expected = cfHesitationExpectedFireAtMs;
      cfRuntimeClearHesitationTimeoutOnlyNoFlags();
      cfTryFireWidgetHesitationTimer("visibility_resume", expected);
    } catch (eVis) {
      /* ignore */
    }
  }

  function cfRafPaint(cb) {
    cb = typeof cb === "function" ? cb : function () {};
    try {
      if (typeof requestAnimationFrame === "function") {
        requestAnimationFrame(function () {
          requestAnimationFrame(cb);
        });
        return;
      }
    } catch (eRaf) {
      /* ignore */
    }
    setTimeout(cb, 0);
  }

  function cfScheduleHesitationAfterCartIntent(sourceEvent) {
    var srcEv =
      sourceEvent != null && String(sourceEvent).trim() !== ""
        ? String(sourceEvent)
        : "add_to_cart";
    var rcSnap = cfRuntimeConfig(true);
    cfHesitationScheduleGen += 1;
    var gen = cfHesitationScheduleGen;
    cfRuntimeClearHesitationTimer("cart_intent_schedule_reset", false);
    if (!rcSnap.widget_enabled || !rcSnap.hesitation_enabled) {
      try {
        console.log("[CF TIMER BLOCKED]", {
          gate: !rcSnap.widget_enabled ? "widget_disabled" : "hesitation_disabled",
          source_event: srcEv,
        });
      } catch (eSb0) {}
      return;
    }
    if (
      rcSnap.hesitation_condition !== "after_cart_add" &&
      rcSnap.hesitation_condition !== "cart_interaction"
    ) {
      try {
        console.log("[CF TIMER BLOCKED]", {
          gate: "hesitation_condition_not_cart",
          condition: rcSnap.hesitation_condition,
          source_event: srcEv,
        });
      } catch (eSb1) {}
      return;
    }
    try {
      function tryArm(attempt) {
        if (gen !== cfHesitationScheduleGen) {
          return;
        }
        if (!step1Ready) {
          fetchReadyThen(function () {
            tryArm(0);
          });
          return;
        }
        if (!haveCartForWidget()) {
          if (attempt < 6) {
            setTimeout(function () {
              tryArm(attempt + 1);
            }, attempt === 0 ? 0 : Math.min(120, 20 * attempt));
          } else {
            try {
              console.log("[CF TIMER BLOCKED]", {
                gate: "no_cart_when_scheduling_window_closed",
                source_event: srcEv,
              });
            } catch (eSb2) {}
          }
          return;
        }
        var now = Date.now();
        var delayMs = cfHesitationAnchorDelayMs();
        var expectedAt = now + delayMs;
        cfHesitationScheduledAtMs = now;
        cfHesitationExpectedFireAtMs = expectedAt;
        cfRuntimeTrigger.expectedAt = expectedAt;
        cfRuntimeTrigger.source = srcEv;
        var sid = getSessionId();
        var cid = cartLifecycleStableCartId();
        try {
          console.log("[CF TIMER SCHEDULE]", {
            source_event: srcEv,
            delay_seconds: delayMs / 1000,
            scheduled_at: now,
            expected_fire_at: expectedAt,
            cart_id: cid,
            session_id: sid,
            hesitation_condition: rcSnap.hesitation_condition,
          });
        } catch (eSchLog) {
          /* ignore */
        }
        cfRuntimeTrigger.timer = setTimeout(function () {
          cfRuntimeTrigger.timer = null;
          cfHesitationAnchorTimer = null;
          if (gen !== cfHesitationScheduleGen) {
            return;
          }
          cfTryFireWidgetHesitationTimer("timeout", expectedAt);
        }, delayMs);
        cfHesitationAnchorTimer = cfRuntimeTrigger.timer;
      }
      tryArm(0);
    } catch (eSch) {
      /* ignore */
    }
  }

  try {
    if (typeof document !== "undefined" && !window.__cfHesitationVisBound) {
      window.__cfHesitationVisBound = true;
      document.addEventListener(
        "visibilitychange",
        function () {
          try {
            if (document.visibilityState === "visible") {
              cfHesitationResumeAfterVisible();
            }
          } catch (eV1) {
            /* ignore */
          }
        },
        false
      );
      if (typeof window !== "undefined") {
        window.addEventListener(
          "pageshow",
          function (ev) {
            try {
              void ev;
              cfHesitationResumeAfterVisible();
            } catch (ePs) {
              /* ignore */
            }
          },
          false
        );
      }
    }
  } catch (eBind) {
    /* ignore */
  }

  function getPrimaryRecoveryReason(storeId) {
    var sid =
      storeId != null && String(storeId).replace(/\s/g, "") !== ""
        ? String(storeId).trim()
        : getStoreSlug();
    if (window.__cfPrimaryByStore && window.__cfPrimaryByStore[sid]) {
      var v1 = String(window.__cfPrimaryByStore[sid]);
      try {
        window._cfPrimaryReason = v1;
      } catch (e) {
        /* ignore */
      }
      return v1;
    }
    if (_cfDashPrimaryCache != null && _cfDashPrimaryCache !== "") {
      var v2 = String(_cfDashPrimaryCache);
      try {
        window._cfPrimaryReason = v2;
      } catch (e) {
        /* ignore */
      }
      return v2;
    }
    return "price";
  }

  /**
   * رابط واحد نهائي حسب ‎type‎ — لا تُستخرج التسمية/الرابط من أي مكان آخر.
   */
  function getLinkByType(type) {
    var label;
    var url;
    if (type === "cart") {
      label = "🛒 رابط السلة:";
      url = resolveWhatsappCartUrlString();
    } else if (type === "alternatives") {
      label = "🔄 تصفح البدائل:";
      url = "https://smartreplyai.net/demo/store";
    } else {
      label = "📦 رابط المنتج:";
      url = resolveWhatsappProductUrlString() || resolveWhatsappCartUrlString();
    }
    return { label: label, url: url };
  }

  function getPersuasionMessage(reason) {
    if (reason === "price") {
      return (
        "واضح إن السعر مهم لك 💸\n" +
        "عشان كذا جهزنا لك خيارات قريبة من نفس المنتج بس بسعر أخف\n" +
        "تقدر تشوف البدائل المناسبة لك من هنا 👇"
      );
    }
    if (reason === "shipping") {
      return (
        "لا تشيل هم الشحن 🚚\n" +
        "التوصيل سريع ويوصل خلال أيام قليلة بإذن الله\n" +
        "وتقدر تختار الطريقة اللي تناسبك بكل سهولة 👇"
      );
    }
    if (reason === "thinking" || reason === "hesitation") {
      return (
        "🤝 خذها ببساطة\n\n" +
        "لو محتار بين الخيارات، نقدر نرشح لك الأنسب حسب استخدامك بدون تعقيد\n\n" +
        "ابدأ بالأقرب لك، ولو ما كان مناسب تقدر تغيّره بكل سهولة 👇"
      );
    }
    if (reason === "warranty") {
      return (
        "🛡️ اطمّن\n\n" +
        "المنتج عليه ضمان، وإذا ما كان مناسب لك تقدر ترجعه أو تستبدله بكل سهولة\n\n" +
        "هدفنا إنك تطلب وأنت مرتاح 100% 👇"
      );
    }
    return "موجود لك خيارات مناسبة 👌";
  }

  /**
   * مصدر واحد لنص واتساب في المعاينة — النوع + رابط واحد فقط.
   * opts: reason, sub_category (نص المعاينة من الـ API لا يُلحق هنا لتفادي التكرار)
   */
  function buildWhatsappMessage(opts) {
    var reason = (opts && opts.reason != null) ? String(opts.reason).trim() : "";
    var sub_category = (opts.sub_category || "").trim();
    var appliedDashboardFallback = false;
    // TEST MODE: force no reason
    if (window._cfForceNoReason === true) {
      console.log("FORCING NO REASON (TEST MODE)");
      reason = null;
      sub_category = null;
    }

    // Fallback from dashboard
    if (!reason || reason === "unknown") {
      if (window._cfPrimaryReason) {
        reason = window._cfPrimaryReason;
        sub_category = null; // IMPORTANT: reset old logic
        appliedDashboardFallback = true;
        console.log("PRIMARY_REASON_FROM_DASHBOARD", reason);
      }
    }
    if (!reason || reason === "auto") {
      var primaryReason = getPrimaryRecoveryReason(getStoreSlug());
      try {
        console.log("PRIMARY_REASON_FROM_DASHBOARD", primaryReason);
      } catch (e) {
        /* ignore */
      }
      reason = primaryReason;
    }
    if (reason === "price" && !sub_category && !appliedDashboardFallback) {
      sub_category = "price_discount_request";
    }
    var type = "cart";
    if (
      reason === "price" &&
      (sub_category === "price_budget_issue" ||
        sub_category === "price_cheaper_alternative")
    ) {
      type = "alternatives";
    } else if (reason === "price" && sub_category === "price_discount_request") {
      type = "cart";
    } else if (
      reason === "quality" ||
      reason === "warranty" ||
      reason === "shipping" ||
      reason === "thinking" ||
      reason === "other" ||
      reason === "human_support"
    ) {
      type = "product";
    } else if (reason === "price") {
      type = "cart";
    }
    var link = getLinkByType(type);
    try {
      Object.freeze(link);
    } catch (e) {
      /* ignore */
    }
    var persuasionText = getPersuasionMessage(reason);
    var intro = "👋 مرحباً\n\n" + persuasionText;
    var finalMessage =
      intro + "\n\n" + link.label + "\n" + link.url;
    try {
      console.log("WHATSAPP_BUILD", {
        reason: reason,
        sub_category: sub_category,
        type: type,
      });
      console.log("FINAL_LINK_USED", link);
      if (type === "alternatives" && String(link.url).indexOf("cart") >= 0) {
        console.error("WRONG LINK USED FOR ALTERNATIVES", link);
      }
    } catch (e) {
      /* ignore */
    }
    return finalMessage;
  }

  function postGenerateWhatsappMessage(payload) {
    var url = apiBase()
      ? apiBase() + "/api/cartflow/generate-whatsapp-message"
      : "/api/cartflow/generate-whatsapp-message";
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }).then(function (r) {
      return r.json().then(
        function (j) {
          return { ok: r.ok, j: j != null ? j : {} };
        },
        function () {
          return { ok: r.ok, j: {} };
        }
      );
    });
  }

  /**
   * ‎wa.me/{digits}?text=‎ عند وجود رقم متجر (‎E.164‎ بلا +) وإلا ‎wa.me/?text=‎.
   */
  function buildWaMeComposeUrl(fullText, merchantE164Raw) {
    var enc = encodeURIComponent(fullText);
    var d = merchantE164Raw && String(merchantE164Raw).replace(/\D/g, "");
    if (d) {
      return "https://wa.me/" + d + "?text=" + enc;
    }
    return "https://wa.me/?text=" + enc;
  }

  function handoffToMerchant(optionalButton) {
    if (optionalButton) {
      optionalButton.setAttribute("disabled", "true");
    }
    return postReason({ reason: "human_support" })
      .then(function (j) {
        if (!(j && j.ok)) {
          return null;
        }
        setReasonTag("human_support");
        var bb = apiBase();
        var cfgUrl =
          (bb || "") +
          "/api/cartflow/public-config" +
          "?store_slug=" +
          encodeURIComponent(getStoreSlug());
        return fetch(cfgUrl, { method: "GET" });
      })
      .then(function (resp) {
        if (!resp) {
          return;
        }
        if (!resp.ok) {
          return;
        }
        return resp.json();
      })
      .then(function (cfg) {
        applyTemplateConfigFromReady(cfg, "public_config");
        if (cfg && cfg.whatsapp_url) {
          window.open(
            cfg.whatsapp_url,
            "_blank",
            "noopener,noreferrer"
          );
        }
      })
      .catch(function () {})
      .then(function () {
        if (optionalButton) {
          optionalButton.removeAttribute("disabled");
        }
      });
  }

  function isDemoPath() {
    var p = (window.location.pathname || "") + (window.location.search || "");
    return /\/demo\//i.test(p);
  }

  function isDemoScenarioActive() {
    return (
      typeof window.cartflowDemoIsScenarioActive === "function" &&
      window.cartflowDemoIsScenarioActive()
    );
  }

  function emitDemoGuideEvent(name, detail) {
    if (!isDemoPath()) {
      return;
    }
    try {
      if (
        document.querySelector(
          "[data-cartflow-bubble][data-cf-vip-inline-blocking=\"1\"]"
        )
      ) {
        return;
      }
    } catch (eBlk) {
      /* ignore */
    }
    try {
      document.dispatchEvent(
        new CustomEvent(name, { bubbles: true, detail: detail || {} })
      );
    } catch (e) {
      /* ignore */
    }
  }

  /** جذر مع ‎public-config‎ لتمرير مجموع السلة الحالي وحساب ‎is_vip‎ بالخادم. */
  function cartTotalQuerySuffixForPublicConfig() {
    try {
      if (!haveCartForWidget()) {
        return "";
      }
      var cart = window.cart;
      if (!Array.isArray(cart)) {
        return "";
      }
      var total = cartLifecycleSumCart(cart);
      return "&cart_total=" + encodeURIComponent(String(total));
    } catch (eCtq) {
      return "";
    }
  }

  /** لوحة التجربة والعرض العام: يقرأ نفس حقول النمط + تخصيص الودجيت مع ‎GET /api/cartflow/ready‎. */
  function fetchPublicConfigForWidgetCustomization(done) {
    done = typeof done === "function" ? done : function () {};
    var bb = apiBase();
    var u =
      (bb || "") +
      "/api/cartflow/public-config" +
      "?store_slug=" +
      encodeURIComponent(getStoreSlug()) +
      cartTotalQuerySuffixForPublicConfig();
    fetch(u, { method: "GET" })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        if (j && typeof j === "object" && j.ok !== false) {
          applyTemplateConfigFromReady(j, "public_config");
        }
        if (isDemoPath()) {
          demoCustomizationLoaded = true;
        }
        done();
      })
      .catch(function () {
        if (isDemoPath()) {
          demoCustomizationLoaded = true;
        }
        done();
      });
  }

  function ensureDemoWidgetCustomizationLoaded(done) {
    done = typeof done === "function" ? done : function () {};
    if (!isDemoPath()) {
      done();
      return;
    }
    if (demoCustomizationLoaded) {
      done();
      return;
    }
    fetchPublicConfigForWidgetCustomization(done);
  }

  function fetchReadyThen(cb) {
    cb = typeof cb === "function" ? cb : function () {};
    if (isDemoPath()) {
      step1Ready = true;
      ensureDemoWidgetCustomizationLoaded(cb);
      return;
    }
    if (step1Ready) {
      cb();
      return;
    }
    var b = apiBase();
    var u =
      (b || "") +
      "/api/cartflow/ready" +
      "?store_slug=" +
      encodeURIComponent(getStoreSlug()) +
      "&session_id=" +
      encodeURIComponent(getSessionId());
    fetch(u, { method: "GET" })
      .then(function (r) {
        return r.json();
      })
      .then(function (j) {
        applyTemplateConfigFromReady(j, "ready");
        if (j && j.after_step1) {
          step1Ready = true;
          if (step1Poll !== null) {
            clearInterval(step1Poll);
            step1Poll = null;
          }
          cb();
        }
      })
      .catch(function () {});
  }

  function ensureStep1ThenStartIdle() {
    if (step1Ready) {
      resetIdle();
      return;
    }
    fetchReadyThen(function () {
      if (!shown) {
        resetIdle();
      }
    });
    if (step1Poll === null) {
      step1Poll = setInterval(function () {
        if (shown) {
          if (step1Poll !== null) {
            clearInterval(step1Poll);
            step1Poll = null;
          }
          return;
        }
        fetchReadyThen(function () {
          if (step1Ready && !shown) {
            resetIdle();
          }
        });
      }, 5000);
    }
  }

  var rowStyleCol =
    "display:flex;flex-direction:column;gap:10px;width:100%;align-items:stretch;";

  /**
   * Scroll to cart / checkout on the host page (no widget close).
   * Tries common ids/selectors; falls back to first cart-like section.
   */
  function scrollToCartOrCheckout() {
    var selectors = [
      "#cart",
      "#Cart",
      "#shopping-cart",
      "#shopify-section-cart",
      "#checkout",
      "[data-cartflow-cart]",
      "[data-cart-section]",
      "[id*='cart' i]:not([id*='cartflow' i])",
    ];
    var i;
    var el;
    for (i = 0; i < selectors.length; i++) {
      try {
        el = document.querySelector(selectors[i]);
      } catch (e) {
        el = null;
      }
      if (el && el.scrollIntoView) {
        el.scrollIntoView({ behavior: "smooth", block: "start" });
        if (el.focus) {
          try {
            el.focus({ preventScroll: true });
          } catch (e2) {
            el.focus();
          }
        }
        return;
      }
    }
    el = document.querySelector("form[action*='checkout' i], [name='checkout']");
    if (el && el.scrollIntoView) {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
  }

  function showBubble(triggerSource, revealOpts) {
    revealOpts = revealOpts || {};
    syncWindowCartflowVipRuntime();
    var openSource =
      triggerSource === TRIGGER_SOURCE_EXIT_INTENT
        ? TRIGGER_SOURCE_EXIT_INTENT
        : TRIGGER_SOURCE_CART;
    if (!cfWgEnabled) {
      try {
        console.log("[CF FRONT] skip showBubble: merchant disabled widget recovery UI");
      } catch (eWgDis) {}
      return;
    }
    if (Date.now() < cfWgPromptNotBefore) {
      try {
        console.log("[CF FRONT] skip showBubble: merchant delay not elapsed");
      } catch (eWgDly) {}
      return;
    }
    var _trPre = getCfWidgetTrigger();
    if (_trPre && _trPre.visibility_widget_globally_enabled === false) {
      cfLogWidgetTriggerBlocked("widget_disabled", "globally_off");
      return;
    }
    if (_trPre && _trPre.visibility_temporarily_disabled === true) {
      cfLogWidgetTriggerBlocked("widget_disabled", "temporarily_off");
      return;
    }
    if (isSessionConverted()) {
      cfLogWidgetTriggerBlocked("purchase_completed", "");
      return;
    }
    if (openSource === TRIGGER_SOURCE_EXIT_INTENT) {
      try {
        if (!_trPre.exit_intent_enabled) {
          cfLogWidgetTriggerBlocked("exit_intent_disabled", "show_bubble");
          return;
        }
        if (!cfExitIntentSurfaceAllowed()) {
          cfLogWidgetTriggerBlocked("page_scope_blocked", "exit_intent_surface");
          return;
        }
      } catch (eExi) {
        /* ignore */
      }
    }
    if (openSource === TRIGGER_SOURCE_CART && !cfPageScopeAllowsCartUi()) {
      cfLogWidgetTriggerBlocked("page_scope_blocked", "cart_bubble");
      return;
    }
    if (!cfFrequencyAllowsShow(openSource)) {
      cfLogWidgetTriggerBlocked("frequency_blocked", String(openSource || ""));
      return;
    }
    if (_trPre.suppress_when_checkout_started && cfCheckoutPathActive()) {
      cfLogWidgetTriggerBlocked("checkout_started", "");
      return;
    }
    try {
      window._cartflowApplyNoHelpUi = null;
    } catch (eClrNk) {
      /* ignore */
    }
    try {
      console.log("[CF FRONT] trigger detected", triggerSource);
    } catch (eCfTrig) {
      /* ignore */
    }
    var hasCartItems = haveCartForWidget();
    if (
      openSource === TRIGGER_SOURCE_CART &&
      isMobileDeferCartBubbleViewport() &&
      !revealOpts.mobileCartReveal &&
      !revealOpts.vipImmediate
    ) {
      try {
        console.log(
          "[CF FRONT] skip cart bubble on mobile (use exit/timer/deferred reveal only)"
        );
      } catch (eMobSk) {
        /* ignore */
      }
      return;
    }
    if (
      openSource === TRIGGER_SOURCE_CART &&
      isMobileDeferCartBubbleViewport() &&
      revealOpts.mobileCartReveal === true &&
      revealOpts.mobileDeferredRevealOk !== true &&
      !revealOpts.vipImmediate
    ) {
      try {
        console.log("[BLOCK IMMEDIATE WIDGET]");
        console.log("reason=mobile_add_to_cart");
      } catch (eMobBlk) {
        /* ignore */
      }
      return;
    }
    try {
      console.log("HAS CART:", hasCartItems);
    } catch (eLog) {
      /* ignore */
    }
    if (
      openSource === TRIGGER_SOURCE_EXIT_INTENT &&
      !hasCartItems &&
      readExitIntentPreCartDeclined()
    ) {
      try {
        console.log("[CF FRONT] skip showBubble exit intent: pre-cart declined");
      } catch (eSkipDecl) {
        /* ignore */
      }
      return;
    }
    if (openSource === TRIGGER_SOURCE_EXIT_INTENT && hasCartItems) {
      try {
        console.log("EXIT INTENT BLOCKED:", true);
      } catch (eLog2) {
        /* ignore */
      }
      return;
    }
    if (openSource === TRIGGER_SOURCE_CART && !hasCartItems) {
      return;
    }
    if (!step1Ready) {
      return;
    }
    if (isDemoStoreProductPage()) {
      if (!readDemoStoreWidgetArmed()) {
        return;
      }
      if (demoStoreBubbleDismissed) {
        return;
      }
    }
    if (isDemoPath() && !demoCustomizationLoaded) {
      ensureDemoWidgetCustomizationLoaded(function () {
        showBubble(triggerSource, revealOpts);
      });
      return;
    }
    if (shown) {
      if (document.querySelector("[data-cartflow-bubble]")) {
        return;
      }
      var openFab = document.querySelector("[data-cartflow-fab]");
      if (openFab) {
        if (openSource === TRIGGER_SOURCE_EXIT_INTENT) {
          removeFabIfAny();
          shown = false;
          setCartflowWidgetShownFlag(false);
        } else {
          return;
        }
      } else {
        shown = false;
        setCartflowWidgetShownFlag(false);
      }
    }
    cartflowSyncHasCartFromCart();
    cartflowSyncWidgetShownForState();
    if (!cartflowCanShowWidget(openSource)) {
      return;
    }
    try {
      console.log("[CF FRONT] widget should open", triggerSource);
    } catch (eCfOpen) {
      /* ignore */
    }
    shown = true;
    setCartflowWidgetShownFlag(true);
    cfMarkWidgetShownForFrequency();
    cfLogWidgetTriggerFired(openSource);
    removeFabIfAny();
    if (step1Poll !== null) {
      clearInterval(step1Poll);
      step1Poll = null;
    }
    clearTimeout(idleTimer);
    idleTimer = null;
    cfClearHesitationAnchorTimer();
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });

    ensureMobileUxStyles();
    ensureChatBodyLayoutStyles();
    var shell = widgetShellChromeCss();
    var pcNorm = normalizeWidgetPrimaryHexClient(widgetPrimaryColor);
    var shellBorderCss = shell.border ? "border:" + shell.border + ";" : "";
    var shellBg = shell.bg || "#1e1b4b";
    var shellFg = shell.fg || "#f5f3ff";
    var shellPad =
      widgetChromeStyle === "minimal"
        ? "13px 15px"
        : widgetChromeStyle === "bold"
        ? "13px 15px"
        : "12px 14px";
    var w = document.createElement("div");
    w.setAttribute("dir", "rtl");
    w.setAttribute("lang", "ar");
    w.setAttribute("data-cartflow-bubble", "1");
    w._cfDragY = 0;
    w.style.cssText =
      "position:fixed;z-index:2147483640;box-sizing:border-box;" +
      "padding:" +
      shellPad +
      ";border-radius:" +
      shell.radius +
      ";background:" +
      shellBg +
      ";color:" +
      shellFg +
      ";" +
      "font:14px/1.45 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:" +
      shell.shadow +
      ";" +
      shellBorderCss +
      "pointer-events:auto;isolation:isolate;";

    var headerBand = document.createElement("div");
    headerBand.setAttribute("data-cf-widget-header", "1");
    var bandDark = shadeHex(pcNorm, -0.48);
    var bandMid = shadeHex(pcNorm, -0.22);
    var bandRadius =
      widgetChromeStyle === "bold" ? "12px" : widgetChromeStyle === "minimal" ? "10px" : "11px";
    var titleEl = document.createElement("div");
    titleEl.setAttribute("data-cf-widget-title", "1");
    titleEl.textContent = widgetBrandName || "مساعد المتجر";
    if (widgetChromeStyle === "minimal") {
      headerBand.style.cssText =
        "margin:0 0 12px 0;padding:11px 13px;border-radius:" +
        bandRadius +
        ";background:#ffffff;box-sizing:border-box;width:100%;border-bottom:3px solid " +
        pcNorm +
        ";box-shadow:none;";
      titleEl.style.cssText =
        "font-weight:700;font-size:15px;line-height:1.35;margin:0;letter-spacing:-0.01em;color:#0f172a;";
    } else if (widgetChromeStyle === "bold") {
      var bandDarkB = shadeHex(pcNorm, -0.58);
      var bandMidB = shadeHex(pcNorm, -0.06);
      headerBand.style.cssText =
        "margin:0 0 12px 0;padding:13px 15px;border-radius:" +
        bandRadius +
        ";background:linear-gradient(145deg," +
        bandDarkB +
        " 0%," +
        bandMidB +
        " 100%);box-sizing:border-box;width:100%;box-shadow:inset 0 -3px 0 rgba(0,0,0,.18);border:2px solid rgba(255,255,255,.22);";
      var lumBold = relativeLuminanceHex(bandMidB);
      titleEl.style.cssText =
        "font-weight:800;font-size:16px;line-height:1.35;margin:0;letter-spacing:-0.02em;" +
        (lumBold > 0.55
          ? "color:#1e1b4b;text-shadow:none;"
          : "color:#ffffff;text-shadow:0 2px 4px rgba(0,0,0,.35);");
    } else {
      headerBand.style.cssText =
        "margin:0 0 11px 0;padding:11px 13px;border-radius:" +
        bandRadius +
        ";background:linear-gradient(135deg," +
        bandDark +
        " 0%," +
        bandMid +
        " 100%);box-sizing:border-box;width:100%;box-shadow:0 4px 14px rgba(0,0,0,.12);";
      var lumMid = relativeLuminanceHex(bandMid);
      titleEl.style.cssText =
        "font-weight:700;font-size:15px;line-height:1.35;margin:0;letter-spacing:-0.01em;" +
        (lumMid > 0.55
          ? "color:#1e1b4b;text-shadow:none;"
          : "color:#ffffff;text-shadow:0 1px 2px rgba(0,0,0,.28);");
    }
    headerBand.appendChild(titleEl);

    w.addEventListener(
      "click",
      function (ev) {
        if (ev.target === w) {
          ev.stopPropagation();
        }
      },
      false
    );

    var chromeBtnStyle = chromeToolbarBtnStyle();
    var chromeBorderW =
      widgetChromeStyle === "minimal" ? "1px" : widgetChromeStyle === "bold" ? "4px" : "2px";
    var chromeBorderCol = widgetChromeStyle === "minimal" ? "#e2e8f0" : pcNorm;

    var chrome = document.createElement("div");
    chrome.setAttribute("data-cf-chrome", "1");
    w._cfChrome = chrome;
    if (isNarrowViewport()) {
      chrome.style.cssText =
        "display:flex;flex-direction:row;align-items:stretch;justify-content:space-between;gap:10px;" +
        "width:100%;margin:0 0 10px 0;box-sizing:border-box;border-bottom:" +
        chromeBorderW +
        " solid " +
        chromeBorderCol +
        ";padding-bottom:10px;";
    } else {
      chrome.style.cssText =
        "display:flex;justify-content:flex-end;align-items:center;gap:" +
        (widgetChromeStyle === "bold" ? "10px" : "8px") +
        ";" +
        "width:100%;margin:0 0 10px 0;box-sizing:border-box;border-bottom:" +
        chromeBorderW +
        " solid " +
        chromeBorderCol +
        ";padding-bottom:10px;";
    }

    function getMaxDragPx() {
      return Math.max(0, Math.round(window.innerHeight * 0.28));
    }

    var dragPtrActive = false;
    var dragStartClientY = 0;
    var dragStartOffset = 0;

    var _cfTouchMoveOpts = { capture: true, passive: false };

    function endDrag() {
      dragPtrActive = false;
      document.removeEventListener("mousemove", onDragPointerMove, true);
      document.removeEventListener("mouseup", onDragPointerEnd, true);
      document.removeEventListener("touchmove", onDragPointerMove, _cfTouchMoveOpts);
      document.removeEventListener("touchend", onDragPointerEnd, true);
      document.removeEventListener("touchcancel", onDragPointerEnd, true);
    }

    function onDragPointerMove(ev) {
      if (!dragPtrActive) {
        return;
      }
      var p = ev.touches && ev.touches[0] ? ev.touches[0] : ev;
      if (!p) {
        return;
      }
      var dy = p.clientY - dragStartClientY;
      var next = dragStartOffset - dy;
      var m = getMaxDragPx();
      if (next < 0) {
        next = 0;
      }
      if (next > m) {
        next = m;
      }
      w._cfDragY = next;
      w.style.transform =
        next > 0 ? "translate3d(0, " + String(-next) + "px, 0)" : "";
      if (ev.cancelable) {
        ev.preventDefault();
      }
    }

    function onDragPointerEnd() {
      endDrag();
    }

    if (isNarrowViewport()) {
      var handle = document.createElement("div");
      handle.setAttribute("data-cf-drag-handle", "1");
      handle.setAttribute("aria-label", "سحب لتحريك النافذة");
      handle.style.cssText =
        "flex:1 1 auto;min-height:44px;min-width:48px;cursor:grab;user-select:none;-webkit-user-select:none;" +
        "touch-action:none;display:flex;align-items:center;opacity:0.75;";
      var grip = document.createElement("span");
      grip.setAttribute("aria-hidden", "true");
      grip.textContent = "⋮⋮";
      grip.style.cssText = "font-size:14px;letter-spacing:1px;";
      handle.appendChild(grip);
      function onHandleDown(ev) {
        if (ev.type === "mousedown" && ev.button !== 0) {
          return;
        }
        dragPtrActive = true;
        var p = ev.touches && ev.touches[0] ? ev.touches[0] : ev;
        dragStartClientY = p.clientY;
        dragStartOffset = w._cfDragY || 0;
        if (ev.cancelable) {
          ev.preventDefault();
        }
        document.addEventListener("mousemove", onDragPointerMove, true);
        document.addEventListener("mouseup", onDragPointerEnd, true);
        document.addEventListener("touchmove", onDragPointerMove, _cfTouchMoveOpts);
        document.addEventListener("touchend", onDragPointerEnd, true);
        document.addEventListener("touchcancel", onDragPointerEnd, true);
      }
      handle.addEventListener("mousedown", onHandleDown, false);
      handle.addEventListener("touchstart", onHandleDown, { passive: false });
      chrome.appendChild(handle);
    }

    function stripContentKeepChrome() {
      var body = w.querySelector(".cartflow-widget-body");
      if (body) {
        while (body.firstChild) {
          body.removeChild(body.firstChild);
        }
        return;
      }
      var ch = w.children;
      var i;
      for (i = ch.length - 1; i >= 0; i--) {
        var node = ch[i];
        if (node.getAttribute("data-cf-chrome") !== "1") {
          w.removeChild(node);
        }
      }
    }

    function onWinResize() {
      if (!w) {
        return;
      }
      if (!w.isConnected) {
        return;
      }
      var m = getMaxDragPx();
      if (w._cfDragY > m) {
        w._cfDragY = m;
      }
      if (w._cfDragY > 0) {
        w.style.transform =
          "translate3d(0, " + String(-w._cfDragY) + "px, 0)";
      } else {
        w.style.transform = "";
      }
      applyBubbleLayout(w);
    }

    w._cfCleanup = function () {
      endDrag();
      window.removeEventListener("resize", onWinResize);
      window.removeEventListener("orientationchange", onWinResize);
    };
    window.addEventListener("resize", onWinResize, { passive: true });
    window.addEventListener("orientationchange", onWinResize, { passive: true });

    function mountMinimizedFab() {
      removeFabIfAny();
      ensureMobileUxStyles();
      ensureChatBodyLayoutStyles();
      var fab = document.createElement("button");
      fab.type = "button";
      fab.setAttribute("data-cartflow-fab", "1");
      fab.setAttribute("aria-label", "توسيع CartFlow");
      var fabFill = widgetButtonFillHex(widgetPrimaryColor);
      var fabRad =
        widgetChromeStyle === "minimal" ? "16px" : widgetChromeStyle === "bold" ? "50%" : "50%";
      var fabShadow =
        widgetChromeStyle === "minimal"
          ? "0 1px 4px rgba(15,23,42,.08)"
          : widgetChromeStyle === "bold"
          ? "0 14px 36px rgba(0,0,0,.48), 0 4px 12px rgba(0,0,0,.22)"
          : "0 8px 26px rgba(0,0,0,.26)";
      var fabBorder =
        widgetChromeStyle === "minimal"
          ? "2px solid rgba(15,23,42,.14)"
          : widgetChromeStyle === "bold"
          ? "4px solid rgba(255,255,255,.42)"
          : "0";
      var fabMin =
        widgetChromeStyle === "bold" ? "54px" : widgetChromeStyle === "minimal" ? "50px" : "48px";
      fab.style.cssText =
        "position:fixed;z-index:2147483639;padding:0;margin:0;min-width:" +
        fabMin +
        ";min-height:" +
        fabMin +
        ";" +
        "width:" +
        fabMin +
        ";height:" +
        fabMin +
        ";border-radius:" +
        fabRad +
        ";" +
        "border:" +
        fabBorder +
        ";background:" +
        fabFill +
        ";color:#fff;font-size:20px;line-height:1;cursor:pointer;" +
        "box-shadow:" +
        fabShadow +
        ";touch-action:manipulation;pointer-events:auto;" +
        "display:flex;align-items:center;justify-content:center;position:relative;" +
        "animation:cfFabPulse 2.2s ease-in-out infinite;";
      if (isNarrowViewport()) {
        fab.style.right = "max(12px, env(safe-area-inset-right, 0px))";
        fab.style.left = "auto";
        fab.style.bottom = "max(12px, env(safe-area-inset-bottom, 0px))";
        fab.style.top = "auto";
      } else {
        fab.style.right = "max(12px, env(safe-area-inset-right, 0px))";
        fab.style.bottom = "max(12px, env(safe-area-inset-bottom, 0px))";
        fab.style.left = "auto";
        fab.style.top = "auto";
      }
      var fabIcon = document.createElement("span");
      fabIcon.textContent = "💬";
      fabIcon.style.cssText = "line-height:1;";
      fab.appendChild(fabIcon);
      var actDot = document.createElement("span");
      actDot.setAttribute("aria-hidden", "true");
      actDot.title = "نشاط";
      var dotBorder =
        widgetChromeStyle === "minimal" ? "#ffffff" : widgetChromeStyle === "bold" ? "#0f172a" : "#1e1b4a";
      actDot.style.cssText =
        "position:absolute;top:5px;right:5px;width:8px;height:8px;border-radius:50%;" +
        "background:#34d399;border:2px solid " +
        dotBorder +
        ";box-sizing:border-box;pointer-events:none;" +
        "animation:cfFabDot 1.6s ease-in-out infinite;";
      fab.appendChild(actDot);
      fab.addEventListener("click", function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (fab.parentNode) {
          fab.parentNode.removeChild(fab);
        }
        w._cfDragY = 0;
        w.style.transform = "";
        document.body.appendChild(w);
        applyBubbleLayout(w);
        applyWidgetCustomization();
      });
      document.body.appendChild(fab);
      applyWidgetCustomization();
    }

    var btnMin = document.createElement("button");
    btnMin.type = "button";
    btnMin.setAttribute("aria-label", "تصغير");
    btnMin.textContent = "−";
    btnMin.style.cssText = chromeBtnStyle;
    btnMin.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (isDemoStoreProductPage() && isDemoScenarioActive()) {
        return;
      }
      if (w.parentNode) {
        w.parentNode.removeChild(w);
      }
      endDrag();
      mountMinimizedFab();
    });

    var btnClose = document.createElement("button");
    btnClose.type = "button";
    btnClose.setAttribute("aria-label", "إخفاء");
    btnClose.textContent = "×";
    btnClose.style.cssText = chromeBtnStyle;
    btnClose.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      cfMaybeMarkDismissSuppress();
      removeFabIfAny();
      if (typeof w._cfCleanup === "function") {
        w._cfCleanup();
      }
      if (w.parentNode) {
        w.parentNode.removeChild(w);
      }
      if (isDemoStoreProductPage()) {
        shown = false;
        setCartflowWidgetShownFlag(false);
        demoStoreBubbleDismissed = true;
        clearTimeout(idleTimer);
        idleTimer = null;
      }
    });

    var btnGroup = document.createElement("div");
    btnGroup.style.cssText =
      "display:flex;flex-direction:row;align-items:center;gap:8px;flex-shrink:0;";
    btnGroup.appendChild(btnMin);
    btnGroup.appendChild(btnClose);
    if (isNarrowViewport()) {
      chrome.appendChild(btnGroup);
    } else {
      chrome.appendChild(btnMin);
      chrome.appendChild(btnClose);
    }
    w.appendChild(headerBand);
    w.appendChild(chrome);

    var widgetBody = document.createElement("div");
    widgetBody.className = "cartflow-widget-body chat-body";
    widgetBody.style.cssText = "min-width:0;box-sizing:border-box;";
    w.appendChild(widgetBody);

    applyBubbleLayout(w);

    function collectDiscoveryProductCandidates(maxN) {
      var out = [];
      var limit = typeof maxN === "number" ? maxN : 3;
      limit = Math.min(Math.max(limit, 2), 3);
      try {
        var demoMap = window.CF_DEMO_PRODUCTS;
        if (demoMap && typeof demoMap === "object") {
          var keys = Object.keys(demoMap);
          var i;
          for (i = 0; i < keys.length && out.length < limit; i++) {
            var row = demoMap[keys[i]];
            if (row && typeof row === "object") {
              out.push(row);
            }
          }
          if (out.length) {
            return out;
          }
        }
      } catch (eDm) {
        /* ignore */
      }
      try {
        var arr = window.CARTFLOW_DISCOVERY_PRODUCTS;
        if (Array.isArray(arr)) {
          var j;
          for (j = 0; j < arr.length && out.length < limit; j++) {
            var item = arr[j];
            if (item && typeof item === "object") {
              out.push(item);
            }
          }
        }
      } catch (eArr) {
        /* ignore */
      }
      return out;
    }

    function appendExitDiscoveryProductCard(prod) {
      if (!prod || typeof prod !== "object") {
        return;
      }
      var name = strTrim(prod.name) || "منتج";
      var priceNum = prod.price;
      var priceSuffix = "";
      if (typeof priceNum === "number" && isFinite(priceNum)) {
        if (priceNum % 1 === 0) {
          priceSuffix = String(Math.round(priceNum)) + " ريال";
        } else {
          priceSuffix = priceNum.toFixed(2) + " ريال";
        }
      }
      var box = document.createElement("div");
      box.setAttribute("data-cf-exit-discovery-product", "1");
      var boxRad =
        widgetChromeStyle === "minimal" ? "10px" : widgetChromeStyle === "bold" ? "14px" : "12px";
      var boxBg =
        widgetChromeStyle === "minimal"
          ? "#f8fafc"
          : "rgba(255,255,255,.1)";
      var boxBorderCss =
        widgetChromeStyle === "minimal"
          ? "1px solid #e2e8f0"
          : widgetChromeStyle === "bold"
          ? "2px solid rgba(255,255,255,.22)"
          : "1px solid rgba(255,255,255,.14)";
      box.style.cssText =
        "margin:10px 0;padding:" +
        (widgetChromeStyle === "bold" ? "14px" : "12px") +
        ";border-radius:" +
        boxRad +
        ";background:" +
        boxBg +
        ";" +
        "border:" +
        boxBorderCss +
        ";font-size:13px;line-height:1.45;";
      var titleRow = document.createElement("div");
      titleRow.style.cssText =
        "font-weight:700;margin-bottom:8px;color:" +
        (widgetChromeStyle === "minimal" ? "#0f172a" : "inherit") +
        ";";
      titleRow.textContent = name + (priceSuffix ? " — " + priceSuffix : "");
      box.appendChild(titleRow);
      var btnAdd = document.createElement("button");
      btnAdd.type = "button";
      btnAdd.textContent = "أضف للسلة";
      btnAdd.setAttribute("data-cf-exit-discovery-add", "1");
      stampPrimaryBubbleBtn(btnAdd, "width:100%!important;font-size:14px!important;min-height:48px!important;");
      btnAdd.addEventListener("click", function (evAdd) {
        evAdd.stopPropagation();
        evAdd.preventDefault();
        try {
          if (typeof window.addToCart === "function") {
            window.addToCart(Object.assign({}, prod));
          }
        } catch (eAtc) {
          /* ignore */
        }
        logWidgetDiscoveryFlow("add_to_cart_click");
      });
      box.appendChild(btnAdd);
      widgetBody.appendChild(box);
    }

    function renderExitIntentProductDiscovery() {
      stripContentKeepChrome();
      try {
        w.removeAttribute("data-cf-yes");
      } catch (eRy) {
        /* ignore */
      }
      var introDisc = document.createElement("p");
      introDisc.setAttribute("data-cf-exit-discovery-intro", "1");
      introDisc.style.cssText =
        "margin:0 0 12px 0;font-size:14px;line-height:1.55;white-space:pre-line;color:" +
        (widgetChromeStyle === "minimal" ? "#334155" : "inherit") +
        ";";
      introDisc.textContent = getExitDiscoveryIntroText();
      widgetBody.appendChild(introDisc);
      var picks = collectDiscoveryProductCandidates(3);
      var pi;
      for (pi = 0; pi < picks.length; pi++) {
        appendExitDiscoveryProductCard(picks[pi]);
      }
      if (!picks.length) {
        var ph = document.createElement("p");
        ph.setAttribute("data-cf-exit-discovery-empty", "1");
        ph.style.cssText =
          "margin:0 0 10px 0;font-size:13px;line-height:1.5;opacity:" +
          (widgetChromeStyle === "minimal" ? "1" : "0.95") +
          ";color:" +
          (widgetChromeStyle === "minimal" ? "#475569" : "inherit") +
          ";";
        ph.textContent =
          "تصفّح منتجات المتجر من الصفحة واضغط «أضف للسلة» على اللي يعجبك 👍";
        widgetBody.appendChild(ph);
        try {
          var gridEl = document.getElementById("cf-demo-products");
          if (gridEl && gridEl.scrollIntoView) {
            var btnScroll = document.createElement("button");
            btnScroll.type = "button";
            btnScroll.textContent = "انتقل للمنتجات 👇";
            stampPrimaryBubbleBtn(btnScroll);
            btnScroll.addEventListener("click", function (evSc) {
              evSc.stopPropagation();
              evSc.preventDefault();
              gridEl.scrollIntoView({ behavior: "smooth", block: "start" });
            });
            widgetBody.appendChild(btnScroll);
          }
        } catch (eGr) {
          /* ignore */
        }
      }
    }

    function openProductDiscoveryMode() {
      var body = w.querySelector(".cartflow-widget-body");
      if (!body) {
        return;
      }
      w._cfOnBackToEntry = function () {
        renderBrowsingGeneralOptions();
      };
      stripContentKeepChrome();
      var sec = document.createElement("div");
      sec.className = "cf-section";
      sec.setAttribute("data-cf-product-discovery", "1");
      var title = document.createElement("div");
      title.className = "cf-title";
      title.textContent = "وش تبحث عنه؟ 👀";
      title.style.cssText = "font-weight:700;font-size:15px;margin:0 0 10px 0;line-height:1.45;";
      sec.appendChild(title);
      var quick = ["عطور", "ملابس", "إلكترونيات", "هدايا"];
      var j;
      for (j = 0; j < quick.length; j++) {
        (function (label) {
          var b = document.createElement("button");
          b.type = "button";
          b.className = "cf-btn";
          b.textContent = label;
          stampPrimaryBubbleBtn(b);
          b.addEventListener("click", function (e) {
            e.stopPropagation();
            e.preventDefault();
          });
          sec.appendChild(b);
        })(quick[j]);
      }
      var bBack = document.createElement("button");
      bBack.type = "button";
      bBack.textContent = BTN_BACK;
      bBack.setAttribute("aria-label", "رجوع لقائمة التصفح");
      stampPrimaryBubbleBtn(bBack);
      bBack.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        renderBrowsingGeneralOptions();
      });
      sec.appendChild(bBack);
      body.appendChild(sec);
    }

      function mountLayerDAbandonIfEligible() {
      try {
        w.setAttribute("data-cf-reason-entry", "layer_d");
      } catch (eEnLd) {
        /* ignore */
      }
      if (openSource !== TRIGGER_SOURCE_CART) {
        return;
      }
      if (w.getAttribute("data-cf-cart-affirm-help") !== "1") {
        return;
      }
      if (w.getAttribute("data-cf-layer-d-no-help-active") === "1") {
        return;
      }

      if (vipPhoneTryMountBubbleBlock(widgetBody)) {
        return;
      }

      function remountPrimaryCartReasonSurface() {
        try {
          if (String(w.getAttribute("data-cf-reason-entry") || "") === "classic") {
            renderReasonList();
            return;
          }
        } catch (eRmS) {
          /* ignore */
        }
        mountLayerDAbandonIfEligible();
      }

      function remountCartReasonChoicesFromFollowUp() {
        logWidgetFlow("reason_menu_back", "", "رجوع_للقائمة_السابقة");
        try {
          w.removeAttribute("data-cf-layer-d-no-help-active");
        } catch (eRmNoHelpFlg) {
          /* ignore */
        }
        stripContentKeepChrome();
        remountPrimaryCartReasonSurface();
      }

      var wrap = document.createElement("div");
      wrap.setAttribute("data-cf-layer-d-abandon", "1");
      wrap.style.cssText =
        "display:block;width:100%;box-sizing:border-box;margin:0 0 10px 0;";

      function appendReturnToRecoveryChatButtonRow() {
        var rowReturn = document.createElement("div");
        rowReturn.setAttribute("data-cf-layer-d-return-row", "1");
        var bChat = document.createElement("button");
        bChat.type = "button";
        bChat.setAttribute("data-cf-layer-d-chat-return", "1");
        bChat.setAttribute("aria-label", "رجوع للمحادثة");
        bChat.textContent = "رجوع للمحادثة";
        stampPrimaryBubbleBtn(bChat);
        bChat.addEventListener("click", function (evRet) {
          evRet.stopPropagation();
          evRet.preventDefault();
          stripContentKeepChrome();
          remountPrimaryCartReasonSurface();
        });
        rowReturn.appendChild(bChat);
        widgetBody.appendChild(rowReturn);
      }

      window._cfFlowStack = window._cfFlowStack || [];

      function cfSetNavStep(label) {
        try {
          window._cfNavStepLabel =
            label != null ? String(label) : "";
        } catch (eCfNav) {
          /* ignore */
        }
      }

      function cfGetNavStep() {
        try {
          return window._cfNavStepLabel != null
            ? String(window._cfNavStepLabel)
            : "";
        } catch (eCfG) {
          return "";
        }
      }

      function cfClearFlowStack() {
        window._cfFlowStack = [];
        cfSetNavStep("");
      }

      function cfPushFlow(renderPrev) {
        if (!window._cfFlowStack) {
          window._cfFlowStack = [];
        }
        if (typeof renderPrev === "function") {
          window._cfFlowStack.push(renderPrev);
        }
      }

      function cfPopFlow() {
        if (!window._cfFlowStack || !window._cfFlowStack.length) {
          return null;
        }
        return window._cfFlowStack.pop();
      }

      function logWidgetNav(action, fromStep, toStep) {
        try {
          console.log(
            "[WIDGET NAV] action=" +
              String(action) +
              " from=" +
              String(fromStep != null ? fromStep : "") +
              " to=" +
              String(toStep != null ? toStep : "")
          );
        } catch (eNav) {
          /* ignore */
        }
      }

      function appendObjectionFlowNavRow(flowKind) {
        var rowNav = document.createElement("div");
        rowNav.setAttribute("data-cf-objection-flow-nav", "1");
        rowNav.style.cssText =
          "display:flex;flex-direction:row;flex-wrap:nowrap;align-items:stretch;" +
          "gap:8px;margin-top:12px;width:100%;box-sizing:border-box;";

        var bBack = document.createElement("button");
        bBack.type = "button";
        bBack.setAttribute("aria-label", "رجوع خطوة للخلف");
        bBack.textContent = "⬅️ رجوع";
        stampPrimaryBubbleBtn(bBack, "flex:1 1 0;min-width:0;text-align:center;");
        bBack.addEventListener("click", function (evRb) {
          evRb.stopPropagation();
          evRb.preventDefault();
          var from = cfGetNavStep();
          var prevRender = cfPopFlow();
          if (typeof prevRender === "function") {
            logWidgetNav("back", from, String(flowKind) + "_previous");
            try {
              prevRender();
            } catch (ePrev) {
              /* ignore */
            }
          } else {
            logWidgetNav("back", from, "reason_menu");
            cfClearFlowStack();
            remountCartReasonChoicesFromFollowUp();
          }
        });

        var bHome = document.createElement("button");
        bHome.type = "button";
        bHome.setAttribute("aria-label", "القائمة الرئيسية للأسباب");
        bHome.textContent = "🏠 الرئيسية";
        stampPrimaryBubbleBtn(bHome, "flex:1 1 0;min-width:0;text-align:center;");
        bHome.addEventListener("click", function (evHm) {
          evHm.stopPropagation();
          evHm.preventDefault();
          logWidgetNav("home", cfGetNavStep(), "reason_menu");
          if (flowKind === "price") {
            logWidgetFlow("price_followup_nav", "price_high", "رجوع_للقائمة");
            logWidgetConversionFlow("price", "رجوع_للقائمة");
          } else if (flowKind === "shipping") {
            logWidgetFlow("shipping_followup_nav", "shipping_cost", "رجوع_للقائمة");
            logWidgetConversionFlow("shipping_cost", "رجوع_للقائمة");
          } else if (flowKind === "quality") {
            logWidgetFlow("quality_followup_nav", "quality_uncertainty", "رجوع_للقائمة");
            logWidgetConversionFlow("quality", "رجوع_للقائمة");
          } else if (flowKind === "delivery") {
            logWidgetFlow("delivery_followup_nav", "delivery_time", "رجوع_للقائمة");
            logWidgetConversionFlow("delivery", "رجوع_للقائمة");
          }
          cfClearFlowStack();
          stripContentKeepChrome();
          mountLayerDAbandonIfEligible();
        });

        rowNav.appendChild(bBack);
        rowNav.appendChild(bHome);
        widgetBody.appendChild(rowNav);
      }

      function showLayerDAckAfterPick(wrapEl) {
        while (wrapEl.firstChild) {
          wrapEl.removeChild(wrapEl.firstChild);
        }
        var ack = document.createElement("p");
        ack.style.cssText =
          "margin:0 0 8px 0;font-size:13px;line-height:1.5;opacity:0.95;";
        ack.textContent =
          "شكراً 🙏 سجلنا ملاحظتك؛ تقدر تتواصل وقت ما تحتاج.";
        wrapEl.appendChild(ack);
        appendReturnToRecoveryChatButtonRow();
      }

      window._cartflowApplyNoHelpUi = function applyNoHelpUi() {
        try {
          w.setAttribute("data-cf-layer-d-no-help-active", "1");
        } catch (eNoHelpAttr) {
          /* ignore */
        }
        logWidgetFlow("layer_d_no_help_ui", "no_help", "open");
        persistSessionAbandonReason("no_help", null);
        stripContentKeepChrome();
        var pNk = document.createElement("p");
        pNk.setAttribute("data-cf-layer-d-no-help", "1");
        pNk.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.55;";
        pNk.textContent = "تمام، أنا هنا إذا احتجت أي شيء.";
        widgetBody.appendChild(pNk);

        var rowNk = document.createElement("div");
        rowNk.setAttribute("data-cf-layer-d-no-help-buttons", "1");
        rowNk.style.cssText = rowStyleCol;

        function dismissAssistBubble(evDismiss) {
          if (evDismiss) {
            evDismiss.stopPropagation();
            evDismiss.preventDefault();
          }
          if (isDemoStoreProductPage() && isDemoScenarioActive()) {
            return;
          }
          logWidgetFlow("layer_d_no_help_nav", "no_help", "إغلاق_المساعد");
          removeFabIfAny();
          if (typeof w._cfCleanup === "function") {
            w._cfCleanup();
          }
          if (w && w.parentNode) {
            w.parentNode.removeChild(w);
          }
          if (isDemoStoreProductPage()) {
            shown = false;
            setCartflowWidgetShownFlag(false);
            demoStoreBubbleDismissed = true;
            clearTimeout(idleTimer);
            idleTimer = null;
          }
        }

        var bBackMenu = document.createElement("button");
        bBackMenu.type = "button";
        bBackMenu.textContent = "رجوع للقائمة السابقة";
        stampPrimaryBubbleBtn(bBackMenu);
        bBackMenu.addEventListener("click", function (ev) {
          ev.stopPropagation();
          ev.preventDefault();
          logWidgetFlow("layer_d_no_help_nav", "no_help", "رجوع_للقائمة");
          remountCartReasonChoicesFromFollowUp();
        });

        var bCloseAssist = document.createElement("button");
        bCloseAssist.type = "button";
        bCloseAssist.textContent = "إغلاق المساعد";
        stampPrimaryBubbleBtn(bCloseAssist);
        bCloseAssist.addEventListener("click", dismissAssistBubble);

        rowNk.appendChild(bBackMenu);
        rowNk.appendChild(bCloseAssist);
        widgetBody.appendChild(rowNk);
      };

      function mountPriceObjectionFollowUp() {
        logWidgetFlow("price_followup_ui", "price_high", "open");
        logWidgetConversionFlow("price", "open");
        persistSessionAbandonReason("price_high", null);

        function cartLineNumericPrice(line) {
          if (!line || typeof line !== "object") {
            return null;
          }
          var p = line.price;
          if (typeof p === "number" && isFinite(p)) {
            return p;
          }
          if (p == null || strTrim(String(p)) === "") {
            return null;
          }
          var m = String(p).replace(/[^\d.,]/g, "").replace(/,/g, ".");
          var n = parseFloat(m);
          return isFinite(n) ? n : null;
        }

        function pickCheapestLines(items, maxN) {
          if (!items || !items.length) {
            return [];
          }
          var arr = items.slice();
          arr.sort(function (a, b) {
            var pa = cartLineNumericPrice(a);
            var pb = cartLineNumericPrice(b);
            if (pa == null && pb == null) {
              return 0;
            }
            if (pa == null) {
              return 1;
            }
            if (pb == null) {
              return -1;
            }
            return pa - pb;
          });
          return arr.slice(0, maxN);
        }

        function pickLowerPricedThanAnchor(items, anchor, maxN) {
          if (!items || !items.length || anchor == null) {
            return [];
          }
          var scored = [];
          var i;
          for (i = 0; i < items.length; i++) {
            var pn = cartLineNumericPrice(items[i]);
            if (pn != null && pn < anchor) {
              scored.push({ line: items[i], p: pn });
            }
          }
          scored.sort(function (x, y) {
            return x.p - y.p;
          });
          var out = [];
          for (i = 0; i < scored.length && out.length < maxN; i++) {
            out.push(scored[i].line);
          }
          return out;
        }

        function pickLinesInBudget(items, minP, maxP, maxN) {
          var matches = [];
          var i;
          for (i = 0; i < (items || []).length; i++) {
            var pn = cartLineNumericPrice(items[i]);
            if (pn == null) {
              continue;
            }
            if (maxP != null) {
              if (pn >= minP && pn < maxP) {
                matches.push(items[i]);
              }
            } else if (pn >= minP) {
              matches.push(items[i]);
            }
          }
          var inRange = pickCheapestLines(matches, maxN);
          if (inRange.length) {
            return inRange;
          }
          return pickCheapestLines(items, maxN);
        }

        function lineDiscountStrength(line) {
          var p = cartLineNumericPrice(line);
          if (p == null) {
            return -1;
          }
          var keys = [
            "compare_at_price",
            "original_price",
            "old_price",
            "list_price",
          ];
          var k;
          for (k = 0; k < keys.length; k++) {
            var raw = line[keys[k]];
            var op = cartLineNumericPrice({ price: raw });
            if (op != null && op > p) {
              return op - p;
            }
          }
          if (line.on_sale === true || line.is_on_sale === true) {
            return 1;
          }
          return 0;
        }

        function pickDiscountedOrBestValue(items, maxN) {
          var scored = [];
          var i;
          for (i = 0; i < (items || []).length; i++) {
            var s = lineDiscountStrength(items[i]);
            if (s > 0) {
              scored.push({ line: items[i], s: s });
            }
          }
          scored.sort(function (a, b) {
            return b.s - a.s;
          });
          if (scored.length) {
            var out = [];
            for (i = 0; i < scored.length && out.length < maxN; i++) {
              out.push(scored[i].line);
            }
            return out;
          }
          return pickCheapestLines(items, maxN);
        }

        function appendPriceFollowUpMsgParagraph(text) {
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-price-followup-msg", "1");
          pOut.style.cssText =
            "margin:0 0 10px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          pOut.textContent = text;
          widgetBody.appendChild(pOut);
        }

        function appendPriceProductCard(line, caption) {
          if (!line || typeof line !== "object") {
            return;
          }
          var name = strTrim(line.name) || "منتج في سلتك";
          var pl = formatPriceRiyal(line);
          var box = document.createElement("div");
          box.setAttribute("data-cf-price-conversion-product", "1");
          box.style.cssText =
            "margin:10px 0;padding:10px;border-radius:8px;background:rgba(124,58,237,.09);" +
            "font-size:13px;line-height:1.5;";
          if (caption && strTrim(caption) !== "") {
            var cap = document.createElement("div");
            cap.style.cssText = "font-weight:700;margin-bottom:4px;";
            cap.textContent = caption;
            box.appendChild(cap);
          }
          var row = document.createElement("div");
          row.textContent = name + (pl ? " — " + pl : "");
          box.appendChild(row);
          widgetBody.appendChild(box);
        }

        function appendPriceContinueCTA(optionKey) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.setAttribute("data-cf-price-conversion-cta", "1");
          btn.textContent = "كمّل الطلب والدفع 👇";
          stampPrimaryBubbleBtn(btn);
          btn.addEventListener("click", function (evCta) {
            evCta.stopPropagation();
            evCta.preventDefault();
            logWidgetConversionFlow(
              "price",
              String(optionKey) + "_cta_continue"
            );
            scrollToCartOrCheckout();
          });
          widgetBody.appendChild(btn);
        }

        function mountPriceConversionStep(responseMsg, optionKey, extrasFn) {
          stripContentKeepChrome();
          cfSetNavStep("price_results_" + String(optionKey));
          if (responseMsg && strTrim(responseMsg) !== "") {
            appendPriceFollowUpMsgParagraph(responseMsg);
          }
          if (typeof extrasFn === "function") {
            extrasFn();
          }
          appendPriceContinueCTA(optionKey);
          appendObjectionFlowNavRow("price");
        }

        function innerBudgetChipUI() {
          stripContentKeepChrome();
          cfSetNavStep("price_budget_chips");
          appendPriceFollowUpMsgParagraph(
            "تمام 👍 كم الميزانية اللي في بالك؟"
          );
          var row = document.createElement("div");
          row.setAttribute("data-cf-price-budget-chips", "1");
          row.style.cssText =
            "display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;width:100%;box-sizing:border-box;";
          function bindChip(label, minP, maxP, slug) {
            var b = document.createElement("button");
            b.type = "button";
            b.textContent = label;
            stampPrimaryBubbleBtn(b);
            b.addEventListener("click", function (ev) {
              ev.stopPropagation();
              ev.preventDefault();
              logWidgetFlow(
                "price_followup_pick",
                "price_high",
                "ميزانية_" + slug
              );
              logWidgetConversionFlow("price", "ميزانية_" + slug);
              cfPushFlow(innerBudgetChipUI);
              var items = getCartLineItems();
              var picked = pickLinesInBudget(items, minP, maxP, 3);
              mountPriceConversionStep(
                "هذه مقترحات تناسب اختيارك 👇",
                "budget_" + slug,
                function () {
                  var j;
                  for (j = 0; j < picked.length; j++) {
                    appendPriceProductCard(picked[j], null);
                  }
                  if (!picked.length) {
                    appendPriceFollowUpMsgParagraph(
                      "جرّب تكمّل من السلة لمقارنة الخيارات المناسبة."
                    );
                  }
                }
              );
            });
            row.appendChild(b);
          }
          bindChip("أقل من 100", 0, 100, "under_100");
          bindChip("100–200", 100, 200, "100_200");
          bindChip("200–300", 200, 300, "200_300");
          bindChip("300+", 300, null, "300_plus");
          widgetBody.appendChild(row);
          appendObjectionFlowNavRow("price");
        }

        function mountBudgetChipStep() {
          logWidgetFlow("price_followup_pick", "price_high", "ميزانية_محددة");
          logWidgetConversionFlow("price", "ميزانية_محددة");
          innerBudgetChipUI();
        }

        function renderPriceOptionsScreen() {
          stripContentKeepChrome();
          cfSetNavStep("price_options");
          var introEl = document.createElement("p");
          introEl.setAttribute("data-cf-price-followup-intro", "1");
          introEl.style.cssText =
            "margin:0 0 12px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          introEl.textContent =
            "واضح إن السعر مهم لك 👍 خلني أساعدك توصل لأفضل خيار بسرعة:";

          var rowPfEl = document.createElement("div");
          rowPfEl.setAttribute("data-cf-price-followup-buttons", "1");
          rowPfEl.style.cssText = rowStyleCol;

          function addPfBtn(label, onActivate) {
            var bx = document.createElement("button");
            bx.type = "button";
            bx.textContent = label;
            stampPrimaryBubbleBtn(bx);
            bx.addEventListener("click", function (ev) {
              ev.stopPropagation();
              ev.preventDefault();
              onActivate();
            });
            rowPfEl.appendChild(bx);
          }

          addPfBtn("أبغى خيار أرخص الآن", function () {
            cfPushFlow(renderPriceOptionsScreen);
            logWidgetFlow("price_followup_pick", "price_high", "خيار_أرخص");
            logWidgetConversionFlow("price", "خيار_أرخص");
            var items = getCartLineItems();
            var anchor = items.length ? cartLineNumericPrice(items[0]) : null;
            var picked = pickLowerPricedThanAnchor(items, anchor, 3);
            if (!picked.length) {
              picked = pickCheapestLines(items, 3);
            }
            mountPriceConversionStep(
              "تمام 👍 خلني أرشح لك بديل قريب بسعر أقل 👇",
              "cheaper_now",
              function () {
                var j;
                for (j = 0; j < picked.length; j++) {
                  appendPriceProductCard(picked[j], null);
                }
                if (!picked.length) {
                  appendPriceFollowUpMsgParagraph(
                    "أضف للسلة ثم كمّل الطلب لمقارنة أفضل الأسعار."
                  );
                }
              }
            );
          });

          addPfBtn("عندي ميزانية محددة", function () {
            cfPushFlow(renderPriceOptionsScreen);
            mountBudgetChipStep();
          });

          addPfBtn("هل فيه خصم أو عرض؟", function () {
            cfPushFlow(renderPriceOptionsScreen);
            logWidgetFlow("price_followup_pick", "price_high", "خصم_أو_عرض");
            logWidgetConversionFlow("price", "خصم_أو_عرض");
            var items = getCartLineItems();
            var picked = pickDiscountedOrBestValue(items, 3);
            mountPriceConversionStep(
              "أحيانًا فيه عروض أو خيارات أوفر 👌 خلني أطلع لك الأفضل الآن 👇",
              "discount_offer",
              function () {
                var j;
                for (j = 0; j < picked.length; j++) {
                  appendPriceProductCard(picked[j], "خيار بقيمة مناسبة");
                }
                if (!picked.length) {
                  appendPriceFollowUpMsgParagraph(
                    "كمّل الطلب من السلة لتظهر أي عروض أو خصومات نشطة عند الدفع."
                  );
                }
              }
            );
          });

          widgetBody.appendChild(introEl);
          widgetBody.appendChild(rowPfEl);
          appendObjectionFlowNavRow("price");
        }

        cfClearFlowStack();
        renderPriceOptionsScreen();
      }

      function mountQualityObjectionFollowUp() {
        logWidgetFlow("quality_followup_ui", "quality_uncertainty", "open");
        logWidgetConversionFlow("quality", "open");
        persistSessionAbandonReason("quality_uncertainty", null);

        function pickQualityDisplayLines(maxN) {
          var items = getCartLineItems();
          if (!items || !items.length) {
            return [];
          }
          var n = typeof maxN === "number" ? maxN : 2;
          n = Math.min(Math.max(n, 1), 2);
          return items.slice(0, n);
        }

        function appendQualityFollowUpMsgParagraph(text) {
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-quality-followup-msg", "1");
          pOut.style.cssText =
            "margin:0 0 10px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          pOut.textContent = text;
          widgetBody.appendChild(pOut);
        }

        function appendQualityProductCard(line, opts) {
          if (!line || typeof line !== "object") {
            return;
          }
          var o = opts && typeof opts === "object" ? opts : {};
          var badgeAbove = o.badgeAbove;
          var caption = o.caption;
          var subtitleBelow = o.subtitleBelow;
          var footerNote = o.footerNote;

          if (badgeAbove != null && strTrim(String(badgeAbove)) !== "") {
            var bd = document.createElement("div");
            bd.setAttribute("data-cf-quality-product-badge", "1");
            bd.style.cssText =
              "font-size:12px;font-weight:700;color:#166534;margin:0 0 8px 0;padding:4px 10px;" +
              "background:#dcfce7;border-radius:6px;display:inline-block;";
            bd.textContent = String(badgeAbove);
            widgetBody.appendChild(bd);
          }

          var name = strTrim(line.name) || "منتج في سلتك";
          var pl = formatPriceRiyal(line);
          var box = document.createElement("div");
          box.setAttribute("data-cf-quality-conversion-product", "1");
          box.style.cssText =
            "margin:10px 0;padding:10px;border-radius:8px;background:rgba(124,58,237,.09);" +
            "font-size:13px;line-height:1.5;";
          if (caption != null && strTrim(String(caption)) !== "") {
            var cap = document.createElement("div");
            cap.style.cssText = "font-weight:700;margin-bottom:4px;";
            cap.textContent = String(caption);
            box.appendChild(cap);
          }
          var row = document.createElement("div");
          row.textContent = name + (pl ? " — " + pl : "");
          box.appendChild(row);
          if (subtitleBelow != null && strTrim(String(subtitleBelow)) !== "") {
            var sub = document.createElement("div");
            sub.setAttribute("data-cf-quality-product-subtitle", "1");
            sub.style.cssText =
              "font-size:12px;color:#475569;margin-top:8px;line-height:1.45;";
            sub.textContent = String(subtitleBelow);
            box.appendChild(sub);
          }
          if (footerNote != null && strTrim(String(footerNote)) !== "") {
            var fn = document.createElement("div");
            fn.setAttribute("data-cf-quality-product-foot", "1");
            fn.style.cssText =
              "font-size:12px;color:#92400e;margin-top:8px;font-weight:600;";
            fn.textContent = String(footerNote);
            box.appendChild(fn);
          }
          widgetBody.appendChild(box);
        }

        function appendQualityContinueCTA(optionKey) {
          var hint = document.createElement("p");
          hint.setAttribute("data-cf-quality-cta-hint", "1");
          hint.style.cssText =
            "margin:12px 0 6px 0;font-size:13px;line-height:1.45;color:#334155;";
          hint.textContent = "تقدر تكمل الطلب الآن بكل راحة 👍";
          widgetBody.appendChild(hint);

          var btn = document.createElement("button");
          btn.type = "button";
          btn.setAttribute("data-cf-quality-conversion-cta", "1");
          btn.textContent = "كمّل الطلب الآن 👇";
          stampPrimaryBubbleBtn(
            btn,
            "width:100%!important;margin-top:4px!important;font-size:15px!important;font-weight:700!important;padding:14px 18px!important;border-radius:10px!important;" +
              "box-shadow:0 2px 10px rgba(0,0,0,.22)!important;min-height:48px!important;"
          );
          btn.addEventListener("click", function (evCta) {
            evCta.stopPropagation();
            evCta.preventDefault();
            logWidgetConversionFlow(
              "quality",
              String(optionKey) + "_cta_continue"
            );
            scrollToCartOrCheckout();
          });
          widgetBody.appendChild(btn);
        }

        function mountQualityConversionStep(responseMsg, optionKey, extrasFn) {
          stripContentKeepChrome();
          cfSetNavStep("quality_results_" + String(optionKey));
          if (responseMsg && strTrim(responseMsg) !== "") {
            appendQualityFollowUpMsgParagraph(responseMsg);
          }
          if (typeof extrasFn === "function") {
            extrasFn();
          }
          appendQualityContinueCTA(optionKey);
          appendObjectionFlowNavRow("quality");
        }

        function renderQualityOptionsScreen() {
          stripContentKeepChrome();
          cfSetNavStep("quality_options");
          var introEl = document.createElement("p");
          introEl.setAttribute("data-cf-quality-followup-intro", "1");
          introEl.style.cssText =
            "margin:0 0 12px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          introEl.textContent =
            "واضح إن الجودة تهمك 👍\nخلني أأكد لك قبل ما تقرر:";

          var rowQ = document.createElement("div");
          rowQ.setAttribute("data-cf-quality-followup-buttons", "1");
          rowQ.style.cssText = rowStyleCol;

          function addQFBtn(label, onActivate) {
            var bx = document.createElement("button");
            bx.type = "button";
            bx.textContent = label;
            stampPrimaryBubbleBtn(bx);
            bx.addEventListener("click", function (ev) {
              ev.stopPropagation();
              ev.preventDefault();
              onActivate();
            });
            rowQ.appendChild(bx);
          }

          addQFBtn("هل عليه ضمان؟", function () {
            cfPushFlow(renderQualityOptionsScreen);
            logWidgetFlow(
              "quality_followup_pick",
              "quality_uncertainty",
              "ضمان"
            );
            logWidgetConversionFlow("quality", "ضمان");
            mountQualityConversionStep(
              "هذا المنتج عليه ضمان واضح 👍\nوهو من الخيارات اللي كثير يختارونها بدون تردد 👌",
              "ضمان",
              function () {
                var lines = pickQualityDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendQualityProductCard(lines[j], {
                    badgeAbove: "✔️ ضمان متوفر",
                  });
                }
                if (!lines.length) {
                  appendQualityFollowUpMsgParagraph(
                    "أضف المنتج للسلة لتشوف التفاصيل وتكمّل الطلب."
                  );
                }
              }
            );
          });

          addQFBtn("كيف جودته مقارنة بغيره؟", function () {
            cfPushFlow(renderQualityOptionsScreen);
            logWidgetFlow(
              "quality_followup_pick",
              "quality_uncertainty",
              "مقارنة"
            );
            logWidgetConversionFlow("quality", "مقارنة");
            mountQualityConversionStep(
              "هذا من الخيارات اللي يعتمد عليها 👍\nومناسب للاستخدام اليومي بدون مشاكل 👌\nوكثير من العملاء يستخدمونه لنفس الغرض",
              "مقارنة",
              function () {
                var lines = pickQualityDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendQualityProductCard(lines[j], {
                    subtitleBelow: "خيار موثوق للاستخدام اليومي",
                  });
                }
                if (!lines.length) {
                  appendQualityFollowUpMsgParagraph(
                    "أضف منتجاً للسلة لمقارنة الخيارات وتكمّل الطلب."
                  );
                }
              }
            );
          });

          addQFBtn("هل فيه تقييمات؟", function () {
            cfPushFlow(renderQualityOptionsScreen);
            logWidgetFlow(
              "quality_followup_pick",
              "quality_uncertainty",
              "تقييمات"
            );
            logWidgetConversionFlow("quality", "تقييمات");
            mountQualityConversionStep(
              "عليه تقييمات إيجابية 👍\nوكثير من العملاء يرجعون يطلبونه مرة ثانية 👌",
              "تقييمات",
              function () {
                var lines = pickQualityDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendQualityProductCard(lines[j], {
                    footerNote: "⭐ تقييمات إيجابية",
                  });
                }
                if (!lines.length) {
                  appendQualityFollowUpMsgParagraph(
                    "افتح صفحة المنتج للتقييمات ثم ارجع وتكمّل من السلة."
                  );
                }
              }
            );
          });

          widgetBody.appendChild(introEl);
          widgetBody.appendChild(rowQ);
          appendObjectionFlowNavRow("quality");
        }

        cfClearFlowStack();
        renderQualityOptionsScreen();
      }

      function mountShippingObjectionFollowUp() {
        logWidgetFlow("shipping_followup_ui", "shipping_cost", "open");
        logWidgetConversionFlow("shipping_cost", "open");
        persistSessionAbandonReason("shipping_cost", null);

        function cartLineNumericPrice(line) {
          if (!line || typeof line !== "object") {
            return null;
          }
          var p = line.price;
          if (typeof p === "number" && isFinite(p)) {
            return p;
          }
          if (p == null || strTrim(String(p)) === "") {
            return null;
          }
          var m = String(p).replace(/[^\d.,]/g, "").replace(/,/g, ".");
          var n = parseFloat(m);
          return isFinite(n) ? n : null;
        }

        function pickLowestPriceCartLine(items) {
          if (!items || !items.length) {
            return null;
          }
          var best = null;
          var bestP = Infinity;
          var i;
          for (i = 0; i < items.length; i++) {
            var pn = cartLineNumericPrice(items[i]);
            if (pn != null && pn < bestP) {
              bestP = pn;
              best = items[i];
            }
          }
          if (best != null) {
            return best;
          }
          return items[0];
        }

        function getOptionalMerchantShippingOfferText() {
          try {
            var w = window.CARTFLOW_SHIPPING_OFFER_TEXT;
            if (w != null && strTrim(String(w)) !== "") {
              return firstLineOrClip(String(w), 400);
            }
          } catch (eSo) {
            /* ignore */
          }
          var ctx = buildProductContext();
          var sh = ctx.shipping;
          if (!sh) {
            return "";
          }
          var t = strTrim(sh);
          if (
            /عرض|مجاني|خصم|%|توصيل مجاني|شحن مجاني|مجّاني/i.test(t)
          ) {
            return firstLineOrClip(t, 280);
          }
          return "";
        }

        function appendShippingFollowUpMsgParagraph(text) {
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-shipping-followup-msg", "1");
          pOut.style.cssText =
            "margin:0 0 10px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          pOut.textContent = text;
          widgetBody.appendChild(pOut);
        }

        function appendShippingConversionProductCard(line, caption) {
          if (!line || typeof line !== "object") {
            return;
          }
          var name = strTrim(line.name) || "منتج في سلتك";
          var pl = formatPriceRiyal(line);
          var box = document.createElement("div");
          box.setAttribute("data-cf-shipping-conversion-product", "1");
          box.style.cssText =
            "margin:10px 0;padding:10px;border-radius:8px;background:rgba(124,58,237,.09);" +
            "font-size:13px;line-height:1.5;";
          if (caption && strTrim(caption) !== "") {
            var cap = document.createElement("div");
            cap.style.cssText = "font-weight:700;margin-bottom:4px;";
            cap.textContent = caption;
            box.appendChild(cap);
          }
          var row = document.createElement("div");
          row.textContent = name + (pl ? " — " + pl : "");
          box.appendChild(row);
          widgetBody.appendChild(box);
        }

        function appendShippingContinuePurchaseCTA(optionKey) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.setAttribute("data-cf-shipping-conversion-cta", "1");
          btn.textContent = "كمّل الطلب والدفع 👇";
          stampPrimaryBubbleBtn(btn);
          btn.addEventListener("click", function (evCta) {
            evCta.stopPropagation();
            evCta.preventDefault();
            logWidgetConversionFlow(
              "shipping_cost",
              String(optionKey) + "_cta_continue"
            );
            scrollToCartOrCheckout();
          });
          widgetBody.appendChild(btn);
        }

        function mountShippingConversionAnswer(responseMsg, optionKey, extrasFn) {
          stripContentKeepChrome();
          cfSetNavStep("shipping_results_" + String(optionKey));
          appendShippingFollowUpMsgParagraph(responseMsg);
          if (typeof extrasFn === "function") {
            extrasFn();
          }
          appendShippingContinuePurchaseCTA(optionKey);
          appendObjectionFlowNavRow("shipping");
        }

        function renderShippingOptionsScreen() {
          stripContentKeepChrome();
          cfSetNavStep("shipping_options");
          var introEl = document.createElement("p");
          introEl.setAttribute("data-cf-shipping-followup-intro", "1");
          introEl.style.cssText =
            "margin:0 0 12px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          introEl.textContent =
            "متفهم 👍 كثير يهتمون بتكلفة الشحن\nخلني أساعدك تختار الأنسب لك بسرعة:";

          var rowSEl = document.createElement("div");
          rowSEl.setAttribute("data-cf-shipping-followup-buttons", "1");
          rowSEl.style.cssText = rowStyleCol;

          function addSFBtn(label, onActivate) {
            var bx = document.createElement("button");
            bx.type = "button";
            bx.textContent = label;
            stampPrimaryBubbleBtn(bx);
            bx.addEventListener("click", function (ev) {
              ev.stopPropagation();
              ev.preventDefault();
              onActivate();
            });
            rowSEl.appendChild(bx);
          }

          addSFBtn("أبغى أقل تكلفة الآن", function () {
            cfPushFlow(renderShippingOptionsScreen);
            logWidgetFlow("shipping_followup_pick", "shipping_cost", "اقل_تكلفة");
            logWidgetConversionFlow("shipping_cost", "اقل_تكلفة");
            mountShippingConversionAnswer(
              "تمام 👍 خلني أرشح لك خيار قريب بسعر أقل 👇",
              "اقل_تكلفة",
              function () {
                var items = getCartLineItems();
                var low = pickLowestPriceCartLine(items);
                if (low) {
                  appendShippingConversionProductCard(
                    low,
                    "مناسب لأقل تكلفة ضمن سلتك"
                  );
                } else {
                  appendShippingFollowUpMsgParagraph(
                    "كمّل من السلة أو الدفع لمقارنة الخيارات وتقليل التكلفة قدر الإمكان."
                  );
                }
              }
            );
          });

          addSFBtn("أبغى أسرع توصيل", function () {
            cfPushFlow(renderShippingOptionsScreen);
            logWidgetFlow("shipping_followup_pick", "shipping_cost", "اسرع_توصيل");
            logWidgetConversionFlow("shipping_cost", "اسرع_توصيل");
            mountShippingConversionAnswer(
              "تمام 👍 هذا الخيار يساعدك تكمل الطلب بأسرع طريقة ممكنة 👇",
              "اسرع_توصيل",
              function () {
                var ctx = buildProductContext();
                var line = ctx.line;
                if (line) {
                  appendShippingConversionProductCard(line, "منتجك الحالي في السلة");
                }
                appendShippingFollowUpMsgParagraph(
                  "خطوة الدفع تعرض مدد الشحن المتاحة بحسب عنوانك 👍"
                );
              }
            );
          });

          addSFBtn("عندكم عرض شحن؟", function () {
            cfPushFlow(renderShippingOptionsScreen);
            logWidgetFlow("shipping_followup_pick", "shipping_cost", "عرض_شحن");
            logWidgetConversionFlow("shipping_cost", "عرض_شحن");
            var offer = getOptionalMerchantShippingOfferText();
            mountShippingConversionAnswer(
              "أحيانًا فيه عروض أو خيارات أوفر 👌 خلني أساعدك تشوف الأنسب 👇",
              "عرض_شحن",
              function () {
                if (offer) {
                  appendShippingFollowUpMsgParagraph("📦 " + offer);
                } else {
                  appendShippingFollowUpMsgParagraph(
                    "غالبًا تظهر عروض الشحن أو الخيارات الأوفر حسب عنوانك عند الدفع؛ كمّل الطلب لتمرّ على خطوة الشحن وتختار الأنسب."
                  );
                }
                var ctx = buildProductContext();
                if (ctx.line) {
                  appendShippingConversionProductCard(ctx.line, "تابع مع هذا الطلب");
                }
              }
            );
          });

          widgetBody.appendChild(introEl);
          widgetBody.appendChild(rowSEl);
          appendObjectionFlowNavRow("shipping");
        }

        cfClearFlowStack();
        renderShippingOptionsScreen();
      }

      function mountDeliveryObjectionFollowUp() {
        logWidgetFlow("delivery_followup_ui", "delivery_time", "open");
        logWidgetConversionFlow("delivery", "open");
        persistSessionAbandonReason("delivery_time", null);

        function pickDeliveryDisplayLines(maxN) {
          var items = getCartLineItems();
          if (!items || !items.length) {
            return [];
          }
          var n = typeof maxN === "number" ? maxN : 2;
          n = Math.min(Math.max(n, 1), 2);
          return items.slice(0, n);
        }

        function appendDeliveryFollowUpMsgParagraph(text) {
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-delivery-followup-msg", "1");
          pOut.style.cssText =
            "margin:0 0 10px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          pOut.textContent = text;
          widgetBody.appendChild(pOut);
        }

        function appendDeliveryConversionProductCard(line, caption, subtitleBelow) {
          if (!line || typeof line !== "object") {
            return;
          }
          var name = strTrim(line.name) || "منتج في سلتك";
          var pl = formatPriceRiyal(line);
          var box = document.createElement("div");
          box.setAttribute("data-cf-delivery-conversion-product", "1");
          box.style.cssText =
            "margin:10px 0;padding:10px;border-radius:8px;background:rgba(124,58,237,.09);" +
            "font-size:13px;line-height:1.5;";
          if (caption != null && strTrim(String(caption)) !== "") {
            var cap = document.createElement("div");
            cap.style.cssText = "font-weight:700;margin-bottom:4px;";
            cap.textContent = String(caption);
            box.appendChild(cap);
          }
          var row = document.createElement("div");
          row.textContent = name + (pl ? " — " + pl : "");
          box.appendChild(row);
          if (subtitleBelow != null && strTrim(String(subtitleBelow)) !== "") {
            var sub = document.createElement("div");
            sub.setAttribute("data-cf-delivery-product-subtitle", "1");
            sub.style.cssText =
              "font-size:12px;color:#475569;margin-top:8px;line-height:1.45;";
            sub.textContent = String(subtitleBelow);
            box.appendChild(sub);
          }
          widgetBody.appendChild(box);
        }

        function appendDeliveryContinuePurchaseCTA(optionKey) {
          var btn = document.createElement("button");
          btn.type = "button";
          btn.setAttribute("data-cf-delivery-conversion-cta", "1");
          btn.textContent = "كمّل الطلب الآن 👇";
          stampPrimaryBubbleBtn(btn);
          btn.addEventListener("click", function (evCta) {
            evCta.stopPropagation();
            evCta.preventDefault();
            logWidgetConversionFlow(
              "delivery",
              String(optionKey) + "_cta_continue"
            );
            scrollToCartOrCheckout();
          });
          widgetBody.appendChild(btn);
        }

        function mountDeliveryConversionStep(responseMsg, optionKey, extrasFn) {
          stripContentKeepChrome();
          cfSetNavStep("delivery_results_" + String(optionKey));
          if (responseMsg && strTrim(responseMsg) !== "") {
            appendDeliveryFollowUpMsgParagraph(responseMsg);
          }
          if (typeof extrasFn === "function") {
            extrasFn();
          }
          appendDeliveryContinuePurchaseCTA(optionKey);
          appendObjectionFlowNavRow("delivery");
        }

        function renderDeliveryOptionsScreen() {
          stripContentKeepChrome();
          cfSetNavStep("delivery_options");
          var intro = document.createElement("p");
          intro.setAttribute("data-cf-delivery-followup-intro", "1");
          intro.style.cssText =
            "margin:0 0 12px 0;font-size:14px;line-height:1.55;white-space:pre-line;";
          intro.textContent =
            "اتفق معك إن وقت التوصيل يهم 👍\nخلني أساعدك تختار الأنسب لك:";

          var rowD = document.createElement("div");
          rowD.setAttribute("data-cf-delivery-followup-buttons", "1");
          rowD.style.cssText = rowStyleCol;

          function addDFBtn(label, onActivate) {
            var bx = document.createElement("button");
            bx.type = "button";
            bx.textContent = label;
            stampPrimaryBubbleBtn(bx);
            bx.addEventListener("click", function (ev) {
              ev.stopPropagation();
              ev.preventDefault();
              onActivate();
            });
            rowD.appendChild(bx);
          }

          addDFBtn("أبغى توصله بسرعة", function () {
            cfPushFlow(renderDeliveryOptionsScreen);
            logWidgetFlow(
              "delivery_followup_pick",
              "delivery_time",
              "توصله_بسرعة"
            );
            logWidgetConversionFlow("delivery", "توصله_بسرعة");
            mountDeliveryConversionStep(
              "إذا كنت تحتاجه بسرعة 👍\nخلني أساعدك تكمل بأقرب خيار مناسب 👇",
              "توصله_بسرعة",
              function () {
                var lines = pickDeliveryDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendDeliveryConversionProductCard(lines[j], "", "");
                }
                if (!lines.length) {
                  appendDeliveryFollowUpMsgParagraph(
                    "أضف المنتج للسلة لتكمّل الطلب وتختار الخيار الأنسب لك عند الدفع."
                  );
                }
              }
            );
          });

          addDFBtn("أبغى أوفر في الشحن", function () {
            cfPushFlow(renderDeliveryOptionsScreen);
            logWidgetFlow(
              "delivery_followup_pick",
              "delivery_time",
              "اوفر_شحن"
            );
            logWidgetConversionFlow("delivery", "اوفر_شحن");
            mountDeliveryConversionStep(
              "إذا تبي توفر في الشحن 👍\nخلني أساعدك تختار الخيار الأنسب بدون استعجال 👇",
              "اوفر_شحن",
              function () {
                var lines = pickDeliveryDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendDeliveryConversionProductCard(lines[j], "", "");
                }
                if (!lines.length) {
                  appendDeliveryFollowUpMsgParagraph(
                    "أضف المنتج للسلة لمقارنة خيارات الشحن وتكمّل الطلب براحة."
                  );
                }
              }
            );
          });

          addDFBtn("متى يوصل بالضبط؟", function () {
            cfPushFlow(renderDeliveryOptionsScreen);
            logWidgetFlow(
              "delivery_followup_pick",
              "delivery_time",
              "متى_يوصل"
            );
            logWidgetConversionFlow("delivery", "متى_يوصل");
            mountDeliveryConversionStep(
              "تقدر تشوف مدة التوصيل والرسوم قبل تأكيد الطلب مباشرة 👍",
              "متى_يوصل",
              function () {
                var lines = pickDeliveryDisplayLines(2);
                var j;
                for (j = 0; j < lines.length; j++) {
                  appendDeliveryConversionProductCard(lines[j], "", "");
                }
                if (!lines.length) {
                  appendDeliveryFollowUpMsgParagraph(
                    "أضف المنتج للسلة؛ تظهر لك مدة التوصيل والرسوم قبل تأكيد الطلب."
                  );
                }
              }
            );
          });

          widgetBody.appendChild(intro);
          widgetBody.appendChild(rowD);
          appendObjectionFlowNavRow("delivery");
        }

        cfClearFlowStack();
        renderDeliveryOptionsScreen();
      }

      function mountWarrantyObjectionFollowUp() {
        logWidgetFlow("warranty_followup_ui", "warranty", "open");
        persistSessionAbandonReason("warranty", null);
        stripContentKeepChrome();

        function replaceBodyWithSingleMessage(msg) {
          stripContentKeepChrome();
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-warranty-followup-msg", "1");
          pOut.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.55;";
          pOut.textContent = msg;
          widgetBody.appendChild(pOut);
          appendReturnToRecoveryChatButtonRow();
        }

        var intro = document.createElement("p");
        intro.setAttribute("data-cf-warranty-followup-intro", "1");
        intro.style.cssText = "margin:0 0 12px 0;font-size:14px;line-height:1.55;";
        intro.textContent =
          "الضمان يعطي راحة بال 👍 اختر واحدة وأوضّح لك أكثر قبل ما تقرر:";

        var rowW = document.createElement("div");
        rowW.setAttribute("data-cf-warranty-followup-buttons", "1");
        rowW.style.cssText = rowStyleCol;

        function addWFBtn(label, onActivate) {
          var bx = document.createElement("button");
          bx.type = "button";
          bx.textContent = label;
          stampPrimaryBubbleBtn(bx);
          bx.addEventListener("click", function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            onActivate();
          });
          rowW.appendChild(bx);
        }

        addWFBtn("كم مدة الضمان المعتادة؟", function () {
          logWidgetFlow("warranty_followup_pick", "warranty", "مدة_الضمان");
          replaceBodyWithSingleMessage(
            "تختلف حسب نوع المنتج والمتجر، وغالباً تُبيَّن وقت الشراء وبطاقة الضمان 👍"
          );
        });
        addWFBtn("وش يشمل الضمان ووش ما يغطيه؟", function () {
          logWidgetFlow("warranty_followup_pick", "warranty", "نطاق_التغطية");
          replaceBodyWithSingleMessage(
            "عادة يغطّي عيوب التصنيع والأعطال غير المتوقعة ضمن الشروط المعلنة؛ استثناءات مثل سوء الاستخدام تُبيَّن سياسياً 👍."
          );
        });
        addWFBtn("وش أسوي عملياً لو احتجت لمطابقة ضمان لاحقاً؟", function () {
          logWidgetFlow("warranty_followup_pick", "warranty", "إجراءات_المطالبة");
          replaceBodyWithSingleMessage(
            "احفظ الإيصال وصور الوضع وبادر على خط الدعم المذكور عند المتجر؛ يختصر معالجة طلبك 👍."
          );
        });
        addWFBtn("رجوع للقائمة السابقة", function () {
          logWidgetFlow("warranty_followup_nav", "warranty", "رجوع_للقائمة");
          remountCartReasonChoicesFromFollowUp();
        });

        widgetBody.appendChild(intro);
        widgetBody.appendChild(rowW);
      }

      function mountOtherCustomReasonFlow() {
        logWidgetFlow("layer_d_other_ui", "other", "open");
        if (!(cartflowState.isVip === true)) {
          persistSessionAbandonReason("other", null);
        }
        stripContentKeepChrome();

        var intro = document.createElement("p");
        intro.setAttribute("data-cf-layer-d-other-intro", "1");
        intro.style.cssText = "margin:0 0 12px 0;font-size:14px;line-height:1.55;";
        intro.textContent =
          "تمام 👍 كيف نخدمك؟";

        var row = document.createElement("div");
        row.setAttribute("data-cf-layer-d-other-actions", "1");
        row.style.cssText = rowStyleCol;

        function addOBtn(label, onActivate) {
          var bx = document.createElement("button");
          bx.type = "button";
          bx.textContent = label;
          stampPrimaryBubbleBtn(bx);
          bx.addEventListener("click", function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            onActivate();
          });
          row.appendChild(bx);
        }

        addOBtn("عندي سؤال عن المنتج", function () {
          logWidgetFlow("layer_d_other_pick", "other", "سؤال_عن_المنتج");
          w._cfOnBackToEntry = function () {
            mountOtherCustomReasonFlow();
          };
          mountOtherForm();
        });
        addOBtn("أحتاج مساعدة بالطلب", function () {
          logWidgetFlow("layer_d_other_pick", "other", "مساعدة_بالطلب");
          stripContentKeepChrome();
          scrollToCartOrCheckout();
          var pOk = document.createElement("p");
          pOk.setAttribute("data-cf-layer-d-other-order-help", "1");
          pOk.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.55;";
          pOk.textContent =
            "تمام 👍 حاولنا نوصّلك لمنطقة السلة أو الدفع.";
          widgetBody.appendChild(pOk);
          appendReturnToRecoveryChatButtonRow();
        });
        addOBtn("رجوع للمحادثة", function () {
          logWidgetFlow("layer_d_other_nav", "other", "رجوع_للمحادثة");
          w._cfOnBackToEntry = null;
          renderReasonList();
        });
        addOBtn("رجوع للقائمة السابقة", function () {
          logWidgetFlow("layer_d_other_nav", "other", "رجوع_للقائمة");
          w._cfOnBackToEntry = null;
          remountCartReasonChoicesFromFollowUp();
        });

        widgetBody.appendChild(intro);
        widgetBody.appendChild(row);
      }

      /** VIP: بعد ‎POST /api/cartflow/reason‎ يُفتح جمع الرقم مباشرة دون رسالة وسيطة. */
      function vipPostCartflowReasonThenFollowup(
        reasonPayload,
        layerAbandonTag,
        layerAbandonCustom
      ) {
        postReason(reasonPayload)
          .then(function (j) {
            if (!(j && j.ok)) {
              return;
            }
            try {
              if (layerAbandonTag != null) {
                persistSessionAbandonReason(
                  layerAbandonTag,
                  layerAbandonCustom != null ? layerAbandonCustom : null
                );
              }
            } catch (ePs) {}
            mountVipInlinePhoneCapture();
          })
          .catch(function () {});
      }

      function vipMountLayerOtherBrief() {
        logWidgetFlow("layer_d_other_ui", "other", "vip_brief_open");
        stripContentKeepChrome();
        var introVx = document.createElement("p");
        introVx.setAttribute("data-cf-vip-other-brief", "1");
        introVx.style.cssText =
          "margin:0 0 12px 0;font-size:14px;line-height:1.55;";
        introVx.textContent =
          "تمام 👍 كيف نخدمك؟ اكتب سبب التردّد باختصار.";
        widgetBody.appendChild(introVx);

        var taVx = document.createElement("textarea");
        taVx.setAttribute("rows", "3");
        taVx.setAttribute("placeholder", "…");
        taVx.setAttribute("aria-label", "سبب التردّد باختصار");
        taVx.style.cssText =
          "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;color:#1e1b4b;resize:vertical;min-height:3.5em;";
        widgetBody.appendChild(taVx);

        var pVxErr = document.createElement("p");
        pVxErr.setAttribute("role", "alert");
        pVxErr.style.cssText =
          "margin:0 0 8px 0;font-size:13px;line-height:1.4;color:#b91c1c;min-height:0;";
        pVxErr.textContent = "";
        widgetBody.appendChild(pVxErr);

        var rowVxO = document.createElement("div");
        rowVxO.style.cssText = rowStyleCol;

        var bVxSend = document.createElement("button");
        bVxSend.type = "button";
        bVxSend.textContent = "متابعة";
        stampPrimaryBubbleBtn(bVxSend);

        var bVxBackO = document.createElement("button");
        bVxBackO.type = "button";
        bVxBackO.textContent = BTN_BACK;
        stampPrimaryBubbleBtn(bVxBackO);
        bVxBackO.addEventListener("click", function (ebo) {
          ebo.stopPropagation();
          ebo.preventDefault();
          remountCartReasonChoicesFromFollowUp();
        });

        bVxSend.addEventListener("click", function (eso) {
          eso.stopPropagation();
          eso.preventDefault();
          var noteVx = String(taVx.value || "").trim();
          if (!noteVx) {
            pVxErr.textContent = "يرجى كتابة الملاحظة";
            return;
          }
          pVxErr.textContent = "";
          bVxSend.setAttribute("disabled", "true");
          postReason({
            reason: "other",
            custom_text: noteVx,
          })
            .then(function (jvo) {
              bVxSend.removeAttribute("disabled");
              if (!(jvo && jvo.ok)) {
                pVxErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
                return;
              }
              try {
                persistSessionAbandonReason("other", noteVx);
              } catch (_) {}
              setReasonTag("other");
              emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
                reason: "other",
                sub_category: null,
              });
              mountVipInlinePhoneCapture();
            })
            .catch(function () {
              bVxSend.removeAttribute("disabled");
              pVxErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
            });
        });

        rowVxO.appendChild(bVxSend);
        rowVxO.appendChild(bVxBackO);
        widgetBody.appendChild(rowVxO);
      }

      function buildChoices() {
        while (wrap.firstChild) {
          wrap.removeChild(wrap.firstChild);
        }
        var hintHead = document.createElement("div");
        hintHead.setAttribute("data-cf-layer-d-hint", "1");
        hintHead.style.cssText =
          "font-weight:700;font-size:14px;margin:0 0 12px 0;line-height:1.45;";
        hintHead.textContent = "وش اللي مخليك متردد؟";
        var rowCh = document.createElement("div");
        rowCh.style.cssText =
          "display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-start;margin:0;padding:2px 0;" +
          "max-height:220px;overflow-y:auto;-webkit-overflow-scrolling:touch;overscroll-behavior:contain;";
        var layerOpts = cfLayerDChipsFromConfig();
        wrap.appendChild(hintHead);
        var idx;
        for (idx = 0; idx < layerOpts.length; idx++) {
          (function (opt) {
            var bChip = document.createElement("button");
            bChip.type = "button";
            bChip.textContent = opt.label;
            stampPrimaryBubbleBtn(bChip);
            bChip.addEventListener("click", function (e) {
              e.stopPropagation();
              e.preventDefault();
              logWidgetFlow(
                "layer_d_reason_pick",
                String(opt.tag),
                String(opt.label)
              );
              if (opt.tag === "no_help") {
                cartflowRejectHelp();
              } else if (cartflowState.isVip === true) {
                if (opt.tag === "_other") {
                  vipMountLayerOtherBrief();
                } else if (opt.tag === "price_high") {
                  vipPostCartflowReasonThenFollowup(
                    {
                      reason: "price",
                      sub_category: "price_budget_issue",
                    },
                    "price_high",
                    null
                  );
                } else if (opt.tag === "quality_uncertainty") {
                  vipPostCartflowReasonThenFollowup(
                    { reason: "quality" },
                    "quality_uncertainty",
                    null
                  );
                } else if (opt.tag === "shipping_cost") {
                  vipPostCartflowReasonThenFollowup(
                    { reason: "shipping" },
                    "shipping_cost",
                    null
                  );
                } else if (opt.tag === "delivery_time") {
                  vipPostCartflowReasonThenFollowup(
                    { reason: "thinking" },
                    "delivery_time",
                    null
                  );
                } else if (opt.tag === "warranty") {
                  vipPostCartflowReasonThenFollowup(
                    { reason: "warranty" },
                    "warranty",
                    null
                  );
                }
              } else if (opt.tag === "_other") {
                mountOtherCustomReasonFlow();
              } else if (opt.tag === "price_high") {
                mountPriceObjectionFollowUp();
              } else if (opt.tag === "quality_uncertainty") {
                mountQualityObjectionFollowUp();
              } else if (opt.tag === "shipping_cost") {
                mountShippingObjectionFollowUp();
              } else if (opt.tag === "delivery_time") {
                mountDeliveryObjectionFollowUp();
              } else if (opt.tag === "warranty") {
                mountWarrantyObjectionFollowUp();
              } else {
                persistSessionAbandonReason(opt.tag, null);
                showLayerDAckAfterPick(wrap);
              }
            });
            rowCh.appendChild(bChip);
          })(layerOpts[idx]);
        }
        wrap.appendChild(rowCh);
      }

      buildChoices();
      widgetBody.appendChild(wrap);
    }

    function vipRemountCartLayerDReasonChoicesFromFollowUp() {
      logWidgetFlow("reason_menu_back", "", "رجوع_للقائمة_السابقة");
      try {
        w.removeAttribute("data-cf-layer-d-no-help-active");
      } catch (eRmNoHelpFlg) {
        /* ignore */
      }
      stripContentKeepChrome();
      try {
        w.setAttribute("data-cf-cart-affirm-help", "1");
      } catch (eAff) {}
      mountLayerDAbandonIfEligible();
    }

    var vipImmediateUi = !!(revealOpts && revealOpts.vipImmediate);

    var p0 = null;
    var row0 = null;
    var btnY = null;
    var btnN = null;
    if (!vipImmediateUi) {
      (function cfMountMainEntry() {
        if (cfRuntimeConfig(true).phone_capture_mode === "immediate" && !cfCustomerPhoneSaved()) {
          var gP = document.createElement("p");
          gP.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.45;";
          gP.textContent = "أدخل رقم جوالك لمتابعة التواصل";
          var pin = document.createElement("input");
          pin.type = "tel";
          pin.setAttribute("dir", "ltr");
          pin.setAttribute("placeholder", "05xxxxxxxx");
          pin.setAttribute("autocomplete", "tel");
          pin.style.cssText =
            "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:10px;margin-bottom:8px;font:inherit;color:#1e1b4b;";
          var gErr = document.createElement("p");
          gErr.style.cssText =
            "margin:0 0 8px 0;font-size:13px;color:#b91c1c;min-height:1em;";
          var bGo = document.createElement("button");
          bGo.type = "button";
          bGo.textContent = "متابعة";
          stampPrimaryBubbleBtn(bGo);
          bGo.addEventListener("click", function (gev) {
            gev.stopPropagation();
            gev.preventDefault();
            gErr.textContent = "";
            var n = normalizeSaPhoneForCartflow(pin.value);
            if (!n) {
              gErr.textContent = "رقم غير صحيح";
              return;
            }
            try {
              localStorage.setItem(CARTFLOW_LS_CUSTOMER_PHONE, n);
            } catch (eLsIm) {
              /* ignore */
            }
            stripContentKeepChrome();
            cfMountMainEntry();
          });
          widgetBody.appendChild(gP);
          widgetBody.appendChild(pin);
          widgetBody.appendChild(gErr);
          widgetBody.appendChild(bGo);
          return;
        }
        p0 = document.createElement("p");
        p0.style.cssText =
          openSource === TRIGGER_SOURCE_EXIT_INTENT
            ? "margin:0 0 8px 0;font-size:14px;line-height:1.55;white-space:pre-line;"
            : "margin:0 0 8px 0;";
        p0.textContent =
          openSource === TRIGGER_SOURCE_EXIT_INTENT
            ? getExitIntentOpeningText()
            : "تبي أساعدك تكمل طلبك؟";

        if (
          openSource === TRIGGER_SOURCE_EXIT_INTENT ||
          openSource === TRIGGER_SOURCE_CART
        ) {
          row0 = document.createElement("div");
          row0.style.cssText =
            "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:2px;";

          btnY = document.createElement("button");
          btnY.type = "button";
          btnY.textContent =
            openSource === TRIGGER_SOURCE_EXIT_INTENT
              ? "نعم، خلني أشوف 👌"
              : "نعم";
          stampPrimaryBubbleBtn(btnY);

          btnN = document.createElement("button");
          btnN.type = "button";
          btnN.textContent =
            openSource === TRIGGER_SOURCE_EXIT_INTENT
              ? "لا، أتصفح بس"
              : "لا";
          stampPrimaryBubbleBtn(btnN);
          btnN.addEventListener("click", function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            if (isDemoStoreProductPage() && isDemoScenarioActive()) {
              return;
            }
            if (openSource === TRIGGER_SOURCE_EXIT_INTENT && !haveCartForWidget()) {
              logWidgetDiscoveryFlow("declined");
              persistExitIntentPreCartDeclined();
            }
            logWidgetFlow("first_prompt_pick", "", "لا");
            cfMaybeMarkDismissSuppress();
            removeFabIfAny();
            if (typeof w._cfCleanup === "function") {
              w._cfCleanup();
            }
            if (w && w.parentNode) {
              w.parentNode.removeChild(w);
            }
            if (isDemoStoreProductPage()) {
              shown = false;
              setCartflowWidgetShownFlag(false);
              demoStoreBubbleDismissed = true;
              clearTimeout(idleTimer);
              idleTimer = null;
            }
          });
        }
      })();
    }

    function getReasonActionOrder(rkey) {
      return CARTFLOW_REASON_ACTION_ORDER[rkey]
        ? CARTFLOW_REASON_ACTION_ORDER[rkey]
        : CARTFLOW_REASON_ACTION_ORDER.quality;
    }

    function appendReasonPersonalizationBlock(rkey) {
      var box = document.createElement("div");
      box.setAttribute("data-cf-reason-confirm", "1");
      box.setAttribute("aria-live", "polite");
      box.style.cssText =
        "margin:0 0 10px 0;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,.08);";
      var l1 = document.createElement("div");
      l1.style.cssText = "font-weight:700;font-size:13px;margin:0 0 6px 0;";
      l1.textContent = "✔ تم تسجيل سبب التردد";
      var l2 = document.createElement("p");
      l2.style.cssText = "margin:0;font-size:12px;line-height:1.5;opacity:0.92;";
      l2.textContent = CARTFLOW_REASON_PERSONALIZE_DEFAULT;
      box.appendChild(l1);
      box.appendChild(l2);
      widgetBody.appendChild(box);
    }

    function actionButtonText(rkey, flow, actionId) {
      var d = CARTFLOW_ACTIONS[actionId];
      if (!d) {
        return "…";
      }
      if (d.useFlowA1) {
        return (flow && flow.a1) ? flow.a1 : d.label;
      }
      if (d.useStaticLabel === "handoff") {
        return BTN_HANDOFF;
      }
      if (d.useStaticLabel === "back") {
        return BTN_BACK;
      }
      if (d.useStaticLabel === "return_to_cart") {
        return BTN_RETURN_CART;
      }
      if (d.label) {
        return d.label;
      }
      return "…";
    }

    function showDiscountStubPanel(rkey) {
      var def = CARTFLOW_ACTIONS.discount_offer;
      var msg = (def && def.discountMessage) || "";
      stripContentKeepChrome();
      var pex = document.createElement("p");
      pex.style.cssText = "margin:0 0 10px 0;font-size:14px;line-height:1.55;";
      pex.textContent = msg;
      widgetBody.appendChild(pex);
      var rowB = document.createElement("div");
      rowB.style.cssText = rowStyleCol;
      var bBack1 = document.createElement("button");
      bBack1.type = "button";
      bBack1.textContent = BTN_BACK;
      bBack1.setAttribute("aria-label", "رجوع لاستجابة المنتج");
      stampPrimaryBubbleBtn(bBack1);
      bBack1.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        mountProductAwareView(rkey);
      });
      rowB.appendChild(bBack1);
      widgetBody.appendChild(rowB);
    }

    function showAlternativesPanel(rkey, flow) {
      stripContentKeepChrome();
      var pex = document.createElement("p");
      pex.style.cssText = "margin:0 0 10px 0;font-size:14px;line-height:1.55;";
      pex.textContent = flow.explain;
      widgetBody.appendChild(pex);
      var rowB = document.createElement("div");
      rowB.style.cssText = rowStyleCol;
      var bBack1 = document.createElement("button");
      bBack1.type = "button";
      bBack1.textContent = BTN_BACK;
      bBack1.setAttribute("aria-label", "رجوع للعروض");
      stampPrimaryBubbleBtn(bBack1);
      bBack1.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        mountProductAwareView(rkey);
      });
      rowB.appendChild(bBack1);
      widgetBody.appendChild(rowB);
    }

    function mountProductAwareView(rkey) {
      var flow;
      if (rkey === "auto") {
        flow = {
          message:
            "نُخصّص رسالة المتابعة حسب أكثر أسباب التردد شيوعاً في متجرك (بيانات CartRecoveryReason).",
          explain:
            "يُستنتج السبب الأساسي من لوحة التحليلات؛ عند غياب البيانات يُستخدم تركيز السعر/الخصم.",
          a1: "تفاصيل",
        };
      } else {
        flow = getProductAwareCopy(rkey);
      }
      if (!flow) {
        return;
      }
      stripContentKeepChrome();
      if (rkey === "auto") {
        var phAuto = document.createElement("p");
        phAuto.style.cssText =
          "margin:0 0 10px 0;font-size:13px;line-height:1.5;opacity:0.95;";
        phAuto.textContent =
          "📊 وضع القرار التلقائي: يُقرأ السبب الأكثر تكراراً من لوحة CartFlow ثم تُبنى رسالة واتساب التجريبية.";
        widgetBody.appendChild(phAuto);
      } else {
        appendReasonPersonalizationBlock(rkey);
      }
      (function () {
        var payload = buildWhatsappGeneratePayload(rkey);
        var waReason = rkey === "auto" ? "" : rkey;
        var waSub =
          payload && payload.sub_category
            ? String(payload.sub_category).trim()
            : "";
        var strip = document.createElement("div");
        strip.setAttribute("data-cf-wa-mock-preview", "1");
        strip.setAttribute("aria-label", "معاينة واتساب تجريبية");
        strip.style.cssText =
          "margin:0 0 12px 0;padding:10px 10px;border-radius:10px;background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.12);";
        var previewBox = document.createElement("div");
        previewBox.setAttribute("data-cf-wa-preview", "1");
        var ht = document.createElement("div");
        ht.style.cssText = "font-weight:700;margin:0 0 8px 0;font-size:13px;";
        ht.textContent = "📱 نموذج رسالة واتساب جاهزة للإرسال";
        var msgEl = document.createElement("p");
        msgEl.style.cssText =
          "margin:0 0 10px 0;font-size:13px;line-height:1.55;opacity:0.95;white-space:pre-line;word-break:break-word;";
        msgEl.textContent = "…";
        previewBox.appendChild(ht);
        previewBox.appendChild(msgEl);
        var bMock = document.createElement("button");
        bMock.type = "button";
        bMock.textContent = "📤 إرسال عبر واتساب";
        bMock.setAttribute("data-cf-wa-mock-send", "1");
        bMock.setAttribute("aria-label", "فتح واتساب مع الرسالة المجهّزة");
        stampPrimaryBubbleBtn(bMock);
        bMock.setAttribute("disabled", "true");
        var generatedCore = null;
        var merchantE164 = null;
        var convFeedbackT1 = null;
        var convFeedbackT2 = null;
        var mockStatus = document.createElement("p");
        mockStatus.setAttribute("data-cf-wa-mock-status", "1");
        mockStatus.style.cssText =
          "margin:8px 0 0 0;font-size:12px;line-height:1.45;opacity:0.95;display:none;";
        var convHint = document.createElement("div");
        convHint.setAttribute("data-cf-wa-conversion-feedback", "1");
        convHint.setAttribute("aria-hidden", "true");
        convHint.style.cssText =
          "display:none;flex-direction:column;gap:4px;margin:8px 0 0 0;padding:6px 8px;border-radius:6px;border:1px solid rgba(34,197,94,0.35);background:rgba(34,197,94,0.08);";
        bMock.addEventListener("click", function (ev) {
          ev.stopPropagation();
          ev.preventDefault();
          if (!generatedCore) {
            return;
          }
          if (convFeedbackT1) {
            clearTimeout(convFeedbackT1);
            convFeedbackT1 = null;
          }
          if (convFeedbackT2) {
            clearTimeout(convFeedbackT2);
            convFeedbackT2 = null;
          }
          convHint.innerHTML = "";
          convHint.style.display = "none";
          function openWhatsappCompose(effectiveReason, effectiveSub) {
            var useApiCore =
              generatedCore &&
              String(generatedCore).trim() !== "" &&
              String(effectiveReason || "").trim() === "vip_neutral_followup";
            var finalMessage = useApiCore
              ? String(generatedCore)
              : buildWhatsappMessage({
                  reason: effectiveReason,
                  sub_category: effectiveSub,
                });
            var wurl = buildWaMeComposeUrl(finalMessage, merchantE164);
            try {
              window.open(wurl, "_blank", "noopener,noreferrer");
            } catch (e) {
              /* ignore */
            }
            try {
              console.log("whatsapp compose opened");
            } catch (e) {
              /* ignore */
            }
            mockStatus.textContent = "تم فتح واتساب لإرسال الرسالة ✅";
            mockStatus.style.display = "block";
            convFeedbackT1 = setTimeout(function () {
              if (!strip.isConnected) {
                return;
              }
              var p1 = document.createElement("p");
              p1.style.cssText =
                "margin:0;font-size:11.5px;line-height:1.4;color:#86efac;font-weight:600;";
              p1.textContent = "💰 تم استرجاع عميل محتمل";
              convHint.appendChild(p1);
              convHint.style.display = "flex";
              convFeedbackT2 = setTimeout(function () {
                if (!strip.isConnected) {
                  return;
                }
                var p2 = document.createElement("p");
                p2.style.cssText =
                  "margin:0;font-size:11.5px;line-height:1.4;color:#a7f3d0;opacity:0.95;font-weight:500;";
                p2.textContent = "🟢 العميل عاد إلى السلة";
                convHint.appendChild(p2);
              }, 1200);
            }, 1200);
          }
          var needDashboardReason =
            !waReason || waReason === "auto";
          if (needDashboardReason) {
            fetchDashboardPrimaryReasonFromApi(getStoreSlug())
              .then(function (pr) {
                try {
                  console.log("PRIMARY_REASON_FROM_DASHBOARD", pr);
                } catch (e) {
                  /* ignore */
                }
                openWhatsappCompose(pr, waSub);
              })
              .catch(function () {
                var fb = getPrimaryRecoveryReason(getStoreSlug());
                try {
                  console.log("PRIMARY_REASON_FROM_DASHBOARD", fb);
                } catch (e) {
                  /* ignore */
                }
                openWhatsappCompose(fb, waSub);
              });
          } else {
            openWhatsappCompose(waReason, waSub);
          }
        });
        previewBox.appendChild(bMock);
        previewBox.appendChild(mockStatus);
        previewBox.appendChild(convHint);
        strip.appendChild(previewBox);
        widgetBody.appendChild(strip);
        postGenerateWhatsappMessage(payload)
          .then(function (x) {
            if (x && x.j && x.j.ok && x.j.message) {
              generatedCore = String(x.j.message);
              if (x.j.resolved_reason) {
                waReason = String(x.j.resolved_reason);
              }
              if (x.j.resolved_sub_category !== undefined && x.j.resolved_sub_category !== null) {
                waSub = String(x.j.resolved_sub_category).trim();
              }
              var vipNeutralPrev =
                String(x.j.resolved_reason || "") === "vip_neutral_followup";
              if (vipNeutralPrev) {
                msgEl.textContent = String(generatedCore);
              } else {
                msgEl.textContent = buildWhatsappMessage({
                  reason: waReason,
                  sub_category: waSub,
                });
              }
              bMock.removeAttribute("disabled");
              if (
                x.j.merchant_whatsapp_e164 != null &&
                String(x.j.merchant_whatsapp_e164) !== ""
              ) {
                merchantE164 = String(x.j.merchant_whatsapp_e164);
              }
            } else {
              msgEl.textContent = "تعذر تجهيز رسالة واتساب التجريبية حالياً.";
            }
          })
          .catch(function () {
            msgEl.textContent = "تعذر تجهيز رسالة واتساب التجريبية حالياً.";
          });
      })();
      var p = document.createElement("p");
      p.style.cssText = "margin:0 0 10px 0;font-size:14px;line-height:1.55;";
      p.textContent = flow.message;
      widgetBody.appendChild(p);
      var rowA = document.createElement("div");
      rowA.style.cssText = rowStyleCol;
      var order = getReasonActionOrder(rkey);
      var k;
      for (k = 0; k < order.length; k++) {
        (function (actionId) {
          if (!CARTFLOW_ACTIONS[actionId]) {
            return;
          }
          var b = document.createElement("button");
          b.type = "button";
          b.textContent = actionButtonText(rkey, flow, actionId);
          stampPrimaryBubbleBtn(b);
          b.addEventListener("click", function (e) {
            e.stopPropagation();
            e.preventDefault();
            if (actionId === "alternatives") {
              showAlternativesPanel(rkey, flow);
            } else if (actionId === "discount_offer" && rkey === "price") {
              showDiscountStubPanel(rkey);
            } else if (actionId === "discount_offer") {
              return;
            } else if (actionId === "merchant_handoff") {
              handoffToMerchant(b);
            } else if (actionId === "back") {
              setReasonTag(null);
              renderReasonList();
            } else if (actionId === "return_to_cart") {
              scrollToCartOrCheckout();
            }
          });
          rowA.appendChild(b);
        })(order[k]);
      }
      widgetBody.appendChild(rowA);
    }

    function postPriceWithSubCategory(sub) {
      try {
        console.log("[REASON CLICKED]", {
          reason_key: "price",
          sub_category: sub,
          ui_updated_immediately: true,
        });
      } catch (eClk) {
        /* ignore */
      }
      var subWrap = widgetBody.querySelector("[data-cf-price-sub-ui]");
      if (subWrap) {
        var pb = subWrap.querySelectorAll("button");
        var pi;
        for (pi = 0; pi < pb.length; pi++) {
          pb[pi].setAttribute("disabled", "true");
          pb[pi].style.opacity = "0.55";
        }
      }
      stripContentKeepChrome();

      function removeLd() {
        var x = widgetBody.querySelector("[data-cf-reason-loading]");
        if (x && x.parentNode) {
          x.parentNode.removeChild(x);
        }
      }

      if (cfDeferAfterReasonPhoneCapture()) {
        cfBeginAfterReasonDeferredPhone(
          "price",
          { reason: "price", sub_category: sub },
          { sub_category: sub }
        );
        return;
      }

      function onFailPrice() {
        removeLd();
        try {
          console.log("[REASON SAVE FAILED]", { reason_key: "price" });
        } catch (eF) {}
        var pe = document.createElement("p");
        pe.style.cssText = "color:#b91c1c;font-size:13px;margin:0 0 8px 0;";
        pe.textContent = "تعذّر حفظ السبب. حاول مرة ثانية.";
        widgetBody.appendChild(pe);
        var br = document.createElement("button");
        br.type = "button";
        br.textContent = "رجوع للأسباب";
        stampPrimaryBubbleBtn(br);
        br.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          setReasonTag(null);
          setReasonSubTag(null);
          renderReasonList();
        });
        widgetBody.appendChild(br);
      }

      cfHandleReasonSelected(
        "price",
        { reason: "price", sub_category: sub },
        { sub_category: sub },
        {
          onSuccessUi: function () {
            removeLd();
          },
          onFailResponse: function () {
            onFailPrice();
          },
          onNetworkError: function () {
            onFailPrice();
          },
        }
      );
    }

    function showPriceSubMenu() {
      setReasonTag(null);
      setReasonSubTag(null);
      stripContentKeepChrome();
      var psub = document.createElement("p");
      psub.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.5;";
      psub.textContent = "وش يناسب وضعك بالنسبة للسعر؟";
      widgetBody.appendChild(psub);
      var rsub = document.createElement("div");
      rsub.setAttribute("data-cf-price-sub-ui", "1");
      rsub.style.cssText = rowStyleCol;
      CARTFLOW_PRICE_SUB_OPTIONS.forEach(function (o) {
        var bs = document.createElement("button");
        bs.type = "button";
        bs.textContent = o.label;
        stampPrimaryBubbleBtn(bs);
        (function (sub) {
          bs.addEventListener("click", function (e) {
            e.stopPropagation();
            e.preventDefault();
            postPriceWithSubCategory(sub);
          });
        })(o.sub);
        rsub.appendChild(bs);
      });
      var bPBack = document.createElement("button");
      bPBack.type = "button";
      bPBack.textContent = BTN_BACK;
      bPBack.setAttribute("aria-label", "رجوع لقائمة الأسباب");
      stampPrimaryBubbleBtn(bPBack);
      bPBack.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        setReasonTag(null);
        setReasonSubTag(null);
        renderReasonList();
      });
      rsub.appendChild(bPBack);
      widgetBody.appendChild(rsub);
    }

    function mountOtherForm() {
      stripContentKeepChrome();
      var rcPh = cfRuntimeConfig(true);
      var pcm = rcPh.phone_capture_mode;
      var hidePhone = pcm === "none";
      var phoneAfterReason = pcm === "after_reason";
      var showPhoneInline = pcm === "immediate";
      var pHint = document.createElement("p");
      pHint.style.cssText =
        "margin:0 0 8px 0;font-size:13px;line-height:1.45;color:rgba(30,27,75,0.82);";
      if (hidePhone) {
        pHint.textContent =
          "اكتب ملاحظتك وسنوصلها للمتجر (بدون رقم جوال داخل الودجيت).";
      } else if (phoneAfterReason) {
        pHint.textContent =
          "اكتب ملاحظتك أولاً؛ بعد حفظ السبب يمكنك إدخال رقم الجوال في نفس الودجيت إذا لزم.";
      } else {
        pHint.textContent = "نستخدم الرقم فقط لمساعدتك في إكمال الطلب";
      }
      widgetBody.appendChild(pHint);
      var phoneIn = null;
      if (showPhoneInline) {
        phoneIn = document.createElement("input");
        phoneIn.type = "tel";
        phoneIn.setAttribute("dir", "ltr");
        phoneIn.setAttribute("placeholder", "اكتب رقمك للتواصل عبر واتساب");
        phoneIn.setAttribute("autocomplete", "tel");
        phoneIn.setAttribute("aria-label", "اكتب رقمك للتواصل عبر واتساب");
        phoneIn.style.cssText =
          "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:10px 10px;margin-bottom:6px;font:inherit;color:#1e1b4b;";
        try {
          var savedP = localStorage.getItem(CARTFLOW_LS_CUSTOMER_PHONE);
          if (savedP) {
            phoneIn.value = String(savedP);
          }
        } catch (eLs0) {
          /* ignore */
        }
        widgetBody.appendChild(phoneIn);
      }
      var pErr = document.createElement("p");
      pErr.setAttribute("role", "alert");
      pErr.style.cssText =
        "margin:0 0 8px 0;font-size:13px;line-height:1.4;color:#b91c1c;min-height:0;";
      pErr.textContent = "";
      widgetBody.appendChild(pErr);
      var p2o = document.createElement("p");
      p2o.style.cssText =
        "margin:0 0 6px 0;font-size:12px;line-height:1.4;opacity:0.9;";
      p2o.textContent = hidePhone || phoneAfterReason ? "الملاحظة" : "ملاحظة (اختياري)";
      widgetBody.appendChild(p2o);
      var ta = document.createElement("textarea");
      ta.setAttribute("rows", "3");
      ta.setAttribute("placeholder", "…");
      ta.setAttribute("aria-label", "ملاحظة اختيارية مع سبب آخر");
      ta.style.cssText =
        "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;color:#1e1b4b;resize:vertical;min-height:3.5em;";
      widgetBody.appendChild(ta);
      var row2 = document.createElement("div");
      row2.style.cssText = rowStyleCol;
      var bSend = document.createElement("button");
      bSend.type = "button";
      bSend.textContent = "إرسال";
      stampPrimaryBubbleBtn(bSend);
      bSend.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        pErr.textContent = "";
        var note = (ta.value || "").trim();
        var norm = null;
        if (showPhoneInline && phoneIn) {
          norm = normalizeSaPhoneForCartflow(phoneIn.value);
          if (!norm) {
            pErr.textContent = "أدخل رقم جوال صحيح";
            return;
          }
        }
        if (!note) {
          pErr.textContent = "اكتب ملاحظة قصيرة";
          return;
        }
        try {
          console.log("[REASON CLICKED]", {
            reason_key: "other",
            ui_updated_immediately: true,
          });
        } catch (eClkO) {
          /* ignore */
        }
        var payload = { reason: "other", custom_text: note };
        if (norm) {
          payload.customer_phone = norm;
        }

        function removeLdO() {
          var x = row2.querySelector("[data-cf-reason-loading]");
          if (x && x.parentNode) {
            x.parentNode.removeChild(x);
          }
        }

        function reEnableRow() {
          bSend.removeAttribute("disabled");
          bHandoffO.removeAttribute("disabled");
          bBackO.removeAttribute("disabled");
        }

        if (cfDeferAfterReasonPhoneCapture()) {
          cfBeginAfterReasonDeferredPhone(
            "other",
            { reason: "other", custom_text: note },
            { custom_text: note }
          );
          return;
        }

        bSend.setAttribute("disabled", "true");
        bHandoffO.setAttribute("disabled", "true");
        bBackO.setAttribute("disabled", "true");

        cfHandleReasonSelected(
          "other",
          payload,
          { custom_text: note },
          {
            onSuccessUi: function () {
              removeLdO();
              if (norm) {
                try {
                  localStorage.setItem(CARTFLOW_LS_CUSTOMER_PHONE, norm);
                } catch (eLs1) {
                  /* ignore */
                }
                try {
                  console.log("[CF PHONE CAPTURED] phone=" + norm);
                } catch (eC) {
                  /* ignore */
                }
              }
            },
            onFailResponse: function (j) {
              reEnableRow();
              try {
                console.log("[REASON SAVE FAILED]", { reason_key: "other" });
              } catch (eFo) {}
              var eb = (j && j.body) || {};
              var em = (eb.error && String(eb.error)) || "";
              if (
                em.indexOf("invalid_customer_phone") !== -1 ||
                em === "invalid_customer_phone"
              ) {
                pErr.textContent = "رقم غير صحيح";
              } else {
                pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
              }
            },
            onNetworkError: function () {
              removeLdO();
              reEnableRow();
              try {
                console.log("[REASON SAVE FAILED]", { reason_key: "other" });
              } catch (eFc) {}
              pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
            },
          }
        );
      });
      var bHandoffO = document.createElement("button");
      bHandoffO.type = "button";
      bHandoffO.textContent = BTN_HANDOFF;
      stampPrimaryBubbleBtn(bHandoffO);
      bHandoffO.addEventListener("click", function (e3) {
        e3.stopPropagation();
        e3.preventDefault();
        handoffToMerchant(bHandoffO);
      });
      var bBackO = document.createElement("button");
      bBackO.type = "button";
      bBackO.textContent = BTN_BACK;
      stampPrimaryBubbleBtn(bBackO);
      bBackO.addEventListener("click", function (e4) {
        e4.stopPropagation();
        e4.preventDefault();
        if (typeof w._cfOnBackToEntry === "function") {
          w._cfOnBackToEntry();
        } else {
          renderReasonList();
        }
      });
      row2.appendChild(bSend);
      row2.appendChild(bHandoffO);
      row2.appendChild(bBackO);
      widgetBody.appendChild(row2);
    }

    function replayCartEntryPromptAfterVipInline() {
      try {
        w.removeAttribute("data-cf-vip-inline-flow");
        w.removeAttribute("data-cf-vip-inline-blocking");
        w.removeAttribute("data-cf-vip-inline-phone-step");
        w.removeAttribute("data-cf-after-reason-phone-step");
        w.removeAttribute("data-cf-yes");
      } catch (eRl) {}
      stripContentKeepChrome();
      if (p0 && row0 && btnY && btnN) {
        if (btnY.parentNode !== row0) {
          row0.appendChild(btnY);
        }
        if (btnN.parentNode !== row0) {
          row0.appendChild(btnN);
        }
        widgetBody.appendChild(p0);
        widgetBody.appendChild(row0);
      }
    }

    function mountVipInlinePhoneCapture() {
      stripContentKeepChrome();
      try {
        w.setAttribute("data-cf-vip-inline-phone-step", "1");
        w.setAttribute("data-cf-vip-inline-blocking", "1");
        w.setAttribute("data-cf-vip-inline-flow", "1");
      } catch (eAttr) {}

      var pHint = document.createElement("p");
      pHint.style.cssText =
        "margin:0 0 8px 0;font-size:13px;line-height:1.45;color:rgba(30,27,75,0.82);";
      pHint.textContent = "نستخدم الرقم فقط لمساعدتك في إكمال الطلب";
      widgetBody.appendChild(pHint);

      var phoneIn = document.createElement("input");
      phoneIn.type = "tel";
      phoneIn.setAttribute("dir", "ltr");
      phoneIn.setAttribute("placeholder", "اكتب رقمك للتواصل عبر واتساب");
      phoneIn.setAttribute("autocomplete", "tel");
      phoneIn.setAttribute("aria-label", "اكتب رقمك للتواصل عبر واتساب");
      phoneIn.style.cssText =
        "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:10px 10px;margin-bottom:6px;font:inherit;color:#1e1b4b;";
      try {
        var savedVp = localStorage.getItem(CARTFLOW_LS_CUSTOMER_PHONE);
        if (savedVp) {
          phoneIn.value = String(savedVp);
        }
      } catch (eLsV) {}

      widgetBody.appendChild(phoneIn);

      var pErr = document.createElement("p");
      pErr.setAttribute("role", "alert");
      pErr.style.cssText =
        "margin:0 0 8px 0;font-size:13px;line-height:1.4;color:#b91c1c;min-height:0;";
      pErr.textContent = "";
      widgetBody.appendChild(pErr);

      var rowV = document.createElement("div");
      rowV.style.cssText = rowStyleCol;

      var bSend = document.createElement("button");
      bSend.type = "button";
      bSend.textContent = "حفظ الرقم";
      stampPrimaryBubbleBtn(bSend);

      var bBackV = document.createElement("button");
      bBackV.type = "button";
      bBackV.textContent = BTN_BACK;
      stampPrimaryBubbleBtn(bBackV);
      bBackV.addEventListener("click", function (eb) {
        eb.stopPropagation();
        eb.preventDefault();
        try {
          w.removeAttribute("data-cf-vip-inline-phone-step");
        } catch (eBs) {}
        vipRemountCartLayerDReasonChoicesFromFollowUp();
      });

      bSend.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        pErr.textContent = "";
        var norm = normalizeSaPhoneForCartflow(phoneIn.value);
        if (!norm) {
          pErr.textContent = "رقم غير صحيح";
          return;
        }
        try {
          console.log("[CF PHONE RECEIVED] phone=" + norm);
        } catch (eCfR) {}

        bSend.setAttribute("disabled", "true");
        postReason({
          reason: "vip_phone_capture",
          customer_phone: norm,
          custom_text: "vip_cart_phone_capture",
        })
          .then(function (j) {
            bSend.removeAttribute("disabled");
            if (!(j && j.ok)) {
              var eb = (j && j.body) || {};
              var em = (eb.error && String(eb.error)) || "";
              if (
                em.indexOf("invalid_customer_phone") !== -1 ||
                em === "invalid_customer_phone"
              ) {
                pErr.textContent = "رقم غير صحيح";
              } else {
                pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
              }
              return;
            }
            try {
              localStorage.setItem(CARTFLOW_LS_CUSTOMER_PHONE, norm);
            } catch (eLs1) {
              /* ignore */
            }
            try {
              console.log("[CF PHONE SAVED] phone=" + norm);
            } catch (eCfS) {}

            stripContentKeepChrome();
            try {
              w.removeAttribute("data-cf-vip-inline-phone-step");
            } catch (eDone) {}

            var topOk = document.createElement("p");
            topOk.style.cssText =
              "margin:0 0 10px 0;font-size:15px;line-height:1.55;font-weight:600;";
            topOk.textContent = "تمام 👍 بنراجع طلبك ونرجع لك";
            widgetBody.appendChild(topOk);

            var rowOk = document.createElement("div");
            rowOk.style.cssText = rowStyleCol;
            var bChatV = document.createElement("button");
            bChatV.type = "button";
            bChatV.textContent = "رجوع للمحادثة";
            stampPrimaryBubbleBtn(bChatV);
            bChatV.addEventListener("click", function (e) {
              e.stopPropagation();
              e.preventDefault();
              replayCartEntryPromptAfterVipInline();
            });
            rowOk.appendChild(bChatV);
            widgetBody.appendChild(rowOk);
          })
          .catch(function () {
            bSend.removeAttribute("disabled");
            pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
          });
      });

      rowV.appendChild(bSend);
      rowV.appendChild(bBackV);
      widgetBody.appendChild(rowV);
    }

    function cfShowContinuation(reasonKey, subCategory) {
      mountNonVipPostPhoneContinuation(reasonKey, subCategory);
    }

    function cfBeginAfterReasonDeferredPhone(reasonKey, payload, detail) {
      detail = detail || {};
      var rk = String(reasonKey || "other").toLowerCase();
      try {
        console.log("[CF REASON SELECTED]", { reason_key: rk });
      } catch (eRs) {}
      var subNorm =
        detail.sub_category != null && String(detail.sub_category).trim() !== ""
          ? String(detail.sub_category).trim()
          : null;
      var customNorm =
        detail.custom_text != null && String(detail.custom_text).trim() !== ""
          ? String(detail.custom_text).trim()
          : null;
      cfRafPaint(function () {
        try {
          console.log("[CF PHONE SHOW IMMEDIATE]", { reason_key: rk });
        } catch (ePi) {}
        mountNonVipAfterReasonPhoneCaptureUI(
          rk,
          subNorm,
          customNorm,
          function () {
            cfShowContinuation(rk, subNorm);
          },
          { pendingReasonPayload: payload }
        );
      });
    }

    function cfShowPhoneCapture(reasonKey, detail) {
      detail = detail || {};
      var rk = String(reasonKey || "other").toLowerCase();
      var sub =
        detail.sub_category != null && String(detail.sub_category).trim() !== ""
          ? String(detail.sub_category).trim()
          : null;
      try {
        console.log("[CF PHONE SHOW]", { reason_key: rk });
      } catch (ePs) {}
      mountNonVipAfterReasonPhoneCaptureUI(
        rk,
        sub,
        detail.custom_text != null && String(detail.custom_text).trim() !== ""
          ? String(detail.custom_text).trim()
          : null,
        function () {
          cfShowContinuation(rk, sub);
        },
        {}
      );
    }

    function cfAfterReasonSaved(reasonKey, detail) {
      detail = detail || {};
      var rk = String(reasonKey || "other").toLowerCase();
      var subNorm =
        detail.sub_category != null && String(detail.sub_category).trim() !== ""
          ? String(detail.sub_category).trim()
          : null;
      var cfg = cfRuntimeConfig(true);
      var hasPhone = cfHasValidStoredPhone();

      if (cartflowState.isVip === true) {
        mountProductAwareView(rk);
        try {
          emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
            reason: rk,
            sub_category: subNorm,
          });
        } catch (eDgV) {}
        return;
      }

      if (cfg.phone_capture_mode === "after_reason" && !hasPhone) {
        cfShowPhoneCapture(rk, detail);
        return;
      }

      if (cfg.phone_capture_mode === "none" || hasPhone) {
        cfShowContinuation(rk, subNorm);
        return;
      }

      cfShowContinuation(rk, subNorm);
    }

    function cfHandleReasonSelected(reasonKey, payload, detail, callbacks) {
      callbacks = callbacks || {};
      detail = detail || {};
      var rk = String(reasonKey || "other").toLowerCase();
      cfRafPaint(function () {
        try {
          console.log("[REASON SAVE START]", { reason_key: rk });
        } catch (eSt0) {}
        postReason(payload)
          .then(function (j) {
            if (!cfCartflowReasonPostOk(j)) {
              if (typeof callbacks.onFailResponse === "function") {
                callbacks.onFailResponse(j);
              }
              return;
            }
            try {
              console.log("[REASON SAVE SUCCESS]", { reason_key: rk });
            } catch (eOk0) {}
            if (typeof callbacks.onSuccessUi === "function") {
              callbacks.onSuccessUi(j);
            }
            setReasonTag(rk);
            if (
              detail.sub_category != null &&
              String(detail.sub_category).trim() !== ""
            ) {
              setReasonSubTag(String(detail.sub_category).trim());
            } else {
              setReasonSubTag(null);
            }
            cfAfterReasonSaved(rk, detail);
          })
          .catch(function () {
            if (typeof callbacks.onNetworkError === "function") {
              callbacks.onNetworkError();
            }
          });
      });
    }

    function showOtherSuccessView() {
      stripContentKeepChrome();
      var top = document.createElement("p");
      top.style.cssText = "margin:0 0 10px 0;font-size:15px;line-height:1.55;font-weight:600;";
      top.textContent = "تمام 👍 تم استلام طلبك";
      widgetBody.appendChild(top);
      appendReasonPersonalizationBlock("other");
      var row = document.createElement("div");
      row.style.cssText = rowStyleCol;
      var bChat = document.createElement("button");
      bChat.type = "button";
      bChat.textContent = "رجوع للمحادثة";
      stampPrimaryBubbleBtn(bChat);
      bChat.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        if (typeof w._cfOnBackToEntry === "function") {
          w._cfOnBackToEntry();
        } else {
          renderReasonList();
        }
      });
      row.appendChild(bChat);
      widgetBody.appendChild(row);
    }



    function mountNonVipPostPhoneContinuation(reasonKey, subCategory) {
      var rk = String(reasonKey || "other").toLowerCase();
      stripContentKeepChrome();
      try {
        console.log("[CF CONTINUATION SHOW]", { reason_key: rk });
      } catch (ePcs) {
        /* ignore */
      }
      var msgs = {
        price:
          "أفهم 👍\nخلني أساعدك بخيار أنسب أو أوضح لك القيمة بشكل أفضل.",
        shipping:
          "واضح إن الشحن مهم لك 👍\nأقدر أوضح لك خيارات الشحن أو الأسرع للطلب.",
        delivery:
          "أكيد 👍\nخلني أوضح لك مدة التوصيل المتوقعة بشكل أدق.",
        quality:
          "أتفهم 👍\nأقدر أوضح لك الجودة والتفاصيل بشكل أفضل.",
        warranty:
          "أكيد 👍\nأوضح لك سياسة الضمان والاستبدال بكل بساطة.",
        thinking:
          "خذ وقتك 👍\nأقدر أقارن لك بين الخيارات أو أوضح اللي يهمك قبل لا تكمّل.",
        other:
          "تمام 👍\nأنا معك إذا احتجت أي توضيح قبل تكمل الطلب.",
      };
      var msg = msgs[rk] != null ? msgs[rk] : msgs.other;
      var pCont = document.createElement("p");
      pCont.style.cssText =
        "margin:0 0 16px 0;font-size:14px;line-height:1.65;white-space:pre-line;";
      pCont.textContent = msg;
      widgetBody.appendChild(pCont);
      var rowC = document.createElement("div");
      rowC.style.cssText = rowStyleCol;
      function addContBtn(label, fn) {
        var bx = document.createElement("button");
        bx.type = "button";
        bx.textContent = label;
        stampPrimaryBubbleBtn(bx);
        bx.addEventListener("click", function (ev) {
          ev.stopPropagation();
          ev.preventDefault();
          fn();
        });
        rowC.appendChild(bx);
      }
      addContBtn("أكمل الطلب", function () {
        scrollToCartOrCheckout();
      });
      addContBtn("أحتاج مساعدة الآن", function () {
        mountProductAwareView(rk);
      });
      addContBtn("رجوع للأسباب", function () {
        setReasonTag(null);
        setReasonSubTag(null);
        renderReasonList();
      });
      widgetBody.appendChild(rowC);
      try {
        emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
          reason: rk,
          sub_category:
            subCategory != null && String(subCategory).trim() !== ""
              ? String(subCategory).trim()
              : null,
        });
      } catch (eEm) {
        /* ignore */
      }
    }

    function mountNonVipAfterReasonPhoneCaptureUI(
      reasonKey,
      subCategory,
      customText,
      onDone,
      phoneCaptureOpts
    ) {
      phoneCaptureOpts = phoneCaptureOpts || {};
      var pendingReasonPayload = phoneCaptureOpts.pendingReasonPayload;
      onDone = typeof onDone === "function" ? onDone : function () {};
      var rkey = String(reasonKey || "").toLowerCase();
      var pcm = cfRuntimeConfig(true).phone_capture_mode;
      var hasPh = !!getCartflowStoredCustomerPhoneNorm();
      var willShowPhone =
        pcm === "after_reason" && cartflowState.isVip !== true && !hasPh;
      try {
        console.log("[PHONE CAPTURE CHECK]", {
          mode: pcm,
          reason_key: rkey,
          has_existing_phone: hasPh,
          should_show_phone_capture: willShowPhone,
        });
      } catch (eChk0) {
        /* ignore */
      }
      if (pcm !== "after_reason") {
        try {
          console.log("[PHONE CAPTURE SKIPPED]", {
            reason: "internal_capture_mode_guard",
            widget_phone_capture_mode: pcm,
          });
        } catch (eIg0) {
          /* ignore */
        }
        onDone();
        return;
      }
      if (cartflowState.isVip === true) {
        try {
          console.log("[PHONE CAPTURE SKIPPED]", { reason: "internal_vip_guard" });
        } catch (eIg1) {
          /* ignore */
        }
        onDone();
        return;
      }
      if (hasPh) {
        try {
          console.log("[PHONE CAPTURE SKIPPED]", {
            reason: "internal_already_has_valid_phone",
          });
        } catch (eIg2) {
          /* ignore */
        }
        onDone();
        return;
      }
      stripContentKeepChrome();
      try {
        w.setAttribute("data-cf-after-reason-phone-step", "1");
      } catch (eAt) {
        /* ignore */
      }
      var pTitle = document.createElement("p");
      pTitle.style.cssText =
        "margin:0 0 6px 0;font-size:16px;line-height:1.35;font-weight:700;";
      pTitle.textContent = "رقم الجوال لإكمال المتابعة";
      widgetBody.appendChild(pTitle);

      var pSub = document.createElement("p");
      pSub.style.cssText =
        "margin:0 0 10px 0;font-size:13px;line-height:1.45;color:rgba(30,27,75,0.82);";
      pSub.textContent = "نستخدمه فقط لمتابعة طلبك إذا احتجت مساعدة.";
      widgetBody.appendChild(pSub);

      var phoneIn = document.createElement("input");
      phoneIn.type = "tel";
      phoneIn.setAttribute("dir", "ltr");
      phoneIn.setAttribute("placeholder", "05xxxxxxxx");
      phoneIn.setAttribute("autocomplete", "tel");
      phoneIn.setAttribute("aria-label", "رقم الجوال للتواصل");
      phoneIn.style.cssText =
        "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:10px 10px;margin-bottom:6px;font:inherit;color:#1e1b4b;";
      widgetBody.appendChild(phoneIn);

      var pErr = document.createElement("p");
      pErr.setAttribute("role", "alert");
      pErr.style.cssText =
        "margin:0 0 8px 0;font-size:13px;line-height:1.4;color:#b91c1c;min-height:0;";
      pErr.textContent = "";
      widgetBody.appendChild(pErr);

      var rowB = document.createElement("div");
      rowB.style.cssText = rowStyleCol;

      var bSend = document.createElement("button");
      bSend.type = "button";
      bSend.textContent = "حفظ الرقم";
      stampPrimaryBubbleBtn(bSend);

      var bBackPh = document.createElement("button");
      bBackPh.type = "button";
      bBackPh.textContent = BTN_BACK;
      stampPrimaryBubbleBtn(bBackPh);
      bBackPh.addEventListener("click", function (eb) {
        eb.stopPropagation();
        eb.preventDefault();
        try {
          w.removeAttribute("data-cf-after-reason-phone-step");
        } catch (eBr) {
          /* ignore */
        }
        renderReasonList();
      });

      bSend.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        pErr.textContent = "";
        var norm = normalizeSaPhoneForCartflow(phoneIn.value);
        if (!norm) {
          pErr.textContent = "رقم غير صحيح";
          return;
        }
        bSend.setAttribute("disabled", "true");
        var body;
        if (pendingReasonPayload && typeof pendingReasonPayload === "object") {
          body = {};
          var pk;
          for (pk in pendingReasonPayload) {
            if (Object.prototype.hasOwnProperty.call(pendingReasonPayload, pk)) {
              body[pk] = pendingReasonPayload[pk];
            }
          }
          body.customer_phone = norm;
          if (body.reason == null || String(body.reason).trim() === "") {
            body.reason = rkey;
          }
        } else {
          body = { reason: rkey, customer_phone: norm };
          if (subCategory != null && String(subCategory).trim() !== "") {
            body.sub_category = String(subCategory).trim();
          }
          if (customText != null && String(customText).trim() !== "") {
            body.custom_text = String(customText).trim();
          }
        }
        if (
          pendingReasonPayload &&
          typeof pendingReasonPayload === "object"
        ) {
          if (
            subCategory != null &&
            String(subCategory).trim() !== "" &&
            body.sub_category == null
          ) {
            body.sub_category = String(subCategory).trim();
          }
          if (
            customText != null &&
            String(customText).trim() !== "" &&
            body.custom_text == null
          ) {
            body.custom_text = String(customText).trim();
          }
        }
        try {
          console.log("[CF REASON_PHONE_SAVE_START]", { reason_key: rkey });
        } catch (ePs0) {}
        postReason(body)
          .then(function (pj) {
            bSend.removeAttribute("disabled");
            if (!cfCartflowReasonPostOk(pj)) {
              try {
                console.log("[CF REASON_PHONE_SAVE_FAILED]", {
                  reason_key: rkey,
                  trace: "server_reject",
                });
              } catch (ePf) {}
              var eb = (pj && pj.body) || {};
              var em = (eb.error && String(eb.error)) || "";
              if (
                em.indexOf("invalid_customer_phone") !== -1 ||
                em === "invalid_customer_phone"
              ) {
                pErr.textContent = "رقم غير صحيح";
              } else {
                pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
              }
              return;
            }
            try {
              localStorage.setItem(CARTFLOW_LS_CUSTOMER_PHONE, norm);
            } catch (eLs1) {
              /* ignore */
            }
            var sid = getSessionId();
            var cid = cartLifecycleStableCartId();
            try {
              console.log("[CF REASON_PHONE_SAVE_SUCCESS]", {
                session_id: sid,
                cart_id: cid,
                reason_key: rkey,
              });
            } catch (eSv) {
              /* ignore */
            }
            try {
              w.removeAttribute("data-cf-after-reason-phone-step");
            } catch (eRm) {
              /* ignore */
            }
            if (
              pendingReasonPayload &&
              typeof pendingReasonPayload === "object"
            ) {
              setReasonTag(String(body.reason || rkey).toLowerCase());
              if (
                body.sub_category != null &&
                String(body.sub_category).trim() !== ""
              ) {
                setReasonSubTag(String(body.sub_category).trim());
              } else {
                setReasonSubTag(null);
              }
            }
            onDone();
          })
          .catch(function () {
            bSend.removeAttribute("disabled");
            try {
              console.log("[CF REASON_PHONE_SAVE_FAILED]", {
                reason_key: rkey,
                trace: "network",
              });
            } catch (ePn) {}
            pErr.textContent = "تعذّر الحفظ، حاول مرة ثانية.";
          });
      });

      rowB.appendChild(bSend);
      rowB.appendChild(bBackPh);
      widgetBody.appendChild(rowB);
    }

    function showStandardResponse(rkey) {
      try {
        console.log("[REASON CLICKED]", {
          reason_key: rkey,
          ui_updated_immediately: true,
        });
      } catch (eLc) {
        /* ignore */
      }
      var rowR = widgetBody.querySelector("[data-cf-reason-row]");
      if (rowR) {
        var btns = rowR.querySelectorAll("button");
        var bi;
        for (bi = 0; bi < btns.length; bi++) {
          btns[bi].setAttribute("disabled", "true");
          btns[bi].style.opacity = "0.55";
        }
      }
      stripContentKeepChrome();

      function removeLoading() {
        var x = widgetBody.querySelector("[data-cf-reason-loading]");
        if (x && x.parentNode) {
          x.parentNode.removeChild(x);
        }
      }

      if (cfDeferAfterReasonPhoneCapture()) {
        cfBeginAfterReasonDeferredPhone(rkey, { reason: rkey }, {});
        return;
      }

      function onFailStd() {
        removeLoading();
        try {
          console.log("[REASON SAVE FAILED]", { reason_key: rkey });
        } catch (eFs) {}
        var pe = document.createElement("p");
        pe.style.cssText = "color:#b91c1c;font-size:13px;margin:0 0 8px 0;";
        pe.textContent = "تعذّر حفظ السبب. حاول مرة ثانية.";
        widgetBody.appendChild(pe);
        var br = document.createElement("button");
        br.type = "button";
        br.textContent = "رجوع للأسباب";
        stampPrimaryBubbleBtn(br);
        br.addEventListener("click", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          renderReasonList();
        });
        widgetBody.appendChild(br);
      }

      cfHandleReasonSelected(
        rkey,
        { reason: rkey },
        {},
        {
          onSuccessUi: function () {
            removeLoading();
          },
          onFailResponse: function () {
            onFailStd();
          },
          onNetworkError: function () {
            onFailStd();
          },
        }
      );
    }

    function renderReasonList() {
      try {
        w.setAttribute("data-cf-reason-entry", "classic");
      } catch (eReEnt) {
        /* ignore */
      }
      w._cfOnBackToEntry = null;
      setReasonTag(null);
      stripContentKeepChrome();
      if (vipPhoneTryMountBubbleBlock(widgetBody)) {
        return;
      }
      var p2 = document.createElement("p");
      p2.style.cssText = "margin:0 0 8px 0;";
      p2.textContent = "وش أكثر شيء مخليك متردد؟ تبيني أساعدك";
      widgetBody.appendChild(p2);
      var row = document.createElement("div");
      row.setAttribute("data-cf-reason-row", "1");
      row.style.cssText =
        "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;max-height:220px;overflow-y:auto;" +
        "-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:2px 0;";

      var options = cfBuildVisibleReasonRows();
      if (!options.length) {
        var pEmpty = document.createElement("p");
        pEmpty.style.cssText = "margin:0;font-size:13px;opacity:0.9;";
        pEmpty.textContent = "لا توجد أسباب مفعّلة حالياً.";
        widgetBody.appendChild(pEmpty);
        return;
      }

      options.forEach(function (o) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = o.label;
        stampPrimaryBubbleBtn(b);
        b.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          if (o.r === "other") {
            mountOtherForm();
          } else if (o.r === "price") {
            showPriceSubMenu();
          } else {
            showStandardResponse(o.r);
          }
        });
        row.appendChild(b);
      });
      widgetBody.appendChild(row);
    }

    function renderBrowsingGeneralOptions() {
      w._cfOnBackToEntry = function () {
        renderBrowsingGeneralOptions();
      };
      setReasonTag(null);
      stripContentKeepChrome();
      var p2 = document.createElement("p");
      p2.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.5;";
      p2.textContent = "اختر وش يهمّك، أو تقدر تتواصل مباشرة مع المتجر";
      widgetBody.appendChild(p2);
      var row = document.createElement("div");
      row.style.cssText = rowStyleCol;
      var opts = [
        { label: "أبحث عن منتج", action: "products" },
        { label: "عندي سؤال", action: "question" },
        { label: "أريد عرض / خصم", action: "discount" },
        { label: "تحويل لصاحب المتجر", action: "handoff" }
      ];
      opts.forEach(function (o) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = o.label;
        stampPrimaryBubbleBtn(b);
        b.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          if (o.action === "products") {
            openProductDiscoveryMode();
            emitDemoGuideEvent("cartflow-demo-browsing-option", { option: "products" });
          } else if (o.action === "question") {
            mountOtherForm();
          } else if (o.action === "discount") {
            var defD = CARTFLOW_ACTIONS.discount_offer;
            var msgD =
              (defD && defD.discountMessage) ||
              "نقدر نرشّح لك عروضاً وخصومات عند التوفر — تقدر تكمل عبر واتساب مع المتجر.";
            stripContentKeepChrome();
            var pd = document.createElement("p");
            pd.style.cssText = "margin:0 0 10px 0;font-size:14px;line-height:1.55;";
            pd.textContent = msgD;
            widgetBody.appendChild(pd);
            var rB = document.createElement("div");
            rB.style.cssText = rowStyleCol;
            var bBackD = document.createElement("button");
            bBackD.type = "button";
            bBackD.textContent = BTN_BACK;
            stampPrimaryBubbleBtn(bBackD);
            bBackD.addEventListener("click", function (e2) {
              e2.stopPropagation();
              e2.preventDefault();
              renderBrowsingGeneralOptions();
            });
            rB.appendChild(bBackD);
            widgetBody.appendChild(rB);
            emitDemoGuideEvent("cartflow-demo-browsing-option", { option: "discount" });
          } else if (o.action === "handoff") {
            handoffToMerchant(b);
            emitDemoGuideEvent("cartflow-demo-browsing-option", { option: "handoff" });
          }
        });
        row.appendChild(b);
      });
      widgetBody.appendChild(row);
    }

    if (!vipImmediateUi) {
      if (btnY) {
        btnY.addEventListener("click", function (ev) {
          ev.stopPropagation();
          ev.preventDefault();
          if (w.getAttribute("data-cf-yes") === "1") {
            return;
          }
          w.setAttribute("data-cf-yes", "1");
          if (
            openSource === TRIGGER_SOURCE_EXIT_INTENT &&
            !haveCartForWidget()
          ) {
            if (shouldUseRecoveryReasonFlowAfterExitIntentYes()) {
              logWidgetFlow("first_prompt_pick", "", "نعم");
              stripContentKeepChrome();
              renderReasonList();
              emitDemoGuideEvent("cartflow-demo-reason-list-visible", {});
            } else {
              logWidgetDiscoveryFlow("accepted");
              renderExitIntentProductDiscovery();
              emitDemoGuideEvent("cartflow-demo-exit-discovery-visible", {});
            }
          } else if (openSource === TRIGGER_SOURCE_CART) {
            logWidgetFlow("first_prompt_pick", "", "نعم");
            stripContentKeepChrome();
            emitDemoGuideEvent("cartflow-demo-reason-list-visible", {});
            if (cartflowState.isVip === true) {
              w.setAttribute("data-cf-cart-affirm-help", "1");
              mountLayerDAbandonIfEligible();
              return;
            }
            w.setAttribute("data-cf-cart-affirm-help", "1");
            if (cfRuntimeConfig(true).phone_capture_mode === "after_reason") {
              renderReasonList();
            } else {
              mountLayerDAbandonIfEligible();
            }
          } else {
            renderReasonList();
            emitDemoGuideEvent("cartflow-demo-reason-list-visible", {});
          }
        }, false);
      }

      if (row0 && btnY && btnN) {
        row0.appendChild(btnY);
        row0.appendChild(btnN);
      }
      if (p0) {
        widgetBody.appendChild(p0);
      }
      mountLayerDAbandonIfEligible();
      if (row0) {
        widgetBody.appendChild(row0);
      }
    } else {
      try {
        w.setAttribute("data-cf-vip-immediate-open", "1");
      } catch (eVia) {}
      vipPhoneTryMountBubbleBlock(widgetBody);
    }
    try {
      window.cartflowDevMountProductViewAuto = function () {
        mountProductAwareView("auto");
      };
    } catch (e) {
      /* ignore */
    }
    document.body.appendChild(w);
    applyWidgetCustomization();
    emitDemoGuideEvent("cartflow-demo-bubble-visible", {});
  }

  function resetIdle() {
    if (isSessionConverted() || !step1Ready) {
      return;
    }
    if (isDemoStoreProductPage()) {
      if (!readDemoStoreWidgetArmed()) {
        return;
      }
      if (demoStoreBubbleDismissed) {
        return;
      }
    }
    if (shown) {
      return;
    }
    try {
      var trR = getCfWidgetTrigger();
      if (trR && trR.hesitation_trigger_enabled === false) {
        return;
      }
      if (trR) {
        var hcCart = String(trR.hesitation_condition || "").toLowerCase();
        if (hcCart === "after_cart_add" || hcCart === "cart_interaction") {
          clearTimeout(idleTimer);
          idleTimer = null;
          return;
        }
      }
    } catch (eHt) {
      /* ignore */
    }
    clearTimeout(idleTimer);
    idleTimer = null;
    if (!haveCartForWidget()) {
      return;
    }
    try {
      window._cartflowLastActivityTs = Date.now();
    } catch (eTs) {
      /* ignore */
    }
    var delayMs = getWidgetCartUiIdleMs();
    try {
      console.log("[CF FRONT] cart UI idle timer ms=", delayMs);
    } catch (eL) {
      /* ignore */
    }
    idleTimer = setTimeout(function () {
      idleTimer = null;
      var nowMs = Date.now();
      var lab =
        typeof window._cartflowLastActivityTs === "number"
          ? window._cartflowLastActivityTs
          : nowMs;
      var deltaMs = nowMs - lab;
      var shouldSend = haveCartForWidget();
      try {
        console.log("[CF FRONT] widget triggered by timer");
        console.log("HAS CART:", haveCartForWidget());
        console.log("LAST ACTIVITY:", lab);
        console.log("UI idle timer ms:", delayMs);
        console.log("TIME SINCE LAST ACTIVITY:", deltaMs);
        console.log("SHOULD SHOW WIDGET:", shouldSend);
      } catch (e2) {
        /* ignore */
      }
      if (!shouldSend) {
        return;
      }
      try {
        var trId = getCfWidgetTrigger();
        if (trId.suppress_after_widget_dismiss && cfReadDismissSuppressFlag()) {
          cfLogWidgetTriggerBlocked("closed_recently", "idle_timer");
          return;
        }
        if (trId.suppress_when_checkout_started && cfCheckoutPathActive()) {
          cfLogWidgetTriggerBlocked("checkout_started", "idle_timer");
          return;
        }
        if (!cfPageScopeAllowsCartUi()) {
          cfLogWidgetTriggerBlocked("page_scope_blocked", "idle_timer");
          return;
        }
        var hcond = String(trId.hesitation_condition || "").toLowerCase();
        if (hcond === "after_cart_add" || hcond === "cart_interaction") {
          var st = window.CartFlowState;
          if (!st || st.lastIntentAt == null) {
            return;
          }
          if (nowMs - st.lastIntentAt > 50 * 60 * 1000) {
            return;
          }
        }
      } catch (eGate) {
        /* ignore */
      }
      function finishIdleCartBubbleReveal() {
        showBubble(TRIGGER_SOURCE_CART, {
          mobileCartReveal: true,
          mobileDeferredRevealOk: true,
        });
        try {
          var widgetVisible = isWidgetDomVisible();
          console.log("widget visible:", widgetVisible);
        } catch (e) {
          /* ignore */
        }
      }
      if (!isMobileDeferCartBubbleViewport()) {
        finishIdleCartBubbleReveal();
        return;
      }
      var elapsedSec = mobileSecondsSinceLastAddToCartForGuard();
      var guardOk =
        elapsedSec === null ||
        elapsedSec >= MOBILE_POST_ADD_WIDGET_GUARD_MS / 1000;
      logMobileWidgetDelayGuard(elapsedSec, guardOk);
      if (elapsedSec !== null && elapsedSec < MOBILE_POST_ADD_WIDGET_GUARD_MS / 1000) {
        try {
          console.log("[BLOCK EARLY MOBILE WIDGET]");
          console.log("reason=too_soon_after_add_to_cart");
        } catch (eBlk) {
          /* ignore */
        }
        var lastAddTs = window._cartflowMobileLastAddToCartTs;
        var waitMs =
          typeof lastAddTs === "number" && isFinite(lastAddTs)
            ? MOBILE_POST_ADD_WIDGET_GUARD_MS - (nowMs - lastAddTs)
            : 0;
        if (waitMs > 0) {
          idleTimer = setTimeout(function () {
            idleTimer = null;
            if (!haveCartForWidget() || shown || isSessionConverted() || !step1Ready) {
              return;
            }
            if (isDemoStoreProductPage()) {
              if (!readDemoStoreWidgetArmed() || demoStoreBubbleDismissed) {
                return;
              }
            }
            var now2 = Date.now();
            var lab2 =
              typeof window._cartflowLastActivityTs === "number"
                ? window._cartflowLastActivityTs
                : now2;
            if (now2 - lab2 < delayMs) {
              return;
            }
            var elapsed2 = mobileSecondsSinceLastAddToCartForGuard();
            var guard2Ok =
              elapsed2 === null ||
              elapsed2 >= MOBILE_POST_ADD_WIDGET_GUARD_MS / 1000;
            logMobileWidgetDelayGuard(elapsed2, guard2Ok);
            if (elapsed2 !== null && elapsed2 < MOBILE_POST_ADD_WIDGET_GUARD_MS / 1000) {
              try {
                console.log("[BLOCK EARLY MOBILE WIDGET]");
                console.log("reason=too_soon_after_add_to_cart");
              } catch (eB2) {
                /* ignore */
              }
              return;
            }
            finishIdleCartBubbleReveal();
          }, waitMs);
        }
        return;
      }
      finishIdleCartBubbleReveal();
    }, delayMs);
  }

  function arm() {
    runArmBody();
  }

  var armFallbackTimer = null;
  var cartWidgetFallbackTimer = null;

  window.cartflowDemoArmStoreWidget = function () {
    try {
      window.sessionStorage.setItem(DEMO_STORE_WIDGET_ARMED_KEY, "1");
    } catch (e) {
      /* ignore */
    }
    demoStoreBubbleDismissed = false;
    try {
      console.log("widget armed");
    } catch (e) {
      /* ignore */
    }
    runArmBody();
    nudgeWidgetIdle();
    if (armFallbackTimer) {
      clearTimeout(armFallbackTimer);
      armFallbackTimer = null;
    }
    armFallbackTimer = setTimeout(function () {
      armFallbackTimer = null;
      if (isWidgetDomVisible()) {
        try {
          var wvCheck = isWidgetDomVisible();
          console.log("widget visible:", wvCheck);
        } catch (e) {
          /* ignore */
        }
        return;
      }
      if (!isDemoStoreProductPage() || !readDemoStoreWidgetArmed()) {
        return;
      }
      if (demoStoreBubbleDismissed || !haveCartForWidget() || isSessionConverted() || !step1Ready) {
        return;
      }
      try {
        console.log("widget triggered (arm fallback)");
      } catch (e) {
        /* ignore */
      }
      clearTimeout(idleTimer);
      idleTimer = null;
      if (!shown) {
        showBubble(TRIGGER_SOURCE_CART, { mobileCartReveal: true });
      } else {
        var hasDom =
          document.querySelector("[data-cartflow-bubble]") ||
          document.querySelector("[data-cartflow-fab]");
        if (!hasDom) {
          shown = false;
          setCartflowWidgetShownFlag(false);
          showBubble(TRIGGER_SOURCE_CART, { mobileCartReveal: true });
        }
      }
      try {
        var widgetVisible = isWidgetDomVisible();
        console.log("widget visible:", widgetVisible);
      } catch (e) {
        /* ignore */
      }
    }, 1800);
  };

  window.cartflowDemoDisarmStoreWidget = function () {
    if (isDemoScenarioActive()) {
      return;
    }
    try {
      window.sessionStorage.removeItem(DEMO_STORE_WIDGET_ARMED_KEY);
    } catch (e) {}
    clearDemoStoreExitIntentShown();
    clearDemoStoreExitPromptResolved();
    clearExitIntentPreCartDeclined();
    demoStoreBubbleDismissed = false;
    clearTimeout(idleTimer);
    idleTimer = null;
    if (cartSmartExitPollInterval !== null) {
      clearInterval(cartSmartExitPollInterval);
      cartSmartExitPollInterval = null;
    }
    removeFabIfAny();
    removeCartflowBubbleDom();
    shown = false;
    setCartflowWidgetShownFlag(false);
    detachArmListeners();
  };

  function ensureDemoStoreBubbleVisible() {
    if (!isDemoStoreProductPage()) {
      return;
    }
    if (!readDemoStoreWidgetArmed() && !isDemoScenarioActive()) {
      return;
    }
    if (demoStoreBubbleDismissed) {
      return;
    }
    if (!haveCartForWidget()) {
      return;
    }
    if (isSessionConverted() || !step1Ready) {
      return;
    }
    if (
      document.querySelector("[data-cartflow-bubble]") ||
      document.querySelector("[data-cartflow-fab]")
    ) {
      return;
    }
    shown = false;
    setCartflowWidgetShownFlag(false);
    try {
      var rcGu = cfRuntimeConfig(true);
      if (
        rcGu.hesitation_enabled &&
        (rcGu.hesitation_condition === "after_cart_add" ||
          rcGu.hesitation_condition === "cart_interaction") &&
        cfRuntimeTrigger.timer != null
      ) {
        try {
          console.log("[CF TIMER BLOCKED]", {
            gate: "demo_visibility_poll_deferred_anchor_active",
          });
        } catch (eGd) {}
        return;
      }
    } catch (eRc) {}
    showBubble(TRIGGER_SOURCE_CART);
  }

  /**
   * ‎/demo/store‎: خروج ذكي لزائر التصفّح (بدون شرط سلة) مرة لكل جلسة تخزين.
   * باقي صفحات السلة: يشترط وجود أصناف في السلة كسابق.
   * الـ FAB لا يعيق.
   */
  function canShowExitIntentWidget() {
    if (isSessionConverted()) {
      return false;
    }
    try {
      if (!getCfWidgetTrigger().exit_intent_enabled) {
        return false;
      }
      if (!cfExitIntentSurfaceAllowed()) {
        return false;
      }
    } catch (eCan) {
      return false;
    }
    if (haveCartForWidget()) {
      try {
        console.log("EXIT INTENT BLOCKED:", true);
      } catch (e0) {
        /* ignore */
      }
      return false;
    }
    if (readExitIntentPreCartDeclined()) {
      return false;
    }
    if (!isCartPage()) {
      return false;
    }
    if (isDemoStoreProductPage()) {
      if (demoStoreBubbleDismissed) {
        return false;
      }
      if (isWidgetDomVisible()) {
        return false;
      }
      return true;
    }
    if (document.querySelector("[data-cartflow-bubble]")) {
      return false;
    }
    return true;
  }

  /** تنفيذ فتح الفقاعة بعد التهيئة — لا يطبّق تأخير الإعداد؛ يستخدمه مسار الخروج فقط. */
  function cfExitIntentRevealNowAfterArm() {
    try {
      console.log("[CF EXIT INTENT FIRE]", { trace: "reveal_execute" });
    } catch (eFi) {}
    if (!canShowExitIntentWidget()) {
      try {
        console.log("[CF EXIT INTENT BLOCKED]", { gate: "recheck_failed" });
      } catch (eRb) {}
      return;
    }
    if (isDemoPath()) {
      if (!step1Ready) {
        step1Ready = true;
      }
    }
    if (isDemoStoreProductPage() && typeof window.cartflowDemoArmStoreWidget === "function") {
      window.cartflowDemoArmStoreWidget();
    } else {
      runArmBody();
    }
    clearTimeout(idleTimer);
    idleTimer = null;
    if (!canShowExitIntentWidget()) {
      try {
        console.log("[CF EXIT INTENT BLOCKED]", { gate: "post_arm_failed" });
      } catch (eRb2) {}
      return;
    }
    if (isDemoPath()) {
      showBubble(TRIGGER_SOURCE_EXIT_INTENT);
      return;
    }
    fetchReadyThen(function () {
      if (!canShowExitIntentWidget()) {
        try {
          console.log("[CF EXIT INTENT BLOCKED]", { gate: "after_ready_failed" });
        } catch (_) {}
        return;
      }
      showBubble(TRIGGER_SOURCE_EXIT_INTENT);
    });
  }

  /** نفس تسلسل التهيئة كما بعد add to cart، ثم showBubble(exit_intent) فقط. */
  function openExitIntentWidget(opts) {
    opts = opts || {};
    clearTimeout(cfExitIntentScheduledOpenTimer);
    cfExitIntentScheduledOpenTimer = null;

    try {
      if (!cfRuntimeConfig(true).exit_intent_enabled) {
        try {
          console.log("[CF EXIT INTENT BLOCKED]", { gate: "exit_disabled" });
        } catch (eEb) {}
        return;
      }
    } catch (_) {}

    if (!canShowExitIntentWidget()) {
      try {
        var trOp = getCfWidgetTrigger();
        if (!trOp.exit_intent_enabled) {
          cfLogWidgetTriggerBlocked("exit_intent_disabled", "open_exit");
        } else if (!haveCartForWidget() && !cfExitIntentSurfaceAllowed()) {
          cfLogWidgetTriggerBlocked("page_scope_blocked", "open_exit");
        }
        console.log("[CF EXIT INTENT BLOCKED]", { gate: "can_show_exit_false" });
      } catch (eOp) {
        /* ignore */
      }
      return;
    }

    if (opts.skipScheduledDelay !== true) {
      var xiDelaySec = cfRuntimeConfig(true).exit_intent_delay_seconds;
      var xiMs = Math.max(0, Math.min(60000, Math.floor(Number(xiDelaySec) || 0) * 1000));
      if (xiMs > 0) {
        try {
          console.log("[CF EXIT INTENT SCHEDULED]", {
            delay_ms: xiMs,
            sensor: opts.sensorType != null ? String(opts.sensorType) : "",
          });
        } catch (eSd) {}
        cfExitIntentScheduledOpenTimer = setTimeout(function () {
          cfExitIntentScheduledOpenTimer = null;
          openExitIntentWidget({ skipScheduledDelay: true, sensorType: opts.sensorType });
        }, xiMs);
        return;
      }
    }

    cfExitIntentRevealNowAfterArm();
  }

  function openCartflowWidgetFromTrigger(trigger, sensorType) {
    if (trigger !== "exit_intent") {
      return;
    }
    openExitIntentWidget(
      sensorType != null ? { sensorType: String(sensorType) } : {}
    );
  }

  function CartflowExitIntentController() {
    if (!isCartPage()) {
      return;
    }
    try {
      if (!getCfWidgetTrigger().exit_intent_enabled) {
        return;
      }
      if (!cfExitIntentSurfaceAllowed()) {
        return;
      }
    } catch (eCi) {
      return;
    }
    var triggered = false;
    var inactivityTimer = null;
    function canTrigger() {
      syncCartflowExitFlags();
      if (triggered) {
        return false;
      }
      if (window.cartflowWidgetVisible) {
        return false;
      }
      if (window.cartflowManualClosed) {
        return false;
      }
      if (isSessionConverted()) {
        return false;
      }
      if (haveCartForWidget()) {
        return false;
      }
      return canShowExitIntentWidget();
    }
    function fire(type) {
      if (!canTrigger()) {
        try {
          console.log("[CF EXIT INTENT BLOCKED]", {
            gate: "controller_suppressed_or_ineligible",
            type: type,
          });
        } catch (eBl) {}
        return;
      }
      triggered = true;
      try {
        console.log("[CF EXIT INTENT DETECTED]", { type: type });
      } catch (eCf) {
        /* ignore */
      }
      openCartflowWidgetFromTrigger("exit_intent", type);
    }
    function resetTimer() {
      if (inactivityTimer) {
        clearTimeout(inactivityTimer);
        inactivityTimer = null;
      }
      inactivityTimer = setTimeout(function () {
        inactivityTimer = null;
        fire("inactivity");
      }, cfExitIntentInactivityMs());
    }
    ["touchstart", "touchmove", "scroll", "mousemove", "keydown"].forEach(function (ev) {
      document.addEventListener(
        ev,
        function () {
          resetTimer();
        },
        { passive: true, capture: true }
      );
    });
    resetTimer();
    var lastY = getScrollYForExit();
    function onScroll() {
      resetTimer();
      var y = getScrollYForExit();
      if (lastY - y > cfExitIntentScrollDelta() && lastY > 300) {
        fire("scroll_up");
      }
      lastY = y;
    }
    window.addEventListener("scroll", onScroll, { passive: true, capture: true });
    document.addEventListener("scroll", onScroll, { passive: true, capture: true });
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") {
        fire("visibility_return");
      }
    });
    var root = document.documentElement;
    if (root) {
      root.addEventListener("mouseleave", function (e) {
        if (typeof e.clientY === "number" && e.clientY <= 0) {
          fire("mouse_leave");
        }
      });
    }
  }
  try {
    if (typeof window !== "undefined") {
      window.CartflowExitIntentController = CartflowExitIntentController;
    }
  } catch (e) {
    /* ignore */
  }

  if (isDemoStoreProductPage()) {
    setInterval(ensureDemoStoreBubbleVisible, 2500);
  }

  if (isDemoPath()) {
    document.addEventListener("cf-demo-cart-updated", function () {
      setTimeout(function () {
        runArmBody();
        maybeAttachCartSmartExitIntent();
        nudgeWidgetIdle();
        setTimeout(function () {
          try {
            if (haveCartForWidget() && step1Ready && !shown && !isSessionConverted()) {
              resetIdle();
            }
          } catch (eDefer) {
            /* ignore */
          }
        }, 60);
        if (cartWidgetFallbackTimer) {
          clearTimeout(cartWidgetFallbackTimer);
          cartWidgetFallbackTimer = null;
        }
        cartWidgetFallbackTimer = setTimeout(function () {
          cartWidgetFallbackTimer = null;
          if (!isDemoStoreProductPage()) {
            return;
          }
          if (!haveCartForWidget()) {
            return;
          }
          if (isWidgetDomVisible()) {
            return;
          }
          if (isSessionConverted() || !step1Ready) {
            return;
          }
          if (demoStoreBubbleDismissed) {
            return;
          }
          try {
            var trFb = getCfWidgetTrigger();
            var hcFb = String(trFb.hesitation_condition || "").toLowerCase();
            if (
              trFb.hesitation_trigger_enabled !== false &&
              (hcFb === "after_cart_add" || hcFb === "cart_interaction") &&
              (cfHesitationExpectedFireAtMs > 0 || cfHesitationAnchorTimer != null)
            ) {
              return;
            }
          } catch (eFb) {
            /* ignore */
          }
          if (!readDemoStoreWidgetArmed()) {
            runArmBody();
          }
          if (!readDemoStoreWidgetArmed()) {
            return;
          }
          try {
            console.log("widget triggered (cart fallback)");
          } catch (e) {
            /* ignore */
          }
          clearTimeout(idleTimer);
          idleTimer = null;
          if (!shown) {
            showBubble(TRIGGER_SOURCE_CART, { mobileCartReveal: true });
          } else {
            var d =
              document.querySelector("[data-cartflow-bubble]") ||
              document.querySelector("[data-cartflow-fab]");
            if (!d) {
              shown = false;
              setCartflowWidgetShownFlag(false);
              showBubble(TRIGGER_SOURCE_CART, { mobileCartReveal: true });
            }
          }
          try {
            var widgetVisible = isWidgetDomVisible();
            console.log("widget visible:", widgetVisible);
          } catch (e) {
            /* ignore */
          }
        }, 3000);
      }, 0);
    });
  }

  var cartflowInitialArmQueued = false;
  function cartflowBootstrapPublicConfigThenScheduleArm() {
    fetchPublicConfigForWidgetCustomization(function () {
      if (!cartflowInitialArmQueued) {
        cartflowInitialArmQueued = true;
        setTimeout(arm, ARM_DELAY_MS);
      }
    });
  }

  setTimeout(function () {
    cartflowBootstrapPublicConfigThenScheduleArm();
  }, 0);
  cfScheduleMerchantHeavyAfterLoadIdle(function () {
    try {
      prefetchDashboardPrimaryReason();
    } catch (ePf) {}
    try {
      cartflowInstallCartLifecycleObserver();
    } catch (eLc) {}
  });
})();

/**
 * Exit intent: guaranteed init (also when main bundle ran before document ready on /demo/store).
 * Uses window.CartflowExitIntentController from the main IIFE.
 */
(function () {
  try {
    console.log("EXIT ENGINE FORCE INIT");
    var c = function () {
      if (typeof window.CartflowExitIntentController === "function") {
        window.CartflowExitIntentController();
      } else {
        console.error("EXIT ENGINE: CartflowExitIntentController not on window");
      }
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        try {
          console.log("EXIT ENGINE INIT AFTER DOM");
          c();
        } catch (e) {
          console.error("EXIT ENGINE ERROR", e);
        }
      });
    } else {
      try {
        console.log("EXIT ENGINE INIT IMMEDIATE");
        c();
      } catch (e) {
        console.error("EXIT ENGINE ERROR", e);
      }
    }
  } catch (e) {
    console.error("EXIT ENGINE ERROR", e);
  }
})();
