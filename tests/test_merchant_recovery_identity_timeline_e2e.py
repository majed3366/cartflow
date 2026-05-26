# -*- coding: utf-8 -*-
"""Merchant recovery identity through schedule + delay_started timeline."""
from __future__ import annotations

import os
import unittest
import uuid
from unittest.mock import patch

from extensions import db
from main import app
from models import RecoverySchedule, RecoveryTruthTimelineEvent
from schema_recovery_truth_timeline import (
    ensure_recovery_truth_timeline_schema,
    reset_recovery_truth_timeline_schema_guard_for_tests,
)
from services.recovery_restart_survival import (
    persist_recovery_schedule_durable,
    reconcile_schedule_row_identity,
)
from services.recovery_store_context import reconcile_recovery_identity
from services.recovery_truth_timeline_v1 import (
    STATUS_DELAY_STARTED,
    STATUS_SCHEDULED,
    get_recovery_truth_timeline,
)


class MerchantRecoveryIdentityTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        reset_recovery_truth_timeline_schema_guard_for_tests()

    def setUp(self) -> None:
        os.environ["ENV"] = "development"
        self._suffix = uuid.uuid4().hex[:10]
        self.merchant_slug = f"mwt-id-{self._suffix}"
        self.session_id = f"s_{self._suffix}"
        db.create_all()
        ensure_recovery_truth_timeline_schema(db)

    def tearDown(self) -> None:
        try:
            db.session.query(RecoveryTruthTimelineEvent).filter(
                RecoveryTruthTimelineEvent.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.recovery_key.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_reconcile_identity_rewrites_demo_prefix(self) -> None:
        rk, slug, sid = reconcile_recovery_identity(
            recovery_key=f"demo:{self.session_id}",
            store_slug=self.merchant_slug,
            session_id=self.session_id,
            recovery_context={
                "store_slug": self.merchant_slug,
                "recovery_key": f"demo:{self.session_id}",
            },
        )
        self.assertEqual(slug, self.merchant_slug)
        self.assertEqual(sid, self.session_id)
        self.assertEqual(rk, f"{self.merchant_slug}:{self.session_id}")

    def test_persist_schedule_and_dispatch_use_merchant_recovery_key(self) -> None:
        demo_rk = f"demo:{self.session_id}"
        merchant_rk = f"{self.merchant_slug}:{self.session_id}"
        rc = {
            "store_slug": self.merchant_slug,
            "session_id": self.session_id,
            "recovery_key": merchant_rk,
        }
        row = persist_recovery_schedule_durable(
            recovery_key=demo_rk,
            store_slug=self.merchant_slug,
            session_id=self.session_id,
            cart_id=f"cf_{self._suffix}",
            reason_tag="shipping",
            abandon_event_phone=None,
            delay_seconds_scheduled=120.0,
            schedule_timing={"effective_delay_seconds": 120.0, "source": "test"},
            recovery_context=rc,
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.recovery_key, merchant_rk)
        self.assertEqual(row.store_slug, self.merchant_slug)

        tl_sched = get_recovery_truth_timeline(merchant_rk)
        statuses = [e["status"] for e in tl_sched]
        self.assertIn(STATUS_SCHEDULED, statuses)

        rk2, _, _ = reconcile_schedule_row_identity(row)
        self.assertEqual(rk2, merchant_rk)

        import asyncio

        from services.recovery_delay_dispatcher import dispatch_recovery_schedule

        async def _noop_sleep(_s: float) -> None:
            return None

        async def _noop_exec(**_: object) -> dict:
            return {"ok": True, "reason": "test_skip_exec"}

        async def _run() -> None:
            with patch(
                "services.recovery_delay_dispatcher._delay_sleep",
                new=_noop_sleep,
            ):
                with patch(
                    "services.recovery_delay_dispatcher.execute_recovery_schedule",
                    new=_noop_exec,
                ):
                    await dispatch_recovery_schedule(
                        int(row.id),
                        row.due_at,
                        "test_identity",
                    )

        asyncio.run(_run())

        tl = get_recovery_truth_timeline(merchant_rk)
        st_set = {e["status"] for e in tl}
        self.assertIn(STATUS_SCHEDULED, st_set)
        self.assertIn(STATUS_DELAY_STARTED, st_set)
        for ev in tl:
            self.assertTrue(str(ev.get("recovery_key") or "").startswith(self.merchant_slug))

    def test_dev_recovery_truth_merchant_key_after_schedule(self) -> None:
        merchant_rk = f"{self.merchant_slug}:{self.session_id}"
        persist_recovery_schedule_durable(
            recovery_key=f"demo:{self.session_id}",
            store_slug=self.merchant_slug,
            session_id=self.session_id,
            cart_id=None,
            reason_tag="shipping",
            abandon_event_phone=None,
            delay_seconds_scheduled=60.0,
            schedule_timing={"effective_delay_seconds": 60.0, "source": "test"},
            recovery_context={"store_slug": self.merchant_slug, "recovery_key": merchant_rk},
        )
        from fastapi.testclient import TestClient

        client = TestClient(app)
        r = client.get(f"/dev/recovery-truth?recovery_key={merchant_rk}")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertTrue(body.get("ok"))
        statuses = [e.get("status") for e in body.get("timeline") or []]
        self.assertIn(STATUS_SCHEDULED, statuses)


if __name__ == "__main__":
    unittest.main()
