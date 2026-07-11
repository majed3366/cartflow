# -*- coding: utf-8 -*-
"""Investigation-only instrumentation presence for Fast Path Root Cause V1."""
from __future__ import annotations

import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ROUTES = (_ROOT / "routes/cartflow.py").read_text(encoding="utf-8")
_FLOWS = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_flows.js").read_text(
    encoding="utf-8"
)
_FETCH = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_fetch.js").read_text(
    encoding="utf-8"
)
_LOADER = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")


class WidgetFastPathInvestV1Tests(unittest.TestCase):
    def test_server_stage_clock_and_cf_timing(self) -> None:
        self.assertIn("class _ReasonStageClock", _ROUTES)
        self.assertIn('phase="committed_reason_response"', _ROUTES)
        self.assertIn('"cf_timing": timing', _ROUTES)
        self.assertIn('clock.mark("db_warm")', _ROUTES)
        self.assertIn('clock.mark("db_commit")', _ROUTES)
        self.assertIn('clock.mark("schedule_recovery_bg")', _ROUTES)
        # Recovery still background — not awaited on response path
        self.assertIn("background_tasks.add_task", _ROUTES)
        self.assertIn("_arm_recovery_after_reason_saved_bg", _ROUTES)

    def test_client_trace_logs(self) -> None:
        self.assertIn("[CF FAST PATH TRACE]", _FLOWS)
        self.assertIn("reasonMark(\"ui_ack\")", _FLOWS)
        self.assertIn("reasonMark(\"bridge_ensure\")", _FLOWS)
        self.assertIn("reasonMark(\"post_reason\")", _FLOWS)
        self.assertIn("_cf_client_net_ms", _FETCH)
        self.assertIn("v2-widget-fast-path-invest-v1", _LOADER)


if __name__ == "__main__":
    unittest.main()
