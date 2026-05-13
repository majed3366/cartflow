# -*- coding: utf-8 -*-
"""
Static + HTML-contract guards for the stable V2 demo storefront baseline.

Intent: catching accidental removal of shim wiring, UX flow scaffolding, or
hesitation/add-to-cart wiring before unrelated cleanups ship. Browser behavior
is *not* executed here — only deterministic source / response inspection.
"""

from __future__ import annotations

import pathlib
import unittest

from fastapi.testclient import TestClient

from main import app


_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME_DIR = _ROOT / "static" / "cartflow_widget_runtime"


class V2WidgetBaselineLockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_demo_store_pages_use_v2_shim_not_legacy_blob(self) -> None:
        """Primary storefront: widget_loader + V2 flag; never inline legacy monolith."""
        for path in ("/demo/store", "/demo/store/cart", "/demo/store/product/1"):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200, f"{path}: {r.text[:400]}")
            t = r.text or ""
            self.assertIn("widget_loader.js", t, path)
            self.assertIn("CARTFLOW_WIDGET_RUNTIME_V2", t, path)
            self.assertNotIn('/static/cartflow_widget.js"', t, path)

    def test_widget_loader_coerces_demo_store_v2(self) -> None:
        """Shim must keep /demo/store* on layered runtime (path guard)."""
        wl = (_ROOT / "static" / "widget_loader.js").read_text(encoding="utf-8")
        self.assertIn("cartflowIsDemoStorePrimaryV2Path", wl)
        self.assertIn("/demo/store", wl)
        self.assertIn("CARTFLOW_WIDGET_RUNTIME_V2 = true", wl)

    def test_v2_runtime_module_chain_is_declared(self) -> None:
        """Serial loader chain must list every expected module (order-sensitive)."""
        loader = (_RUNTIME_DIR / "cartflow_widget_loader.js").read_text(encoding="utf-8")
        self.assertIn("var MODULES = [", loader)
        for name in (
            "cartflow_widget_config.js",
            "cartflow_widget_api.js",
            "cartflow_widget_state.js",
            "cartflow_widget_triggers.js",
            "cartflow_widget_phone.js",
            "cartflow_widget_shell.js",
            "cartflow_widget_ui.js",
            "cartflow_widget_flows.js",
            "cartflow_widget_legacy_bridge.js",
        ):
            self.assertIn(f'"{name}"', loader, f"MODULES missing {name}")
            self.assertTrue((_RUNTIME_DIR / name).is_file(), f"Missing file {name}")

    def test_add_to_cart_hesitation_path_exists_in_triggers(self) -> None:
        tri = (_RUNTIME_DIR / "cartflow_widget_triggers.js").read_text(encoding="utf-8")
        self.assertIn('logFired("add_to_cart"', tri)
        self.assertIn("cf-demo-cart-updated", tri)
        self.assertIn('"add_to_cart"', tri)

    def test_yes_no_reason_phone_continuation_steps_exist_in_ui(self) -> None:
        ui = (_RUNTIME_DIR / "cartflow_widget_ui.js").read_text(encoding="utf-8")
        for step in ("yes_no", "reason", "phone", "continuation"):
            self.assertIn(f'Shell.setStep("{step}")', ui, step)
        self.assertIn("renderYesNo", ui)
        self.assertIn("renderReasonGrid", ui)
        self.assertIn("renderPhoneStep", ui)
        self.assertIn("renderContinuation", ui)
        self.assertIn("[CF V2 SHOW YESNO]", ui)
        self.assertIn("[CF V2 SHOW REASONS]", ui)
        self.assertIn("[CF V2 SHOW PHONE]", ui)
        self.assertIn("[CF V2 SHOW CONTINUATION]", ui)
        self.assertIn("أكمل الطلب", ui)

    def test_cart_recovery_no_minimizes_or_hides(self) -> None:
        """Baseline: «لا» on cart recovery yes/no minimizes launcher (not only close)."""
        flows = (_RUNTIME_DIR / "cartflow_widget_flows.js").read_text(encoding="utf-8")
        self.assertIn("Cf.Ui.renderYesNo", flows)
        self.assertIn("minimizeLauncher", flows)
        anchor = flows.find("question: getCartRecoveryQuestion()")
        self.assertGreater(anchor, 0, "cart recovery renderYesNo anchor missing")
        window = flows[anchor : anchor + 1800]
        self.assertIn("onNo: function () {", window)
        self.assertIn("minimizeLauncher()", window)


if __name__ == "__main__":
    unittest.main()
