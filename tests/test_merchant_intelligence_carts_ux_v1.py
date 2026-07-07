# -*- coding: utf-8 -*-
"""Merchant Intelligence Carts UX Stabilization V1 — certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_POLISH_CSS = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(
    encoding="utf-8"
)

_INTERNAL_UI_TOKENS = (
    "waiting_first_send",
    "waiting_customer_reply",
    "needs_merchant",
    "reason_tag:",
    "decision_key",
    "lifecycle_state",
    "merchant_cart_primary_bucket",
)


class MerchantIntelligenceCartsUxV1Tests(unittest.TestCase):
    def test_expand_state_preserved_across_rerender(self) -> None:
        self.assertIn("openGroupState", _MI_CARTS_JS)
        self.assertIn("captureOpenGroups", _MI_CARTS_JS)
        self.assertIn("mousedown", _MI_CARTS_JS)
        self.assertIn("openGroupState[norm(group.group_id)]", _MI_CARTS_JS)

    def test_workspace_key_ignores_refresh_token(self) -> None:
        block = _LAZY_JS[
            _LAZY_JS.index("function miCartsWorkspaceKey")
            : _LAZY_JS.index("function updateMiCartsV1QueueSelection")
        ]
        self.assertNotIn("merchant_dashboard_refresh_token", block)
        self.assertIn("affected_carts", block)

    def test_skips_rerender_when_workspace_unchanged(self) -> None:
        block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertIn("wsKey === lastMiCartsWorkspaceKey", block)
        self.assertIn("updateMiCartsV1QueueSelection", block)

    def test_arabic_reason_tag_mappings(self) -> None:
        for token, ar in (
            ("price", "تردد بسبب السعر"),
            ("shipping", "تردد بسبب الشحن"),
            ("other", "أسباب أخرى"),
            ("waiting_first_send", "بانتظار إرسال الرسالة الأولى"),
        ):
            self.assertIn(f'{token}: "{ar}"', _MI_CARTS_JS)

    def test_decision_card_questions_present(self) -> None:
        for label in (
            "ماذا يحدث؟",
            "لماذا يهم؟",
            "ماذا فعل CartFlow؟",
            "هل يلزم إجراء؟",
        ):
            self.assertIn(label, _MI_CARTS_JS)

    def test_no_internal_tokens_in_merchant_html_templates(self) -> None:
        html_blocks = re.findall(r"'<[^']*>'", _MI_CARTS_JS)
        joined = "\n".join(html_blocks)
        for token in _INTERNAL_UI_TOKENS:
            self.assertNotIn(token, joined, msg=f"internal token leaked: {token}")

    def test_mi_queue_items_use_merchant_facing_scan(self) -> None:
        self.assertIn("function miCartQueueItemHtml", _MI_CARTS_JS)
        self.assertIn("merchantFacingText", _MI_CARTS_JS)
        idx_fn = _MI_CARTS_JS.index("function miCartQueueItemHtml")
        fn_block = _MI_CARTS_JS[idx_fn : idx_fn + 600]
        self.assertIn("merchantFacingText", fn_block)

    def test_no_local_grouping_in_lazy_mi_block(self) -> None:
        block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertNotIn("merchant_cart_primary_bucket", block)
        self.assertNotIn("deriveRecommendation", block)

    def test_decision_row_css_present(self) -> None:
        for cls in (
            ".ma-mi-decision-row",
            ".ma-mi-decision-row--action",
            ".ma-mi-group-section--rec",
        ):
            self.assertIn(cls, _POLISH_CSS, msg=f"missing {cls}")

    def test_update_group_selection_exported(self) -> None:
        self.assertIn("updateGroupSelection", _MI_CARTS_JS)
        self.assertIn("updateGroupSelection: updateGroupSelection", _MI_CARTS_JS)


if __name__ == "__main__":
    unittest.main()
