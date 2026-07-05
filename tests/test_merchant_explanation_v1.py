# -*- coding: utf-8 -*-
"""Merchant Explanation Unification v1 — unified explanation layer tests."""
from __future__ import annotations

import unittest

from services.customer_lifecycle_states_v1 import (
    STATE_COMPLETED,
    STATE_NEEDS_INTERVENTION,
    STATE_RETURN_TO_SITE,
    STATE_WAITING_CUSTOMER_REPLY,
    STATE_WAITING_FIRST_SEND,
    STATE_WAITING_PURCHASE_WINDOW,
)
from services.merchant_explanation_v1 import (
    EXPLANATION_VERSION,
    _EXPLANATION_CATALOG,
    attach_merchant_explanation_v1,
    build_merchant_explanation_v1,
    validate_merchant_explanation_merchant_safe,
)


class MerchantExplanationV1Tests(unittest.TestCase):
    def test_all_catalog_entries_are_merchant_safe(self) -> None:
        for state_key, entry in _EXPLANATION_CATALOG.items():
            expl = build_merchant_explanation_v1(lifecycle_state=state_key)
            errors = validate_merchant_explanation_merchant_safe(expl)
            self.assertEqual(errors, [], msg=f"{state_key}: {errors}")

    def test_waiting_purchase_window_uses_merchant_copy(self) -> None:
        expl = build_merchant_explanation_v1(
            lifecycle_state=STATE_WAITING_PURCHASE_WINDOW,
            what_happened_ar="عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
        )
        self.assertEqual(expl["explanation_id"], "return_without_purchase")
        self.assertIn("CartFlow", expl["system_did_ar"])
        self.assertNotIn("waiting_purchase_window", expl["what_happened_ar"])
        self.assertFalse(expl["action_required"])

    def test_leaky_lifecycle_label_is_replaced(self) -> None:
        expl = build_merchant_explanation_v1(
            lifecycle_state=STATE_WAITING_FIRST_SEND,
            lifecycle_label_ar="waiting_first_send",
        )
        self.assertNotIn("waiting_first_send", expl["status_label_ar"])
        self.assertEqual(expl["status_label_ar"], "بانتظار الإرسال")

    def test_needs_intervention_marks_action_required(self) -> None:
        expl = build_merchant_explanation_v1(
            lifecycle_state=STATE_NEEDS_INTERVENTION,
            merchant_needed_ar="نعم",
        )
        self.assertTrue(expl["action_required"])
        self.assertIn("واتساب", expl["merchant_action_needed_ar"])

    def test_metadata_for_knowledge_routing_prep(self) -> None:
        expl = build_merchant_explanation_v1(lifecycle_state=STATE_RETURN_TO_SITE)
        self.assertEqual(expl["version"], EXPLANATION_VERSION)
        self.assertTrue(expl.get("explanation_id"))
        self.assertTrue(expl.get("knowledge_event_type"))
        self.assertEqual(expl.get("merchant_visibility"), "merchant_dashboard")
        self.assertIn("cart_detail", expl.get("eligible_surfaces") or [])

    def test_diagnostic_internal_preserves_state_key(self) -> None:
        expl = build_merchant_explanation_v1(
            lifecycle_state=STATE_WAITING_CUSTOMER_REPLY,
            diagnostic_lifecycle_state=STATE_WAITING_CUSTOMER_REPLY,
            diagnostic_proof_summary_ar="حالة المسار: waiting_customer_reply",
        )
        diag = expl.get("diagnostic_internal") or {}
        self.assertEqual(diag.get("lifecycle_state"), STATE_WAITING_CUSTOMER_REPLY)
        self.assertIn("حالة المسار", diag.get("proof_summary_diagnostic_ar") or "")

    def test_attach_syncs_legacy_lifecycle_fields(self) -> None:
        row: dict = {
            "customer_lifecycle_state": STATE_WAITING_PURCHASE_WINDOW,
            "customer_lifecycle_label_ar": "waiting_purchase_window",
            "customer_lifecycle_what_happened_ar": "عاد العميل إلى المتجر بعد الرسالة.",
            "customer_lifecycle_system_did_ar": "CartFlow أوقف المتابعة مؤقتًا.",
            "customer_lifecycle_what_next_ar": "سيواصل المتابعة حسب الإعدادات.",
            "customer_lifecycle_merchant_needed_ar": "لا",
            "merchant_proof_surface_v1": {
                "why_we_know_diagnostic_ar": "حالة المسار: waiting_purchase_window",
            },
        }
        attach_merchant_explanation_v1(row)
        self.assertIn("merchant_explanation_v1", row)
        self.assertNotIn("waiting_purchase_window", row["customer_lifecycle_label_ar"])
        self.assertNotIn("waiting_purchase_window", row["customer_lifecycle_what_happened_ar"])
        self.assertEqual(
            row["customer_lifecycle_label_ar"],
            row["merchant_explanation_v1"]["status_label_ar"],
        )

    def test_purchase_truth_maps_to_completed_explanation(self) -> None:
        expl = build_merchant_explanation_v1(
            lifecycle_state=STATE_WAITING_CUSTOMER_REPLY,
            purchase_truth=True,
        )
        self.assertEqual(expl["explanation_id"], "purchase_confirmed")


if __name__ == "__main__":
    unittest.main()
