/**
 * CartFlow — عرض سبب التردد بعد ‎step1‎ استرجاع (بلا مزوّد واتساب في الودجت).
 * ‎/demo/‎: يتخطّى انتظار ‎step1‎ (تجارب). باقي المسارات: حتى ‎GET /api/cartflow/ready‎.
 */
(function () {
  "use strict";

  window.CartFlowState =
    window.CartFlowState ||
    {
      hasCart: false,
      widgetShown: false,
      userRejectedHelp: false,
      rejectionTimestamp: null,
      lastIntentAt: null,
    };

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
  var shown = false;
  var idleTimer = null;
  var step1Ready = false;
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
    showBubble(TRIGGER_SOURCE_CART);
  }

  function maybeAttachCartSmartExitIntent() {
    if (cartSmartExitAttached) {
      return;
    }
    if (!isCartPage()) {
      return;
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
      try {
        console.log(
          "CARTFLOW RECOVERY:",
          "gates cleared on cart arm (suppress key + demo dismiss)"
        );
      } catch (eL) {
        /* ignore */
      }
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

  /** جاهزية الاسترجاع بعد إضافة للسلة أو جلسة جديدة (لا يعطّل المحادثة نهائياً) */
  function clearStaleRecoveryGatesOnCartActivity() {
    clearCartRecoverySuppressed();
    if (isDemoStoreProductPage() && isDemoPath()) {
      demoStoreBubbleDismissed = false;
    }
  }

  function haveCartForWidget() {
    if (isSessionConverted()) {
      return false;
    }
    try {
      if (typeof window.cart === "undefined" || window.cart === null) {
        return false;
      }
      if (!Array.isArray(window.cart)) {
        return false;
      }
      return window.cart.length > 0;
    } catch (e) {
      return false;
    }
  }

  function apiBase() {
    return (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
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
      return {
        store_slug: getStoreSlug(),
        session_id: getSessionId(),
        reason: "auto",
        product_name: ctx.name || "",
        product_price: ctx.priceLabel || "",
        cart_url: hrefAuto,
      };
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
      var o = window.CARTFLOW_WIDGET_UI_IDLE_MS;
      if (typeof o === "number" && isFinite(o) && o >= 0) {
        return o;
      }
    } catch (e) {
      /* ignore */
    }
    return WIDGET_CART_UI_IDLE_MS;
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
      document.dispatchEvent(
        new CustomEvent(name, { bubbles: true, detail: detail || {} })
      );
    } catch (e) {
      /* ignore */
    }
  }

  function fetchReadyThen(cb) {
    if (isDemoPath()) {
      step1Ready = true;
      cb();
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

  var btnStyle =
    "cursor:pointer;border:0;border-radius:8px;padding:10px 16px;font:inherit;" +
    "font-weight:600;background:#7c3aed;color:#fff;min-height:44px;box-sizing:border-box;" +
    "touch-action:manipulation;";
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

  function showBubble(triggerSource) {
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
    var openSource =
      triggerSource === TRIGGER_SOURCE_EXIT_INTENT
        ? TRIGGER_SOURCE_EXIT_INTENT
        : TRIGGER_SOURCE_CART;
    var hasCartItems = haveCartForWidget();
    try {
      console.log("HAS CART:", hasCartItems);
    } catch (eLog) {
      /* ignore */
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
    removeFabIfAny();
    if (step1Poll !== null) {
      clearInterval(step1Poll);
      step1Poll = null;
    }
    clearTimeout(idleTimer);
    events.forEach(function (e) {
      document.removeEventListener(e, resetIdle, true);
    });

    ensureMobileUxStyles();
    ensureChatBodyLayoutStyles();
    var w = document.createElement("div");
    w.setAttribute("dir", "rtl");
    w.setAttribute("lang", "ar");
    w.setAttribute("data-cartflow-bubble", "1");
    w._cfDragY = 0;
    w.style.cssText =
      "position:fixed;z-index:2147483640;box-sizing:border-box;" +
      "padding:10px 12px;border-radius:12px;background:#1e1b4b;color:#f5f3ff;" +
      "font:14px/1.4 system-ui,-apple-system,'Segoe UI',sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.2);" +
      "pointer-events:auto;isolation:isolate;";

    w.addEventListener(
      "click",
      function (ev) {
        if (ev.target === w) {
          ev.stopPropagation();
        }
      },
      false
    );

    var chromeBtnStyle =
      "cursor:pointer;border:0;border-radius:8px;padding:0 12px;font:inherit;font-size:18px;line-height:1;" +
      "font-weight:700;background:rgba(255,255,255,.12);color:#f5f3ff;min-width:44px;min-height:44px;" +
      "box-sizing:border-box;display:inline-flex;align-items:center;justify-content:center;" +
      "touch-action:manipulation;";

    var chrome = document.createElement("div");
    chrome.setAttribute("data-cf-chrome", "1");
    w._cfChrome = chrome;
    if (isNarrowViewport()) {
      chrome.style.cssText =
        "display:flex;flex-direction:row;align-items:stretch;justify-content:space-between;gap:10px;" +
        "width:100%;margin:0 0 8px 0;box-sizing:border-box;";
    } else {
      chrome.style.cssText =
        "display:flex;justify-content:flex-end;align-items:center;gap:8px;" +
        "width:100%;margin:0 0 8px 0;box-sizing:border-box;";
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
      fab.style.cssText =
        "position:fixed;z-index:2147483639;padding:0;margin:0;min-width:48px;min-height:48px;" +
        "width:48px;height:48px;border-radius:50%;" +
        "border:0;background:#7c3aed;color:#fff;font-size:20px;line-height:1;cursor:pointer;" +
        "box-shadow:0 2px 14px rgba(0,0,0,.28);touch-action:manipulation;pointer-events:auto;" +
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
      actDot.style.cssText =
        "position:absolute;top:5px;right:5px;width:8px;height:8px;border-radius:50%;" +
        "background:#34d399;border:2px solid #1e1b4a;box-sizing:border-box;pointer-events:none;" +
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
      });
      document.body.appendChild(fab);
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
    w.appendChild(chrome);

    var widgetBody = document.createElement("div");
    widgetBody.className = "cartflow-widget-body chat-body";
    widgetBody.style.cssText = "min-width:0;box-sizing:border-box;";
    w.appendChild(widgetBody);

    applyBubbleLayout(w);

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
          b.style.cssText = btnStyle;
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
      bBack.style.cssText = btnStyle;
      bBack.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        renderBrowsingGeneralOptions();
      });
      sec.appendChild(bBack);
      body.appendChild(sec);
    }

      function mountLayerDAbandonIfEligible() {
      if (openSource !== TRIGGER_SOURCE_CART) {
        return;
      }
      if (w.getAttribute("data-cf-cart-affirm-help") !== "1") {
        return;
      }
      if (w.getAttribute("data-cf-layer-d-no-help-active") === "1") {
        return;
      }

      function remountCartReasonChoicesFromFollowUp() {
        logWidgetFlow("reason_menu_back", "", "رجوع_للقائمة_السابقة");
        try {
          w.removeAttribute("data-cf-layer-d-no-help-active");
        } catch (eRmNoHelpFlg) {
          /* ignore */
        }
        stripContentKeepChrome();
        mountLayerDAbandonIfEligible();
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
        bChat.style.cssText = btnStyle;
        bChat.addEventListener("click", function (evRet) {
          evRet.stopPropagation();
          evRet.preventDefault();
          stripContentKeepChrome();
          mountLayerDAbandonIfEligible();
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

        var btnFlex =
          btnStyle + "flex:1 1 0;min-width:0;text-align:center;";

        var bBack = document.createElement("button");
        bBack.type = "button";
        bBack.setAttribute("aria-label", "رجوع خطوة للخلف");
        bBack.textContent = "⬅️ رجوع";
        bBack.style.cssText = btnFlex;
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
        bHome.style.cssText = btnFlex;
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
        bBackMenu.style.cssText = btnStyle;
        bBackMenu.addEventListener("click", function (ev) {
          ev.stopPropagation();
          ev.preventDefault();
          logWidgetFlow("layer_d_no_help_nav", "no_help", "رجوع_للقائمة");
          remountCartReasonChoicesFromFollowUp();
        });

        var bCloseAssist = document.createElement("button");
        bCloseAssist.type = "button";
        bCloseAssist.textContent = "إغلاق المساعد";
        bCloseAssist.style.cssText = btnStyle;
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
          btn.style.cssText = btnStyle;
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
            b.style.cssText = btnStyle;
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
            bx.style.cssText = btnStyle;
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
          btn.style.cssText =
            "cursor:pointer;border:0;border-radius:10px;padding:14px 18px;font:inherit;" +
            "font-weight:700;font-size:15px;background:linear-gradient(180deg,#6d28d9 0%,#5b21b6 100%);" +
            "color:#fff;min-height:48px;width:100%;box-sizing:border-box;margin-top:4px;" +
            "box-shadow:0 2px 10px rgba(91,33,182,0.4);touch-action:manipulation;";
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
            bx.style.cssText = btnStyle;
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
          btn.style.cssText = btnStyle;
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
            bx.style.cssText = btnStyle;
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
        persistSessionAbandonReason("delivery_time", null);
        stripContentKeepChrome();

        function replaceBodyWithSingleMessage(msg) {
          stripContentKeepChrome();
          var pOut = document.createElement("p");
          pOut.setAttribute("data-cf-delivery-followup-msg", "1");
          pOut.style.cssText = "margin:0 0 8px 0;font-size:14px;line-height:1.55;";
          pOut.textContent = msg;
          widgetBody.appendChild(pOut);
          appendReturnToRecoveryChatButtonRow();
        }

        var intro = document.createElement("p");
        intro.setAttribute("data-cf-delivery-followup-intro", "1");
        intro.style.cssText = "margin:0 0 12px 0;font-size:14px;line-height:1.55;";
        intro.textContent =
          "التوقيت مهم 👍 هذا ثلاث نقرات لتفهم وقت وصول الطلب أكثر بدقة:";

        var rowD = document.createElement("div");
        rowD.setAttribute("data-cf-delivery-followup-buttons", "1");
        rowD.style.cssText = rowStyleCol;

        function addDFBtn(label, onActivate) {
          var bx = document.createElement("button");
          bx.type = "button";
          bx.textContent = label;
          bx.style.cssText = btnStyle;
          bx.addEventListener("click", function (ev) {
            ev.stopPropagation();
            ev.preventDefault();
            onActivate();
          });
          rowD.appendChild(bx);
        }

        addDFBtn("كم أقصى مدة قبل التسليم المتوقعة؟", function () {
          logWidgetFlow("delivery_followup_pick", "delivery_time", "حد_التسليم");
          replaceBodyWithSingleMessage(
            "عادة بين يومين وعدّة أيام حسب المدينة وشركة الشحن المعتمدة 👍 كامل التفاصيل تظهر عند المتجر وقت الدفع."
          );
        });
        addDFBtn("هل في توصيل سريع؟", function () {
          logWidgetFlow("delivery_followup_pick", "delivery_time", "توصيل_سريع");
          replaceBodyWithSingleMessage(
            "أحياناً يتوفر خيار تنفيذ أو شحن مستعجل وفق المتجر وبعض المناطق 👍"
          );
        });
        addDFBtn("كم يمكن أن يمتد التجهيز قبل الشحن فعلاً؟", function () {
          logWidgetFlow("delivery_followup_pick", "delivery_time", "تجهيز");
          replaceBodyWithSingleMessage(
            "بيوم إلى يومَي عمل عادة لتجهيز ومغادرة المستودع، ثم تُحمَّل شحنتك."
          );
        });
        addDFBtn("رجوع للقائمة السابقة", function () {
          logWidgetFlow("delivery_followup_nav", "delivery_time", "رجوع_للقائمة");
          remountCartReasonChoicesFromFollowUp();
        });

        widgetBody.appendChild(intro);
        widgetBody.appendChild(rowD);
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
          bx.style.cssText = btnStyle;
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
        persistSessionAbandonReason("other", null);
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
          bx.style.cssText = btnStyle;
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
        var layerOpts = [
          { tag: "price_high", label: "السعر مرتفع" },
          { tag: "quality_uncertainty", label: "غير متأكد من الجودة" },
          { tag: "shipping_cost", label: "تكلفة الشحن" },
          { tag: "delivery_time", label: "مدة التوصيل" },
          { tag: "warranty", label: "الضمان" },
          { tag: "_other", label: "سبب آخر / أحتاج أتحدث معك" },
          { tag: "no_help", label: "ما أحتاج مساعدة الآن" },
        ];
        wrap.appendChild(hintHead);
        var idx;
        for (idx = 0; idx < layerOpts.length; idx++) {
          (function (opt) {
            var bChip = document.createElement("button");
            bChip.type = "button";
            bChip.textContent = opt.label;
            bChip.style.cssText = btnStyle;
            bChip.addEventListener("click", function (e) {
              e.stopPropagation();
              e.preventDefault();
              logWidgetFlow(
                "layer_d_reason_pick",
                String(opt.tag),
                String(opt.label)
              );
              if (opt.tag === "_other") {
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
              } else if (opt.tag === "no_help") {
                cartflowRejectHelp();
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

    var p0 = document.createElement("p");
    p0.style.cssText = "margin:0 0 8px 0;";
    p0.textContent =
      openSource === TRIGGER_SOURCE_EXIT_INTENT
        ? "هلا 👋 أقدر أخدمك بشيء؟"
        : "تبي أساعدك تكمل طلبك؟";

    var row0 = null;
    var btnY = null;
    var btnN = null;
    if (
      openSource === TRIGGER_SOURCE_EXIT_INTENT ||
      openSource === TRIGGER_SOURCE_CART
    ) {
      row0 = document.createElement("div");
      row0.style.cssText =
        "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:2px;";

      btnY = document.createElement("button");
      btnY.type = "button";
      btnY.textContent = "نعم";
      btnY.style.cssText = btnStyle;

      btnN = document.createElement("button");
      btnN.type = "button";
      btnN.textContent = "لا";
      btnN.style.cssText = btnStyle;
      btnN.addEventListener("click", function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        if (isDemoStoreProductPage() && isDemoScenarioActive()) {
          return;
        }
        logWidgetFlow("first_prompt_pick", "", "لا");
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
      bBack1.style.cssText = btnStyle;
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
      bBack1.style.cssText = btnStyle;
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
        bMock.style.cssText = btnStyle;
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
            var finalMessage = buildWhatsappMessage({
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
              msgEl.textContent = buildWhatsappMessage({
                reason: waReason,
                sub_category: waSub,
              });
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
          b.style.cssText = btnStyle;
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
      postReason({ reason: "price", sub_category: sub })
        .then(function (j) {
          if (j && j.ok) {
            setReasonTag("price");
            setReasonSubTag(sub);
            mountProductAwareView("price");
            emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
              reason: "price",
              sub_category: sub,
            });
          }
        })
        .catch(function () {});
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
      rsub.style.cssText = rowStyleCol;
      CARTFLOW_PRICE_SUB_OPTIONS.forEach(function (o) {
        var bs = document.createElement("button");
        bs.type = "button";
        bs.textContent = o.label;
        bs.style.cssText = btnStyle;
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
      bPBack.style.cssText = btnStyle;
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
      var p2o = document.createElement("p");
      p2o.style.cssText = "margin:0 0 8px 0;";
      p2o.textContent = "اكتب السبب أو اطلب تحويلك لصاحب المتجر";
      widgetBody.appendChild(p2o);
      var ta = document.createElement("textarea");
      ta.setAttribute("rows", "3");
      ta.setAttribute("placeholder", "…");
      ta.setAttribute("aria-label", "سبب آخر");
      ta.style.cssText =
        "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;color:#1e1b4b;resize:vertical;min-height:3.5em;";
      widgetBody.appendChild(ta);
      var row2 = document.createElement("div");
      row2.style.cssText = rowStyleCol;
      var bSend = document.createElement("button");
      bSend.type = "button";
      bSend.textContent = "إرسال السبب";
      bSend.style.cssText = btnStyle;
      bSend.addEventListener("click", function (e2) {
        e2.stopPropagation();
        e2.preventDefault();
        var t = (ta.value || "").trim();
        if (!t) {
          return;
        }
        bSend.setAttribute("disabled", "true");
        postReason({ reason: "other", custom_text: t })
          .then(function (j) {
            if (j && j.ok) {
              setReasonTag("other");
              emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
                reason: "other",
                sub_category: null,
              });
              showOtherSuccessView();
            } else {
              bSend.removeAttribute("disabled");
            }
          })
          .catch(function () {
            bSend.removeAttribute("disabled");
          });
      });
      var bHandoffO = document.createElement("button");
      bHandoffO.type = "button";
      bHandoffO.textContent = BTN_HANDOFF;
      bHandoffO.style.cssText = btnStyle;
      bHandoffO.addEventListener("click", function (e3) {
        e3.stopPropagation();
        e3.preventDefault();
        handoffToMerchant(bHandoffO);
      });
      var bBackO = document.createElement("button");
      bBackO.type = "button";
      bBackO.textContent = BTN_BACK;
      bBackO.style.cssText = btnStyle;
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

    function showOtherSuccessView() {
      stripContentKeepChrome();
      appendReasonPersonalizationBlock("other");
      var succ = document.createElement("div");
      succ.style.cssText = rowStyleCol;
      var bH2 = document.createElement("button");
      bH2.type = "button";
      bH2.textContent = BTN_HANDOFF;
      bH2.style.cssText = btnStyle;
      bH2.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        handoffToMerchant(bH2);
      });
      var bAgain = document.createElement("button");
      bAgain.type = "button";
      bAgain.textContent = "ملاحظة جديدة";
      bAgain.style.cssText = btnStyle;
      bAgain.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        mountOtherForm();
      });
      var bR = document.createElement("button");
      bR.type = "button";
      bR.textContent = BTN_BACK;
      bR.setAttribute("aria-label", "رجوع لاختيار السبب");
      bR.style.cssText = btnStyle;
      bR.addEventListener("click", function (e) {
        e.stopPropagation();
        e.preventDefault();
        if (typeof w._cfOnBackToEntry === "function") {
          w._cfOnBackToEntry();
        } else {
          renderReasonList();
        }
      });
      succ.appendChild(bH2);
      succ.appendChild(bAgain);
      succ.appendChild(bR);
      widgetBody.appendChild(succ);
    }

    function showStandardResponse(rkey) {
      setReasonTag(rkey);
      postReason({ reason: rkey })
        .then(function (j) {
          if (j && j.ok) {
            mountProductAwareView(rkey);
            emitDemoGuideEvent("cartflow-demo-reason-confirmed", {
              reason: rkey,
              sub_category: null,
            });
          }
        })
        .catch(function () {});
    }

    function renderReasonList() {
      w._cfOnBackToEntry = null;
      setReasonTag(null);
      stripContentKeepChrome();
      var p2 = document.createElement("p");
      p2.style.cssText = "margin:0 0 8px 0;";
      p2.textContent = "وش أكثر شيء مخليك متردد؟ تبيني أساعدك";
      widgetBody.appendChild(p2);
      var row = document.createElement("div");
      row.setAttribute("data-cf-reason-row", "1");
      row.style.cssText =
        "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:4px;max-height:220px;overflow-y:auto;" +
        "-webkit-overflow-scrolling:touch;overscroll-behavior:contain;padding:2px 0;";

      var options = [
        { label: "السعر", r: "price" },
        { label: "الجودة", r: "quality" },
        { label: "الضمان", r: "warranty" },
        { label: "الشحن", r: "shipping" },
        { label: "أفكر", r: "thinking" },
        { label: "سبب آخر", r: "_other" },
      ];

      options.forEach(function (o) {
        var b = document.createElement("button");
        b.type = "button";
        b.textContent = o.label;
        b.style.cssText = btnStyle;
        b.addEventListener("click", function (e) {
          e.stopPropagation();
          e.preventDefault();
          if (o.r === "_other") {
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
        b.style.cssText = btnStyle;
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
            bBackD.style.cssText = btnStyle;
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
          isDemoStoreProductPage() &&
          !haveCartForWidget()
        ) {
          renderBrowsingGeneralOptions();
          emitDemoGuideEvent("cartflow-demo-browsing-options-visible", {});
        } else if (openSource === TRIGGER_SOURCE_CART) {
          logWidgetFlow("first_prompt_pick", "", "نعم");
          stripContentKeepChrome();
          w.setAttribute("data-cf-cart-affirm-help", "1");
          mountLayerDAbandonIfEligible();
          emitDemoGuideEvent("cartflow-demo-reason-list-visible", {});
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
    widgetBody.appendChild(p0);
    mountLayerDAbandonIfEligible();
    if (row0) {
      widgetBody.appendChild(row0);
    }
    try {
      window.cartflowDevMountProductViewAuto = function () {
        mountProductAwareView("auto");
      };
    } catch (e) {
      /* ignore */
    }
    document.body.appendChild(w);
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
      showBubble(TRIGGER_SOURCE_CART);
      try {
        var widgetVisible = isWidgetDomVisible();
        console.log("widget visible:", widgetVisible);
      } catch (e) {
        /* ignore */
      }
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
        showBubble(TRIGGER_SOURCE_CART);
      } else {
        var hasDom =
          document.querySelector("[data-cartflow-bubble]") ||
          document.querySelector("[data-cartflow-fab]");
        if (!hasDom) {
          shown = false;
          setCartflowWidgetShownFlag(false);
          showBubble(TRIGGER_SOURCE_CART);
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
    if (haveCartForWidget()) {
      try {
        console.log("EXIT INTENT BLOCKED:", true);
      } catch (e0) {
        /* ignore */
      }
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

  /** نفس تسلسل التهيئة كما بعد add to cart، ثم showBubble(exit_intent) فقط. */
  function openExitIntentWidget() {
    if (!canShowExitIntentWidget()) {
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
      return;
    }
    if (isDemoPath()) {
      showBubble(TRIGGER_SOURCE_EXIT_INTENT);
      return;
    }
    fetchReadyThen(function () {
      if (!canShowExitIntentWidget()) {
        return;
      }
      showBubble(TRIGGER_SOURCE_EXIT_INTENT);
    });
  }

  function openCartflowWidgetFromTrigger(trigger) {
    if (trigger !== "exit_intent") {
      return;
    }
    openExitIntentWidget();
  }

  function CartflowExitIntentController() {
    if (!isCartPage()) {
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
        return;
      }
      triggered = true;
      try {
        console.log("EXIT_INTENT_FIRED:", type);
      } catch (e) {
        /* ignore */
      }
      openCartflowWidgetFromTrigger("exit_intent");
    }
    function resetTimer() {
      if (inactivityTimer) {
        clearTimeout(inactivityTimer);
        inactivityTimer = null;
      }
      inactivityTimer = setTimeout(function () {
        inactivityTimer = null;
        fire("inactivity");
      }, 10000);
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
      if (lastY - y > 120 && lastY > 300) {
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
            showBubble(TRIGGER_SOURCE_CART);
          } else {
            var d =
              document.querySelector("[data-cartflow-bubble]") ||
              document.querySelector("[data-cartflow-fab]");
            if (!d) {
              shown = false;
              setCartflowWidgetShownFlag(false);
              showBubble(TRIGGER_SOURCE_CART);
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

  setTimeout(prefetchDashboardPrimaryReason, 0);
  setTimeout(arm, ARM_DELAY_MS);
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
