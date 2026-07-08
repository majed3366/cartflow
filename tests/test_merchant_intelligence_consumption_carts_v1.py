# -*- coding: utf-8 -*-
"""Merchant Intelligence Consumption V1 — Carts workspace certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")
_POLISH_CSS = (_ROOT / "static" / "merchant_product_polish_v1.css").read_text(
    encoding="utf-8"
)
_SNAPSHOT = (
    _ROOT / "services" / "dashboard_snapshot_normal_carts_slim_v1.py"
).read_text(encoding="utf-8")


class MerchantIntelligenceConsumptionCartsV1Tests(unittest.TestCase):
    def test_dashboard_loads_mi_carts_script(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_intelligence_carts_v1.js", html)

    def test_template_mi_groups_root_not_raw_queue_first(self) -> None:
        self.assertIn('id="ma-carts-groups-v2"', _TEMPLATE)
        self.assertIn("ma-mi-carts-root", _TEMPLATE)
        self.assertNotIn('id="ma-carts-queue-v2"', _TEMPLATE)
        self.assertNotIn('data-ma-group="all"', _TEMPLATE)
        self.assertIn('id="ma-cart-filters"', _TEMPLATE)
        self.assertIn("hidden", _TEMPLATE.split("ma-cart-filters")[1][:80])

    def test_mi_carts_consumes_store_payload_only(self) -> None:
        self.assertIn("merchant_intelligence_store_v1", _MI_CARTS_JS)
        self.assertIn("merchant_intelligence_v1", _MI_CARTS_JS)
        self.assertIn("intelligence_group_key", _MI_CARTS_JS)
        self.assertNotIn("merchant_next_action_urgent", _MI_CARTS_JS)

    def test_queue_accent_reads_row_bucket_for_presentation_only(self) -> None:
        block = _MI_CARTS_JS[
            _MI_CARTS_JS.index("function queueAccentClass")
            : _MI_CARTS_JS.index("var REASON_TAG_AR")
        ]
        self.assertIn("merchant_cart_primary_bucket", block)
        self.assertNotIn("sortGroups", block)

    def test_no_local_recommendation_derivation_in_mi_carts_js(self) -> None:
        self.assertIn("recommendationForGroup", _MI_CARTS_JS)
        self.assertNotIn("CartFlow يقترح", _MI_CARTS_JS)
        self.assertNotIn("deriveRecommendation", _MI_CARTS_JS)
        self.assertNotIn("decision_class_to_recommendation", _MI_CARTS_JS)

    def test_no_local_grouping_by_bucket_in_lazy_wiring(self) -> None:
        block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertIn("maIntelligenceCartsV1", block)
        self.assertIn("merchant_intelligence_store_v1", block)
        self.assertNotIn("merchant_cart_primary_bucket", block)

    def test_group_priority_order_defined(self) -> None:
        self.assertIn('"needs_merchant"', _MI_CARTS_JS)
        idx_needs = _MI_CARTS_JS.index('"needs_merchant"')
        idx_completed = _MI_CARTS_JS.index('"completed"')
        self.assertLess(idx_needs, idx_completed)

    def test_representative_carts_collapsed_pattern(self) -> None:
        self.assertIn("ma-mi-group-more", _MI_CARTS_JS)
        self.assertIn("splitRepresentative", _MI_CARTS_JS)
        self.assertIn("أمثلة من السلال", _MI_CARTS_JS)
        self.assertIn("باقي السلال", _MI_CARTS_JS)

    def test_expanded_group_story_order(self) -> None:
        block = _MI_CARTS_JS[
            _MI_CARTS_JS.index("function groupExpandedHtml")
            : _MI_CARTS_JS.index("function miCartQueueItemHtml")
        ]
        idx_why = block.index("لماذا هذه المجموعة؟")
        idx_obs = block.index("ماذا لاحظ CartFlow؟")
        idx_did = block.index("ماذا فعل CartFlow؟")
        idx_rec = block.index("التوصية")
        idx_rep = block.index("أمثلة من السلال")
        self.assertLess(idx_why, idx_obs)
        self.assertLess(idx_obs, idx_did)
        self.assertLess(idx_did, idx_rec)
        self.assertLess(idx_rec, idx_rep)

    def test_meaning_first_empty_states(self) -> None:
        self.assertIn("لا توجد سلات تحتاج انتباهك", _MI_CARTS_JS)
        self.assertNotIn("No data", _MI_CARTS_JS)

    def test_css_mi_group_cards(self) -> None:
        for cls in (
            ".ma-mi-group",
            ".ma-mi-group-card",
            ".ma-mi-group-body",
            ".ma-carts--mi-v1",
        ):
            self.assertIn(cls, _POLISH_CSS, msg=f"missing {cls}")

    def test_expanded_story_card_hides_duplicate_summary_rows(self) -> None:
        """Expanded cards must unmount collapsed preview — not CSS-hide duplicate copy."""
        self.assertIn("data-mi-summary-preview", _MI_CARTS_JS)
        self.assertIn("syncMiGroupSummaryPreview", _MI_CARTS_JS)
        self.assertIn("summaryPreviewBlock", _MI_CARTS_JS)
        self.assertIn("isolation: isolate", _POLISH_CSS)

    def test_expand_animations_do_not_use_opacity(self) -> None:
        pds = (_ROOT / "static" / "merchant_pds_compliance_v1.css").read_text(encoding="utf-8")
        cfvi = (_ROOT / "static" / "merchant_visual_identity_v1.css").read_text(encoding="utf-8")
        pds_block = pds[pds.index("@keyframes pds-expand-in") : pds.index("@keyframes pds-expand-in") + 120]
        cfvi_block = cfvi[cfvi.index("@keyframes cfvi-expand") : cfvi.index("@keyframes cfvi-expand") + 120]
        self.assertNotIn("opacity", pds_block)
        self.assertNotIn("opacity", cfvi_block)

    def test_snapshot_allowlist_includes_mi_fields(self) -> None:
        self.assertIn('"merchant_intelligence_v1"', _SNAPSHOT)
        self.assertIn('"intelligence_group_key"', _SNAPSHOT)
        self.assertIn('"merchant_intelligence_store_v1"', _SNAPSHOT)
        self.assertIn('"merchant_value_stories_v1"', _SNAPSHOT)

    def test_carts_prefers_value_stories_payload(self) -> None:
        self.assertIn("merchant_value_stories_v1", _MI_CARTS_JS)
        self.assertIn("renderStories", _MI_CARTS_JS)
        block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertIn("hasValueStories", block)
        self.assertIn("renderStories", block)

    def test_lazy_delegates_to_mi_module(self) -> None:
        self.assertIn("renderMiCartsV1Workspace", _LAZY_JS)
        self.assertIn("renderMiCartsV1Workspace(d, sortedRows)", _LAZY_JS)

    def test_filter_bar_disabled_in_mi_mode(self) -> None:
        self.assertIn("ma-carts--mi-v1", _LAZY_JS)
        self.assertIn('filters.hidden = true', _LAZY_JS)

    def test_regression_carts_workspace_still_wired(self) -> None:
        self.assertIn("merchantPeV2ConversationHtml", _LAZY_JS)
        self.assertIn("renderPeV2CartPanel", _LAZY_JS)


if __name__ == "__main__":
    unittest.main()
