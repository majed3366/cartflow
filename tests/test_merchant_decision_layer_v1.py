# -*- coding: utf-8 -*-
"""Merchant decision layer v1-A — unit tests."""
from __future__ import annotations

import unittest

from services.merchant_decision_layer_v1 import (
    DECISION_CONTACT_CUSTOMER,
    DECISION_FIX_CHANNEL,
    DECISION_MONITOR,
    DECISION_OBTAIN_CONTACT,
    attach_merchant_decision_layer_v1,
    resolve_merchant_decision_key_v1,
)


def _resolve(**kwargs: object) -> str | None:
    return resolve_merchant_decision_key_v1(**kwargs)  # type: ignore[arg-type]


class MerchantDecisionLayerV1Tests(unittest.TestCase):
    def test_t1_needs_intervention_no_phone(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=False,
            ),
            DECISION_OBTAIN_CONTACT,
        )

    def test_t2_schedule_blocked_missing_phone_log(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=True,
                log_statuses=["schedule_blocked_missing_phone"],
            ),
            DECISION_OBTAIN_CONTACT,
        )

    def test_t3_whatsapp_failed(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=True,
                log_statuses=["whatsapp_failed"],
            ),
            DECISION_FIX_CHANNEL,
        )

    def test_t4_failed_final(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=True,
                log_statuses=["failed_final"],
            ),
            DECISION_FIX_CHANNEL,
        )

    def test_t5_generic_intervention(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=True,
                log_statuses=["sent_real"],
            ),
            DECISION_CONTACT_CUSTOMER,
        )

    def test_t6_schedule_not_materialized_no_key(self) -> None:
        self.assertIsNone(
            _resolve(
                customer_lifecycle_state="needs_intervention",
                customer_lifecycle_merchant_needed_ar="لا",
                customer_lifecycle_label_ar="لم يتم تجهيز الإرسال بعد",
            ),
        )

    def test_t7_return_to_site_monitor(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="return_to_site",
                customer_lifecycle_merchant_needed_ar="لا",
            ),
            DECISION_MONITOR,
        )

    def test_t8_waiting_purchase_window_monitor(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="waiting_purchase_window",
                customer_lifecycle_merchant_needed_ar="لا",
            ),
            DECISION_MONITOR,
        )

    def test_t9_waiting_customer_reply_no_key(self) -> None:
        self.assertIsNone(
            _resolve(
                customer_lifecycle_state="waiting_customer_reply",
                customer_lifecycle_merchant_needed_ar="لا",
            ),
        )

    def test_t10_completed_purchase_truth_no_key(self) -> None:
        self.assertIsNone(
            _resolve(
                customer_lifecycle_state="completed",
                customer_lifecycle_merchant_needed_ar="لا",
                purchase_truth=True,
            ),
        )

    def test_t11_archived_no_key(self) -> None:
        self.assertIsNone(
            _resolve(
                customer_lifecycle_state="archived",
                customer_lifecycle_merchant_needed_ar="لا",
            ),
        )

    def test_t12_attach_sets_and_omits_key(self) -> None:
        with_key: dict = {}
        attach_merchant_decision_layer_v1(
            with_key,
            customer_lifecycle_state="return_to_site",
            customer_lifecycle_merchant_needed_ar="لا",
        )
        self.assertEqual(with_key.get("merchant_decision_key"), DECISION_MONITOR)

        without_key: dict = {}
        attach_merchant_decision_layer_v1(
            without_key,
            customer_lifecycle_state="waiting_customer_reply",
            customer_lifecycle_merchant_needed_ar="لا",
        )
        self.assertNotIn("merchant_decision_key", without_key)

    def test_t13_return_precedence_over_intervention(self) -> None:
        self.assertEqual(
            _resolve(
                customer_lifecycle_state="return_to_site",
                customer_lifecycle_merchant_needed_ar="نعم",
                has_phone=False,
            ),
            DECISION_MONITOR,
        )


if __name__ == "__main__":
    unittest.main()
