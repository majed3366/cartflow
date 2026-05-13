# -*- coding: utf-8 -*-
"""Static checks for V2 trigger orchestrator (cartflow_widget_triggers.js)."""
from __future__ import annotations

import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent
_TRIGGERS = _ROOT / "static" / "cartflow_widget_runtime" / "cartflow_widget_triggers.js"


class CartflowWidgetTriggerOrchestratorTests(unittest.TestCase):
    def test_orchestrator_diagnostic_logs(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        for tag in (
            "[CF TRIGGER ORCHESTRATOR READY]",
            "[CF TRIGGER RECEIVED]",
            "[CF TRIGGER SCHEDULED]",
            "[CF TRIGGER FIRED]",
            "[CF TRIGGER BLOCKED]",
            "[CF TRIGGER CLEARED]",
        ):
            self.assertIn(tag, s)

    def test_receive_trigger_exported(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        self.assertIn("receiveTrigger", s)
        self.assertIn("window.CartflowWidgetRuntime.Triggers = Triggers", s)

    def test_blocking_reason_lexicon(self) -> None:
        s = _TRIGGERS.read_text(encoding="utf-8")
        for reason in (
            "widget_disabled",
            "no_cart",
            "page_scope_blocked",
            "checkout_started",
            "purchase_completed",
            "frequency_blocked",
            "recently_dismissed",
            "timer_replaced",
        ):
            self.assertIn(reason, s)


if __name__ == "__main__":
    unittest.main()
