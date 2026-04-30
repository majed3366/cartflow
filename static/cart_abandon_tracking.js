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
