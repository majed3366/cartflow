/**
 * تتبع السلة المتروكة على مستوى التطبيق — أي صفحة فيها ‎window.cart‎.
 * Static asset cache token (keep in sync with templates/partials/cart_abandon_tracking.html ?v=):
 * cartflow-abandon-inv-20260207a
 */
(function () {
  "use strict";
  try {
    console.log("[TRACKING SCRIPT LOADED]");
  } catch (eTsl) {
    /* ignore */
  }
  try {
    function cartflowLogTrackingDomContentLoaded() {
      try {
        console.log("[TRACKING DOMContentLoaded]");
      } catch (eDcl) {
        /* ignore */
      }
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", cartflowLogTrackingDomContentLoaded, false);
    } else {
      cartflowLogTrackingDomContentLoaded();
    }
  } catch (eReg) {
    /* ignore */
  }
  try {
    window.addEventListener(
      "error",
      function (ev) {
        try {
          console.warn(
            "[TRACKING RUNTIME ERROR]",
            ev && ev.message,
            ev && ev.filename,
            ev && ev.lineno
          );
        } catch (eWin) {
          /* ignore */
        }
      },
      true
    );
  } catch (eWinReg) {
    /* ignore */
  }
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

  var CF_TEST_CUSTOMER_PHONE_LS = "cartflow_test_customer_phone";

  function readCfTestCustomerPhoneForPayload() {
    try {
      if (
        typeof window.__CARTFLOW_CF_TEST_PHONE === "string" &&
        window.__CARTFLOW_CF_TEST_PHONE.trim()
      ) {
        return String(window.__CARTFLOW_CF_TEST_PHONE).trim().slice(0, 100);
      }
    } catch (eW) {
      /* ignore */
    }
    try {
      var ls = window.localStorage.getItem(CF_TEST_CUSTOMER_PHONE_LS);
      if (ls != null && String(ls).trim()) {
        return String(ls).trim().slice(0, 100);
      }
    } catch (eLs) {
      /* ignore */
    }
    return "";
  }

  window.cartflowReadCfTestCustomerPhone = readCfTestCustomerPhoneForPayload;

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
      var cart_total = cartTotal;
      window.cart_total = cart_total;
      window.cartflow_cart_total = cart_total;
      window.cart_items_count = items_count;

      console.log("[WINDOW CART TOTAL SET]", {
        cart_total: window.cart_total,
        items_count: window.cart_items_count,
      });

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
  var CF_RECOVERY_FLOW_STARTED_KEY = "cartflow_recovery_flow_started";
  var CF_RECOVERY_RETURN_STATE_LS_KEY = "cartflow_recovery_return_state_v1";
  var CF_REASON_TAG_SS = "cartflow_reason_tag";
  var CF_REASON_SUB_TAG_SS = "cartflow_reason_sub_tag";
  var CF_RECOVERY_LAST_ACTIVITY_SS = "cartflow_recovery_last_activity";
  var CF_LS_CUSTOMER_PHONE = "cartflow_customer_phone";
  // Return-to-site POST is handled only by static/cartflow_return_tracker.js (isolated).
  // يُلزِم id واحداً لكل تبويب حتى عند تزامن ‎beforeunload + visibility‎ أو فشل ‎sessionStorage‎
  var _cachedRecoverySessionId = null;

  function getCartflowStoreSlugForPayload() {
    try {
      if (
        typeof window.CARTFLOW_STORE_SLUG !== "undefined" &&
        window.CARTFLOW_STORE_SLUG !== null &&
        String(window.CARTFLOW_STORE_SLUG).trim() !== ""
      ) {
        return String(window.CARTFLOW_STORE_SLUG).trim();
      }
    } catch (eSl) {
      /* ignore */
    }
    return "demo";
  }

  function cartflowReadDurableRecoveryReturnState() {
    try {
      var raw = window.localStorage.getItem(CF_RECOVERY_RETURN_STATE_LS_KEY);
      if (!raw || !String(raw).trim()) {
        return null;
      }
      return JSON.parse(raw);
    } catch (eRd) {
      return null;
    }
  }

  function cartflowClearDurableRecoveryReturnState() {
    try {
      window.localStorage.removeItem(CF_RECOVERY_RETURN_STATE_LS_KEY);
    } catch (eCl) {
      /* ignore */
    }
  }
  window.cartflowClearDurableRecoveryReturnState = cartflowClearDurableRecoveryReturnState;

  function cartflowHydrateDurableRecoveryReturnState() {
    try {
      if (cartflowIsSessionConverted()) {
        cartflowClearDurableRecoveryReturnState();
        return;
      }
    } catch (eCv) {
      /* ignore */
    }
    var o = cartflowReadDurableRecoveryReturnState();
    if (
      !o ||
      o.v !== 1 ||
      (o.recovery_flow_started !== "1" && o.recovery_flow_started !== true)
    ) {
      return;
    }
    var curStore = getCartflowStoreSlugForPayload();
    if (o.store_slug && curStore && o.store_slug !== curStore) {
      return;
    }
    if (!o.session_id || !o.cart_id) {
      return;
    }
    try {
      window.sessionStorage.setItem(
        CARTFLOW_SESSION_KEY,
        String(o.session_id).slice(0, 300)
      );
      window.sessionStorage.setItem(
        CF_CART_EVENT_ID_STORAGE_KEY,
        String(o.cart_id).slice(0, 255)
      );
      window.sessionStorage.setItem(CF_RECOVERY_FLOW_STARTED_KEY, "1");
      _cachedRecoverySessionId = String(o.session_id);
      var rsn = o.reason_tag != null ? String(o.reason_tag).trim() : "";
      if (rsn) {
        window.sessionStorage.setItem(CF_REASON_TAG_SS, rsn.slice(0, 64));
      }
      var rsub = o.reason_sub_tag != null ? String(o.reason_sub_tag).trim() : "";
      if (rsub) {
        window.sessionStorage.setItem(CF_REASON_SUB_TAG_SS, rsub.slice(0, 64));
      }
      var lact = o.last_activity != null ? String(o.last_activity).trim() : "";
      if (lact) {
        window.sessionStorage.setItem(CF_RECOVERY_LAST_ACTIVITY_SS, lact.slice(0, 80));
      }
    } catch (eHy) {
      /* ignore */
    }
  }

  function _cfNonEmptyStr(v) {
    if (v == null) {
      return "";
    }
    return String(v).trim();
  }

  function _mergeRecoveryScalar(incoming, baseVal, readFallback) {
    var inc = _cfNonEmptyStr(incoming);
    if (inc) {
      return inc;
    }
    var b = baseVal != null ? _cfNonEmptyStr(baseVal) : "";
    if (b) {
      return b;
    }
    if (typeof readFallback === "function") {
      try {
        var fb = readFallback();
        return fb != null ? _cfNonEmptyStr(fb) : "";
      } catch (eFb) {
        return "";
      }
    }
    return "";
  }

  function cartflowMergePersistDurableRecoveryReturnState(patch) {
    patch = patch || {};
    var baseRaw = cartflowReadDurableRecoveryReturnState();
    var base = baseRaw && typeof baseRaw === "object" ? baseRaw : {};
    var sid = getRecoverySessionId();
    var cid = getStableCartEventIdForTracking();
    var store = getCartflowStoreSlugForPayload();

    var reason_tag = _mergeRecoveryScalar(
      patch.reason_tag,
      base.reason_tag,
      function () {
        return typeof window.cartflowGetReasonTag === "function"
          ? window.cartflowGetReasonTag()
          : "";
      }
    );
    if (!reason_tag) {
      try {
        reason_tag = _cfNonEmptyStr(window.sessionStorage.getItem(CF_REASON_TAG_SS));
      } catch (eSs) {
        reason_tag = "";
      }
    }
    reason_tag = reason_tag ? reason_tag.slice(0, 64) : "";

    var reason_sub_tag = _mergeRecoveryScalar(
      patch.reason_sub_tag,
      base.reason_sub_tag,
      function () {
        return typeof window.cartflowGetReasonSubTag === "function"
          ? window.cartflowGetReasonSubTag()
          : "";
      }
    );
    if (!reason_sub_tag) {
      try {
        reason_sub_tag = _cfNonEmptyStr(
          window.sessionStorage.getItem(CF_REASON_SUB_TAG_SS)
        );
      } catch (eS2) {
        reason_sub_tag = "";
      }
    }
    reason_sub_tag = reason_sub_tag ? reason_sub_tag.slice(0, 64) : "";

    var last_activity = _mergeRecoveryScalar(
      patch.last_activity,
      base.last_activity,
      function () {
        try {
          return window.sessionStorage.getItem(CF_RECOVERY_LAST_ACTIVITY_SS) || "";
        } catch (eLa) {
          return "";
        }
      }
    );
    last_activity = last_activity ? last_activity.slice(0, 80) : "";

    var customer_phone = _mergeRecoveryScalar(
      patch.customer_phone,
      base.customer_phone,
      function () {
        var w = getOptionalCartflowCustomerPhone();
        if (w) {
          return w;
        }
        var t = readCfTestCustomerPhoneForPayload();
        if (t) {
          return t;
        }
        try {
          var ls = window.localStorage.getItem(CF_LS_CUSTOMER_PHONE);
          return ls != null ? String(ls) : "";
        } catch (eLs) {
          return "";
        }
      }
    );
    customer_phone = customer_phone ? customer_phone.slice(0, 100) : "";

    var recovery_started_at = _cfNonEmptyStr(base.recovery_started_at);
    if (!recovery_started_at) {
      recovery_started_at = new Date().toISOString();
    }

    if (!last_activity) {
      last_activity = new Date().toISOString().slice(0, 80);
    }

    var out = {
      v: 1,
      recovery_flow_started: "1",
      session_id: sid,
      cart_id: cid,
      store_slug: store,
      ts: Date.now(),
      recovery_started_at: recovery_started_at,
      reason_tag: reason_tag || null,
      last_activity: last_activity || null,
    };
    if (reason_sub_tag) {
      out.reason_sub_tag = reason_sub_tag;
    }
    if (customer_phone) {
      out.customer_phone = customer_phone;
    }

    try {
      window.localStorage.setItem(
        CF_RECOVERY_RETURN_STATE_LS_KEY,
        JSON.stringify(out)
      );
    } catch (ePs) {
      /* ignore */
    }
    try {
      console.log(
        "[RECOVERY CONTEXT PERSISTED] session_id=" +
          String(sid) +
          " cart_id=" +
          String(cid) +
          " reason_tag=" +
          (out.reason_tag != null ? String(out.reason_tag) : "") +
          " last_activity=" +
          (out.last_activity != null ? String(out.last_activity) : "")
      );
    } catch (eLog) {
      /* ignore */
    }
  }

  function cartflowPersistDurableRecoveryReturnState() {
    cartflowMergePersistDurableRecoveryReturnState({});
  }

  window.cartflowRefreshDurableRecoveryContext = cartflowMergePersistDurableRecoveryReturnState;

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

  cartflowHydrateDurableRecoveryReturnState();

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
    var cfTestPh = readCfTestCustomerPhoneForPayload();
    if (cfTestPh) {
      bodyObj.cf_test_phone = cfTestPh;
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
        try {
          var st = response && response.status;
          var body = response && response.body;
          if (st === 200 && body && body.ok !== false) {
            cartflowMarkRecoveryFlowStarted();
          }
        } catch (eOk) {
          /* ignore */
        }
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

  function cartflowMarkRecoveryFlowStarted() {
    try {
      window.sessionStorage.setItem(CF_RECOVERY_FLOW_STARTED_KEY, "1");
    } catch (eMs) {
      /* ignore */
    }
    cartflowPersistDurableRecoveryReturnState();
  }
  window.cartflowMarkRecoveryFlowStarted = cartflowMarkRecoveryFlowStarted;

  window.cartflowSendUserReturnedToSite = function () {
    return Promise.resolve();
  };

  /* للوحة ‎/demo*‎: معرفة الجلسة نفسه بدون تكرار المنطق */
  window.cartflowGetSessionId = getRecoverySessionId;
})();
