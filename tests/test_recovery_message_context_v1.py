# -*- coding: utf-8 -*-
"""Recovery message context v1 — cart/message truth alignment."""
from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone

from extensions import db, init_database
from models import AbandonedCart, CartRecoveryLog, Store
from schema_recovery_message_context import (
    ensure_recovery_message_context_schema,
    reset_recovery_message_context_schema_guard_for_tests,
)
from services.merchant_recovery_lifecycle_truth import (
    attach_merchant_recovery_lifecycle_truth,
    build_merchant_recovery_lifecycle_truth,
)
from services.recovery_message_context_v1 import (
    CONTEXT_MISSING,
    CONTEXT_OK,
    LEGACY_CONTEXT_MISSING,
    build_recovery_message_context,
    build_recovery_message_truth_debug,
    classify_context_linkage,
    context_from_log_row,
    derive_carts_page_status,
    derive_messages_page_status,
    detect_truth_mismatch,
    enrich_cart_row_truth_fields,
)


class RecoveryMessageContextV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        init_database("sqlite:///:memory:")
        db.create_all()
        ensure_recovery_message_context_schema(db)

    def setUp(self) -> None:
        reset_recovery_message_context_schema_guard_for_tests()
        ensure_recovery_message_context_schema(db)
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        try:
            db.session.query(CartRecoveryLog).filter(
                CartRecoveryLog.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(AbandonedCart).filter(
                AbandonedCart.zid_cart_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_classify_context_missing_without_cart_and_session(self) -> None:
        st = classify_context_linkage(
            recovery_key="demo:only",
            store_slug="demo",
            session_id="",
            cart_id="",
        )
        self.assertEqual(st, CONTEXT_MISSING)

    def test_classify_context_ok_with_session(self) -> None:
        st = classify_context_linkage(
            recovery_key="demo:s1",
            store_slug="demo",
            session_id="s1",
            cart_id="",
        )
        self.assertEqual(st, CONTEXT_OK)

    def test_persist_context_on_log_row(self) -> None:
        sid = f"s-ctx-{self._suffix}"
        zid = f"c-ctx-{self._suffix}"
        ctx = build_recovery_message_context(
            recovery_key=f"demo:{sid}",
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            customer_phone="966501112233",
            reason_tag="price",
            message_body="رسالة مرتبطة بالسلة",
            message_type="reason_template",
            attempt=1,
            send_status="mock_sent",
            source="test",
        )
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            phone="966501112233",
            message=ctx.message_body,
            status="mock_sent",
            step=1,
            recovery_key=ctx.recovery_key,
            reason_tag=ctx.reason_tag,
            context_status=ctx.context_status,
            context_json=json.dumps(ctx.to_dict(), ensure_ascii=False),
            message_type=ctx.message_type,
            source=ctx.source,
            sent_at=datetime.now(timezone.utc),
        )
        db.session.add(lg)
        db.session.commit()
        loaded = context_from_log_row(lg)
        self.assertEqual(loaded.get("recovery_key"), ctx.recovery_key)
        self.assertEqual(loaded.get("cart_id"), zid)
        self.assertEqual(loaded.get("context_status"), CONTEXT_OK)

    def test_sent_message_agrees_messages_and_carts_pages(self) -> None:
        sid = f"s-agree-{self._suffix}"
        zid = f"c-agree-{self._suffix}"
        ac = AbandonedCart(
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            customer_phone="966501112233",
            cart_value=120.0,
        )
        db.session.add(ac)
        db.session.flush()
        sent_at = datetime.now(timezone.utc)
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            phone="966501112233",
            message="مرحباً — سلة بقيمة 120",
            status="mock_sent",
            step=1,
            recovery_key=f"demo:{sid}",
            reason_tag="price",
            context_status=CONTEXT_OK,
            context_json=json.dumps(
                {
                    "recovery_key": f"demo:{sid}",
                    "store_slug": "demo",
                    "session_id": sid,
                    "cart_id": zid,
                    "message_body": "مرحباً — سلة بقيمة 120",
                    "reason_tag": "price",
                    "context_status": CONTEXT_OK,
                },
                ensure_ascii=False,
            ),
            sent_at=sent_at,
        )
        db.session.add(lg)
        db.session.commit()
        truth = build_merchant_recovery_lifecycle_truth(
            ac=ac,
            phase_key="first_message_sent",
            coarse="sent",
            sent_ct=1,
            log_statuses=frozenset({"mock_sent"}),
            behavioral={},
            reason_tag="price",
            has_phone=True,
            latest_log=lg,
            matched_logs=[lg],
            store_slug="demo",
        )
        self.assertEqual(truth["whatsapp_status"], "sent")
        self.assertEqual(truth.get("messages_page_status"), "sent")
        self.assertEqual(truth.get("carts_page_status"), "sent")
        self.assertFalse(truth.get("truth_mismatch_detected"))
        self.assertIn("مرحباً", truth.get("message_preview") or "")

    def test_context_missing_detected(self) -> None:
        mp = derive_messages_page_status(
            "mock_sent", context_status=CONTEXT_MISSING
        )
        cp = derive_carts_page_status(
            phase_key="pending_send",
            coarse="pending",
            sent_ct=0,
            log_status="mock_sent",
            context_status=CONTEXT_MISSING,
        )
        mismatch, reason = detect_truth_mismatch(
            messages_page_status=mp,
            carts_page_status=cp,
            log_status="mock_sent",
            context_status=CONTEXT_MISSING,
        )
        self.assertTrue(mismatch)
        self.assertEqual(reason, "message_missing_cart_context")

    def test_legacy_context_without_json(self) -> None:
        sid = f"s-leg-{self._suffix}"
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=f"c-leg-{self._suffix}",
            message="قديم",
            status="mock_sent",
            recovery_key=f"demo:{sid}",
        )
        db.session.add(lg)
        db.session.commit()
        ctx = context_from_log_row(lg)
        self.assertEqual(ctx.get("context_status"), LEGACY_CONTEXT_MISSING)

    def test_truth_debug_endpoint_payload_shape(self) -> None:
        sid = f"s-dbg-{self._suffix}"
        zid = f"c-dbg-{self._suffix}"
        rk = f"demo:{sid}"
        ac = AbandonedCart(
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
        )
        db.session.add(ac)
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            message="dbg",
            status="mock_sent",
            recovery_key=rk,
            context_status=CONTEXT_OK,
        )
        db.session.add(lg)
        db.session.commit()
        store = Store(zid_store_id="demo")
        dbg = build_recovery_message_truth_debug(rk, dash_store=store)
        self.assertEqual(dbg["recovery_key"], rk)
        self.assertTrue(dbg["cart_recovery_logs"])
        self.assertFalse(dbg["mismatch_detected"])

    def test_generic_fallback_message_type(self) -> None:
        ctx = build_recovery_message_context(
            recovery_key="demo:s-fb",
            store_slug="demo",
            session_id="s-fb",
            cart_id="c-fb",
            reason_tag="",
            message_body="",
            store=None,
        )
        self.assertIn(ctx.message_type, ("generic_fallback", "explicit", "reason_fallback"))


if __name__ == "__main__":
    unittest.main()
