# -*- coding: utf-8 -*-
"""Sprint 2.3 / Fast Path V1.1 — reason POST must not wait on recovery arm."""
from __future__ import annotations

import time
import threading
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
import main
from models import CartRecoveryReason, Store
from tests.test_recovery_isolation import _reset_recovery_memory

_ROOT = Path(__file__).resolve().parent.parent
_ROUTES = (_ROOT / "routes" / "cartflow.py").read_text(encoding="utf-8")


class ReasonArmFastPathStructuralTests(unittest.TestCase):
    def test_reason_route_spawns_detached_arm_not_background_tasks(self) -> None:
        self.assertIn("_arm_recovery_after_reason_saved_bg", _ROUTES)
        self.assertIn("_spawn_reason_recovery_arm_detached", _ROUTES)
        self.assertIn("committed_reason_response", _ROUTES)
        self.assertIn("recovery_arm_background", _ROUTES)
        self.assertIn("scoped_db_session_begin", _ROUTES)
        self.assertIn("detached_thread", _ROUTES)
        route_idx = _ROUTES.find("async def post_abandonment_reason")
        self.assertGreaterEqual(route_idx, 0)
        route_body = _ROUTES[route_idx:]
        self.assertIn("_spawn_reason_recovery_arm_detached(", route_body)
        self.assertNotIn(
            "background_tasks.add_task(\n                _arm_recovery_after_reason_saved_bg",
            route_body,
        )
        spawn_idx = _ROUTES.find("def _spawn_reason_recovery_arm_detached")
        self.assertGreaterEqual(spawn_idx, 0)
        spawn_body = _ROUTES[spawn_idx:route_idx]
        self.assertIn("threading.Thread", spawn_body)
        self.assertIn("asyncio.run", spawn_body)


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

    @patch("routes.cartflow._spawn_reason_recovery_arm_detached")
    def test_reason_ok_schedules_detached_arm(self, spawn) -> None:
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
        self.assertEqual(r.headers.get("x-cf-reason-arm"), "detached_thread")
        spawn.assert_called_once()
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

    def test_detached_spawn_returns_before_arm_finishes(self) -> None:
        """Daemon thread must not be joined by the reason HTTP response path."""
        started = threading.Event()
        release = threading.Event()
        done = []

        def _fake_spawn(**_kwargs):
            def _run():
                started.set()
                release.wait(timeout=5)
                done.append(True)

            threading.Thread(target=_run, daemon=True).start()

        with patch(
            "routes.cartflow._spawn_reason_recovery_arm_detached",
            side_effect=_fake_spawn,
        ):
            # Warm path once so schema bootstrap is not in the measured sample.
            warm = self.client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": self.slug,
                    "session_id": f"s-rafp-warm-{self.suffix}",
                    "reason": "price",
                    "sub_category": "price_discount_request",
                },
            )
            self.assertEqual(warm.status_code, 200, warm.text)

        with patch(
            "routes.cartflow._spawn_reason_recovery_arm_detached",
            side_effect=_fake_spawn,
        ):
            t0 = time.perf_counter()
            r = self.client.post(
                "/api/cartflow/reason",
                json={
                    "store_slug": self.slug,
                    "session_id": f"s-rafp-fast-{self.suffix}",
                    "reason": "price",
                    "sub_category": "price_discount_request",
                },
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self.assertEqual(r.status_code, 200, r.text)
        self.assertTrue(started.wait(timeout=2))
        # Response returned while arm thread still blocked on ``release``.
        self.assertFalse(done)
        self.assertLess(elapsed_ms, 2000.0, f"unexpectedly slow response {elapsed_ms:.1f}ms")
        release.set()
        time.sleep(0.05)
        self.assertTrue(done)

class ReasonPostDetachClientTests(unittest.TestCase):
    def test_fetch_records_arm_header_and_resource_timing(self) -> None:
        text = (
            _ROOT / "static/cartflow_widget_runtime/cartflow_widget_fetch.js"
        ).read_text(encoding="utf-8")
        self.assertIn("_cf_reason_arm", text)
        self.assertIn("_cf_resource_timing", text)
        self.assertIn("request_to_response", text)

    def test_runtime_version(self) -> None:
        loader = (_ROOT / "static/widget_loader.js").read_text(encoding="utf-8")
        self.assertIn("v2-widget-reason-post-detach-v1-4", loader)


if __name__ == "__main__":
    unittest.main()
