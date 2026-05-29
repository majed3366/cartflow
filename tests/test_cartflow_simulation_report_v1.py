# -*- coding: utf-8 -*-
"""Dry-run multi-store CartFlow simulation report."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from extensions import db
from main import app
from models import AbandonedCart, CartRecoveryLog, Store
from services.cartflow_simulation_report_v1 import (
    SIM_STORE_PREFIX,
    cleanup_simulation_data,
    is_simulation_store_slug,
    run_cartflow_simulation_report,
    sim_store_slug,
)


class CartflowSimulationReportTests(unittest.TestCase):
    def setUp(self) -> None:
        from services.dashboard_normal_carts_guard_v1 import (  # noqa: PLC0415
            dashboard_nc_guard_begin,
        )

        dashboard_nc_guard_begin()
        db.create_all()
        cleanup_simulation_data()

    def tearDown(self) -> None:
        cleanup_simulation_data()

    def test_sim_slug_helper(self) -> None:
        self.assertEqual(sim_store_slug(1), "sim-store-001")
        self.assertTrue(is_simulation_store_slug("sim-store-042"))
        self.assertFalse(is_simulation_store_slug("demo"))

    def test_two_store_report_all_pass(self) -> None:
        with patch("main.send_whatsapp") as mock_send:
            with patch("main.recovery_uses_real_whatsapp", return_value=False):
                report = run_cartflow_simulation_report(stores=2, dry_run=True)
        mock_send.assert_not_called()
        self.assertTrue(report.get("dry_run"))
        self.assertEqual(report.get("total_stores"), 2)
        if report.get("fail_count"):
            self.fail(str(report.get("failed_cases")))
        self.assertEqual(report.get("pass_count"), 2)
        self.assertEqual(report.get("fail_count"), 0)
        self.assertTrue(report.get("ok"))
        self.assertFalse(report.get("whatsapp_sent"))
        self.assertFalse(report.get("production_merchants_touched"))
        summaries = report.get("per_store_summary") or []
        self.assertEqual(len(summaries), 2)
        self.assertIsInstance(report.get("avg_lifecycle_ms"), (int, float))
        self.assertGreater(float(report.get("avg_lifecycle_ms") or 0), 0.0)
        tb = report.get("timing_breakdown") or {}
        for key in (
            "setup_ms",
            "template_save_ms",
            "schedule_create_ms",
            "simulated_send_ms",
            "dashboard_check_ms",
            "reply_check_ms",
            "return_check_ms",
            "purchase_check_ms",
            "cleanup_or_commit_ms",
            "initial_cleanup_ms",
        ):
            self.assertIn(key, tb)
            self.assertIsInstance(tb[key], (int, float))
        self.assertTrue(report.get("slowest_store"))
        self.assertTrue(report.get("slowest_stage"))
        dpr = report.get("deep_profile_report") or {}
        self.assertIn("dashboard_check_ms", dpr)
        self.assertIn("purchase_check_ms", dpr)
        self.assertIn("top_slowest_functions", dpr)
        self.assertGreaterEqual(len(dpr.get("top_slowest_functions") or []), 1)
        dash_bd = (dpr.get("dashboard_check_ms") or {}).get("breakdown_ms") or {}
        for key in ("db_ms", "lifecycle_ms", "grouping_ms", "merge_ms", "other_ms"):
            self.assertIn(key, dash_bd)
        purch_bd = (dpr.get("purchase_check_ms") or {}).get("breakdown_ms") or {}
        for key in (
            "record_truth_ms",
            "lifecycle_closure_ms",
            "reconcile_active_carts_ms",
            "dashboard_after_purchase_ms",
        ):
            self.assertIn(key, purch_bd)
        for row in summaries:
            self.assertTrue(row.get("pass"))
            self.assertTrue(row.get("template_saved"))
            self.assertEqual(row.get("configured_count"), 2)
            self.assertEqual(row.get("dashboard_bucket_after_2_of_2"), "sent")
            self.assertEqual(row.get("purchase_state"), "completed")
            self.assertGreater(float(row.get("per_store_elapsed_ms") or 0), 0.0)
            self.assertIn("timing", row)
            self.assertIn("slowest_stage", row)

    def test_stores_above_10_without_expanded_rejected(self) -> None:
        report = run_cartflow_simulation_report(stores=20, dry_run=True, expanded=False)
        self.assertFalse(report.get("ok"))
        self.assertIn("expanded", str(report.get("error") or ""))

    def test_cleanup_removes_sim_stores(self) -> None:
        run_cartflow_simulation_report(stores=1, dry_run=True)
        self.assertGreater(
            db.session.query(Store)
            .filter(Store.zid_store_id.like(f"{SIM_STORE_PREFIX}%"))
            .count(),
            0,
        )
        out = cleanup_simulation_data()
        self.assertTrue(out.get("ok"))
        self.assertEqual(
            db.session.query(Store)
            .filter(Store.zid_store_id.like(f"{SIM_STORE_PREFIX}%"))
            .count(),
            0,
        )

    def test_dev_endpoint_dry_run(self) -> None:
        client = TestClient(app)
        with patch("main.send_whatsapp") as mock_send:
            res = client.get(
                "/dev/cartflow-simulation-report",
                params={"stores": 2, "dry_run": "true"},
            )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("pass_count"), 2)
        mock_send.assert_not_called()

    def test_sim_logs_marked_simulation(self) -> None:
        run_cartflow_simulation_report(stores=1, dry_run=True)
        slug = sim_store_slug(1)
        logs = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == slug)
            .all()
        )
        self.assertGreater(len(logs), 0)
        for lg in logs:
            self.assertEqual((lg.source or "").strip(), "simulation")

    def test_no_demo_store_modified(self) -> None:
        demo_before = (
            db.session.query(Store).filter(Store.zid_store_id == "demo").count()
        )
        run_cartflow_simulation_report(stores=1, dry_run=True)
        demo_after = (
            db.session.query(Store).filter(Store.zid_store_id == "demo").count()
        )
        self.assertEqual(demo_before, demo_after)
        ac_demo = (
            db.session.query(AbandonedCart)
            .join(Store, AbandonedCart.store_id == Store.id)
            .filter(Store.zid_store_id == "demo")
            .count()
        )
        self.assertEqual(ac_demo, 0)
