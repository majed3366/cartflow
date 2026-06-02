# -*- coding: utf-8 -*-
"""Zid embed: approved cart-recovery V2 mode (not browsing assistant)."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_LOADER = _ROOT / "static" / "widget_loader.js"
_FLOWS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_flows.js"
_TRIGGERS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_triggers.js"


class ZidStorefrontRecoveryWidgetModeTests(unittest.TestCase):
    def test_browsing_assistant_copy_is_exit_no_cart_only(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("اختَر واحد يخدمك الآن", flows)
        idx_browse = flows.find("اختَر واحد يخدمك الآن")
        idx_show_exit = flows.find("function showExitNoCart")
        self.assertGreater(idx_show_exit, 0)
        self.assertGreater(idx_browse, idx_show_exit)

    def test_recovery_question_routes_to_reason_list_not_browsing(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("CARTFLOW_RECOVERY_WIDGET_MODE", flows)
        self.assertIn("exit_intent_storefront_recovery", flows)
        self.assertIn("showBubbleCartRecovery", flows)
        self.assertIn("mountReasonList();", flows)
        anchor = flows.find("fireExitNoCart: function ()")
        self.assertGreater(anchor, 0)
        block = flows[anchor : anchor + 420]
        self.assertIn("isStorefrontRecoveryMode()", block)
        self.assertIn('showBubbleCartRecovery("exit_intent_storefront_recovery")', block)

    def test_widget_loader_sets_recovery_mode_on_storefront_embed(self) -> None:
        loader = _LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflowIsStorefrontEmbed", loader)
        self.assertIn("cartflowEnsureStorefrontRecoveryMode", loader)
        self.assertIn("CARTFLOW_RECOVERY_WIDGET_MODE = true", loader)
        self.assertIn("[CARTFLOW RECOVERY MODE]", loader)
        self.assertIn("CARTFLOW_RUNTIME_VERSION = RUNTIME_VERSION", loader)

    def test_triggers_cart_path_fallback_when_recovery_mode(self) -> None:
        tri = _TRIGGERS.read_text(encoding="utf-8")
        self.assertIn("haveCartApproxFromStorefrontPath", tri)
        self.assertIn("storefrontRecoveryModeActive", tri)
        self.assertIn("/cart", tri)


if __name__ == "__main__":
    unittest.main()
