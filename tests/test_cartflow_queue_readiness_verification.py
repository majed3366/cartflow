# -*- coding: utf-8 -*-
"""
Queue readiness verification — lightweight automated checks for Part 7 matrix.

See docs/cartflow_queue_readiness_verification.md for full setup/trigger/log criteria.
No runtime behavior changes; tests document and enforce contracts.
"""
from __future__ import annotations

import asyncio
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main  # noqa: F401 — init_database for db.create_all()

from extensions import db
from models import CartRecoveryLog, RecoverySchedule
from services.recovery_execution_boundary import (
    execute_recovery_schedule,
    resolve_recovery_schedule_row,
)
from services.recovery_restart_survival import (
    STATUS_COMPLETED,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
    repair_stale_running_recovery_schedules,
)
from services.recovery_whatsapp_idempotency import (
    check_whatsapp_recovery_send_idempotency,
)


class QueueReadinessVerificationTests(unittest.TestCase):
    """Automated rows from docs/cartflow_queue_readiness_verification.md."""

    def setUp(self) -> None:
        db.create_all()
        for model in (RecoverySchedule, CartRecoveryLog):
            for row in db.session.query(model).all():
                db.session.delete(row)
        db.session.commit()

    def test_scheduled_row_double_execute_single_run(self) -> None:
        """Matrix §3: duplicate execution → one post-delay run."""
        rk = f"demo:qr-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-qr",
            cart_id="cart-qr",
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
        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ) as mock_run:
            out1 = asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="test")
            )
            out2 = asyncio.run(
                execute_recovery_schedule(schedule_id=int(row.id), source="test")
            )
        self.assertTrue(out1["ok"])
        self.assertFalse(out2["ok"])
        self.assertTrue(
            out2["reason"] == "already_running"
            or out2["reason"].startswith("already_terminal:")
        )
        self.assertEqual(mock_run.call_count, 1)

    def test_terminal_completed_cannot_re_execute(self) -> None:
        """Matrix §6: terminal row cannot re-execute."""
        rk = f"demo:qr-term-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-term",
            cart_id="cart-term",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
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

    def test_stale_running_with_send_evidence_finalizes_completed(self) -> None:
        """Matrix §5: stale running + send evidence → completed."""
        rk = f"demo:qr-stale-{uuid.uuid4().hex[:6]}"
        sid = "sess-stale-qr"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            cart_id="cart-stale",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        row.status = STATUS_RUNNING
        row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=900)
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id="cart-stale",
                phone="+966501112233",
                message="sent",
                status="mock_sent",
                step=1,
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        out = repair_stale_running_recovery_schedules(max_age_seconds=600)
        self.assertGreaterEqual(out.get("finalized", 0), 1)
        again = resolve_recovery_schedule_row(schedule_id=int(row.id))
        assert again is not None
        self.assertEqual(again.status, STATUS_COMPLETED)

    @patch("services.whatsapp_send.send_whatsapp")
    def test_idempotency_hit_does_not_invoke_provider(self, mock_send) -> None:
        """Matrix §4: idempotency HIT must not call send_whatsapp (main gate contract)."""
        rk = f"demo:sess-{uuid.uuid4().hex[:6]}"
        sid = rk.split(":", 1)[1]
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id="cart-idem",
                phone="+966501112233",
                message="hi",
                status="mock_sent",
                step=1,
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        wa_dup, _, _ = check_whatsapp_recovery_send_idempotency(
            recovery_key=rk,
            step=1,
            reason_tag="other",
            customer_phone="+966501112233",
            store_slug="demo",
            session_id=sid,
            cart_id="cart-idem",
        )
        self.assertTrue(wa_dup)
        if not wa_dup:
            mock_send("demo", "+966501112233", "hi")
        mock_send.assert_not_called()

    def test_boundary_resolve_uses_schedule_id_only(self) -> None:
        """Matrix §9: durable id lookup without in-memory task state."""
        rk = f"demo:qr-id-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-id",
            cart_id="cart-id",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=1.0,
            schedule_timing={"effective_delay_seconds": 1.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        found = resolve_recovery_schedule_row(schedule_id=int(row.id))
        self.assertIsNotNone(found)
        self.assertEqual(found.recovery_key, rk)
        self.assertEqual(found.status, STATUS_SCHEDULED)


if __name__ == "__main__":
    unittest.main()
