# -*- coding: utf-8
"""Continuous dashboard snapshot builder loop tests."""
from __future__ import annotations

import asyncio
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from extensions import db
from models import DashboardSnapshot, MerchantUser, Store
from services.dashboard_snapshot_loop_v1 import (
    dashboard_snapshot_loop_interval_seconds,
    is_dashboard_snapshot_loop_running,
    run_dashboard_snapshot_loop_tick,
    start_dashboard_snapshot_builder_loop,
    stop_dashboard_snapshot_builder_loop,
)
from services.dashboard_snapshot_v1 import (
    ENV_SNAPSHOT_MODE,
    SNAPSHOT_TYPE_NORMAL_CARTS,
    SNAPSHOT_TYPE_SUMMARY,
    fetch_latest_snapshot_row,
    list_store_slugs_for_snapshot_build,
    snapshot_row_is_stale,
    upsert_dashboard_snapshot,
)
from services.scheduler_snapshot_loop_health_v1 import (
    clear_scheduler_snapshot_loop_health_for_tests,
)


def _enable_scheduler_snapshot_env() -> None:
    os.environ["ENV"] = "development"
    os.environ["SECRET_KEY"] = "unit-test-snapshot-loop-continuous-v1"
    os.environ["CARTFLOW_PROCESS_ROLE"] = "scheduler"
    os.environ[ENV_SNAPSHOT_MODE] = "1"
    os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
    os.environ["CARTFLOW_RECOVERY_RESUME_ON_STARTUP"] = "1"


class DashboardSnapshotLoopContinuousTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        clear_scheduler_snapshot_loop_health_for_tests()
        _enable_scheduler_snapshot_env()
        db.create_all()
        db.session.query(DashboardSnapshot).delete()
        db.session.query(Store).filter(
            Store.zid_store_id.in_(
                [
                    "cartflow-loop-write-test",
                    "cartflow-loop-priority-test",
                ]
            )
        ).delete(synchronize_session=False)
        db.session.query(MerchantUser).filter(
            MerchantUser.email.in_(
                [
                    "snap-loop-write@example.com",
                    "snap-loop-priority@example.com",
                ]
            )
        ).delete(synchronize_session=False)
        db.session.commit()

    def tearDown(self) -> None:
        clear_scheduler_snapshot_loop_health_for_tests()

    async def asyncTearDown(self) -> None:
        await stop_dashboard_snapshot_builder_loop()

    async def test_scheduler_role_starts_snapshot_loop(self) -> None:
        with patch(
            "services.dashboard_snapshot_builder_v1.run_dashboard_snapshot_builder_tick",
            return_value={"skipped": False, "stores_built": 1, "errors": 0, "stores_seen": 1},
        ):
            start_dashboard_snapshot_builder_loop()
            await asyncio.sleep(0.05)
        self.assertTrue(is_dashboard_snapshot_loop_running())

    async def test_loop_continues_after_one_tick(self) -> None:
        calls = {"n": 0}

        def _tick() -> dict:
            calls["n"] += 1
            return {"skipped": False, "stores_built": 1, "errors": 0, "stores_seen": 1}

        async def _fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch(
            "services.dashboard_snapshot_loop_v1.dashboard_snapshot_loop_interval_seconds",
            return_value=0.05,
        ), patch(
            "services.dashboard_snapshot_builder_v1.run_dashboard_snapshot_builder_tick",
            side_effect=_tick,
        ), patch(
            "services.dashboard_snapshot_loop_v1.asyncio.to_thread",
            side_effect=_fake_to_thread,
        ):
            start_dashboard_snapshot_builder_loop()
            await asyncio.sleep(0.25)
        self.assertGreaterEqual(calls["n"], 2)
        self.assertTrue(is_dashboard_snapshot_loop_running())

    async def test_tick_exception_does_not_kill_loop(self) -> None:
        calls = {"n": 0}

        def _tick() -> dict:
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("builder boom")
            return {"skipped": False, "stores_built": 1, "errors": 0, "stores_seen": 1}

        async def _fake_to_thread(fn, *args, **kwargs):
            return fn(*args, **kwargs)

        with patch(
            "services.dashboard_snapshot_loop_v1.dashboard_snapshot_loop_interval_seconds",
            return_value=0.05,
        ), patch(
            "services.dashboard_snapshot_builder_v1.run_dashboard_snapshot_builder_tick",
            side_effect=_tick,
        ), patch(
            "services.dashboard_snapshot_loop_v1.asyncio.to_thread",
            side_effect=_fake_to_thread,
        ):
            start_dashboard_snapshot_builder_loop()
            await asyncio.sleep(0.25)
        self.assertGreaterEqual(calls["n"], 2)
        self.assertTrue(is_dashboard_snapshot_loop_running())

    async def test_run_dashboard_snapshot_loop_tick_returns_error_without_raising(self) -> None:
        with patch(
            "services.dashboard_snapshot_builder_v1.run_dashboard_snapshot_builder_tick",
            side_effect=RuntimeError("thread tick failed"),
        ):
            out = await run_dashboard_snapshot_loop_tick()
        self.assertIn("error", out)
        self.assertIn("thread tick failed", out["error"])

    def test_snapshot_write_updates_generated_at(self) -> None:
        slug = "cartflow-loop-write-test"
        user = MerchantUser(
            email="snap-loop-write@example.com",
            password_hash="x",
            merchant_name="Snap Loop Write",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id=slug,
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.commit()

        old = datetime.now(timezone.utc) - timedelta(minutes=30)
        upsert_dashboard_snapshot(
            store_id=int(st.id),
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload={"merchant_carts_page_rows": []},
        )
        row_before = fetch_latest_snapshot_row(
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        )
        self.assertIsNotNone(row_before)
        row_before.generated_at = old.replace(tzinfo=None)
        row_before.expires_at = (old - timedelta(seconds=60)).replace(tzinfo=None)
        db.session.commit()
        db.session.refresh(row_before)
        self.assertTrue(snapshot_row_is_stale(row_before))

        upsert_dashboard_snapshot(
            store_id=int(st.id),
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
            payload={"merchant_carts_page_rows": [{"recovery_key": f"{slug}:cf_cart_x"}]},
        )
        row_after = fetch_latest_snapshot_row(
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS,
        )
        self.assertIsNotNone(row_after)
        self.assertFalse(snapshot_row_is_stale(row_after))
        self.assertGreater(row_after.generated_at, row_before.generated_at)

    def test_stale_store_is_selected_for_rebuild(self) -> None:
        slug = "cartflow-loop-priority-test"
        user = MerchantUser(
            email="snap-loop-priority@example.com",
            password_hash="x",
            merchant_name="Snap Loop Priority",
        )
        db.session.add(user)
        db.session.flush()
        st = Store(
            zid_store_id=slug,
            merchant_user_id=int(user.id),
            is_active=True,
            recovery_attempts=1,
        )
        db.session.add(st)
        db.session.commit()

        stale_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        upsert_dashboard_snapshot(
            store_id=int(st.id),
            store_slug=slug,
            snapshot_type=SNAPSHOT_TYPE_SUMMARY,
            payload={"kpis": {}},
        )
        row = (
            db.session.query(DashboardSnapshot)
            .filter(
                DashboardSnapshot.store_slug == slug,
                DashboardSnapshot.snapshot_type == SNAPSHOT_TYPE_SUMMARY,
            )
            .order_by(DashboardSnapshot.id.desc())
            .first()
        )
        self.assertIsNotNone(row)
        row.generated_at = stale_at.replace(tzinfo=None)
        row.expires_at = (stale_at - timedelta(minutes=1)).replace(tzinfo=None)
        db.session.commit()

        slugs = [s for _sid, s in list_store_slugs_for_snapshot_build(limit=5)]
        self.assertIn(slug, slugs)

    async def test_runtime_startup_starts_snapshot_loop_on_scheduler(self) -> None:
        from services.runtime_startup_v1 import run_scheduler_drivers_at_startup

        with patch(
            "services.dashboard_snapshot_builder_v1.run_dashboard_snapshot_builder_tick",
            return_value={"skipped": False, "stores_built": 0, "errors": 0, "stores_seen": 0},
        ):
            out = await run_scheduler_drivers_at_startup()
            await asyncio.sleep(0.05)
        self.assertTrue(out.get("snapshot_loop_started"))
        self.assertTrue(is_dashboard_snapshot_loop_running())


if __name__ == "__main__":
    unittest.main()
