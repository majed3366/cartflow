# -*- coding: utf-8 -*-
"""Priority Surface Contract V1 — two-lane labels; no ranking/lifecycle change."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PrioritySurfaceContractStaticTests(unittest.TestCase):
    def test_home_two_lane_labels(self) -> None:
        home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        self.assertIn("Priority Surface Contract V1", home)
        self.assertIn("إجراء تشغيلي مطلوب", home)
        self.assertIn("ما يلزم تشغيلًا الآن", home)
        self.assertIn("المهمة التجارية الحالية", home)
        self.assertIn('data-cf2-priority-lane="operational"', home)
        self.assertIn('data-cf2-priority-lane="commercial"', home)
        self.assertIn("mission_ready", home)
        # No competing “most important now” merchant headings painted
        self.assertNotIn("مركز الجاذبية", home)
        self.assertNotIn("ما الذي أحتاج فعله الآن؟", home)
        self.assertNotIn("ما أهم مهمة تجارية الآن؟", home)
        self.assertNotIn("أين توجد أهم فرصة تجارية الآن؟", home)
        # No frontend commercial ranking engine
        self.assertNotIn("score_opportunity", home)
        self.assertNotIn("_FAMILY_WEIGHT", home)
        self.assertNotIn("catalog_score", home)

    def test_workspace_two_lane_labels(self) -> None:
        ws = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Priority Surface Contract V1", ws)
        self.assertIn("إجراء تشغيلي مطلوب", ws)
        self.assertIn("المهمة التجارية الحالية", ws)
        self.assertIn('data-cf2-priority-lane="commercial"', ws)
        self.assertIn('data-cf2-priority-lane="operational"', ws)
        self.assertIn("only mission-ready may own commercial Console", ws)
        self.assertNotIn("قرار تجاري", ws)
        self.assertNotIn("القرار التجاري", ws)
        self.assertNotIn("score_opportunity", ws)

    def test_cachebust_psc1(self) -> None:
        html = (ROOT / "templates" / "merchant_app_v2.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("psc1", html)

    def test_competing_heading_paint_count(self) -> None:
        """Merchant-visible competing headings must be zero as painted string literals."""
        home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        ws = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        painted = []
        for blob, name in ((home, "home"), (ws, "ws")):
            for needle in (
                '"مركز الجاذبية"',
                '"ما الذي أحتاج فعله الآن؟"',
                '"ما أهم مهمة تجارية الآن؟"',
                '"أين توجد أهم فرصة تجارية الآن؟"',
                '"أهم مهمة تجارية الآن"',
                '"أهم فرصة تجارية الآن"',
                '"أهم قرار اليوم"',
            ):
                if needle in blob:
                    painted.append(f"{name}:{needle}")
        self.assertEqual(painted, [], msg=str(painted))


class PrioritySurfaceContractScenarioTests(unittest.TestCase):
    """Backend owners unchanged; coexistence scenarios for founder-shaped truth."""

    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_priority_surface_contract_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        os.environ["CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"] = "1"
        os.environ["ENV"] = "development"
        os.environ["SECRET_KEY"] = "priority-surface-contract-v1"

        import sys

        sys.path.insert(0, str(ROOT))
        from extensions import db, init_database  # noqa: E402
        import models  # noqa: F401, E402
        from schema_commercial_decision_commitment_v1 import (  # noqa: E402
            ensure_commercial_decision_commitment_schema,
            reset_commercial_decision_commitment_schema_guard_for_tests,
        )
        from services.founder_evaluation_reality_v1.seed_v1 import (  # noqa: E402
            seed_founder_evaluation_tenants_v1,
        )
        from services.founder_production_evaluation_tenant_v1.ensure_v1 import (  # noqa: E402
            ensure_founder_production_evaluation_tenant_v1,
        )

        init_database()
        db.create_all()
        reset_commercial_decision_commitment_schema_guard_for_tests()
        ensure_commercial_decision_commitment_schema(db)
        seed_founder_evaluation_tenants_v1(reset=True)
        ensure_founder_production_evaluation_tenant_v1()
        cls.db = db

    def _compose_stack(
        self,
        *,
        store_slug: str,
        reason_counts: dict[str, int] | None,
        no_phone: int,
    ) -> dict:
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1
        from services.operational_guidance_v1.compose_v1 import (
            compose_operational_guidance_v1,
        )

        summary: dict = {
            "store_slug": store_slug,
            "ok": True,
            "home_teaser_inputs_v1": {
                "health": {"no_phone": no_phone, "abandoned_carts": max(no_phone, 1)}
            },
        }
        if reason_counts:
            summary["merchant_reason_counts_week"] = dict(reason_counts)
            summary["hesitation_evidence_v1"] = {
                "hesitation_total": sum(reason_counts.values()),
                "hesitation_distribution": dict(reason_counts),
            }
        col = compose_commercial_opportunity_layer_v1(
            summary, store_slug=store_slug, environ=os.environ
        )
        cat = compose_mission_catalog_v1(col_package=col, store_slug=store_slug)
        port = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=store_slug
        )
        ogl = compose_operational_guidance_v1(summary, store_slug=store_slug)
        return {"col": col, "cat": cat, "port": port, "ogl": ogl, "summary": summary}

    def test_A_contact_ops_plus_merchandising_commercial(self) -> None:
        from services.founder_production_evaluation_tenant_v1.contract_v1 import (
            FOUNDER_EVAL_STORE_SLUG,
        )

        out = self._compose_stack(
            store_slug=FOUNDER_EVAL_STORE_SLUG,
            reason_counts={"quality": 12, "warranty": 12, "shipping": 2},
            no_phone=39,
        )
        self.assertEqual(out["ogl"].get("family"), "communication_followup")
        self.assertEqual(
            (out["cat"].get("primary") or {}).get("family"),
            "product_opportunity_focus",
        )
        self.assertTrue((out["cat"].get("primary") or {}).get("mission_ready"))
        self.assertEqual(out["port"]["capacity"]["active_count"], 0)
        self.assertEqual(out["port"]["capacity"]["available_slots"], 1)
        # Ops does not consume mission capacity
        self.assertFalse(out["port"].get("ready_consumes_capacity", True))

    def test_B_shipping_ops_attention_price_commercial(self) -> None:
        """No contact block → OGL from hesitation; Catalog prefers mission-ready price."""
        from services.founder_evaluation_reality_v1.constants_v1 import STORE_PRICE

        out = self._compose_stack(
            store_slug=STORE_PRICE,
            reason_counts={"price": 12, "shipping": 5, "thinking": 3},
            no_phone=0,
        )
        self.assertIn(
            out["ogl"].get("family"),
            {"price_hesitation", "shipping_friction", "wait_insufficient"},
        )
        # With price-dominant READY, catalog primary is price
        self.assertEqual(
            (out["cat"].get("primary") or {}).get("family"), "price_hesitation"
        )
        self.assertEqual(out["port"]["capacity"]["active_count"], 0)

    def test_C_open_cdc_plus_independent_ops(self) -> None:
        from services.commercial_decision_commitment_v1 import accept_commitment
        from services.commercial_decision_commitment_v1.contract_v1 import (
            PHASE_ACTION_CHOSEN,
        )
        from services.commercial_opportunity_layer_v1.compose_v1 import (
            compose_commercial_opportunity_layer_v1,
        )
        from services.commercial_decision_commitment_v1 import (
            attach_commitment_truth,
        )
        from services.founder_evaluation_reality_v1.constants_v1 import STORE_PRICE
        from services.mission_catalog_v1 import compose_mission_catalog_v1
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1
        from services.operational_guidance_v1.compose_v1 import (
            compose_operational_guidance_v1,
        )
        from models import CommercialDecisionCommitment

        # Accept commercial mission first (no contact noise in COL rank).
        summary_commerce = {
            "store_slug": STORE_PRICE,
            "home_teaser_inputs_v1": {"health": {"no_phone": 0}},
            "merchant_reason_counts_week": {
                "price": 12,
                "shipping": 5,
                "thinking": 3,
            },
        }
        col_commerce = compose_commercial_opportunity_layer_v1(
            summary_commerce, store_slug=STORE_PRICE, environ=os.environ
        )
        self.assertEqual(
            (col_commerce.get("primary") or {}).get("family"), "price_hesitation"
        )
        oid = str((col_commerce.get("primary") or {}).get("opportunity_id") or "")
        self.db.session.query(CommercialDecisionCommitment).filter_by(
            store_slug=STORE_PRICE
        ).delete()
        self.db.session.commit()
        acc = accept_commitment(
            store_slug=STORE_PRICE, opportunity_key=oid, col_package=col_commerce
        )
        self.assertTrue(acc.get("ok"), msg=str(acc))

        # Independent operational obligation (contact) coexists.
        summary = {
            "store_slug": STORE_PRICE,
            "home_teaser_inputs_v1": {"health": {"no_phone": 12}},
            "merchant_reason_counts_week": {
                "price": 12,
                "shipping": 5,
                "thinking": 3,
            },
            "commercial_opportunity_layer_v1": col_commerce,
        }
        attach_commitment_truth(summary, store_slug=STORE_PRICE)
        by_key = (summary.get("commercial_decision_commitment_v1") or {}).get(
            "by_opportunity_key"
        ) or {}
        cat = compose_mission_catalog_v1(
            col_package=col_commerce,
            commitments_by_key=by_key,
            store_slug=STORE_PRICE,
        )
        port = compose_mission_portfolio_v1(
            catalog_package=cat, store_slug=STORE_PRICE
        )
        ogl = compose_operational_guidance_v1(summary, store_slug=STORE_PRICE)
        self.assertEqual(ogl.get("family"), "communication_followup")
        self.assertEqual((cat.get("primary") or {}).get("family"), "price_hesitation")
        self.assertEqual((cat.get("primary") or {}).get("cdc_phase"), PHASE_ACTION_CHOSEN)
        self.assertEqual(port["capacity"]["active_count"], 1)
        self.assertEqual(port["capacity"]["available_slots"], 0)
        self.db.session.query(CommercialDecisionCommitment).filter_by(
            store_slug=STORE_PRICE
        ).delete()
        self.db.session.commit()

    def test_D_commercial_insufficient_plus_ops(self) -> None:
        from services.founder_evaluation_reality_v1.constants_v1 import (
            STORE_INSUFFICIENT,
        )

        out = self._compose_stack(
            store_slug=STORE_INSUFFICIENT,
            reason_counts=None,
            no_phone=8,
        )
        self.assertEqual(out["ogl"].get("family"), "communication_followup")
        primary = out["cat"].get("primary")
        # Catalog may be empty or col_only — UI will not paint col_only as commercial
        if primary:
            self.assertFalse(
                primary.get("mission_ready"),
                msg="insufficient reasons should not yield mission_ready primary",
            )
        self.assertEqual(out["port"]["capacity"]["active_count"], 0)

    def test_E_commercial_mission_only(self) -> None:
        from services.founder_evaluation_reality_v1.constants_v1 import STORE_QUALITY

        out = self._compose_stack(
            store_slug=STORE_QUALITY,
            reason_counts={"quality": 20, "shipping": 3, "thinking": 2},
            no_phone=0,
        )
        self.assertEqual(
            (out["cat"].get("primary") or {}).get("family"), "product_confidence"
        )
        self.assertNotEqual(out["ogl"].get("family"), "communication_followup")
        self.assertEqual(out["port"]["capacity"]["active_count"], 0)

    def test_F_operational_obligation_only(self) -> None:
        from services.founder_evaluation_reality_v1.constants_v1 import (
            STORE_INSUFFICIENT,
        )

        out = self._compose_stack(
            store_slug=STORE_INSUFFICIENT,
            reason_counts={},
            no_phone=5,
        )
        self.assertEqual(out["ogl"].get("family"), "communication_followup")
        self.assertTrue(
            out["cat"].get("empty")
            or not (out["cat"].get("primary") or {}).get("mission_ready")
        )


if __name__ == "__main__":
    unittest.main()
