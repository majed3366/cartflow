# -*- coding: utf-8 -*-
"""Widget Trigger Arbitration Shadow Mode v1 — wiring + decision harness."""
from __future__ import annotations

import json
import pathlib
import subprocess
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_ARBITRATION = _RUNTIME / "cartflow_widget_arbitration.js"
_FLOWS = _RUNTIME / "cartflow_widget_flows.js"
_TRIGGERS = _RUNTIME / "cartflow_widget_triggers.js"
_LOADER = _RUNTIME / "cartflow_widget_loader.js"
_WIDGET_LOADER = _ROOT / "static" / "widget_loader.js"
_NODE_HARNESS = _ROOT / "tests" / "fixtures" / "widget_arbitration_shadow_harness.js"


class WidgetArbitrationShadowWiringTests(unittest.TestCase):
    def test_arbitration_module_in_loader_chain(self) -> None:
        loader = _LOADER.read_text(encoding="utf-8")
        ix_state = loader.index('"cartflow_widget_state.js"')
        ix_arb = loader.index('"cartflow_widget_arbitration.js"')
        ix_theme = loader.index('"cartflow_widget_theme.js"')
        self.assertGreater(ix_arb, ix_state)
        self.assertLess(ix_arb, ix_theme)

    def test_shadow_mode_flag_and_logs(self) -> None:
        src = _ARBITRATION.read_text(encoding="utf-8")
        self.assertIn("SHADOW_MODE = true", src)
        self.assertIn("[CF ARBITRATION INTENT]", src)
        self.assertIn("[CF ARBITRATION DECISION]", src)
        self.assertIn("[CF ARBITRATION CONFLICT]", src)
        self.assertIn("[CF ARBITRATION COPY]", src)
        self.assertIn("[CF ARBITRATION STATE]", src)
        self.assertIn("enforce: false", src)

    def test_widget_open_intent_fields(self) -> None:
        src = _ARBITRATION.read_text(encoding="utf-8")
        for field in (
            "trigger_source",
            "customer_context",
            "cart_present",
            "cart_value",
            "has_reason",
            "has_phone",
            "is_vip",
            "journey_type",
            "priority",
            "requested_at",
            "session_id",
        ):
            self.assertIn(field, src)

    def test_journey_types_declared(self) -> None:
        src = _ARBITRATION.read_text(encoding="utf-8")
        for jt in (
            "cart_recovery",
            "vip_recovery",
            "exit_without_cart",
            "return_to_site",
            "manual_help",
        ):
            self.assertIn('"' + jt + '"', src)

    def test_flows_observes_without_blocking(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("cfArbitrationShadowObserveOpen", flows)
        self.assertIn('cfArbitrationShadowObserveOpen("showBubbleCartRecovery"', flows)
        self.assertIn('cfArbitrationShadowObserveOpen("showExitNoCart"', flows)
        self.assertIn("cfArbitrationShadowObserveTrigger", flows)
        show_ix = flows.index("function showBubbleCartRecovery")
        observe_ix = flows.index("cfArbitrationShadowObserveOpen", show_ix)
        blocked_ix = flows.index("if (storefrontUiBlocked())", show_ix)
        self.assertLess(observe_ix, blocked_ix)

    def test_flows_hooks_still_call_show_functions(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("showBubbleCartRecovery(String(tag || \"cart_timer\"))", flows)
        self.assertIn("showExitNoCart();", flows)
        self.assertIn('showBubbleCartRecovery("exit_intent_with_cart")', flows)

    def test_triggers_schedule_observes(self) -> None:
        tri = _TRIGGERS.read_text(encoding="utf-8")
        self.assertIn("hesitation_scheduled", tri)
        self.assertIn("exit_intent_scheduled", tri)

    def test_runtime_version_bumped(self) -> None:
        wl = _WIDGET_LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-widget-trigger-arbitration-shadow-v1", wl)

    def test_no_enforcement_gate_in_flows(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertNotIn("requestWidgetOpen", flows.replace("observeWidgetOpenAttempt", ""))
        self.assertNotIn("decision.action", flows)


class WidgetArbitrationShadowDecisionTests(unittest.TestCase):
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
        self.assertGreaterEqual(payload.get("total"), 10)


if __name__ == "__main__":
    unittest.main()
