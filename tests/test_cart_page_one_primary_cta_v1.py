# -*- coding: utf-8 -*-
"""Cart Page V2 Phase 1 — one-primary CTA rendering contract (JS source)."""
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


class CartPageOnePrimaryCtaV1Tests(unittest.TestCase):
    def test_resolve_reads_projection_and_fails_safe_to_review(self) -> None:
        block = _extract_js_function(_LAZY_JS, "resolveCartPagePrimaryAction")
        self.assertIn("cart_page_primary_action_v1", block)
        self.assertIn('key = "review_cart"', block)
        self.assertNotIn('key = "archive"', block)
        self.assertIn("isArchivedVisual(mc)", block)
        self.assertIn('key = "reopen"', block)

    def test_primary_html_uses_projection_key_markers(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2PrimaryActionHtml")
        self.assertIn("resolveCartPagePrimaryAction", block)
        self.assertIn('data-cf-primary-action="contact_customer"', block)
        self.assertIn('data-cf-primary-action="follow_up_manually"', block)
        self.assertIn('data-cf-primary-action="reopen"', block)
        self.assertIn("data-cf-primary-action=", block)
        # Archive may exist as primary branch only for explicit projection; never fail-safe.
        self.assertIn('key === "archive"', block)

    def test_secondary_demotes_archive_only(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2SecondaryActionsHtml")
        self.assertIn("resolveCartPagePrimaryAction", block)
        self.assertIn("secondary_demoted", block)
        self.assertIn('data-cf-lifecycle-secondary="archive"', block)
        self.assertIn("إغلاق الحالة", block)
        self.assertNotIn("data-lc-reopen", block)
        self.assertIn('pa.key !== "archive"', block)
        self.assertIn('pa.key !== "reopen"', block)

    def test_footer_order_primary_then_secondary(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantPeV2ConversationFooterHtml")
        idx_primary = block.index("merchantPeV2PrimaryActionHtml")
        idx_secondary = block.index("merchantPeV2SecondaryActionsHtml")
        self.assertLess(idx_primary, idx_secondary)

    def test_archived_compact_shows_reopen_as_primary(self) -> None:
        block = _extract_js_function(_LAZY_JS, "customerLifecycleArchivedCompactHtml")
        self.assertIn("merchantPeV2PrimaryActionHtml", block)
        idx_primary = block.index("merchantPeV2PrimaryActionHtml")
        idx_secondary = block.index("merchantPeV2SecondaryActionsHtml")
        self.assertLess(idx_primary, idx_secondary)

    def test_completed_table_lifecycle_uses_projection(self) -> None:
        block = _extract_js_function(_LAZY_JS, "merchantCartSecondaryLifecycleHtml")
        self.assertIn("resolveCartPagePrimaryAction", block)
        self.assertIn('data-cf-primary-action="reopen"', block)
        self.assertIn('data-cf-lifecycle-secondary="archive"', block)
        self.assertIn("ma-cart-action-primary", block)

    def test_legacy_lifecycle_btn_uses_one_primary_helpers(self) -> None:
        block = _extract_js_function(_LAZY_JS, "cartLifecycleActionBtnHtml")
        self.assertIn("merchantPeV2PrimaryActionHtml", block)
        self.assertIn("merchantPeV2SecondaryActionsHtml", block)
        self.assertNotIn("cf-lc-btn-archive", block)

    def test_css_demotes_lifecycle_control(self) -> None:
        self.assertIn(".v2-btn--lifecycle", _CSS)


if __name__ == "__main__":
    unittest.main()
