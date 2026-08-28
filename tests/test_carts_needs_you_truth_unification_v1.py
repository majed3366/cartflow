# -*- coding: utf-8 -*-
"""Needs-You Truth Unification V1 — presentation-contract guards."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARTS_JS = (ROOT / "static" / "merchant_ui_v2_carts.js").read_text(encoding="utf-8")


class CartsNeedsYouTruthUnificationV1Tests(unittest.TestCase):
    def test_unification_marker_and_exports(self) -> None:
        self.assertIn("needs-you-unification-v1", CARTS_JS)
        self.assertIn("needsMerchantActionNow", CARTS_JS)
        self.assertIn("merchantResponsibility", CARTS_JS)
        self.assertIn("NEEDS_MERCHANT_ACTION_NOW", CARTS_JS)
        self.assertIn("WAITING_ON_CARTFLOW", CARTS_JS)

    def test_attention_filter_uses_primary_action_not_tabs(self) -> None:
        self.assertIn('if (filter === "attention") return needsMerchantActionNow(mc);', CARTS_JS)
        self.assertIn("attention: prim.needs_you", CARTS_JS)
        self.assertNotIn("merchant_cart_filter_counts", CARTS_JS)
        self.assertNotIn('tabs.indexOf("attention")', CARTS_JS)

    def test_primary_action_keys_unchanged(self) -> None:
        for key in (
            "wait",
            "contact_customer",
            "follow_up_manually",
            "review_cart",
            "no_action_required",
            "reopen",
        ):
            self.assertIn(key, CARTS_JS)
        self.assertIn("ACTIONABLE", CARTS_JS)

    def test_snapshot_miss_is_not_false_calm(self) -> None:
        self.assertIn("snapshotTruthPending", CARTS_JS)
        self.assertIn("تعذّر تأكيد حالة السلال", CARTS_JS)
        self.assertIn("لا نعرض هدوءاً افتراضياً", CARTS_JS)
        self.assertIn("hot_merged", CARTS_JS)

    def test_orientation_and_filter_share_count_primary(self) -> None:
        self.assertIn("var counts = countPrimary(state.rows);", CARTS_JS)
        self.assertIn("var fc = filterCounts();", CARTS_JS)
        self.assertIn("orientationCopy(counts)", CARTS_JS)


if __name__ == "__main__":
    unittest.main()
