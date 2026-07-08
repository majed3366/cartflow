# -*- coding: utf-8 -*-
"""Cart example / remaining queue currency regression — SR prefix, single atom."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_CURRENCY_CSS = (
    _ROOT / "static" / "merchant_currency_certification_v1.css"
).read_text(encoding="utf-8")

_REJECTED = ("ر.س", "ريال", "ريال سعودي", '" ر"', "+ \" ر\"", "merchantCurrencyHtml(v)")
_LEGACY_NESTED = (
    '<div class="v2-queue-amount">' + "\n" + "      merchantCurrencyHtml",
    "v2-queue-amount'>" + "\n" + "      formatMerchantSarHtml",
)


class CurrencyCartExamplesV1Tests(unittest.TestCase):
    def test_mi_cart_queue_uses_single_certified_atom(self) -> None:
        self.assertIn("function queueAmountHtml", _MI_CARTS_JS)
        self.assertIn("function miCartQueueItemHtml", _MI_CARTS_JS)
        self.assertIn("merchantCurrencyText", _MI_CARTS_JS)
        self.assertIn("queueAmountHtml(v, esc)", _MI_CARTS_JS)
        self.assertIn('class="v2-queue-amount cf-currency-atom', _MI_CARTS_JS)
        self.assertIn("v2-queue-accent", _MI_CARTS_JS)
        self.assertIn("v2-queue-time", _MI_CARTS_JS)
        for bad in _LEGACY_NESTED:
            self.assertNotIn(bad, _MI_CARTS_JS)

    def test_mi_group_card_value_uses_certified_atom(self) -> None:
        self.assertIn("ma-mi-group-card__value cf-currency-atom", _MI_CARTS_JS)
        self.assertIn("merchantCurrencyText(value)", _MI_CARTS_JS)

    def test_no_legacy_arabic_currency_in_mi_renderer(self) -> None:
        fn_block = _MI_CARTS_JS.split("function miCartQueueItemHtml", 1)[1].split(
            "function workspaceSubtitle", 1
        )[0]
        for bad in _REJECTED:
            self.assertNotIn(bad, fn_block, msg=f"rejected token {bad!r} in queue renderer")
        self.assertNotIn("formatMerchantSarHtml", fn_block)

    def test_lazy_queue_matches_single_atom_pattern(self) -> None:
        block = _LAZY_JS.split("function cartQueueItemHtml", 1)[1].split(
            "function ", 1
        )[0]
        self.assertIn("queueAmountHtml(v)", block)
        self.assertIn('class="v2-queue-amount cf-currency-atom', _LAZY_JS)
        self.assertNotIn("formatMerchantSarHtml(v)", block)

    def test_css_prevents_queue_clipping_and_nested_atoms(self) -> None:
        for token in (
            "#page-carts .ma-mi-group-section__queue .v2-queue-item",
            "min-width: 0",
            ".v2-queue-amount.cf-currency-atom",
            "#page-carts .v2-queue-amount .cf-currency-atom",
        ):
            self.assertIn(token, _CURRENCY_CSS)

    def test_queue_amount_html_emits_sr_prefix_only(self) -> None:
        sample = (
            '<div class="v2-queue-amount cf-currency-atom cftyp-currency" '
            'data-cf-currency="1" dir="ltr">SR 449</div>'
        )
        self.assertRegex(sample, r"SR\s[\d,]+")
        self.assertIsNone(re.search(r"ر\.س|ريال", sample))
        self.assertEqual(sample.count("cf-currency-atom"), 1)


if __name__ == "__main__":
    unittest.main()
