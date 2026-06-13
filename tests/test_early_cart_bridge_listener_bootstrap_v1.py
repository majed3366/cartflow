# -*- coding: utf-8 -*-
"""Early Cart Bridge Listener Bootstrap v1 — static wiring checks."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_LOADER = _ROOT / "static" / "widget_loader.js"
_SOURCES = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_cart_sources.js"
_BRIDGE_CORE = (
    _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_storefront_cart_bridge_core.js"
)

EXPECTED = "v2-early-cart-bridge-listener-bootstrap-v1"


class EarlyCartBridgeListenerBootstrapV1Tests(unittest.TestCase):
    def test_runtime_version_bumped(self) -> None:
        wl = _LOADER.read_text(encoding="utf-8")
        self.assertIn(EXPECTED, wl)

    def test_early_listener_in_widget_loader(self) -> None:
        wl = _LOADER.read_text(encoding="utf-8")
        for needle in (
            "cartflowEarlyCartClickBootstrap",
            "__CARTFLOW_EARLY_CART_BOOTSTRAP__",
            "[CF EARLY CART LISTENER BOUND]",
            "[CF EARLY CART CLICK CAPTURED]",
            "DOMContentLoaded",
            "document.addEventListener(\"click\", onCaptureClick, true)",
        ):
            self.assertIn(needle, wl)

    def test_early_bind_before_window_load_widget(self) -> None:
        wl = _LOADER.read_text(encoding="utf-8")
        early_ix = wl.index("cartflowEarlyCartClickBootstrap")
        load_ix = wl.index('window.addEventListener("load", loadWidget)')
        self.assertLess(early_ix, load_ix)

    def test_replay_wiring_in_cart_sources(self) -> None:
        s = _SOURCES.read_text(encoding="utf-8")
        for needle in (
            "_replayEarlyCapturedClicks",
            "__CARTFLOW_EARLY_CART_BOOTSTRAP__",
            "consumeQueue",
            "markBridgeReady",
            "[CF EARLY CART CLICK REPLAY]",
            "[CF EARLY CART CLICK REPLAY DIAGNOSTIC]",
            "early_click_replay_1200ms",
        ):
            self.assertIn(needle, s)
        init_ix = s.index("init: function (bridge)")
        replay_ix = s.index("_replayEarlyCapturedClicks")
        install_ix = s.index("_installClickListener();")
        self.assertLess(install_ix, replay_ix)
        init_body = s[init_ix:replay_ix]
        self.assertEqual(init_body.count("_installClickListener();"), 1)

    def test_bridge_core_priority_early_click_hint(self) -> None:
        s = _BRIDGE_CORE.read_text(encoding="utf-8")
        self.assertIn("early_click", s)


if __name__ == "__main__":
    unittest.main()
