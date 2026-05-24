# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.merchant_activation_v1 import _activation_milestone_flags_for_layout


class TestActivationMilestoneFlags(unittest.TestCase):
    def test_list_milestones_do_not_raise(self) -> None:
        """API milestones are a list; .get() on list caused summary inspect to fail."""
        out = {
            "milestones": [
                {"milestone_id": "first_cart", "done": True, "title_ar": "x"},
                {"milestone_id": "first_message", "done": True, "title_ar": "y"},
            ]
        }
        first_cart, first_scheduled, first_sent, first_recovered = (
            _activation_milestone_flags_for_layout(None, out)
        )
        self.assertTrue(first_cart)
        self.assertTrue(first_sent)
        self.assertFalse(first_scheduled)
        self.assertFalse(first_recovered)


if __name__ == "__main__":
    unittest.main()
