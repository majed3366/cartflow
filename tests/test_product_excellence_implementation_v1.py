# -*- coding: utf-8 -*-
"""Product Excellence Implementation V1 — production presentation contract."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_HOME_JS = (_ROOT / "static" / "merchant_home_experience.js").read_text(encoding="utf-8")
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_pe_v2.css").read_text(encoding="utf-8")
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class ProductExcellenceImplementationV1Tests(unittest.TestCase):
    def test_dashboard_shell_has_pe_v2_assets(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_pe_v2.css", html)
        self.assertIn('id="page-home"', html)
        self.assertIn("ma-pe-v2", html)
        self.assertIn('id="ma-carts-queue-v2"', html)
        self.assertIn('id="ma-carts-panel-v2"', html)
        self.assertIn('id="ma-tbody-all-carts"', html)

    def test_home_js_emits_v2_hero_not_legacy_blocks(self) -> None:
        self.assertIn("v2-hero", _HOME_JS)
        self.assertIn("v2-action-card", _HOME_JS)
        self.assertIn("maApplyHomeExperience", _HOME_JS)
        self.assertNotIn("ma-home-block--achievements", _HOME_JS)
        self.assertNotIn("ma-home-block--attention", _HOME_JS)

    def test_carts_lazy_js_queue_and_conversation_contract(self) -> None:
        self.assertIn("function cartQueueItemHtml", _LAZY_JS)
        self.assertIn("function merchantPeV2FlowHtml", _LAZY_JS)
        self.assertIn("function renderPeV2CartsQueue", _LAZY_JS)
        self.assertIn('data-mxp="carts-pe-v2"', _LAZY_JS)
        self.assertIn("v2-queue-item", _LAZY_JS)
        self.assertIn("v2-flow-step", _LAZY_JS)
        self.assertIn("ma-pe-v2-timeline-v2", _LAZY_JS)

    def test_flow_beat_order_in_pe_v2_html(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2FlowHtml")
        idx_what = block.index("ما حدث")
        idx_did = block.index("CartFlow")
        idx_next = block.index("action_required")
        idx_you = block.index("إجراءك")
        self.assertLess(idx_what, idx_did)
        self.assertLess(idx_did, idx_next)
        self.assertLess(idx_next, idx_you)

    def test_cart_row_sync_for_filter_without_inline_workspace(self) -> None:
        sync = _extract_js_function(_LAZY_JS, "cartRowSyncTr")
        self.assertIn("data-ma-filter", sync)
        self.assertNotIn("merchantCartWorkspaceHtml", sync)

    def test_workspace_composition_delegates_to_pe_v2(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartWorkspaceFromParts")
        self.assertIn("merchantPeV2ConversationHtml", block)

    def test_pe_v2_css_present_in_static(self) -> None:
        for cls in (
            ".v2-hero",
            ".v2-queue-item",
            ".v2-flow-step",
            "#page-carts.ma-pe-v2",
        ):
            self.assertIn(cls, _CSS, msg=f"missing {cls}")

    def test_template_carts_page_uses_workspace_not_visible_table(self) -> None:
        self.assertIn("ma-pe-v2-carts-shell", _TEMPLATE)
        self.assertIn("v2-workspace", _TEMPLATE)
        self.assertNotIn("<th>قيمة السلة</th>", _TEMPLATE.split("page-carts")[1].split("page-followup")[0])


if __name__ == "__main__":
    unittest.main()
