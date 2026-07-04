# -*- coding: utf-8 -*-
"""Merchant claim evidence v1 — claim-level ownership tests."""
from __future__ import annotations

import unittest

from services.merchant_claim_evidence_v1 import (
    enrich_claim_evidence_fields,
    enrich_knowledge_report_claim_evidence_v1,
    resolve_claim_evidence_id,
)
from services.merchant_evidence_registry_v1 import (
    EVIDENCE_CUSTOMER_RESPONSE,
    EVIDENCE_PURCHASE_RECORD,
    EVIDENCE_RECOVERY_RECORD,
    EVIDENCE_STORE_ACTIVITY,
    EVIDENCE_VISITOR_BEHAVIOR,
)


class MerchantClaimEvidenceV1Tests(unittest.TestCase):
    def test_conversion_purchase_uses_purchase_record(self) -> None:
        eid = resolve_claim_evidence_id(insight_key="conversion_cart_to_purchase")
        self.assertEqual(eid, EVIDENCE_PURCHASE_RECORD)

    def test_hesitation_uses_customer_response(self) -> None:
        eid = resolve_claim_evidence_id(insight_key="hesitation_top_reason")
        self.assertEqual(eid, EVIDENCE_CUSTOMER_RESPONSE)

    def test_recovery_uses_recovery_record(self) -> None:
        eid = resolve_claim_evidence_id(insight_key="recovery_bottleneck")
        self.assertEqual(eid, EVIDENCE_RECOVERY_RECORD)

    def test_traffic_visitor_uses_visitor_behavior(self) -> None:
        eid = resolve_claim_evidence_id(insight_key="traffic_visitor_unavailable")
        self.assertEqual(eid, EVIDENCE_VISITOR_BEHAVIOR)

    def test_enrich_claim_fields_on_insight(self) -> None:
        ins: dict = {
            "insight_key": "store_health_overview",
            "category": "store_health",
            "confidence": "medium",
        }
        enrich_claim_evidence_fields(ins)
        self.assertEqual(ins["evidence_id"], EVIDENCE_STORE_ACTIVITY)
        self.assertEqual(ins["evidence_label_ar"], "بيانات المتجر")
        self.assertTrue(ins["claim_evidence_source_ar"].startswith("مصدر الدليل:"))
        self.assertNotIn("Knowledge Layer", ins["evidence_label_ar"])

    def test_report_enrichment_is_claim_owned_not_section(self) -> None:
        payload: dict = {
            "ok": True,
            "insights": [
                {
                    "insight_key": "conversion_cart_to_purchase",
                    "category": "conversion",
                    "confidence": "high",
                },
                {
                    "insight_key": "recovery_activity_summary",
                    "category": "recovery",
                    "confidence": "medium",
                },
            ],
        }
        enrich_knowledge_report_claim_evidence_v1(payload)
        reg = payload["merchant_evidence_registry_v1"]
        self.assertNotIn("section_source_ar", reg)
        self.assertNotIn("section_evidence_id", reg)
        self.assertEqual(payload["merchant_claim_evidence_v1"]["ownership"], "claim")
        by_key = {i["insight_key"]: i for i in payload["insights"]}
        self.assertEqual(
            by_key["conversion_cart_to_purchase"]["evidence_id"],
            EVIDENCE_PURCHASE_RECORD,
        )
        self.assertEqual(
            by_key["recovery_activity_summary"]["evidence_id"],
            EVIDENCE_RECOVERY_RECORD,
        )
        self.assertNotEqual(
            by_key["conversion_cart_to_purchase"]["evidence_id"],
            by_key["recovery_activity_summary"]["evidence_id"],
        )


if __name__ == "__main__":
    unittest.main()
