# -*- coding: utf-8 -*-
"""First-100 DB Resource Safety V1 — contracts + concurrent equilibrium."""
from __future__ import annotations

import concurrent.futures
import os
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from services.db_resource_safety_v1.admission_v1 import (
    HEAVY_GLOBAL_LIMIT,
    admit_heavy_route,
    release,
    reset_for_tests,
    snapshot as admission_snapshot,
    try_acquire,
)
from services.db_resource_safety_v1.hold_budget_v1 import (
    CLASS_CRITICAL,
    CLASS_FAST,
    CLASS_HEAVY,
    CLASS_UNSAFE,
    classify_hold_ms,
    verdict_for_route,
)
from services.db_resource_safety_v1.query_bounds_v1 import (
    CUSTOMER_REPLY_MAP_LIMIT,
    MESSAGE_LOG_PHONE_BULK_LIMIT,
    MESSAGES_FETCH_CAP,
    RECOVERY_SCHEDULE_BULK_LIMIT,
)

ROOT = Path(__file__).resolve().parents[1]
MAIN_PY = (ROOT / "main.py").read_text(encoding="utf-8")
OPS_PY = (ROOT / "routes" / "ops.py").read_text(encoding="utf-8")
WA_PY = (ROOT / "services" / "whatsapp_provider.py").read_text(encoding="utf-8")
ZID_PY = (ROOT / "integrations" / "zid_client.py").read_text(encoding="utf-8")
PROJ_PY = (ROOT / "services" / "cart_workspace" / "merchant_api_v1.py").read_text(
    encoding="utf-8"
)
APP_JS = (ROOT / "static" / "merchant_ui_v2_app.js").read_text(encoding="utf-8")
SETTINGS_JS = (ROOT / "static" / "merchant_ui_v2_settings.js").read_text(
    encoding="utf-8"
)


class First100HoldBudgetTests(unittest.TestCase):
    def test_hold_classes(self) -> None:
        self.assertEqual(classify_hold_ms(100), CLASS_FAST)
        self.assertEqual(classify_hold_ms(800), "NORMAL")
        self.assertEqual(classify_hold_ms(2000), CLASS_HEAVY)
        self.assertEqual(classify_hold_ms(4000), CLASS_UNSAFE)
        self.assertEqual(
            classify_hold_ms(100, network_while_held=True), CLASS_CRITICAL
        )

    def test_justified_heavy_vs_violation(self) -> None:
        self.assertEqual(
            verdict_for_route("/api/dashboard/messages", 2000),
            "JUSTIFIED_HEAVY",
        )
        self.assertEqual(verdict_for_route("/login", 2000), "VIOLATION")
        self.assertEqual(
            verdict_for_route("/api/dashboard/messages", 100, network_while_held=True),
            "VIOLATION",
        )


class First100AdmissionTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_for_tests()

    def tearDown(self) -> None:
        reset_for_tests()

    def test_global_cap_rejects(self) -> None:
        held = []
        for i in range(HEAVY_GLOBAL_LIMIT):
            self.assertTrue(try_acquire(f"/r{i}"))
            held.append(f"/r{i}")
        self.assertFalse(try_acquire("/overflow"))
        self.assertGreaterEqual(admission_snapshot()["rejected"], 1)
        for route in held:
            release(route)
        self.assertEqual(admission_snapshot()["global_in_use"], 0)

    def test_per_route_cap(self) -> None:
        with admit_heavy_route("/same") as a:
            self.assertTrue(a)
            with admit_heavy_route("/same") as b:
                self.assertTrue(b)
                with admit_heavy_route("/same") as c:
                    self.assertFalse(c)
        self.assertEqual(admission_snapshot()["global_in_use"], 0)


class First100SourceContractsTests(unittest.TestCase):
    def test_query_bounds_wired(self) -> None:
        self.assertIn("RECOVERY_SCHEDULE_BULK_LIMIT", MAIN_PY)
        self.assertIn("MESSAGE_LOG_PHONE_BULK_LIMIT", MAIN_PY)
        self.assertIn("CUSTOMER_REPLY_MAP_LIMIT", MAIN_PY)
        self.assertIn("MESSAGES_FETCH_CAP", MAIN_PY)
        self.assertGreaterEqual(RECOVERY_SCHEDULE_BULK_LIMIT, 100)
        self.assertGreaterEqual(MESSAGE_LOG_PHONE_BULK_LIMIT, 100)
        self.assertGreaterEqual(CUSTOMER_REPLY_MAP_LIMIT, 40)
        self.assertLessEqual(MESSAGES_FETCH_CAP, 80)

    def test_release_before_wait_choke_points(self) -> None:
        self.assertIn("release_before_external_wait", WA_PY)
        self.assertIn("release_before_external_wait", ZID_PY)
        self.assertIn("_zid_get", ZID_PY)
        self.assertIn("return requests.get", ZID_PY)

    def test_health_survivability_wired(self) -> None:
        self.assertIn("pool_pressure_blocks_db_probe", OPS_PY)
        self.assertIn("pool_pressure", OPS_PY)

    def test_heavy_admission_wired(self) -> None:
        self.assertIn("admit_heavy_route", MAIN_PY)
        self.assertIn("admit_heavy_route", PROJ_PY)

    def test_lazy_init_and_settings_queuepool_preserved(self) -> None:
        self.assertIn("SURFACE_PRODUCT_INIT", APP_JS)
        self.assertIn("settings-queuepool-pressure-remediation-v1", SETTINGS_JS)
        self.assertNotIn("Promise.all", SETTINGS_JS)


class First100CriticalRoutesTests(unittest.TestCase):
    def test_ping_health_login(self) -> None:
        c = TestClient(app)
        ping = c.get("/ping")
        self.assertEqual(ping.status_code, 200)
        self.assertTrue((ping.json() or {}).get("ok"))
        health = c.get("/health")
        self.assertEqual(health.status_code, 200)
        login = c.get("/login")
        self.assertEqual(login.status_code, 200)

    def test_health_db_probe_local(self) -> None:
        c = TestClient(app)
        r = c.get("/health?db=1")
        self.assertIn(r.status_code, (200, 503))
        body = r.json() or {}
        if r.status_code == 200:
            self.assertTrue(body.get("ok"))
        else:
            self.assertIn(body.get("database"), ("error", "pool_pressure"))


class First100BurstEquilibriumTests(unittest.TestCase):
    def test_ping_burst_returns_to_idle_admission(self) -> None:
        reset_for_tests()
        c = TestClient(app)

        def hit(_n: int) -> int:
            return c.get("/ping").status_code

        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
            codes = list(ex.map(hit, range(50)))
        elapsed = time.perf_counter() - t0
        self.assertTrue(all(code == 200 for code in codes))
        self.assertEqual(admission_snapshot()["global_in_use"], 0)
        self.assertLess(elapsed, 30.0)


if __name__ == "__main__":
    unittest.main()
