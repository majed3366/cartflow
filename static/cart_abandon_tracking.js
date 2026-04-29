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
