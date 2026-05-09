# -*- coding: utf-8 -*-
"""
Integration-style operational checks: recovery paths, identifiers, deduplication.

These tests use patching for timing/WhatsApp where needed; they do not change product code.
"""
from __future__ import annotations

import asyncio
import contextlib
import io
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import func

import main
from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, CartRecoveryReason, Store
from services.behavioral_recovery.state_store import behavioral_dict_for_abandoned_cart
from services.recovery_session_phone import recovery_key_for_reason_session
from tests.operational.diagnostics import build_operational_diagnostics_snapshot
from tests.test_recovery_isolation import _reset_recovery_memory

_PHONE_OK = "9665444555666"


def _abandon(store: str, session_id: str, cart_id: str) -> dict:
    return {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart_id": cart_id,
        "cart": [{"name": "Item", "price": 10}],
        "phone": _PHONE_OK,
    }


class OperationalRecoveryIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        db.create_all()
        try:
            main._ensure_store_widget_schema()
        except Exception:  # noqa: BLE001
            db.session.rollback()
        self._suffix = uuid.uuid4().hex[:10]
        self.client = TestClient(app)

    def tearDown(self) -> None:
        _reset_recovery_memory()
        try:
            sfx = self._suffix
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{sfx}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(Store.zid_store_id.like(f"%{sfx}%")).delete(
                synchronize_session=False
            )
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _seed_store_cart_reason(
        self,
        *,
        slug: str,
        sid: str,
        cid: str,
        with_phone: bool,
    ) -> None:
        st = Store(
            zid_store_id=slug,
            vip_cart_threshold=999999,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=cid,
            recovery_session_id=sid,
            cart_value=25.0,
            status="abandoned",
            vip_mode=False,
        )
        db.session.add(ac)
        db.session.commit()

        r = self.client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": slug,
                "session_id": sid,
                "reason_tag": "price",
                **({"phone": _PHONE_OK} if with_phone else {}),
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        aged = datetime.now(timezone.utc) - timedelta(hours=3)
        db.session.query(CartRecoveryReason).filter_by(
            store_slug=slug, session_id=sid
        ).update(
            {"updated_at": aged, "created_at": aged},
            synchronize_session=False,
        )
        db.session.commit()

    def test_recovery_key_matches_between_cart_event_and_reason_session(self) -> None:
        slug = f"op_key_{self._suffix}"
        sid = f"op_sid_{self._suffix}"
        cid = f"op_cid_{self._suffix}"
        rk_payload = main._recovery_key_from_payload(
            {"store": slug, "session_id": sid, "cart_id": cid}
        )
        rk_reason = recovery_key_for_reason_session(slug, sid)
        self.assertEqual(rk_payload, rk_reason)

    def test_delayed_recovery_sequence_logs_skip_when_phone_missing(self) -> None:
        slug = f"op_np_{self._suffix}"
        sid = f"op_sid_{self._suffix}"
        cid = f"op_cid_{self._suffix}"
        self._seed_store_cart_reason(slug=slug, sid=sid, cid=cid, with_phone=False)
        recovery_key = f"{slug}:{sid}"

        async def _run() -> None:
            await main._run_recovery_sequence_after_cart_abandoned_impl(
                recovery_key,
                0.0,
                slug,
                sid,
                cid,
                None,
            )

        with patch.object(main.asyncio, "sleep", new_callable=AsyncMock):
            asyncio.run(_run())

        st_logs = [
            row.status
            for row in db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.session_id == sid)
            .all()
        ]
        self.assertIn("skipped_no_verified_phone", st_logs)

    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    @patch("main.should_send_whatsapp", return_value=True)
    def test_whatsapp_failure_recorded_without_raise(
        self, _ss: object, _gd: object, _ur: object, mock_send: object
    ) -> None:
        mock_send.return_value = {"ok": False, "error": "operational_forced_fail"}
        slug = f"op_wf_{self._suffix}"
        sid = f"op_sid_{self._suffix}"
        cid = f"op_cid_{self._suffix}"
        self._seed_store_cart_reason(slug=slug, sid=sid, cid=cid, with_phone=True)

        r = self.client.post("/api/cart-event", json=_abandon(slug, sid, cid))
        self.assertEqual(r.status_code, 200, r.text)

        st_logs = [
            row.status
            for row in db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.session_id == sid)
            .all()
        ]
        self.assertIn("whatsapp_failed", st_logs)

    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.get_recovery_delay", return_value=0)
    def test_user_returned_suppresses_whatsapp_send(
        self, _gd: object, _ur: object, mock_send: object
    ) -> None:
        mock_send.return_value = {"ok": True}
        slug = f"op_rt_{self._suffix}"
        sid = f"op_sid_{self._suffix}"
        cid = f"op_cid_{self._suffix}"
        self._seed_store_cart_reason(slug=slug, sid=sid, cid=cid, with_phone=True)
        main._mark_user_returned_for_payload({"store": slug, "session_id": sid})

        r = self.client.post("/api/cart-event", json=_abandon(slug, sid, cid))
        self.assertEqual(r.status_code, 200, r.text)
        mock_send.assert_not_called()
        st_blocked = (
            db.session.query(CartRecoveryLog)
            .filter(
                CartRecoveryLog.session_id == sid,
                CartRecoveryLog.status == "skipped_delay_gate",
            )
            .first()
        )
        self.assertIsNotNone(st_blocked)

    def test_duplicate_cart_state_sync_single_abandoned_row(self) -> None:
        slug = f"op_sync_{self._suffix}"
        sid = f"op_sid_{self._suffix}"
        cid = f"op_cid_{self._suffix}"
        st = Store(
            zid_store_id=slug,
            vip_cart_threshold=500,
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.commit()
        body = {
            "event": "cart_state_sync",
            "reason": "page_load",
            "store": slug,
            "session_id": sid,
            "cart_id": cid,
            "cart_total": 120.0,
            "items_count": 1,
            "cart": [{"price": 120.0, "quantity": 1}],
        }
        r1 = self.client.post("/api/cart-event", json=body)
        r2 = self.client.post("/api/cart-event", json=body)
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        n = (
            db.session.query(func.count(AbandonedCart.id))
            .filter(AbandonedCart.zid_cart_id == cid)
            .scalar()
        )
        self.assertEqual(int(n or 0), 1)


class OperationalPhoneResolutionLogTests(unittest.TestCase):
    def test_phone_resolution_log_emits_banner(self) -> None:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main._log_phone_resolution(
                store_id="1",
                store_slug="demo",
                session_id="s1",
                cart_id="c1",
                source="cf_test_phone",
                phone="966511122233",
                allowed_to_send=True,
            )
        out = buf.getvalue()
        self.assertIn("[PHONE RESOLUTION]", out)
        self.assertIn("source=", out)


class OperationalDiagnosticsHelperTests(unittest.TestCase):
    def test_diagnostics_snapshot_shape(self) -> None:
        snap = build_operational_diagnostics_snapshot()
        self.assertIn("runtime_status", snap)
        self.assertIn("duplicate_send_guard", snap)
        self.assertIn("phone_resolution", snap)
        self.assertIn("started_len", snap["duplicate_send_guard"])
        self.assertIn("duplicate_guard_operational", snap)
        self.assertIn("counters", snap["duplicate_guard_operational"])


class OperationalBehavioralRobustnessTests(unittest.TestCase):
    def test_corrupt_raw_payload_does_not_break_behavioral_read(self) -> None:
        ac = AbandonedCart()
        ac.raw_payload = "{ not json"
        self.assertEqual(behavioral_dict_for_abandoned_cart(ac), {})


class OperationalScalingDocumentationTests(unittest.TestCase):
    def test_delay_scheduling_uses_inline_async_task_documented(self) -> None:
        """
        Current limitation (by design in this repo): scheduled delay work is driven via
        asyncio tasks in the web process (see asyncio.create_task around recovery dispatch),
        not a separate queue worker for the countdown itself. WhatsApp may still queue
        separately when real mode is enabled.
        """
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(root, "main.py"), encoding="utf-8", errors="replace") as f:
            src = f.read()
        self.assertIn("asyncio.create_task", src)
        self.assertIn("_run_recovery_dispatch_cart_abandoned", src)
