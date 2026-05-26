# -*- coding: utf-8 -*-
"""Recovery truth timeline — proven send/reply gating."""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from main import app
from models import RecoveryTruthTimelineEvent
from schema_recovery_truth_timeline import (
    ensure_recovery_truth_timeline_schema,
    reset_recovery_truth_timeline_schema_guard_for_tests,
)
from services.merchant_cart_row_classifier import classify_merchant_cart_row
from services.recovery_truth_timeline_v1 import (
    STATUS_CUSTOMER_REPLY,
    STATUS_DELAY_STARTED,
    STATUS_PROVIDER_QUEUED,
    STATUS_PROVIDER_SENT,
    STATUS_SCHEDULED,
    get_recovery_truth_timeline,
    provider_send_proven,
    record_recovery_truth_event,
)


class RecoveryTruthTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()

    def setUp(self) -> None:
        db.create_all()
        ensure_recovery_truth_timeline_schema(db)
        self._suffix = uuid.uuid4().hex[:8]

    def tearDown(self) -> None:
        try:
            db.session.query(RecoveryTruthTimelineEvent).filter(
                RecoveryTruthTimelineEvent.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_timeline_order_and_dedupe(self) -> None:
        rk = f"demo:s_{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_SCHEDULED,
            source="test",
            store_slug="demo",
            session_id=f"s_{self._suffix}",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_SCHEDULED,
            source="test_dup",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_DELAY_STARTED,
            source="test",
            store_slug="demo",
        )
        tl = get_recovery_truth_timeline(rk)
        self.assertEqual(len(tl), 2)
        self.assertEqual(tl[0]["status"], STATUS_SCHEDULED)
        self.assertEqual(tl[1]["status"], STATUS_DELAY_STARTED)
        self.assertIn("timestamp", tl[0])

    def test_provider_send_not_proven_on_queued_only(self) -> None:
        rk = f"demo:q_{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_QUEUED,
            source="test",
            store_slug="demo",
        )
        self.assertFalse(
            provider_send_proven(rk, log_statuses=frozenset({"queued"}), sent_count=0)
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        self.assertTrue(provider_send_proven(rk, log_statuses=frozenset({"queued"})))

    def test_classifier_sent_requires_provider_sent(self) -> None:
        rk = f"demo:c_{self._suffix}"
        cl = classify_merchant_cart_row(
            sent_count=0,
            log_statuses=frozenset({"queued"}),
            coarse="sent",
            recovery_key=rk,
        )
        self.assertEqual(cl.primary_bucket, "waiting")
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        cl2 = classify_merchant_cart_row(
            sent_count=1,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            recovery_key=rk,
        )
        self.assertEqual(cl2.primary_bucket, "sent")

    def test_dev_recovery_truth_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        rk = f"demo:api_{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
            session_id=f"api_{self._suffix}",
        )
        client = TestClient(app)
        r = client.get(f"/dev/recovery-truth?recovery_key={rk}")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        self.assertEqual(len(body.get("timeline") or []), 1)
        self.assertEqual(body["timeline"][0]["status"], STATUS_CUSTOMER_REPLY)


if __name__ == "__main__":
    unittest.main()
