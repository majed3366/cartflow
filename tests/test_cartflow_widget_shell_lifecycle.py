# -*- coding: utf-8 -*-
"""Static checks for V2 widget shell lifecycle and singleton guarantees.

Manual smoke (browser): __cfV2ShowNow → close × → reopen → reason → phone →
continuation → رجوع للأسباب → close → reopen. Expect [CF SHELL REUSED] on
reopens, single [data-cartflow-bubble][data-cf-shell="1"], no duplicate close
handlers (see [CF SHELL LISTENER DUPLICATE BLOCKED] if regression).
"""
from __future__ import annotations

import pathlib
import re
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_SHELL = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_shell.js"


class CartflowWidgetShellLifecycleTests(unittest.TestCase):
    def test_shell_has_lifecycle_diagnostic_logs(self) -> None:
        s = _SHELL.read_text(encoding="utf-8")
        for tag in (
            "[CF SHELL OPEN]",
            "[CF SHELL CLOSE]",
            "[CF SHELL CONTENT SET]",
            "[CF SHELL REUSED]",
            "[CF SHELL LISTENER DUPLICATE BLOCKED]",
        ):
            self.assertIn(tag, s)

    def test_shell_singleton_selector_and_dedupe(self) -> None:
        s = _SHELL.read_text(encoding="utf-8")
        self.assertIn('[data-cartflow-bubble][data-cf-shell="1"]', s)
        self.assertIn("dedupeShellRoots", s)
        self.assertIn("data-cf-shell-bound", s)

    def test_close_resets_shell_state_fields(self) -> None:
        s = _SHELL.read_text(encoding="utf-8")
        self.assertIsNotNone(
            re.search(
                r"patchShell\s*\(\s*\{[^}]*currentStep\s*:\s*null",
                s,
                re.DOTALL,
            ),
            "close() should patch shell state with null steps",
        )
        self.assertIn("lastTriggerSource: null", s)
        self.assertIn("clearContentMount", s)

    def test_set_content_logs_and_avoids_nested_innerhtml_only_stack(self) -> None:
        s = _SHELL.read_text(encoding="utf-8")
        self.assertIn("[CF SHELL CONTENT SET]", s)
        self.assertIn("while (mount.firstChild)", s)
        self.assertIn("removeChild(mount.firstChild)", s)


if __name__ == "__main__":
    unittest.main()
