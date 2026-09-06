# -*- coding: utf-8 -*-
"""Commercial Mission V2 — price_hesitation reuse + genericity gates."""
from __future__ import annotations

import ast
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


class CommercialMissionV2PriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_commercial_mission_v2.db"
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

    def _price_col(self, slug: str = "cm_v2_price"):
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )

        return compose_commercial_opportunity_layer_v1(
            {
                "store_slug": slug,
                "merchant_reason_counts_week": {
                    "price": 12,
                    "shipping": 5,
                    "thinking": 3,
                },
            },
            store_slug=slug,
        )

    def _shipping_col(self, slug: str = "cm_v2_ship"):
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

    def test_price_family_supported_in_col(self) -> None:
        col = self._price_col()
        self.assertTrue(col.get("primary"))
        self.assertEqual(col["primary"]["family"], "price_hesitation")
        self.assertTrue(
            str(col["primary"]["opportunity_id"]).startswith(
                "col:price_hesitation:price:"
            )
        )
        self.assertIn("بلا خصم", col["primary"]["action_ar"])

    def test_full_path_price_cdc(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_price_mission,
            confirm_price_execution,
            recheck_price_mission,
        )
        from services.commercial_decision_commitment_v1 import derive_commitment_state
        from services.commercial_mission_v1.contract_v1 import PROFILE_PRICE_HESITATION

        slug = "cm_v2_full"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        c = a["commitment"]
        self.assertEqual(c["phase"], "ACTION_CHOSEN")
        self.assertEqual(a["mission"]["family"], "price_hesitation")

        m = confirm_price_execution(
            store_slug=slug,
            commitment_id=c["commitment_id"],
            col_package=col,
        )
        self.assertEqual(m["commitment"]["phase"], "UNDER_MEASUREMENT")
        self.assertEqual(
            m["commitment"]["measurement_start_authority"],
            PROFILE_PRICE_HESITATION.execution_authority,
        )
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == c["commitment_id"])
            .first()
        )
        assert row is not None
        self.assertEqual(row.opportunity_family, "price_hesitation")
        self.assertEqual(
            row.recheck_condition_frozen, PROFILE_PRICE_HESITATION.recheck_condition
        )
        self.assertEqual(row.metric_key, PROFILE_PRICE_HESITATION.metric_key)

        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        self.assertEqual(derive_commitment_state(row), "RECHECK_DUE")

        r = recheck_price_mission(
            store_slug=slug,
            commitment_id=c["commitment_id"],
            col_package=col,
        )
        self.assertTrue(r["ok"])
        self.assertTrue(r["remains_open"])
        self.assertEqual(r["col_reread"]["family"], "price_hesitation")
        self.assertFalse(r["signals"]["won"])

    def test_generic_accept_both_families_same_api(self) -> None:
        from services.commercial_mission_v1 import accept_mission

        ship = accept_mission(
            store_slug="cm_v2_both_s", col_package=self._shipping_col("cm_v2_both_s")
        )
        price = accept_mission(
            store_slug="cm_v2_both_p", col_package=self._price_col("cm_v2_both_p")
        )
        self.assertEqual(ship["mission"]["family"], "shipping_friction")
        self.assertEqual(price["mission"]["family"], "price_hesitation")
        self.assertEqual(ship["commitment"]["phase"], price["commitment"]["phase"])

    def test_duplicate_accept(self) -> None:
        from services.commercial_mission_v1 import accept_price_mission
        from extensions import db
        from models import CommercialDecisionCommitment

        slug = "cm_v2_dup"
        col = self._price_col(slug)
        a1 = accept_price_mission(store_slug=slug, col_package=col)
        a2 = accept_price_mission(store_slug=slug, col_package=col)
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

    def test_wrong_store(self) -> None:
        from services.commercial_mission_v1 import (
            MissionError,
            accept_price_mission,
            confirm_price_execution,
        )

        col = self._price_col("cm_v2_own")
        a = accept_price_mission(store_slug="cm_v2_own", col_package=col)
        with self.assertRaises(MissionError):
            confirm_price_execution(
                store_slug="cm_v2_other",
                commitment_id=a["commitment"]["commitment_id"],
                col_package=col,
            )

    def test_stale_price_opportunity(self) -> None:
        from services.commercial_mission_v1 import MissionError, accept_price_mission

        with self.assertRaises(MissionError):
            accept_price_mission(
                store_slug="cm_v2_stale",
                col_package=self._shipping_col("cm_v2_stale"),
            )

    def test_execution_confirm_twice(self) -> None:
        from services.commercial_mission_v1 import (
            accept_price_mission,
            confirm_price_execution,
        )

        slug = "cm_v2_twice"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        m1 = confirm_price_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        m2 = confirm_price_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        self.assertEqual(m1["commitment"]["phase"], "UNDER_MEASUREMENT")
        self.assertEqual(m2["commitment"]["phase"], "UNDER_MEASUREMENT")

    def test_insufficient_evidence(self) -> None:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.commercial_mission_v1 import MissionError, accept_mission

        col = compose_commercial_opportunity_layer_v1(
            {"store_slug": "cm_v2_insuf", "merchant_reason_counts_week": {}},
            store_slug="cm_v2_insuf",
        )
        with self.assertRaises(MissionError):
            accept_mission(store_slug="cm_v2_insuf", col_package=col)

    def test_opportunity_disappears_recheck_weaker(self) -> None:
        from services.commercial_mission_v1 import (
            accept_price_mission,
            confirm_price_execution,
            recheck_price_mission,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from extensions import db
        from models import CommercialDecisionCommitment

        slug = "cm_v2_gone"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        confirm_price_execution(store_slug=slug, commitment_id=cid, col_package=col)
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == cid)
            .first()
        )
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        empty = compose_commercial_opportunity_layer_v1(
            {"store_slug": slug, "merchant_reason_counts_week": {}},
            store_slug=slug,
        )
        r = recheck_price_mission(
            store_slug=slug, commitment_id=cid, col_package=empty
        )
        self.assertTrue(r["signals"]["weaker_evidence"])
        self.assertTrue(r["remains_open"])

    def test_conflicting_stronger_evidence(self) -> None:
        from services.commercial_mission_v1 import (
            accept_price_mission,
            confirm_price_execution,
            recheck_price_mission,
        )
        from extensions import db
        from models import CommercialDecisionCommitment

        slug = "cm_v2_strong"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        confirm_price_execution(store_slug=slug, commitment_id=cid, col_package=col)
        row = (
            db.session.query(CommercialDecisionCommitment)
            .filter(CommercialDecisionCommitment.id == cid)
            .first()
        )
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        stronger = self._price_col(slug)
        r = recheck_price_mission(
            store_slug=slug, commitment_id=cid, col_package=stronger
        )
        self.assertTrue(r["signals"]["stronger_same_family"])
        self.assertFalse(r["signals"]["won"])

    def test_merchant_abandon(self) -> None:
        from services.commercial_mission_v1 import (
            abandon_mission,
            accept_price_mission,
        )

        slug = "cm_v2_abandon"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        out = abandon_mission(
            store_slug=slug, commitment_id=a["commitment"]["commitment_id"]
        )
        self.assertIsNotNone(out["commitment"].get("closed_at"))

    def test_purchase_cannot_close(self) -> None:
        from services.commercial_decision_commitment_v1.contract_v1 import (
            FORBIDDEN_CLOSE_REASONS,
        )
        from services.commercial_decision_commitment_v1 import (
            CommitmentError,
            close_commitment,
        )
        from services.commercial_mission_v1 import (
            accept_price_mission,
            confirm_price_execution,
        )

        slug = "cm_v2_purchase"
        col = self._price_col(slug)
        a = accept_price_mission(store_slug=slug, col_package=col)
        confirm_price_execution(
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

    def test_eval_tenant_price_seed(self) -> None:
        from services.founder_evaluation_reality_v1.constants_v1 import STORE_PRICE
        from services.founder_evaluation_reality_v1.seed_v1 import (
            seed_founder_evaluation_tenants_v1,
        )
        from services.commercial_mission_v1 import accept_price_mission
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.dashboard_kpi_time_v1 import merchant_reason_counts_store_window
        from models import Store
        from extensions import db

        seed_founder_evaluation_tenants_v1(reset=True)
        store = (
            db.session.query(Store).filter(Store.zid_store_id == STORE_PRICE).first()
        )
        self.assertIsNotNone(store)
        counts = merchant_reason_counts_store_window(store, days=7)
        col = compose_commercial_opportunity_layer_v1(
            {"store_slug": STORE_PRICE, "merchant_reason_counts_week": counts},
            store_slug=STORE_PRICE,
        )
        self.assertEqual(col["primary"]["family"], "price_hesitation")
        out = accept_price_mission(store_slug=STORE_PRICE, col_package=col)
        self.assertEqual(out["commitment"]["phase"], "ACTION_CHOSEN")

    def test_no_new_schema_or_authority(self) -> None:
        from services.commercial_decision_commitment_v1.contract_v1 import (
            AUTHORITIES,
            MERCHANT_CONFIRM_FAMILY_ALLOWLIST,
        )
        from services.commercial_mission_v1.contract_v1 import PROFILE_PRICE_HESITATION

        self.assertIn(
            PROFILE_PRICE_HESITATION.execution_authority, AUTHORITIES
        )
        self.assertIn("price_hesitation", MERCHANT_CONFIRM_FAMILY_ALLOWLIST)
        self.assertNotIn("price_merchant_discount", AUTHORITIES)

    def test_ui_supports_price_family_copy_only(self) -> None:
        root = Path(__file__).resolve().parents[1]
        ws = (root / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        html = (root / "templates" / "merchant_app_v2.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("price_hesitation", ws)
        self.assertIn("CF2_MISSION_FAMILIES", ws)
        self.assertIn("cm2", html)
        self.assertNotIn("SIMULATION_TRUTH", ws)
        self.assertNotIn("WON", ws.split("CF2_MISSION_FAMILIES")[1][:800])

    def test_genericity_lifecycle_branches_zero(self) -> None:
        """AST audit: mission_v1.py must not hard-branch lifecycle on family names."""
        path = (
            Path(__file__).resolve().parents[1]
            / "services"
            / "commercial_mission_v1"
            / "mission_v1.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        lifecycle_family_ifs = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue
            # Detect comparisons of string literals shipping_friction / price_hesitation
            # used as lifecycle switches (D). Profile lookups are OK.
            for comp in node.comparators:
                if isinstance(comp, ast.Constant) and comp.value in (
                    "shipping_friction",
                    "price_hesitation",
                ):
                    # Allowed only inside wrappers that pass expected_family=...
                    lifecycle_family_ifs += 1
        # Wrappers accept_shipping / accept_price pass expected_family — those are
        # B/C entry points, not lifecycle D. Cap: accept aliases only (≤3).
        # Fail if accept/confirm/recheck core bodies branch on family strings.
        src = path.read_text(encoding="utf-8")
        core = src.split("# --- V1 shipping aliases")[0]
        for needle in ('== "shipping_friction"', '== "price_hesitation"', "!= \"shipping_friction\"", "!= \"price_hesitation\""):
            self.assertNotIn(
                needle,
                core,
                msg=f"Lifecycle core must not branch on family literal: {needle}",
            )
        # Confirm aliases section may reference price_hesitation only as expected_family
        self.assertIn('expected_family="price_hesitation"', src)


if __name__ == "__main__":
    unittest.main()
