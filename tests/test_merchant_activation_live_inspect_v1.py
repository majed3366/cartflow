# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.merchant_activation_live_inspect_v1 import (
    activation_inspect_response,
    infer_ui_blocker_inferred,
)


class TestActivationLiveInspect(unittest.TestCase):
    def test_inspect_response_shape(self) -> None:
        body = {
            "merchant_kpi_abandoned_fmt": "99",
            "merchant_activation": {
                "home_stage": "activated",
                "activation_display": "compact",
                "hide_setup_card": True,
                "production_signal_reasons": [],
                "milestones": [{"milestone_id": "first_cart", "done": True}],
            },
            "merchant_activation_visibility_debug": {
                "ui_blocker_server": "x",
            },
        }
        snap = activation_inspect_response(body)
        self.assertNotIn("merchant_kpi_abandoned_fmt", snap)
        self.assertEqual(snap["merchant_activation"]["home_stage"], "activated")
        self.assertIn("merchant_activation_visibility_debug", snap)

    def test_infer_hidden(self) -> None:
        act = {"activation_display": "hidden", "production_signal_reasons": ["x"]}
        self.assertEqual(
            infer_ui_blocker_inferred(act, {}),
            "server_activation_display_hidden",
        )


if __name__ == "__main__":
    unittest.main()
