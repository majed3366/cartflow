# -*- coding: utf-8 -*-
"""لوحة VIP: دورة حياة المتابعة (contacted / closed / converted) — قراءة قائمة + ‎POST /api/dashboard/vip-cart/{id}/lifecycle‎."""
from __future__ import annotations

import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from extensions import db
from fastapi.testclient import TestClient

from main import app, _ensure_store_widget_schema
from models import AbandonedCart, Store


class VipDashboardLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:  # noqa: BLE001
            pass

    @patch("main._cleanup_duplicate_vip_abandoned_rows", return_value=0)
    def test_lifecycle_post_sets_contacted(self, _noop_cleanup: object) -> None:
        db.create_all()
        _ensure_store_widget_schema()
        slug = f"vip_lc_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug)
        db.session.add(store)
        db.session.commit()

        ac = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"zlc-{uuid.uuid4().hex[:8]}",
            cart_value=900.0,
            status="abandoned",
            vip_mode=True,
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add(ac)
        db.session.commit()
        rid = int(ac.id)

        r = self.client.post(
            f"/api/dashboard/vip-cart/{rid}/lifecycle",
            json={"status": "contacted"},
        )
        self.assertEqual(r.status_code, 200, r.text)
        out = r.json()
        self.assertTrue(out.get("ok"), out)
        self.assertEqual(out.get("status"), "contacted")

        db.session.expire_all()
        ac2 = db.session.get(AbandonedCart, rid)
        self.assertIsNotNone(ac2)
        assert ac2 is not None
        self.assertEqual((getattr(ac2, "vip_lifecycle_status", None) or "").strip(), "contacted")

    @patch("main._cleanup_duplicate_vip_abandoned_rows", return_value=0)
    def test_dashboard_hides_closed_and_converted_cards(self, _noop_cleanup: object) -> None:
        db.create_all()
        _ensure_store_widget_schema()
        slug = f"vip_lc_hide_{uuid.uuid4().hex[:12]}"
        store = Store(zid_store_id=slug)
        db.session.add(store)
        db.session.commit()

        ac_open = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"open-{uuid.uuid4().hex[:8]}",
            cart_value=800.0,
            status="abandoned",
            vip_mode=True,
            vip_lifecycle_status=None,
            last_seen_at=datetime.now(timezone.utc),
        )
        ac_closed = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"closed-{uuid.uuid4().hex[:8]}",
            cart_value=801.0,
            status="abandoned",
            vip_mode=True,
            vip_lifecycle_status="closed",
            last_seen_at=datetime.now(timezone.utc),
        )
        ac_conv = AbandonedCart(
            store_id=store.id,
            zid_cart_id=f"conv-{uuid.uuid4().hex[:8]}",
            cart_value=802.0,
            status="abandoned",
            vip_mode=True,
            vip_lifecycle_status="converted",
            last_seen_at=datetime.now(timezone.utc),
        )
        db.session.add_all([ac_open, ac_closed, ac_conv])
        db.session.commit()

        r = self.client.get("/dashboard/vip-cart-settings")
        self.assertEqual(r.status_code, 200, r.text)
        html = r.text.replace("&#34;", '"')
        self.assertIn(f'data-cart-row-id="{ac_open.id}"', html)
        self.assertNotIn(f'data-cart-row-id="{ac_closed.id}"', html)
        self.assertNotIn(f'data-cart-row-id="{ac_conv.id}"', html)
        self.assertIn("data-vip-lifecycle-close", html)


if __name__ == "__main__":
    unittest.main()
