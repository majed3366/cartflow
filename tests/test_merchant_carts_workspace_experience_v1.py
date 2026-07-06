# -*- coding: utf-8 -*-
"""Carts Workspace Experience V1 — MXP pattern presentation certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_CSS = (_ROOT / "static" / "merchant_app.css").read_text(encoding="utf-8")


def _extract_js_function(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    next_fn = re.search(r"\n  function \w+\(", source[start + 1 :])
    end = start + 1 + next_fn.start() if next_fn else len(source)
    return source[start:end]


class MerchantCartsWorkspaceExperienceV1Tests(unittest.TestCase):
    def test_workspace_root_and_pattern_markers(self) -> None:
        self.assertIn("function merchantCartWorkspaceFromParts", _LAZY_JS)
        self.assertIn('data-mxp="carts-v1"', _LAZY_JS)
        self.assertIn("ma-cart-workspace-v1", _LAZY_JS)
        self.assertIn("ma-cart-recovery-story-v1", _LAZY_JS)
        self.assertIn("ma-cart-suggested-action-v1", _LAZY_JS)
        self.assertIn("ma-cart-timeline-v1", _LAZY_JS)

    def test_recovery_story_fixed_beat_order(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantRecoveryStoryBeatsHtml")
        idx_what = block.index("ma-cart-story-beat--what")
        idx_did = block.index("ma-cart-story-beat--did")
        idx_next = block.index("ma-cart-story-beat--next")
        idx_action = block.index("ma-cart-story-beat--action")
        self.assertLess(idx_what, idx_did)
        self.assertLess(idx_did, idx_next)
        self.assertLess(idx_next, idx_action)

    def test_composition_order_story_action_timeline(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartWorkspaceFromParts")
        idx_story = block.index("merchantRecoveryStoryBeatsHtml")
        idx_action = block.index("merchantSuggestedActionPrimaryHtml")
        idx_timeline = block.index("merchantCartTimelineHtml")
        self.assertLess(idx_story, idx_action)
        self.assertLess(idx_action, idx_timeline)

    def test_suggested_action_primary_not_inline_label(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantSuggestedActionPrimaryHtml")
        self.assertIn("ma-cart-action-primary", block)
        self.assertNotIn("الإجراء المقترح:", block)

    def test_timeline_collapsed_by_default(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartTimelineHtml")
        self.assertIn("<details class=\"ma-cart-timeline-v1\">", block)
        self.assertIn("ma-cart-timeline-summary", block)

    def test_proof_surface_wired_into_timeline(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartTimelineHtml")
        self.assertIn("merchantProofSurfaceTimelineHtml", block)

    def test_waiting_band_when_no_action_required(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantRecoveryStoryBeatsHtml")
        self.assertIn("ma-cart-waiting-band", block)
        self.assertIn("!expl.action_required", block)

    def test_cart_row_full_uses_unified_workspace(self) -> None:
        fn = _LAZY_JS[
            _LAZY_JS.index("function cartRowFull")
            : _LAZY_JS.index("function normalCartsLoadingRowHtml")
        ]
        self.assertIn("merchantCartWorkspaceHtml(mc)", fn)
        self.assertNotIn("lifecycleTruthHtml(mc)", fn)
        self.assertNotIn("customerMovementHtml(mc)", fn)

    def test_legacy_explanation_uses_workspace(self) -> None:
        block = _extract_js_function(_LAZY_JS, "customerLifecycleExplanationLegacyHtml")
        self.assertIn("merchantCartWorkspaceFromParts", block)
        self.assertNotIn("ماذا حدث؟", block)

    def test_css_whisper_hierarchy_present(self) -> None:
        for cls in (
            ".ma-cart-workspace-v1",
            ".ma-cart-recovery-story-v1",
            ".ma-cart-waiting-band",
            ".ma-cart-action-primary",
            ".ma-cart-timeline-v1",
            ".ma-cart-achievement-v1",
        ):
            self.assertIn(cls, _CSS, msg=f"missing {cls}")


if __name__ == "__main__":
    unittest.main()
