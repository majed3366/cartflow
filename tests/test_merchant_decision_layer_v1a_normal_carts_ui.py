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
    def test_normal_cart_workspace_omits_merchant_intervention_label(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartWorkspaceFromParts")
        self.assertNotIn("تدخل التاجر", block)

    def test_suggested_action_from_projection_not_js_gate(self) -> None:
        suggested = _extract_js_function(_LAZY_JS, "merchantSuggestedActionPrimaryHtml")
        self.assertIn("proj.suggested_action", suggested)
        self.assertNotIn("NORMAL_CART_MERCHANT_EXECUTABLE_DECISION_KEYS", _LAZY_JS)

    def test_workspace_no_inline_suggested_action_label(self) -> None:
        suggested = _extract_js_function(_LAZY_JS, "merchantSuggestedActionPrimaryHtml")
        self.assertNotIn("الإجراء المقترح:", suggested)

    def test_vip_manual_follow_up_surfaces_unchanged(self) -> None:
        self.assertIn("__maVipCartsTestHooks", _LAZY_JS)
        self.assertIn("applyVipCarts", _LAZY_JS)
        self.assertIn("ma-vip-suggest-btn", _VIP_AUTOMATION_JS)
        self.assertIn("تواصل يدوي", _VIP_AUTOMATION_JS)


if __name__ == "__main__":
    unittest.main()
