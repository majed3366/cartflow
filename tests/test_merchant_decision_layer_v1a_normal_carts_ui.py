# -*- coding: utf-8 -*-
"""Merchant Decision Layer V1-A — normal-carts lifecycle UI adjustments."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_VIP_AUTOMATION_JS = (
    _ROOT / "static" / "merchant_vip_automation_ui.js"
).read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class MerchantDecisionLayerV1ANormalCartsUiTests(unittest.TestCase):
    def test_normal_cart_lifecycle_block_omits_merchant_intervention_label(self) -> None:
        block = _extract_js_function(_LAZY_JS, "customerLifecycleExplanationHtml")
        self.assertNotIn("تدخل التاجر", block)

    def test_normal_cart_lifecycle_block_keeps_operational_explanation(self) -> None:
        block = _extract_js_function(_LAZY_JS, "customerLifecycleExplanationHtml")
        self.assertIn("الحالة:", block)
        self.assertIn("ماذا حدث؟", block)
        self.assertIn("ماذا فعل النظام؟", block)
        self.assertIn("التالي:", block)

    def test_suggested_action_gated_by_executable_keys(self) -> None:
        self.assertIn("NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS", _LAZY_JS)
        suggested = _extract_js_function(_LAZY_JS, "merchantDecisionSuggestedActionHtml")
        self.assertIn("NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS[key]", suggested)
        self.assertNotRegex(
            _LAZY_JS,
            r"NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS\s*=\s*\{[^}]+obtain_contact",
        )

    def test_missing_phone_decision_key_not_shown_as_fake_action(self) -> None:
        suggested = _extract_js_function(_LAZY_JS, "merchantDecisionSuggestedActionHtml")
        self.assertIn("NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS[key]", suggested)
        lifecycle = _extract_js_function(_LAZY_JS, "customerLifecycleExplanationHtml")
        self.assertNotIn("الإجراء المقترح", lifecycle.replace(
            "merchantDecisionSuggestedActionHtml(mc)", ""
        ))

    def test_vip_manual_follow_up_surfaces_unchanged(self) -> None:
        self.assertIn("__maVipCartsTestHooks", _LAZY_JS)
        self.assertIn("applyVipCarts", _LAZY_JS)
        self.assertIn("ma-vip-suggest-btn", _VIP_AUTOMATION_JS)
        self.assertIn("تواصل يدوي", _VIP_AUTOMATION_JS)


if __name__ == "__main__":
    unittest.main()
