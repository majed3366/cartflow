/**
 * Stateful runtime snapshot — no rendering.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var LS_PHONE = "cartflow_customer_phone";
  var ST = {
    hesitationTimer: null,
    hesitationAnchorTimer: null,
    idlePollTimer: null,
    exitInactivityTimer: null,
    step1Poll: null,
    step1Ready: false,
    bubbleShown: false,
    dismissSuppress: false,
    open_source: null,
    pending_reason_payload: null,
    pending_reason_detail: null,
    pending_reason_key: null,
    background_retry_meta: null,
    background_save_failed: false,
    last_exit_fire_ts: 0,
    exit_session_block: false,
    shell: {
      isOpen: false,
      currentStep: null,
      loading: false,
      mountedView: null,
      lastTriggerSource: null,
    },
  };

  function readDismissSuppress() {
    try {
      return window.sessionStorage.getItem("cartflow_cf_suppress_after_dismiss") === "1";
    } catch (e1) {
      return false;
    }
  }

  window.cartflowState =
    window.cartflowState ||
    {
      cartTotal: 0,
      itemsCount: 0,
      vipThreshold: 500,
      isVip: false,
    };

  window.CartFlowState =
    window.CartFlowState ||
    {
      hasCart: false,
      widgetShown: false,
      userRejectedHelp: false,
      rejectionTimestamp: null,
      lastIntentAt: null,
    };

  function normalizePhoneDigits(s) {
    var d = String(s || "").replace(/\D/g, "");
    if (d.length === 10 && d.slice(0, 2) === "05") {
      d = "966" + d.slice(1);
    } else if (d.length === 9 && d.charAt(0) === "5") {
      d = "966" + d;
    }
    return /^9665\d{8}$/.test(d) ? d : "";
  }

  function getStoredPhoneNorm() {
    try {
      return normalizePhoneDigits(window.localStorage.getItem(LS_PHONE));
    } catch (eLs) {
      return "";
    }
  }

  function hasValidStoredPhone() {
    return !!getStoredPhoneNorm();
  }

  function mirrorCartTotalsFromGlobals() {
    try {
      var cart =
        typeof window.cart !== "undefined" && Array.isArray(window.cart) ? window.cart : [];
      var total = typeof window.cart_total === "number" ? window.cart_total : 0;
      var th =
        typeof window.cartflowVipCartThreshold !== "undefined" &&
        window.cartflowVipCartThreshold != null &&
        window.cartflowVipCartThreshold !== ""
          ? Number(window.cartflowVipCartThreshold)
          : typeof window.vip_threshold === "number"
          ? Number(window.vip_threshold)
          : window.cartflowState && window.cartflowState.vipThreshold;
      window.cartflowState.itemsCount = cart.length;
      window.cartflowState.cartTotal = isFinite(total) ? total : 0;
      window.cartflowState.vipThreshold = isFinite(th) ? th : 500;
      window.cartflowState.isVip =
        cart.length > 0 &&
        isFinite(window.cartflowState.vipThreshold) &&
        window.cartflowState.cartTotal >= window.cartflowState.vipThreshold;
    } catch (eMt) {}
  }

  function clearTimers() {
    try {
      if (ST.hesitationTimer != null) {
        clearTimeout(ST.hesitationTimer);
      }
    } catch (e1) {}
    try {
      if (ST.hesitationAnchorTimer != null) {
        clearTimeout(ST.hesitationAnchorTimer);
      }
    } catch (e2) {}
    try {
      if (ST.idlePollTimer != null) {
        clearTimeout(ST.idlePollTimer);
      }
    } catch (e3) {}
    ST.hesitationTimer = null;
    ST.hesitationAnchorTimer = null;
    ST.idlePollTimer = null;
  }

  function checkoutPathActive() {
    try {
      var p =
        String(window.location.pathname || "") + String(window.location.search || "");
      return /\/checkout\b/i.test(p);
    } catch (eCk) {
      return false;
    }
  }

  function sessionConvertedBlock() {
    try {
      if (
        typeof window.cartflowIsSessionConverted === "function" &&
        window.cartflowIsSessionConverted()
      ) {
        return true;
      }
    } catch (eC) {}
    try {
      return window.sessionStorage.getItem("cartflow_converted") === "1";
    } catch (eS) {}
    return false;
  }

  function shellState() {
    return ST.shell;
  }

  var State = {
    internals: ST,
    shellState: shellState,
    readDismissSuppress: readDismissSuppress,
    normalizePhoneDigits: normalizePhoneDigits,
    getStoredPhoneNorm: getStoredPhoneNorm,
    hasValidStoredPhone: hasValidStoredPhone,
    mirrorCartTotalsFromGlobals: mirrorCartTotalsFromGlobals,
    clearHesitationTimers: clearTimers,
    checkoutPathActive: checkoutPathActive,
    sessionConvertedBlock: sessionConvertedBlock,
    LS_CUSTOMER_PHONE: LS_PHONE,
  };
  window.CartflowWidgetRuntime.State = State;
})();
