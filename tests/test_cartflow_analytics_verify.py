# -*- coding: utf-8 -*-
"""
Verify GET /api/cartflow/analytics/{store_slug} against CartRecoveryLog
and that demo vs demo2 are isolated.
"""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import CartRecoveryLog
from routes.cartflow import compute_recovery_analytics


class CartflowAnalyticsVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        db.create_all()
        self._row_ids: list[int] = []

    def tearDown(self) -> None:
        for rid in self._row_ids:
            try:
                r = db.session.get(CartRecoveryLog, rid)
                if r is not None:
                    db.session.delete(r)
            except (OSError, Exception):
                pass
        try:
            db.session.commit()
        except (OSError, Exception):
            db.session.rollback()

    def _insert(
        self,
        *,
        store_slug: str,
        session_id: str,
        status: str,
        step: int | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        row = CartRecoveryLog(
            store_slug=store_slug[:255],
            session_id=session_id[:512],
            cart_id=None,
            phone="0",
            message="m",
            status=status[:50],
            step=step,
            created_at=now,
            sent_at=now if "sent" in status else None,
        )
        db.session.add(row)
        db.session.commit()
        db.session.refresh(row)
        self._row_ids.append(int(row.id))

    def _json_metrics(self, payload: dict) -> dict:
        return {
            "store_slug": payload["store_slug"],
            "total_attempts": payload["total_attempts"],
            "sent_real": payload["sent_real"],
            "failed_final": payload["failed_final"],
            "stopped_converted": payload["stopped_converted"],
            "steps": payload["steps"],
        }

    def test_analytics_matches_orm_for_demo_and_demo2(self) -> None:
        """API response metrics match compute_recovery_analytics (CartRecoveryLog) per store."""
        for slug in ("demo", "demo2"):
            ref = compute_recovery_analytics(slug)
            r = self.client.get(f"/api/cartflow/analytics/{slug}")
            self.assertEqual(200, r.status_code, r.text)
            data = r.json()
            self.assertTrue(data.get("ok"), data)
            self.assertEqual(data.get("revenue_recovered"), 0.0)
            self.assertEqual(
                self._json_metrics(data),
                ref,
                f"mismatch for {slug}: API vs ORM",
            )

    def test_isolation_demo_vs_demo2(self) -> None:
        before_demo = compute_recovery_analytics("demo")
        before_d2 = compute_recovery_analytics("demo2")
        # Row visible only for demo: increases demo counts, not demo2
        self._insert(
            store_slug="demo",
            session_id="analyt-isol-1",
            status="failed_final",
            step=1,
        )
        after_demo = compute_recovery_analytics("demo")
        after_d2 = compute_recovery_analytics("demo2")
        self.assertEqual(
            after_demo["total_attempts"] - before_demo["total_attempts"],
            1,
            "one new log for demo",
        )
        self.assertEqual(
            after_d2["total_attempts"],
            before_d2["total_attempts"],
            "demo2 unchanged when only demo got a new row",
        )
        self.assertEqual(
            after_d2["failed_final"],
            before_d2["failed_final"],
        )
        r = self.client.get("/api/cartflow/analytics/demo2")
        self.assertEqual(200, r.status_code, r.text)
        self.assertEqual(
            self._json_metrics(r.json()),
            after_d2,
        )

    def test_step_grouping_against_orm(self) -> None:
        self._insert(
            store_slug="demo",
            session_id="analyt-step-1",
            status="mock_sent",
            step=1,
        )
        self._insert(
            store_slug="demo",
            session_id="analyt-step-2",
            status="stopped_converted",
            step=2,
        )
        self._insert(
            store_slug="demo",
            session_id="analyt-step-3",
            status="sent_real",
            step=3,
        )
        ref = compute_recovery_analytics("demo")
        r = self.client.get("/api/cartflow/analytics/demo")
        self.assertEqual(200, r.status_code, r.text)
        d = r.json()
        s = d["steps"]
        self.assertEqual(
            s["step1"]["sent"],
            ref["steps"]["step1"]["sent"],
        )
        self.assertEqual(
            s["step2"]["converted"],
            ref["steps"]["step2"]["converted"],
        )
        self.assertEqual(
            s["step3"]["sent"],
            ref["steps"]["step3"]["sent"],
        )
        self.assertEqual(self._json_metrics(d), ref, d)


if __name__ == "__main__":
    unittest.main()
