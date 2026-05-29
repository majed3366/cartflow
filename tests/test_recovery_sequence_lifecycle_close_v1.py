# -*- coding: utf-8 -*-
"""Lifecycle closes after final recovery send + post-sequence engagement window."""

from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from extensions import db
from services.customer_lifecycle_states_v1 import (
    LABEL_AR,
    STATE_COMPLETED,
    STATE_CUSTOMER_REPLY,
    STATE_RECOVERY_FOLLOWUP_COMPLETE,
    STATE_WAITING_CUSTOMER_REPLY,
    STATE_WAITING_PURCHASE_WINDOW,
    classify_customer_lifecycle_state_v1,
)
from services.recovery_truth_timeline_v1 import (
    STATUS_CUSTOMER_REPLY,
    STATUS_PROVIDER_SENT,
    record_recovery_truth_event,
)


class RecoverySequenceLifecycleCloseTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:8]
        self._now = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)
        self._last_sent = self._now - timedelta(hours=72)

    @patch("services.customer_lifecycle_states_v1._utc_now")
    @patch(
        "services.normal_recovery_merchant_view_config.post_recovery_sequence_engagement_wait_minutes",
        return_value=60,
    )
    def test_scenario_d_window_expired_closes_lifecycle(
        self, _wait_min: int, mock_now
    ) -> None:
        mock_now.return_value = self._now
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=f"demo:seq-d-{self._suffix}",
            sent_count=3,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent", "skipped_attempt_limit"}),
            coarse="sent",
            last_provider_sent_at=self._last_sent.isoformat(),
        )
        self.assertEqual(lc.state_key, STATE_RECOVERY_FOLLOWUP_COMPLETE)
        self.assertEqual(lc.label_ar, LABEL_AR[STATE_RECOVERY_FOLLOWUP_COMPLETE])
        self.assertIn("لم يحدث تفاعل", lc.what_happened_ar)
        self.assertIn("أكمل CartFlow", lc.system_did_ar)
        self.assertIn("لا توجد إجراءات", lc.what_next_ar)
        self.assertNotIn("بانتظار تفاعل العميل", lc.label_ar)

    @patch("services.customer_lifecycle_states_v1._utc_now")
    @patch(
        "services.normal_recovery_merchant_view_config.post_recovery_sequence_engagement_wait_minutes",
        return_value=10080,
    )
    def test_scenario_d_still_waiting_during_window(
        self, _wait_min: int, mock_now
    ) -> None:
        mock_now.return_value = self._now
        recent = self._now - timedelta(minutes=30)
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=f"demo:seq-wait-{self._suffix}",
            sent_count=3,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent"}),
            coarse="sent",
            last_provider_sent_at=recent.isoformat(),
        )
        self.assertEqual(lc.state_key, STATE_WAITING_CUSTOMER_REPLY)
        self.assertEqual(lc.label_ar, LABEL_AR[STATE_WAITING_CUSTOMER_REPLY])

    @patch("services.customer_lifecycle_states_v1._utc_now")
    @patch(
        "services.normal_recovery_merchant_view_config.post_recovery_sequence_engagement_wait_minutes",
        return_value=60,
    )
    def test_scenario_a_purchase_wins_over_window(self, _wait_min: int, mock_now) -> None:
        mock_now.return_value = self._now
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=f"demo:seq-buy-{self._suffix}",
            sent_count=3,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent", "stopped_converted"}),
            coarse="converted",
            purchase_truth=True,
            last_provider_sent_at=self._last_sent.isoformat(),
        )
        self.assertEqual(lc.state_key, STATE_COMPLETED)
        self.assertEqual(lc.label_ar, "تم الشراء")

    @patch("services.customer_lifecycle_states_v1._utc_now")
    @patch(
        "services.normal_recovery_merchant_view_config.post_recovery_sequence_engagement_wait_minutes",
        return_value=60,
    )
    def test_scenario_b_reply_wins_over_window(self, _wait_min: int, mock_now) -> None:
        mock_now.return_value = self._now
        rk = f"demo:seq-reply-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_CUSTOMER_REPLY,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            sent_count=3,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent"}),
            coarse="replied",
            behavioral={"customer_replied": True},
            last_provider_sent_at=self._last_sent.isoformat(),
        )
        self.assertEqual(lc.state_key, STATE_CUSTOMER_REPLY)

    @patch("services.customer_lifecycle_states_v1._utc_now")
    @patch(
        "services.normal_recovery_merchant_view_config.post_recovery_sequence_engagement_wait_minutes",
        return_value=60,
    )
    def test_scenario_c_return_wins_over_window(self, _wait_min: int, mock_now) -> None:
        mock_now.return_value = self._now
        rk = f"demo:seq-ret-{self._suffix}"
        record_recovery_truth_event(
            recovery_key=rk,
            status=STATUS_PROVIDER_SENT,
            source="test",
            store_slug="demo",
        )
        lc = classify_customer_lifecycle_state_v1(
            recovery_key=rk,
            phase_key="customer_returned",
            coarse="returned",
            sent_count=3,
            attempt_cap=3,
            log_statuses=frozenset({"mock_sent", "returned_to_site"}),
            behavioral={"user_returned_to_site": True},
            last_provider_sent_at=self._last_sent.isoformat(),
        )
        self.assertEqual(lc.state_key, STATE_WAITING_PURCHASE_WINDOW)
        self.assertNotEqual(lc.state_key, STATE_RECOVERY_FOLLOWUP_COMPLETE)


if __name__ == "__main__":
    unittest.main()
