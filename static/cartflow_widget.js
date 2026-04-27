/**
 * CartFlow — عرض سبب التردد بعد ‎step1‎ استرجاع (بلا مزوّد واتساب في الودجت).
 * ‎/demo/‎: يتخطّى انتظار ‎step1‎ (تجارب). باقي المسارات: حتى ‎GET /api/cartflow/ready‎.
 */
(function () {
  "use strict";

  var ARM_DELAY_MS = 3000;
  var IDLE_MS = 8000;
  /** على ‎/demo/store‎ عند تفعيل الودجت: عرض أسرع (ثانية تقريباً) */
  var DEMO_ARMED_IDLE_MS = 1600;
  var REASON_TAG_KEY = "cartflow_reason_tag";
  var REASON_SUB_TAG_KEY = "cartflow_reason_sub_tag";
  var DEMO_STORE_WIDGET_ARMED_KEY = "cartflow_demo_store_widget_armed";
  var DEMO_STORE_EXIT_INTENT_SHOWN_KEY = "cartflow_demo_store_exit_intent_shown";
  var shown = false;
  var idleTimer = null;
  var step1Ready = false;
  var step1Poll = null;
  var armListenersAttached = false;
  var demoStoreBubbleDismissed = false;
  var exitIntentScheduleTimer = null;
  var exitInactivityTimer = null;
  var exitLastScrollY = 0;
  var exitLastScrollT = 0;
  var exitMaxScrollDepth = 0;
  var exitTabWasHidden = false;
  /** مصدر فتح الودجت — نص الترحيب فقط */
  var TRIGGER_SOURCE_CART = "cart";
  var TRIGGER_SOURCE_EXIT_INTENT = "exit_intent";
  var mobileExitInactivityTimer = null;
  var mobileExitLastScrollY = 0;
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
    if (path === "/demo/store" || path.indexOf("/demo/store/") === 0) {
      return true;
    }
    return false;
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

  function isWidgetDomVisible() {
    return !!(
      document.querySelector("[data-cartflow-bubble]") ||
      document.querySelector("[data-cartflow-fab]")
    );
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

  function runArmBody() {
    if (isSessionConverted() || !isCartPage()) {
      return;
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

  function haveCartForWidget() {
    if (isSessionConverted()) {
      return false;
    }
    var p = (window.location.pathname || "") + (window.location.search || "");
    if (p.indexOf("/demo/") < 0) {
      return true;
    }
    if (typeof window.cart === "undefined" || window.cart === null) {
      return false;
    }
    if (!Array.isArray(window.cart)) {
      return false;
    }
    return window.cart.length > 0;
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
    var openSource =
      triggerSource === TRIGGER_SOURCE_EXIT_INTENT
        ? TRIGGER_SOURCE_EXIT_INTENT
        : TRIGGER_SOURCE_CART;
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
        } else {
          return;
        }
      } else {
        shown = false;
      }
    }
    if (!haveCartForWidget()) {
      if (!(openSource === TRIGGER_SOURCE_EXIT_INTENT && isDemoStoreProductPage())) {
        return;
      }
    }
    shown = true;
    if (openSource === TRIGGER_SOURCE_EXIT_INTENT && isDemoStoreProductPage()) {
      setDemoStoreExitIntentShown();
    }
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

    applyBubbleLayout(w);

    var p0 = document.createElement("p");
    p0.style.cssText = "margin:0 0 8px 0;";
    p0.textContent =
      openSource === TRIGGER_SOURCE_EXIT_INTENT
        ? "هلا 👋 أقدر أخدمك بشيء؟"
        : "تبي أساعدك تكمل طلبك؟";

    var row0 = document.createElement("div");
    row0.style.cssText =
      "display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-start;margin-top:2px;";

    var btnY = document.createElement("button");
    btnY.type = "button";
    btnY.textContent = "نعم";
    btnY.style.cssText = btnStyle;

    var btnN = document.createElement("button");
    btnN.type = "button";
    btnN.textContent = "لا";
    btnN.style.cssText = btnStyle;
    btnN.addEventListener("click", function (ev) {
      ev.stopPropagation();
      ev.preventDefault();
      if (isDemoStoreProductPage() && isDemoScenarioActive()) {
        return;
      }
      removeFabIfAny();
      if (typeof w._cfCleanup === "function") {
        w._cfCleanup();
      }
      if (w && w.parentNode) {
        w.parentNode.removeChild(w);
      }
      if (isDemoStoreProductPage()) {
        shown = false;
        demoStoreBubbleDismissed = true;
        clearTimeout(idleTimer);
        idleTimer = null;
      }
    });

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
      w.appendChild(box);
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
      w.appendChild(pex);
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
      w.appendChild(rowB);
    }

    function showAlternativesPanel(rkey, flow) {
      stripContentKeepChrome();
      var pex = document.createElement("p");
      pex.style.cssText = "margin:0 0 10px 0;font-size:14px;line-height:1.55;";
      pex.textContent = flow.explain;
      w.appendChild(pex);
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
      w.appendChild(rowB);
    }

    function mountProductAwareView(rkey) {
      var flow = getProductAwareCopy(rkey);
      if (!flow) {
        return;
      }
      stripContentKeepChrome();
      appendReasonPersonalizationBlock(rkey);
      (function () {
        var payload = buildWhatsappGeneratePayload(rkey);
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
          var cartUrl = "#";
          if (payload && payload.cart_url && String(payload.cart_url).trim()) {
            cartUrl = String(payload.cart_url).trim();
          }
          var fullText =
            "👋 مرحباً\n\n" +
            String(generatedCore) +
            "\n\n🛒 رابط السلة:\n" +
            cartUrl;
          var wurl = buildWaMeComposeUrl(fullText, merchantE164);
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
        });
        previewBox.appendChild(bMock);
        previewBox.appendChild(mockStatus);
        previewBox.appendChild(convHint);
        strip.appendChild(previewBox);
        w.appendChild(strip);
        postGenerateWhatsappMessage(payload)
          .then(function (x) {
            if (x && x.j && x.j.ok && x.j.message) {
              generatedCore = String(x.j.message);
              msgEl.textContent = generatedCore;
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
      w.appendChild(p);
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
      w.appendChild(rowA);
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
      w.appendChild(psub);
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
      w.appendChild(rsub);
    }

    function mountOtherForm() {
      stripContentKeepChrome();
      var p2o = document.createElement("p");
      p2o.style.cssText = "margin:0 0 8px 0;";
      p2o.textContent = "اكتب السبب أو اطلب تحويلك لصاحب المتجر";
      w.appendChild(p2o);
      var ta = document.createElement("textarea");
      ta.setAttribute("rows", "3");
      ta.setAttribute("placeholder", "…");
      ta.setAttribute("aria-label", "سبب آخر");
      ta.style.cssText =
        "width:100%;box-sizing:border-box;border-radius:8px;border:0;padding:8px;margin-bottom:8px;font:inherit;color:#1e1b4b;resize:vertical;min-height:3.5em;";
      w.appendChild(ta);
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
      w.appendChild(row2);
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
      w.appendChild(succ);
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
      w.appendChild(p2);
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
      w.appendChild(row);
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
      w.appendChild(p2);
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
            var grid = document.getElementById("cf-demo-products");
            if (grid && grid.scrollIntoView) {
              grid.scrollIntoView({ behavior: "smooth", block: "start" });
            }
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
            w.appendChild(pd);
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
            w.appendChild(rB);
            emitDemoGuideEvent("cartflow-demo-browsing-option", { option: "discount" });
          } else if (o.action === "handoff") {
            handoffToMerchant(b);
            emitDemoGuideEvent("cartflow-demo-browsing-option", { option: "handoff" });
          }
        });
        row.appendChild(b);
      });
      w.appendChild(row);
    }

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
      } else {
        renderReasonList();
        emitDemoGuideEvent("cartflow-demo-reason-list-visible", {});
      }
    }, false);

    row0.appendChild(btnY);
    row0.appendChild(btnN);
    w.appendChild(p0);
    w.appendChild(row0);
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
    var delay =
      isDemoStoreProductPage() && readDemoStoreWidgetArmed()
        ? DEMO_ARMED_IDLE_MS
        : IDLE_MS;
    try {
      console.log("widget triggered");
    } catch (e) {
      /* ignore */
    }
    idleTimer = setTimeout(function () {
      showBubble(TRIGGER_SOURCE_CART);
      try {
        var widgetVisible = isWidgetDomVisible();
        console.log("widget visible:", widgetVisible);
      } catch (e) {
        /* ignore */
      }
    }, delay);
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
    demoStoreBubbleDismissed = false;
    clearTimeout(idleTimer);
    idleTimer = null;
    removeFabIfAny();
    removeCartflowBubbleDom();
    shown = false;
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
    showBubble(TRIGGER_SOURCE_CART);
  }

  function getExitScrollY() {
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

  function clearExitInactivity() {
    if (exitInactivityTimer) {
      clearTimeout(exitInactivityTimer);
      exitInactivityTimer = null;
    }
  }

  function clearMobileExitInactivity() {
    if (mobileExitInactivityTimer) {
      clearTimeout(mobileExitInactivityTimer);
      mobileExitInactivityTimer = null;
    }
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
    if (!isCartPage()) {
      return false;
    }
    if (isDemoStoreProductPage()) {
      if (readDemoStoreExitIntentShown()) {
        return false;
      }
      if (demoStoreBubbleDismissed) {
        return false;
      }
      if (document.querySelector("[data-cartflow-bubble]")) {
        return false;
      }
      return true;
    }
    if (!haveCartForWidget()) {
      return false;
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

  function resetMobileExitInactivity() {
    clearMobileExitInactivity();
    if (!isNarrowViewport()) {
      return;
    }
    if (!isCartPage()) {
      return;
    }
    if (!isDemoStoreProductPage() && !haveCartForWidget()) {
      return;
    }
    if (isDemoStoreProductPage() && demoStoreBubbleDismissed) {
      return;
    }
    if (document.querySelector("[data-cartflow-bubble]")) {
      return;
    }
    mobileExitInactivityTimer = setTimeout(function () {
      mobileExitInactivityTimer = null;
      if (!canShowExitIntentWidget()) {
        return;
      }
      try {
        console.log("mobile inactivity fired");
      } catch (e) {
        /* ignore */
      }
      scheduleExitIntent();
    }, 10000);
  }

  function resetExitInactivity() {
    clearExitInactivity();
    if (isNarrowViewport()) {
      resetMobileExitInactivity();
      return;
    }
    if (!isCartPage()) {
      return;
    }
    if (!isDemoStoreProductPage() && !haveCartForWidget()) {
      return;
    }
    if (isDemoStoreProductPage() && demoStoreBubbleDismissed) {
      return;
    }
    if (document.querySelector("[data-cartflow-bubble]")) {
      return;
    }
    var waitMs = 10000 + Math.random() * 5000;
    exitInactivityTimer = setTimeout(function () {
      exitInactivityTimer = null;
      if (!canShowExitIntentWidget()) {
        return;
      }
      scheduleExitIntent();
    }, waitMs);
  }

  function scheduleExitIntent() {
    if (!canShowExitIntentWidget()) {
      return;
    }
    if (exitIntentScheduleTimer) {
      return;
    }
    var delay = 300 + Math.random() * 500;
    exitIntentScheduleTimer = setTimeout(function () {
      exitIntentScheduleTimer = null;
      if (!canShowExitIntentWidget()) {
        return;
      }
      openExitIntentWidget();
    }, delay);
  }

  function tryExitIntentOnPageLeave() {
    if (!canShowExitIntentWidget()) {
      return;
    }
    openExitIntentWidget();
  }

  function initExitIntent() {
    try {
      console.log("initExitIntent called");
    } catch (e) {
      /* ignore */
    }
    var yInit = getExitScrollY();
    exitLastScrollY = yInit;
    exitLastScrollT = Date.now();
    exitMaxScrollDepth = yInit;
    mobileExitLastScrollY = yInit;

    if (isNarrowViewport()) {
      function handleNarrowScroll() {
        resetExitInactivity();
        var currentY = getExitScrollY();
        if (
          mobileExitLastScrollY - currentY > 120 &&
          mobileExitLastScrollY > 300
        ) {
          try {
            console.log("mobile scroll-up fired");
          } catch (e) {
            /* ignore */
          }
          scheduleExitIntent();
        }
        mobileExitLastScrollY = currentY;
      }
      window.addEventListener("scroll", handleNarrowScroll, { passive: true, capture: true });
      document.addEventListener("scroll", handleNarrowScroll, { passive: true, capture: true });
      document.addEventListener(
        "touchstart",
        function () {
          resetExitInactivity();
        },
        { passive: true, capture: true }
      );
      document.addEventListener(
        "touchmove",
        function () {
          resetExitInactivity();
        },
        { passive: true, capture: true }
      );
    } else {
      function handleDesktopScroll() {
        var y = getExitScrollY();
        var t = Date.now();
        var dt = t - exitLastScrollT;
        if (y > exitMaxScrollDepth) {
          exitMaxScrollDepth = y;
        }
        if (dt > 0 && y < exitLastScrollY && exitMaxScrollDepth > 300) {
          var v = (exitLastScrollY - y) / dt;
          if (v > 0.35 && exitLastScrollY - y > 18) {
            scheduleExitIntent();
          }
        }
        exitLastScrollY = y;
        exitLastScrollT = t;
        resetExitInactivity();
      }
      window.addEventListener("scroll", handleDesktopScroll, { passive: true, capture: true });
      document.addEventListener("scroll", handleDesktopScroll, { passive: true, capture: true });
      document.addEventListener(
        "mouseout",
        function (e) {
          if (isNarrowViewport()) {
            return;
          }
          if (!isDemoStoreProductPage()) {
            return;
          }
          if (typeof e.clientY !== "number" || e.clientY > 0) {
            return;
          }
          if (!canShowExitIntentWidget()) {
            return;
          }
          scheduleExitIntent();
        },
        true
      );
      ["pointerdown", "click", "keydown", "touchstart"].forEach(function (ev) {
        document.addEventListener(
          ev,
          function () {
            resetExitInactivity();
          },
          { passive: true, capture: true }
        );
      });
    }

    document.addEventListener("visibilitychange", function () {
      if (isNarrowViewport()) {
        if (document.visibilityState === "hidden") {
          exitTabWasHidden = true;
          try {
            console.log("mobile tab hidden");
          } catch (e) {
            /* ignore */
          }
        } else if (document.visibilityState === "visible") {
          try {
            console.log("mobile tab returned");
          } catch (e) {
            /* ignore */
          }
          if (exitTabWasHidden) {
            exitTabWasHidden = false;
            scheduleExitIntent();
          }
        }
        resetExitInactivity();
        return;
      }
      if (document.hidden) {
        exitTabWasHidden = true;
      } else {
        if (exitTabWasHidden) {
          exitTabWasHidden = false;
          scheduleExitIntent();
        }
      }
      resetExitInactivity();
    });

    window.addEventListener("pagehide", tryExitIntentOnPageLeave, { capture: true });
    window.addEventListener("beforeunload", tryExitIntentOnPageLeave, { capture: true });

    if (isCartPage() && (isDemoStoreProductPage() || haveCartForWidget())) {
      resetExitInactivity();
    }
    try {
      console.log(
        "[CartFlow] exit intent listeners registered",
        window.location.pathname,
        "isCartPage:",
        isCartPage(),
        "narrow:",
        isNarrowViewport()
      );
    } catch (e) {
      /* ignore */
    }
  }

  function bootExitIntent() {
    initExitIntent();
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootExitIntent);
  } else {
    bootExitIntent();
  }

  if (isDemoStoreProductPage()) {
    setInterval(ensureDemoStoreBubbleVisible, 2500);
  }

  if (isDemoPath()) {
    document.addEventListener("cf-demo-cart-updated", function () {
      setTimeout(function () {
        resetExitInactivity();
        runArmBody();
        nudgeWidgetIdle();
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

  setTimeout(arm, ARM_DELAY_MS);
})();
