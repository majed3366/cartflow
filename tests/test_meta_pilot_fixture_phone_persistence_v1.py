# -*- coding: utf-8 -*-
"""Meta Pilot Fixture Phone Persistence V1 — durable phone via customer_phone."""
from __future__ import annotations

import json
import time
import unittest
import uuid
from datetime import datetime, timezone
from unittest import mock

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryReason, RecoverySchedule, Store
from schema_widget import ensure_store_widget_schema
from scripts.meta_pilot_fixture_v1 import (
    PILOT_PHONE_DIGITS,
    PILOT_PHONE_E164,
    build_abandon_payload,
    build_cartflow_reason_payload,
    evaluate_phone_persistence_ready,
)
from services.recovery_session_phone import recovery_phone_memory_clear
from tests.test_recovery_isolation import _reset_recovery_memory


def _ensure_demo_store() -> Store:
    ensure_store_widget_schema(db)
    db.create_all()
    st = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
    templates = {
        "other": {
            "enabled": True,
            "message": "msg",
            "message_count": 1,
            "messages": [{"delay": 60, "unit": "minutes", "text": "msg"}],
        }
    }
    tpl = json.dumps(templates, ensure_ascii=False)
    if st is None:
        st = Store(
            zid_store_id="demo",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            reason_templates_json=tpl,
            whatsapp_recovery_enabled=True,
        )
        db.session.add(st)
    else:
        st.reason_templates_json = tpl
        st.whatsapp_recovery_enabled = True
        db.session.add(st)
    db.session.commit()
    return st


class MetaPilotFixturePhonePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        recovery_phone_memory_clear()
        self.client = TestClient(app)
        self.store = _ensure_demo_store()
        self.token = uuid.uuid4().hex[:12]
        self.session_id = f"meta_fix_phone_{self.token}"
        self.cart_id = f"cf_cart_meta_fix_phone_{self.token}"
        self.rk = f"demo:{self.cart_id}"

    def tearDown(self) -> None:
        recovery_phone_memory_clear()
        _reset_recovery_memory()

    def _abandon_then_reason(self, *, use_cf_test_only: bool = False):
        ab = build_abandon_payload(session_id=self.session_id, cart_id=self.cart_id)
        r_ab = self.client.post("/api/cart-event", json=ab)
        self.assertEqual(200, r_ab.status_code, r_ab.text)

        if use_cf_test_only:
            body = {
                "store": "demo",
                "store_slug": "demo",
                "session_id": self.session_id,
                "cart_id": self.cart_id,
                "reason": "other",
                "custom_text": "سبب اخر",
                "cf_test_phone": PILOT_PHONE_E164,
            }
        else:
            body = build_cartflow_reason_payload(
                session_id=self.session_id,
                cart_id=self.cart_id,
                customer_phone=PILOT_PHONE_E164,
            )

        # Suppress detached arm during request; run sync after response.
        with mock.patch("routes.cartflow._spawn_reason_recovery_arm_detached"):
            r_rs = self.client.post("/api/cartflow/reason", json=body)

        if r_rs.status_code == 200 and (r_rs.json() or {}).get("ok"):
            import asyncio

            from routes.cartflow import _arm_recovery_after_reason_saved_bg

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(
                    _arm_recovery_after_reason_saved_bg(
                        store_slug="demo",
                        session_id=self.session_id,
                        body=body,
                    )
                )
            finally:
                loop.close()
        return r_ab, r_rs

    def _wait_durable_phones(self, timeout: float = 10.0):
        deadline = time.time() + timeout
        crr = None
        ac = None
        while time.time() < deadline:
            db.session.expire_all()
            crr = (
                db.session.query(CartRecoveryReason)
                .filter(
                    CartRecoveryReason.store_slug == "demo",
                    CartRecoveryReason.session_id == self.session_id,
                )
                .order_by(CartRecoveryReason.id.desc())
                .first()
            )
            ac = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.zid_cart_id == self.cart_id)
                .order_by(AbandonedCart.id.desc())
                .first()
            )
            crr_ok = bool(crr and "".join(c for c in (crr.customer_phone or "") if c.isdigit()))
            ac_ok = bool(ac and "".join(c for c in (ac.customer_phone or "") if c.isdigit()))
            if crr_ok and ac_ok:
                return crr, ac
            time.sleep(0.25)
        return crr, ac

    def test_customer_phone_persists_durable_crr_and_ac(self) -> None:
        _ab, r_rs = self._abandon_then_reason()
        self.assertEqual(200, r_rs.status_code, r_rs.text)
        self.assertTrue(r_rs.json().get("ok"))

        crr, ac = self._wait_durable_phones()
        self.assertIsNotNone(crr)
        self.assertIsNotNone(ac)
        assert crr is not None and ac is not None
        self.assertEqual(
            "".join(c for c in (crr.customer_phone or "") if c.isdigit()),
            PILOT_PHONE_DIGITS,
        )
        self.assertEqual(
            "".join(c for c in (ac.customer_phone or "") if c.isdigit()),
            PILOT_PHONE_DIGITS,
        )

        sched = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.cart_id == self.cart_id)
            .order_by(RecoverySchedule.id.desc())
            .first()
        )
        self.assertIsNotNone(sched)
        assert sched is not None
        self.assertIsNotNone(sched.due_at)
        due = sched.due_at
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        self.assertGreater(due, datetime.now(timezone.utc))

        report = evaluate_phone_persistence_ready(
            recovery_key=self.rk,
            crr_phone=crr.customer_phone,
            ac_phone=ac.customer_phone,
            schedule_id=int(sched.id),
            schedule_recovery_key=getattr(sched, "recovery_key", None) or self.rk,
        )
        self.assertTrue(report["phone_persistence_ready"])

    def test_scheduler_process_resolves_phone_from_db_not_memory(self) -> None:
        _ab, r_rs = self._abandon_then_reason()
        self.assertEqual(200, r_rs.status_code, r_rs.text)
        crr, ac = self._wait_durable_phones()
        self.assertIsNotNone(ac)
        self.assertIsNotNone(crr)

        # Separate Scheduler process simulation: clear API in-memory phone cache
        recovery_phone_memory_clear()
        _reset_recovery_memory()

        from main import _resolve_cartflow_recovery_phone

        db.session.expire_all()
        store_row = db.session.query(Store).filter(Store.zid_store_id == "demo").first()
        crr_fresh = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == self.session_id,
            )
            .first()
        )
        phone, source, allowed = _resolve_cartflow_recovery_phone(
            store_slug="demo",
            session_id=self.session_id,
            cart_id=self.cart_id,
            store_obj=store_row,
            abandon_event_phone=None,
            recovery_key=self.rk,
            reason_row=crr_fresh,
        )
        digits = "".join(c for c in (phone or "") if c.isdigit())
        self.assertEqual(digits, PILOT_PHONE_DIGITS)
        self.assertTrue(allowed)
        self.assertNotEqual(source, "none")

    def test_cf_test_phone_only_on_cartflow_reason_does_not_falsely_pass(self) -> None:
        _ab, r_rs = self._abandon_then_reason(use_cf_test_only=True)
        self.assertEqual(200, r_rs.status_code, r_rs.text)
        time.sleep(1.5)
        db.session.expire_all()
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "demo",
                CartRecoveryReason.session_id == self.session_id,
            )
            .first()
        )
        if crr is not None:
            self.assertFalse(bool((crr.customer_phone or "").strip()))

        ac = (
            db.session.query(AbandonedCart)
            .filter(AbandonedCart.zid_cart_id == self.cart_id)
            .first()
        )
        ac_phone = getattr(ac, "customer_phone", None) if ac else None
        # May be null or empty — must not equal pilot digits via this path alone
        ac_digits = "".join(c for c in str(ac_phone or "") if c.isdigit())
        self.assertNotEqual(ac_digits, PILOT_PHONE_DIGITS)

        report = evaluate_phone_persistence_ready(
            recovery_key=self.rk,
            crr_phone=getattr(crr, "customer_phone", None) if crr else None,
            ac_phone=ac_phone,
            schedule_id=1,
        )
        self.assertFalse(report["phone_persistence_ready"])

    def test_fixture_uses_customer_phone_not_cf_test_phone(self) -> None:
        body = build_cartflow_reason_payload(session_id="s1", cart_id="c1")
        self.assertEqual(body["customer_phone"], PILOT_PHONE_E164)
        self.assertNotIn("cf_test_phone", body)
        ab = build_abandon_payload(session_id="s1", cart_id="c1")
        self.assertNotIn("cf_test_phone", ab)
        self.assertNotIn("customer_phone", ab)

    def test_no_manual_abandoned_cart_phone_write_in_fixture(self) -> None:
        import inspect

        import scripts.meta_pilot_fixture_v1 as mod

        src = inspect.getsource(mod)
        self.assertNotIn("AbandonedCart(", src)
        self.assertNotIn(".customer_phone =", src)


if __name__ == "__main__":
    unittest.main()
