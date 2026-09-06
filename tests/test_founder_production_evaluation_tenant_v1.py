# -*- coding: utf-8 -*-
"""Founder Production Evaluation Tenant V1 — production-scope hardening tests."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class ProductionAllowlistOwnershipTests(unittest.TestCase):
    def test_allowlist_is_exactly_one_identity(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
            PRODUCTION_EVALUATION_ALLOWLIST,
        )

        self.assertEqual(len(PRODUCTION_EVALUATION_ALLOWLIST), 1)
        self.assertEqual(
            set(PRODUCTION_EVALUATION_ALLOWLIST), {FOUNDER_EVAL_STORE_SLUG}
        )
        self.assertEqual(FOUNDER_EVAL_STORE_SLUG, "cf_founder_evaluation")

    def test_owner_function_name(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            is_founder_evaluation_tenant,
            is_founder_production_evaluation_tenant,
        )

        self.assertIs(
            is_founder_evaluation_tenant, is_founder_production_evaluation_tenant
        )

    def test_authenticated_store_overrides_caller_slug(self) -> None:
        """Caller cannot override store identity when Store row is supplied."""
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_INTEGRATION_SOURCE,
            FOUNDER_EVAL_STORE_SLUG,
            is_founder_production_evaluation_tenant,
            merchandising_families_allowed_for_store,
        )

        store = MagicMock()
        store.zid_store_id = "normal_merchant_abc"
        store.integration_source = "zid_oauth"
        self.assertFalse(
            is_founder_production_evaluation_tenant(
                store_slug=FOUNDER_EVAL_STORE_SLUG,
                store=store,
            )
        )
        self.assertFalse(
            merchandising_families_allowed_for_store(
                store_slug=FOUNDER_EVAL_STORE_SLUG,
                store=store,
                environ={},
            )
        )

        founder = MagicMock()
        founder.zid_store_id = FOUNDER_EVAL_STORE_SLUG
        founder.integration_source = FOUNDER_EVAL_INTEGRATION_SOURCE
        self.assertTrue(
            is_founder_production_evaluation_tenant(
                store_slug="spoofed_other_slug",
                store=founder,
            )
        )


class TestProductionSeparationTests(unittest.TestCase):
    def test_cf_fe_v1_slug_alone_not_production_eligible(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            founder_evaluation_feature_enabled,
            is_fixture_evaluation_slug,
            is_founder_production_evaluation_tenant,
            merchandising_families_allowed_for_store,
        )

        for slug in (
            "cf_fe_v1_quality",
            "cf_fe_v1_focus",
            "cf_fe_v1_actionable",
            "cf_fe_v1_price",
        ):
            self.assertTrue(is_fixture_evaluation_slug(slug), msg=slug)
            self.assertFalse(
                is_founder_production_evaluation_tenant(store_slug=slug), msg=slug
            )
            self.assertFalse(
                founder_evaluation_feature_enabled(
                    "merchandising_mission_slice_v1",
                    store_slug=slug,
                    environ={},
                ),
                msg=slug,
            )
            # Production request path (no test infra flag) → merchandising denied.
            self.assertFalse(
                merchandising_families_allowed_for_store(
                    store_slug=slug, environ={}
                ),
                msg=slug,
            )

    def test_cf_fe_v1_allowed_only_via_test_infrastructure_flag(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            ENV_TEST_ALLOW_MERCHANDISING_SLICE,
            is_founder_production_evaluation_tenant,
            merchandising_families_allowed_for_store,
        )

        slug = "cf_fe_v1_quality"
        self.assertFalse(is_founder_production_evaluation_tenant(store_slug=slug))
        self.assertTrue(
            merchandising_families_allowed_for_store(
                store_slug=slug,
                environ={ENV_TEST_ALLOW_MERCHANDISING_SLICE: "1"},
            )
        )
        # Still not production evaluation tenant.
        self.assertFalse(is_founder_production_evaluation_tenant(store_slug=slug))

    def test_no_env_global_merchandising_enablement(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            merchandising_families_allowed_for_store,
        )

        for env in (
            {"CARTFLOW_MERCHANDISING_MISSION_SLICE_V1_RELEASE": "1"},
            {"CARTFLOW_FOUNDER_EVAL": "1"},
            {"preview": "1"},
        ):
            self.assertFalse(
                merchandising_families_allowed_for_store(
                    store_slug="normal_shop", environ=env
                ),
                msg=str(env),
            )


class NegativeMerchantProofTests(unittest.TestCase):
    def _primary_family(self, slug: str, counts: dict) -> str:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        col = compose_commercial_opportunity_layer_v1(
            {"store_slug": slug, "merchant_reason_counts_week": counts},
            store_slug=slug,
            environ={},
        )
        return str((col.get("primary") or {}).get("family") or "")

    def test_demo_no_merchandising(self) -> None:
        fam = self._primary_family(
            "demo", {"quality": 20, "shipping": 3, "thinking": 2}
        )
        self.assertNotEqual(fam, "product_confidence")
        self.assertNotEqual(fam, "product_opportunity_focus")

    def test_normal_merchant_no_merchandising(self) -> None:
        fam = self._primary_family(
            "normal_merchant_fixture_v1",
            {"quality": 20, "shipping": 3, "thinking": 2},
        )
        self.assertNotEqual(fam, "product_confidence")

    def test_spoofed_cf_fe_v1_production_request_no_merchandising(self) -> None:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "cf_fe_v1_quality",
                "merchant_reason_counts_week": {
                    "quality": 20,
                    "shipping": 3,
                    "thinking": 2,
                },
            },
            store_slug="cf_fe_v1_quality",
            environ={},  # production-shaped: no test infra flag
        )
        primary = col.get("primary") or {}
        self.assertNotEqual(primary.get("family"), "product_confidence")
        reasons = {str(s.get("reason") or "") for s in (col.get("suppressed") or [])}
        self.assertIn("merchandising_eval_tenant_gate", reasons)


class FounderPositiveProofTests(unittest.TestCase):
    def test_founder_gets_product_confidence(self) -> None:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
        )
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1

        col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": FOUNDER_EVAL_STORE_SLUG,
                "merchant_reason_counts_week": {
                    "quality": 20,
                    "shipping": 3,
                    "thinking": 2,
                },
            },
            store_slug=FOUNDER_EVAL_STORE_SLUG,
            environ={},
        )
        self.assertEqual((col.get("primary") or {}).get("family"), "product_confidence")

        cat = compose_mission_catalog_v1(
            col_package=col,
            commitments_by_key={},
            store_slug=FOUNDER_EVAL_STORE_SLUG,
        )
        self.assertEqual(cat["primary"]["family"], "product_confidence")
        self.assertTrue(cat["primary"].get("mission_ready"))

        port = compose_mission_portfolio_v1(
            catalog_package=cat,
            store_slug=FOUNDER_EVAL_STORE_SLUG,
        )
        self.assertTrue(port.get("ok"))

    def test_founder_product_opportunity_focus(self) -> None:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
        )

        col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": FOUNDER_EVAL_STORE_SLUG,
                "merchant_reason_counts_week": {
                    "quality": 12,
                    "warranty": 12,
                    "shipping": 2,
                },
            },
            store_slug=FOUNDER_EVAL_STORE_SLUG,
            environ={},
        )
        self.assertEqual(
            (col.get("primary") or {}).get("family"), "product_opportunity_focus"
        )


class SideEffectBlockTests(unittest.TestCase):
    def test_founder_and_fixtures_blocked(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
            evaluation_tenant_blocks_external_side_effects,
        )

        self.assertTrue(
            evaluation_tenant_blocks_external_side_effects(
                store_slug=FOUNDER_EVAL_STORE_SLUG
            )
        )
        self.assertTrue(
            evaluation_tenant_blocks_external_side_effects(
                store_slug="cf_fe_v1_actionable"
            )
        )
        self.assertFalse(
            evaluation_tenant_blocks_external_side_effects(store_slug="normal_shop")
        )

    def test_twilio_send_blocked(self) -> None:
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
        )
        from services.whatsapp_send import send_whatsapp

        with patch.dict(
            "os.environ",
            {
                "TWILIO_ACCOUNT_SID": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
                "TWILIO_AUTH_TOKEN": "token",
                "TWILIO_WHATSAPP_FROM": "whatsapp:+15551234567",
            },
        ):
            out = send_whatsapp(
                "+966500000000",
                "hello",
                wa_trace_store_slug=FOUNDER_EVAL_STORE_SLUG,
            )
        self.assertFalse(out.get("ok"))
        self.assertEqual(
            out.get("error"), "founder_evaluation_tenant_side_effects_blocked"
        )


class AttachAuthSlugTests(unittest.TestCase):
    def test_authenticated_slug_overrides_summary_spoof(self) -> None:
        from services.commercial_opportunity_layer_v1.attach_v1 import (
            attach_commercial_opportunity_layer_to_summary_v1,
        )
        from services.founder_production_evaluation_tenant_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
        )

        summary = {
            "store_slug": FOUNDER_EVAL_STORE_SLUG,  # spoofed founder claim
            "merchant_reason_counts_week": {
                "quality": 20,
                "shipping": 3,
                "thinking": 2,
            },
        }
        out = attach_commercial_opportunity_layer_to_summary_v1(
            summary,
            environ={"CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1": "1"},
            authenticated_store_slug="normal_merchant_auth",
        )
        self.assertEqual(out.get("store_slug"), "normal_merchant_auth")
        primary = (out.get("commercial_opportunity_layer_v1") or {}).get("primary") or {}
        self.assertNotEqual(primary.get("family"), "product_confidence")


class GateSurfaceHygieneTests(unittest.TestCase):
    def test_no_frontend_or_query_bypass_in_gate(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        gate = (
            root
            / "services"
            / "founder_production_evaluation_tenant_v1"
            / "gate_v1.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "preview=",
            "localStorage",
            "sessionStorage",
            "request.args",
            "CARTFLOW_MERCHANDISING_MISSION_SLICE_V1_RELEASE",
        ):
            self.assertNotIn(forbidden, gate)


if __name__ == "__main__":
    unittest.main()
