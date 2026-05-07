# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import unittest
import uuid

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import CartRecoveryReason
from schema_widget import ensure_store_widget_schema
from services.cf_test_phone_override import (
    cf_test_customer_phone_override_allowed,
    normalize_cf_test_customer_phone,
)
from sqlalchemy import and_


class TestCfTestCustomerPhoneOverride(unittest.TestCase):
    def test_normalize_sa_mobile(self) -> None:
        self.assertEqual(normalize_cf_test_customer_phone("0546518011"), "966546518011")
        self.assertEqual(normalize_cf_test_customer_phone("966546518011"), "966546518011")

    def test_allowed_demo_slug_even_when_env_production(self) -> None:
        prev = os.environ.get("ENV")
        try:
            os.environ["ENV"] = "production"
            self.assertTrue(cf_test_customer_phone_override_allowed("demo"))
            self.assertFalse(cf_test_customer_phone_override_allowed("demo2"))
            self.assertFalse(cf_test_customer_phone_override_allowed("acme"))
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev

    def test_allowed_any_slug_in_development(self) -> None:
        prev = os.environ.get("ENV")
        try:
            os.environ["ENV"] = "development"
            self.assertTrue(cf_test_customer_phone_override_allowed("demo2"))
            self.assertTrue(cf_test_customer_phone_override_allowed("other_slug"))
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev

    def test_reason_endpoint_applies_cf_test_phone_for_demo(self) -> None:
        ensure_store_widget_schema(db)
        client = TestClient(app)
        sid = "cf-demo-" + uuid.uuid4().hex
        r = client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason_tag": "price",
                "cf_test_phone": "966546518011",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                and_(
                    CartRecoveryReason.store_slug == "demo",
                    CartRecoveryReason.session_id == sid,
                )
            )
            .first()
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual((row.customer_phone or "").strip(), "966546518011")

    def test_reason_endpoint_ignores_cf_test_phone_non_demo_non_dev(self) -> None:
        ensure_store_widget_schema(db)
        client = TestClient(app)
        prev = os.environ.get("ENV")
        try:
            os.environ["ENV"] = "production"
            sid = "cf-prod-" + uuid.uuid4().hex
            r = client.post(
                "/api/cart-recovery/reason",
                json={
                    "store_slug": "acme_real_store",
                    "session_id": sid,
                    "reason_tag": "price",
                    "cf_test_phone": "966546518011",
                },
            )
            self.assertEqual(200, r.status_code, r.text)
            row = (
                db.session.query(CartRecoveryReason)
                .filter(
                    and_(
                        CartRecoveryReason.store_slug == "acme_real_store",
                        CartRecoveryReason.session_id == sid,
                    )
                )
                .first()
            )
            self.assertIsNotNone(row)
            assert row is not None
            self.assertFalse((row.customer_phone or "").strip())
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev

    def test_inject_cf_test_into_abandon_payload_demo(self) -> None:
        from main import _inject_cf_test_customer_phone_into_abandon_payload

        p = {
            "store": "demo",
            "session_id": "s_cf_inj_1",
            "cart_id": "cid_cf_inj_1",
            "cf_test_phone": "966546518011",
        }
        _inject_cf_test_customer_phone_into_abandon_payload(p)
        self.assertEqual((p.get("phone") or "").strip(), "966546518011")

    def test_inject_cf_test_skipped_non_demo_production_env(self) -> None:
        from main import _inject_cf_test_customer_phone_into_abandon_payload

        prev = os.environ.get("ENV")
        try:
            os.environ["ENV"] = "production"
            p = {
                "store": "acme_prod",
                "session_id": "s_cf_inj_2",
                "cf_test_phone": "966546518011",
            }
            _inject_cf_test_customer_phone_into_abandon_payload(p)
            self.assertNotIn("phone", p)
        finally:
            if prev is None:
                os.environ.pop("ENV", None)
            else:
                os.environ["ENV"] = prev
