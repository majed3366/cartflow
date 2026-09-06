# -*- coding: utf-8 -*-
"""Merchandising Mission Slice V1 — product_confidence + product_opportunity_focus."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_EXPOSURE = (
    "homepage",
    "زيادة الظهور",
    "زد ظهور",
    "ضع المنتج في الصفحة الرئيسية",
    "advertise",
    "ROAS",
    "ضعف موضع العرض يستدعي",
)


class MerchandisingMissionSliceV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        db_path = os.path.join(
            tempfile.gettempdir(), "cartflow_pytest_merch_mission_slice_v1.db"
        )
        if os.path.exists(db_path):
            os.remove(db_path)
        os.environ["DATABASE_URL"] = "sqlite:///" + db_path.replace("\\", "/")
        os.environ["CARTFLOW_COMMERCIAL_OPPORTUNITY_LAYER_V1"] = "1"
        # Unit tests exercise merchandising truth paths via test infrastructure
        # flag — NOT production evaluation eligibility (cf_fe_v1_* / RELEASE).
        os.environ["CARTFLOW_TEST_ALLOW_MERCHANDISING_SLICE"] = "1"
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

    def _catalog(self, slug: str, counts: dict, *, by_key=None) -> dict:
        from services.mission_catalog_v1 import compose_mission_catalog_v1

        return compose_mission_catalog_v1(
            col_package=self._col(slug, counts),
            commitments_by_key=by_key,
            store_slug=slug,
        )

    def _cdc_map(self, slug: str) -> dict:
        from services.commercial_decision_commitment_v1 import attach_commitment_truth

        summary = {"store_slug": slug, "commercial_opportunity_layer_v1": {}}
        attach_commitment_truth(summary, store_slug=slug)
        return dict(
            (summary.get("commercial_decision_commitment_v1") or {}).get(
                "by_opportunity_key"
            )
            or {}
        )

    def test_profiles_mission_ready(self) -> None:
        from services.commercial_mission_v1 import (
            MISSION_PROFILES,
            get_mission_profile,
        )
        from services.mission_catalog_v1 import mission_ready_families

        self.assertIn("product_confidence", MISSION_PROFILES)
        self.assertIn("product_opportunity_focus", MISSION_PROFILES)
        self.assertEqual(
            get_mission_profile("product_confidence").metric_key, "hesitation_share"
        )
        self.assertEqual(
            get_mission_profile("product_opportunity_focus").measurement_window_days, 7
        )
        ready = mission_ready_families()
        self.assertIn("product_confidence", ready)
        self.assertIn("product_opportunity_focus", ready)

    def test_A_product_confidence_primary(self) -> None:
        cat = self._catalog("mm_a", {"quality": 20, "shipping": 3, "thinking": 2})
        self.assertEqual(cat["primary"]["family"], "product_confidence")
        self.assertTrue(cat["primary"]["mission_ready"])

    def test_B_shipping_outranks_weaker_confidence(self) -> None:
        cat = self._catalog("mm_b", {"shipping": 12, "quality": 5, "thinking": 3})
        self.assertEqual(cat["primary"]["family"], "shipping_friction")

    def test_C_confidence_outranks_weaker_shipping(self) -> None:
        cat = self._catalog("mm_c", {"quality": 20, "shipping": 3, "thinking": 2})
        self.assertEqual(cat["primary"]["family"], "product_confidence")
        fams = {s["family"] for s in cat.get("secondaries") or []}
        # shipping may appear secondary or suppressed by score
        self.assertNotEqual(cat["primary"]["family"], "shipping_friction")

    def test_D_price_active_defers_product_confidence(self) -> None:
        from services.commercial_mission_v1 import accept_price_mission
        from services.mission_portfolio_v1 import compose_mission_portfolio_v1
        from services.mission_catalog_v1.contract_v1 import SUPPRESS_CONFLICT_GROUP

        slug = "mm_d"
        col = self._col(slug, {"price": 12, "quality": 8, "shipping": 3})
        self.assertEqual(col["primary"]["family"], "price_hesitation")
        accept_price_mission(store_slug=slug, col_package=col)
        cat = self._catalog(
            slug, {"price": 12, "quality": 8, "shipping": 3}, by_key=self._cdc_map(slug)
        )
        port = compose_mission_portfolio_v1(catalog_package=cat, store_slug=slug)
        self.assertEqual(port["active_mission"]["family"], "price_hesitation")
        # Catalog conflict group suppresses confidence as secondary; portfolio mirrors
        conf_deferred = [
            d for d in port["deferred"] if d["family"] == "product_confidence"
        ]
        conf_suppressed = [
            s for s in port["suppressed"] if s.get("family") == "product_confidence"
        ]
        self.assertTrue(
            conf_deferred or conf_suppressed,
            msg=f"deferred={port['deferred']} suppressed={port['suppressed']}",
        )
        if conf_suppressed:
            self.assertEqual(conf_suppressed[0].get("catalog_code"), SUPPRESS_CONFLICT_GROUP)
        self.assertNotEqual(
            (port.get("next_mission") or {}).get("family"), "product_confidence"
        )

    def test_E_confidence_under_measurement_continuity(self) -> None:
        from services.commercial_mission_v1 import (
            accept_product_confidence_mission,
            confirm_product_confidence_execution,
        )

        slug = "mm_e"
        col = self._col(slug, {"quality": 20, "shipping": 3, "thinking": 2})
        a = accept_product_confidence_mission(store_slug=slug, col_package=col)
        confirm_product_confidence_execution(
            store_slug=slug,
            commitment_id=a["commitment"]["commitment_id"],
            col_package=col,
        )
        # Fresh COL would prefer shipping if counts flipped — continuity must hold
        cat = self._catalog(
            slug,
            {"shipping": 12, "quality": 5, "thinking": 3},
            by_key=self._cdc_map(slug),
        )
        self.assertEqual(cat["primary"]["family"], "product_confidence")
        self.assertEqual(cat["primary"]["cdc_phase"], "UNDER_MEASUREMENT")

    def test_F_confidence_recheck_continuity(self) -> None:
        from extensions import db
        from models import CommercialDecisionCommitment
        from services.commercial_mission_v1 import (
            accept_product_confidence_mission,
            confirm_product_confidence_execution,
        )

        slug = "mm_f"
        col = self._col(slug, {"quality": 20, "shipping": 3, "thinking": 2})
        a = accept_product_confidence_mission(store_slug=slug, col_package=col)
        cid = a["commitment"]["commitment_id"]
        confirm_product_confidence_execution(
            store_slug=slug, commitment_id=cid, col_package=col
        )
        row = db.session.query(CommercialDecisionCommitment).filter_by(id=cid).first()
        assert row is not None
        row.measurement_due_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db.session.commit()
        cat = self._catalog(
            slug,
            {"shipping": 12, "price": 5, "thinking": 3},
            by_key=self._cdc_map(slug),
        )
        self.assertEqual(cat["primary"]["cdc_phase"], "RECHECK_DUE")
        self.assertEqual(cat["primary"]["family"], "product_confidence")

    def test_G_product_focus_actionable(self) -> None:
        from services.commercial_mission_v1 import accept_product_focus_mission

        # Dual quality+warranty → focus primary (not single-reason confidence)
        col = self._col("mm_g", {"quality": 8, "warranty": 8, "shipping": 3})
        self.assertEqual(col["primary"]["family"], "product_opportunity_focus")
        blob = str(col["primary"])
        for bad in FORBIDDEN_EXPOSURE:
            self.assertNotIn(bad, blob)
        out = accept_product_focus_mission(store_slug="mm_g", col_package=col)
        self.assertTrue(out.get("ok") or out.get("commitment"))
        self.assertEqual(out["mission"]["family"], "product_opportunity_focus")

        # Shipping primary + trust pool secondary
        col2 = self._col("mm_g2", {"shipping": 12, "quality": 6, "warranty": 6})
        self.assertEqual(col2["primary"]["family"], "shipping_friction")
        secs = [s for s in (col2.get("secondaries") or []) if s.get("family") == "product_opportunity_focus"]
        self.assertTrue(secs)
    def test_H_exposure_claims_refused_in_copy(self) -> None:
        col = self._col("mm_h", {"quality": 20, "shipping": 3, "thinking": 2})
        blob = str(col)
        for bad in (
            "homepage",
            "زيادة الظهور",
            "ضع المنتج في الصفحة الرئيسية",
            "advertise this",
            "ROAS",
        ):
            self.assertNotIn(bad, blob)
        # Explicit dont language forbids placement/ads
        why = (col.get("primary") or {}).get("decision_contract_ar") or {}
        dont = str(why.get("dont_ar") or "")
        self.assertTrue(dont)
        self.assertIn("موضع", dont)

    def test_I_insufficient_no_merch_mission(self) -> None:
        cat = self._catalog("mm_i", {})
        self.assertTrue(cat["empty"])
        self.assertIsNone(cat["primary"])

    def test_J_tenant_isolation(self) -> None:
        from services.commercial_mission_v1 import accept_product_confidence_mission

        col_a = self._col("mm_j_a", {"quality": 20, "shipping": 3, "thinking": 2})
        accept_product_confidence_mission(store_slug="mm_j_a", col_package=col_a)
        cat_a = self._catalog(
            "mm_j_a",
            {"quality": 20, "shipping": 3, "thinking": 2},
            by_key=self._cdc_map("mm_j_a"),
        )
        cat_b = self._catalog("mm_j_b", {"shipping": 12, "price": 5, "thinking": 3})
        self.assertEqual(cat_a["primary"]["family"], "product_confidence")
        self.assertEqual(cat_b["primary"]["family"], "shipping_friction")
        self.assertIsNone(cat_b["primary"].get("cdc_phase"))

    def test_workspace_mission_families_wired(self) -> None:
        ws = (ROOT / "static" / "merchant_ui_v2_workspace.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("product_confidence:", ws)
        self.assertIn("product_opportunity_focus:", ws)

    def test_truth_map_exists(self) -> None:
        p = (
            ROOT
            / "docs"
            / "product"
            / "merchandising_mission_slice_v1"
            / "00_PRODUCT_TRUTH_MAP.md"
        )
        self.assertTrue(p.is_file())
        text = p.read_text(encoding="utf-8")
        self.assertIn("UNSAFE", text)
        self.assertIn("exposure", text.lower())


if __name__ == "__main__":
    unittest.main()
