/**
 * V2 Trigger Orchestrator — owns when the widget may open; never renders UI.
 * Delegates to Flows via hooks registered at init (CartflowWidgetRuntime.Flows bootstrap).
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

  var v2TriggerInitDone = false;
  var v2DeferredScheduleReasons = [];

  /** One pending resume coalesce (same tick merges pageshow + visibilitychange). */
  var resumeFlushTimer = null;

  function trigLog(tag, meta) {
    try {
      if (meta !== undefined && meta !== null) {
        console.log(tag, meta);
      } else {
        console.log(tag);
      }
    } catch (eL) {}
  }

  function logReceived(source, extra) {
    trigLog("[CF TRIGGER RECEIVED]", Object.assign({ source: source }, extra || {}));
  }

  function logScheduled(source, extra) {
    trigLog("[CF TRIGGER SCHEDULED]", Object.assign({ source: source }, extra || {}));
  }

  function logFired(source, extra) {
    trigLog("[CF TRIGGER FIRED]", Object.assign({ source: source }, extra || {}));
  }

  function logBlocked(reason, extra) {
    trigLog("[CF TRIGGER BLOCKED]", Object.assign({ reason: reason }, extra || {}));
  }

  function logAllowed(extra) {
    trigLog("[CF TRIGGER ALLOWED]", extra || {});
  }

  function logCleared(extra) {
    trigLog("[CF TRIGGER CLEARED]", extra || {});
  }

  function merchantWidgetDisabled() {
    try {
      var M = Cf.Config.merchant();
      if (!M) {
        return false;
      }
      if (M.widget_enabled === false) {
        return true;
      }
      if (
        typeof M.prompt_not_before_ms === "number" &&
        isFinite(M.prompt_not_before_ms) &&
        Date.now() < M.prompt_not_before_ms
      ) {
        return true;
      }
    } catch (eM) {}
    return false;
  }

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

  function st() {
    return Cf.State && Cf.State.internals ? Cf.State.internals : {};
  }

  function emitHesitationFireLogs(deadlineMs) {
    var actual = Date.now();
    var drift =
      deadlineMs != null && isFinite(deadlineMs) ? actual - deadlineMs : 0;
    try {
      console.log("[CF V2 TIMER FIRE]", {
        actual_fire_at: actual,
        drift_ms: drift,
      });
      console.log("[CF V2 SHOW NOW]");
    } catch (eL) {}
  }

  function fireCartRecoveryAfterHesitation(stInner, flowsRef) {
    stInner.hesitationAnchorTimer = null;
    var dl = stInner.cfV2HesitationDeadlineAt;
    stInner.cfV2HesitationDeadlineAt = null;
    emitHesitationFireLogs(dl);
    logFired("add_to_cart", {
      timer: "hesitation_anchor",
    });
    if (typeof Hooks.fireCartRecovery === "function") {
      Hooks.fireCartRecovery("cart_hesitation_timer");
    } else if (flowsRef && typeof flowsRef.onHesitationTimerFire === "function") {
      flowsRef.onHesitationTimerFire();
    }
  }

  function clearHesitationTimersOnly() {
    if (Cf.State && typeof Cf.State.clearHesitationTimers === "function") {
      Cf.State.clearHesitationTimers();
    }
  }

  /** Gate opening cart-recovery style flows (normalized Config + State only). */
  function gateCartRecoveryOpen(extraTag) {
    try {
      Cf.State.mirrorCartTotalsFromGlobals();
    } catch (eM) {}
    if (Cf.State.sessionConvertedBlock()) {
      return { ok: false, reason: "purchase_completed" };
    }
    if (!Cf.Config.widgetGloballyAllowed()) {
      return { ok: false, reason: "widget_disabled" };
    }
    if (merchantWidgetDisabled()) {
      return { ok: false, reason: "widget_disabled" };
    }
    var tr = Cf.Config.widgetTrigger();
    if (
      Cf.State.checkoutPathActive() &&
      tr &&
      tr.suppress_when_checkout_started !== false
    ) {
      return { ok: false, reason: "checkout_started" };
    }
    if (
      Cf.State.readDismissSuppress() &&
      tr &&
      tr.suppress_after_widget_dismiss !== false
    ) {
      return { ok: false, reason: "recently_dismissed" };
    }
    if (!pageScopeAllows()) {
      return { ok: false, reason: "page_scope_blocked" };
    }
    if (!haveCartApprox()) {
      return { ok: false, reason: "no_cart" };
    }
    if (st().bubbleShown) {
      return { ok: false, reason: "frequency_blocked" };
    }
    return { ok: true, reason: null, tag: extraTag };
  }

  /** TEMP (stabilization): hesitation allows schedule only widget_disabled | no_cart. */
  function gateHesitationAfterCartAdd() {
    try {
      Cf.State.mirrorCartTotalsFromGlobals();
    } catch (eM) {}
    if (!Cf.Config.widgetGloballyAllowed()) {
      return { ok: false, reason: "widget_disabled" };
    }
    if (merchantWidgetDisabled()) {
      return { ok: false, reason: "widget_disabled" };
    }
    var tr = Cf.Config.widgetTrigger();
    if (!tr || tr.hesitation_trigger_enabled === false) {
      return { ok: false, reason: "widget_disabled" };
    }
    if (!haveCartApprox()) {
      return { ok: false, reason: "no_cart" };
    }
    return { ok: true, reason: null };
  }

  function gateExitIntentTimer() {
    if (!Cf.Config.widgetGloballyAllowed()) {
      return { ok: false, reason: "widget_disabled" };
    }
    if (merchantWidgetDisabled()) {
      return { ok: false, reason: "widget_disabled" };
    }
    var tr = Cf.Config.widgetTrigger();
    if (!tr || !tr.exit_intent_enabled) {
      return { ok: false, reason: "widget_disabled" };
    }
    if (Cf.State.sessionConvertedBlock()) {
      return { ok: false, reason: "purchase_completed" };
    }
    if (
      Cf.State.readDismissSuppress() &&
      tr &&
      tr.suppress_after_widget_dismiss !== false
    ) {
      return { ok: false, reason: "recently_dismissed" };
    }
    if (
      Cf.State.checkoutPathActive() &&
      tr &&
      tr.suppress_when_checkout_started !== false
    ) {
      return { ok: false, reason: "checkout_started" };
    }
    if (!pageScopeAllows()) {
      return { ok: false, reason: "page_scope_blocked" };
    }
    var fq = Cf.Config.normalizeToken(
      tr.exit_intent_frequency,
      ["per_session", "per_24h", "no_rapid_repeat"],
      "per_session"
    );
    if (fq === "per_session" && exitAlreadyThisSession()) {
      return { ok: false, reason: "frequency_blocked" };
    }
    return { ok: true, reason: null };
  }

  function scheduleCartHesitation(stRef, flowsRef, timingOpts) {
    timingOpts = timingOpts || {};
    flowsRef = flowsRef || {};
    var g = gateHesitationAfterCartAdd();
    if (!g.ok) {
      logBlocked(g.reason || "widget_disabled", {
        path: "hesitation_schedule",
      });
      return;
    }
    logAllowed({ path: "hesitation_schedule" });

    if (stRef.hesitationAnchorTimer != null) {
      logCleared({ cause: "timer_replaced", timer: "hesitation_anchor" });
    }
    clearHesitationTimersOnly();

    var baseMs =
      typeof timingOpts.armBaseAtMs === "number" && isFinite(timingOpts.armBaseAtMs)
        ? timingOpts.armBaseAtMs
        : Date.now();
    var msConfigured = hesitationMs();
    var deadline = baseMs + msConfigured;
    var remainingMs = Math.max(0, Math.floor(deadline - Date.now()));

    stRef.cfV2HesitationDeadlineAt = deadline;

    try {
      console.log("[CF V2 TIMER ARM]", {
        expected_fire_at: deadline,
      });
    } catch (eArm) {}

    logScheduled("add_to_cart", {
      delay_ms: remainingMs,
      timer: "hesitation_anchor",
      configured_delay_ms: msConfigured,
    });

    stRef.hesitationAnchorTimer = setTimeout(function () {
      fireCartRecoveryAfterHesitation(stRef, flowsRef);
    }, remainingMs);
  }

  function scheduleInactivityBubble(st, flowsRef, delayMs) {
    if (st.hesitationAnchorTimer != null || st.idlePollTimer != null) {
      logCleared({ cause: "timer_replaced", timer: "idle" });
    }
    clearHesitationTimersOnly();
    try {
      st.cfV2HesitationDeadlineAt = null;
    } catch (eDl) {}
    logScheduled("add_to_cart", {
      delay_ms: delayMs || 120000,
      timer: "inactivity",
      note: "hesitation_condition_inactivity",
    });
    st.idlePollTimer = setTimeout(function () {
      st.idlePollTimer = null;
      logFired("add_to_cart", { timer: "inactivity" });
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

  function detectAddToCart(sourceTag, detail) {
    detail = detail || {};
    var rsEarly = String(detail.reason || "").toLowerCase();
    return (
      detail.kind === "add_to_cart" ||
      sourceTag === "demo_dom" ||
      (sourceTag === "sync" && rsEarly === "add")
    );
  }

  function onV2CartChannel(sourceTag, detail) {
    detail = detail || {};
    if (detectAddToCart(sourceTag, detail)) {
      logReceived("add_to_cart", { via: sourceTag });
    } else {
      logReceived("cart_channel", { via: sourceTag });
    }

    if (!Cf.State || typeof Cf.State.mirrorCartTotalsFromGlobals !== "function") {
      return;
    }
    Cf.State.mirrorCartTotalsFromGlobals();

    try {
      if (window.CartFlowState && sourceTag !== "replay") {
        window.CartFlowState.lastIntentAt = Date.now();
      }
    } catch (eLf) {}

    if (!v2TriggerInitDone) {
      try {
        st().cfV2HesitationDeferredBaseAt = Date.now();
      } catch (eB) {}
      try {
        v2DeferredScheduleReasons.push(sourceTag);
      } catch (ePu) {}
      return;
    }

    scheduleCartHesitation(st(), {});
  }

  function scheduleExitIntentTimer(st) {
    logReceived("exit_intent", { phase: "raw" });

    var g = gateExitIntentTimer();
    if (!g.ok) {
      logBlocked(g.reason, { path: "exit_intent_schedule" });
      return;
    }

    if (st.exitInactivityTimer != null) {
      logCleared({ cause: "timer_replaced", timer: "exit_intent" });
      try {
        clearTimeout(st.exitInactivityTimer);
      } catch (eC) {}
      st.exitInactivityTimer = null;
    }

    var delayMs = exitBaselineMs();
    logScheduled("exit_intent", { delay_ms: delayMs, timer: "exit_intent" });

    st.exitInactivityTimer = setTimeout(function () {
      st.exitInactivityTimer = null;
      markExitSession();
      st.last_exit_fire_ts = Date.now();
      logFired("exit_intent", { has_cart: haveCartApprox() });
      if (!haveCartApprox()) {
        if (typeof Hooks.fireExitNoCart === "function") {
          Hooks.fireExitNoCart();
        }
      } else {
        if (typeof Hooks.fireExitWithCart === "function") {
          Hooks.fireExitWithCart();
        }
      }
    }, delayMs);
  }

  function bootstrapExitListeners(st, flowsRef) {
    function onExitProbe() {
      scheduleExitIntentTimer(st);
    }

    document.addEventListener(
      "mouseout",
      function (ev) {
        try {
          if (!ev.relatedTarget && ev.clientY < 40) {
            onExitProbe();
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
            onExitProbe();
          }
        } catch (ev) {}
      },
      false
    );
  }

  function enqueueVisibilityResumeSoon() {
    try {
      window.clearTimeout(resumeFlushTimer);
    } catch (eC) {}
    resumeFlushTimer = window.setTimeout(function () {
      resumeFlushTimer = null;
      try {
        receiveTrigger("visibility_resume", { from: "tab_visible_or_pageshow" });
      } catch (eR) {}
    }, 0);
  }

  function installVisibilityResumeListener() {
    document.addEventListener(
      "visibilitychange",
      function () {
        try {
          if (document.visibilityState === "visible") {
            enqueueVisibilityResumeSoon();
          }
        } catch (ev) {}
      },
      false
    );

    window.addEventListener(
      "pageshow",
      function (ev) {
        try {
          enqueueVisibilityResumeSoon();
        } catch (eP) {}
      },
      false
    );
  }

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

  function flushDeferredScheduling(stRef, flowsRef) {
    var had = false;
    try {
      had = v2DeferredScheduleReasons.length > 0;
      v2DeferredScheduleReasons.length = 0;
    } catch (eE) {}
    if (!had || !stRef || stRef.bubbleShown || !haveCartApprox()) {
      return;
    }
    var baseAt =
      stRef.cfV2HesitationDeferredBaseAt != null
        ? stRef.cfV2HesitationDeferredBaseAt
        : Date.now();
    try {
      stRef.cfV2HesitationDeferredBaseAt = null;
    } catch (eC) {}
    scheduleCartHesitation(stRef, flowsRef || {}, { armBaseAtMs: baseAt });
  }

  /**
   * External entry: manual_debug, visibility_resume.
   * add_to_cart and exit_intent use internal paths above.
   */
  function receiveTrigger(source, detail) {
    detail = detail || {};
    logReceived(source, detail);

    if (source === "manual_debug") {
      if (!v2TriggerInitDone) {
        return null;
      }
      var gm = gateCartRecoveryOpen("manual_debug");
      if (!gm.ok) {
        logBlocked(gm.reason, { source: source });
        return false;
      }
      if (typeof Hooks.fireCartRecovery !== "function") {
        logBlocked("widget_disabled", { source: source, note: "hooks_missing" });
        return false;
      }
      logFired("manual_debug", { direct: true });
      Hooks.fireCartRecovery("manual_debug");
      return true;
    }

    if (source === "visibility_resume") {
      if (!v2TriggerInitDone) {
        return null;
      }
      Cf.State.mirrorCartTotalsFromGlobals();

      var stRef = st();
      var dl = stRef.cfV2HesitationDeadlineAt;
      var deadlinePassed =
        dl != null && isFinite(dl) && Date.now() >= dl && haveCartApprox();

      try {
        console.log("[CF V2 RETURN RESUME]", {
          delay_passed: !!deadlinePassed,
        });
      } catch (eRs) {}

      if (!haveCartApprox() || stRef.bubbleShown) {
        return true;
      }

      if (deadlinePassed && dl != null) {
        var gm = gateCartRecoveryOpen("visibility_resume");
        if (!gm.ok) {
          return true;
        }
        if (stRef.hesitationAnchorTimer != null) {
          try {
            clearTimeout(stRef.hesitationAnchorTimer);
          } catch (eCt) {}
          stRef.hesitationAnchorTimer = null;
        }
        stRef.cfV2HesitationDeadlineAt = null;
        emitHesitationFireLogs(dl);
        logFired("visibility_resume", { timer: "hesitation_catch_up" });
        if (typeof Hooks.fireCartRecovery === "function") {
          Hooks.fireCartRecovery("cart_hesitation_timer");
        }
        return true;
      }

      if (
        dl != null &&
        isFinite(dl) &&
        gateHesitationAfterCartAdd().ok
      ) {
        var remainder = Math.max(0, Math.floor(dl - Date.now()));
        try {
          if (stRef.hesitationAnchorTimer != null) {
            clearTimeout(stRef.hesitationAnchorTimer);
          }
        } catch (eCrs) {}
        stRef.hesitationAnchorTimer = setTimeout(function () {
          fireCartRecoveryAfterHesitation(stRef, {});
        }, remainder);
      }

      return true;
    }

    logBlocked("widget_disabled", { source: source, note: "unknown_trigger_source" });
    return false;
  }

  function init(opts) {
    var stRef =
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

    bootstrapExitListeners(stRef, opts.flowsRef);
    installVisibilityResumeListener();
    flushDeferredScheduling(stRef, opts.flowsRef);

    try {
      document.addEventListener(
        "cf-demo-cart-updated",
        function () {
          onV2CartChannel("demo_dom", {
            kind: "add_to_cart",
            synthetic: true,
          });
        },
        false
      );
    } catch (eDemo) {}

    var cond = Cf.Config.hesitationCondition();
    if (cond === "inactivity") {
      scheduleInactivityBubble(stRef, opts.flowsRef, 120000);
    }

    trigLog("[CF TRIGGER ORCHESTRATOR READY]", {
      hesitation_condition: cond,
    });

    return {
      scheduleCartHesitation: function () {
        scheduleCartHesitation(stRef, {});
      },
    };
  }

  var Triggers = {
    init: init,
    haveCartApprox: haveCartApprox,
    receiveTrigger: receiveTrigger,
  };
  window.CartflowWidgetRuntime.Triggers = Triggers;
})();
