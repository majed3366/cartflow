# -*- coding: utf-8 -*-
"""MERCHANT_UI_PRODUCTION_CONFIG_PARITY_REGRESSION_GATE — fail-closed cases A–E."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app
from services.merchant_ui_config_parity_v1 import (
    FLAG_CARTS_V2_UI,
    FLAG_CART_WORKSPACE_V1,
    FLAG_MERCHANT_UI_V2,
    INVARIANT_ID,
    MATERIAL_FLAG_REGISTRY,
    MERCHANT_UI_CONFIG_VERSION,
    PRODUCTION_MERCHANT_UI_CONFIG,
    REGRESSION_GATE,
    compare_merchant_ui_config_parity,
    evaluate_config_parity,
    material_flag_names,
    production_merchant_ui_config_identity,
    review_merchant_ui_config_identity,
)
from services.merchant_visual_deploy_authorization_v1 import (
    DEPLOY_AUTH_GATE,
    evaluate_merchant_visual_deploy_authorization,
)


def _prod_like_env(**overrides: str) -> dict[str, str]:
    """Explicit production-equivalent effective ON without relying on Railway SHA."""
    base = {
        FLAG_CART_WORKSPACE_V1: "true",
        FLAG_MERCHANT_UI_V2: "1",
        FLAG_CARTS_V2_UI: "1",
    }
    base.update(overrides)
    return base


class MaterialFlagRegistryTests(unittest.TestCase):
    def test_registry_includes_required_flags(self) -> None:
        names = material_flag_names()
        self.assertIn(FLAG_CART_WORKSPACE_V1, names)
        self.assertIn(FLAG_MERCHANT_UI_V2, names)
        self.assertIn(FLAG_CARTS_V2_UI, names)
        self.assertEqual(len(names), len(MATERIAL_FLAG_REGISTRY))
        self.assertEqual(len(names), 3)

    def test_production_identity_inspectable(self) -> None:
        prod = production_merchant_ui_config_identity()
        self.assertEqual(prod["merchant_ui_config_version"], MERCHANT_UI_CONFIG_VERSION)
        self.assertEqual(prod["invariant"], INVARIANT_ID)
        self.assertTrue(prod["resolved"])
        self.assertEqual(prod["material_flags"], PRODUCTION_MERCHANT_UI_CONFIG)
        self.assertNotIn("SECRET_KEY", str(prod))
        self.assertNotIn("password", str(prod).lower())


class ConfigParityCases(unittest.TestCase):
    """CASE A–E from Merchant UI Production Config Parity Regression Gate V1."""

    def test_case_a_review_equals_production_pass(self) -> None:
        result = compare_merchant_ui_config_parity(env=_prod_like_env())
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["ok"])
        self.assertTrue(result["review_equals_production"])
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(result["gate"], REGRESSION_GATE)

    def test_case_b_one_material_flag_differs_fail(self) -> None:
        env = _prod_like_env(**{FLAG_CART_WORKSPACE_V1: "false"})
        result = compare_merchant_ui_config_parity(env=env)
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["ok"])
        flags = {m["flag"] for m in result["mismatches"]}
        self.assertIn(FLAG_CART_WORKSPACE_V1, flags)

    def test_case_c_raw_differs_effective_equal_pass(self) -> None:
        # Production contract: Workspace effective True.
        # Review: unset Workspace + Railway SHA → same effective True (raw differs).
        env = {
            FLAG_MERCHANT_UI_V2: "",  # unset → default ON
            FLAG_CARTS_V2_UI: "yes",  # alternate truthy spelling
            "RAILWAY_GIT_COMMIT_SHA": "b8c1318a06e99fe75eccefecf7e4492db489ab4d",
        }
        # Explicitly omit CARTFLOW_CART_WORKSPACE_V1
        self.assertNotIn(FLAG_CART_WORKSPACE_V1, env)
        result = compare_merchant_ui_config_parity(env=env)
        self.assertEqual(result["status"], "pass", result)
        self.assertTrue(result["review"]["material_flags"][FLAG_CART_WORKSPACE_V1])
        self.assertTrue(result["review"]["material_flags"][FLAG_MERCHANT_UI_V2])
        self.assertTrue(result["review"]["material_flags"][FLAG_CARTS_V2_UI])

    def test_case_d_unresolved_effective_fail_closed(self) -> None:
        # CARTS_V2_UI with unrecognized non-empty token → effective None → fail closed.
        env = _prod_like_env(**{FLAG_CARTS_V2_UI: "maybe"})
        result = compare_merchant_ui_config_parity(env=env)
        self.assertEqual(result["status"], "fail")
        reasons = {m["reason"] for m in result["mismatches"]}
        self.assertIn("unresolved_effective_value", reasons)

        # Direct None injection also fail-closed.
        review = dict(PRODUCTION_MERCHANT_UI_CONFIG)
        review[FLAG_MERCHANT_UI_V2] = None
        result2 = compare_merchant_ui_config_parity(review=review)
        self.assertEqual(result2["status"], "fail")

    def test_case_e_unrelated_non_merchant_ui_env_ignored(self) -> None:
        env = _prod_like_env()
        env["SECRET_KEY"] = "not-a-material-flag"
        env["CARTFLOW_OBSERVABILITY_MODE"] = "debug"
        env["ENV"] = "development"
        result = compare_merchant_ui_config_parity(env=env)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["mismatches"], [])


class DeployAuthorizationIntegration(unittest.TestCase):
    def test_config_parity_required_for_safe_deploy(self) -> None:
        blocked = evaluate_merchant_visual_deploy_authorization(
            visual_contracts="pass",
            semantic_regression="pass",
            real_device_review="pass",
            production_config_parity="fail",
        )
        self.assertEqual(blocked["gate"], DEPLOY_AUTH_GATE)
        self.assertFalse(blocked["safe_for_exact_sha_deploy"])
        self.assertEqual(blocked["safe_for_exact_sha_deploy_label"], "NO")
        self.assertIn("production_config_parity", blocked["failed_axes"])

        allowed = evaluate_merchant_visual_deploy_authorization(
            visual_contracts="pass",
            semantic_regression="pass",
            real_device_review="pass",
            production_config_parity="pass",
        )
        self.assertTrue(allowed["safe_for_exact_sha_deploy"])
        self.assertEqual(allowed["safe_for_exact_sha_deploy_label"], "YES")

    def test_live_env_mismatch_blocks_deploy(self) -> None:
        env = _prod_like_env(**{FLAG_CART_WORKSPACE_V1: "false"})
        auth = evaluate_merchant_visual_deploy_authorization(
            visual_contracts="pass",
            semantic_regression="pass",
            real_device_review="pass",
            env=env,
        )
        self.assertFalse(auth["safe_for_exact_sha_deploy"])
        self.assertEqual(auth["axes"]["production_config_parity"], "fail")


class RuntimeIdentityProbe(unittest.TestCase):
    def test_identity_exposes_config_parity_fields(self) -> None:
        with patch.dict(
            os.environ,
            {
                FLAG_CART_WORKSPACE_V1: "true",
                FLAG_MERCHANT_UI_V2: "1",
                FLAG_CARTS_V2_UI: "1",
            },
            clear=False,
        ):
            # Drop Railway SHA so explicit true is the Workspace path.
            os.environ.pop("RAILWAY_GIT_COMMIT_SHA", None)
            probe = TestClient(app).get("/dev/merchant-runtime-identity").json()
        self.assertEqual(probe.get("merchant_ui_config_version"), MERCHANT_UI_CONFIG_VERSION)
        self.assertEqual(probe.get("merchant_ui_config_parity_gate"), REGRESSION_GATE)
        self.assertIn(FLAG_CART_WORKSPACE_V1, probe.get("merchant_ui_material_flags") or {})
        self.assertEqual(probe.get("merchant_ui_config_parity"), "pass")
        self.assertTrue(probe.get("merchant_ui_config_parity_ok"))

    def test_local_default_workspace_off_fails_parity_on_identity(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG_CART_WORKSPACE_V1, None)
            os.environ.pop("RAILWAY_GIT_COMMIT_SHA", None)
            # Ensure V2 + Carts remain production-like so only Workspace mismatches.
            os.environ[FLAG_MERCHANT_UI_V2] = "1"
            os.environ[FLAG_CARTS_V2_UI] = "1"
            review = review_merchant_ui_config_identity()
            result = evaluate_config_parity()
        self.assertFalse(review["material_flags"][FLAG_CART_WORKSPACE_V1])
        self.assertEqual(result["status"], "fail")


if __name__ == "__main__":
    unittest.main()
