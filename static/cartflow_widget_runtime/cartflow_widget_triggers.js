/**
 * Hesitation + exit-intent timers only (delegates presentation to flows).
 */
(function () {
  "use strict";

  var Cf = window.CartflowWidgetRuntime || {};
  var Hooks = {
    fireCartRecovery: null,
    fireExitNoCart: null,
    fireExitWithCart: null,
  };

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

  function clearAnchors(st) {
    if (Cf.State) {
      Cf.State.clearHesitationTimers();
    }
    try {
      if (st.step1Poll != null) {
        clearInterval(st.step1Poll);
        st.step1Poll = null;
      }
    } catch (eP) {}
  }

  function scheduleCartHesitation(st, flowsRef) {
    if (!(Cf.Config && Cf.Config.widgetGloballyAllowed())) {
      return;
    }
    try {
      if (
        !st.step1Ready &&
        !/\b\/demo\//i.test(String(window.location.pathname || ""))
      ) {
        return;
      }
    } catch (eS1) {}
    var tr = Cf.Config.widgetTrigger();
    if (!tr || tr.hesitation_trigger_enabled === false) {
      return;
    }
    if (Cf.Config.hesitationCondition() !== "after_cart_add") {
      return;
    }
    clearAnchors(st);
    var ms = hesitationMs();
    try {
      console.log("[CF TIMER SCHEDULE V2]", { ms: ms, source: "after_cart_intent" });
    } catch (eLg) {}
    st.hesitationAnchorTimer = setTimeout(function () {
      st.hesitationAnchorTimer = null;
      if (typeof Hooks.fireCartRecovery === "function") {
        Hooks.fireCartRecovery("cart_heistation_timer");
      } else if (flowsRef && typeof flowsRef.onHesitationTimerFire === "function") {
        flowsRef.onHesitationTimerFire();
      }
    }, ms);
  }

  function scheduleInactivityBubble(st, flowsRef, delayMs) {
    clearAnchors(st);
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
      var fq = Cf.Config.normalizeToken(tr.exit_intent_frequency, ["per_session", "per_24h", "no_rapid_repeat"], "per_session");
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

  /** Wrap cart sync so hesitation anchor stays single-flight. */
  function patchCartflowSync(st, flowsRef) {
    var prior = typeof window.cartflowSyncCartState === "function"
      ? window.cartflowSyncCartState
      : null;
    window.cartflowSyncCartState = function (reason) {
      if (typeof prior === "function") {
        try {
          prior(reason);
        } catch (eP) {}
      }
      Cf.State.mirrorCartTotalsFromGlobals();
      try {
        if (!st.step1Ready && !/\b\/demo\//i.test(String(window.location.pathname || ""))) {
          return;
        }
      } catch (eS1) {}
      try {
        if (window.CartFlowState) {
          window.CartFlowState.lastIntentAt = Date.now();
        }
      } catch (eLt) {}
      var r = String(reason || "").toLowerCase();
      if (Cf.Config.widgetGloballyAllowed() && Cf.Config.hesitationCondition() === "after_cart_add") {
        if (
          !st.bubbleShown &&
          (r === "add" ||
            r === "remove" ||
            r === "clear" ||
            r === "abandon" ||
            r === "page_load")
        ) {
          scheduleCartHesitation(st, flowsRef);
        }
      }
    };
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
    bootstrapExitListeners(st, opts.flowsRef);
    patchCartflowSync(st, opts.flowsRef);
    try {
      document.addEventListener(
        "cf-demo-cart-updated",
        function () {
          if (Cf.Config.hesitationCondition() === "after_cart_add") {
            scheduleCartHesitation(st, opts.flowsRef);
          }
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
        scheduleCartHesitation(st, opts.flowsRef);
      },
    };
  }

  window.CartflowWidgetRuntime = Cf;
  window.CartflowWidgetRuntime.Triggers = {
    init: init,
    haveCartApprox: haveCartApprox,
  };
})();
