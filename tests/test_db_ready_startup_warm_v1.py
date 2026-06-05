# -*- coding: utf-8 -*-
"""Startup DB warm (Step 4B.3)."""
from __future__ import annotations

import io
import os
import threading
import time
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import main

from services.db_ready_operational_snapshot_v1 import (
    clear_db_ready_operational_snapshot_for_tests,
    load_db_ready_operational_snapshot,
    record_startup_warm_snapshot,
)
from services.db_ready_startup_warm_v1 import (
    clear_db_ready_startup_warm_for_tests,
    is_startup_warm_running,
    should_defer_user_db_ready,
    start_db_ready_startup_warm_async,
    startup_warm_status,
    wait_for_startup_warm,
)


class DbReadyStartupWarmV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_db_ready_startup_warm_for_tests()
        clear_db_ready_operational_snapshot_for_tests()
        main._cartflow_api_db_warmed = False
        os.environ["CARTFLOW_DISABLE_STARTUP_DB_WARM"] = "1"

    def tearDown(self) -> None:
        clear_db_ready_startup_warm_for_tests()
        clear_db_ready_operational_snapshot_for_tests()
        main._cartflow_api_db_warmed = True
        os.environ.pop("CARTFLOW_DISABLE_STARTUP_DB_WARM", None)

    def test_background_warm_sets_succeeded_and_logs(self) -> None:
        os.environ.pop("CARTFLOW_DISABLE_STARTUP_DB_WARM", None)
        done = threading.Event()

        def _warm() -> None:
            time.sleep(0.05)
            main._cartflow_api_db_warmed = True
            done.set()

        buf = io.StringIO()
        with redirect_stdout(buf):
            start_db_ready_startup_warm_async(warm_fn=_warm)
            self.assertTrue(done.wait(timeout=3.0))
            wait_for_startup_warm(timeout_s=2.0)
        text = buf.getvalue()
        self.assertIn("[DB READY STARTUP WARM] stage=start", text)
        self.assertIn("[DB READY STARTUP WARM] stage=done", text)
        self.assertEqual(startup_warm_status(), "succeeded")

    def test_should_defer_while_running(self) -> None:
        gate = threading.Event()

        def _warm() -> None:
            gate.wait(timeout=3.0)
            main._cartflow_api_db_warmed = True

        os.environ.pop("CARTFLOW_DISABLE_STARTUP_DB_WARM", None)
        start_db_ready_startup_warm_async(warm_fn=_warm)
        deadline = time.time() + 2.0
        while not is_startup_warm_running() and time.time() < deadline:
            time.sleep(0.01)
        self.assertTrue(is_startup_warm_running())
        self.assertTrue(should_defer_user_db_ready(allow_defer=True))
        self.assertFalse(should_defer_user_db_ready(allow_defer=False))
        gate.set()
        self.assertTrue(wait_for_startup_warm(timeout_s=3.0))
        self.assertFalse(should_defer_user_db_ready(allow_defer=True))

    def test_merchant_dashboard_db_ready_defers_for_refresh_state(self) -> None:
        gate = threading.Event()

        def _warm() -> None:
            gate.wait(timeout=3.0)
            main._cartflow_api_db_warmed = True

        os.environ.pop("CARTFLOW_DISABLE_STARTUP_DB_WARM", None)
        start_db_ready_startup_warm_async(warm_fn=_warm)
        deadline = time.time() + 2.0
        while not is_startup_warm_running() and time.time() < deadline:
            time.sleep(0.01)
        with patch.object(main, "_ensure_cartflow_api_db_warmed") as mock_warm:
            ok = main._merchant_dashboard_db_ready(allow_defer=True)
        self.assertFalse(ok)
        mock_warm.assert_not_called()
        gate.set()
        wait_for_startup_warm(timeout_s=3.0)

    def test_startup_warm_snapshot_persisted(self) -> None:
        record_startup_warm_snapshot(
            {
                "startup_warm_status": "running",
                "startup_warm_duration_ms": 0.0,
                "startup_warm_error": None,
                "last_request_cached_verification": None,
            }
        )
        snap = load_db_ready_operational_snapshot(reload_db=False)
        self.assertEqual(snap.get("startup_warm_status"), "running")


if __name__ == "__main__":
    unittest.main()
