# -*- coding: utf-8 -*-
"""Business Reasoning Review Lab V1 — Product acceptance surface."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.business_reasoning_contract_v1 import (
    TYPE_PRIORITY,
    TYPE_RELATIONSHIP,
)
from services.business_reasoning_review_lab_v1 import (
    build_reasoning_review_lab_payload_v1,
    reasoning_to_review_card_v1,
    reasoning_type_label_ar,
)

_REPO = Path(__file__).resolve().parents[1]


class TestBusinessReasoningReviewLabV1(unittest.TestCase):
    def test_payload_has_merchant_cards_only(self) -> None:
        payload = build_reasoning_review_lab_payload_v1(
            store_slug="demo", source="fixture"
        )
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["card_count"], 5)
        self.assertEqual(len(payload["cards"]), payload["card_count"])
        for card in payload["cards"]:
            self.assertTrue(card["headline"])
            self.assertTrue(card["business_meaning"])
            self.assertTrue(card["merchant_priority"])
            self.assertTrue(card["expected_impact"])
            self.assertTrue(card["confidence_ar"])
            self.assertTrue(card["certainty_ar"])
            self.assertTrue(card["reasoning_type_ar"])
            self.assertGreaterEqual(len(card["supporting_findings"]), 2)
            blob = " ".join(
                [
                    card["headline"],
                    card["business_meaning"],
                    card["merchant_priority"],
                    card["expected_impact"],
                    card["reasoning_type_ar"],
                    " ".join(card["supporting_findings"]),
                ]
            )
            for banned in (
                "BusinessReasoning",
                "finding_relationship_v1",
                "priority_detection_v1",
                "Relationship Graph",
                "Rule Engine",
                "Finding Registry",
                "confidence_score",
                "reasoning_id",
                "supporting_finding_ids",
                "Evidence Bundle",
                "Knowledge Routing",
            ):
                self.assertNotIn(banned, blob)

    def test_reasoning_type_labels_are_merchant_arabic(self) -> None:
        self.assertEqual(
            reasoning_type_label_ar(TYPE_PRIORITY), "أولوية القرار"
        )
        self.assertEqual(
            reasoning_type_label_ar(TYPE_RELATIONSHIP), "ربط بين ملاحظات"
        )
        self.assertNotIn("v1", reasoning_type_label_ar(TYPE_PRIORITY))

    def test_card_mapping_hides_internal_fields(self) -> None:
        card = reasoning_to_review_card_v1(
            {
                "reasoning_id": "reasoning:demo",
                "headline": "عنوان تجريبي",
                "business_meaning": "معنى",
                "recommended_priority": "أولوية",
                "expected_impact": "أثر",
                "confidence_level": "high",
                "certainty": "observed",
                "reasoning_type": TYPE_RELATIONSHIP,
                "supporting_finding_ids": ["finding:a", "finding:b"],
                "supporting_finding_labels": ["نتيجة أ", "نتيجة ب"],
            },
            index=1,
        )
        self.assertEqual(card["headline"], "عنوان تجريبي")
        self.assertEqual(card["confidence_ar"], "مرتفعة")
        self.assertEqual(card["certainty_ar"], "ملاحظ")
        self.assertEqual(card["reasoning_type_ar"], "ربط بين ملاحظات")
        self.assertEqual(card["supporting_findings"], ["نتيجة أ", "نتيجة ب"])
        self.assertNotIn("supporting_finding_ids", card)
        self.assertNotIn("reasoning_type", card)
        self.assertNotIn("confidence_level", card)

    def test_template_has_review_questions_and_no_internals(self) -> None:
        html = (
            _REPO / "templates" / "business_reasoning_review_lab_v1.html"
        ).read_text(encoding="utf-8")
        self.assertIn("هل يخلق هذا الاستنتاج قراراً تجارياً حقيقياً؟", html)
        self.assertIn("هل هو أثمن من قراءة النتائج منفصلة؟", html)
        self.assertIn("هل يثق تاجر خبير بهذا الاستنتاج؟", html)
        self.assertIn("هل يوفّر وقت التفكير على التاجر؟", html)
        self.assertIn("التصنيف", html)
        self.assertIn("Wow", html)
        self.assertIn("عرض النتائج الداعمة", html)
        self.assertIn("المعنى التجاري", html)
        self.assertIn("أولوية التاجر", html)
        self.assertIn("الأثر المتوقع", html)
        self.assertNotIn("BusinessReasoning", html)
        self.assertNotIn("finding_relationship_v1", html)
        self.assertNotIn("Relationship Graph", html)
        self.assertNotIn("Rule Engine", html)
        self.assertNotIn("Finding Registry", html)
        self.assertNotIn("reasoning_id", html)
        self.assertNotIn("supporting_finding_ids", html)
        self.assertNotIn("confidence_score", html)
        self.assertNotIn("<pre>", html)

    def test_route_registered_in_main(self) -> None:
        main_py = (_REPO / "main.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("/dev/business-reasoning-review", main_py)
        self.assertIn("dev_business_reasoning_review", main_py)
        self.assertIn("business_reasoning_review_lab_v1.html", main_py)
        self.assertIn(
            '"/dev/business-reasoning-review"',
            main_py.replace("'", '"'),
        )

    def test_acceptance_thresholds(self) -> None:
        payload = build_reasoning_review_lab_payload_v1(
            store_slug="demo", source="fixture"
        )
        self.assertEqual(payload["acceptance"]["useful_or_wow_needed"], 5)
        self.assertEqual(payload["acceptance"]["wow_needed"], 3)


if __name__ == "__main__":
    unittest.main()
