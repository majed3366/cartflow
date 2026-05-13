# -*- coding: utf-8 -*-
"""Static checks for additive layered widget runtime (v2) modules."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_LOADER = _ROOT / "static" / "widget_loader.js"


class CartflowWidgetLayeredRuntimeTests(unittest.TestCase):
    def test_v2_loader_orders_modules_and_busts_cache(self) -> None:
        s = (_RUNTIME / "cartflow_widget_loader.js").read_text(encoding="utf-8")
        self.assertIn("[CF V2 LOAD START]", s)
        self.assertIn("layered-runtime-v4", s)
        p = s.index("cartflow_widget_phone.js")
        u = s.index("cartflow_widget_ui.js")
        f = s.index("cartflow_widget_flows.js")
        self.assertLess(p, u)
        self.assertLess(u, f)

    def test_runtime_modules_exist(self) -> None:
        expected = (
            "cartflow_widget_loader.js",
            "cartflow_widget_config.js",
            "cartflow_widget_state.js",
            "cartflow_widget_triggers.js",
            "cartflow_widget_flows.js",
            "cartflow_widget_phone.js",
            "cartflow_widget_api.js",
            "cartflow_widget_ui.js",
            "cartflow_widget_legacy_bridge.js",
        )
        for name in expected:
            p = _RUNTIME / name
            self.assertTrue(p.is_file(), f"Missing runtime module {p.relative_to(_ROOT)}")

    def test_unified_loader_branches_on_runtime_v2_flag(self) -> None:
        s = _LOADER.read_text(encoding="utf-8")
        self.assertIn("CARTFLOW_WIDGET_RUNTIME_V2", s)
        self.assertIn("/static/cartflow_widget_runtime/cartflow_widget_loader.js", s)
        self.assertIn("/static/cartflow_widget.js", s)
