# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from services.merchant_followup_clarity_v1 import build_merchant_followup_clarity_fields


class _FakeSchedule:
    def __init__(self, status: str, due_at: datetime) -> None:
        self.status = status
        self.due_at = due_at


class MerchantFollowupClarityTests(unittest.TestCase):
    def test_progress_one_of_two(self) -> None:
        f = build_merchant_followup_clarity_fields(
            sent_count=1, configured_count=2
        )
        self.assertEqual(f["merchant_followup_progress_ar"], "تم إرسال ١ من ٢")
        self.assertIsNone(f["merchant_followup_sequence_line_ar"])

    def test_progress_and_sequence_when_complete(self) -> None:
        f = build_merchant_followup_clarity_fields(
            sent_count=2, configured_count=2
        )
        self.assertEqual(f["merchant_followup_progress_ar"], "تم إرسال ٢ من ٢")
        self.assertEqual(
            f["merchant_followup_sequence_line_ar"],
            "اكتملت سلسلة المتابعة — بانتظار تفاعل العميل",
        )
        self.assertIsNone(f["merchant_followup_next_line_ar"])

    def test_next_line_when_followup_scheduled(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        due = now + timedelta(minutes=45)
        f = build_merchant_followup_clarity_fields(
            sent_count=1,
            configured_count=2,
            next_attempt_due_at=due.isoformat(),
            now=now,
        )
        self.assertEqual(f["merchant_followup_progress_ar"], "تم إرسال ١ من ٢")
        self.assertIsNone(f["merchant_followup_sequence_line_ar"])
        self.assertEqual(
            f["merchant_followup_next_line_ar"],
            "الرسالة التالية خلال ٤٥ دقيقة",
        )

    def test_next_from_recovery_schedule_rows(self) -> None:
        now = datetime(2026, 5, 28, 12, 0, tzinfo=timezone.utc)
        due = now + timedelta(hours=2)
        f = build_merchant_followup_clarity_fields(
            sent_count=1,
            configured_count=3,
            schedule_rows=[_FakeSchedule("scheduled", due)],
            now=now,
        )
        self.assertIn("الرسالة التالية خلال", f["merchant_followup_next_line_ar"] or "")
        self.assertIn("ساعتين", f["merchant_followup_next_line_ar"] or "")

    def test_no_lines_before_first_send(self) -> None:
        f = build_merchant_followup_clarity_fields(
            sent_count=0, configured_count=2
        )
        self.assertIsNone(f["merchant_followup_progress_ar"])

    def test_no_lines_when_purchased(self) -> None:
        f = build_merchant_followup_clarity_fields(
            sent_count=2,
            configured_count=2,
            purchased=True,
        )
        self.assertIsNone(f["merchant_followup_progress_ar"])


if __name__ == "__main__":
    unittest.main()
