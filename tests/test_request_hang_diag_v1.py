# -*- coding: utf-8 -*-
"""Request hang diagnostics v1 — stage logs + refresh-state wall guard."""
from __future__ import annotations

import io
import time
import unittest
import uuid
from contextlib import redirect_stdout
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from extensions import db
from models import Store
from services.dashboard_refresh_state_guard_v1 import (
    clear_refresh_state_guard_for_tests,
    refresh_state_guard_begin,
    refresh_state_log_stage,
    refresh_state_minimal_payload,
    refresh_state_wall_budget_s,
)
from services.demo_store_request_diag_v1 import (
    begin_demo_store_trace,
    demo_store_log_stage,
)
from services.request_hang_diag_v1 import clear_hang_trace_for_tests


class _FakeUrl:
    def __init__(self, path: str) -> None:
        self.path = path


class _FakeRequest:
    method = "GET"

    def __init__(self, path: str, query: dict[str, str] | None = None) -> None:
        self.url = _FakeUrl(path)
        self.query_params = query or {}


class RequestHangDiagV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        clear_hang_trace_for_tests()
        clear_refresh_state_guard_for_tests()

    def tearDown(self) -> None:
        clear_hang_trace_for_tests()
        clear_refresh_state_guard_for_tests()

    def test_demo_store_stage_log_format(self) -> None:
        req = _FakeRequest(
            "/demo/store",
            {"merchant_activation": "1", "reset_demo": "1", "store_slug": "shop-a"},
        )
        begin_demo_store_trace(req)
        buf = io.StringIO()
        with redirect_stdout(buf):
            demo_store_log_stage("request_entered", request=req)
            demo_store_log_stage("guard_done", request=req)
            demo_store_log_stage("response_ready", request=req)
        text = buf.getvalue()
        self.assertIn("[DEMO STORE STAGE]", text)
        self.assertIn("stage=request_entered", text)
        self.assertIn("merchant_activation=1", text)
        self.assertIn("reset_demo=1", text)
        self.assertIn("store_slug=shop-a", text)
        self.assertIn("trace_id=", text)
        self.assertIn("elapsed_ms=", text)

    def test_refresh_state_stage_log_format(self) -> None:
        req = _FakeRequest("/api/dashboard/refresh-state")
        refresh_state_guard_begin(req)
        buf = io.StringIO()
        with redirect_stdout(buf):
            refresh_state_log_stage("request_entered", store_slug="demo-shop")
            refresh_state_log_stage(
                "db_ready_done",
                store_slug="demo-shop",
                stage_t0=time.perf_counter(),
            )
        text = buf.getvalue()
        self.assertIn("[REFRESH STATE STAGE]", text)
        self.assertIn("stage=request_entered", text)
        self.assertIn("store_slug=demo-shop", text)
        self.assertIn("stage_elapsed_ms=", text)

    def test_refresh_state_minimal_payload_shape(self) -> None:
        out = refresh_state_minimal_payload(store_slug="my-store", stage="db_ready_done")
        self.assertEqual(out["merchant_dashboard_refresh_last_log_id"], 0)
        self.assertEqual(out["merchant_dashboard_refresh_sent_total"], 0)
        self.assertTrue(out["refresh_state_partial"])
        self.assertIn("my-store:partial:0:0:0", out["merchant_dashboard_refresh_token"])

    def test_demo_store_route_emits_stage_logs(self) -> None:
        client = TestClient(main.app)
        buf = io.StringIO()
        with redirect_stdout(buf):
            r = client.get(
                "/demo/store",
                params={"merchant_activation": "0"},
            )
        self.assertEqual(r.status_code, 200)
        text = buf.getvalue()
        self.assertIn("[DEMO STORE STAGE] stage=request_entered", text)
        self.assertIn("[DEMO STORE STAGE] stage=response_ready", text)

    def test_refresh_state_deadline_returns_minimal_ok(self) -> None:
        slug = f"hang-diag-{uuid.uuid4().hex[:8]}"
        st = Store(zid_store_id=slug, recovery_delay=1, recovery_delay_unit="minutes")
        db.create_all()
        db.session.add(st)
        db.session.commit()
        client = TestClient(main.app)
        buf = io.StringIO()

        def _slow_ready() -> None:
            # Wall budget clamps to >= 1.0s; exceed it inside db_ready.
            time.sleep(1.15)

        with patch.dict("os.environ", {"ENV": "development", "CARTFLOW_REFRESH_STATE_WALL_BUDGET_S": "1"}):
            with patch("main._merchant_dashboard_db_ready", side_effect=_slow_ready):
                with patch("main._dashboard_recovery_store_row", return_value=st):
                    with redirect_stdout(buf):
                        r = client.get("/api/dashboard/refresh-state")
        self.assertEqual(r.status_code, 200)
        body = r.json() or {}
        self.assertTrue(body.get("ok"))
        self.assertTrue(body.get("refresh_state_partial"))
        self.assertIn("partial:0:0:0", str(body.get("merchant_dashboard_refresh_token") or ""))
        text = buf.getvalue()
        self.assertIn("[REFRESH STATE DEADLINE EXCEEDED]", text)

    def test_refresh_state_wall_budget_default(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            self.assertGreaterEqual(refresh_state_wall_budget_s(), 1.0)


if __name__ == "__main__":
    unittest.main()
