# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timezone

from extensions import db
from models import AbandonedCart, CartRecoveryLog, Store
from services.merchant_recovery_lifecycle_truth import build_merchant_recovery_lifecycle_truth


class MerchantRecoveryLifecycleTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        self._suffix = uuid.uuid4().hex[:12]

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

    def test_sent_message_preview_and_time(self) -> None:
        sid = f"sid-mlt-{self._suffix}"
        zid = f"zid-mlt-{self._suffix}"
        ac = AbandonedCart(
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            customer_phone="966501112233",
            cart_value=50.0,
        )
        db.session.add(ac)
        db.session.flush()
        sent_at = datetime.now(timezone.utc)
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            phone="966501112233",
            message="مرحباً، لاحظنا اهتمامك بالسلة",
            status="mock_sent",
            step=1,
            created_at=sent_at,
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
            reason_tag="quality",
            has_phone=True,
            latest_log=lg,
            matched_logs=[lg],
        )
        self.assertEqual(truth["whatsapp_status"], "sent")
        self.assertIn("تم إرسال الرسالة", truth["merchant_whatsapp_line_ar"])
        self.assertIn("مرحباً", truth["message_preview"] or "")
        self.assertTrue(truth["customer_phone_present"])

    def test_returned_to_site_copy(self) -> None:
        sid = f"sid-ret-{self._suffix}"
        zid = f"zid-ret-{self._suffix}"
        raw = {"cf_behavioral": {"user_returned_to_site": True}}
        ac = AbandonedCart(
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            raw_payload=json.dumps(raw, ensure_ascii=False),
            cart_value=30.0,
        )
        truth = build_merchant_recovery_lifecycle_truth(
            ac=ac,
            phase_key="customer_returned",
            coarse="returned",
            sent_ct=0,
            log_statuses=frozenset(),
            behavioral=raw["cf_behavioral"],
            reason_tag="price",
            has_phone=True,
            latest_log=None,
            matched_logs=[],
        )
        self.assertTrue(truth["returned_to_site"])
        self.assertEqual(
            truth["merchant_return_line_ar"],
            "العميل عاد للموقع — أوقفنا الرسائل تلقائيًا.",
        )

    def test_purchased_copy(self) -> None:
        sid = f"sid-pur-{self._suffix}"
        zid = f"zid-pur-{self._suffix}"
        ac = AbandonedCart(
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="recovered",
            cart_value=80.0,
        )
        lg = CartRecoveryLog(
            store_slug="demo",
            session_id=sid,
            cart_id=zid,
            phone=None,
            message="x",
            status="stopped_converted",
            step=1,
            created_at=datetime.now(timezone.utc),
        )
        truth = build_merchant_recovery_lifecycle_truth(
            ac=ac,
            phase_key="stopped_purchase",
            coarse="stopped",
            sent_ct=1,
            log_statuses=frozenset({"stopped_converted", "mock_sent"}),
            behavioral={},
            reason_tag="quality",
            has_phone=True,
            latest_log=lg,
            matched_logs=[lg],
        )
        self.assertTrue(truth["purchased"])
        self.assertEqual(
            truth["merchant_purchase_line_ar"],
            "تمت عملية الشراء — انتهت مهمة الاسترجاع.",
        )
        self.assertEqual(truth["lifecycle_status"], "purchased")


if __name__ == "__main__":
    unittest.main()
