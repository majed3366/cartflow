# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid

import unittest

from main import app
from extensions import db
from models import CartRecoveryReason
from schema_widget import ensure_store_widget_schema
from sqlalchemy import and_


class TestCartRecoveryWidgetReasonApi(unittest.TestCase):
    def setUp(self) -> None:
        from fastapi.testclient import TestClient

        self.client = TestClient(app)

    def test_post_widget_reason_tag(self) -> None:
        ensure_store_widget_schema(db)
        sid = "w-" + uuid.uuid4().hex
        r = self.client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason_tag": "price_high",
            },
        )
        self.assertEqual(200, r.status_code, r.text)
        j = r.json() or {}
        self.assertTrue(j.get("ok"))
        self.assertTrue(j.get("saved"))
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
        self.assertEqual((row.reason or "").lower(), "price_high")
        self.assertEqual(row.source, "widget")

    def test_post_widget_other_requires_custom(self) -> None:
        ensure_store_widget_schema(db)
        r = self.client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": "demo",
                "session_id": "x1",
                "reason_tag": "other",
            },
        )
        self.assertEqual(400, r.status_code)
        self.assertFalse((r.json() or {}).get("saved", True))

    def test_post_widget_other_with_custom(self) -> None:
        ensure_store_widget_schema(db)
        sid = "o-" + uuid.uuid4().hex
        r = self.client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason_tag": "other",
                "custom_reason": "أفكر في الموعد",
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
        self.assertEqual((row.custom_text or "").strip(), "أفكر في الموعد")

    def test_post_widget_reason_accepts_customer_phone_alias(self) -> None:
        ensure_store_widget_schema(db)
        sid = "o-ph-" + uuid.uuid4().hex
        r = self.client.post(
            "/api/cart-recovery/reason",
            json={
                "store_slug": "demo",
                "session_id": sid,
                "reason_tag": "other",
                "custom_reason": "تجربة",
                "customer_phone": "966511122233",
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
        self.assertEqual((row.customer_phone or "").strip(), "966511122233")
