# -*- coding: utf-8 -*-
"""Queue-ready recovery execution boundary."""
from __future__ import annotations

import asyncio
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from extensions import db
from models import RecoverySchedule
from services.recovery_execution_boundary import (
    execute_recovery_schedule,
    resolve_recovery_schedule_row,
)
from services.recovery_restart_survival import (
    STATUS_COMPLETED,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    claim_recovery_schedule_execution,
    persist_recovery_schedule_durable,
)


class RecoveryExecutionBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        for row in db.session.query(RecoverySchedule).all():
            db.session.delete(row)
        db.session.commit()

    def _row(self, tag: str) -> RecoverySchedule:
        rk = f"demo:exec-{tag}-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-exec",
            cart_id="cart-exec",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=60.0,
            schedule_timing={
                "effective_delay_seconds": 60.0,
                "source": "reason_templates.messages",
            },
            recovery_context={"recovery_key": rk, "store_slug": "demo"},
        )
        assert row is not None
        return row

    def test_resolve_by_schedule_id(self) -> None:
        row = self._row("resolve")
        found = resolve_recovery_schedule_row(schedule_id=int(row.id))
        self.assertIsNotNone(found)
        self.assertEqual(int(found.id), int(row.id))

    def test_skips_terminal_schedule(self) -> None:
        row = self._row("terminal")
        row.status = STATUS_COMPLETED
        db.session.commit()
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
        ) as mock_run:
            out = asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="test")
            )
        self.assertFalse(out["ok"])
        self.assertIn("already_terminal", out["reason"])
        mock_run.assert_not_called()

    def test_claims_and_runs_post_delay(self) -> None:
        row = self._row("run")
        self.assertEqual(row.status, STATUS_SCHEDULED)
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_run:
            out = asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="test")
            )
        self.assertTrue(out["ok"])
        mock_run.assert_called_once()
        _args, kwargs = mock_run.call_args
        rc = kwargs.get("recovery_context") or {}
        self.assertTrue(rc.get("recovery_post_delay_only"))
        self.assertTrue(rc.get("schedule_execution_claimed"))
        again = resolve_recovery_schedule_row(schedule_id=int(row.id))
        assert again is not None
        self.assertNotEqual(again.status, STATUS_RUNNING)

    def test_second_execute_skipped_after_claim(self) -> None:
        row = self._row("dup")
        self.assertTrue(
            claim_recovery_schedule_execution(
                recovery_key=row.recovery_key,
                row_id=int(row.id),
                path="arm",
            )[0]
        )
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
        ) as mock_run:
            out = asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="test")
            )
        self.assertFalse(out["ok"])
        self.assertEqual(out["reason"], "already_running")
        mock_run.assert_not_called()
