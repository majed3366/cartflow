# -*- coding: utf-8 -*-
"""WhatsApp recovery send idempotency — DB/log based."""
from __future__ import annotations

import io
import unittest
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timezone

from extensions import db
from models import CartRecoveryLog
from services.recovery_whatsapp_idempotency import (
    check_whatsapp_recovery_send_idempotency,
    find_existing_whatsapp_recovery_send,
)


class RecoveryWhatsappIdempotencyTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        for row in db.session.query(CartRecoveryLog).all():
            db.session.delete(row)
        db.session.commit()

    def test_miss_then_hit_after_mock_sent(self) -> None:
        rk = f"demo:sess-{uuid.uuid4().hex[:6]}"
        buf = io.StringIO()
        with redirect_stdout(buf):
            dup, st, _ = check_whatsapp_recovery_send_idempotency(
                recovery_key=rk,
                step=1,
                reason_tag="other",
                customer_phone="+966501112233",
                store_slug="demo",
                session_id=rk.split(":", 1)[1],
                cart_id="cart-1",
            )
        self.assertFalse(dup)
        self.assertIn("[WA IDEMPOTENCY MISS]", buf.getvalue())

        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=rk.split(":", 1)[1],
                cart_id="cart-1",
                phone="+966501112233",
                message="hi",
                status="mock_sent",
                step=1,
                sent_at=datetime.now(timezone.utc),
            )
        )
        db.session.commit()

        buf2 = io.StringIO()
        with redirect_stdout(buf2):
            dup2, st2, _ = check_whatsapp_recovery_send_idempotency(
                recovery_key=rk,
                step=1,
                reason_tag="other",
                customer_phone="+966501112233",
                store_slug="demo",
                session_id=rk.split(":", 1)[1],
                cart_id="cart-1",
            )
        self.assertTrue(dup2)
        self.assertEqual(st2, "mock_sent")
        self.assertIn("[WA IDEMPOTENCY HIT]", buf2.getvalue())

    def test_whatsapp_failed_does_not_block(self) -> None:
        rk = f"demo:sess-{uuid.uuid4().hex[:6]}"
        sid = rk.split(":", 1)[1]
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id="cart-f",
                phone="+966501112233",
                message="hi",
                status="whatsapp_failed",
                step=1,
            )
        )
        db.session.commit()
        dup, _, _ = check_whatsapp_recovery_send_idempotency(
            recovery_key=rk,
            step=1,
            customer_phone="+966501112233",
            store_slug="demo",
            session_id=sid,
            cart_id="cart-f",
        )
        self.assertFalse(dup)

    def test_queued_blocks_retry(self) -> None:
        rk = f"demo:sess-{uuid.uuid4().hex[:6]}"
        sid = rk.split(":", 1)[1]
        db.session.add(
            CartRecoveryLog(
                store_slug="demo",
                session_id=sid,
                cart_id="cart-q",
                phone="+966501112233",
                message="hi",
                status="queued",
                step=1,
            )
        )
        db.session.commit()
        row = find_existing_whatsapp_recovery_send(
            {
                "recovery_key": rk,
                "store_slug": "demo",
                "session_id": sid,
                "cart_id": "cart-q",
                "step": 1,
                "customer_phone_digits": "966501112233",
            }
        )
        self.assertIsNotNone(row)
        dup, st, _ = check_whatsapp_recovery_send_idempotency(
            recovery_key=rk,
            step=1,
            customer_phone="+966501112233",
            store_slug="demo",
            session_id=sid,
            cart_id="cart-q",
        )
        self.assertTrue(dup)
        self.assertEqual(st, "queued")


if __name__ == "__main__":
    unittest.main()
