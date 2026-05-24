# -*- coding: utf-8 -*-
"""Activation visibility debug payload."""
from __future__ import annotations

import unittest

from services.merchant_activation_visibility_debug_v1 import (
    build_activation_visibility_debug,
)
from services.merchant_dashboard_home_stage_v1 import (
    ACTIVATION_DISPLAY_HIDDEN,
    resolve_merchant_home_layout,
)


class TestActivationVisibilityDebug(unittest.TestCase):
    def test_production_debug_lists_reasons(self) -> None:
        layout = resolve_merchant_home_layout(
            None,
            onboarding_complete=True,
            first_cart=True,
            first_sent=True,
            first_recovered=True,
            month_recovered=1,
        )
        self.assertEqual(layout.activation_display, ACTIVATION_DISPLAY_HIDDEN)
        dbg = build_activation_visibility_debug(
            layout,
            onboarding_complete=True,
            first_cart=True,
            first_sent=True,
            first_recovered=True,
            month_recovered=1,
        )
        self.assertEqual(dbg["verdict_primary"], "B")
        self.assertIn("first_recovered", dbg["production_signal_reasons"])
        self.assertIn("month_recovered_gt_0", dbg["production_signal_reasons"])
        self.assertTrue(dbg["hide_setup_card"])


if __name__ == "__main__":
    unittest.main()
