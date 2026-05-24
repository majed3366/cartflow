# -*- coding: utf-8 -*-
"""Adaptive dashboard home stage resolution."""
from __future__ import annotations

import unittest

from services.merchant_dashboard_home_stage_v1 import (
    ACTIVATION_DISPLAY_COMPACT,
    ACTIVATION_DISPLAY_HIDDEN,
    ACTIVATION_DISPLAY_PROMINENT,
    HOME_STAGE_ACTIVATED,
    HOME_STAGE_ACTIVATION,
    HOME_STAGE_PRODUCTION,
    resolve_merchant_home_layout,
)


class TestMerchantHomeStage(unittest.TestCase):
    def test_new_merchant_activation_stage(self) -> None:
        layout = resolve_merchant_home_layout(
            None,
            onboarding_complete=False,
            first_cart=False,
        )
        self.assertEqual(layout.home_stage, HOME_STAGE_ACTIVATION)
        self.assertEqual(layout.activation_display, ACTIVATION_DISPLAY_PROMINENT)
        self.assertFalse(layout.hide_setup_card)

    def test_activated_stage(self) -> None:
        layout = resolve_merchant_home_layout(
            None,
            onboarding_complete=True,
            first_cart=True,
            first_sent=True,
            activation_working=True,
        )
        self.assertEqual(layout.home_stage, HOME_STAGE_ACTIVATED)
        self.assertEqual(layout.activation_display, ACTIVATION_DISPLAY_COMPACT)
        self.assertTrue(layout.hide_setup_card)

    def test_production_stage(self) -> None:
        layout = resolve_merchant_home_layout(
            None,
            onboarding_complete=True,
            first_cart=True,
            first_sent=True,
            first_recovered=True,
            month_recovered=2,
        )
        self.assertEqual(layout.home_stage, HOME_STAGE_PRODUCTION)
        self.assertEqual(layout.activation_display, ACTIVATION_DISPLAY_HIDDEN)


if __name__ == "__main__":
    unittest.main()
