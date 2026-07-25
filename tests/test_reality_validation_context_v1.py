# -*- coding: utf-8 -*-
"""Reality Validation Identity Certification V1."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("ENV", "development")
os.environ.setdefault("CARTFLOW_ALLOW_TESTCLIENT", "1")


_COUNTS_OK = {
    "observation_count": 4,
    "foundation_ready_count": 4,
    "business_fact_count": 6,
    "situation_count": 4,
    "situation_ids": ["a", "b", "c", "d"],
    "home_projection": 4,
    "workspace_projection": 3,
    "products_projection": 3,
    "carts_projection": 2,
    "communication_projection": 1,
    "home_situation_ids": ["a", "b", "c", "d"],
    "workspace_situation_ids": ["a", "b", "c"],
    "products_situation_ids": ["a", "b", "c"],
    "carts_situation_ids": ["a", "b"],
    "communication_situation_ids": ["d"],
    "orv_store_slug": "demo",
    "facts_store_slug": "demo",
    "situations_store_slug": "demo",
}


class DetectEnvironmentTests(unittest.TestCase):
    def test_sqlite_development(self) -> None:
        from services.reality_validation_context_v1 import (
            detect_database_environment_v1,
        )

        env = detect_database_environment_v1(
            environ={"ENV": "development", "DATABASE_URL": "sqlite:///tmp.db"}
        )
        self.assertEqual(env["environment"], "development")
        self.assertIn("sqlite", env["database_environment"])


class AllowlistTests(unittest.TestCase):
    def test_dev_route_allowlisted(self) -> None:
        from main import _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT

        self.assertIn(
            "/dev/reality-validation-context",
            _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT,
        )
        self.assertIn(
            "/dev/reality-validation-console",
            _DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT,
        )


class CertificationTests(unittest.TestCase):
    def test_missing_simulation_inconsistent_and_unsafe(self) -> None:
        from services.reality_validation_context_v1 import (
            build_reality_validation_context_v1,
        )

        with patch(
            "services.reality_validation_context_v1._latest_living_store_run",
            return_value={
                "simulation_run_id": None,
                "living_store_profile": None,
                "last_simulation_timestamp": None,
                "store_slug": "demo",
                "status": None,
                "source": None,
            },
        ), patch(
            "services.reality_validation_context_v1._merchant_session_identity",
            return_value={
                "store_slug": "demo",
                "merchant_id": "1",
                "email": "x@y.z",
                "session_resolves_to": "demo",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._dataset_counts",
            return_value=dict(_COUNTS_OK),
        ):
            ctx = build_reality_validation_context_v1(
                store_slug="demo", cookies={"cf": "1"}
            )
        self.assertEqual(ctx["status"], "INCONSISTENT")
        self.assertFalse(ctx["CEO_REVIEW_SAFE"])
        self.assertEqual(ctx["divergence_begins_at"], "canonical.simulation_run_id")
        self.assertIn("simulation_run_missing", ctx["CEO_REVIEW_SAFE_reasons"])
        self.assertTrue(ctx["recommendation"])

    def test_consistent_but_not_safe_outside_production(self) -> None:
        from services.reality_validation_context_v1 import (
            build_reality_validation_context_v1,
        )

        with patch(
            "services.reality_validation_context_v1._latest_living_store_run",
            return_value={
                "simulation_run_id": "srs_test",
                "living_store_profile": "living_store",
                "last_simulation_timestamp": "2026-07-25T12:00:00+00:00",
                "store_slug": "demo",
                "status": "completed",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._merchant_session_identity",
            return_value={
                "store_slug": "demo",
                "merchant_id": "42",
                "email": "cf.living.store.review@smartreplyai.net",
                "session_resolves_to": "demo",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._dataset_counts",
            return_value=dict(_COUNTS_OK),
        ), patch(
            "services.reality_validation_context_v1.detect_database_environment_v1",
            return_value={
                "environment": "development",
                "database_environment": "development:sqlite",
                "app_env": "development",
                "db_dialect": "sqlite",
                "db_host": "local",
                "productionish": False,
            },
        ):
            ctx = build_reality_validation_context_v1(
                store_slug="demo", cookies={"cf": "1"}
            )
        self.assertEqual(ctx["status"], "CONSISTENT")
        self.assertFalse(ctx["CEO_REVIEW_SAFE"])
        self.assertIn("environment_not_production", ctx["CEO_REVIEW_SAFE_reasons"])

    def test_ceo_review_safe_true_on_production_aligned(self) -> None:
        from services.reality_validation_context_v1 import (
            build_reality_validation_context_v1,
        )

        with patch(
            "services.reality_validation_context_v1._latest_living_store_run",
            return_value={
                "simulation_run_id": "srs_test",
                "living_store_profile": "living_store",
                "last_simulation_timestamp": "2026-07-25T12:00:00+00:00",
                "store_slug": "demo",
                "status": "completed",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._merchant_session_identity",
            return_value={
                "store_slug": "demo",
                "merchant_id": "42",
                "email": "cf.living.store.review@smartreplyai.net",
                "session_resolves_to": "demo",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._dataset_counts",
            return_value=dict(_COUNTS_OK),
        ), patch(
            "services.reality_validation_context_v1.detect_database_environment_v1",
            return_value={
                "environment": "production",
                "database_environment": "production:postgresql",
                "app_env": "production",
                "db_dialect": "postgresql",
                "db_host": "db",
                "productionish": True,
            },
        ):
            ctx = build_reality_validation_context_v1(
                store_slug="demo", cookies={"sid": "1"}
            )
        self.assertEqual(ctx["status"], "CONSISTENT")
        self.assertTrue(ctx["CEO_REVIEW_SAFE"])
        self.assertEqual(ctx["CEO_REVIEW_SAFE_reasons"], [])
        self.assertTrue(ctx["ok"])
        marks = {r["row"]: r["ok"] for r in ctx["identity_matrix"]}
        self.assertTrue(marks["Environment"])
        self.assertTrue(marks["Database"])
        self.assertTrue(marks["Store Slug"])
        self.assertTrue(marks["Merchant Session"])
        self.assertTrue(marks["Simulation Run"])
        self.assertTrue(marks["Home"])
        self.assertTrue(marks["Workspace"])

    def test_session_mismatch_divergence_report(self) -> None:
        from services.reality_validation_context_v1 import (
            build_reality_validation_context_v1,
        )

        with patch(
            "services.reality_validation_context_v1._latest_living_store_run",
            return_value={
                "simulation_run_id": "srs_test",
                "living_store_profile": "living_store",
                "last_simulation_timestamp": "2026-07-25T12:00:00+00:00",
                "store_slug": "demo",
                "status": "completed",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._merchant_session_identity",
            return_value={
                "store_slug": "merchant_abc",
                "merchant_id": "42",
                "email": "x@y.z",
                "session_resolves_to": "merchant_abc",
                "source": "test",
            },
        ), patch(
            "services.reality_validation_context_v1._dataset_counts",
            return_value=dict(_COUNTS_OK),
        ), patch(
            "services.reality_validation_context_v1.detect_database_environment_v1",
            return_value={
                "environment": "production",
                "database_environment": "production:postgresql",
                "app_env": "production",
                "db_dialect": "postgresql",
                "db_host": "db",
                "productionish": True,
            },
        ):
            ctx = build_reality_validation_context_v1(
                store_slug="demo", cookies={"sid": "1"}
            )
        self.assertEqual(ctx["status"], "INCONSISTENT")
        self.assertFalse(ctx["CEO_REVIEW_SAFE"])
        self.assertEqual(
            ctx["divergence_begins_at"],
            "authenticated_merchant_session.store_slug",
        )
        self.assertEqual(ctx["expected_value"], "demo")
        self.assertEqual(ctx["actual_value"], "merchant_abc")
        self.assertTrue(ctx["affected_surfaces"])
        self.assertTrue(ctx["recommendation"])

    def test_html_certificate_contains_safe_banner(self) -> None:
        from services.reality_validation_context_v1 import render_certification_html_v1

        html = render_certification_html_v1(
            {
                "status": "CONSISTENT",
                "CEO_REVIEW_SAFE": True,
                "store_slug": "demo",
                "merchant_id": "1",
                "simulation_run_id": "srs_x",
                "observations": 4,
                "facts": 6,
                "situations": 4,
                "identity_matrix": [
                    {"row": "Environment", "ok": True, "mark": "✔", "value": "production"}
                ],
                "constitutional_rule": "No review without certification.",
                "composed_at_utc": "2026-07-25T00:00:00+00:00",
            }
        )
        self.assertIn("CEO_REVIEW_SAFE = TRUE", html)
        self.assertIn("Status = CONSISTENT", html)


if __name__ == "__main__":
    unittest.main()
