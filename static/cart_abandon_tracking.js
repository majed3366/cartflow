/**
 * تتبع السلة المتروكة على مستوى التطبيق — أي صفحة فيها ‎window.cart‎.
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

  function cartflowBootstrapLogState() {
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
    } catch (eBl) {
      /* ignore */
    }
  }

  function cartflowBootstrapRegisterNewIntent(kind) {
    var s = window.CartFlowState;
    if (!s || kind !== "add_to_cart") {
      return;
    }
    s.hasCart = true;
    s.lastIntentAt = Date.now();
    if (s.userRejectedHelp === true) {
      s.userRejectedHelp = false;
      s.rejectionTimestamp = null;
      console.log("[BEHAVIOR RESET] reason=add_to_cart");
    }
    try {
      if (
        typeof window.matchMedia === "function" &&
        window.matchMedia("(max-width: 767px)").matches
      ) {
        console.log("[ADD TO CART MONITORING STARTED]");
        console.log("device=mobile");
        console.log("show_widget=false");
      }
    } catch (eMob) {
      /* ignore */
    }
    cartflowBootstrapLogState();
  }

  if (typeof window.cartflowRejectHelp !== "function") {
    window.cartflowRejectHelp = function () {};
  }

  if (typeof window.cartflowRegisterNewIntent !== "function") {
    window.cartflowRegisterNewIntent = cartflowBootstrapRegisterNewIntent;
  }

  if (typeof window.cart === "undefined" || window.cart === null) {
    window.cart = [];
  } else if (!Array.isArray(window.cart)) {
    window.cart = [];
  }
  if (typeof window.replyaiTrack !== "function") {
    window.replyaiTrack = function () {};
  }

  function notifyBackendAddToCartIntent() {
    if (cartflowIsSessionConverted()) {
      return;
    }
    try {
      if (typeof window.cartflowSyncCartState === "function") {
        window.cartflowSyncCartState("add");
      }
    } catch (eNfy) {
      /* ignore */
    }
  }

  /** إعادة تفعيل الويدجت بعد رفض المساعدة عند ‎add_to_cart‎ (وتجربة ‎demo‎ عبر ‎cf-demo-cart-updated‎). */
  (function wrapReplyaiTrackForBehaviorReset() {
    var prevTrack = window.replyaiTrack;
    window.replyaiTrack = function (payload) {
      try {
        if (
          payload &&
          typeof payload === "object" &&
          payload.event === "add_to_cart"
        ) {
          window.cartflowRegisterNewIntent("add_to_cart");
          notifyBackendAddToCartIntent();
        }
      } catch (eBr) {
        /* ignore */
      }
      if (typeof prevTrack === "function") {
        return prevTrack.apply(this, arguments);
      }
    };
  })();

  document.addEventListener(
    "cf-demo-cart-updated",
    function () {
      try {
        window.cartflowRegisterNewIntent("add_to_cart");
        notifyBackendAddToCartIntent();
      } catch (eCf) {
        /* ignore */
      }
    },
    false
  );

  console.log("abandon tracking active");

  function apiCartEventUrl() {
    var base = (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
    return base ? base + "/api/cart-event" : "/api/cart-event";
  }

  var CF_CART_EVENT_ID_STORAGE_KEY = "cartflow_cart_event_id";

  function getStableCartEventIdForTracking() {
    try {
      if (
        typeof window.CARTFLOW_CART_ID !== "undefined" &&
        window.CARTFLOW_CART_ID != null &&
        String(window.CARTFLOW_CART_ID).trim()
      ) {
        return String(window.CARTFLOW_CART_ID).trim().slice(0, 255);
      }
    } catch (eCid) {
      /* ignore */
    }
    var existing = null;
    try {
      existing = sessionStorage.getItem(CF_CART_EVENT_ID_STORAGE_KEY);
    } catch (e1) {}
    if (existing && String(existing).trim()) {
      return String(existing).trim().slice(0, 255);
    }
    var nid =
      typeof window.crypto !== "undefined" && window.crypto.randomUUID
        ? "cf_cart_" + window.crypto.randomUUID()
        : "cf_cart_" + String(Date.now()) + "_" + String(Math.random());
    try {
      sessionStorage.setItem(CF_CART_EVENT_ID_STORAGE_KEY, nid);
    } catch (e2) {}
    return nid.slice(0, 255);
  }

  function sumCartArrayTotal(cartArr) {
    if (!cartArr || !Array.isArray(cartArr)) {
      return 0;
    }
    var sum = 0;
    var anyRow = false;
    for (var i = 0; i < cartArr.length; i++) {
      var row = cartArr[i];
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

  function cartflowBootstrapCartStateSync(reason) {
    if (cartflowIsSessionConverted()) {
      return;
    }
    var r = String(reason || "page_load").toLowerCase();
    var okR = { add: 1, remove: 1, clear: 1, abandon: 1, page_load: 1 };
    if (!okR[r]) {
      r = "page_load";
    }
    var storeSlug =
      typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
      window.CARTFLOW_STORE_SLUG !== null &&
      String(window.CARTFLOW_STORE_SLUG).trim() !== ""
        ? String(window.CARTFLOW_STORE_SLUG).trim()
        : "demo";
    var cartArr =
      typeof window.cart !== "undefined" && window.cart !== null && Array.isArray(window.cart)
        ? window.cart
        : [];
    var cartTotal = sumCartArrayTotal(cartArr);
    var items_count = cartArr.length;

    window.cart_total = cartTotal;
    var vipCartThresholdRaw =
      typeof window.cartflowVipCartThreshold !== "undefined" &&
      window.cartflowVipCartThreshold !== null &&
      window.cartflowVipCartThreshold !== ""
        ? window.cartflowVipCartThreshold
        : typeof window.CARTFLOW_VIP_CART_THRESHOLD !== "undefined" &&
          window.CARTFLOW_VIP_CART_THRESHOLD !== null &&
          String(window.CARTFLOW_VIP_CART_THRESHOLD).trim() !== ""
        ? window.CARTFLOW_VIP_CART_THRESHOLD
        : undefined;
    var vipCartThreshold = vipCartThresholdRaw;
    if (vipCartThreshold == null || vipCartThreshold === "") {
      window.vip_threshold = undefined;
      window.is_vip = false;
    } else {
      var vipThNum =
        typeof vipCartThreshold === "number"
          ? vipCartThreshold
          : parseFloat(String(vipCartThreshold));
      if (!isFinite(vipThNum) || vipThNum < 1) {
        window.vip_threshold = undefined;
        window.is_vip = false;
      } else {
        window.vip_threshold = vipThNum;
        window.is_vip = cartTotal >= vipThNum;
      }
    }

    console.log("[VIP DATA READY]", {
      cart_total: window.cart_total,
      vip_threshold: window.vip_threshold,
      is_vip: window.is_vip,
    });

    var session_id = getRecoverySessionId();
    var cart_id = getStableCartEventIdForTracking();
    var body = JSON.stringify({
      event: "cart_state_sync",
      reason: r,
      store: storeSlug,
      session_id: session_id,
      cart_id: cart_id,
      cart_total: cartTotal,
      items_count: items_count,
      cart: cartArr,
    });
    try {
      console.log(
        "[WIDGET CART SYNC SENT] reason=" +
          r +
          " cart_id=" +
          cart_id +
          " session_id=" +
          session_id +
          " cart_total=" +
          cartTotal +
          " items_count=" +
          items_count
      );
    } catch (eL) {}
    try {
      fetch(apiCartEventUrl(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
      }).catch(function () {});
    } catch (eF) {}
  }

  if (typeof window.cartflowSyncCartState !== "function") {
    window.cartflowSyncCartState = cartflowBootstrapCartStateSync;
  }

  function getOptionalCartflowCustomerPhone() {
    try {
      if (
        typeof window.CARTFLOW_CUSTOMER_PHONE === "string" &&
        window.CARTFLOW_CUSTOMER_PHONE.trim()
      ) {
        return String(window.CARTFLOW_CUSTOMER_PHONE).trim().slice(0, 100);
      }
    } catch (ePh) {
      /* ignore */
    }
    return "";
  }

  var CARTFLOW_SESSION_KEY = "cartflow_recovery_session_id";
  var CARTFLOW_CONVERTED_KEY = "cartflow_converted";
  // يُلزِم id واحداً لكل تبويب حتى عند تزامن ‎beforeunload + visibility‎ أو فشل ‎sessionStorage‎
  var _cachedRecoverySessionId = null;

  function cartflowIsSessionConverted() {
    try {
      return window.sessionStorage.getItem(CARTFLOW_CONVERTED_KEY) === "1";
    } catch (e) {
      return false;
    }
  }
  window.cartflowIsSessionConverted = cartflowIsSessionConverted;

  /**
   * يسمح ببدء ‎Start Demo Scenario‎: مسح الـ ‎cache‎ وضبط ‎session_id‎ (لا يغيّر منطق الاسترجاع).
   */
  function resetRecoverySessionIdForDemo(newId) {
    _cachedRecoverySessionId = null;
    try {
      if (newId) {
        window.sessionStorage.setItem(CARTFLOW_SESSION_KEY, newId);
        _cachedRecoverySessionId = newId;
      } else {
        window.sessionStorage.removeItem(CARTFLOW_SESSION_KEY);
      }
    } catch (e) {
      /* ignore */
    }
  }
  window.cartflowResetRecoverySessionIdForDemo = resetRecoverySessionIdForDemo;

  /**
   * Delay-testing helper only (manual/console): new cart-abandon session without changing server duplicate protection.
   * Clears localStorage replyai_session if present; forces new session id in sessionStorage.
   * Call from DevTools before each delay run: cartflowFreshSessionForDelayTest()
   */
  function freshRecoverySessionForDelayTest() {
    try {
      localStorage.removeItem("replyai_session");
    } catch (eRmLocal) {
      /* ignore */
    }
    var nid =
      typeof window.crypto !== "undefined" && window.crypto.randomUUID
        ? "s_" + window.crypto.randomUUID()
        : "s_" + String(Date.now()) + "_" + String(Math.random());
    resetRecoverySessionIdForDemo(nid);
    _abandonEventSentToBackend = false;
    try {
      console.log("[CF TEST] cartflowFreshSessionForDelayTest session_id=", nid);
    } catch (eLog) {
      /* ignore */
    }
    return nid;
  }
  window.cartflowFreshSessionForDelayTest = freshRecoverySessionForDelayTest;

  function getRecoverySessionId() {
    if (_cachedRecoverySessionId) {
      return _cachedRecoverySessionId;
    }
    var s;
    try {
      s = window.sessionStorage.getItem(CARTFLOW_SESSION_KEY);
    } catch (e) {
      s = null;
    }
    if (s) {
      _cachedRecoverySessionId = s;
      return s;
    }
    s =
      typeof window.crypto !== "undefined" && window.crypto.randomUUID
        ? "s_" + window.crypto.randomUUID()
        : "s_" + String(Date.now()) + "_" + String(Math.random());
    _cachedRecoverySessionId = s;
    try {
      window.sessionStorage.setItem(CARTFLOW_SESSION_KEY, s);
    } catch (e2) {}
    return s;
  }

  function sendCartAbandonedToBackend(source) {
    if (cartflowIsSessionConverted()) {
      return;
    }
    var storeSlug =
      typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
      window.CARTFLOW_STORE_SLUG !== null &&
      String(window.CARTFLOW_STORE_SLUG).trim() !== ""
        ? String(window.CARTFLOW_STORE_SLUG).trim()
        : "demo";
    var cartArr =
      typeof window.cart !== "undefined" && window.cart !== null && Array.isArray(window.cart)
        ? window.cart
        : [];
    var cartTotal = sumCartArrayTotal(cartArr);
    var bodyObj = {
      event: "cart_abandoned",
      store: storeSlug,
      source: source,
      session_id: getRecoverySessionId(),
      cart_id: getStableCartEventIdForTracking(),
      cart_total: cartTotal,
      cart: cartArr,
    };
    var ph = getOptionalCartflowCustomerPhone();
    if (ph) {
      bodyObj.phone = ph;
    }
    var body = JSON.stringify(bodyObj);
    var url = apiCartEventUrl();
    var opts = {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body,
    };
    if (source === "beforeunload") {
      opts.keepalive = true;
    }
    return fetch(url, opts)
      .then(function (r) {
        return r.json().then(function (j) {
          return { status: r.status, body: j };
        });
      })
      .then(function (response) {
        console.log("cart_abandoned backend response", response);
        return response;
      })
      .catch(function (err) {
        console.log("cart_abandoned backend response", err);
      });
  }

  // منع طلبين لنفس التبويب (مثلاً ‎hidden‎ ثم ‎beforeunload‎) — جدولة استرجاع واحدة
  var _abandonEventSentToBackend = false;

  function onCartAbandoned(source) {
    if (cartflowIsSessionConverted()) {
      return;
    }
    if (typeof window.cart === "undefined" || window.cart === null) {
      window.cart = [];
    } else if (!Array.isArray(window.cart)) {
      window.cart = [];
    }
    if (window.cart.length === 0) {
      return;
    }
    if (_abandonEventSentToBackend) {
      return;
    }
    _abandonEventSentToBackend = true;
    console.log("cart_abandoned triggered");
    window.replyaiTrack({ event: "cart_abandoned" });
    console.log("sending cart_abandoned to backend");
    void sendCartAbandonedToBackend(source);
  }

  window.addEventListener("beforeunload", function () {
    onCartAbandoned("beforeunload");
  });
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      onCartAbandoned("visibility");
    }
  });

  /* للوحة ‎/demo*‎: معرفة الجلسة نفسه بدون تكرار المنطق */
  window.cartflowGetSessionId = getRecoverySessionId;
})();
