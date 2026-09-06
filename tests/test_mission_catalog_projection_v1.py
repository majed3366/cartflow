# -*- coding: utf-8 -*-
"""Mission Catalog Product Projection V1 — UI consumes catalog; no frontend rerank."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MissionCatalogProjectionV1Tests(unittest.TestCase):
    def test_home_consumes_catalog_markers(self) -> None:
        home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        self.assertIn("missionCatalogToColLayer", home)
        self.assertIn("resolveCommercialLayer", home)
        self.assertIn("data-cf2-mission-catalog", home)
        self.assertIn("Presence of primary wins", home)
        self.assertIn("ما أهم مهمة تجارية الآن؟", home)
        self.assertIn("هناك فرص أخرى مؤجلة", home)
        # No frontend rerank of COL score
        self.assertNotIn("score_opportunity", home)
        self.assertNotIn("_FAMILY_WEIGHT", home)
        self.assertNotIn("catalog_score", home)

    def test_workspace_binds_catalog_primary(self) -> None:
        ws = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("catalogPrimaryFromSummary", ws)
        self.assertIn("mission_catalog_v1", ws)
        self.assertIn("refreshColFocusFromSummary", ws)
        self.assertIn("data-cf2-catalog-explain", ws)
        self.assertNotIn("score_opportunity", ws)
        self.assertNotIn("_FAMILY_WEIGHT", ws)

    def test_cachebust_and_no_simulation(self) -> None:
        html = (ROOT / "templates" / "merchant_app_v2.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("mcp2", html)
        home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        ws = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("SIMULATION_TRUTH", home)
        self.assertNotIn("SIMULATION_TRUTH", ws)
        self.assertNotIn("WON", home.split("Mission Catalog")[1][:1200])

    def test_secondary_cap_and_primary_only_focus(self) -> None:
        home = (ROOT / "static" / "merchant_ui_v2_home.js").read_text(encoding="utf-8")
        self.assertIn("slice(0, 2)", home)
        self.assertIn("only primary may become focus", home)

    def test_read_model_map_exists(self) -> None:
        p = (
            ROOT
            / "docs"
            / "product"
            / "mission_catalog_projection_v1"
            / "00_READ_MODEL_MAP.md"
        )
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("mission_catalog_v1.primary", text)
        self.assertIn("never re-ranks", text.lower())


class MissionCatalogProjectionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_mission_catalog_proj_v1.db"
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

    def test_home_workspace_identity_match(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        col = self._col("mcp_id", {"shipping": 12, "price": 5, "thinking": 3})
        pkg = compose_mission_catalog_v1(col_package=col, store_slug="mcp_id")
        self.assertIsNotNone(pkg["primary"])
        self.assertEqual(
            pkg["primary"]["opportunity_id"],
            pkg["workspace"]["active_mission"]["opportunity_id"],
        )
        self.assertEqual(pkg["primary"]["family"], "shipping_friction")
        self.assertNotIn("catalog_score", pkg["primary"])

    def test_no_score_in_merchant_card(self) -> None:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        pkg = compose_mission_catalog_v1(
            col_package=self._col(
                "mcp_sc", {"price": 12, "shipping": 5, "thinking": 3}
            ),
            store_slug="mcp_sc",
        )
        self.assertEqual(pkg["primary"]["family"], "price_hesitation")
        self.assertNotIn("catalog_score", pkg["primary"])
        self.assertIn("why_this_one_now_ar", pkg["explain"])


if __name__ == "__main__":
    unittest.main()
