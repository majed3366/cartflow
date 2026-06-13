# -*- coding: utf-8 -*-
"""Recovery schedule materialization v1 — cart_state_sync + reason path."""

from __future__ import annotations

import asyncio
import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, RecoverySchedule, Store
from services.customer_lifecycle_states_v1 import (
    LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    attach_customer_lifecycle_state_v1,
)
from services.recovery_db_due_scanner import scan_due_recovery_schedules
from services.recovery_restart_survival import STATUS_SCHEDULED
from services.recovery_schedule_materialization_v1 import SCHEDULE_BLOCKED_MISSING_PHONE
from tests.test_recovery_isolation import _reset_recovery_memory

_NORMAL_PHONE = "9665444555666"


def _price_templates_json() -> str:
    return json.dumps(
        {
            "price": {
                "enabled": True,
                "message": "رسالة 1",
                "message_count": 3,
                "messages": [
                    {"delay": 0, "unit": "minutes", "text": "رسالة 1"},
                    {"delay": 1, "unit": "minutes", "text": "رسالة 2"},
                    {"delay": 2, "unit": "minutes", "text": "رسالة 3"},
                ],
            }
        }
    )


def _cart_state_sync_payload(
    store: str,
    session_id: str,
    cart_id: str,
    *,
    cart_total: float = 500.0,
) -> dict:
    return {
        "event": "cart_state_sync",
        "reason": "add",
        "store": store,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart_total": cart_total,
        "items_count": 1,
        "cart": [{"name": "Item", "price": cart_total, "quantity": 1}],
    }


def _reason_payload(
    store: str,
    session_id: str,
    cart_id: str,
    *,
    phone: str | None = _NORMAL_PHONE,
) -> dict:
    body = {
        "store_slug": store,
        "session_id": session_id,
        "reason": "price",
        "sub_category": "price_discount_request",
        "cart_id": cart_id,
    }
    if phone:
        body["customer_phone"] = phone
    return body


class RecoveryScheduleMaterializationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        db.create_all()
        self.client = TestClient(app)
        self.suffix = uuid.uuid4().hex[:12]

    def tearDown(self) -> None:
        try:
            pat = f"%{self.suffix}%"
            db.session.query(RecoverySchedule).filter(
                RecoverySchedule.session_id.like(pat)
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(pat)
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(pat)
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.recovery_session_id.like(pat)
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"%{self.suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _ensure_store(self, slug: str) -> Store:
        st = Store(
            zid_store_id=slug,
            recovery_delay=0,
            recovery_delay_unit="minutes",
            recovery_attempts=3,
            vip_cart_threshold=15000,
            reason_templates_json=_price_templates_json(),
            whatsapp_recovery_enabled=True,
        )
        db.session.add(st)
        db.session.commit()
        return st

    @patch("main.asyncio.create_task")
    @patch("main.get_recovery_delay", return_value=0)
    def test_cart_state_sync_reason_phone_creates_schedule(
        self, _delay: object, _ct: object
    ) -> None:
        slug = f"mat-sync-{self.suffix}"
        sid = f"s-sync-{self.suffix}"
        cid = f"cf_cart_{self.suffix}"
        self._ensure_store(slug)

        r_sync = self.client.post(
            "/api/cart-event",
            json=_cart_state_sync_payload(slug, sid, cid),
        )
        self.assertEqual(r_sync.status_code, 200, r_sync.text)
        self.assertTrue(r_sync.json().get("cart_state_sync"))

        r_reason = self.client.post(
            "/api/cartflow/reason",
            json=_reason_payload(slug, sid, cid),
        )
        self.assertEqual(r_reason.status_code, 200, r_reason.text)
        self.assertTrue(r_reason.json().get("ok"))

        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.recovery_session_id == sid)
            .first()
        )
        self.assertIsNotNone(ac)

        schedules = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .all()
        )
        self.assertGreaterEqual(len(schedules), 1)
        self.assertEqual(
            (schedules[0].status or "").strip().lower(),
            STATUS_SCHEDULED,
        )

    @patch("main.asyncio.create_task")
    @patch("main.get_recovery_delay", return_value=0)
    def test_cart_state_sync_reason_missing_phone_blocks_schedule(
        self, _delay: object, _ct: object
    ) -> None:
        slug = f"mat-nophone-{self.suffix}"
        sid = f"s-nophone-{self.suffix}"
        cid = f"cf_cart_np_{self.suffix}"
        self._ensure_store(slug)

        self.client.post(
            "/api/cart-event",
            json=_cart_state_sync_payload(slug, sid, cid),
        )
        self.client.post(
            "/api/cartflow/reason",
            json=_reason_payload(slug, sid, cid, phone=None),
        )

        n_sched = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .count()
        )
        self.assertEqual(0, n_sched)

        logs = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.session_id == sid)
            .all()
        )
        statuses = {(getattr(lg, "status", None) or "").strip() for lg in logs}
        self.assertIn(SCHEDULE_BLOCKED_MISSING_PHONE, statuses)

    @patch("main.asyncio.create_task")
    @patch("main.get_recovery_delay", return_value=0)
    def test_legacy_abandon_waiting_reason_still_arms(
        self, _delay: object, _ct: object
    ) -> None:
        slug = f"mat-legacy-{self.suffix}"
        sid = f"s-legacy-{self.suffix}"
        cid = f"cf_cart_leg_{self.suffix}"
        self._ensure_store(slug)

        abandon = {
            "event": "cart_abandoned",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 120.0,
            "cart": [{"name": "Item", "price": 120, "quantity": 1}],
        }
        j1 = self.client.post("/api/cart-event", json=abandon).json()
        self.assertEqual("waiting_for_reason", j1.get("recovery_state"))

        self.client.post(
            "/api/cartflow/reason",
            json=_reason_payload(slug, sid, cid),
        )

        n_sched = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .count()
        )
        self.assertGreaterEqual(n_sched, 1)

    @patch("main.asyncio.create_task")
    @patch("main.get_recovery_delay", return_value=0)
    def test_repeated_reason_post_no_duplicate_schedule(
        self, _delay: object, _ct: object
    ) -> None:
        slug = f"mat-dup-{self.suffix}"
        sid = f"s-dup-{self.suffix}"
        cid = f"cf_cart_dup_{self.suffix}"
        self._ensure_store(slug)

        self.client.post(
            "/api/cart-event",
            json=_cart_state_sync_payload(slug, sid, cid),
        )
        payload = _reason_payload(slug, sid, cid)
        self.client.post("/api/cartflow/reason", json=payload)
        self.client.post("/api/cartflow/reason", json=payload)

        n_sched = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.session_id == sid,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .count()
        )
        self.assertGreaterEqual(n_sched, 1)
        first_count = n_sched
        self.client.post("/api/cartflow/reason", json=payload)
        n_sched_after = (
            db.session.query(RecoverySchedule)
            .filter(
                RecoverySchedule.session_id == sid,
                RecoverySchedule.status == STATUS_SCHEDULED,
            )
            .count()
        )
        self.assertEqual(first_count, n_sched_after)

    @patch("main.asyncio.create_task")
    @patch("main.get_recovery_delay", return_value=0)
    def test_scanner_finds_due_schedule_after_materialization(
        self, _delay: object, _ct: object
    ) -> None:
        from unittest.mock import AsyncMock

        slug = f"mat-scan-{self.suffix}"
        sid = f"s-scan-{self.suffix}"
        cid = f"cf_cart_scan_{self.suffix}"
        self._ensure_store(slug)

        self.client.post(
            "/api/cart-event",
            json=_cart_state_sync_payload(slug, sid, cid),
        )
        self.client.post(
            "/api/cartflow/reason",
            json=_reason_payload(slug, sid, cid),
        )

        rows = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.session_id == sid)
            .all()
        )
        self.assertGreaterEqual(len(rows), 1)
        for row in rows:
            row.due_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.session.commit()

        with patch(
            "main._run_recovery_sequence_after_cart_abandoned",
            new_callable=AsyncMock,
            return_value=None,
        ):
            out = asyncio.run(
                scan_due_recovery_schedules(limit=20, source="test_mat_v1")
            )
        self.assertGreaterEqual(int(out.get("found") or 0), 1)

    def test_dashboard_no_next_send_line_without_schedule(self) -> None:
        rk = f"demo:s-dash-{self.suffix}"
        out: dict = {}
        attach_customer_lifecycle_state_v1(
            out,
            recovery_key=rk,
            phase_key="pending_send",
            coarse="pending",
            sent_count=0,
            attempt_cap=3,
            log_statuses=frozenset({SCHEDULE_BLOCKED_MISSING_PHONE}),
            has_phone=False,
            schedule_prefetched=True,
            effective_delay_seconds_prefetched=None,
        )
        self.assertEqual(
            out.get("merchant_status_label_ar"),
            LABEL_WAITING_CONTACT_COMPLETION_AR,
        )
        followup = str(out.get("customer_lifecycle_next_followup_line_ar") or "")
        self.assertNotIn("الإرسال الأول", followup)

        out2: dict = {}
        attach_customer_lifecycle_state_v1(
            out2,
            recovery_key=rk,
            phase_key="pending_send",
            coarse="pending",
            sent_count=0,
            attempt_cap=3,
            log_statuses=frozenset(),
            has_phone=True,
            schedule_prefetched=True,
            effective_delay_seconds_prefetched=None,
        )
        self.assertEqual(
            out2.get("merchant_status_label_ar"),
            LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
        )
        self.assertNotIn(
            "الإرسال الأول",
            str(out2.get("customer_lifecycle_next_followup_line_ar") or ""),
        )


if __name__ == "__main__":
    unittest.main()
