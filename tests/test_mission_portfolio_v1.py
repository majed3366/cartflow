# -*- coding: utf-8 -*-
"""Mission Portfolio V1 — capacity, conflict, continuity, reality A–J + failures."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


class MissionPortfolioV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_mission_portfolio_v1.db"
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

    def _catalog(self, slug: str, counts: dict, *, commitments_by_key=None) -> dict:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        col = self._col(slug, counts)
        return compose_mission_catalog_v1(
            col_package=col,
            commitments_by_key=commitments_by_key,
            store_slug=slug,
        )

    def _portfolio(self, catalog: dict, slug: str = "") -> dict:
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1

        return compose_mission_portfolio_v1(
            catalog_package=catalog, store_slug=slug or catalog.get("store_slug") or ""
        )

    def _cdc_map(self, slug: str) -> dict:
        from services.commercial_decision_commitment_v1 import attach_commitment_truth

        summary = {"store_slug": slug, "commercial_opportunity_layer_v1": {}}
        attach_commitment_truth(summary, store_slug=slug)
        cdc = summary.get("commercial_decision_commitment_v1") or {}
        return dict(cdc.get("by_opportunity_key") or {})

    # --- Reality A–J ---

    def test_A_shipping_ready_price_ready_one_next(self) -> None:
        cat = self._catalog("mp_a", {"shipping": 12, "price": 5, "thinking": 3})
        port = self._portfolio(cat, "mp_a")
        self.assertIsNone(port["active_mission"])
        self.assertEqual(port["next_mission"]["family"], "shipping_friction")
        self.assertEqual(port["capacity"]["available_slots"], 1)
        self.assertEqual(port["capacity"]["active_count"], 0)
        # price may be safe secondary (no slot)
        fams = {s["family"] for s in port["safe_secondaries"]}
        self.assertTrue(
            "price_hesitation" in fams or any(
                d["family"] == "price_hesitation" for d in port["deferred"]
            )
            or any(s.get("family") == "price_hesitation" for s in cat.get("secondaries") or [])
        )
        if port["safe_secondaries"]:
            self.assertLessEqual(len(port["safe_secondaries"]), 2)

    def test_B_shipping_action_chosen_price_deferred(self) -> None:
        from services.commercial_mission_v1 import accept_shipping_mission

        slug = "mp_b"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        accept_shipping_mission(store_slug=slug, col_package=col)
        by_key = self._cdc_map(slug)
        cat = self._catalog(slug, {"shipping": 12, "price": 5, "thinking": 3}, commitments_by_key=by_key)
        port = self._portfolio(cat, slug)
        self.assertEqual(port["active_mission"]["family"], "shipping_friction")
        self.assertEqual(port["active_mission"]["cdc_phase"], "ACTION_CHOSEN")
        self.assertEqual(port["next_mission"]["opportunity_id"], port["active_mission"]["opportunity_id"])
        self.assertEqual(port["capacity"]["available_slots"], 0)
        deferred_fams = {d["family"] for d in port["deferred"]}
        self.assertIn("price_hesitation", deferred_fams)
        from services.mission_portfolio_v1 import portfolio_allows_accept_v1

        gate = portfolio_allows_accept_v1(port)
        self.assertFalse(gate["allowed"])

    def test_C_under_measurement_price_contamination(self) -> None:
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )
        from services.mission_portfolio_v1.contract_v1 import (
            CONFLICT_MEASUREMENT_CONTAMINATION,
            REASON_MEASUREMENT_CONTAMINATION,
        )

        slug = "mp_c"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        confirm_shipping_execution(
            store_slug=slug,
            commitment_id=a["commitment"]["commitment_id"],
            col_package=col,
        )
        by_key = self._cdc_map(slug)
        cat = self._catalog(slug, {"shipping": 12, "price": 5, "thinking": 3}, commitments_by_key=by_key)
        port = self._portfolio(cat, slug)
        self.assertEqual(port["active_mission"]["cdc_phase"], "UNDER_MEASUREMENT")
        price_def = [d for d in port["deferred"] if d["family"] == "price_hesitation"]
        self.assertTrue(price_def)
        self.assertEqual(price_def[0]["conflict_type"], CONFLICT_MEASUREMENT_CONTAMINATION)
        self.assertEqual(price_def[0]["reason_code"], REASON_MEASUREMENT_CONTAMINATION)

    def test_D_recheck_continuity_over_fresh_price(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )
        from services.mission_portfolio_v1.contract_v1 import REASON_LOWER_PRIORITY_RECHECK

        slug = "mp_d"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        confirm_shipping_execution(store_slug=slug, commitment_id=cid, col_package=col)
        row = db.session.query(CommercialDecisionCommitment).filter_by(id=cid).first()
        assert row is not None
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.commit()
        # Fresh COL would prefer price
        by_key = self._cdc_map(slug)
        cat = self._catalog(
            slug, {"price": 12, "shipping": 5, "thinking": 3}, commitments_by_key=by_key
        )
        port = self._portfolio(cat, slug)
        self.assertEqual(port["active_mission"]["family"], "shipping_friction")
        self.assertEqual(port["active_mission"]["cdc_phase"], "RECHECK_DUE")
        self.assertEqual(port["next_mission"]["family"], "shipping_friction")
        price_def = [d for d in port["deferred"] if d["family"] == "price_hesitation"]
        self.assertTrue(price_def)
        self.assertEqual(price_def[0]["reason_code"], REASON_LOWER_PRIORITY_RECHECK)

    def test_E_price_action_chosen_shipping_deferred(self) -> None:
        from services.commercial_mission_v1 import accept_price_mission

        slug = "mp_e"
        col = self._col(slug, {"price": 12, "shipping": 5, "thinking": 3})
        accept_price_mission(store_slug=slug, col_package=col)
        by_key = self._cdc_map(slug)
        cat = self._catalog(slug, {"price": 12, "shipping": 5, "thinking": 3}, commitments_by_key=by_key)
        port = self._portfolio(cat, slug)
        self.assertEqual(port["active_mission"]["family"], "price_hesitation")
        self.assertEqual(port["active_mission"]["cdc_phase"], "ACTION_CHOSEN")
        ship_def = [d for d in port["deferred"] if d["family"] == "shipping_friction"]
        self.assertTrue(ship_def)

    def test_F_active_closed_capacity_freed(self) -> None:
        from services.commercial_mission_v1 import (
            abandon_mission,
            accept_shipping_mission,
        )

        slug = "mp_f"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        abandon_mission(store_slug=slug, commitment_id=a["commitment"]["commitment_id"])
        by_key = self._cdc_map(slug)
        # open map should be empty after abandon
        self.assertEqual(by_key, {})
        cat = self._catalog(slug, {"shipping": 12, "price": 5, "thinking": 3}, commitments_by_key=by_key)
        port = self._portfolio(cat, slug)
        self.assertIsNone(port["active_mission"])
        self.assertEqual(port["capacity"]["available_slots"], 1)
        self.assertEqual(port["next_mission"]["family"], "shipping_friction")

    def test_G_duplicate_suppressed_in_portfolio(self) -> None:
        from services.mission_catalog_v1.contract_v1 import SUPPRESS_DUPLICATE_FAMILY

        cat = self._catalog("mp_g", {"shipping": 12, "price": 5, "thinking": 3})
        # Inject duplicate suppress into catalog package
        cat = dict(cat)
        cat["suppressed"] = list(cat.get("suppressed") or []) + [
            {
                "family": "shipping_friction",
                "opportunity_id": "dup",
                "code": SUPPRESS_DUPLICATE_FAMILY,
                "reason": "duplicate",
            }
        ]
        cat["suppressed_count"] = len(cat["suppressed"])
        port = self._portfolio(cat, "mp_g")
        codes = {s["catalog_code"] for s in port["suppressed"]}
        self.assertIn(SUPPRESS_DUPLICATE_FAMILY, codes)

    def test_H_safe_secondary_no_slot(self) -> None:
        cat = self._catalog("mp_h", {"shipping": 12, "price": 5, "thinking": 3})
        port = self._portfolio(cat, "mp_h")
        self.assertIsNone(port["active_mission"])
        self.assertTrue(port["next_mission"])
        # Secondaries visible without owning slot
        for s in port["safe_secondaries"]:
            self.assertNotEqual(s.get("opportunity_id"), port["next_mission"]["opportunity_id"])

    def test_I_insufficient_no_active_no_next(self) -> None:
        cat = self._catalog("mp_i", {})
        port = self._portfolio(cat, "mp_i")
        self.assertTrue(port["empty"])
        self.assertIsNone(port["active_mission"])
        self.assertIsNone(port["next_mission"])
        self.assertEqual(port["capacity"]["available_slots"], 1)

    def test_J_tenant_isolation(self) -> None:
        from services.commercial_mission_v1 import accept_shipping_mission

        col_a = self._col("mp_j_a", {"shipping": 12, "price": 5, "thinking": 3})
        accept_shipping_mission(store_slug="mp_j_a", col_package=col_a)
        cat_a = self._catalog(
            "mp_j_a",
            {"shipping": 12, "price": 5, "thinking": 3},
            commitments_by_key=self._cdc_map("mp_j_a"),
        )
        cat_b = self._catalog("mp_j_b", {"price": 12, "shipping": 5, "thinking": 3})
        port_a = self._portfolio(cat_a, "mp_j_a")
        port_b = self._portfolio(cat_b, "mp_j_b")
        self.assertEqual(port_a["store_slug"], "mp_j_a")
        self.assertEqual(port_b["store_slug"], "mp_j_b")
        self.assertEqual(port_a["active_mission"]["family"], "shipping_friction")
        self.assertIsNone(port_b["active_mission"])
        self.assertEqual(port_b["next_mission"]["family"], "price_hesitation")

    # --- Failure / fail-safe ---

    def test_double_accept_capacity_gate(self) -> None:
        from services.commercial_mission_v1 import accept_shipping_mission
        from services.mission_portfolio_v1 import portfolio_allows_accept_v1

        slug = "mp_fail_cap"
        col = self._col(slug, {"shipping": 12, "price": 5, "thinking": 3})
        accept_shipping_mission(store_slug=slug, col_package=col)
        cat = self._catalog(
            slug, {"shipping": 12, "price": 5}, commitments_by_key=self._cdc_map(slug)
        )
        port = self._portfolio(cat, slug)
        self.assertFalse(portfolio_allows_accept_v1(port)["allowed"])

    def test_unknown_family_fail_safe(self) -> None:
        from services.mission_portfolio_v1 import evaluate_conflict_v1
        from services.mission_portfolio_v1.contract_v1 import REASON_UNKNOWN_FAMILY

        active = {
            "opportunity_id": "a",
            "family": "shipping_friction",
            "cdc_phase": "ACTION_CHOSEN",
        }
        cand = {"opportunity_id": "b", "family": ""}
        ev = evaluate_conflict_v1(active=active, candidate=cand)
        self.assertFalse(ev["may_execute"])
        self.assertEqual(ev["reason_code"], REASON_UNKNOWN_FAMILY)

    def test_measurement_contamination_rule_present(self) -> None:
        from services.mission_portfolio_v1.contract_v1 import (
            MEASUREMENT_CONTAMINATION_PAIRS,
        )

        self.assertIn(("shipping_friction", "price_hesitation"), MEASUREMENT_CONTAMINATION_PAIRS)
        self.assertIn(("price_hesitation", "shipping_friction"), MEASUREMENT_CONTAMINATION_PAIRS)

    def test_zero_missions_empty(self) -> None:
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1

        port = compose_mission_portfolio_v1(
            catalog_package={"ok": True, "empty": True, "primary": None, "secondaries": [], "suppressed": []},
            store_slug="mp_zero",
        )
        self.assertTrue(port["empty"])
        self.assertIsNone(port["next_mission"])

    def test_attach_query_delta_zero(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_portfolio_v1 import attach_mission_portfolio_to_summary_v1

        col = self._col("mp_q", {"shipping": 12, "price": 5, "thinking": 3})
        cat = compose_mission_catalog_v1(col_package=col, store_slug="mp_q")
        summary = {"store_slug": "mp_q", "mission_catalog_v1": cat}
        attach_mission_portfolio_to_summary_v1(summary, store_slug="mp_q")
        self.assertEqual(summary["mission_portfolio_v1"]["query_delta"], 0)
        self.assertEqual(summary["mission_portfolio_v1"]["next_mission"]["family"], "shipping_friction")

    def test_no_frontend_portfolio_logic(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        home = (root / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        ws = (root / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
        self.assertNotIn("mission_portfolio_v1", home)
        self.assertNotIn("mission_portfolio_v1", ws)
        self.assertNotIn("compose_mission_portfolio", home)

    def test_contract_constants(self) -> None:
        from services.mission_portfolio_v1 import (
            CONFLICT_TYPES,
            MAX_ACTIVE_MISSIONS,
            MAX_SECONDARY_READY,
            SLOT_PHASES,
        )

        self.assertEqual(MAX_ACTIVE_MISSIONS, 1)
        self.assertEqual(MAX_SECONDARY_READY, 2)
        self.assertEqual(SLOT_PHASES, frozenset({"ACTION_CHOSEN", "UNDER_MEASUREMENT", "RECHECK_DUE"}))
        self.assertIn("MEASUREMENT_CONTAMINATION", CONFLICT_TYPES)
        self.assertIn("CAPACITY_ONLY", CONFLICT_TYPES)


if __name__ == "__main__":
    unittest.main()
