# -*- coding: utf-8 -*-
"""Merchant trust: dashboard coarse status must not claim 'sent' without successful log statuses."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone

from extensions import db
from main import (
    _NORMAL_RECOVERY_SENT_LOG_STATUSES,
    _cart_recovery_sent_real_count_for_abandoned,
    _normal_recovery_coarse_status,
    _normal_recovery_dashboard_phase_key,
    _normal_recovery_phase_steps_payload,
)
from models import AbandonedCart, CartRecoveryLog, Store


class OperationalDashboardTrustTests(unittest.TestCase):
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
                Store.zid_store_id.like(f"op_dash_{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_skipped_no_verified_phone_does_not_count_as_sent(self) -> None:
        st = Store(
            zid_store_id=f"op_dash_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"op_dash_sid_{self._suffix}"
        zid = f"op_dash_z_{self._suffix}"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=20.0,
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
                status="skipped_no_verified_phone",
                step=1,
                created_at=datetime.now(timezone.utc),
                sent_at=None,
            )
        )
        db.session.commit()
        n_sent = _cart_recovery_sent_real_count_for_abandoned(ac)
        self.assertEqual(n_sent, 0)
        self.assertNotIn("skipped_no_verified_phone", _NORMAL_RECOVERY_SENT_LOG_STATUSES)
        pk = _normal_recovery_dashboard_phase_key(ac)
        coarse = _normal_recovery_coarse_status(pk)
        self.assertNotEqual(coarse, "sent")

    def test_snapshot_core_dashboard_keys_stable(self) -> None:
        """Core machine-readable keys for normal recovery card (not Arabic copy)."""
        st = Store(
            zid_store_id=f"op_dash_{self._suffix}b",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"op_dash_sid_{self._suffix}b"
        zid = f"op_dash_z_{self._suffix}b"
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=30.0,
        )
        db.session.add(ac)
        db.session.commit()
        payload = _normal_recovery_phase_steps_payload(ac)
        for key in (
            "normal_recovery_phase_key",
            "normal_recovery_status",
            "normal_recovery_attempt_cap",
            "normal_recovery_attempt_sent",
            "normal_recovery_last_skip_reason",
            "normal_recovery_phase_steps",
        ):
            self.assertIn(key, payload)

    def test_behavioral_replied_precedes_return_in_phase_key(self) -> None:
        """When both flags exist in payload, dashboard phase follows behavioral precedence."""
        import json

        st = Store(
            zid_store_id=f"op_dash_{self._suffix}c",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"op_dash_sid_{self._suffix}c"
        zid = f"op_dash_z_{self._suffix}c"
        raw = {
            "cf_behavioral": {
                "customer_replied": True,
                "user_returned_to_site": True,
            }
        }
        ac = AbandonedCart(
            store_id=int(st.id),
            zid_cart_id=zid,
            recovery_session_id=sid,
            status="abandoned",
            vip_mode=False,
            cart_value=15.0,
            raw_payload=json.dumps(raw, ensure_ascii=False),
        )
        db.session.add(ac)
        db.session.commit()
        pk = _normal_recovery_dashboard_phase_key(ac)
        self.assertEqual(pk, "behavioral_replied")
