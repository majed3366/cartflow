# -*- coding: utf-8 -*-
"""Knowledge Layer Migration v1 — routing consumer certification tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from services.knowledge_layer_projection_v1 import (
    MAX_KL_DISPLAY_ITEMS,
    comparison_period_label,
    enrich_knowledge_report_kl_routing_and_projection_v1,
    project_kl_oia_v1,
)
from services.knowledge_producer_metadata_v1 import enrich_knowledge_report_producer_metadata_v1
from services.knowledge_routing_v1 import (
    SURFACE_KNOWLEDGE_LAYER,
    route_knowledge_layer_knowledge_v1,
)

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_knowledge_layer.js").read_text(encoding="utf-8")


def _sample_insight(**overrides: object) -> dict:
    base = {
        "insight_key": "hesitation_top_reason",
        "category": "hesitation",
        "severity": "info",
        "title_ar": "سبب التردد الأبرز",
        "message_ar": "السبب الأكثر تسجيلاً هو «price» (42 من 75 — 56.0%).",
        "evidence": {
            "top_reason": "price",
            "top_count": 42,
            "hesitation_total": 75,
            "distribution": {"price": 42, "shipping": 20, "other": 13},
        },
        "confidence": "medium",
        "data_window": {"days": 7},
        "sample_size": 75,
        "source_tables": ["cart_recovery_reasons"],
        "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        "evidence_id": "hesitation_reason",
        "evidence_label_ar": "سبب التردد",
    }
    base.update(overrides)
    return base


class KnowledgeLayerMigrationV1Tests(unittest.TestCase):
    def test_js_has_no_local_selection_ownership(self) -> None:
        forbidden = (
            "INSIGHT_PRIORITY",
            "pickTopInsights",
            "insightScore",
            "OIA_BUILDERS",
            "buildHesitationTopReasonOIA",
            "buildKnowledgeCardOIA",
        )
        for token in forbidden:
            self.assertNotIn(token, _JS, msg=f"JS still owns knowledge: {token}")

    def test_js_consumes_projection_feed(self) -> None:
        self.assertIn("knowledge_layer_projection_v1", _JS)
        self.assertIn("display_cards", _JS)
        self.assertIn("/api/knowledge/report", _JS)

    def test_route_knowledge_layer_surface(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo-store",
            "window_days": 7,
            "insights": [
                _sample_insight(),
                _sample_insight(
                    insight_key="recovery_activity_summary",
                    category="recovery",
                    title_ar="ملخص نشاط الاسترجاع",
                    message_ar="رسائل مُرسَلة: 10",
                    evidence={"messages_sent": 10, "replies": 3, "purchase_count": 2, "returns": 1},
                    confidence="medium",
                ),
                _sample_insight(
                    insight_key="traffic_visitor_unavailable",
                    category="traffic",
                    title_ar="بيانات الزوار غير متوفرة",
                    message_ar="CartFlow لا يرى عدد زوار المتجر حالياً.",
                    evidence={"visitor_data_available": False},
                    confidence="insufficient",
                ),
            ],
        }
        enrich_knowledge_report_producer_metadata_v1(payload)
        routed = route_knowledge_layer_knowledge_v1(kl_insights=payload["insights"])
        self.assertEqual(routed["surface"], SURFACE_KNOWLEDGE_LAYER)
        self.assertGreaterEqual(routed["observability"]["eligible_items"], 2)

    def test_projection_excludes_insufficient_and_caps_display(self) -> None:
        insights = [
            _sample_insight(
                insight_key=f"insight_{i}",
                title_ar=f"عنوان {i}",
                confidence="medium" if i < 7 else "insufficient",
            )
            for i in range(8)
        ]
        payload = {"ok": True, "store_slug": "demo", "window_days": 7, "insights": insights}
        enrich_knowledge_report_producer_metadata_v1(payload)
        enrich_knowledge_report_kl_routing_and_projection_v1(payload)
        projection = payload["knowledge_layer_projection_v1"]
        self.assertLessEqual(len(projection["display_cards"]), MAX_KL_DISPLAY_ITEMS)
        for card in projection["display_cards"]:
            self.assertNotEqual(card["confidence"], "insufficient")
            self.assertTrue(card.get("source_knowledge_id"))

    def test_projection_oia_fields_present(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo",
            "window_days": 7,
            "insights": [_sample_insight()],
        }
        enrich_knowledge_report_producer_metadata_v1(payload)
        enrich_knowledge_report_kl_routing_and_projection_v1(payload)
        card = payload["knowledge_layer_projection_v1"]["display_cards"][0]
        self.assertTrue(card["title_ar"])
        self.assertTrue(card["observation_ar"])
        self.assertTrue(card["impact_ar"])
        self.assertTrue(card["action_ar"])
        self.assertIn("routing_knowledge_id", card)

    def test_identical_input_identical_projection(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo",
            "window_days": 7,
            "insights": [
                _sample_insight(),
                _sample_insight(
                    insight_key="recovery_activity_summary",
                    category="recovery",
                    confidence="medium",
                    evidence={"messages_sent": 1, "replies": 0, "purchase_count": 0, "returns": 0},
                ),
            ],
        }
        enrich_knowledge_report_producer_metadata_v1(payload)
        a = json.loads(json.dumps(payload, ensure_ascii=False))
        b = json.loads(json.dumps(payload, ensure_ascii=False))
        enrich_knowledge_report_kl_routing_and_projection_v1(a)
        enrich_knowledge_report_kl_routing_and_projection_v1(b)
        self.assertEqual(
            [c["source_knowledge_id"] for c in a["knowledge_layer_projection_v1"]["display_cards"]],
            [c["source_knowledge_id"] for c in b["knowledge_layer_projection_v1"]["display_cards"]],
        )

    def test_hesitation_oia_projection_localizes_price(self) -> None:
        oia = project_kl_oia_v1(_sample_insight(), window_days=7)
        self.assertIn("السعر", oia["observation_ar"])
        self.assertIn("راجع التسعير", oia["action_ar"])

    def test_comparison_period_label(self) -> None:
        self.assertEqual(comparison_period_label(7), "مقارنة بالأسبوع السابق")
        self.assertEqual(comparison_period_label(30), "مقارنة بآخر 30 يوماً")

    def test_api_payload_includes_routing_and_projection_blocks(self) -> None:
        payload = {"ok": True, "store_slug": "demo", "window_days": 7, "insights": [_sample_insight()]}
        enrich_knowledge_report_producer_metadata_v1(payload)
        enrich_knowledge_report_kl_routing_and_projection_v1(payload)
        self.assertIn("knowledge_routing_v1", payload)
        self.assertIn("knowledge_layer_projection_v1", payload)
        self.assertEqual(payload["knowledge_routing_v1"]["surface"], SURFACE_KNOWLEDGE_LAYER)

    def test_empty_actionable_insights_yields_empty_reason(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo",
            "window_days": 7,
            "insights": [_sample_insight(confidence="insufficient")],
        }
        enrich_knowledge_report_producer_metadata_v1(payload)
        enrich_knowledge_report_kl_routing_and_projection_v1(payload)
        projection = payload["knowledge_layer_projection_v1"]
        self.assertEqual(projection["display_cards"], [])
        self.assertEqual(projection["empty_reason"], "insufficient_actionable_knowledge")


if __name__ == "__main__":
    unittest.main()
