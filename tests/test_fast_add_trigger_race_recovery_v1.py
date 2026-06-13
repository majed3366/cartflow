# -*- coding: utf-8 -*-
"""Fast Add Trigger Race Recovery v1 — static wiring checks."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_TRIGGERS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_triggers.js"
_BRIDGE = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_storefront_cart_bridge_core.js"
_LOADER = _ROOT / "static" / "widget_loader.js"


class FastAddTriggerRaceRecoveryV1Tests(unittest.TestCase):
    def test_runtime_version_bumped(self) -> None:
        wl = _LOADER.read_text(encoding="utf-8")
        self.assertIn("v2-fast-add-trigger-race-recovery-v1", wl)

    def test_triggers_durable_replay_wiring(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        for needle in (
            "onStorefrontCartPersisted",
            "storefrontBridgeHasCart",
            "scheduleDeferredReplay",
            "[CF TRIGGER DEFERRED REPLAY]",
            "finalizeDeferredHesitation",
            "recordDeferredArmIntent",
            "exhausted_explicit_schedule",
        ):
            self.assertIn(needle, s)

    def test_flush_no_silent_cart_miss(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        self.assertIn("storefrontPending", s)
        self.assertIn("scheduleDeferredReplay", s)
        self.assertNotIn("if (!had || !stRef || stRef.bubbleShown || !haveCartApprox())", s)

    def test_storefront_bridge_calls_triggers_on_post_ok(self) -> None:
        s = _BRIDGE.read_text(encoding="utf-8")
        self.assertIn("onStorefrontCartPersisted", s)
        self.assertIn("Cf.Triggers.onStorefrontCartPersisted", s)

    def test_have_cart_includes_storefront_bridge(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        idx = s.index("function haveCartApprox()")
        body = s[idx : idx + 800]
        self.assertIn("storefrontBridgeHasCart()", body)


if __name__ == "__main__":
    unittest.main()
