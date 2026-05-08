# -*- coding: utf-8 -*-
"""Source-level checks for log markers and front-end idempotency guards (no JS execution)."""
from __future__ import annotations

import os
import unittest


def _read(rel: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, rel.replace("/", os.sep))
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


class OperationalStaticObservabilityTests(unittest.TestCase):
    def test_log_markers_exist_for_runtime_triage(self) -> None:
        main_src = _read("main.py")
        self.assertIn("[PHONE RESOLUTION]", main_src)
        self.assertIn("[NORMAL RECOVERY STATUS UPDATE]", main_src)
        wa_src = _read("services/whatsapp_send.py")
        self.assertIn("[WA SENT]", wa_src)
        self.assertIn("[WA STATUS]", wa_src)
        ret_src = _read("services/behavioral_recovery/user_return.py")
        self.assertIn("[RETURN TO SITE BACKEND PERSISTED]", ret_src)
        loader = _read("static/widget_loader.js")
        self.assertIn("[CARTFLOW RUNTIME]", loader)

    def test_widget_boot_duplicate_guards_present(self) -> None:
        """Loader and widget bundle declare single-flight guards (operational maintainability)."""
        loader = _read("static/widget_loader.js")
        self.assertIn("__CARTFLOW_RT_SCRIPT_SCHEDULED__", loader)
        self.assertIn("__CARTFLOW_WIDGET_LOADER_ACTIVE__", loader)
        widget = _read("static/cartflow_widget.js")
        self.assertIn("__CARTFLOW_WIDGET_ACTIVE__", widget)
        self.assertIn("skipped duplicate", widget.lower())

    def test_exit_intent_constants_present(self) -> None:
        widget = _read("static/cartflow_widget.js")
        self.assertIn("exit_intent", widget.lower())

    def test_normal_recovery_message_path_has_no_llm_import(self) -> None:
        """Rule-based default path for abandonment copy: no AI client usage in strategy module."""
        strat = _read("services/recovery_message_strategy.py")
        lowered = strat.lower()
        self.assertNotIn("anthropic", lowered)
        self.assertNotIn("openai", lowered)

    def test_duplicate_attempt_guard_string_in_recovery_sources(self) -> None:
        main_src = _read("main.py")
        self.assertIn("skipped_duplicate", main_src)
        self.assertIn("already_sent", main_src)


class OperationalDemoIntegrationSourceTests(unittest.TestCase):
    """Template-level consistency: demo store exposes store slug for client bundles."""

    def test_demo_store_sets_cartflow_store_slug(self) -> None:
        demo = _read("templates/demo_store.html")
        self.assertIn("window.CARTFLOW_STORE_SLUG", demo)
