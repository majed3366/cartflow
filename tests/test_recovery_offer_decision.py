# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from services.recovery_offer_decision import decide_recovery_offer_strategy


class RecoveryOfferDecisionTests(unittest.TestCase):
    def test_premium_high_price_no_discount(self) -> None:
        d = decide_recovery_offer_strategy(
            "price",
            800.0,
            "",
            "غالي جدا",
            has_cheaper_alternative=True,
        )
        self.assertFalse(d["should_offer_discount"])
        self.assertFalse(d["should_offer_alternative"])

    def test_alternative_before_discount_mid_tier(self) -> None:
        d = decide_recovery_offer_strategy(
            "price",
            200.0,
            "",
            "غالي",
            has_cheaper_alternative=True,
        )
        self.assertTrue(d["should_offer_alternative"])
        self.assertFalse(d["should_offer_discount"])
        self.assertEqual(d["strategy_type"], "alternative_first")

    def test_low_price_avoids_discount(self) -> None:
        d = decide_recovery_offer_strategy(
            "price",
            40.0,
            "",
            "غالي جدا",
            has_cheaper_alternative=False,
        )
        self.assertFalse(d["should_offer_discount"])

    def test_expensive_reassurance_without_alt(self) -> None:
        d = decide_recovery_offer_strategy(
            "price",
            500.0,
            "",
            "غالي شوي",
            has_cheaper_alternative=False,
        )
        self.assertFalse(d["should_offer_discount"])
        self.assertFalse(d["should_offer_alternative"])
        self.assertEqual(d["strategy_type"], "reassurance_only")

    def test_high_conf_mid_allows_soft_discount_without_alt(self) -> None:
        d = decide_recovery_offer_strategy(
            "price",
            200.0,
            "",
            "غالي جدا ومبالغ فيه",
            has_cheaper_alternative=False,
        )
        self.assertTrue(d["should_offer_discount"])
        self.assertEqual(d["strategy_type"], "soft_discount_path")


if __name__ == "__main__":
    unittest.main()
