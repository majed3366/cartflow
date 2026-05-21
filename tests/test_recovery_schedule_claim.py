# -*- coding: utf-8 -*-
"""DB claim gate for recovery_schedules — single execution ownership."""
from __future__ import annotations

import unittest
import uuid

from extensions import db
from models import RecoverySchedule
from services.recovery_restart_survival import (
    STATUS_COMPLETED,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_DUPLICATE,
    claim_recovery_schedule_execution,
    finalize_recovery_schedule_durable,
    persist_recovery_schedule_durable,
)


class RecoveryScheduleClaimTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        for row in db.session.query(RecoverySchedule).all():
            db.session.delete(row)
        db.session.commit()

    def _row(self, tag: str) -> RecoverySchedule:
        rk = f"demo:claim-{tag}-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-claim",
            cart_id="cart-claim",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        return row

    def test_claim_scheduled_to_running(self) -> None:
        row = self._row("ok")
        claimed, reason, out = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key,
            path="test",
        )
        self.assertTrue(claimed, reason)
        self.assertIsNotNone(out)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_RUNNING)

    def test_second_claim_skipped(self) -> None:
        row = self._row("race")
        self.assertTrue(
            claim_recovery_schedule_execution(
                recovery_key=row.recovery_key, path="first"
            )[0]
        )
        claimed2, reason2, _ = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key, path="second"
        )
        self.assertFalse(claimed2)
        self.assertEqual(reason2, "already_running")

    def test_terminal_not_claimable(self) -> None:
        row = self._row("done")
        self.assertTrue(
            claim_recovery_schedule_execution(
                recovery_key=row.recovery_key, path="arm"
            )[0]
        )
        finalize_recovery_schedule_durable(
            row.recovery_key, status=STATUS_COMPLETED
        )
        db.session.refresh(row)
        claimed, reason, _ = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key, path="after_complete"
        )
        self.assertFalse(claimed)
        self.assertTrue(reason.startswith("already_terminal:"))

    def test_terminal_no_overwrite_completed(self) -> None:
        row = self._row("protect")
        self.assertTrue(
            claim_recovery_schedule_execution(
                recovery_key=row.recovery_key, path="arm"
            )[0]
        )
        finalize_recovery_schedule_durable(
            row.recovery_key, status=STATUS_COMPLETED
        )
        ok = finalize_recovery_schedule_durable(
            row.recovery_key,
            status=STATUS_SKIPPED_DUPLICATE,
            detail="should_not_apply",
        )
        self.assertFalse(ok)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_COMPLETED)

    def test_finalize_from_running(self) -> None:
        row = self._row("fin")
        claim_recovery_schedule_execution(recovery_key=row.recovery_key, path="t")
        ok = finalize_recovery_schedule_durable(
            row.recovery_key,
            status=STATUS_SKIPPED_DUPLICATE,
            detail="skipped_duplicate",
        )
        self.assertTrue(ok)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_SKIPPED_DUPLICATE)

    def test_accept_already_running_for_resume_reentry(self) -> None:
        row = self._row("reentry")
        row.status = STATUS_RUNNING
        db.session.commit()
        claimed, reason, _ = claim_recovery_schedule_execution(
            recovery_key=row.recovery_key,
            path="resume_delay_task",
            accept_already_running=True,
        )
        self.assertTrue(claimed)
        self.assertEqual(reason, "already_running_holder")


if __name__ == "__main__":
    unittest.main()
