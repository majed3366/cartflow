# -*- coding: utf-8 -*-
"""Living Store production demo seed + Home review session."""
from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")


class LivingStoreProdCalendarTests(unittest.TestCase):
    def test_wall_clock_trailing_window(self) -> None:
        from services.living_store_reality_prod_v1 import wall_clock_living_calendar_v1

        now = datetime(2026, 7, 25, 12, 0, 0, tzinfo=timezone.utc)
        cal = wall_clock_living_calendar_v1(now=now, duration_days=30)
        self.assertEqual(cal["calendar_mode"], "wall_clock_trailing")
        self.assertEqual(cal["duration_days"], 30)
        self.assertEqual(cal["start_date"], "2026-06-26")
        self.assertEqual(cal["sim_end"].isoformat(), "2026-07-25T12:00:00+00:00")


class LivingStoreProdAllowlistTests(unittest.TestCase):
    def test_routes_allowlisted_for_production(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT

        for path in (
            "/dev/living-store-reality-run",
            "/dev/living-store-reality-status",
            "/dev/living-store-home-review-session",
            "/dev/living-store-home-review",
        ):
            self.assertIn(path, _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT)


class LivingStoreProdReviewSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import models  # noqa: F401
        from extensions import db, init_database

        init_database()
        db.create_all()

    def test_review_session_primary_is_demo(self) -> None:
        from extensions import db
        from models import MerchantUser, Store
        from services.living_store_reality_prod_v1 import (
            REVIEW_EMAIL,
            issue_demo_home_review_session_v1,
        )
        from services.merchant_auth_v1 import resolve_authenticated_store_slug

        payload = issue_demo_home_review_session_v1()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["store_slug"], "demo")
        self.assertEqual(payload["email"], REVIEW_EMAIL)
        self.assertTrue(payload["cookie_value"])

        user = db.session.query(MerchantUser).filter_by(email=REVIEW_EMAIL).one()
        demo = db.session.query(Store).filter_by(zid_store_id="demo").one()
        self.assertEqual(int(user.primary_store_id), int(demo.id))
        self.assertEqual(int(demo.merchant_user_id), int(user.id))

        slug = resolve_authenticated_store_slug(
            {payload["cookie_name"]: payload["cookie_value"]}
        )
        self.assertEqual(slug, "demo")


class LivingStoreProdJobGuardTests(unittest.TestCase):
    def test_start_rejects_when_already_running(self) -> None:
        from services import living_store_reality_prod_v1 as mod

        with mod._JOB_LOCK:
            mod._JOB.update({"status": "running", "ok": None, "error": None})
        try:
            out = mod.start_living_store_prod_run_v1()
            self.assertFalse(out["ok"])
            self.assertEqual(out["error"], "already_running")
        finally:
            with mod._JOB_LOCK:
                mod._JOB.update({"status": "idle", "ok": None, "error": None})


if __name__ == "__main__":
    unittest.main()
