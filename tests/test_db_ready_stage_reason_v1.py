# -*- coding: utf-8 -*-
"""Root-cause probes for DB Ready stages (Step 4B.2)."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from services.db_ready_stage_reason_v1 import (
    build_tracked_classifications,
    probe_bootstrap_merchant_auth_reason,
    probe_identity_backfill_register_reason,
    probe_identity_backfill_reason,
    probe_production_schema_reason,
    probe_widget_schema_reason,
)


class DbReadyStageReasonV1Tests(unittest.TestCase):
    def test_probe_widget_schema_cache_miss(self) -> None:
        with patch("schema_widget.store_widget_schema_warm_done", return_value=False):
            self.assertEqual(probe_widget_schema_reason(), "cache_miss")

    def test_probe_widget_schema_cache_hit_skip(self) -> None:
        with patch("schema_widget.store_widget_schema_warm_done", return_value=True):
            self.assertEqual(probe_widget_schema_reason(), "cache_hit_skip")

    def test_probe_production_schema_verification_required(self) -> None:
        with patch(
            "schema_production_store_bootstrap.production_store_bootstrap_verified",
            return_value=True,
        ):
            self.assertEqual(
                probe_production_schema_reason(context="dashboard"),
                "verification_required",
            )

    def test_probe_production_schema_cold_start(self) -> None:
        with patch(
            "schema_production_store_bootstrap.production_store_bootstrap_verified",
            return_value=False,
        ):
            with patch("main._cartflow_api_db_warmed", False, create=True):
                self.assertEqual(
                    probe_production_schema_reason(context="startup"),
                    "cold_start",
                )

    def test_probe_production_schema_dashboard_not_verified(self) -> None:
        with patch(
            "schema_production_store_bootstrap.production_store_bootstrap_verified",
            return_value=False,
        ):
            with patch("main._cartflow_api_db_warmed", True, create=True):
                self.assertEqual(
                    probe_production_schema_reason(context="dashboard"),
                    "bootstrap_not_verified",
                )

    def test_probe_identity_backfill_always_run_on_cold_warm(self) -> None:
        with patch("main._cartflow_api_db_warmed", False, create=True):
            self.assertEqual(probe_identity_backfill_reason(), "always_run_on_cold_warm")

    def test_probe_identity_backfill_register_reasons(self) -> None:
        self.assertEqual(
            probe_identity_backfill_register_reason(rows_scanned=0),
            "no_stores_to_scan",
        )
        self.assertEqual(
            probe_identity_backfill_register_reason(rows_scanned=10, rows_inserted=0),
            "aliases_already_present",
        )
        self.assertEqual(
            probe_identity_backfill_register_reason(rows_scanned=10, rows_inserted=3),
            "backfill_needed",
        )

    def test_probe_bootstrap_merchant_auth_cache_miss(self) -> None:
        with patch("schema_merchant_auth.merchant_auth_schema_warm_done", return_value=False):
            with patch(
                "schema_merchant_auth.verify_merchant_auth_schema",
                return_value={"missing_columns": []},
            ):
                self.assertEqual(probe_bootstrap_merchant_auth_reason(), "cache_miss")

    def test_build_tracked_classifications_order_and_fields(self) -> None:
        rows = [
            {"stage": "widget_schema", "reason": "cache_miss", "query_count": 606},
            {"stage": "identity_backfill_register", "reason": "backfill_needed", "query_count": 128,
             "rows_scanned": 45, "rows_inserted": 12},
            {"stage": "noise_stage", "reason": "ignored", "query_count": 1},
        ]
        out = build_tracked_classifications(rows)
        self.assertEqual([r["stage"] for r in out], ["widget_schema", "identity_backfill_register"])
        self.assertEqual(out[0]["reason"], "cache_miss")
        self.assertEqual(out[1]["rows_scanned"], 45)
        self.assertEqual(out[1]["rows_inserted"], 12)


if __name__ == "__main__":
    unittest.main()
