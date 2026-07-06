# -*- coding: utf-8 -*-
"""Merchant Intelligence Service v1 — certification tests."""
from __future__ import annotations

import unittest

from services.merchant_cart_row_classifier import (
    PRIMARY_NO_PHONE,
    PRIMARY_RECOVERED,
    PRIMARY_RETURN_TO_SITE,
    PRIMARY_SENT,
)
from services.merchant_decision_layer_v1 import (
    CLASS_CRITICAL_ACTION,
    CLASS_OBSERVATION,
    CLASS_SUGGESTED_ACTION,
    LIFECYCLE_PUBLISHED,
    attach_merchant_decisions_v1,
)
from services.merchant_intelligence_v1 import (
    AUTHORITY,
    GROUP_COMPLETED,
    GROUP_NEEDS_MERCHANT,
    GROUP_NO_CONTACT,
    GROUP_REPEATED_HESITATION,
    GROUP_RETURNED,
    GROUP_VIP,
    GROUP_WAITING_REPLY,
    INTELLIGENCE_VERSION,
    REC_BLOCKED,
    REC_NO_ACTION,
    REC_REQUIRED,
    REC_SUGGESTED,
    REC_WATCH,
    SURFACE_CARTS,
    SURFACE_MERCHANT_HOME,
    assign_cart_intelligence_group,
    attach_merchant_intelligence_v1,
    build_memory_beats_v1,
    build_store_merchant_intelligence_v1,
    decision_class_to_recommendation_type,
    derive_recommendation_v1,
    get_merchant_intelligence_observability_v1,
    reset_merchant_intelligence_observability_v1,
    validate_merchant_intelligence_contract_v1,
)
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1


def _base_row(**overrides: object) -> dict:
    row = {
        "recovery_key": "store:cart:1",
        "store_slug": "demo",
        "has_phone": True,
        "merchant_cart_primary_bucket": PRIMARY_SENT,
        "merchant_cart_bucket": "sent",
        "customer_lifecycle_state": "waiting_customer_reply",
        "customer_lifecycle_merchant_needed_ar": "لا",
        "merchant_intervention_executable": True,
        "cart_value": 1240.0,
        "reason_tag": "",
    }
    row.update(overrides)
    return row


def _attach_decisions(row: dict, *, action_key: str = "contact_customer") -> None:
    attach_merchant_proof_surface_v1(
        row,
        recovery_key=str(row.get("recovery_key") or ""),
        customer_lifecycle_state=str(row.get("customer_lifecycle_state") or ""),
        customer_lifecycle_what_happened_ar="تحتاج تدخل",
        log_statuses=[],
    )
    row["merchant_decision_key"] = action_key
    attach_merchant_decisions_v1(row)


class MerchantIntelligenceServiceV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        reset_merchant_intelligence_observability_v1()

    def test_decision_class_to_recommendation_mapping(self) -> None:
        self.assertEqual(
            decision_class_to_recommendation_type(CLASS_CRITICAL_ACTION),
            REC_REQUIRED,
        )
        self.assertEqual(
            decision_class_to_recommendation_type(CLASS_SUGGESTED_ACTION),
            REC_SUGGESTED,
        )
        self.assertEqual(
            decision_class_to_recommendation_type(
                "needs_attention",
                action_eligible=False,
            ),
            REC_WATCH,
        )

    def test_group_assignment_needs_merchant(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_decisions(row)
        assignment = assign_cart_intelligence_group(row)
        self.assertIsNotNone(assignment)
        assert assignment is not None
        self.assertEqual(assignment["group_id"], GROUP_NEEDS_MERCHANT)
        self.assertEqual(assignment["authority"], AUTHORITY)
        self.assertIn(SURFACE_MERCHANT_HOME, assignment["eligible_surfaces"])

    def test_group_assignment_vip(self) -> None:
        row = _base_row(is_vip_lane=True, customer_lifecycle_merchant_needed_ar="لا")
        assignment = assign_cart_intelligence_group(row)
        self.assertIsNotNone(assignment)
        assert assignment is not None
        self.assertEqual(assignment["group_id"], GROUP_VIP)

    def test_group_assignment_completed(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_RECOVERED,
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="purchased",
        )
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_COMPLETED)

    def test_group_assignment_returned(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_RETURN_TO_SITE,
            customer_lifecycle_state="return_to_site",
        )
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_RETURNED)

    def test_group_assignment_no_contact(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_NO_PHONE,
            has_phone=False,
        )
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_NO_CONTACT)

    def test_group_assignment_waiting_reply_calm(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_SENT,
            customer_lifecycle_merchant_needed_ar="لا",
        )
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_WAITING_REPLY)

    def test_recommendation_derivation_required(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_decisions(row)
        rec = derive_recommendation_v1(row)
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec["recommendation_type"], REC_SUGGESTED)
        self.assertTrue(rec["merchant_message_ar"])
        self.assertEqual(rec["authority"], AUTHORITY)

    def test_recommendation_blocked_missing_phone(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_NO_PHONE,
            has_phone=False,
        )
        rec = derive_recommendation_v1(row, group_assignment={"group_id": GROUP_NO_CONTACT})
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec["recommendation_type"], REC_BLOCKED)

    def test_attach_merchant_intelligence_v1(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_decisions(row)
        attach_merchant_intelligence_v1(row)
        bundle = row.get("merchant_intelligence_v1")
        self.assertIsInstance(bundle, dict)
        assert isinstance(bundle, dict)
        self.assertEqual(bundle.get("version"), INTELLIGENCE_VERSION)
        self.assertEqual(row.get("intelligence_group_key"), GROUP_NEEDS_MERCHANT)
        self.assertEqual(validate_merchant_intelligence_contract_v1(bundle), [])

    def test_store_intelligence_groups_and_patterns(self) -> None:
        rows = [
            _base_row(
                recovery_key="a",
                reason_tag="price",
                customer_lifecycle_merchant_needed_ar="نعم",
            ),
            _base_row(
                recovery_key="b",
                reason_tag="price",
                customer_lifecycle_merchant_needed_ar="نعم",
            ),
            _base_row(recovery_key="c", reason_tag="price"),
        ]
        for r in rows[:2]:
            _attach_decisions(r)
        store = build_store_merchant_intelligence_v1(rows)
        self.assertEqual(store.get("version"), INTELLIGENCE_VERSION)
        groups = store.get("groups") or []
        group_ids = {g.get("group_id") for g in groups}
        self.assertIn(GROUP_NEEDS_MERCHANT, group_ids)
        self.assertIn(GROUP_REPEATED_HESITATION, group_ids)
        self.assertTrue(store.get("priorities"))
        obs = store.get("observability") or {}
        self.assertTrue(obs.get("reviewable"))

    def test_memory_requires_comparison_context(self) -> None:
        groups = [{"group_id": GROUP_NEEDS_MERCHANT, "affected_carts": 3}]
        beats_no_ctx = build_memory_beats_v1([], groups)
        self.assertFalse(any(b.get("memory_type") == "compared_to_yesterday" for b in beats_no_ctx))
        beats = build_memory_beats_v1(
            [],
            groups,
            comparison_context={"group_counts_yesterday": {GROUP_NEEDS_MERCHANT: 1}},
        )
        self.assertTrue(any(b.get("memory_type") == "compared_to_yesterday" for b in beats))

    def test_memory_repeated_pattern_in_batch(self) -> None:
        rows = [_base_row(reason_tag="shipping") for _ in range(2)]
        beats = build_memory_beats_v1(rows, [])
        self.assertTrue(any(b.get("memory_type") == "repeated_pattern" for b in beats))

    def test_deterministic_regression_same_inputs(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_decisions(row)
        a = assign_cart_intelligence_group(row)
        b = assign_cart_intelligence_group(row)
        self.assertEqual(a, b)

    def test_completed_recommendation_no_action(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket=PRIMARY_RECOVERED,
            customer_lifecycle_state="completed",
        )
        rec = derive_recommendation_v1(row, group_assignment={"group_id": GROUP_COMPLETED})
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec["recommendation_type"], REC_NO_ACTION)

    def test_forbidden_no_ui_imports(self) -> None:
        import services.merchant_intelligence_v1 as mi

        source = open(mi.__file__, encoding="utf-8").read()
        self.assertNotIn("flask", source.lower())
        self.assertNotIn("jinja", source.lower())
        self.assertNotIn("merchant_dashboard_lazy", source)

    def test_observability_counters(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_decisions(row)
        attach_merchant_intelligence_v1(row)
        obs = get_merchant_intelligence_observability_v1()
        self.assertGreaterEqual(obs.get("groups_assigned", 0), 1)
        self.assertGreaterEqual(obs.get("recommendations_projected", 0), 1)

    def test_surface_eligibility_on_group(self) -> None:
        row = _base_row(is_vip_lane=True)
        assignment = assign_cart_intelligence_group(row)
        assert assignment is not None
        self.assertIn(SURFACE_CARTS, assignment["eligible_surfaces"])


if __name__ == "__main__":
    unittest.main()
