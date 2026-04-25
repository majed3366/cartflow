/**
 * تتبع السلة المتروكة على مستوى التطبيق — أي صفحة فيها ‎window.cart‎.
 */
(function () {
  "use strict";
  if (typeof window.cart === "undefined" || window.cart === null) {
    window.cart = [];
  } else if (!Array.isArray(window.cart)) {
    window.cart = [];
  }
  if (typeof window.replyaiTrack !== "function") {
    window.replyaiTrack = function () {};
  }
  console.log("abandon tracking active");

  function apiCartEventUrl() {
    var base = (window.CARTFLOW_API_BASE || "").toString().replace(/\/$/, "");
    return base ? base + "/api/cart-event" : "/api/cart-event";
  }

  var CARTFLOW_SESSION_KEY = "cartflow_recovery_session_id";
  // يُلزِم id واحداً لكل تبويب حتى عند تزامن ‎beforeunload + visibility‎ أو فشل ‎sessionStorage‎
  var _cachedRecoverySessionId = null;

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
    var storeSlug =
      typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
      window.CARTFLOW_STORE_SLUG !== null &&
      String(window.CARTFLOW_STORE_SLUG).trim() !== ""
        ? String(window.CARTFLOW_STORE_SLUG).trim()
        : "demo";
    var body = JSON.stringify({
      event: "cart_abandoned",
      store: storeSlug,
      source: source,
      session_id: getRecoverySessionId(),
      cart: window.cart,
    });
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
