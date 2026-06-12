/**
 * Node harness for Widget Trigger Arbitration shadow pure tests.
 * Usage: node tests/fixtures/widget_arbitration_shadow_harness.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "..", "..");
const ARB_PATH = path.join(
  ROOT,
  "static",
  "cartflow_widget_runtime",
  "cartflow_widget_arbitration.js"
);

function makeSandbox() {
  return loadArbitration().Arb;
}

function loadArbitrationLegacyAlias() {
  return loadArbitration().Arb;
}

function loadArbitration() {
  const code = fs.readFileSync(ARB_PATH, "utf8");
  const ctx = {
    window: { CartflowWidgetRuntime: {} },
    console: { log() {} },
  };
  vm.createContext(ctx);
  vm.runInContext(code, ctx);
  const Cf = ctx.window.CartflowWidgetRuntime;
  Cf.State = {
    internals: { bubbleShown: false, pending_reason_key: null, shell: {} },
    mirrorCartTotalsFromGlobals: function () {},
    checkoutPathActive: function () {
      return false;
    },
    readDismissSuppress: function () {
      return false;
    },
    sessionConvertedBlock: function () {
      return false;
    },
    hasValidStoredPhone: function () {
      return false;
    },
  };
  Cf.Triggers = {
    haveCartApprox: function () {
      return false;
    },
  };
  return { Arb: Cf.Arbitration, Cf: Cf };
}

function assert(cond, msg) {
  if (!cond) {
    throw new Error(msg || "assertion failed");
  }
}

function run() {
  const loaded = loadArbitration();
  const Arb = loaded.Arb;
  const Cf = loaded.Cf;
  const pure = Arb._shadowPure;
  const results = [];

  function case_(name, fn) {
    try {
      Arb._testResetShadowState();
      fn();
      results.push({ name, ok: true });
    } catch (e) {
      results.push({ name, ok: false, error: String(e && e.message ? e.message : e) });
    }
  }

  case_("cart_plus_exit_upgrade", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent_with_cart",
      cart_present: true,
      journey_type: "exit_without_cart",
      is_vip: false,
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "upgrade", "expected upgrade got " + d.action);
    assert(d.upgraded_to === "cart_recovery", "expected cart_recovery upgrade");
  });

  case_("vip_plus_exit_upgrade", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent_with_cart",
      cart_present: true,
      is_vip: true,
      cart_value: 10000,
      journey_type: "exit_without_cart",
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "upgrade", "expected upgrade");
    assert(d.upgraded_to === "vip_recovery", "expected vip_recovery");
  });

  case_("cart_hesitation_allow", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "cart_hesitation_timer",
      cart_present: true,
      journey_type: "cart_recovery",
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "allow", "expected allow");
  });

  case_("widget_already_open_ignore", () => {
    Arb._testApplyShadowState({ widget_visible: true, first_screen_locked: true });
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent",
      journey_type: "exit_without_cart",
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "ignore", "expected ignore");
  });

  case_("reason_active_deny", () => {
    Arb._testApplyShadowState({ reason_active: true });
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent_with_cart",
      cart_present: true,
      journey_type: "cart_recovery",
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "deny", "expected deny");
  });

  case_("phone_active_deny", () => {
    Arb._testApplyShadowState({ phone_active: true });
    const intent = pure.buildMockIntent({
      trigger_source: "cart_hesitation_timer",
      cart_present: true,
      journey_type: "cart_recovery",
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "deny", "expected deny");
  });

  case_("return_resume_journey_type", () => {
    const jt = pure.resolveShadowJourneyType("visibility_resume", {
      cart_present: false,
      cart_detected: "no",
      cart_value: 0,
    });
    assert(jt === "return_to_site", "expected return_to_site got " + jt);
  });

  case_("multiple_intents_tracked", () => {
    const t0 = Date.now();
    Arb.observeTriggerSignal({ trigger_source: "exit_intent", phase: "test_a", requested_at: t0 });
    Arb.observeTriggerSignal({ trigger_source: "cart_hesitation_timer", phase: "test_b", requested_at: t0 + 100 });
    const st = Arb.getShadowState();
    assert(st.recent_intent_count >= 2, "expected recent intents");
  });

  case_("cart_pending_defer", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent",
      cart_present: false,
      journey_type: "exit_without_cart",
      customer_context: { cart_detected: "pending", cart_pending: true },
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "defer", "expected defer got " + d.action);
  });

  case_("no_cart_exit_blocked", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent",
      cart_present: false,
      journey_type: "exit_without_cart",
      customer_context: { cart_detected: "no", cart_pending: false },
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "deny", "expected deny got " + d.action);
    assert(d.reason === "exit_without_cart_blocked", "expected exit_without_cart_blocked");
    assert(d.enforce === true, "expected enforce true");
  });

  case_("storefront_recovery_no_cart_blocked", () => {
    const intent = pure.buildMockIntent({
      trigger_source: "exit_intent_storefront_recovery",
      cart_present: false,
      journey_type: "exit_without_cart",
      customer_context: { cart_detected: "no", cart_pending: false },
    });
    const d = Arb.evaluateShadowDecision(intent);
    assert(d.action === "deny", "expected deny");
    assert(d.reason === "exit_without_cart_blocked", "expected blocked reason");
  });

  case_("gate_exit_no_cart_blocks", () => {
    Cf.Triggers.haveCartApprox = function () {
      return false;
    };
    const gate = Arb.gateExitIntentOpen({
      trigger_source: "exit_intent",
      entrypoint: "test_fireExitNoCart",
    });
    assert(gate.allowed === false, "expected not allowed");
    assert(gate.decision.action === "deny", "expected deny");
    assert(gate.decision.reason === "exit_without_cart_blocked", "expected blocked reason");
  });

  case_("gate_exit_with_cart_cart_tag", () => {
    Cf.Triggers.haveCartApprox = function () {
      return true;
    };
    const gate = Arb.gateExitIntentOpen({
      trigger_source: "exit_intent_with_cart",
      entrypoint: "test_fireExitWithCart",
    });
    assert(gate.allowed === true, "expected allowed");
    assert(gate.openTag === "cart_hesitation_timer", "expected cart tag");
    assert(
      gate.journey_type === "cart_recovery" || gate.journey_type === "vip_recovery",
      "expected cart journey"
    );
  });

  case_("copy_mismatch_detection", () => {
    const actual = pure.computeActualCopySource("exit_intent_with_cart", "showBubbleCartRecovery");
    const shadow = pure.computeShadowCopySource("cart_recovery");
    assert(actual === "exit_intent_template_via_tag", "actual source");
    assert(shadow === "cart_recovery_default", "shadow source");
    assert(actual !== shadow, "copy sources should differ for future fix");
  });

  const failed = results.filter((r) => !r.ok);
  console.log(JSON.stringify({ total: results.length, failed: failed.length, results }, null, 2));
  if (failed.length) {
    process.exit(1);
  }
}

run();
