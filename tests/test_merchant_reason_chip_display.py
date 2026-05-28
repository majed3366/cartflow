# -*- coding: utf-8 -*-
"""Merchant dashboard reason chip must preserve widget reason labels."""
from __future__ import annotations

import unittest

from services.merchant_dashboard_reference_ui import (
    merchant_reason_canonical_key,
    merchant_reason_chip_class_and_label,
)


class MerchantReasonChipDisplayTests(unittest.TestCase):
    def test_quality_stays_quality_not_trust(self) -> None:
        cls, lbl = merchant_reason_chip_class_and_label("quality")
        self.assertEqual(cls, "c-quality")
        self.assertEqual(lbl, "الجودة")
        self.assertNotIn("الثقة", lbl)

    def test_quality_uncertainty_canonicalizes_to_quality(self) -> None:
        self.assertEqual(merchant_reason_canonical_key("quality_uncertainty"), "quality")
        cls, lbl = merchant_reason_chip_class_and_label("quality_uncertainty")
        self.assertEqual(lbl, "الجودة")

    def test_warranty_not_merged_with_quality(self) -> None:
        cls, lbl = merchant_reason_chip_class_and_label("warranty")
        self.assertEqual(cls, "c-warranty")
        self.assertEqual(lbl, "الضمان")

    def test_human_support_stays_trust_class(self) -> None:
        cls, lbl = merchant_reason_chip_class_and_label("human_support")
        self.assertEqual(cls, "c-trust")
        self.assertIn("دعم", lbl)

    def test_price_high_unchanged(self) -> None:
        cls, lbl = merchant_reason_chip_class_and_label("price_high")
        self.assertEqual(cls, "c-price")
        self.assertIn("السعر", lbl)


if __name__ == "__main__":
    unittest.main()
