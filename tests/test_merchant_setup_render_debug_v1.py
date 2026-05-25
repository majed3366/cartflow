# -*- coding: utf-8 -*-
"""Merchant setup render debug payload on dashboard summary."""
from __future__ import annotations

import unittest

from services.merchant_setup_experience_v1 import merchant_setup_render_debug_payload
from services.merchant_setup_render_build import MERCHANT_SETUP_RENDER_BUILD


class TestMerchantSetupRenderDebug(unittest.TestCase):
    def test_debug_payload_includes_build_and_flags(self) -> None:
        exp = {
            "unified_p0": True,
            "setup_mode": True,
            "show_card": True,
            "steps": [{"phase": "sandbox", "step_id": "sandbox_account"}],
        }
        act = {"hide_setup_card": False, "home_stage": "activation"}
        dbg = merchant_setup_render_debug_payload(exp, activation=act)
        self.assertEqual(dbg["MERCHANT_SETUP_RENDER_BUILD"], MERCHANT_SETUP_RENDER_BUILD)
        self.assertTrue(dbg["unified_p0"])
        self.assertTrue(dbg["setup_mode"])
        self.assertTrue(dbg["show_card"])
        self.assertTrue(dbg["has_phase_steps"])


if __name__ == "__main__":
    unittest.main()
