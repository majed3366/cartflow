# -*- coding: utf-8 -*-
"""Phone resolution contracts: missing, present, demo cf_test_phone (QA-only)."""
from __future__ import annotations

import os
import unittest
import uuid

os.environ.setdefault("ENV", "development")

from extensions import db
from main import _resolve_cartflow_recovery_phone
from models import CartRecoveryReason, Store
from services.recovery_session_phone import (
    record_recovery_customer_phone,
    recovery_phone_memory_clear,
)


class OperationalPhoneResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        db.create_all()
        recovery_phone_memory_clear()
        self._suffix = uuid.uuid4().hex[:10]

    def tearDown(self) -> None:
        recovery_phone_memory_clear()
        try:
            db.session.query(CartRecoveryReason).filter(
                CartRecoveryReason.session_id.like(f"%{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(
                Store.zid_store_id.like(f"op_ph_{self._suffix}%")
            ).delete(synchronize_session=False)
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()

    def test_missing_phone_safe_skip_resolution(self) -> None:
        st = Store(
            zid_store_id=f"op_ph_{self._suffix}",
            recovery_delay=1,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.flush()
        sid = f"op_ph_sid_{self._suffix}"
        row = CartRecoveryReason(
            store_slug=st.zid_store_id,
            session_id=sid,
            reason="price",
            customer_phone=None,
            source="widget",
        )
        db.session.add(row)
        db.session.commit()
        rk = f"{st.zid_store_id}:{sid}"
        phone, src, allowed = _resolve_cartflow_recovery_phone(
            store_slug=st.zid_store_id,
            session_id=sid,
            cart_id=None,
            store_obj=st,
            abandon_event_phone=None,
            recovery_key=rk,
            reason_row=row,
        )
        self.assertIsNone(phone)
        self.assertEqual(src, "none")
        self.assertFalse(allowed)

    def test_memory_cf_test_phone_resolves_and_allows(self) -> None:
        """Demo QA path: in-memory label cf_test_phone is verified for allowlist."""
        sid = f"op_cf_{self._suffix}"
        rk = f"demo:{sid}"
        record_recovery_customer_phone(rk, "966511122233", source="cf_test_phone")
        phone, src, allowed = _resolve_cartflow_recovery_phone(
            store_slug="demo",
            session_id=sid,
            cart_id=f"cid_{self._suffix}",
            store_obj=None,
            abandon_event_phone=None,
            recovery_key=rk,
            reason_row=None,
        )
        self.assertTrue((phone or "").strip().endswith("966511122233"))
        self.assertEqual(src, "cf_test_phone")
        self.assertTrue(allowed)
