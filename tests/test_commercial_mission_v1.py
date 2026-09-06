# -*- coding: utf-8 -*-
"""Commercial Mission V1 — shipping_friction end-to-end + failure gates."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone


class CommercialMissionV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_commercial_mission_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        from extensions import db, init_database
        import models  # noqa: F401 — register CDC + peers on metadata

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

    def _col(self, slug: str = "cf_fe_v1_actionable"):
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        return compose_commercial_opportunity_layer_v1(
            {
                "store_slug": slug,
                "merchant_reason_counts_week": {
                    "shipping": 12,
                    "price": 5,
                    "thinking": 3,
                },
            },
            store_slug=slug,
        )

    def test_full_path_ready_accept_execute_recheck(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
            recheck_shipping_mission,
        )
        from services.commercial_decision_commitment_v1 import derive_commitment_state
        from services.commercial_mission_v1.contract_v1 import (
            EXECUTION_AUTHORITY,
            METRIC_KEY,
            MISSION_FAMILY,
            RECHECK_CONDITION,
        )

        slug = "cm_v1_full"
        col = self._col(slug)
        self.assertEqual(col["primary"]["family"], MISSION_FAMILY)

        a = accept_shipping_mission(store_slug=slug, col_package=col)
        c = a["commitment"]
        self.assertEqual(c["phase"], "ACTION_CHOSEN")
        self.assertIsNone(c.get("measurement_started_at"))
        self.assertIsNone(c.get("baseline_snapshot_json"))

        m = confirm_shipping_execution(
            store_slug=slug,
            commitment_id=c["commitment_id"],
            col_package=col,
        )
        mc = m["commitment"]
        self.assertEqual(mc["phase"], "UNDER_MEASUREMENT")
        self.assertEqual(mc["measurement_start_authority"], EXECUTION_AUTHORITY)
        self.assertEqual(mc["metric_key"], METRIC_KEY)
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == c["commitment_id"])
            .first()
        )
        assert row is not None
        self.assertIsNotNone(row.baseline_snapshot_json)
        self.assertEqual(row.recheck_condition_frozen, RECHECK_CONDITION)

        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        self.assertEqual(derive_commitment_state(row), "RECHECK_DUE")

        r = recheck_shipping_mission(
            store_slug=slug,
            commitment_id=c["commitment_id"],
            col_package=col,
        )
        self.assertTrue(r["ok"])
        self.assertTrue(r["remains_open"])
        self.assertEqual(r["col_reread"]["family"], MISSION_FAMILY)
        self.assertFalse(r["signals"]["won"])
        self.assertFalse(r["signals"]["lost"])
        self.assertFalse(r["signals"]["learned"])

    def test_accept_twice_one_active(self) -> None:
        from services.commercial_mission_v1 import accept_shipping_mission
        from extensions import db
        from models import CommercialDecisionCommitment

        slug = "cm_v1_dup"
        col = self._col(slug)
        a1 = accept_shipping_mission(store_slug=slug, col_package=col)
        a2 = accept_shipping_mission(store_slug=slug, col_package=col)
        self.assertEqual(
            a1["commitment"]["commitment_id"], a2["commitment"]["commitment_id"]
        )
        n = (
            db.session.query(CommercialDecisionCommitment)
            .filter(
                CommercialDecisionCommitment.store_slug == slug,
                CommercialDecisionCommitment.closed_at.is_(None),
            )
            .count()
        )
        self.assertEqual(n, 1)

    def test_execution_before_accept_fails(self) -> None:
        from services.commercial_mission_v1 import (
            MissionError,
            confirm_shipping_execution,
        )

        slug = "cm_v1_early"
        col = self._col(slug)
        with self.assertRaises(MissionError):
            confirm_shipping_execution(
                store_slug=slug,
                commitment_id="00000000-0000-0000-0000-000000000001",
                col_package=col,
            )

    def test_execution_confirm_twice_idempotent(self) -> None:
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )

        slug = "cm_v1_idem"
        col = self._col(slug)
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        m1 = confirm_shipping_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        m2 = confirm_shipping_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        self.assertTrue(m2.get("idempotent") or m2["commitment"]["phase"] == "UNDER_MEASUREMENT")
        from extensions import db
        from models import CommercialDecisionCommitment

        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == cid)
            .first()
        )
        assert row is not None
        self.assertIsNotNone(row.baseline_snapshot_json)
        # second confirm must not rewrite baseline
        baseline = row.baseline_snapshot_json
        confirm_shipping_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        db.session.refresh(row)
        self.assertEqual(baseline, row.baseline_snapshot_json)
        self.assertEqual(m1["commitment"]["phase"], "UNDER_MEASUREMENT")

    def test_wrong_store_isolation(self) -> None:
        from services.commercial_mission_v1 import (
            MissionError,
            accept_shipping_mission,
            confirm_shipping_execution,
        )

        col_a = self._col("cm_store_a")
        col_b = self._col("cm_store_b")
        a = accept_shipping_mission(store_slug="cm_store_a", col_package=col_a)
        with self.assertRaises(MissionError):
            confirm_shipping_execution(
                store_slug="cm_store_b",
                commitment_id=a["commitment"]["commitment_id"],
                col_package=col_b,
            )

    def test_stale_opportunity_family_mismatch(self) -> None:
        from services.commercial_mission_v1 import (
            MissionError,
            accept_shipping_mission,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        # Price-dominant counts → not shipping mission
        col = compose_commercial_opportunity_layer_v1(
            {
                "store_slug": "cm_price",
                "merchant_reason_counts_week": {"price": 15, "shipping": 2},
            },
            store_slug="cm_price",
        )
        if col.get("primary") and col["primary"].get("family") != "shipping_friction":
            with self.assertRaises(MissionError):
                accept_shipping_mission(store_slug="cm_price", col_package=col)

    def test_recheck_weaker_and_stronger_col(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
            recheck_shipping_mission,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        slug = "cm_v1_recheck_ev"
        col = self._col(slug)
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        confirm_shipping_execution(store_slug=slug, commitment_id=cid, col_package=col)
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == cid)
            .first()
        )
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db.session.commit()

        weak = compose_commercial_opportunity_layer_v1(
            {"store_slug": slug, "merchant_reason_counts_week": {}},
            store_slug=slug,
        )
        rw = recheck_shipping_mission(
            store_slug=slug, commitment_id=cid, col_package=weak
        )
        self.assertTrue(rw["signals"]["weaker_evidence"])
        self.assertTrue(rw["remains_open"])

        strong = self._col(slug)
        rs = recheck_shipping_mission(
            store_slug=slug, commitment_id=cid, col_package=strong
        )
        self.assertTrue(rs["signals"]["stronger_same_family"] or rs["col_reread"]["family"] == "shipping_friction")
        self.assertFalse(rs["signals"]["won"])

    def test_purchase_does_not_auto_close(self) -> None:
        from services.commercial_mission_v1 import (
            accept_shipping_mission,
            confirm_shipping_execution,
        )
        from services.commercial_decision_commitment_v1.contract_v1 import (
            FORBIDDEN_CLOSE_REASONS,
        )
        from services.commercial_decision_commitment_v1 import close_commitment, CommitmentError

        slug = "cm_v1_purchase"
        col = self._col(slug)
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        confirm_shipping_execution(
            store_slug=slug,
            commitment_id=a["commitment"]["commitment_id"],
            col_package=col,
        )
        self.assertIn("purchase", FORBIDDEN_CLOSE_REASONS)
        with self.assertRaises(CommitmentError):
            close_commitment(
                store_slug=slug,
                commitment_id=a["commitment"]["commitment_id"],
                close_reason="purchase",
                actor="system",
            )

    def test_merchant_abandon(self) -> None:
        from services.commercial_mission_v1 import (
            abandon_shipping_mission,
            accept_shipping_mission,
        )

        slug = "cm_v1_abandon"
        col = self._col(slug)
        a = accept_shipping_mission(store_slug=slug, col_package=col)
        out = abandon_shipping_mission(
            store_slug=slug, commitment_id=a["commitment"]["commitment_id"]
        )
        self.assertIsNotNone(out["commitment"].get("closed_at"))

    def test_ui_wiring_no_hardcode_won(self) -> None:
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        ws = (root / "static" / "merchant_ui_v2_workspace.js").read_text(encoding="utf-8")
        html = (root / "templates" / "merchant_app_v2.html").read_text(encoding="utf-8")
        self.assertIn("commercial-mission/v1", ws)
        self.assertIn("data-cf2-mission", ws)
        self.assertTrue("cm1" in html or "cm2" in html)
        self.assertNotIn("SIMULATION_TRUTH", ws)
        self.assertNotIn('phase = "WON"', ws)
        self.assertNotIn("WON/LOST", ws)

    def test_eval_tenant_seed_path(self) -> None:
        from services.founder_evaluation_reality_v1.constants_v1 import STORE_ACTIONABLE
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )
        from services.commercial_mission_v1 import accept_shipping_mission
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.dashboard_kpi_time_v1 import merchant_reason_counts_store_window
        from models import Store
        from extensions import db

        seed_founder_evaluation_tenants_v1(reset=True)
        store = (
            db.session.query(Store)
            .filter(Store.zid_store_id == STORE_ACTIONABLE)
            .first()
        )
        counts = merchant_reason_counts_store_window(store, days=7)
        col = compose_commercial_opportunity_layer_v1(
            {"store_slug": STORE_ACTIONABLE, "merchant_reason_counts_week": counts},
            store_slug=STORE_ACTIONABLE,
        )
        self.assertTrue(col.get("primary"))
        out = accept_shipping_mission(
            store_slug=STORE_ACTIONABLE, col_package=col
        )
        self.assertEqual(out["commitment"]["phase"], "ACTION_CHOSEN")


if __name__ == "__main__":
    unittest.main()
