# -*- coding: utf-8 -*-
"""Knowledge Layer v1 — merchant dashboard placement tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_knowledge_layer.js").read_text(encoding="utf-8")
_HTML = (_ROOT / "templates" / "merchant_app.html").read_text(encoding="utf-8")

SAMPLE_INSIGHTS_PAYLOAD = {
    "ok": True,
    "store_slug": "demo-store",
    "window_days": 7,
    "generated_at": "2026-06-07T12:00:00+00:00",
    "insights": [
        {
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
        },
        {
            "insight_key": "recovery_activity_summary",
            "category": "recovery",
            "severity": "info",
            "title_ar": "ملخص نشاط الاسترجاع",
            "message_ar": "رسائل مُرسَلة: 10؛ ردود: 3؛ مشتريات: 2.",
            "evidence": {
                "messages_sent": 10,
                "replies": 3,
                "purchases": 2,
                "returns": 1,
            },
            "confidence": "medium",
            "data_window": {"days": 7},
            "sample_size": 10,
            "source_tables": ["cart_recovery_logs"],
            "recommended_action_ar": "راقب هذا المؤشر خلال الأيام القادمة.",
        },
        {
            "insight_key": "traffic_visitor_unavailable",
            "category": "traffic",
            "severity": "notice",
            "title_ar": "بيانات الزوار غير متوفرة",
            "message_ar": "CartFlow لا يرى عدد زوار المتجر حالياً.",
            "evidence": {"visitor_data_available": False},
            "confidence": "insufficient",
            "data_window": {"days": 7},
            "sample_size": 0,
            "source_tables": ["abandoned_carts"],
            "recommended_action_ar": "قد تحتاج إلى مراجعة إعدادات التتبع.",
        },
    ],
    "metrics_snapshot": {},
}


class MerchantKnowledgeDashboardV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        import os

        os.environ["ENV"] = "development"
        os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-for-knowledge-dashboard")
        self.client = TestClient(app)

    def test_dashboard_contains_home_experience_composition(self) -> None:
        r = self.client.get("/dashboard")
        self.assertEqual(r.status_code, 200)
        html = r.text or ""
        self.assertIn('id="ma-home-experience-root"', html)
        self.assertIn("ma-home-experience", html)
        self.assertIn("merchant_home_experience.js", html)
        self.assertNotIn('id="ma-knowledge-root"', html)
        self.assertNotIn('id="ma-daily-brief-root"', html)

    def test_knowledge_js_consumes_api_only(self) -> None:
        self.assertIn("/api/knowledge/report", _JS)
        self.assertIn("knowledge_layer_projection_v1", _JS)
        self.assertNotIn("build_knowledge_report", _JS)
        self.assertNotIn("knowledge_insights_v1", _JS)
        self.assertNotIn("INSIGHT_PRIORITY", _JS)
        self.assertNotIn("pickTopInsights", _JS)

    def test_knowledge_js_has_empty_state_copy(self) -> None:
        self.assertIn("لا توجد بيانات كافية حالياً", _JS)
        self.assertIn("استمر في جمع النشاط", _JS)

    def test_knowledge_js_projection_render_only(self) -> None:
        self.assertIn("display_cards", _JS)
        self.assertIn("renderDisplayCard", _JS)
        self.assertIn("OIA_LABEL_OBSERVATION", _JS)
        self.assertNotIn("buildHesitationTopReasonOIA", _JS)
        self.assertNotIn("buildKnowledgeCardOIA", _JS)
        self.assertNotIn("localizeReason", _JS)

    def test_knowledge_css_oia_blocks(self) -> None:
        css = (_ROOT / "static" / "merchant_app.css").read_text(encoding="utf-8")
        self.assertIn(".ma-knowledge-oia-stack", css)
        self.assertIn(".ma-knowledge-oia-label", css)

    def test_knowledge_js_forbidden_marketing_phrases_absent(self) -> None:
        for phrase in ("زد الإعلانات", "غيّر أسعارك", "ROI"):
            self.assertNotIn(phrase, _JS)

    def test_sample_payload_structure_for_ui(self) -> None:
        blob = json.dumps(SAMPLE_INSIGHTS_PAYLOAD, ensure_ascii=False)
        self.assertIn("hesitation_top_reason", blob)
        self.assertIn("recommended_action_ar", blob)
        actionable = [
            i
            for i in SAMPLE_INSIGHTS_PAYLOAD["insights"]
            if i.get("confidence") != "insufficient"
        ]
        self.assertGreaterEqual(len(actionable), 2)

    def test_knowledge_css_uses_card_grid(self) -> None:
        css = (_ROOT / "static" / "merchant_app.css").read_text(encoding="utf-8")
        self.assertIn(".ma-knowledge-cards", css)
        self.assertIn("grid-template-columns: repeat(2", css)
        self.assertIn("ma-knowledge-oia-stack", _JS)

    def test_main_py_unchanged_for_knowledge_logic(self) -> None:
        main_src = (_ROOT / "main.py").read_text(encoding="utf-8")
        self.assertNotIn("build_knowledge_report", main_src)
        self.assertNotIn("knowledge_insights_v1", main_src)


if __name__ == "__main__":
    unittest.main()
