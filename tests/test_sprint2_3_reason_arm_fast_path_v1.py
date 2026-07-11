# -*- coding: utf-8 -*-
"""Sprint 2.3 — reason POST must not await recovery arm (live timing confirmed)."""
from __future__ import annotations

import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from extensions import db
import main
from models import CartRecoveryReason, Store
from tests.test_recovery_isolation import _reset_recovery_memory

_ROOT = Path(__file__).resolve().parent.parent
_ROUTES = (_ROOT / "routes" / "cartflow.py").read_text(encoding="utf-8")


class ReasonArmFastPathStructuralTests(unittest.TestCase):
    def test_reason_route_schedules_arm_as_background_task(self) -> None:
        self.assertIn("_arm_recovery_after_reason_saved_bg", _ROUTES)
        self.assertIn("committed_reason_response", _ROUTES)
        self.assertIn("recovery_arm_background", _ROUTES)
        self.assertIn("scoped_db_session_begin", _ROUTES)
        route_idx = _ROUTES.find("async def post_abandonment_reason")
        bg_idx = _ROUTES.find("async def _arm_recovery_after_reason_saved_bg")
        self.assertGreaterEqual(route_idx, 0)
        self.assertGreaterEqual(bg_idx, 0)
        route_body = _ROUTES[route_idx:]
        self.assertIn(
            "background_tasks.add_task(\n                _arm_recovery_after_reason_saved_bg",
            route_body,
        )
        bg_body = _ROUTES[bg_idx:route_idx] if bg_idx < route_idx else _ROUTES[bg_idx:]
        self.assertIn(
            "await _schedule_normal_recovery_after_cart_recovery_reason_saved",
            bg_body,
        )


class ReasonArmFastPathBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        _reset_recovery_memory()
        self.client = TestClient(main.app)
        db.create_all()
        self.suffix = uuid.uuid4().hex[:8]
        slug = f"rafp-{self.suffix}"
        if not db.session.query(Store).filter(Store.zid_store_id == slug).first():
            db.session.add(Store(zid_store_id=slug))
            db.session.commit()
        self.slug = slug

    def tearDown(self) -> None:
        try:
            db.session.rollback()
        except Exception:
            pass
        _reset_recovery_memory()

    @patch(
        "routes.cartflow._arm_recovery_after_reason_saved_bg",
        new_callable=AsyncMock,
    )
    def test_reason_ok_schedules_background_arm(self, arm_bg: AsyncMock) -> None:
        sid = f"s-rafp-{self.suffix}"
        r = self.client.post(
            "/api/cartflow/reason",
            json={
                "store_slug": self.slug,
                "session_id": sid,
                "reason": "price",
                "sub_category": "price_discount_request",
            },
        )
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(r.json().get("ok"))
        arm_bg.assert_awaited()
        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == self.slug,
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        self.assertIsNotNone(row)
        self.assertEqual((row.reason or "").strip().lower(), "price")


if __name__ == "__main__":
    unittest.main()
