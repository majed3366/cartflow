/**
 * Hesitation + exit-intent timers (delegates UI to flows).
 * Cart interception installs at parse time — before flows/bootstrap — so add-to-cart is never missed.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime;
  var Hooks = {
    fireCartRecovery: null,
    fireExitNoCart: null,
    fireExitWithCart: null,
  };

  /** Set true after Triggers.init assigns Hooks + clears deferred backlog. */
  var v2TriggerInitDone = false;
  var v2DeferredScheduleReasons = [];

  function pageScopeAllows() {
    var tr =
      Cf.Config && Cf.Config.widgetTrigger ? Cf.Config.widgetTrigger() : {};
    var sc = String(tr.visibility_page_scope || "all").toLowerCase();
    var path = String(window.location.pathname || "");
    if (sc === "all") {
      return true;
    }
    try {
      if (sc === "product") {
        return /\/products?\//i.test(path) || /\/product\//i.test(path);
      }
      if (sc === "cart") {
        return /\/cart\b/i.test(path);
      }
    } catch (ePs) {}
    return true;
  }

  function haveCartApprox() {
    try {
      return (
        typeof window.cart !== "undefined" &&
        window.cart != null &&
        Array.isArray(window.cart) &&
        window.cart.length > 0
      );
    } catch (eHc) {
      return false;
    }
  }

  function hesitationMs() {
    var sec =
      Cf.Config && typeof Cf.Config.hesitationDelaySeconds === "function"
        ? Cf.Config.hesitationDelaySeconds()
        : 20;
    return Math.max(0, Math.floor(sec * 1000));
  }

  function exitBaselineMs() {
    var sens = Cf.Config ? Cf.Config.exitIntentSensitivity() : "medium";
    var base = sens === "low" ? 16000 : sens === "high" ? 6500 : 10000;
    var delaySec = Cf.Config.exitIntentDelaySeconds
      ? Cf.Config.exitIntentDelaySeconds()
      : 0;
    return base + Math.max(0, Math.min(60, delaySec)) * 1000;
  }

  function markExitSession() {
    try {
      sessionStorage.setItem("cartflow_cf_exit_intent_fired_sess_v2", "1");
    } catch (eSs) {}
  }

  function exitAlreadyThisSession() {
    try {
      return sessionStorage.getItem("cartflow_cf_exit_intent_fired_sess_v2") === "1";
    } catch (eR) {
      return false;
    }
  }

  function clearHesitationTimersOnly(st) {
    if (Cf.State && typeof Cf.State.clearHesitationTimers === "function") {
      Cf.State.clearHesitationTimers();
    }
    /** Do NOT clear st.step1Poll — owned by flows ensureStep1. */
  }

  /** Central entry: storefront cartflowSyncCartState + cartflowRegisterNewIntent. */
  function onV2CartChannel(sourceTag, detail) {
    detail = detail || {};
    try {
      console.log("[CF V2 CART EVENT RECEIVED]", { source: sourceTag, detail: detail });
    } catch (eL0) {}

    if (!Cf.State || typeof Cf.State.mirrorCartTotalsFromGlobals !== "function") {
      return;
    }
    Cf.State.mirrorCartTotalsFromGlobals();

    var rsEarly = String(detail.reason || "").toLowerCase();
    var addDetected =
      detail.kind === "add_to_cart" ||
      sourceTag === "demo_dom" ||
      (sourceTag === "sync" && rsEarly === "add");
    if (addDetected) {
      try {
        console.log("[CF V2 ADD TO CART DETECTED]", {
          source: sourceTag,
          reason: detail.reason,
          kind: detail.kind,
        });
      } catch (eAd) {}
    }

    try {
      if (window.CartFlowState && sourceTag !== "replay") {
        window.CartFlowState.lastIntentAt = Date.now();
      }
    } catch (eLf) {}

    if (!(Cf.Config && Cf.Config.widgetGloballyAllowed())) {
      return;
    }

    try {
      if (Cf.State.checkoutPathActive && Cf.State.checkoutPathActive()) {
        var tr0 = Cf.Config.widgetTrigger();
        if (tr0 && tr0.suppress_when_checkout_started !== false) {
          return;
        }
      }
    } catch (eCk) {}

    if (Cf.Config.hesitationCondition() !== "after_cart_add") {
      return;
    }

    var stInt = Cf.State.internals ? Cf.State.internals : null;
    if (!stInt) {
      return;
    }
    if (stInt.bubbleShown) {
      return;
    }

    if (!haveCartApprox()) {
      return;
    }
    try {
      console.log("[CF V2 HESITATION ELIGIBLE]", { source: sourceTag });
    } catch (eHel) {}

    if (!v2TriggerInitDone) {
      try {
        v2DeferredScheduleReasons.push(sourceTag);
      } catch (ePu) {}
      return;
    }
    scheduleCartHesitation(stInt, {});
  }

  function scheduleCartHesitation(st, flowsRef) {
    if (!(Cf.Config && Cf.Config.widgetGloballyAllowed())) {
      return;
    }
    var tr = Cf.Config.widgetTrigger();
    if (!tr || tr.hesitation_trigger_enabled === false) {
      return;
    }
    if (Cf.Config.hesitationCondition() !== "after_cart_add") {
      return;
    }
    clearHesitationTimersOnly(st);
    var ms = hesitationMs();
    try {
      console.log("[CF TIMER SCHEDULE V2]", {
        ms: ms,
        source: "after_cart_add",
        hesitation_after_seconds: ms / 1000,
      });
    } catch (eLg) {}
    st.hesitationAnchorTimer = setTimeout(function () {
      st.hesitationAnchorTimer = null;
      try {
        console.log("[CF TIMER FIRE]", { delay_ms: ms });
      } catch (eTf) {}
      if (typeof Hooks.fireCartRecovery === "function") {
        Hooks.fireCartRecovery("cart_hesitation_timer");
      } else if (flowsRef && typeof flowsRef.onHesitationTimerFire === "function") {
        flowsRef.onHesitationTimerFire();
      }
    }, ms);
  }

  function scheduleInactivityBubble(st, flowsRef, delayMs) {
    clearHesitationTimersOnly(st);
    st.idlePollTimer = setTimeout(function () {
      st.idlePollTimer = null;
      if (
        Cf.Config.widgetTrigger &&
        Cf.Config.hesitationCondition() === "inactivity" &&
        typeof Hooks.fireCartRecovery === "function"
      ) {
        Hooks.fireCartRecovery("cart_inactivity_timer");
      } else if (flowsRef && typeof flowsRef.onIdleTimerFire === "function") {
        flowsRef.onIdleTimerFire();
      }
    }, delayMs || 120000);
  }

  function bootstrapExitListeners(st, flowsRef) {
    function maybeFireExit() {
      if (!(Cf.Config && Cf.Config.widgetGloballyAllowed())) {
        return;
      }
      var tr = Cf.Config.widgetTrigger();
      if (!tr.exit_intent_enabled) {
        return;
      }
      if (Cf.State.sessionConvertedBlock()) {
        return;
      }
      if (Cf.State.readDismissSuppress() && tr.suppress_after_widget_dismiss !== false) {
        return;
      }
      if (Cf.State.checkoutPathActive() && tr.suppress_when_checkout_started !== false) {
        return;
      }
      if (!pageScopeAllows()) {
        try {
          console.log("[CF EXIT INTENT BLOCKED V2]", { gate: "page_scope" });
        } catch (eB) {}
        return;
      }
      var fq = Cf.Config.normalizeToken(
        tr.exit_intent_frequency,
        ["per_session", "per_24h", "no_rapid_repeat"],
        "per_session"
      );
      if (fq === "per_session" && exitAlreadyThisSession()) {
        try {
          console.log("[CF EXIT INTENT BLOCKED V2]", { gate: "per_session_already" });
        } catch (eB2) {}
        return;
      }
      try {
        console.log("[CF EXIT INTENT SCHEDULED V2]", { has_cart: haveCartApprox() });
      } catch (eLs) {}
      clearTimeout(st.exitInactivityTimer);
      st.exitInactivityTimer = setTimeout(function () {
        try {
          console.log("[CF EXIT INTENT FIRE V2]");
        } catch (eF) {}
        markExitSession();
        st.last_exit_fire_ts = Date.now();
        if (!haveCartApprox()) {
          if (typeof Hooks.fireExitNoCart === "function") {
            Hooks.fireExitNoCart();
          }
        } else {
          if (typeof Hooks.fireExitWithCart === "function") {
            Hooks.fireExitWithCart();
          }
        }
      }, exitBaselineMs());
    }

    document.addEventListener(
      "mouseout",
      function (ev) {
        try {
          if (!ev.relatedTarget && ev.clientY < 40) {
            maybeFireExit();
          }
        } catch (em) {}
      },
      false
    );
    document.addEventListener(
      "visibilitychange",
      function () {
        try {
          if (document.visibilityState === "hidden") {
            maybeFireExit();
          }
        } catch (ev) {}
      },
      false
    );
  }

  /** Install wrappers as soon as this file loads — before flows/legacy_bridge. */
  function installStorefrontCartBridgeEarly() {
    if (window.__cfV2StorefrontCartBridgeInstalled === true) {
      return;
    }
    window.__cfV2StorefrontCartBridgeInstalled = true;

    var priorSync =
      typeof window.cartflowSyncCartState === "function"
        ? window.cartflowSyncCartState
        : null;
    window.cartflowSyncCartState = function (reason) {
      if (typeof priorSync === "function") {
        try {
          priorSync(reason);
        } catch (eP) {}
      }
      onV2CartChannel("sync", { reason: reason });
    };

    var priorReg =
      typeof window.cartflowRegisterNewIntent === "function"
        ? window.cartflowRegisterNewIntent
        : null;
    window.cartflowRegisterNewIntent = function (kind) {
      if (typeof priorReg === "function") {
        try {
          priorReg.apply(this, arguments);
        } catch (eR) {}
      }
      onV2CartChannel("register_intent", { kind: kind });
    };
  }

  installStorefrontCartBridgeEarly();

  function flushDeferredScheduling(st, flowsRef) {
    var had = false;
    try {
      had = v2DeferredScheduleReasons.length > 0;
      v2DeferredScheduleReasons.length = 0;
    } catch (eE) {}
    if (had && st && !st.bubbleShown && haveCartApprox()) {
      scheduleCartHesitation(st, flowsRef || {});
    }
  }

  function init(opts) {
    var st =
      Cf.State && Cf.State.internals ? Cf.State.internals : {};
    Hooks.fireCartRecovery =
      opts && typeof opts.fireCartRecovery === "function"
        ? opts.fireCartRecovery
        : Hooks.fireCartRecovery;
    Hooks.fireExitNoCart =
      opts && typeof opts.fireExitNoCart === "function"
        ? opts.fireExitNoCart
        : Hooks.fireExitNoCart;
    Hooks.fireExitWithCart =
      opts && typeof opts.fireExitWithCart === "function"
        ? opts.fireExitWithCart
        : Hooks.fireExitWithCart;

    v2TriggerInitDone = true;

    bootstrapExitListeners(st, opts.flowsRef);
    flushDeferredScheduling(st, opts.flowsRef);

    try {
      document.addEventListener(
        "cf-demo-cart-updated",
        function () {
          onV2CartChannel("demo_dom", { kind: "add_to_cart", synthetic: true });
        },
        false
      );
    } catch (eDemo) {}

    var cond = Cf.Config.hesitationCondition();
    if (cond === "inactivity") {
      scheduleInactivityBubble(st, opts.flowsRef, 120000);
    }
    return {
      scheduleCartHesitation: function () {
        scheduleCartHesitation(st, {});
      },
    };
  }

  var Triggers = {
    init: init,
    haveCartApprox: haveCartApprox,
  };
  window.CartflowWidgetRuntime.Triggers = Triggers;
})();
