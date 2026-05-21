# -*- coding: utf-8 -*-
"""Reliability Program v1 — restart survival for delayed recoveries."""
from __future__ import annotations

import json
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main
from extensions import db
from models import CartRecoveryLog, RecoverySchedule, Store
from services.recovery_restart_survival import (
    STATUS_COMPLETED,
    STATUS_FAILED_RESUME,
    STATUS_FAILED_RESUME_STALE,
    STATUS_RUNNING,
    STATUS_SCHEDULED,
    STATUS_SKIPPED_DUPLICATE,
    STATUS_SKIPPED_RESUME,
    _execute_resume_recovery_task,
    dev_verify_recovery_restart_survival,
    evaluate_resume_safety,
    inspect_persistence_state,
    persist_recovery_schedule_durable,
    repair_stale_running_recovery_schedules,
    reconcile_stale_running_schedules,
    resume_one_schedule,
    rearm_one_future_scheduled_recovery,
    run_recovery_resume_scan_sync,
)
from services.recovery_session_phone import recovery_phone_memory_clear


class RecoveryRestartSurvivalTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "0"
        db.create_all()
        main._ensure_store_widget_schema()
        recovery_phone_memory_clear()
        for row in db.session.query(RecoverySchedule).all():
            db.session.delete(row)
        for row in db.session.query(Store).filter_by(zid_store_id="demo").all():
            db.session.delete(row)
        db.session.commit()
        db.session.add(
            Store(
                zid_store_id="demo",
                recovery_delay=2,
                recovery_delay_unit="minutes",
                recovery_attempts=1,
            )
        )
        db.session.commit()

    def _demo_store(self) -> Store:
        z = f"demo-rst-{uuid.uuid4().hex[:8]}"
        for row in db.session.query(Store).filter_by(zid_store_id=z).all():
            db.session.delete(row)
        st = Store(
            zid_store_id=z,
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            reason_templates_json=json.dumps(
                {
                    "other": {
                        "enabled": True,
                        "message": "x",
                        "message_count": 1,
                        "messages": [{"delay": 1, "unit": "minute", "text": "x"}],
                    }
                }
            ),
        )
        db.session.add(st)
        db.session.commit()
        return st

    def _rk(self, tag: str) -> str:
        return f"demo:sess-{tag}-{uuid.uuid4().hex[:6]}"

    def test_persist_durable_schedule_discoverable(self) -> None:
        rk = self._rk("persist")
        timing = {
            "effective_delay_seconds": 60.0,
            "source": "reason_templates.messages",
            "reason_tag": "other",
            "stage": 1,
        }
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-persist",
            cart_id="cart-p1",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=60.0,
            schedule_timing=timing,
            recovery_context={"recovery_key": rk, "store_slug": "demo"},
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.status, STATUS_SCHEDULED)
        self.assertEqual(float(row.effective_delay_seconds), 60.0)
        snap = inspect_persistence_state()
        self.assertGreaterEqual(snap.get("total_rows", 0), 1)
        found = dev_verify_recovery_restart_survival(action="find", recovery_key=rk)
        self.assertGreaterEqual(len(found.get("rows", [])), 1)

    def test_scenario_a_due_after_restart_discoverable(self) -> None:
        """Schedule 1m — simulate restart — resume scan finds due row."""
        rk = self._rk("a")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-a",
            cart_id="cart-a",
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
        row.due_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.session.commit()
        recovery_phone_memory_clear()
        scan = run_recovery_resume_scan_sync(max_dispatch=10, dry_run=True, force=True)
        self.assertTrue(scan.get("enabled"))
        self.assertGreaterEqual(scan.get("due_processed", 0), 1)
        keys = [o.get("recovery_key") for o in scan.get("outcomes", [])]
        self.assertIn(rk, keys)

    def test_future_scheduled_rearms_dispatcher_without_early_execute(self) -> None:
        """Post-restart: future-due row re-arms delay dispatch; no immediate execution."""
        rk = self._rk("future-rearm")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-future",
            cart_id="cart-future",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=120.0,
            schedule_timing={
                "effective_delay_seconds": 120.0,
                "source": "reason_templates.messages",
            },
            recovery_context={"recovery_key": rk, "store_slug": "demo"},
        )
        assert row is not None
        due = datetime.now(timezone.utc) + timedelta(seconds=90)
        row.due_at = due
        db.session.commit()
        with patch(
            "services.recovery_delay_dispatcher.spawn_recovery_schedule_dispatch"
        ) as mock_spawn:
            with patch(
                "services.recovery_restart_survival.resume_one_schedule",
                new_callable=AsyncMock,
            ) as mock_resume:
                scan = run_recovery_resume_scan_sync(
                    max_dispatch=10, dry_run=False, force=True
                )
        self.assertGreaterEqual(scan.get("future_processed", 0), 1)
        self.assertGreaterEqual(scan.get("future_rearmed", 0), 1)
        mock_resume.assert_not_called()
        mock_spawn.assert_called()
        call = mock_spawn.call_args
        self.assertEqual(int(call[0][0]), int(row.id))
        self.assertEqual(call[0][2], "resume_scan_future_rearm")
        db.session.expire_all()
        row_f = db.session.get(RecoverySchedule, int(row.id))
        assert row_f is not None
        self.assertEqual(row_f.status, STATUS_SCHEDULED)

    def test_scenario_b_purchase_blocks_resume(self) -> None:
        rk = self._rk("b")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-b",
            cart_id="cart-b",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=1.0,
            schedule_timing={"effective_delay_seconds": 1.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        with main._recovery_session_lock:
            main._session_recovery_converted[rk] = True
        ok, reason = evaluate_resume_safety(row)
        self.assertFalse(ok)
        self.assertEqual(reason, "purchase_completed")

    def test_scenario_c_returned_blocks_resume(self) -> None:
        rk = self._rk("c")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-c",
            cart_id="cart-c",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=1.0,
            schedule_timing={"effective_delay_seconds": 1.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        with main._recovery_session_lock:
            main._session_recovery_returned[rk] = True
        ok, reason = evaluate_resume_safety(row)
        self.assertFalse(ok)
        self.assertEqual(reason, "user_returned")

    def test_scenario_d_duplicate_resume_claim(self) -> None:
        st = self._demo_store()
        rk = f"{st.zid_store_id}:sess-d-{uuid.uuid4().hex[:6]}"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug=st.zid_store_id,
            session_id="sess-d",
            cart_id="cart-d",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=1.0,
            schedule_timing={
                "effective_delay_seconds": 60.0,
                "source": "reason_templates.messages",
            },
            recovery_context={
                "recovery_key": rk,
                "store_slug": st.zid_store_id,
            },
        )
        assert row is not None
        row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

        import asyncio

        calls: list[str] = []

        def _fake_create_task(coro):  # noqa: ANN001
            calls.append("task")
            coro.close()
            return None

        with patch("asyncio.create_task", side_effect=_fake_create_task):
            asyncio.run(resume_one_schedule(row, dispatch=True))
            asyncio.run(resume_one_schedule(row, dispatch=True))
        self.assertEqual(len(calls), 1)

    def test_scenario_e_store_mismatch_blocked(self) -> None:
        rk = "demo:sess-e:abc"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="loadtest-store-020",
            session_id="sess-e",
            cart_id="cart-e",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={
                "effective_delay_seconds": 60.0,
                "source": "reason_templates.messages",
            },
            recovery_context={"recovery_key": rk, "store_slug": "loadtest-store-020"},
        )
        assert row is not None
        ok, reason = evaluate_resume_safety(row)
        self.assertFalse(ok)
        self.assertEqual(reason, "store_context_mismatch")

    def test_scenario_already_sent_blocks_resume(self) -> None:
        rk = self._rk("sent")
        sid = "sess-sent"
        cid = "cart-sent"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            cart_id=cid,
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=1.0,
            schedule_timing={"effective_delay_seconds": 1.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id=cid,
                phone="+966501112233",
                message="sent",
                status="sent_real",
                step=1,
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()
        ok, reason = evaluate_resume_safety(row)
        self.assertFalse(ok)
        self.assertEqual(reason, "already_sent")

    def test_dev_verify_endpoint_inspect(self) -> None:
        client = main._app_test_client()
        r = client.get("/dev/recovery-restart-survival-verify?action=inspect")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("persistence", body)
        self.assertEqual(body["persistence"].get("table"), "recovery_schedules")

    def test_resume_executor_finalizes_running_not_stuck(self) -> None:
        """Durable resume must not leave recovery_schedules.status=running after task exits."""
        import asyncio
        from unittest.mock import AsyncMock

        rk = self._rk("finalize")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-fin",
            cart_id="cart-fin",
            reason_tag="other",
            abandon_event_phone="+966501112233",
            delay_seconds_scheduled=0.0,
            schedule_timing={"effective_delay_seconds": 0.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk, "store_slug": "demo"},
        )
        assert row is not None
        row.status = STATUS_RUNNING
        row.due_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        with main._recovery_session_lock:
            main._session_recovery_logged[rk] = True

        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            asyncio.run(_execute_resume_recovery_task(row))

        rid = int(row.id)
        db.session.expire_all()
        again = (
            db.session.query(RecoverySchedule).filter(RecoverySchedule.id == rid).one()
        )
        self.assertNotEqual(again.status, STATUS_RUNNING)
        self.assertIn(
            again.status,
            (
                STATUS_COMPLETED,
                STATUS_SKIPPED_RESUME,
                STATUS_FAILED_RESUME,
                STATUS_FAILED_RESUME_STALE,
            ),
        )

    def test_stale_running_reconciled(self) -> None:
        rk = self._rk("stale")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-stale",
            cart_id="cart-stale",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        row.status = STATUS_RUNNING
        row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=900)
        db.session.commit()
        n = reconcile_stale_running_schedules(max_age_seconds=600)
        self.assertGreaterEqual(n, 1)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_FAILED_RESUME_STALE)

    def test_stale_running_finalized_when_mock_sent_evidence(self) -> None:
        rk = self._rk("stale-sent")
        sid = "sess-stale-sent"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            cart_id="cart-sent",
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
                cart_id="cart-sent",
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
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_COMPLETED)

    def test_stale_running_finalized_skipped_duplicate(self) -> None:
        rk = self._rk("stale-dup")
        sid = "sess-stale-dup"
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id=sid,
            cart_id="cart-dup",
            reason_tag="other",
            abandon_event_phone=None,
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
                cart_id="cart-dup",
                phone="+966501112233",
                message="dup",
                status="skipped_duplicate",
                step=1,
            )
        )
        db.session.commit()
        repair_stale_running_recovery_schedules(max_age_seconds=600)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_SKIPPED_DUPLICATE)

    def test_stale_running_not_repaired_when_fresh(self) -> None:
        rk = self._rk("fresh-run")
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="sess-fresh",
            cart_id="cart-fresh",
            reason_tag="other",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "reason_templates.messages"},
            recovery_context={"recovery_key": rk},
        )
        assert row is not None
        row.status = STATUS_RUNNING
        row.updated_at = datetime.now(timezone.utc) - timedelta(seconds=30)
        db.session.commit()
        out = repair_stale_running_recovery_schedules(max_age_seconds=600)
        self.assertEqual(out.get("stale_detected", 0), 0)
        db.session.refresh(row)
        self.assertEqual(row.status, STATUS_RUNNING)


if __name__ == "__main__":
    unittest.main()
