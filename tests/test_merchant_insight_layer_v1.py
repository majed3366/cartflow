# -*- coding: utf-8
"""Merchant Insight Layer V1 — foundation certification tests."""
from __future__ import annotations

import re
import unittest

from services.merchant_insight_layer_templates import (
    INSIGHT_MERCHANT_REQUIRED,
    INSIGHT_MONITORING_ONLY,
)
from services.merchant_insight_layer_v1 import (
    AUTHORITY,
    INSIGHT_VERSION,
    build_page_insight_evidence_v1,
    compose_page_insight_v1,
    validate_page_insight_v1,
)

_FORBIDDEN = re.compile(
    r"\b(lifecycle_state|group_key|reason_tag|bucket|revenue|probability|prediction)\b",
    re.I,
)


class MerchantInsightLayerV1Tests(unittest.TestCase):
    def test_carts_all_attention_meaning_first(self) -> None:
        evidence = {
            "monitored_count": 4,
            "attention_count": 4,
            "automatic_count": 0,
            "has_sufficient_evidence": True,
            "cartflow_action_key": "waiting_merchant",
        }
        insight = compose_page_insight_v1("carts", evidence)
        self.assertEqual(insight["insight_type"], INSIGHT_MERCHANT_REQUIRED)
        self.assertIn("كل السلال", insight["primary_insight"])
        self.assertNotIn("تحتاج انتباهك", insight["primary_insight"])
        self.assertNotRegex(insight["primary_insight"], r"^\d+\s")
        self.assertIn("لأن", insight["reason"])
        self.assertIn("CartFlow", insight["cartflow_action"])
        self.assertEqual(insight["evidence_summary"]["monitored_count"], 4)
        self.assertEqual(insight["evidence_summary"]["attention_count"], 4)
        self.assertEqual(
            insight["composition_order"],
            ["primary_insight", "reason", "cartflow_action", "evidence_summary"],
        )
        self.assertEqual(validate_page_insight_v1(insight), [])

    def test_carts_no_attention_healthy(self) -> None:
        evidence = {
            "monitored_count": 5,
            "attention_count": 0,
            "automatic_count": 5,
            "has_sufficient_evidence": True,
        }
        insight = compose_page_insight_v1("carts", evidence)
        self.assertIn("لا يلزم إجراء", insight["primary_insight"])
        self.assertEqual(validate_page_insight_v1(insight), [])

    def test_carts_insufficient_evidence_monitoring_only(self) -> None:
        insight = compose_page_insight_v1("carts", {"has_sufficient_evidence": False})
        self.assertEqual(insight["insight_type"], INSIGHT_MONITORING_ONLY)
        self.assertEqual(insight["confidence"], "insufficient")
        self.assertEqual(validate_page_insight_v1(insight), [])

    def test_build_evidence_from_payload_delegates_carts(self) -> None:
        payload = {
            "merchant_value_stories_v1": {
                "stories": [{"action_required": True, "affected_carts": 2}],
            },
            "merchant_cart_filter_counts": {"all": 2},
        }
        evidence = build_page_insight_evidence_v1("carts", payload, rows=[{}, {}])
        self.assertTrue(evidence.get("has_sufficient_evidence"))
        self.assertEqual(evidence.get("attention_count"), 2)

    def test_home_attention_insight(self) -> None:
        insight = compose_page_insight_v1("home", {"attention_count": 2})
        self.assertIn("تستحق", insight["primary_insight"])
        self.assertEqual(validate_page_insight_v1(insight), [])

    def test_validate_rejects_forbidden_and_count_first(self) -> None:
        bad = compose_page_insight_v1(
            "carts",
            {
                "monitored_count": 1,
                "attention_count": 1,
                "automatic_count": 0,
                "has_sufficient_evidence": True,
            },
        )
        bad["primary_insight"] = "4 سلال تستحق انتباهك"
        violations = validate_page_insight_v1(bad)
        self.assertTrue(any("raw count" in v for v in violations))

    def test_payload_contract_fields(self) -> None:
        insight = compose_page_insight_v1(
            "carts",
            {
                "monitored_count": 3,
                "attention_count": 1,
                "automatic_count": 2,
                "has_sufficient_evidence": True,
            },
        )
        self.assertEqual(insight["version"], INSIGHT_VERSION)
        self.assertEqual(insight["authority"], AUTHORITY)
        for key in (
            "primary_insight",
            "reason",
            "cartflow_action",
            "evidence_summary",
            "source_refs",
            "confidence",
        ):
            self.assertIn(key, insight)
        combined = " ".join(
            insight[k] for k in ("primary_insight", "reason", "cartflow_action")
        )
        self.assertIsNone(_FORBIDDEN.search(combined))

    def test_unknown_page_raises(self) -> None:
        with self.assertRaises(ValueError):
            compose_page_insight_v1("unknown", {})


if __name__ == "__main__":
    unittest.main()
