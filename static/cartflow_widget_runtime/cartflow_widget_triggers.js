/**
 * V2 Trigger Orchestrator — owns when the widget may open; never renders UI.
 * Delegates to Flows via hooks registered at init (CartflowWidgetRuntime.Flows bootstrap).
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function () {
  "use strict";

  // TEMP DIAGNOSTICS (no behavior change): prove this module actually evaluates
  // on the real storefront and surface any evaluation exception with a stack,
  // so we can tell a fetch/parse failure ([CF V2 MODULE FAILED]) apart from a
  // runtime error that aborts registration.
  try {
    console.log("[CF TRIGGERS INIT]", {
      build: window.CARTFLOW_RUNTIME_VERSION || "",
      runtime_present: !!window.CartflowWidgetRuntime,
      href: (window.location && window.location.href) || "",
    });
  } catch (eTrigInit) {}

  try {
  var Cf = window.CartflowWidgetRuntime;
  var Hooks = {
    fireCartRecovery: null,
    fireExitNoCart: null,
    fireExitWithCart: null,
  };

  var v2TriggerInitDone = false;
  var v2DeferredScheduleReasons = [];
  var v2DeferredReplayTimer = null;
  var V2_DEFERRED_REPLAY_INTERVAL_MS = 250;
  var V2_DEFERRED_REPLAY_MAX_MS = 12000;

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

  /**
   * TEMP DIAGNOSTICS (no behavior change): snapshot every individual gate
   * condition so the single reason a trigger is blocked is visible on real
   * storefronts. Pure read-only; never mutates state or alters gating.
   */
  function diagSafe(fn) {
    try {
      return fn();
    } catch (eDs) {
      return null;
    }
  }

  function collectTriggerGateDiagnostics(triggerTag) {
    var tr = diagSafe(function () {
      return (Cf.Config && Cf.Config.widgetTrigger
        ? Cf.Config.widgetTrigger()
        : null) || {};
    }) || {};
    var M = diagSafe(function () {
      return (Cf.Config && Cf.Config.merchant ? Cf.Config.merchant() : null) || {};
    }) || {};
    var promptNotBefore = null;
    try {
      if (
        typeof M.prompt_not_before_ms === "number" &&
        isFinite(M.prompt_not_before_ms)
      ) {
        promptNotBefore = M.prompt_not_before_ms;
      }
    } catch (ePnb) {}
    return {
      widget_disabled_effective: diagSafe(merchantWidgetDisabled),
      widget_globally_allowed: diagSafe(function () {
        return Cf.Config.widgetGloballyAllowed();
      }),
      exit_intent_enabled: !!tr.exit_intent_enabled,
      hesitation_enabled: tr.hesitation_trigger_enabled !== false,
      frequency_blocked: !!st().bubbleShown,
      session_suppressed:
        diagSafe(function () {
          return Cf.State.sessionConvertedBlock();
        }) === true ||
        diagSafe(function () {
          return Cf.State.readDismissSuppress();
        }) === true,
      delay_not_ready: diagSafe(function () {
        return !!(
          Cf.State.hesitationDelayWallActive &&
          Cf.State.hesitationDelayWallActive()
        );
      }),
      prompt_not_before_ms: promptNotBefore,
      cart_required: true,
      cart_detected: diagSafe(haveCartApprox),
      recovery_mode: diagSafe(storefrontRecoveryModeActive),
      trigger_tag: String(triggerTag || ""),
    };
  }

  function emitTriggerDecision(triggerTag, allowed, blockReason) {
    trigLog("[CF TRIGGER DECISION]", {
      trigger_tag: String(triggerTag || ""),
      allowed: !!allowed,
      block_reason: allowed ? null : blockReason || "unknown",
    });
  }

  /**
   * TEMP DIAGNOSTICS (no behavior change): full read-only snapshot of the
   * hesitation-path state. Used to trace whether the hesitation timer ever
   * arms / fires / dispatches on real storefronts. Never mutates state.
   */
  function hesitationStateSnapshot(extra) {
    var tr = diagSafe(function () {
      return (Cf.Config && Cf.Config.widgetTrigger
        ? Cf.Config.widgetTrigger()
        : null) || {};
    }) || {};
    var snap = {
      cart_detected: diagSafe(haveCartApprox),
      hesitation_enabled: tr.hesitation_trigger_enabled !== false,
      hesitation_after_seconds: diagSafe(function () {
        return Cf.Config && typeof Cf.Config.hesitationDelaySeconds === "function"
          ? Cf.Config.hesitationDelaySeconds()
          : null;
      }),
      delay_ms: diagSafe(hesitationMs),
      hesitation_condition: diagSafe(function () {
        return Cf.Config && typeof Cf.Config.hesitationCondition === "function"
          ? Cf.Config.hesitationCondition()
          : null;
      }),
      widget_globally_allowed: diagSafe(function () {
        return Cf.Config.widgetGloballyAllowed();
      }),
      widget_disabled_effective: diagSafe(merchantWidgetDisabled),
      session_converted: diagSafe(function () {
        return Cf.State.sessionConvertedBlock();
      }),
      frequency_blocked: !!st().bubbleShown,
      suppression_dismiss: diagSafe(function () {
        return Cf.State.readDismissSuppress();
      }),
      recovery_mode: diagSafe(storefrontRecoveryModeActive),
      trigger_init_done: v2TriggerInitDone,
    };
    if (extra) {
      try {
        Object.keys(extra).forEach(function (k) {
          snap[k] = extra[k];
        });
      } catch (eMrg) {}
    }
    return snap;
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

  function storefrontRecoveryModeActive() {
    try {
      return window.CARTFLOW_RECOVERY_WIDGET_MODE === true;
    } catch (eRm) {
      return false;
    }
  }

  function haveCartApproxFromStorefrontPath() {
    try {
      if (!storefrontRecoveryModeActive()) {
        return false;
      }
      var path = String(window.location.pathname || "").toLowerCase();
      var href = String(window.location.href || "").toLowerCase();
      return (
        /\/cart(?:\/|$|\?|#)/.test(path) ||
        /\/checkout(?:\/|$|\?|#)/.test(path) ||
        /\/basket(?:\/|$|\?|#)/.test(path) ||
        /\/(cart|checkout|basket)(?:\/|$|\?|#)/.test(href)
      );
    } catch (ePath) {
      return false;
    }
  }

  function cartBridgeHasCart() {
    try {
      return !!(
        Cf.CartBridge &&
        typeof Cf.CartBridge.hasCart === "function" &&
        Cf.CartBridge.hasCart()
      );
    } catch (eCb) {
      return false;
    }
  }

  function storefrontBridgeHasCart() {
    try {
      var br = Cf.StorefrontCartBridge;
      if (!br || typeof br.getDiagnostics !== "function") {
        return false;
      }
      var d = br.getDiagnostics() || {};
      if (d.cart_persisted !== true) {
        return false;
      }
      var n = d.normalized;
      if (n && typeof n === "object") {
        if (typeof n.item_count === "number" && n.item_count > 0) {
          return true;
        }
        if (typeof n.cart_value === "number" && n.cart_value > 0) {
          return true;
        }
      }
      return true;
    } catch (eSf) {
      return false;
    }
  }

  function haveCartApprox() {
    try {
      if (
        typeof window.cart !== "undefined" &&
        window.cart != null &&
        Array.isArray(window.cart) &&
        window.cart.length > 0
      ) {
        return true;
      }
    } catch (eHc) {
      /* ignore */
    }
    if (cartBridgeHasCart()) {
      return true;
    }
    if (storefrontBridgeHasCart()) {
      return true;
    }
    return haveCartApproxFromStorefrontPath();
  }

  function clearDeferredReplayTimer() {
    if (v2DeferredReplayTimer != null) {
      try {
        clearTimeout(v2DeferredReplayTimer);
      } catch (eCr) {}
      v2DeferredReplayTimer = null;
    }
  }

  function recordDeferredArmIntent(sourceTag) {
    var tag = String(sourceTag || "unknown");
    try {
      var stRef = st();
      if (stRef.cfV2HesitationDeferredBaseAt == null) {
        stRef.cfV2HesitationDeferredBaseAt = Date.now();
      }
    } catch (eB) {}
    try {
      v2DeferredScheduleReasons.push(tag);
    } catch (ePu) {}
  }

  function hesitationAlreadyArmed(stRef) {
    try {
      return !!(
        stRef &&
        (stRef.hesitationAnchorTimer != null ||
          (stRef.cfV2HesitationDeadlineAt != null &&
            isFinite(stRef.cfV2HesitationDeadlineAt)))
      );
    } catch (eHa) {
      return false;
    }
  }

  function finalizeDeferredHesitation(stRef, flowsRef, timingOpts, via) {
    clearDeferredReplayTimer();
    timingOpts = timingOpts || {};
    try {
      stRef.cfV2HesitationDeferredBaseAt = null;
    } catch (eC) {}
    logReceived("add_to_cart", {
      via: via || "deferred_replay",
      replay: true,
    });
    scheduleCartHesitation(stRef, flowsRef || {}, timingOpts);
  }

  function scheduleDeferredReplay(stRef, flowsRef, baseAt, via) {
    clearDeferredReplayTimer();
    var startedAt = Date.now();
    trigLog("[CF TRIGGER DEFERRED REPLAY]", {
      via: String(via || "init_flush"),
      base_at_ms: baseAt != null && isFinite(baseAt) ? baseAt : null,
      started_at_ms: startedAt,
      phase: "start",
    });

    function attempt() {
      v2DeferredReplayTimer = null;
      if (!stRef || stRef.bubbleShown || hesitationAlreadyArmed(stRef)) {
        return;
      }
      var timingOpts = {};
      if (baseAt != null && isFinite(baseAt)) {
        timingOpts.armBaseAtMs = baseAt;
      }
      if (haveCartApprox()) {
        trigLog("[CF TRIGGER DEFERRED REPLAY]", {
          via: String(via || "init_flush"),
          outcome: "cart_detected",
          elapsed_ms: Date.now() - startedAt,
        });
        finalizeDeferredHesitation(stRef, flowsRef, timingOpts, via);
        return;
      }
      if (Date.now() - startedAt >= V2_DEFERRED_REPLAY_MAX_MS) {
        trigLog("[CF TRIGGER DEFERRED REPLAY]", {
          via: String(via || "init_flush"),
          outcome: "exhausted_explicit_schedule",
          elapsed_ms: Date.now() - startedAt,
        });
        finalizeDeferredHesitation(stRef, flowsRef, timingOpts, via);
        return;
      }
      v2DeferredReplayTimer = setTimeout(attempt, V2_DEFERRED_REPLAY_INTERVAL_MS);
    }

    v2DeferredReplayTimer = setTimeout(attempt, V2_DEFERRED_REPLAY_INTERVAL_MS);
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
    try {
      if (Cf.State && typeof Cf.State.clearV2HesitationDeadlinePersisted === "function") {
        Cf.State.clearV2HesitationDeadlinePersisted();
      }
    } catch (eClr) {}
    trigLog(
      "[CF HESITATION TIMER FIRED]",
      hesitationStateSnapshot({
        timer: "hesitation_anchor",
        deadline_at: dl != null && isFinite(dl) ? dl : null,
        drift_ms: dl != null && isFinite(dl) ? Date.now() - dl : null,
      })
    );
    emitHesitationFireLogs(dl);
    logFired("add_to_cart", {
      timer: "hesitation_anchor",
    });
    if (typeof Hooks.fireCartRecovery === "function") {
      trigLog(
        "[CF HESITATION DISPATCH]",
        hesitationStateSnapshot({ dispatch: "cart_hesitation_timer", via: "hook" })
      );
      Hooks.fireCartRecovery("cart_hesitation_timer");
    } else if (flowsRef && typeof flowsRef.onHesitationTimerFire === "function") {
      trigLog(
        "[CF HESITATION DISPATCH]",
        hesitationStateSnapshot({ dispatch: "cart_hesitation_timer", via: "flowsRef" })
      );
      flowsRef.onHesitationTimerFire();
    } else {
      trigLog(
        "[CF HESITATION SKIPPED]",
        hesitationStateSnapshot({ stage: "dispatch", reason: "no_dispatch_hook" })
      );
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
    if (
      Cf.State.readDismissSuppress() &&
      tr &&
      tr.suppress_after_widget_dismiss !== false
    ) {
      return { ok: false, reason: "recently_dismissed" };
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
      trigLog(
        "[CF TRIGGER BLOCKED REASON]",
        collectTriggerGateDiagnostics("cart_hesitation")
      );
      emitTriggerDecision("cart_hesitation", false, g.reason || "widget_disabled");
      trigLog(
        "[CF HESITATION SKIPPED]",
        hesitationStateSnapshot({
          stage: "schedule_gate",
          reason: g.reason || "widget_disabled",
        })
      );
      return;
    }
    emitTriggerDecision("cart_hesitation", true, null);
    logAllowed({ path: "hesitation_schedule" });
    trigLog(
      "[CF HESITATION ARMED]",
      hesitationStateSnapshot({
        arm_base: typeof timingOpts.armBaseAtMs === "number" ? "resumed" : "now",
      })
    );

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
      if (Cf.State && typeof Cf.State.persistV2HesitationDeadline === "function") {
        Cf.State.persistV2HesitationDeadline(deadline);
      }
    } catch (ePSs) {}

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

    try {
      if (Cf.Arbitration && typeof Cf.Arbitration.observeTriggerSignal === "function") {
        Cf.Arbitration.observeTriggerSignal({
          trigger_source: "cart_hesitation_timer",
          phase: "hesitation_scheduled",
        });
      }
    } catch (eArbHes) {}

    trigLog(
      "[CF HESITATION TIMER START]",
      hesitationStateSnapshot({
        timer: "hesitation_anchor",
        countdown_ms: remainingMs,
        configured_delay_ms: msConfigured,
        expected_fire_at: deadline,
      })
    );

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
      if (Cf.State && typeof Cf.State.clearV2HesitationDeadlinePersisted === "function") {
        Cf.State.clearV2HesitationDeadlinePersisted();
      }
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
    var isAdd = detectAddToCart(sourceTag, detail);
    if (isAdd) {
      logReceived("add_to_cart", { via: sourceTag });
    } else {
      logReceived("cart_channel", { via: sourceTag });
    }
    trigLog(
      "[CF HESITATION ARMED]",
      hesitationStateSnapshot({
        stage: "cart_channel",
        via: sourceTag,
        detected_add_to_cart: isAdd,
      })
    );

    if (!Cf.State || typeof Cf.State.mirrorCartTotalsFromGlobals !== "function") {
      trigLog(
        "[CF HESITATION SKIPPED]",
        hesitationStateSnapshot({
          stage: "cart_channel",
          via: sourceTag,
          reason: "state_unavailable",
        })
      );
      return;
    }
    Cf.State.mirrorCartTotalsFromGlobals();

    try {
      if (window.CartFlowState && sourceTag !== "replay") {
        window.CartFlowState.lastIntentAt = Date.now();
      }
    } catch (eLf) {}

    if (!v2TriggerInitDone) {
      recordDeferredArmIntent(sourceTag);
      trigLog(
        "[CF HESITATION SKIPPED]",
        hesitationStateSnapshot({
          stage: "cart_channel",
          via: sourceTag,
          reason: "trigger_init_not_done_deferred",
        })
      );
      return;
    }

    scheduleCartHesitation(st(), {});
  }

  /**
   * Storefront cart bridge persisted a cart (POST /api/cart-event ok).
   * Ensures fast-add-before-init never silently drops hesitation arming.
   */
  function onStorefrontCartPersisted(cart) {
    cart = cart || {};
    var stRef = st();
    logReceived("add_to_cart", { via: "storefront_bridge_persist" });

    if (!v2TriggerInitDone) {
      recordDeferredArmIntent("storefront_bridge_persist");
      trigLog(
        "[CF HESITATION SKIPPED]",
        hesitationStateSnapshot({
          stage: "storefront_persist",
          via: "storefront_bridge_persist",
          reason: "trigger_init_not_done_deferred",
        })
      );
      return;
    }

    if (!stRef || stRef.bubbleShown || hesitationAlreadyArmed(stRef)) {
      return;
    }

    if (haveCartApprox()) {
      scheduleCartHesitation(stRef, {});
      return;
    }

    var baseAt = null;
    try {
      baseAt = stRef.cfV2HesitationDeferredBaseAt;
    } catch (eBa) {}
    scheduleDeferredReplay(
      stRef,
      {},
      baseAt != null && isFinite(baseAt) ? baseAt : Date.now(),
      "storefront_bridge_persist"
    );
  }

  /**
   * Single entry from the platform-neutral Cart Event Bridge.
   * The orchestrator (not the platform adapter) decides display: arm-type
   * cart events route into the existing hesitation scheduling path, which
   * enforces Enable / Hesitation / Delay / Frequency / Suppression gates.
   * Returns true when hesitation was armed (or deferred to flush).
   */
  function onNormalizedCartEvent(evt) {
    evt = evt || {};
    var type = String(evt.event_type || "");
    var armTypes = { add_to_cart: 1, cart_detected: 1, cart_updated: 1 };
    if (type === "cart_removed" || type === "cart_empty") {
      return false;
    }
    if (!armTypes[type]) {
      return false;
    }
    onV2CartChannel("cart_bridge", {
      kind: "add_to_cart",
      reason: "add",
      normalized: evt,
    });
    try {
      var s = st();
      return !!(
        s.hesitationAnchorTimer != null || s.cfV2HesitationDeferredBaseAt != null
      );
    } catch (eRet) {
      return false;
    }
  }

  function scheduleExitIntentTimer(st) {
    logReceived("exit_intent", { phase: "raw" });

    var g = gateExitIntentTimer();
    if (!g.ok) {
      logBlocked(g.reason, { path: "exit_intent_schedule" });
      trigLog(
        "[CF TRIGGER BLOCKED REASON]",
        collectTriggerGateDiagnostics("exit_intent")
      );
      emitTriggerDecision("exit_intent", false, g.reason);
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

    try {
      if (Cf.Arbitration && typeof Cf.Arbitration.observeTriggerSignal === "function") {
        Cf.Arbitration.observeTriggerSignal({
          trigger_source: "exit_intent",
          phase: "exit_intent_scheduled",
        });
      }
    } catch (eArbEx) {}

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
    var via = "deferred";
    try {
      had = v2DeferredScheduleReasons.length > 0;
      if (v2DeferredScheduleReasons.length > 0) {
        via = String(v2DeferredScheduleReasons[v2DeferredScheduleReasons.length - 1]);
      }
      v2DeferredScheduleReasons.length = 0;
    } catch (eE) {}
    var baseAt = null;
    try {
      baseAt = stRef.cfV2HesitationDeferredBaseAt;
    } catch (eBa) {}
    var storefrontPending = storefrontBridgeHasCart();
    var pending =
      had ||
      (baseAt != null && isFinite(baseAt)) ||
      storefrontPending;
    if (storefrontPending && via === "deferred") {
      via = "storefront_bridge_persist";
    }

    if (!pending || !stRef || stRef.bubbleShown || hesitationAlreadyArmed(stRef)) {
      return;
    }

    if (haveCartApprox()) {
      finalizeDeferredHesitation(
        stRef,
        flowsRef,
        {
          armBaseAtMs:
            baseAt != null && isFinite(baseAt) ? baseAt : undefined,
        },
        via
      );
      return;
    }

    scheduleDeferredReplay(
      stRef,
      flowsRef,
      baseAt != null && isFinite(baseAt) ? baseAt : Date.now(),
      via
    );
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
        trigLog(
          "[CF TRIGGER BLOCKED REASON]",
          collectTriggerGateDiagnostics("manual_debug")
        );
        emitTriggerDecision("manual_debug", false, gm.reason);
        return false;
      }
      if (typeof Hooks.fireCartRecovery !== "function") {
        logBlocked("widget_disabled", { source: source, note: "hooks_missing" });
        trigLog(
          "[CF TRIGGER BLOCKED REASON]",
          collectTriggerGateDiagnostics("manual_debug")
        );
        emitTriggerDecision("manual_debug", false, "hooks_missing");
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
      if (
        stRef.cfV2HesitationDeadlineAt == null &&
        Cf.State &&
        typeof Cf.State.readV2HesitationDeadlinePersisted === "function"
      ) {
        try {
          var pDl = Cf.State.readV2HesitationDeadlinePersisted();
          if (pDl != null && isFinite(pDl)) {
            stRef.cfV2HesitationDeadlineAt = pDl;
          }
        } catch (eRes) {}
      }
      var dl = stRef.cfV2HesitationDeadlineAt;
      var delayResumeDidShow = false;

      try {
        console.log("[CF V2 RETURN RESUME]", {
          delay_passed: !!(
            dl != null &&
            isFinite(dl) &&
            Date.now() >= dl &&
            haveCartApprox()
          ),
        });
      } catch (eRs) {}

      if (!haveCartApprox() || stRef.bubbleShown) {
        try {
          console.log("[CF DELAY RESUME COMPLETE]", { show: false });
        } catch (eC1) {}
        return true;
      }

      if (dl != null && isFinite(dl)) {
        try {
          console.log("[CF DELAY RESUME]", {
            remaining_ms: Math.max(0, Math.floor(dl - Date.now())),
          });
        } catch (eDr) {}
      }

      var deadlinePassed =
        dl != null && isFinite(dl) && Date.now() >= dl && haveCartApprox();

      if (deadlinePassed && dl != null) {
        var gm = gateCartRecoveryOpen("visibility_resume");
        if (!gm.ok) {
          try {
            console.log("[CF DELAY RESUME COMPLETE]", { show: false });
          } catch (eCg) {}
          return true;
        }
        if (stRef.hesitationAnchorTimer != null) {
          try {
            clearTimeout(stRef.hesitationAnchorTimer);
          } catch (eCt) {}
          stRef.hesitationAnchorTimer = null;
        }
        stRef.cfV2HesitationDeadlineAt = null;
        try {
          if (Cf.State && typeof Cf.State.clearV2HesitationDeadlinePersisted === "function") {
            Cf.State.clearV2HesitationDeadlinePersisted();
          }
        } catch (eCl2) {}
        trigLog(
          "[CF HESITATION TIMER FIRED]",
          hesitationStateSnapshot({
            timer: "hesitation_catch_up",
            deadline_at: dl != null && isFinite(dl) ? dl : null,
            via: "visibility_resume",
          })
        );
        emitHesitationFireLogs(dl);
        logFired("visibility_resume", { timer: "hesitation_catch_up" });
        delayResumeDidShow = true;
        if (typeof Hooks.fireCartRecovery === "function") {
          trigLog(
            "[CF HESITATION DISPATCH]",
            hesitationStateSnapshot({
              dispatch: "cart_hesitation_timer",
              via: "visibility_resume",
            })
          );
          Hooks.fireCartRecovery("cart_hesitation_timer");
        } else {
          trigLog(
            "[CF HESITATION SKIPPED]",
            hesitationStateSnapshot({
              stage: "dispatch",
              via: "visibility_resume",
              reason: "no_dispatch_hook",
            })
          );
        }
        try {
          console.log("[CF DELAY RESUME COMPLETE]", { show: delayResumeDidShow });
        } catch (eC2) {}
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

        var armDelay = remainder;
        try {
          stRef.cfV2HesitationDeadlineAt = dl;
          if (
            Cf.State &&
            typeof Cf.State.persistV2HesitationDeadline === "function"
          ) {
            Cf.State.persistV2HesitationDeadline(dl);
          }
        } catch (ePer) {}

        var tick = function () {
          fireCartRecoveryAfterHesitation(stRef, {});
        };
        trigLog(
          "[CF HESITATION TIMER START]",
          hesitationStateSnapshot({
            timer: "hesitation_anchor",
            countdown_ms: armDelay,
            expected_fire_at: dl,
            via: "visibility_resume_rearm",
          })
        );
        if (armDelay <= 0) {
          tick();
          delayResumeDidShow = true;
        } else {
          stRef.hesitationAnchorTimer = window.setTimeout(tick, armDelay);
        }
      }

      try {
        console.log("[CF DELAY RESUME COMPLETE]", {
          show: !!delayResumeDidShow,
        });
      } catch (eCf) {}

      return true;
    }

    logBlocked("widget_disabled", { source: source, note: "unknown_trigger_source" });
    trigLog(
      "[CF TRIGGER BLOCKED REASON]",
      collectTriggerGateDiagnostics(String(source || "unknown"))
    );
    emitTriggerDecision(String(source || "unknown"), false, "unknown_trigger_source");
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
    try {
      if (Cf.Config && typeof Cf.Config.logWidgetSettingsRuntimeTruth === "function") {
        Cf.Config.logWidgetSettingsRuntimeTruth("triggers_init");
      }
    } catch (eTr) {}

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
    onNormalizedCartEvent: onNormalizedCartEvent,
    onStorefrontCartPersisted: onStorefrontCartPersisted,
  };
  window.CartflowWidgetRuntime.Triggers = Triggers;
  try {
    console.log("[CF TRIGGERS REGISTERED]", {
      has_init: typeof window.CartflowWidgetRuntime.Triggers.init === "function",
      has_receive:
        typeof window.CartflowWidgetRuntime.Triggers.receiveTrigger === "function",
      has_normalized_cart:
        typeof window.CartflowWidgetRuntime.Triggers.onNormalizedCartEvent ===
        "function",
    });
  } catch (eTrigReg) {}

  // The Triggers object IS the V2 trigger orchestrator (see file header). Expose
  // it under the orchestrator namespace too so any bootstrap consumer that looks
  // up TriggerOrchestrator resolves it. Additive — does not change gating/flow.
  window.CartflowWidgetRuntime.TriggerOrchestrator = Triggers;
  try {
    console.log("[CF ORCHESTRATOR REGISTERED]", {
      present: !!window.CartflowWidgetRuntime.TriggerOrchestrator,
    });
  } catch (eOrcReg) {}
  } catch (eTriggersFatal) {
    try {
      console.error(
        "[CF TRIGGERS ERROR]",
        (eTriggersFatal && eTriggersFatal.stack) || String(eTriggersFatal)
      );
    } catch (eTrigErrLog) {}
  }
})();
