# -*- coding: utf-8 -*-
"""Return-without-purchase merchant explanation + diagnostic language cleanup v1."""
from __future__ import annotations

import unittest

from services.cartflow_merchant_lifecycle import build_normal_recovery_merchant_lifecycle
from services.customer_lifecycle_states_v1 import (
    LIFECYCLE_TRUTH_UNAVAILABLE_LABEL_AR,
    classify_customer_lifecycle_state_v1,
)
from services.merchant_daily_brief_composer_v2 import (
    compose_merchant_daily_brief_v2,
    is_achievement_decision,
)
from services.merchant_decision_layer_v1 import (
    CLASS_OBSERVATION,
    DECISION_MONITOR,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
    _build_explanation,
    build_merchant_decision_v1,
    resolve_merchant_decision_key_v1,
)
from services.merchant_decision_registry_v1 import DECISION_ID_MONITOR_RETURN
from services.merchant_proof_surface_v1 import (
    STEP_LABEL_AR,
    _STEP_MESSAGE_ACCEPTED,
    build_merchant_proof_surface_v1,
)


class ReturnWithoutPurchaseMerchantExplanationV1Tests(unittest.TestCase):
    def test_scenario1_purchase_confirmed_no_technical_terms(self) -> None:
        bundle = build_merchant_proof_surface_v1(
            purchase_truth=True,
            customer_lifecycle_state="completed",
            customer_lifecycle_label_ar="تمت الاستعادة",
            customer_lifecycle_what_happened_ar="أكمل العميل الشراء.",
        )
        why = bundle.get("why_we_know_ar") or ""
        self.assertNotIn("waiting_purchase_window", why)
        self.assertNotIn("حالة المسار", why)
        self.assertNotIn("سجل إرسال", why)
        self.assertIn("أكمل العميل الشراء", why)

    def test_scenario2_waiting_purchase_window_merchant_copy(self) -> None:
        pack = classify_customer_lifecycle_state_v1(
            recovery_key="demo:ret-wait",
            phase_key="first_message_sent",
            coarse="sent",
            sent_count=1,
            attempt_cap=2,
            log_statuses=frozenset({"mock_sent", "returned_to_site"}),
            behavioral={"user_returned_to_site": True},
            purchase_truth=False,
            next_attempt_due_at="2099-01-01T12:00:00+00:00",
            schedule_prefetched=True,
        )
        self.assertEqual(pack.state_key, "waiting_purchase_window")
        self.assertIn("عاد", pack.what_happened_ar)
        self.assertIn("CartFlow", pack.system_did_ar)
        self.assertIn("سيواصل", pack.what_next_ar)
        self.assertEqual(pack.merchant_needed_ar, "لا")
        self.assertNotIn("waiting_purchase_window", pack.what_happened_ar)

    def test_scenario2_merchant_lifecycle_after_message_return(self) -> None:
        ml = build_normal_recovery_merchant_lifecycle(
            phase_key="first_message_sent",
            coarse="sent",
            latest_log_status="skipped_anti_spam",
            blocker_key="",
            behavioral={"user_returned_to_site": True},
            sent_ct=1,
            attempt_cap=2,
            recovery_log_statuses=["mock_sent", "skipped_anti_spam"],
        )
        self.assertEqual(ml["merchant_lifecycle_primary_key"], "customer_returned_after_message")
        self.assertIn("بعد الرسالة", ml["merchant_lifecycle_customer_behavior_ar"])
        self.assertIn("CartFlow", ml["merchant_lifecycle_system_outcome_ar"])
        self.assertIn("سيواصل", ml["merchant_lifecycle_next_action_ar"])

    def test_scenario3_recovery_resume_is_scheduled_not_merchant_action(self) -> None:
        """Purchase window expiry resumes via existing schedule — no merchant action."""
        key = resolve_merchant_decision_key_v1(
            customer_lifecycle_state="waiting_purchase_window",
            customer_lifecycle_merchant_needed_ar="لا",
        )
        self.assertEqual(key, DECISION_MONITOR)
        expl = _build_explanation(
            action_key=DECISION_MONITOR,
            lifecycle_state="waiting_purchase_window",
            what_happened_ar="عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
        )
        self.assertIn("سيواصل", expl["if_omitted_ar"])
        self.assertIn("لا يلزم", expl["why_now_ar"])

    def test_scenario4_proof_surface_no_internal_state_in_merchant_fields(self) -> None:
        bundle = build_merchant_proof_surface_v1(
            customer_lifecycle_state="waiting_purchase_window",
            customer_lifecycle_label_ar="عاد العميل للموقع — أوقفنا المتابعة مؤقتًا",
            customer_lifecycle_what_happened_ar="عاد العميل إلى المتجر بعد الرسالة.",
            log_statuses=["sent_real"],
            sent_count=1,
        )
        why = bundle.get("why_we_know_ar") or ""
        diag = bundle.get("why_we_know_diagnostic_ar") or ""
        self.assertNotIn("waiting_purchase_window", why)
        self.assertNotIn("حالة المسار", why)
        self.assertNotIn("قبول المزود", why)
        self.assertNotIn("سجل إرسال مقبول", why)
        self.assertIn("waiting_purchase_window", diag)
        self.assertIn("حالة المسار", diag)
        step_labels = [s.get("label_ar") for s in bundle.get("recovery_steps") or []]
        self.assertNotIn("قبول المزود للرسالة", step_labels)
        self.assertEqual(
            STEP_LABEL_AR[_STEP_MESSAGE_ACCEPTED],
            "إرسال الرسالة",
        )

    def test_daily_brief_achievement_from_monitor_return_decision(self) -> None:
        proof = build_merchant_proof_surface_v1(
            customer_lifecycle_state="waiting_purchase_window",
            customer_lifecycle_what_happened_ar="عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
        )
        decision = build_merchant_decision_v1(
            decision_id=DECISION_ID_MONITOR_RETURN,
            action_key=DECISION_MONITOR,
            proof=proof,
            proof_source="demo:cart:1",
            lifecycle_state="waiting_purchase_window",
            what_happened_ar="عاد العميل إلى المتجر بعد رسالة الاسترجاع.",
            merchant_needed_ar="لا",
        )
        decision["decision_class"] = CLASS_OBSERVATION
        decision["lifecycle_state"] = LIFECYCLE_PUBLISHED
        decision["verification_status"] = VERIFY_PASSED
        self.assertTrue(is_achievement_decision(decision))
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"version": "v1", "decisions": [decision], "suppressed": []}],
            brief_date="2026-07-05",
        )
        self.assertEqual(len(brief["achievements"]), 1)
        headline = brief["achievements"][0]["headline_ar"]
        self.assertIn("عاد", headline)
        self.assertNotIn("waiting_purchase_window", headline)

    def test_lifecycle_unavailable_label_is_merchant_friendly(self) -> None:
        self.assertNotIn("حالة المسار", LIFECYCLE_TRUTH_UNAVAILABLE_LABEL_AR)


if __name__ == "__main__":
    unittest.main()
