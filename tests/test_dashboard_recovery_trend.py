# -*- coding: utf-8 -*-
"""GET /api/dashboard/recovery-trend — قراءة فقط؛ سبعة أيام."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart


class DashboardRecoveryTrendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_recovery_trend_returns_seven_days(self) -> None:
        r = self.client.get("/api/dashboard/recovery-trend")
        self.assertEqual(200, r.status_code, r.text)
        data = r.json()
        self.assertIsInstance(data, list)
        self.assertEqual(7, len(data))
        for row in data:
            self.assertIn("date", row)
            self.assertIn("value", row)
            self.assertRegex(row["date"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertIsInstance(row["value"], (int, float))

    def test_recovery_trend_sums_recovered_cart_value_by_day(self) -> None:
        db.create_all()
        today = datetime.now(timezone.utc).date()
        recovered_at = datetime(
            today.year, today.month, today.day, 12, 0, 0, tzinfo=timezone.utc
        )
        cart = AbandonedCart(
            zid_cart_id="trend-test-cart-unique",
            status="recovered",
            recovered_at=recovered_at,
            cart_value=100.0,
        )
        db.session.add(cart)
        db.session.commit()
        try:
            r = self.client.get("/api/dashboard/recovery-trend")
            self.assertEqual(200, r.status_code)
            payload = r.json()
            today_row = next((x for x in payload if x["date"] == today.isoformat()), None)
            self.assertIsNotNone(today_row)
            self.assertGreaterEqual(float(today_row["value"]), 100.0)
        finally:
            db.session.delete(cart)
            db.session.commit()
