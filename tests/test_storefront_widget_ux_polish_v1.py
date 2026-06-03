# -*- coding: utf-8 -*-
"""Storefront widget UX polish — back, minimize, stable viewport."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SHELL = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_shell.js"
_FLOWS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_flows.js"


class StorefrontWidgetUxPolishTests(unittest.TestCase):
    def test_close_minimizes_launcher(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        self.assertIn("minimizeLauncher();", shell)
        self.assertIn("[CF SHELL CHROME MINIMIZE]", shell)
        close_handler = shell.split("data-cf-shell-close")[1][:800]
        self.assertNotIn("close({ syncDismiss: true })", close_handler)

    def test_stable_content_viewport(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        self.assertIn("SHELL_EXPANDED_WIDTH_PX", shell)
        self.assertIn("applyExpandedShellLayout", shell)
        self.assertIn('mount.style.minHeight = "0"', shell)
        self.assertIn("applyStableContentViewport", shell)
        self.assertIn("other_recovery", shell)
        self.assertIn('mount.style.overflowY = "hidden"', shell)

    def test_compact_launcher_size(self) -> None:
        shell = _SHELL.read_text(encoding="utf-8")
        self.assertIn("SHELL_LAUNCHER_SIZE_PX", shell)
        self.assertIn("SHELL_LAUNCHER_SIZE_PX = 40", shell)
        self.assertIn("w.style.minHeight = SHELL_LAUNCHER_SIZE_PX", shell)

    def test_thanks_and_no_use_minimize_polite(self) -> None:
        flows = _FLOWS.read_text(encoding="utf-8")
        self.assertIn("minimizeWidgetPolite", flows)
        self.assertIn("gracefulCloseWidget", flows)


if __name__ == "__main__":
    unittest.main()
