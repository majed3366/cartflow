# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import main
from extensions import db
from main import app
from services.recovery_attempt2_trace_v1 import build_attempt2_trace
from services.recovery_restart_survival import (
    STATUS_SCHEDULED,
    persist_recovery_schedule_durable,
)
from tests.test_recovery_isolation import _reset_recovery_memory


class RecoveryAttempt2TraceTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    def test_dev_endpoint_requires_recovery_key(self) -> None:
        r = self.client.get("/dev/attempt-2-trace")
        self.assertEqual(400, r.status_code)

    def test_trace_reports_attempt2_schedule_row(self) -> None:
        db.create_all()
        rk = "demo:trace-a2-1"
        due = datetime.now(timezone.utc) + timedelta(minutes=4)
        row = persist_recovery_schedule_durable(
            recovery_key=rk,
            store_slug="demo",
            session_id="trace-a2-1",
            cart_id="cart-t",
            reason_tag="price",
            abandon_event_phone="966501112223",
            delay_seconds_scheduled=240.0,
            schedule_timing={
                "effective_delay_seconds": 240.0,
                "source": "reason_templates.messages.multi",
                "stage": 2,
            },
            recovery_context={
                "recovery_key": rk,
                "configured_message_count": 2,
                "reason_tag": "price",
            },
            multi_slot_index=2,
            multi_message_text="ثانية",
        )
        self.assertIsNotNone(row)
        trace = build_attempt2_trace(rk)
        self.assertTrue(trace["schedule_row_exists"])
        self.assertEqual(STATUS_SCHEDULED, trace["schedule_status"])
        self.assertEqual(2, trace["attempt_index"])
        self.assertFalse(trace["due_now"])
        self.assertEqual("waiting_due", trace["decision"])

    def test_trace_sent_attempt2_when_log_exists(self) -> None:
        db.create_all()
        rk = "demo:trace-a2-sent"
        sid = "trace-a2-sent"
        main._persist_cart_recovery_log(
            store_slug="demo",
            session_id=sid,
            cart_id="c1",
            phone="966501112223",
            message="msg",
            status="mock_sent",
            step=2,
        )
        trace = build_attempt2_trace(rk)
        self.assertTrue(trace["step2_sent_in_logs"])
        self.assertEqual("sent_attempt_2", trace["decision"])

    def test_runtime_configured_count_in_context(self) -> None:
        db.create_all()
        st = main._load_store_row_for_recovery("demo")
        self.assertIsNotNone(st)
        prev_tpl = getattr(st, "reason_templates_json", None)
        st.reason_templates_json = json.dumps(
            {
                "price": {
                    "enabled": True,
                    "message": "أساسية",
                    "message_count": 2,
                    "messages": [
                        {"delay": 4, "unit": "minute", "text": "أولى"},
                        {"delay": 4, "unit": "minute", "text": "ثانية"},
                    ],
                }
            }
        )
        db.session.commit()
        try:
            ctx = main._build_recovery_context_from_arm(
                store_slug="demo",
                store_row=st,
                session_id="trace-ctx",
                cart_id=None,
                recovery_key="demo:trace-ctx",
                reason_tag="price",
                abandon_event_phone=None,
            )
            self.assertEqual(2, int(ctx.get("configured_message_count") or 0))
        finally:
            st2 = main._load_store_row_for_recovery("demo")
            if st2 is not None:
                st2.reason_templates_json = prev_tpl
                db.session.commit()


if __name__ == "__main__":
    unittest.main()
