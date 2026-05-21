# -*- coding: utf-8 -*-
"""Automatic DB due scanner loop — env gate and tick behavior."""
from __future__ import annotations

import asyncio
import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import main  # noqa: F401

from services.recovery_db_due_scanner_loop import (
    db_due_scanner_loop_interval_seconds,
    is_db_due_scanner_loop_enabled,
    run_db_due_scanner_loop_tick,
    start_db_due_recovery_scanner_loop,
    stop_db_due_recovery_scanner_loop,
)


class RecoveryDbDueScannerLoopTests(unittest.IsolatedAsyncioTestCase):
    def tearDown(self) -> None:
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS", None)

    def test_disabled_by_default(self) -> None:
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
        self.assertFalse(is_db_due_scanner_loop_enabled())

    def test_enabled_when_env_true(self) -> None:
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        self.assertTrue(is_db_due_scanner_loop_enabled())

    def test_interval_defaults_and_minimum(self) -> None:
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS", None)
        self.assertEqual(db_due_scanner_loop_interval_seconds(), 30.0)
        os.environ["CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS"] = "2"
        self.assertEqual(db_due_scanner_loop_interval_seconds(), 5.0)

    async def test_tick_calls_scan_due_recovery_schedules(self) -> None:
        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        mock_out = {"found": 0, "dispatched": 0, "skipped": 0}
        with patch(
            "services.recovery_db_due_scanner.scan_due_recovery_schedules",
            new_callable=AsyncMock,
            return_value=mock_out,
        ) as mock_scan:
            out = await run_db_due_scanner_loop_tick()
        self.assertEqual(out, mock_out)
        mock_scan.assert_awaited_once()
        self.assertEqual(
            mock_scan.await_args.kwargs.get("source"),
            "db_due_scanner_loop",
        )

    async def test_no_overlapping_ticks(self) -> None:
        gate = asyncio.Event()
        started = asyncio.Event()

        async def slow_scan(**_kwargs: object) -> dict:
            started.set()
            await gate.wait()
            return {"found": 0, "dispatched": 0, "skipped": 0}

        with patch(
            "services.recovery_db_due_scanner.scan_due_recovery_schedules",
            side_effect=slow_scan,
        ):
            t1 = asyncio.create_task(run_db_due_scanner_loop_tick())
            await asyncio.wait_for(started.wait(), timeout=2.0)
            out2 = await run_db_due_scanner_loop_tick()
            gate.set()
            out1 = await t1

        self.assertTrue(out2.get("skipped"))
        self.assertEqual(out2.get("reason"), "tick_in_progress")
        self.assertEqual(out1.get("found"), 0)

    async def test_start_loop_only_when_enabled(self) -> None:
        os.environ.pop("CARTFLOW_DB_DUE_SCANNER_ENABLED", None)
        with patch(
            "services.recovery_db_due_scanner_loop.asyncio.get_running_loop"
        ) as mock_loop_fn:
            start_db_due_recovery_scanner_loop()
            mock_loop_fn.assert_not_called()

        os.environ["CARTFLOW_DB_DUE_SCANNER_ENABLED"] = "true"
        os.environ["CARTFLOW_DB_DUE_SCANNER_INTERVAL_SECONDS"] = "60"
        with patch(
            "services.recovery_db_due_scanner_loop._db_due_scanner_loop_forever",
            new_callable=AsyncMock,
        ):
            start_db_due_recovery_scanner_loop()
            await stop_db_due_recovery_scanner_loop()


if __name__ == "__main__":
    unittest.main()
