# -*- coding: utf-8 -*-
"""Merchant lifecycle keys on normal-recovery dashboard payload (behavior-first layer)."""
from __future__ import annotations

import json
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from extensions import db
from main import _normal_recovery_phase_steps_payload
from models import AbandonedCart, CartRecoveryLog, Store


class MerchantLifecyclePayloadTests(unittest.TestCase):
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
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"ml_{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def _store(self) -> Store:
        st = Store(
            zid_store_id=f"ml_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=2,
        )
        db.session.add(st)
        db.session.flush()
        return st

    def test_payload_includes_merchant_lifecycle_keys(self) -> None:
        st = self._store()
        zid = f"zid-ml-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=f"sid-ml-{self._suffix}",
            status="abandoned",
            vip_mode=False,
            cart_value=10.0,
        )
        db.session.add(ac)
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        for k in (
            "merchant_lifecycle_primary_key",
            "merchant_lifecycle_customer_behavior_ar",
            "merchant_lifecycle_system_outcome_ar",
            "merchant_lifecycle_next_action_ar",
            "merchant_lifecycle_internal",
        ):
            self.assertIn(k, p, msg=f"missing {k}")
        self.assertIsInstance(p.get("merchant_lifecycle_internal"), dict)

    def test_behavioral_return_duplicate_log_is_customer_returned_narrative(self) -> None:
        st = self._store()
        sid = f"sid-ml-dup-{self._suffix}"
        zid = f"zid-ml-dup-{self._suffix}"
        raw = {"cf_behavioral": {"user_returned_to_site": True}}
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=20.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="x",
                status="skipped_duplicate",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=None,
            )
        )
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(p.get("merchant_lifecycle_primary_key"), "customer_returned")
        self.assertIn("عاد", p.get("merchant_lifecycle_customer_behavior_ar") or "")
        self.assertIn("تلقائي", p.get("merchant_lifecycle_system_outcome_ar") or "")

    def test_queued_after_skipped_anti_spam_tail_still_customer_returned(self) -> None:
        """Regression: newest log queued must not hide skipped_anti_spam return signal."""
        st = self._store()
        sid = f"sid-ml-antiq-{self._suffix}"
        zid = f"zid-ml-antiq-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=15.0,
            customer_phone="9665111222333",
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=1)
        t2 = t0 + timedelta(seconds=2)
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone="9665111222333",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t0,
                sent_at=t0,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="spam",
                status="skipped_anti_spam",
                step=1,
                created_at=t1,
                sent_at=None,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="q",
                status="queued",
                step=2,
                created_at=t2,
                sent_at=None,
            )
        )
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(p.get("merchant_lifecycle_primary_key"), "customer_returned")
        self.assertIn("عاد", p.get("merchant_lifecycle_customer_behavior_ar") or "")

    def test_durable_returned_to_site_log_survives_skipped_duplicate_for_lifecycle(self) -> None:
        """Durable return row must win over later skipped_duplicate (narrow send path)."""
        st = self._store()
        sid = f"sid-ml-durable-{self._suffix}"
        zid = f"zid-ml-durable-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=15.0,
            customer_phone="9665111222333",
        )
        db.session.add(ac)
        db.session.flush()
        t0 = datetime.now(timezone.utc)
        t1 = t0 + timedelta(seconds=1)
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="return_to_site_detected",
                status="returned_to_site",
                step=None,
                created_at=t0,
                sent_at=None,
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone="9665111222333",
                message="m1",
                status="mock_sent",
                step=1,
                created_at=t0 - timedelta(seconds=5),
                sent_at=t0 - timedelta(seconds=5),
            )
        )
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone=None,
                message="dup",
                status="skipped_duplicate",
                step=2,
                created_at=t1,
                sent_at=None,
            )
        )
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(p.get("merchant_lifecycle_primary_key"), "customer_returned")
        self.assertIn("عاد", p.get("merchant_lifecycle_customer_behavior_ar") or "")
        self.assertIn("تلقائي", p.get("merchant_lifecycle_system_outcome_ar") or "")
        diag = p.get("normal_recovery_diagnostics") or {}
        self.assertTrue(diag.get("returned_to_site_evidence"), msg=diag)
        self.assertEqual(diag.get("merchant_lifecycle_primary_key"), "customer_returned")
        self.assertIn("returned_to_site", diag.get("recovery_log_statuses_seen") or [])

    def test_skipped_anti_spam_log_session_holds_cart_id_correlates_to_abandoned_row(self) -> None:
        """
        Regression: persist may set CartRecoveryLog.session_id to the cart id (no separate
        session_id in widget) while cart_id is null; AbandonedCart.recovery_session_id may
        stay empty. Lifecycle must still see skipped_anti_spam like suppression does.
        """
        st = self._store()
        zid = f"zid-ml-sesscart-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id="",
            status="abandoned",
            vip_mode=False,
            cart_value=12.0,
            customer_phone="9665111222333",
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=zid,
                cart_id=None,
                phone=None,
                message="suppressed",
                status="skipped_anti_spam",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=None,
            )
        )
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(p.get("merchant_lifecycle_primary_key"), "customer_returned")
        diag = p.get("normal_recovery_diagnostics") or {}
        self.assertTrue(diag.get("returned_to_site_evidence"), msg=diag)
        mi = p.get("merchant_lifecycle_internal") or {}
        self.assertTrue(mi.get("lifecycle_evidence_returned"), msg=mi)

    def test_pending_send_no_duplicate_is_no_engagement(self) -> None:
        st = self._store()
        sid = f"sid-ml-pend-{self._suffix}"
        zid = f"zid-ml-pend-{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=15.0,
            customer_phone="9665111222333",
        )
        db.session.add(ac)
        db.session.flush()
        db.session.add(
            CartRecoveryLog(
                store_slug=st.zid_store_id,
                session_id=sid,
                cart_id=zid,
                phone="9665111222333",
                message="queued",
                status="queued",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=None,
            )
        )
        db.session.commit()
        p = _normal_recovery_phase_steps_payload(ac)
        self.assertEqual(p.get("merchant_lifecycle_primary_key"), "delay_waiting")
        self.assertIn("بانتظار", p.get("merchant_lifecycle_customer_behavior_ar") or "")


if __name__ == "__main__":
    unittest.main()
