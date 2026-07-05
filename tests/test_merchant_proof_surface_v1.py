# -*- coding: utf-8 -*-
"""Merchant proof surface v1 — presentation composition tests."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from services.merchant_proof_surface_v1 import (
    CONF_CONFIRMED,
    CONF_UNKNOWN,
    DOMAIN_DECISION,
    DOMAIN_RECOVERY,
    _STEP_MESSAGE_ACCEPTED,
    _STEP_PROVIDER_DELIVERED,
    attach_merchant_proof_surface_v1,
    build_merchant_proof_surface_v1,
    build_recovery_proof_steps,
    resolve_row_proof_confidence,
)


class MerchantProofSurfaceV1Tests(unittest.TestCase):
    def test_purchase_row_confirmed_confidence(self) -> None:
        conf = resolve_row_proof_confidence(
            purchase_truth=True,
            customer_lifecycle_state="completed",
        )
        self.assertEqual(conf, CONF_CONFIRMED)

    def test_sent_without_delivery_is_unknown_for_delivery_step(self) -> None:
        steps = build_recovery_proof_steps(
            log_statuses=["sent_real"],
            sent_count=1,
            latest_log=None,
        )
        by_key = {s["key"]: s for s in steps}
        self.assertEqual(by_key[_STEP_MESSAGE_ACCEPTED]["state"], "done")
        self.assertEqual(by_key[_STEP_PROVIDER_DELIVERED]["state"], "unknown")
        self.assertEqual(by_key[_STEP_PROVIDER_DELIVERED]["confidence"], CONF_UNKNOWN)

    def test_delivered_truth_marks_delivery_done(self) -> None:
        truth = SimpleNamespace(truth_level="delivered_to_customer")
        with mock.patch(
            "services.merchant_proof_surface_v1._lookup_delivery_truth",
            return_value=truth,
        ):
            steps = build_recovery_proof_steps(
                log_statuses=["sent_real"],
                sent_count=1,
                latest_log=SimpleNamespace(provider_message_sid="SM123"),
            )
        delivery = [s for s in steps if s["key"] == _STEP_PROVIDER_DELIVERED][0]
        self.assertEqual(delivery["state"], "done")
        self.assertEqual(delivery["confidence"], CONF_CONFIRMED)

    def test_attach_adds_bundle_without_mutating_lifecycle(self) -> None:
        row = {
            "recovery_key": "demo:abc",
            "customer_lifecycle_state": "waiting_customer_reply",
            "customer_lifecycle_what_happened_ar": "أُرسلت رسالة استرجاع",
        }
        before = dict(row)
        attach_merchant_proof_surface_v1(
            row,
            recovery_key="demo:abc",
            log_statuses=["sent_real"],
            sent_count=1,
        )
        self.assertIn("merchant_proof_surface_v1", row)
        ps = row["merchant_proof_surface_v1"]
        self.assertEqual(ps["version"], "v1")
        self.assertEqual(ps["primary_domain"], DOMAIN_DECISION)
        self.assertTrue(ps["recovery_steps"])
        self.assertEqual(row["customer_lifecycle_state"], before["customer_lifecycle_state"])

    def test_waiting_purchase_window_no_raw_state_in_merchant_why(self) -> None:
        bundle = build_merchant_proof_surface_v1(
            customer_lifecycle_state="waiting_purchase_window",
            customer_lifecycle_label_ar="عاد العميل للموقع — أوقفنا المتابعة مؤقتًا",
            customer_lifecycle_what_happened_ar="عاد العميل إلى المتجر بعد الرسالة.",
            log_statuses=["sent_real"],
            sent_count=1,
        )
        why = bundle.get("why_we_know_ar") or ""
        self.assertNotIn("waiting_purchase_window", why)
        self.assertNotIn("حالة المسار", why)
        diag = bundle.get("why_we_know_diagnostic_ar") or ""
        self.assertIn("waiting_purchase_window", diag)

    def test_purchase_domain_recovery(self) -> None:
        row: dict = {"recovery_key": "s:1"}
        attach_merchant_proof_surface_v1(
            row,
            purchase_truth=True,
            customer_lifecycle_state="completed",
        )
        self.assertEqual(
            row["merchant_proof_surface_v1"]["primary_domain"],
            DOMAIN_RECOVERY,
        )


if __name__ == "__main__":
    unittest.main()
