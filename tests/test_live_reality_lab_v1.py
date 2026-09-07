# -*- coding: utf-8 -*-
"""Live Reality Laboratory V1 — isolation, scenarios, side effects."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LiveRealityLabStaticTests(unittest.TestCase):
    def test_identity_constants(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_EMAIL,
            LAB_INTEGRATION_SOURCE,
            LAB_STORE_SLUG,
            SCENARIO_ALLOWLIST,
            SCENARIO_R7,
        )

        self.assertEqual(LAB_STORE_SLUG, "cf_live_reality_lab")
        self.assertEqual(LAB_EMAIL, "reality.lab@cartflow.local")
        self.assertEqual(LAB_INTEGRATION_SOURCE, "live_reality_lab_v1")
        self.assertEqual(len(SCENARIO_ALLOWLIST), 24)
        self.assertIn(SCENARIO_R7, SCENARIO_ALLOWLIST)

    def test_not_confused_with_other_tenants(self) -> None:
        from services.live_reality_lab_v1 import is_live_reality_lab_tenant

        self.assertFalse(
            is_live_reality_lab_tenant(store_slug="cf_founder_evaluation")
        )
        self.assertFalse(is_live_reality_lab_tenant(store_slug="cf_fe_v1_quality"))
        self.assertFalse(is_live_reality_lab_tenant(store_slug="demo"))
        self.assertTrue(
            is_live_reality_lab_tenant(
                store_slug="cf_live_reality_lab",
                integration_source="live_reality_lab_v1",
            )
        )

    def test_router_registered(self) -> None:
        main = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("live_reality_lab_v1_router", main)


class LiveRealityLabIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_live_reality_lab_v1.db"
        )
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "live-reality-lab-v1"

        import sys

        sys.path.insert(0, str(ROOT))
        from extensions import db, init_database, remove_scoped_session
        import models  # noqa: F401
        try:
            remove_scoped_session()
            db.engine.dispose()
        except Exception:
            pass
        if os.path.exists(db_path):
            os.remove(db_path)
        from schema_commercial_decision_commitment_v1 import (
            ensure_commercial_decision_commitment_schema,
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )
        from services.live_reality_lab_v1 import ensure_live_reality_lab_tenant_v1
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )
        from services.founder_production_evaluation_tenant_v1.ensure_v1 import (
            ensure_founder_production_evaluation_tenant_v1,
        )

        init_database()
        db.create_all()
        reset_commercial_decision_commitment_schema_guard_for_tests()
        ensure_commercial_decision_commitment_schema(db)
        seed_founder_evaluation_tenants_v1(reset=True)
        ensure_founder_production_evaluation_tenant_v1()
        ensure_live_reality_lab_tenant_v1()
        cls.db = db

    def test_side_effect_block(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            lab_blocks_external_side_effects,
            lab_side_effect_block_reason,
        )
        from services.founder_production_evaluation_tenant_v1.side_effects_v1 import (
            evaluation_tenant_blocks_external_side_effects,
        )

        self.assertTrue(lab_blocks_external_side_effects(store_slug=LAB_STORE_SLUG))
        self.assertEqual(
            lab_side_effect_block_reason(store_slug=LAB_STORE_SLUG),
            "live_reality_lab_side_effects_blocked",
        )
        self.assertTrue(
            evaluation_tenant_blocks_external_side_effects(store_slug=LAB_STORE_SLUG)
        )

    def test_merchandising_allowed_for_lab(self) -> None:
        from services.founder_production_evaluation_tenant_v1.gate_v1 import (
            merchandising_families_allowed_for_store,
        )
        from services.live_reality_lab_v1 import LAB_STORE_SLUG

        self.assertTrue(
            merchandising_families_allowed_for_store(store_slug=LAB_STORE_SLUG)
        )
        self.assertFalse(
            merchandising_families_allowed_for_store(store_slug="some_normal_merchant")
        )

    def test_foreign_tenant_cannot_apply(self) -> None:
        from services.live_reality_lab_v1 import apply_lab_scenario_v1, SCENARIO_R2

        with self.assertRaises(ValueError) as ctx:
            apply_lab_scenario_v1(
                authenticated_store_slug="cf_founder_evaluation",
                scenario_id=SCENARIO_R2,
            )
        self.assertIn("unauthorized", str(ctx.exception))

    def test_fixture_tenant_cannot_apply(self) -> None:
        from services.live_reality_lab_v1 import apply_lab_scenario_v1, SCENARIO_R2

        with self.assertRaises(ValueError):
            apply_lab_scenario_v1(
                authenticated_store_slug="cf_fe_v1_quality",
                scenario_id=SCENARIO_R2,
            )

    def test_unknown_scenario_denied(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
        )

        with self.assertRaises(ValueError) as ctx:
            apply_lab_scenario_v1(
                authenticated_store_slug=LAB_STORE_SLUG,
                scenario_id="R99_fake",
            )
        self.assertIn("unknown_scenario", str(ctx.exception))

    def test_reset_does_not_touch_other_tenants(self) -> None:
        from models import CartRecoveryReason
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            apply_lab_scenario_v1,
            reset_lab_tenant_data_v1,
            SCENARIO_R2,
        )

        # Seed foreign reason
        self.db.session.add(
            CartRecoveryReason(
                store_slug="cf_founder_evaluation",
                session_id="protect-me",
                reason="quality",
                source="founder_production_evaluation_v1",
            )
        )
        self.db.session.commit()
        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R2
        )
        reset_lab_tenant_data_v1(authenticated_store_slug=LAB_STORE_SLUG)
        foreign = (
            self.db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == "cf_founder_evaluation",
                CartRecoveryReason.session_id == "protect-me",
            )
            .count()
        )
        self.assertEqual(foreign, 1)
        lab_left = (
            self.db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.store_slug == LAB_STORE_SLUG)
            .count()
        )
        self.assertEqual(lab_left, 0)

    def test_R7_coexistence_and_capacity(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            SCENARIO_R7,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        applied = apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R7
        )
        self.assertTrue(applied.get("ok"))
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R7
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))
        obs = verified.get("observed") or {}
        self.assertEqual(obs.get("operational_lane"), "communication_followup")
        self.assertEqual(obs.get("catalog_primary"), "product_opportunity_focus")
        self.assertEqual(obs.get("portfolio_active_count"), 0)
        self.assertFalse(obs.get("ready_consumes_capacity"))

    def test_R2_shipping_catalog(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            SCENARIO_R2,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R2
        )
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R2
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))

    def test_R8_action_chosen(self) -> None:
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            SCENARIO_R8,
            apply_lab_scenario_v1,
            verify_lab_scenario_v1,
        )

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R8
        )
        verified = verify_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R8
        )
        self.assertTrue(verified.get("ok"), msg=str(verified.get("checks")))
        self.assertEqual(
            (verified.get("observed") or {}).get("cdc_state"), "ACTION_CHOSEN"
        )
        self.assertEqual(
            (verified.get("observed") or {}).get("portfolio_active_count"), 1
        )

    def test_apply_idempotent_reset(self) -> None:
        from models import CartRecoveryReason
        from services.live_reality_lab_v1 import (
            LAB_STORE_SLUG,
            SCENARIO_R3,
            apply_lab_scenario_v1,
        )
        from services.live_reality_lab_v1.contract_v1 import LAB_REASON_SOURCE

        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R3
        )
        n1 = (
            self.db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == LAB_STORE_SLUG,
                CartRecoveryReason.source == LAB_REASON_SOURCE,
            )
            .count()
        )
        apply_lab_scenario_v1(
            authenticated_store_slug=LAB_STORE_SLUG, scenario_id=SCENARIO_R3
        )
        n2 = (
            self.db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == LAB_STORE_SLUG,
                CartRecoveryReason.source == LAB_REASON_SOURCE,
            )
            .count()
        )
        self.assertEqual(n1, n2)


if __name__ == "__main__":
    unittest.main()
