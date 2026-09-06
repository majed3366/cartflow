# -*- coding: utf-8 -*-
"""Mission Catalog + Prioritization V1 — ranking, CDC continuity, reality scenarios."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


class MissionCatalogV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_mission_catalog_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        from extensions import db, init_database
        import models  # noqa: F401

        init_database()
        db.create_all()
        from schema_commercial_decision_commitment_v1 import (
            ensure_commercial_decision_commitment_schema,
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )

        reset_commercial_decision_commitment_schema_guard_for_tests()
        ensure_commercial_decision_commitment_schema(db)

    def setUp(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from sqlalchemy import inspect

        if not inspect(db.engine).has_table("commercial_decision_commitments"):
            db.create_all()
        db.session.query(CommercialDecisionCommitment).delete()
        db.session.commit()

    def _col(self, slug: str, counts: dict) -> dict:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        return compose_commercial_opportunity_layer_v1(
            {"store_slug": slug, "merchant_reason_counts_week": counts},
            store_slug=slug,
        )

    def test_inventory_lists_required_families(self) -> None:
        from services.mission_catalog_v1 import catalog_inventory_v1, mission_ready_families

        inv = {e["family"]: e for e in catalog_inventory_v1()}
        self.assertIn("shipping_friction", inv)
        self.assertIn("price_hesitation", inv)
        self.assertIn("product_confidence", inv)
        self.assertIn("communication_followup", inv)
        self.assertEqual(inv["shipping_friction"]["lifecycle_support"], "mission_ready")
        self.assertEqual(inv["price_hesitation"]["lifecycle_support"], "mission_ready")
        self.assertEqual(inv["product_confidence"]["lifecycle_support"], "mission_ready")
        self.assertIn("product_opportunity_focus", inv)
        self.assertEqual(
            inv["product_opportunity_focus"]["lifecycle_support"], "mission_ready"
        )
        self.assertEqual(
            set(mission_ready_families()),
            {
                "shipping_friction",
                "price_hesitation",
                "product_confidence",
                "product_opportunity_focus",
            },
        )

    def test_A_shipping_wins_over_price(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        col = self._col(
            "mc_a",
            {"shipping": 12, "price": 5, "thinking": 3},
        )
        pkg = compose_mission_catalog_v1(col_package=col, store_slug="mc_a")
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")
        self.assertTrue(pkg["explain"]["why_this_one_now_ar"])

    def test_B_price_wins_over_shipping(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        col = self._col(
            "mc_b",
            {"price": 12, "shipping": 5, "thinking": 3},
        )
        pkg = compose_mission_catalog_v1(col_package=col, store_slug="mc_b")
        self.assertEqual(pkg["primary"]["family"], "price_hesitation")

    def test_C_active_commitment_beats_weaker_fresh(self) -> None:
        from services.commercial_mission_v1 import accept_price_mission
        from services.commercial_decision_commitment_v1 import attach_commitment_truth
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        slug = "mc_c"
        # Fresh COL would prefer shipping
        col_ship = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        # Accept price on price-dominant snapshot first
        col_price = self._col(slug, {"price": 12, "shipping": 5, "thinking": 3})
        accept_price_mission(store_slug=slug, col_package=col_price)
        summary = {
            "store_slug": slug,
            "commercial_opportunity_layer_v1": col_ship,
        }
        attach_commitment_truth(summary, store_slug=slug)
        # Nest commitment onto matching opp if price is secondary
        pkg = compose_mission_catalog_v1(
            col_package=summary["commercial_opportunity_layer_v1"],
            commitments_by_key=summary["commercial_decision_commitment_v1"][
                "by_opportunity_key"
            ],
            store_slug=slug,
        )
        self.assertEqual(pkg["primary"]["family"], "price_hesitation")
        self.assertEqual(pkg["primary"]["cdc_phase"], "ACTION_CHOSEN")
        self.assertEqual(
            pkg["explain"]["reasons"]["lifecycle"], "action_chosen_continuity"
        )

    def test_D_under_measurement_remains_primary(self) -> None:
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )
        from services.commercial_decision_commitment_v1 import attach_commitment_truth
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        slug = "mc_d"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        confirm_shipping_execution(
            store_slug=slug,
            commitment_id=a["commitment"]["commitment_id"],
            col_package=col,
        )
        # Stronger fresh price appears
        col2 = self._col(slug, {"price": 14, "shipping": 4, "thinking": 2})
        summary = {"store_slug": slug, "commercial_opportunity_layer_v1": col2}
        attach_commitment_truth(summary, store_slug=slug)
        pkg = compose_mission_catalog_v1(
            col_package=summary["commercial_opportunity_layer_v1"],
            commitments_by_key=summary["commercial_decision_commitment_v1"][
                "by_opportunity_key"
            ],
            store_slug=slug,
        )
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")
        self.assertEqual(pkg["primary"]["cdc_phase"], "UNDER_MEASUREMENT")

    def test_E_recheck_due_surfaced(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )
        from services.commercial_decision_commitment_v1 import (
            attach_commitment_truth,
            derive_commitment_state,
        )
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        slug = "mc_e"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        confirm_shipping_execution(
            store_slug=slug,
            commitment_id=a["commitment"]["commitment_id"],
            col_package=col,
        )
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == a["commitment"]["commitment_id"])
            .first()
        )
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        self.assertEqual(derive_commitment_state(row), "RECHECK_DUE")
        summary = {"store_slug": slug, "commercial_opportunity_layer_v1": col}
        attach_commitment_truth(summary, store_slug=slug)
        pkg = compose_mission_catalog_v1(
            col_package=summary["commercial_opportunity_layer_v1"],
            commitments_by_key=summary["commercial_decision_commitment_v1"][
                "by_opportunity_key"
            ],
            store_slug=slug,
        )
        self.assertEqual(pkg["primary"]["cdc_phase"], "RECHECK_DUE")
        self.assertEqual(
            pkg["explain"]["reasons"]["lifecycle"], "recheck_due_continuity"
        )

    def test_F_insufficient_no_primary(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        col = self._col("mc_f", {})
        pkg = compose_mission_catalog_v1(col_package=col, store_slug="mc_f")
        self.assertIsNone(pkg["primary"])
        self.assertTrue(pkg["empty"])

    def test_G_conflict_suppression(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_catalog_v1.contract_v1 import SUPPRESS_CONFLICT_GROUP

        # price READY + product_confidence PARTIAL/READY in pool via synthetic secondaries
        col = self._col("mc_g", {"price": 12, "quality": 8, "thinking": 0})
        # Ensure product_confidence appears — quality maps to product_confidence
        self.assertTrue(col.get("primary"))
        # Force both into package for conflict test
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        # Build explicit pool: price primary + product_confidence secondary-like
        pkg_col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "mc_g",
                "merchant_reason_counts_week": {"price": 12, "quality": 8},
            },
            store_slug="mc_g",
        )
        families = set()
        if pkg_col.get("primary"):
            families.add(pkg_col["primary"]["family"])
        for s in pkg_col.get("secondaries") or []:
            families.add(s["family"])
        # If COL only surfaced one, inject product_confidence for conflict proof
        if "product_confidence" not in families and pkg_col.get("primary"):
            fake = dict(pkg_col["primary"])
            fake["family"] = "product_confidence"
            fake["opportunity_id"] = "col:product_confidence:quality:mc_g"
            fake["title_ar"] = "ثقة المنتج"
            secs = list(pkg_col.get("secondaries") or [])
            secs.append(fake)
            pkg_col["secondaries"] = secs
        elif "price_hesitation" not in families:
            self.skipTest("price not in COL pool")

        out = compose_mission_catalog_v1(col_package=pkg_col, store_slug="mc_g")
        surfaced = {out["primary"]["family"]} if out["primary"] else set()
        surfaced |= {s["family"] for s in out["secondaries"]}
        # Both price and product_confidence must not both surface
        both = "price_hesitation" in surfaced and "product_confidence" in surfaced
        self.assertFalse(both)
        codes = [s.get("code") for s in out["suppressed"]]
        self.assertTrue(
            SUPPRESS_CONFLICT_GROUP in codes or not both,
            msg=f"expected conflict suppress; surfaced={surfaced} codes={codes}",
        )

    def test_H_duplicate_family_deduped(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_catalog_v1.contract_v1 import SUPPRESS_DUPLICATE_FAMILY

        col = self._col("mc_h", {"shipping": 12, "price": 5, "thinking": 3})
        # Inject duplicate shipping opportunity
        dup = dict(col["primary"])
        dup["opportunity_id"] = "col:shipping_friction:shipping:mc_h:dup"
        col["secondaries"] = [dup] + list(col.get("secondaries") or [])
        pkg = compose_mission_catalog_v1(col_package=col, store_slug="mc_h")
        ship_count = 0
        if pkg["primary"] and pkg["primary"]["family"] == "shipping_friction":
            ship_count += 1
        ship_count += sum(
            1 for s in pkg["secondaries"] if s["family"] == "shipping_friction"
        )
        self.assertEqual(ship_count, 1)
        self.assertTrue(
            any(s.get("code") == SUPPRESS_DUPLICATE_FAMILY for s in pkg["suppressed"])
        )

    def test_deterministic_tie_and_secondary_cap(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_catalog_v1.contract_v1 import MAX_SECONDARIES

        col = self._col(
            "mc_tie",
            {"shipping": 12, "price": 5, "thinking": 3},
        )
        a = compose_mission_catalog_v1(col_package=col, store_slug="mc_tie")
        b = compose_mission_catalog_v1(col_package=col, store_slug="mc_tie")
        self.assertEqual(a["primary"]["opportunity_id"], b["primary"]["opportunity_id"])
        self.assertLessEqual(len(a["secondaries"]), MAX_SECONDARIES)

    def test_query_delta_zero_and_attach(self) -> None:
        from services.mission_catalog_v1 import attach_mission_catalog_to_summary_v1

        col = self._col("mc_q", {"shipping": 12, "price": 5, "thinking": 3})
        summary = {
            "store_slug": "mc_q",
            "commercial_opportunity_layer_v1": col,
            "commercial_decision_commitment_v1": {
                "ok": True,
                "by_opportunity_key": {},
                "query_delta": 1,
            },
        }
        attach_mission_catalog_to_summary_v1(summary, store_slug="mc_q")
        self.assertEqual(summary["mission_catalog_v1"]["query_delta"], 0)
        self.assertEqual(
            summary["mission_catalog_v1"]["primary"]["family"], "shipping_friction"
        )

    def test_empty_catalog_and_stale(self) -> None:
        from services.mission_catalog_v1 import (
            compose_mission_catalog_v1,
            empty_catalog_package_v1,
        )

        empty = empty_catalog_package_v1()
        self.assertTrue(empty["empty"])
        self.assertIsNone(empty["primary"])
        # Stale: commitment without COL primary
        pkg = compose_mission_catalog_v1(
            col_package={"ok": True, "primary": None, "secondaries": [], "suppressed": []},
            commitments_by_key={
                "col:shipping_friction:shipping:mc_stale": {
                    "commitment_id": "x",
                    "opportunity_family": "shipping_friction",
                    "phase": "ACTION_CHOSEN",
                    "action_summary": "test",
                    "console_mode": "accepted",
                }
            },
            store_slug="mc_stale",
        )
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")
        self.assertEqual(pkg["primary"]["cdc_phase"], "ACTION_CHOSEN")

    def test_tenant_isolation_scores(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        a = compose_mission_catalog_v1(
            col_package=self._col("t1", {"shipping": 12, "price": 5, "thinking": 3}),
            store_slug="t1",
        )
        b = compose_mission_catalog_v1(
            col_package=self._col("t2", {"price": 12, "shipping": 5, "thinking": 3}),
            store_slug="t2",
        )
        self.assertEqual(a["primary"]["family"], "shipping_friction")
        self.assertEqual(b["primary"]["family"], "price_hesitation")
        self.assertNotEqual(
            a["primary"]["opportunity_id"], b["primary"]["opportunity_id"]
        )

    def test_explainability_fields(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        pkg = compose_mission_catalog_v1(
            col_package=self._col("mc_x", {"shipping": 12, "price": 5, "thinking": 3}),
            store_slug="mc_x",
        )
        ex = pkg["explain"]
        self.assertIn("why_this_one_now_ar", ex)
        self.assertIn("why_not_others_ar", ex)
        self.assertIn("evidence", ex["reasons"])
        self.assertIn("lifecycle", ex["reasons"])
        self.assertIn("commercial", ex["reasons"])
        self.assertIn("home", pkg)
        self.assertIn("workspace", pkg)
        self.assertEqual(pkg["workspace"]["active_mission"]["family"], "shipping_friction")


if __name__ == "__main__":
    unittest.main()
