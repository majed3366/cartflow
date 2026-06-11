/**
 * Widget Trigger Arbitration — SHADOW MODE v1
 * Observes open intents, evaluates decisions, logs conflicts.
 * Does NOT enforce — runtime behavior unchanged.
 */
window.CartflowWidgetRuntime = window.CartflowWidgetRuntime || {};
(function (Cf) {
  "use strict";

  var SHADOW_MODE = true;
  var RECENT_INTENT_WINDOW_MS = 1000;
  var CART_RECOVERY_COPY = "تبي أساعدك تكمل طلبك؟";
  var EXIT_FIRST_BEAT_COPY = "تحتاج مساعدة قبل ما تطلع؟";

  var JOURNEY_PRIORITY = {
    vip_recovery: 1,
    cart_recovery: 2,
    reason_continuation: 3,
    manual_help: 4,
    exit_without_cart: 5,
    return_to_site: 6,
  };

  var JOURNEY_TYPES = [
    "cart_recovery",
    "vip_recovery",
    "exit_without_cart",
    "return_to_site",
    "manual_help",
    "reason_continuation",
  ];

  var SHADOW_STATE = {
    journey_type: null,
    trigger_source: null,
    widget_visible: false,
    first_screen_locked: false,
    reason_active: false,
    phone_active: false,
    cart_present: false,
    vip_present: false,
    last_decision_at: null,
    last_decision_action: null,
    recent_intents: [],
  };

  function arbLog(tag, payload) {
    try {
      console.log(tag, payload || {});
    } catch (eLog) {}
  }

  function str(v) {
    return String(v == null ? "" : v).trim();
  }

  function safeNum(v) {
    try {
      var n = parseFloat(v);
      return isFinite(n) ? n : 0;
    } catch (eN) {
      return 0;
    }
  }

  function resolveSessionId() {
    try {
      if (typeof window.cartflowGetSessionId === "function") {
        var sid = str(window.cartflowGetSessionId());
        if (sid) {
          return sid;
        }
      }
    } catch (eS) {}
    try {
      return str(sessionStorage.getItem("cartflow_recovery_session_id"));
    } catch (eSs) {}
    return "";
  }

  function readRuntimeInternals() {
    try {
      return Cf.State && Cf.State.internals ? Cf.State.internals : {};
    } catch (eSt) {
      return {};
    }
  }

  function detectCartBridgePending() {
    try {
      var bridge = Cf.StorefrontCartBridge;
      if (!bridge || typeof bridge.getDiagnostics !== "function") {
        return false;
      }
      var d = bridge.getDiagnostics();
      if (!d) {
        return false;
      }
      if (d.cart_persisted === true) {
        return false;
      }
      if (d.normalized && safeNum(d.normalized.cart_value) > 0) {
        return false;
      }
      var skip = str(d.last_skip_reason);
      if (skip.indexOf("empty") >= 0) {
        return true;
      }
    } catch (eB) {}
    return false;
  }

  function detectCartState() {
    var detected = "no";
    var present = false;
    var value = 0;
    var pending = detectCartBridgePending();

    try {
      if (
        Cf.Triggers &&
        typeof Cf.Triggers.haveCartApprox === "function" &&
        Cf.Triggers.haveCartApprox()
      ) {
        detected = "yes";
        present = true;
      }
    } catch (eHc) {}

    if (!present) {
      try {
        var bridge = Cf.StorefrontCartBridge;
        if (bridge && typeof bridge.getDiagnostics === "function") {
          var diag = bridge.getDiagnostics();
          if (diag && diag.normalized && safeNum(diag.normalized.cart_value) > 0) {
            detected = "yes";
            present = true;
            value = safeNum(diag.normalized.cart_value);
          }
        }
      } catch (eD) {}
    }

    if (!present && pending) {
      detected = "pending";
    }

    try {
      Cf.State.mirrorCartTotalsFromGlobals();
    } catch (eM) {}

    try {
      if (window.cartflowState && safeNum(window.cartflowState.cartTotal) > 0) {
        value = safeNum(window.cartflowState.cartTotal);
        if (present || detected === "yes") {
          /* keep */
        } else if (
          Array.isArray(window.cart) &&
          window.cart.length > 0
        ) {
          detected = "yes";
          present = true;
        }
      }
    } catch (eCt) {}

    try {
      if (window.is_vip === true && present) {
        /* vip read separately */
      }
    } catch (eV) {}

    return {
      cart_detected: detected,
      cart_present: present,
      cart_value: value,
      cart_pending: pending,
    };
  }

  function readIsVip(cartPresent, cartValue) {
    try {
      if (window.is_vip === true && cartPresent) {
        return true;
      }
    } catch (eIv) {}
    try {
      if (window.cartflowState && window.cartflowState.isVip === true && cartPresent) {
        return true;
      }
    } catch (eCs) {}
    try {
      var th =
        window.CARTFLOW_VIP_CART_THRESHOLD != null
          ? safeNum(window.CARTFLOW_VIP_CART_THRESHOLD)
          : window.cartflowVipCartThreshold != null
          ? safeNum(window.cartflowVipCartThreshold)
          : 0;
      if (th > 0 && cartValue >= th && cartPresent) {
        return true;
      }
    } catch (eTh) {}
    return false;
  }

  function syncShadowStateFromRuntime() {
    var inner = readRuntimeInternals();
    SHADOW_STATE.widget_visible = !!inner.bubbleShown;
    SHADOW_STATE.reason_active = !!str(inner.pending_reason_key);
    SHADOW_STATE.phone_active = false;
    try {
      if (inner.shell && inner.shell.currentStep === "optional_phone") {
        SHADOW_STATE.phone_active = true;
      }
    } catch (ePh) {}
    try {
      if (inner.shell && inner.shell.isOpen === true) {
        SHADOW_STATE.widget_visible = true;
      }
    } catch (eSh) {}
    var cart = detectCartState();
    SHADOW_STATE.cart_present = !!cart.cart_present;
    SHADOW_STATE.vip_present = readIsVip(cart.cart_present, cart.cart_value);
    if (SHADOW_STATE.widget_visible && SHADOW_STATE.journey_type) {
      SHADOW_STATE.first_screen_locked = true;
    }
  }

  function resolveShadowJourneyType(triggerSource, snap) {
    var ts = str(triggerSource).toLowerCase();
    var cart = !!snap.cart_present;
    var pending = snap.cart_detected === "pending" || snap.cart_pending === true;
    var vip = readIsVip(cart, snap.cart_value);

    if (ts === "cart_prompt_back_from_reason_list") {
      return "reason_continuation";
    }
    if (vip && cart) {
      return "vip_recovery";
    }
    if (cart || pending) {
      return "cart_recovery";
    }
    if (ts === "manual_debug" || ts.indexOf("manual") >= 0) {
      return "manual_help";
    }
    if (ts === "visibility_resume" || ts.indexOf("return") >= 0) {
      return "return_to_site";
    }
    if (ts.indexOf("exit") >= 0) {
      return "exit_without_cart";
    }
    if (
      ts.indexOf("cart_hesitation") >= 0 ||
      ts.indexOf("cart_inactivity") >= 0 ||
      ts.indexOf("cart_timer") >= 0 ||
      ts.indexOf("add_to_cart") >= 0
    ) {
      return "cart_recovery";
    }
    return cart ? "cart_recovery" : "exit_without_cart";
  }

  function buildIntent(opts) {
    opts = opts || {};
    syncShadowStateFromRuntime();
    var cartSnap = detectCartState();
    var isVip = readIsVip(cartSnap.cart_present, cartSnap.cart_value);
    var triggerSource = str(opts.trigger_source || opts.tag_note || "unknown");
    var journeyType = resolveShadowJourneyType(triggerSource, cartSnap);

    var inner = readRuntimeInternals();
    var hasReason = !!str(inner.pending_reason_key);
    var hasPhone = false;
    try {
      hasPhone =
        (Cf.State && typeof Cf.State.hasValidStoredPhone === "function" &&
          Cf.State.hasValidStoredPhone()) ||
        false;
    } catch (eHp) {}

    var intent = {
      trigger_source: triggerSource,
      customer_context: {
        cart_detected: cartSnap.cart_detected,
        cart_pending: cartSnap.cart_pending,
        checkout_active:
          Cf.State && typeof Cf.State.checkoutPathActive === "function"
            ? Cf.State.checkoutPathActive()
            : false,
        dismiss_suppressed:
          Cf.State && typeof Cf.State.readDismissSuppress === "function"
            ? Cf.State.readDismissSuppress()
            : false,
        converted:
          Cf.State && typeof Cf.State.sessionConvertedBlock === "function"
            ? Cf.State.sessionConvertedBlock()
            : false,
      },
      cart_present: !!cartSnap.cart_present,
      cart_value: cartSnap.cart_value,
      has_reason: hasReason,
      has_phone: hasPhone,
      is_vip: isVip,
      journey_type: journeyType,
      priority: JOURNEY_PRIORITY[journeyType] || 99,
      requested_at:
        typeof opts.requested_at === "number" && isFinite(opts.requested_at)
          ? opts.requested_at
          : Date.now(),
      session_id: resolveSessionId(),
      phase: str(opts.phase || "open_attempt"),
      entrypoint: str(opts.entrypoint || ""),
    };

    arbLog("[CF ARBITRATION INTENT]", intent);
    return intent;
  }

  function computeActualCopySource(tagNote, entrypoint) {
    var tag = str(tagNote);
    if (entrypoint === "showExitNoCart") {
      return "exit_no_cart_first_beat";
    }
    if (tag.indexOf("exit_intent") >= 0) {
      return "exit_intent_template_via_tag";
    }
    return "cart_recovery_default";
  }

  function computeShadowCopySource(journeyType) {
    if (journeyType === "vip_recovery" || journeyType === "cart_recovery") {
      return "cart_recovery_default";
    }
    if (journeyType === "exit_without_cart") {
      return "exit_intent_template";
    }
    if (journeyType === "manual_help") {
      return "manual_help";
    }
    if (journeyType === "return_to_site") {
      return "return_to_site";
    }
    if (journeyType === "reason_continuation") {
      return "reason_continuation";
    }
    return "unknown";
  }

  function shadowCopyPreview(copySource) {
    if (copySource === "cart_recovery_default") {
      return CART_RECOVERY_COPY;
    }
    if (copySource === "exit_no_cart_first_beat") {
      return EXIT_FIRST_BEAT_COPY;
    }
    if (copySource === "exit_intent_template" || copySource === "exit_intent_template_via_tag") {
      return "exit_intent_template";
    }
    return copySource;
  }

  function evaluateShadowDecision(intent) {
    var action = "allow";
    var reason = null;
    var upgradedTo = null;

    if (SHADOW_STATE.reason_active || SHADOW_STATE.phone_active) {
      if (intent.journey_type !== "reason_continuation") {
        return {
          action: "deny",
          reason: "reason_or_phone_flow_active",
          journey_type: intent.journey_type,
          priority: intent.priority,
          shadow_mode: SHADOW_MODE,
        };
      }
    }

    if (SHADOW_STATE.widget_visible || SHADOW_STATE.first_screen_locked) {
      if (
        intent.journey_type !== "reason_continuation" &&
        intent.trigger_source !== "cart_prompt_back_from_reason_list"
      ) {
        return {
          action: "ignore",
          reason: "widget_already_visible",
          journey_type: intent.journey_type,
          priority: intent.priority,
          shadow_mode: SHADOW_MODE,
        };
      }
    }

    if (
      intent.customer_context &&
      (intent.customer_context.cart_detected === "pending" ||
        intent.customer_context.cart_pending === true) &&
      intent.journey_type === "exit_without_cart"
    ) {
      return {
        action: "defer",
        reason: "cart_bridge_pending",
        journey_type: "cart_recovery",
        priority: JOURNEY_PRIORITY.cart_recovery,
        shadow_mode: SHADOW_MODE,
      };
    }

    if (intent.cart_present && intent.journey_type === "exit_without_cart") {
      upgradedTo = intent.is_vip ? "vip_recovery" : "cart_recovery";
      return {
        action: "upgrade",
        reason: intent.is_vip ? "vip_cart_over_exit" : "cart_present_over_exit",
        journey_type: intent.journey_type,
        upgraded_to: upgradedTo,
        priority: JOURNEY_PRIORITY[upgradedTo] || intent.priority,
        shadow_mode: SHADOW_MODE,
      };
    }

    if (intent.is_vip && intent.cart_present && intent.journey_type === "cart_recovery") {
      return {
        action: "allow",
        reason: "vip_cart_recovery",
        journey_type: "vip_recovery",
        priority: JOURNEY_PRIORITY.vip_recovery,
        shadow_mode: SHADOW_MODE,
      };
    }

    return {
      action: action,
      reason: reason,
      journey_type: intent.journey_type,
      priority: intent.priority,
      shadow_mode: SHADOW_MODE,
    };
  }

  function trackRecentIntent(intent) {
    var now = intent.requested_at;
    var recent = [];
    var i;
    for (i = 0; i < SHADOW_STATE.recent_intents.length; i++) {
      var row = SHADOW_STATE.recent_intents[i];
      if (row && now - row.requested_at < RECENT_INTENT_WINDOW_MS) {
        recent.push(row);
      }
    }
    recent.push({
      trigger_source: intent.trigger_source,
      journey_type: intent.journey_type,
      requested_at: now,
    });
    SHADOW_STATE.recent_intents = recent;
    return recent;
  }

  function detectConflicts(intent, decision, copyPayload) {
    var conflicts = [];
    var ts = str(intent.trigger_source).toLowerCase();

    if (intent.cart_present && ts.indexOf("exit") >= 0) {
      conflicts.push("exit_plus_cart");
    }
    if (intent.is_vip && intent.cart_present && ts.indexOf("exit") >= 0) {
      conflicts.push("vip_cart_plus_exit");
    }
    if (decision.action === "ignore" && decision.reason === "widget_already_visible") {
      conflicts.push("widget_already_visible");
    }
    if (
      (SHADOW_STATE.reason_active || SHADOW_STATE.phone_active) &&
      decision.action === "deny"
    ) {
      conflicts.push(
        SHADOW_STATE.phone_active ? "phone_flow_interruption_attempt" : "reason_flow_interruption_attempt"
      );
    }
    if (SHADOW_STATE.recent_intents.length > 1) {
      conflicts.push("multiple_triggers_same_second");
    }
    if (
      copyPayload &&
      copyPayload.actual_copy_source !== copyPayload.shadow_copy_source &&
      intent.cart_present
    ) {
      conflicts.push("copy_source_mismatch_with_cart");
    }

    var c;
    for (c = 0; c < conflicts.length; c++) {
      arbLog("[CF ARBITRATION CONFLICT]", {
        kind: conflicts[c],
        trigger_source: intent.trigger_source,
        journey_type: intent.journey_type,
        decision: decision.action,
        cart_present: intent.cart_present,
        is_vip: intent.is_vip,
      });
    }
    return conflicts;
  }

  function updateShadowStateAfterDecision(intent, decision) {
    SHADOW_STATE.last_decision_at = Date.now();
    SHADOW_STATE.last_decision_action = decision.action;
    SHADOW_STATE.trigger_source = intent.trigger_source;
    if (decision.action === "allow" || decision.action === "upgrade") {
      SHADOW_STATE.journey_type =
        decision.upgraded_to || decision.journey_type || intent.journey_type;
      SHADOW_STATE.first_screen_locked = true;
    }
    arbLog("[CF ARBITRATION STATE]", {
      journey_type: SHADOW_STATE.journey_type,
      trigger_source: SHADOW_STATE.trigger_source,
      widget_visible: SHADOW_STATE.widget_visible,
      first_screen_locked: SHADOW_STATE.first_screen_locked,
      reason_active: SHADOW_STATE.reason_active,
      phone_active: SHADOW_STATE.phone_active,
      cart_present: SHADOW_STATE.cart_present,
      vip_present: SHADOW_STATE.vip_present,
      last_decision_action: SHADOW_STATE.last_decision_action,
    });
  }

  function requestWidgetOpen(intent) {
    if (!intent || typeof intent !== "object") {
      intent = buildIntent({ trigger_source: "unknown" });
    }
    var decision = evaluateShadowDecision(intent);
    arbLog("[CF ARBITRATION DECISION]", {
      trigger_source: intent.trigger_source,
      journey_type: intent.journey_type,
      priority: intent.priority,
      cart_present: intent.cart_present,
      is_vip: intent.is_vip,
      action: decision.action,
      reason: decision.reason,
      upgraded_to: decision.upgraded_to || null,
      shadow_mode: true,
      enforce: false,
    });
    return decision;
  }

  function observeWidgetOpenAttempt(opts) {
    opts = opts || {};
    var intent = buildIntent({
      trigger_source: opts.trigger_source || opts.tag_note,
      tag_note: opts.tag_note,
      entrypoint: opts.entrypoint,
      phase: "open_attempt",
      requested_at: Date.now(),
    });
    var decision = requestWidgetOpen(intent);
    var actualCopySource = computeActualCopySource(opts.tag_note, opts.entrypoint);
    var effectiveJourney =
      decision.upgraded_to || decision.journey_type || intent.journey_type;
    var shadowCopySource = computeShadowCopySource(effectiveJourney);
    var copyPayload = {
      trigger_source: intent.trigger_source,
      journey_type: effectiveJourney,
      cart_present: intent.cart_present,
      actual_copy_source: actualCopySource,
      shadow_copy_source: shadowCopySource,
      actual_copy_preview: shadowCopyPreview(actualCopySource),
      shadow_copy_preview: shadowCopyPreview(shadowCopySource),
      copy_would_change:
        actualCopySource !== shadowCopySource && intent.cart_present,
    };
    arbLog("[CF ARBITRATION COPY]", copyPayload);
    trackRecentIntent(intent);
    detectConflicts(intent, decision, copyPayload);
    updateShadowStateAfterDecision(intent, decision);
    return {
      intent: intent,
      decision: decision,
      copy: copyPayload,
      shadow_state: getShadowState(),
    };
  }

  function observeTriggerSignal(opts) {
    opts = opts || {};
    var intent = buildIntent({
      trigger_source: opts.trigger_source,
      phase: opts.phase || "trigger_signal",
      requested_at: Date.now(),
    });
    var decision = requestWidgetOpen(intent);
    trackRecentIntent(intent);
    detectConflicts(intent, decision, null);
    return { intent: intent, decision: decision };
  }

  function getShadowState() {
    syncShadowStateFromRuntime();
    return {
      journey_type: SHADOW_STATE.journey_type,
      trigger_source: SHADOW_STATE.trigger_source,
      widget_visible: SHADOW_STATE.widget_visible,
      first_screen_locked: SHADOW_STATE.first_screen_locked,
      reason_active: SHADOW_STATE.reason_active,
      phone_active: SHADOW_STATE.phone_active,
      cart_present: SHADOW_STATE.cart_present,
      vip_present: SHADOW_STATE.vip_present,
      last_decision_at: SHADOW_STATE.last_decision_at,
      last_decision_action: SHADOW_STATE.last_decision_action,
      recent_intent_count: SHADOW_STATE.recent_intents.length,
      shadow_mode: SHADOW_MODE,
    };
  }

  Cf.Arbitration = {
    SHADOW_MODE: SHADOW_MODE,
    JOURNEY_TYPES: JOURNEY_TYPES,
    JOURNEY_PRIORITY: JOURNEY_PRIORITY,
    buildIntent: buildIntent,
    requestWidgetOpen: requestWidgetOpen,
    observeWidgetOpenAttempt: observeWidgetOpenAttempt,
    observeTriggerSignal: observeTriggerSignal,
    getShadowState: getShadowState,
    evaluateShadowDecision: evaluateShadowDecision,
    resolveShadowJourneyType: resolveShadowJourneyType,
    computeActualCopySource: computeActualCopySource,
    computeShadowCopySource: computeShadowCopySource,
    _testApplyShadowState: function (patch) {
      patch = patch || {};
      var k;
      for (k in patch) {
        if (Object.prototype.hasOwnProperty.call(patch, k)) {
          SHADOW_STATE[k] = patch[k];
        }
      }
    },
    _testResetShadowState: function () {
      SHADOW_STATE.journey_type = null;
      SHADOW_STATE.trigger_source = null;
      SHADOW_STATE.widget_visible = false;
      SHADOW_STATE.first_screen_locked = false;
      SHADOW_STATE.reason_active = false;
      SHADOW_STATE.phone_active = false;
      SHADOW_STATE.cart_present = false;
      SHADOW_STATE.vip_present = false;
      SHADOW_STATE.last_decision_at = null;
      SHADOW_STATE.last_decision_action = null;
      SHADOW_STATE.recent_intents = [];
    },
    _shadowPure: {
      resolveShadowJourneyType: resolveShadowJourneyType,
      evaluateShadowDecision: evaluateShadowDecision,
      computeActualCopySource: computeActualCopySource,
      computeShadowCopySource: computeShadowCopySource,
      JOURNEY_PRIORITY: JOURNEY_PRIORITY,
      buildMockIntent: function (overrides) {
        overrides = overrides || {};
        return {
          trigger_source: str(overrides.trigger_source || "exit_intent_with_cart"),
          customer_context: overrides.customer_context || {},
          cart_present: !!overrides.cart_present,
          cart_value: safeNum(overrides.cart_value),
          has_reason: !!overrides.has_reason,
          has_phone: !!overrides.has_phone,
          is_vip: !!overrides.is_vip,
          journey_type: str(overrides.journey_type || "exit_without_cart"),
          priority: overrides.priority || 5,
          requested_at: overrides.requested_at || Date.now(),
          session_id: str(overrides.session_id || "test"),
        };
      },
    },
  };
})(window.CartflowWidgetRuntime);
