# -*- coding: utf-8 -*-
"""Merchant Findings Review Lab V1 — Product acceptance surface."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.business_findings_review_lab_v1 import (
    build_review_lab_payload_v1,
    confidence_badge_ar,
    finding_to_review_card_v1,
)

_REPO = Path(__file__).resolve().parents[1]


class TestBusinessFindingsReviewLabV1(unittest.TestCase):
    def test_payload_has_merchant_cards_only(self) -> None:
        payload = build_review_lab_payload_v1(store_slug="demo", source="fixture")
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["card_count"], 5)
        self.assertEqual(len(payload["cards"]), payload["card_count"])
        for card in payload["cards"]:
            self.assertTrue(card["title"])
            self.assertTrue(card["why_it_matters"])
            self.assertTrue(card["next_step"])
            self.assertTrue(card["confidence_ar"])
            self.assertTrue(card["evidence_lines"])
            blob = " ".join(
                [
                    card["title"],
                    card.get("summary") or "",
                    card["why_it_matters"],
                    card["next_step"],
                    " ".join(card["evidence_lines"]),
                ]
            )
            for banned in (
                "BusinessFindingV1",
                "finding_family",
                "Evidence Bundle",
                "Knowledge Routing",
                "confidence_score",
                "source_version",
                "finding_version",
                "Observation",
                "Commercial Pattern",
            ):
                self.assertNotIn(banned, blob)

    def test_confidence_badge_arabic(self) -> None:
        self.assertEqual(confidence_badge_ar("high"), "مرتفعة")
        self.assertEqual(confidence_badge_ar("medium"), "متوسطة")
        self.assertEqual(confidence_badge_ar("insufficient"), "غير كافية بعد")

    def test_card_mapping_hides_internal_ids_from_display_fields(self) -> None:
        card = finding_to_review_card_v1(
            {
                "finding_id": "finding:demo",
                "title": "عنوان تجريبي",
                "merchant_summary": "خلاصة",
                "commercial_meaning": "معنى",
                "recommended_direction": "خطوة",
                "confidence_level": "high",
                "evidence_summary": "add_to_cart=10 purchases=1",
                "sample_size": 10,
                "finding_type": "high_interest_low_purchase_product_v1",
                "family_key": "product_conversion",
            },
            index=1,
        )
        self.assertEqual(card["title"], "عنوان تجريبي")
        self.assertEqual(card["confidence_ar"], "مرتفعة")
        self.assertIn("مرات الإضافة إلى السلة=", " ".join(card["evidence_lines"]))
        self.assertNotIn("finding_type", card)
        self.assertNotIn("family_key", card)

    def test_template_has_review_questions_and_no_json_dump(self) -> None:
        html = (
            _REPO / "templates" / "business_findings_review_lab_v1.html"
        ).read_text(encoding="utf-8")
        self.assertIn("هل هذه النتيجة مفيدة؟", html)
        self.assertIn("هل هذه معلومة جديدة؟", html)
        self.assertIn("هل سيتصرّف التاجر بسببها؟", html)
        self.assertIn("هل تزيد ولاء التاجر", html)
        self.assertIn("التصنيف", html)
        self.assertIn("Wow", html)
        self.assertIn("عرض الأدلة الداعمة", html)
        self.assertNotIn("BusinessFindingV1", html)
        self.assertNotIn("finding_family", html)
        # Must not dump engine packages / contracts into the page.
        self.assertNotIn("evidence_refs", html)
        self.assertNotIn("finding_version", html)
        self.assertNotIn("source_version", html)
        self.assertNotIn("<pre>", html)

    def test_route_registered_in_main(self) -> None:
        main_py = (_REPO / "main.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn('/dev/business-findings-review', main_py)
        self.assertIn("dev_business_findings_review", main_py)
        self.assertIn("business_findings_review_lab_v1.html", main_py)


if __name__ == "__main__":
    unittest.main()
