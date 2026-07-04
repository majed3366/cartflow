# -*- coding: utf-8 -*-
"""Merchant Evidence Registry v1 — governed evidence language tests."""
from __future__ import annotations

import unittest

from services.merchant_evidence_registry_v1 import (
    EVIDENCE_PURCHASE_RECORD,
    EVIDENCE_RECOVERY_RECORD,
    EVIDENCE_STORE_ACTIVITY,
    REGISTRY_VERSION,
    attach_merchant_evidence_registry_v1,
    merchant_evidence_for_tier0_key,
    merchant_evidence_label_ar,
    merchant_evidence_section_source_ar,
)
from services.merchant_proof_surface_v1 import (
    EVIDENCE_PURCHASE,
    attach_merchant_proof_surface_v1,
    build_merchant_proof_surface_v1,
)


class MerchantEvidenceRegistryV1Tests(unittest.TestCase):
    def test_tier0_maps_to_stable_evidence_id(self) -> None:
        meta = merchant_evidence_for_tier0_key("purchase_truth")
        self.assertEqual(meta["evidence_id"], EVIDENCE_PURCHASE_RECORD)
        self.assertNotIn("Truth", meta["label_ar"])
        self.assertNotIn("Lifecycle", meta["label_ar"])

    def test_recovery_record_label_merchant_natural(self) -> None:
        label = merchant_evidence_label_ar(EVIDENCE_RECOVERY_RECORD)
        self.assertEqual(label, "سجل الاسترجاع")

    def test_knowledge_section_source_from_registry(self) -> None:
        note = merchant_evidence_section_source_ar(EVIDENCE_STORE_ACTIVITY)
        self.assertEqual(note, "مصدر الدليل: بيانات المتجر")
        self.assertNotIn("CartFlow", note)
        self.assertNotIn("Knowledge Layer", note)

    def test_store_vs_platform_origin_distinction(self) -> None:
        from services.merchant_evidence_registry_v1 import (
            EVIDENCE_CARTFLOW_ANALYTICS,
            get_merchant_evidence_entry,
        )

        store = get_merchant_evidence_entry(EVIDENCE_STORE_ACTIVITY)
        platform = get_merchant_evidence_entry(EVIDENCE_CARTFLOW_ANALYTICS)
        assert store is not None and platform is not None
        self.assertEqual(store.evidence_origin, "store")
        self.assertEqual(platform.evidence_origin, "platform")
        self.assertEqual(store.label_ar, "بيانات المتجر")
        self.assertEqual(platform.label_ar, "بيانات CartFlow")
        self.assertNotEqual(store.label_ar, platform.label_ar)

    def test_attach_registry_payload(self) -> None:
        payload: dict = {"ok": True}
        attach_merchant_evidence_registry_v1(payload, surface_context="knowledge_layer")
        reg = payload["merchant_evidence_registry_v1"]
        self.assertEqual(reg["version"], REGISTRY_VERSION)
        self.assertEqual(reg["section_evidence_id"], EVIDENCE_STORE_ACTIVITY)
        self.assertIn("section_source_ar", reg)

    def test_proof_surface_consumes_registry(self) -> None:
        bundle = build_merchant_proof_surface_v1(
            purchase_truth=True,
            customer_lifecycle_state="completed",
        )
        self.assertEqual(bundle["evidence_id"], EVIDENCE_PURCHASE_RECORD)
        self.assertEqual(bundle["evidence_source_ar"], "سجل الشراء")
        self.assertNotIn("Purchase Truth", bundle.get("why_we_know_ar") or "")

    def test_proof_steps_include_evidence_id(self) -> None:
        row: dict = {"recovery_key": "s:1"}
        attach_merchant_proof_surface_v1(
            row,
            log_statuses=["sent_real"],
            sent_count=1,
        )
        steps = row["merchant_proof_surface_v1"]["recovery_steps"]
        self.assertTrue(all(s.get("evidence_id") for s in steps))
        self.assertTrue(all(s.get("evidence_label_ar") for s in steps))

    def test_primary_evidence_type_unchanged(self) -> None:
        bundle = build_merchant_proof_surface_v1(
            purchase_truth=False,
            customer_lifecycle_state="waiting_customer_reply",
        )
        self.assertEqual(bundle["evidence_type"], "lifecycle_truth")


if __name__ == "__main__":
    unittest.main()
