# -*- coding: utf-8 -*-
"""
Cart recovery sequence behavior (API-level; mirrors manual /demo/store/cart flows).

Test 1: single decision-engine recovery message per abandon.
Test 2: duplicate cart_abandoned does not re-send.
Test 3: demo vs demo2 isolation (separate keys / sends).
Test 4: conversion during first send; stopped_converted logged for tail step.
Test 5: GET /dev/recovery-logs/{store_slug} shape (ENV=development).
"""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

import main
from main import app
from extensions import db
from models import CartRecoveryLog
from tests.test_recovery_isolation import _reset_recovery_memory


def _abandon(store: str, session_id: str) -> object:
    return {
        "event": "cart_abandoned",
        "store": store,
        "session_id": session_id,
        "cart": [{"name": "Item", "price": 10}],
    }


class CartRecoverySequenceBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(app)

    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_1_normal_sequence_three_steps_once(
        self, _d: object, _ur: object, mock_send: object, _p: object
    ) -> None:
        """One recovery message per scheduled run; no duplicate sends."""
        mock_send.return_value = {"ok": True}
        r = self.client.post(
            "/api/cart-event",
            json=_abandon("demo", "seq-normal-1"),
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(1, mock_send.call_count)
        msgs = [c[0][1] for c in mock_send.call_args_list]
        self.assertEqual(len(msgs), len(set(msgs)), "duplicate message text")
        for m in msgs:
            self.assertIsInstance(m, str)
            self.assertTrue(len(m) > 0)

    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_2_duplicate_protection_no_resend(
        self, _d: object, _ur: object, mock_send: object, _p: object
    ) -> None:
        """Multiple abandons for same session: only one send when first run completes."""
        mock_send.return_value = {"ok": True}
        body = _abandon("demo", "seq-dup-1")
        self.assertTrue(self.client.post("/api/cart-event", json=body).json()["recovery_scheduled"])
        self.assertEqual(1, mock_send.call_count)
        r2 = self.client.post("/api/cart-event", json=body).json()
        self.assertEqual("sent", r2.get("recovery_state"), "sequence already completed")
        self.assertEqual(1, mock_send.call_count, "no extra sends on duplicate post")
        r3 = self.client.post("/api/cart-event", json=body).json()
        self.assertEqual(1, mock_send.call_count, "still no extra sends")

    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_3_store_isolation_demo_and_demo2(
        self, _d: object, _ur: object, mock_send: object, _p: object
    ) -> None:
        """demo and demo2: separate recovery; one send each, 2 total."""
        mock_send.return_value = {"ok": True}
        sid = "shared-sid-iso"
        r1 = self.client.post(
            "/api/cart-event",
            json=_abandon("demo", sid),
        )
        r2 = self.client.post(
            "/api/cart-event",
            json=_abandon("demo2", sid),
        )
        self.assertTrue(r1.json().get("recovery_scheduled"))
        self.assertTrue(r2.json().get("recovery_scheduled"))
        self.assertEqual(2, mock_send.call_count)
        # keys differ
        self.assertNotEqual(
            main._recovery_key_from_payload(_abandon("demo", sid)),
            main._recovery_key_from_payload(_abandon("demo2", sid)),
        )

    @patch("main._persist_cart_recovery_log")
    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_4_conversion_stops_after_step1(
        self, _d: object, _ur: object, mock_send: object, mock_persist: object
    ) -> None:
        """After first mock send, conversion → tail step logged as stopped_converted."""
        states: list[str] = []

        def on_persist(*_a, **kw) -> None:
            st = kw.get("status", "")
            if st:
                states.append(st)

        mock_persist.side_effect = on_persist

        _n = [0]

        def after_step1(phone: str, message: str) -> dict:
            _n[0] += 1
            if _n[0] == 1:
                main._mark_session_converted("demo", "conv-mid-1")
            return {"ok": True}

        mock_send.side_effect = after_step1
        r = self.client.post(
            "/api/cart-event",
            json=_abandon("demo", "conv-mid-1"),
        )
        self.assertEqual(200, r.status_code)
        self.assertEqual(1, mock_send.call_count, "only step1 mock send")
        self.assertIn("stopped_converted", states)
        self.assertIn("mock_sent", states)

    @patch("main.send_whatsapp")
    @patch("main.recovery_uses_real_whatsapp", return_value=False)
    @patch("main.recovery_delay_to_seconds", return_value=0.0)
    def test_5_dev_recovery_logs_includes_fields(
        self, _d: object, _ur: object, _mock_wa: object
    ) -> None:
        """GET /dev/recovery-logs/{store_slug} includes step, status, message, timestamps."""
        _mock_wa.return_value = {"ok": True}
        _reset_recovery_memory()
        old = os.environ.get("ENV")
        os.environ["ENV"] = "development"
        try:
            db.create_all()
            if "sqlite" in (str(getattr(db, "engine", None).url) or ""):
                try:
                    with db.engine.begin() as conn:
                        conn.execute(
                            text(
                                "ALTER TABLE cart_recovery_logs "
                                "ADD COLUMN step INTEGER"
                            )
                        )
                except Exception:  # noqa: BLE001
                    pass
            try:
                db.session.query(CartRecoveryLog).delete()
                db.session.commit()
            except (OSError, Exception):
                db.session.rollback()
            row = CartRecoveryLog(
                store_slug="demo",
                session_id="log-check-1",
                cart_id=None,
                phone=None,
                message="test row",
                status="mock_sent",
                step=2,
                created_at=datetime.now(timezone.utc),
                sent_at=datetime.now(timezone.utc),
            )
            db.session.add(row)
            db.session.commit()

            r = self.client.get("/dev/recovery-logs/demo")
            self.assertEqual(200, r.status_code, r.text)
            data = r.json()
            self.assertTrue(data.get("ok"))
            self.assertEqual("demo", data.get("store_slug"))
            self.assertIsInstance(data.get("logs"), list)
            self.assertTrue(len(data["logs"]) >= 1)
            first = data["logs"][0]
            for k in ("step", "status", "message", "created_at", "sent_at", "id"):
                self.assertIn(k, first, first)
        finally:
            if old is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = old
            try:
                db.session.rollback()
            except (OSError, Exception):
                pass

    def test_demo_store_page_exists(self) -> None:
        """Demo cart: /demo/cart, /demo/store, /demo/store/cart, /demo/store2/cart include cart + CTA."""
        for path in ("/demo/cart", "/demo/store", "/demo/store/cart", "/demo/store2/cart"):
            r = self.client.get(path)
            self.assertEqual(200, r.status_code, path)
            self.assertIn(b"window.cart", r.content)
            self.assertIn(b"cf-store-intro-cta", r.content)
            self.assertIn(b"cartflow_demo_panel.js", r.content)
        r0 = self.client.get("/demo/cart")
        t = r0.text or ""
        self.assertIn("CARTFLOW_DEMO_CART_KEY", t)
        self.assertIn("هودي قطني مريح", t)
        self.assertIn("warranty_info", t)
        self.assertIn("CF_DEMO_PRODUCTS", t)
        self.assertIn("ابدأ التجربة", t)
        self.assertIn("إعادة التجربة", t)


if __name__ == "__main__":
    unittest.main()
