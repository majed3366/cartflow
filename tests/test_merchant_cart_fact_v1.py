# -*- coding: utf-8 -*-
"""Merchant cart fact v1 — unit tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.merchant_cart_fact_v1 import (
    FACT_KIND_CHECKOUT,
    FACT_KIND_PURCHASED,
    FACT_KIND_RETURNED,
    LABEL_CHECKOUT_AR,
    LABEL_PURCHASED_AR,
    LABEL_RETURNED_AR,
    attach_merchant_cart_fact_v1,
    resolve_merchant_cart_fact_v1,
)


def _resolve(**kwargs: object) -> dict[str, str] | None:
    return resolve_merchant_cart_fact_v1(**kwargs)  # type: ignore[arg-type]


class MerchantCartFactV1PurchaseTests(unittest.TestCase):
    def test_p1_purchase_truth(self) -> None:
        fact = _resolve(purchase_truth=True)
        self.assertEqual(fact, {"kind": FACT_KIND_PURCHASED, "label_ar": LABEL_PURCHASED_AR})

    def test_p2_purchased_variant(self) -> None:
        fact = _resolve(
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="purchased",
        )
        self.assertEqual(fact, {"kind": FACT_KIND_PURCHASED, "label_ar": LABEL_PURCHASED_AR})

    def test_p3_recovered_only_not_purchase(self) -> None:
        fact = _resolve(
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="recovered",
            behavioral={"user_returned_to_site": True},
        )
        self.assertNotEqual(fact and fact.get("kind"), FACT_KIND_PURCHASED)
        self.assertEqual(fact, {"kind": FACT_KIND_RETURNED, "label_ar": LABEL_RETURNED_AR})


class MerchantCartFactV1CheckoutTests(unittest.TestCase):
    def test_c1_checkout_page_flag(self) -> None:
        fact = _resolve(behavioral={"recovery_returned_checkout_page": True})
        self.assertEqual(fact, {"kind": FACT_KIND_CHECKOUT, "label_ar": LABEL_CHECKOUT_AR})

    def test_c2_checkout_context(self) -> None:
        fact = _resolve(behavioral={"recovery_return_context": "checkout"})
        self.assertEqual(fact, {"kind": FACT_KIND_CHECKOUT, "label_ar": LABEL_CHECKOUT_AR})


class MerchantCartFactV1ReturnTests(unittest.TestCase):
    def test_r1_returned_flag(self) -> None:
        fact = _resolve(behavioral={"user_returned_to_site": True})
        self.assertEqual(fact, {"kind": FACT_KIND_RETURNED, "label_ar": LABEL_RETURNED_AR})

    def test_r2_return_timestamp(self) -> None:
        fact = _resolve(behavioral={"recovery_return_timestamp": "2026-06-30T12:00:00Z"})
        self.assertEqual(fact, {"kind": FACT_KIND_RETURNED, "label_ar": LABEL_RETURNED_AR})


class MerchantCartFactV1PriorityTests(unittest.TestCase):
    def test_purchase_beats_checkout_and_return(self) -> None:
        fact = _resolve(
            purchase_truth=True,
            behavioral={
                "recovery_returned_checkout_page": True,
                "user_returned_to_site": True,
            },
        )
        self.assertEqual(fact, {"kind": FACT_KIND_PURCHASED, "label_ar": LABEL_PURCHASED_AR})

    def test_checkout_beats_return(self) -> None:
        fact = _resolve(
            behavioral={
                "recovery_returned_checkout_page": True,
                "user_returned_to_site": True,
            }
        )
        self.assertEqual(fact, {"kind": FACT_KIND_CHECKOUT, "label_ar": LABEL_CHECKOUT_AR})


class MerchantCartFactV1VipAndAttachTests(unittest.TestCase):
    def test_vip_suppression(self) -> None:
        self.assertIsNone(
            _resolve(
                is_vip_lane=True,
                purchase_truth=True,
                behavioral={"recovery_returned_checkout_page": True},
            )
        )

    def test_attach_sets_fact(self) -> None:
        row: dict[str, object] = {}
        attach_merchant_cart_fact_v1(
            row,
            purchase_truth=True,
        )
        self.assertEqual(
            row.get("merchant_cart_fact_v1"),
            {"kind": FACT_KIND_PURCHASED, "label_ar": LABEL_PURCHASED_AR},
        )

    def test_attach_omits_when_none(self) -> None:
        row: dict[str, object] = {"recovery_key": "store:cart-1"}
        attach_merchant_cart_fact_v1(row)
        self.assertNotIn("merchant_cart_fact_v1", row)


class MerchantCartFactV1JsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._lazy_js = (
            Path(__file__).resolve().parents[1]
            / "static"
            / "merchant_dashboard_lazy.js"
        ).read_text(encoding="utf-8")

    def test_lazy_js_has_fact_renderer(self) -> None:
        self.assertIn("function merchantCartFactHtml", self._lazy_js)
        self.assertIn("merchant_cart_fact_v1", self._lazy_js)
        self.assertIn("ma-cart-fact-v1", self._lazy_js)

    def test_cart_row_full_renders_fact_before_lifecycle(self) -> None:
        fn = self._lazy_js[
            self._lazy_js.index("function cartRowFull")
            : self._lazy_js.index("function normalCartsLoadingRowHtml")
        ]
        self.assertIn("merchantCartFactHtml(mc)", fn)
        idx_fact = fn.index("merchantCartFactHtml(mc)")
        idx_lifecycle = fn.index("lifecycleTruthHtml(mc)")
        self.assertLess(idx_fact, idx_lifecycle)

    def test_fact_renderer_no_hadath_muhim_heading(self) -> None:
        block = self._lazy_js[
            self._lazy_js.index("function merchantCartFactHtml")
            : self._lazy_js.index("function customerLifecycleExplanationHtml")
        ]
        self.assertNotIn("حدث مهم", block)


if __name__ == "__main__":
    unittest.main()
