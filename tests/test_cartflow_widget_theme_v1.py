# -*- coding: utf-8 -*-
"""Static checks for merchant-color theme token runtime."""
from __future__ import annotations

import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_RUNTIME = _ROOT / "static" / "cartflow_widget_runtime"
_THEME = _RUNTIME / "cartflow_widget_theme.js"
_LOADER = _RUNTIME / "cartflow_widget_loader.js"

_LEGACY_HEX = re.compile(
    r"6366f1|4f46e5|4338ca|312e81|1e1b4b|99,\s*102,\s*241",
    re.IGNORECASE,
)

_RUNTIME_VISUAL_FILES = (
    "cartflow_widget_shell.js",
    "cartflow_widget_ui.js",
    "cartflow_widget_flows.js",
    "cartflow_widget_theme.js",
)


class CartflowWidgetThemeTests(unittest.TestCase):
    def test_theme_module_exports_tokens_and_logs(self) -> None:
        s = _THEME.read_text(encoding="utf-8")
        self.assertIn("Cf.Theme = Theme", s)
        self.assertIn("[CF THEME TOKENS]", s)
        self.assertIn("[CF LEGACY PURPLE CHECK]", s)
        self.assertIn("--cf-primary", s)
        self.assertIn("--cf-surface", s)
        self.assertIn("--cf-border", s)
        self.assertIn("--cf-hover", s)
        self.assertIn("--cf-focus", s)

    def test_loader_includes_theme_module(self) -> None:
        s = _LOADER.read_text(encoding="utf-8")
        self.assertIn("cartflow_widget_theme.js", s)
        self.assertIn('"Theme"', s)

    def test_runtime_visual_files_have_no_legacy_purple_tokens(self) -> None:
        theme_src = _THEME.read_text(encoding="utf-8")
        theme_body = theme_src.split("var _tokens = null", 1)[0]
        theme_body = theme_body.split("LEGACY_PURPLE_PATTERNS", 1)[0]
        self.assertIsNone(
            _LEGACY_HEX.search(theme_body),
            "legacy purple token found in theme.js outside audit patterns",
        )
        for name in _RUNTIME_VISUAL_FILES:
            if name == "cartflow_widget_theme.js":
                continue
            src = (_RUNTIME / name).read_text(encoding="utf-8")
            self.assertIsNone(
                _LEGACY_HEX.search(src),
                f"legacy purple token found in {name}",
            )


if __name__ == "__main__":
    unittest.main()
