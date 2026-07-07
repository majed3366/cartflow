# -*- coding: utf-8 -*-
"""Carts Workspace Experience — Product Excellence V2 presentation certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_pe_v2.css").read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class MerchantCartsWorkspaceExperienceV1Tests(unittest.TestCase):
    def test_workspace_root_and_pattern_markers(self) -> None:
        self.assertIn("function merchantCartWorkspaceFromParts", _LAZY_JS)
        self.assertIn('data-mxp="carts-pe-v2"', _LAZY_JS)
        self.assertIn("merchantPeV2ConversationHtml", _LAZY_JS)
        self.assertIn("merchantPeV2FlowHtml", _LAZY_JS)
        self.assertIn("ma-pe-v2-timeline-v2", _LAZY_JS)
        self.assertIn("cartQueueItemHtml", _LAZY_JS)

    def test_recovery_story_fixed_beat_order(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2FlowHtml")
        idx_what = block.index("ما حدث")
        idx_did = block.index("CartFlow")
        idx_next = block.index("action_required")
        idx_action = block.index("إجراءك")
        self.assertLess(idx_what, idx_did)
        self.assertLess(idx_did, idx_next)
        self.assertLess(idx_next, idx_action)

    def test_composition_order_flow_footer(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2ConversationHtml")
        idx_flow = block.index("merchantPeV2FlowHtml")
        idx_timeline = block.index("merchantPeV2TimelineHtml")
        idx_action = block.index("merchantPeV2PrimaryActionHtml")
        self.assertLess(idx_flow, idx_timeline)
        self.assertLess(idx_timeline, idx_action)

    def test_suggested_action_primary_not_inline_label(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2PrimaryActionHtml")
        self.assertIn("v2-btn", block)
        self.assertNotIn("الإجراء المقترح:", block)

    def test_timeline_collapsed_by_default(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2TimelineHtml")
        self.assertIn("<details class=\"ma-pe-v2-timeline-v2\">", block)
        self.assertIn("ma-cart-timeline-summary", block)

    def test_proof_surface_wired_into_timeline(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2TimelineHtml")
        self.assertIn("merchantProofSurfaceTimelineHtml", block)

    def test_waiting_label_when_no_action_required(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2FlowHtml")
        self.assertIn("الانتظار", block)
        self.assertIn("!expl.action_required", block)

    def test_cart_row_full_uses_sync_tr_when_queue_present(self) -> None:
        fn = _LAZY_JS[
            _LAZY_JS.index("function cartRowFull")
            : _LAZY_JS.index("function normalCartsLoadingRowHtml")
        ]
        self.assertIn("cartRowSyncTr", fn)
        self.assertIn("ma-carts-groups-v2", fn)

    def test_legacy_explanation_uses_workspace(self) -> None:
        block = _extract_js_function(_LAZY_JS, "customerLifecycleExplanationLegacyHtml")
        self.assertIn("merchantCartWorkspaceFromParts", block)
        self.assertNotIn("ماذا حدث؟", block)

    def test_css_v2_hierarchy_present(self) -> None:
        for cls in (
            ".v2-queue-item",
            ".v2-flow-step",
            ".v2-conversation",
            ".v2-hero",
            ".v2-action-card",
        ):
            self.assertIn(cls, _CSS, msg=f"missing {cls}")


if __name__ == "__main__":
    unittest.main()
