# -*- coding: utf-8 -*-
"""Executive Home Implementation V1 — Sprint 1 (E1 Business Health)."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.merchant_home_composition_v1 import (
    _compose_business_health_v1,
    compose_merchant_home_experience_v1,
)

_REPO = Path(__file__).resolve().parents[1]
_JS = _REPO / "static" / "merchant_dashboard_home_v1.js"


class TestExecutiveHomeE1V1(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_composer_emits_e1_disclosure_not_counter_evidence(self) -> None:
        health = _compose_business_health_v1(
            nav={"canonical_no_phone_total": 12, "knowledge_cart_count": 40},
            attention_count=1,
            has_primary_risk=True,
            understanding_confidence="high",
        )
        self.assertEqual(health["executive_band"], "E1")
        self.assertEqual(health["executive_question_id"], "EQ-01")
        self.assertEqual(health["section_question_ar"], "هل عملي بصحة جيدة اليوم؟")
        self.assertEqual(health.get("evidence_summary_ar") or "", "")
        disc = health["disclosure"]
        self.assertIn("كيف وصلنا", disc["label_ar"])
        self.assertTrue(disc.get("trend_ar"))
        self.assertTrue(disc.get("evidence_ar"))
        self.assertNotIn("سلة", disc["evidence_ar"])
        self.assertNotRegex(disc["evidence_ar"], r"\d+")

    def test_stable_path_uses_healthy_status(self) -> None:
        health = _compose_business_health_v1(
            nav={"canonical_no_phone_total": 0, "knowledge_cart_count": 3},
            attention_count=0,
            has_primary_risk=False,
            understanding_confidence="medium",
        )
        self.assertIn("جيدة", health["status_ar"])
        self.assertFalse(health["attention_required"])

    def test_home_composition_keeps_e1_after_intel(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر اختبار",
            date_ar="الأحد",
            brief_date="2026-07-19",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": 20,
                "waiting_send": 2,
                "canonical_no_phone_total": 8,
                "knowledge_cart_count": 20,
            },
            store_slug="e1-demo",
        )
        health = home["business_health"]
        self.assertEqual(health.get("executive_band"), "E1")
        self.assertEqual(health.get("evidence_summary_ar") or "", "")
        self.assertTrue((health.get("disclosure") or {}).get("evidence_ar"))

    def test_js_paints_e1_disclosure_shell(self) -> None:
        js = _JS.read_text(encoding="utf-8")
        self.assertIn('data-executive-band="E1"', js)
        self.assertIn("ma-ecc-e1-disclosure", js)
        self.assertIn("هل عملي بصحة جيدة اليوم؟", js)
        # Trend/evidence not forced open on L0
        self.assertIn("disclosure.trend_ar", js)
        self.assertIn("disclosure.evidence_ar", js)


if __name__ == "__main__":
    unittest.main()
