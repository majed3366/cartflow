# -*- coding: utf-8 -*-
"""Exit Intent No-Cart Enforcement v1 — wiring + arbitration decision tests."""
from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_ARBITRATION = _RUNTIME / "cartflow_widget_arbitration.js"
_FLOWS = _RUNTIME / "cartflow_widget_flows.js"
_BRIDGE = _RUNTIME / "cartflow_storefront_cart_bridge_core.js"
_LOADER = _ROOT / "static" / "widget_loader.js"
_NODE_HARNESS = _ROOT / "tests" / "fixtures" / "widget_arbitration_shadow_harness.js"


class ExitIntentNoCartEnforcementWiringTests(unittest.TestCase):
    def test_policy_flag_and_reason(self) -> None:
        src = _ARBITRATION.read_text(encoding="utf-8")
        self.assertIn("EXIT_NO_CART_POLICY_ENFORCED = true", src)
        self.assertIn("exit_without_cart_blocked", src)
        self.assertIn("gateExitIntentOpen", src)

    def test_flows_exit_paths_use_gate(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("gateExitIntentOpen", flows)
        self.assertIn('entrypoint: "fireExitNoCart"', flows)
        self.assertIn('entrypoint: "fireExitWithCart"', flows)
        self.assertIn('entrypoint: "showExitNoCart"', flows)

    def test_fire_exit_no_cart_does_not_open_storefront_recovery(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        block = flows.split("fireExitNoCart: function () {", 1)[1].split("fireExitWithCart:", 1)[0]
        self.assertIn("gateExitIntentOpen", block)
        gated = block.split("cfArbitrationShadowObserveTrigger", 1)[0]
        self.assertIn("if (!gate || !gate.allowed)", gated)
        self.assertNotIn('showBubbleCartRecovery("exit_intent_storefront_recovery")', gated)

    def test_fire_exit_with_cart_uses_cart_tag(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        block = flows.split("fireExitWithCart: function () {", 1)[1].split(
            "showBubbleCartRecovery(openTag)", 1
        )[0]
        self.assertIn("gate.openTag", block)
        self.assertIn("openTag = gate.openTag", block)

    def test_hesitation_path_unchanged(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("showBubbleCartRecovery(String(tag || \"cart_timer\"))", flows)
        self.assertIn("cfArbitrationShadowObserveTrigger(String(tag || \"cart_timer\")", flows)

    def test_cart_bridge_untouched(self) -> None:
        self.assertTrue(_BRIDGE.exists())
        bridge = _BRIDGE.read_text(encoding="utf-8")
        self.assertIn("StorefrontCartBridge", bridge)

    def test_runtime_version_bumped(self) -> None:
        wl = _LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-early-cart-bridge-listener-bootstrap-v1", wl)

    def test_arbitration_logs_include_policy(self) -> None:
        src = _ARBITRATION.read_text(encoding="utf-8")
        self.assertIn("exit_no_cart_v1", src)
        self.assertIn('kind: "exit_without_cart_blocked"', src)


class ExitIntentNoCartEnforcementDecisionTests(unittest.TestCase):
    def test_node_harness_scenarios(self) -> None:
        proc = subprocess.run(
            ["node", str(_NODE_HARNESS)],
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=(proc.stdout or "") + (proc.stderr or ""),
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload.get("failed"), 0)
        self.assertGreaterEqual(payload.get("total"), 13)
        names = {row["name"] for row in payload.get("results", [])}
        for required in (
            "no_cart_exit_blocked",
            "storefront_recovery_no_cart_blocked",
            "gate_exit_no_cart_blocks",
            "gate_exit_with_cart_cart_tag",
            "cart_hesitation_allow",
            "cart_plus_exit_upgrade",
        ):
            self.assertIn(required, names)


if __name__ == "__main__":
    unittest.main()
