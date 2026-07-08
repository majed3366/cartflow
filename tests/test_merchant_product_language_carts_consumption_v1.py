# -*- coding: utf-8
"""Merchant Product Language Consumption V1 — Carts page certification."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.merchant_insight_layer_v1 import compose_page_insight_v1
from services.merchant_product_language_v1 import (
    build_carts_page_evidence_v1,
    compose_carts_narrative_from_payload_v1,
    has_carts_sufficient_evidence_v1,
    render_product_language_from_insight_v1,
    validate_product_language_from_insight_v1,
)

_ROOT = Path(__file__).resolve().parent.parent
_MIL_JS = (_ROOT / "static" / "merchant_insight_layer_v1.js").read_text(encoding="utf-8")
_MPL_JS = (_ROOT / "static" / "merchant_product_language_v1.js").read_text(encoding="utf-8")
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_TEMPLATE = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")

_FORBIDDEN = re.compile(
    r"\b(lifecycle_state|group_key|reason_tag|snapshot|bucket|decision_key)\b",
    re.I,
)
_FALLBACK = "CartFlow يتابع السلال المتاحة، وستظهر الخلاصة عندما تتوفر بيانات كافية."


def _payload_with_stories(*, attention: int = 2, monitored: int = 5) -> dict:
    return {
        "merchant_cart_filter_counts": {"all": monitored, "sent": 1},
        "merchant_value_stories_v1": {
            "version": "v1",
            "stories": [
                {
                    "story_id": "s1",
                    "action_required": True,
                    "affected_carts": attention,
                }
            ],
        },
    }


class MerchantProductLanguageCartsConsumptionV1Tests(unittest.TestCase):
    def test_dashboard_loads_insight_and_product_language_scripts(self) -> None:
        html = TestClient(app).get("/dashboard").text
        self.assertIn("merchant_insight_layer_v1.js", html)
        self.assertIn("merchant_product_language_v1.js", html)
        insight_idx = html.index("merchant_insight_layer_v1.js")
        mpl_idx = html.index("merchant_product_language_v1.js")
        self.assertLess(insight_idx, mpl_idx)

    def test_template_has_narrative_host_before_groups(self) -> None:
        host_idx = _TEMPLATE.index('id="ma-carts-product-language-v1"')
        groups_idx = _TEMPLATE.index('id="ma-carts-groups-v2"')
        self.assertLess(host_idx, groups_idx)

    def test_js_exposes_mil_mpl_pipeline(self) -> None:
        for token in (
            "composePageInsightV1",
            "renderProductLanguageFromInsightV1",
            "buildCartsEvidenceFromPayload",
            "hasCartsSufficientEvidence",
            "renderPageNarrativeHtml",
            "renderCartsNarrativeFallbackHtml",
        ):
            self.assertIn(token, _MPL_JS if token != "composePageInsightV1" else _MIL_JS)
        self.assertIn(_FALLBACK, _MPL_JS)

    def test_lazy_wires_insight_before_mpl_render(self) -> None:
        narrative_block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsProductLanguageNarrative")
            : _LAZY_JS.index("function miCartsWorkspaceKey")
        ]
        self.assertIn("composePageInsightV1", narrative_block)
        self.assertIn("renderProductLanguageFromInsightV1", narrative_block)

        workspace_block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertIn("renderMiCartsProductLanguageNarrative", workspace_block)
        self.assertIn("mi.renderStories", workspace_block)
        narrative_idx = workspace_block.index("renderMiCartsProductLanguageNarrative")
        stories_idx = workspace_block.index("mi.renderStories")
        self.assertLess(narrative_idx, stories_idx)

    def test_mpl_consumes_mil_output_insight_first(self) -> None:
        payload = _payload_with_stories(attention=4, monitored=4)
        rows = [{"recovery_key": f"rk{i}"} for i in range(4)]
        evidence = build_carts_page_evidence_v1(payload, rows)
        insight = compose_page_insight_v1("carts", evidence)
        narrative = render_product_language_from_insight_v1("carts", insight)

        headline = narrative["sections"]["headline"]["text_ar"]
        self.assertIn("كل السلال", headline)
        self.assertNotRegex(headline, r"^\d+\s")
        self.assertIn("لأن", narrative["sections"]["reason"]["text_ar"])
        self.assertIn("CartFlow", narrative["sections"]["cartflow_action"]["text_ar"])
        evidence_text = " ".join(narrative["sections"]["evidence"]["lines_ar"])
        self.assertIn("الأدلة:", evidence_text)
        self.assertIn("4", evidence_text)
        self.assertNotIn("تحتاج انتباهك", evidence_text)
        self.assertEqual(validate_product_language_from_insight_v1(narrative), [])
        self.assertTrue(narrative["observability"]["renders_from_insight"])

    def test_partial_attention_meaning_not_count_headline(self) -> None:
        payload = _payload_with_stories(attention=2, monitored=5)
        rows = [{"recovery_key": f"rk{i}"} for i in range(5)]
        narrative = compose_carts_narrative_from_payload_v1(payload, rows)
        headline = narrative["sections"]["headline"]["text_ar"]
        self.assertIn("بعض السلال", headline)
        self.assertNotIn("سلتان تستحقان", headline)
        self.assertEqual(validate_product_language_from_insight_v1(narrative), [])

    def test_counts_only_in_evidence_section(self) -> None:
        payload = _payload_with_stories(attention=2, monitored=5)
        rows = [{"recovery_key": f"rk{i}"} for i in range(5)]
        narrative = compose_carts_narrative_from_payload_v1(payload, rows)
        headline = narrative["sections"]["headline"]["text_ar"]
        reason = narrative["sections"]["reason"]["text_ar"]
        self.assertNotIn("5", headline)
        evidence_text = " ".join(narrative["sections"]["evidence"]["lines_ar"])
        self.assertIn("5", evidence_text)
        self.assertIn("2", reason)

    def test_fallback_when_evidence_missing(self) -> None:
        self.assertFalse(has_carts_sufficient_evidence_v1({}, []))
        self.assertIn(_FALLBACK, _MPL_JS)

    def test_no_forbidden_tokens_in_mpl_and_mil_js(self) -> None:
        self.assertIsNone(_FORBIDDEN.search(_MPL_JS))
        self.assertIsNone(_FORBIDDEN.search(_MIL_JS))

    def test_mi_mvc_logic_unchanged(self) -> None:
        self.assertIn("renderStories", _MI_CARTS_JS)
        self.assertIn("renderGroups", _MI_CARTS_JS)
        self.assertNotIn("renderProductLanguageFromInsightV1", _MI_CARTS_JS)
        self.assertNotIn("merchant_product_language", _MI_CARTS_JS)

    def test_evidence_from_needs_merchant_group(self) -> None:
        payload = {
            "merchant_intelligence_store_v1": {
                "groups": [{"group_id": "needs_merchant", "affected_carts": 1}],
            },
            "merchant_cart_filter_counts": {"all": 3},
        }
        rows = [{}, {}, {}]
        narrative = compose_carts_narrative_from_payload_v1(payload, rows)
        self.assertIn("سلة واحدة تحتاج", narrative["sections"]["headline"]["text_ar"])


if __name__ == "__main__":
    unittest.main()
