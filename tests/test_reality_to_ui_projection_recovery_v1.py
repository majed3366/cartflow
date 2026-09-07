# -*- coding: utf-8 -*-
"""Reality-to-UI Projection Recovery V1 — production truth path gates."""
from __future__ import annotations

import inspect
import os
import unittest
from unittest import mock

from services.commercial_opportunity_layer_v1.compose_v1 import (
    compose_commercial_opportunity_layer_v1,
)
from services.commercial_opportunity_layer_v1.contract_v1 import (
    TRUTH_PRODUCTION_READY,
)
from services.commercial_opportunity_layer_v1.flag_v1 import (
    ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1,
)
from services.dashboard_hot_slice_v1 import (
    HOT_SLICE_MAX_ROWS,
    NORMAL_CARTS_PAGE_LIMIT,
    merge_hot_slice_active_rows,
)
from services.home_executive_summary_v1.diagnosis_language_v1 import (
    apply_home_diagnosis_language_v1,
)
from services.decision_composition_engine_v1.merchant_publication_v1 import (
    compose_merchant_publication_v1,
    reconcile_publication_contact_truth_v1,
)
from services.diagnostic_reasoning_v1.evidence_bag_v1 import (
    load_bounded_evidence_bags_v1,
)
from services.mission_catalog_v1 import compose_mission_catalog_v1
from services.operational_guidance_v1.compose_v1 import compose_operational_guidance_v1
from services.operational_guidance_v1.contract_v1 import FAMILY_WAIT_INSUFFICIENT
from services.product_data.product_read_model_contract_v1 import (
    KNOWN_UNKNOWNS,
    PRODUCT_READ_MODEL_SCHEMA,
    VISIT_FIELD_CLASS_LAB_ONLY,
    product_scoped_shipping_claim_allowed,
    visit_field_label,
)

COL_ON = {ENV_COMMERCIAL_OPPORTUNITY_LAYER_V1: "1"}

R17 = {"shipping": 12, "price": 5, "thinking": 3}
R18 = {"delivery": 12, "price": 5, "thinking": 3}
R20 = {"quality": 20, "shipping": 3, "thinking": 2}
R21 = {"price": 12, "shipping": 5, "thinking": 3}


def _col(counts: dict, slug: str = "cf_live_reality_lab") -> dict:
    return compose_commercial_opportunity_layer_v1(
        {"store_slug": slug, "merchant_reason_counts_week": dict(counts)},
        store_slug=slug,
        environ=COL_ON,
    )


def _ogl(counts: dict, slug: str = "cf_live_reality_lab") -> dict:
    return compose_operational_guidance_v1(
        {"store_slug": slug, "merchant_reason_counts_week": dict(counts)},
        store_slug=slug,
    )


def _primary_family(col: dict) -> str:
    primary = col.get("primary") if isinstance(col.get("primary"), dict) else {}
    return str(primary.get("family") or "")


class DiagnosticStoreSlugTests(unittest.TestCase):
    def test_loader_source_uses_store_slug_not_store_id(self) -> None:
        src = inspect.getsource(load_bounded_evidence_bags_v1)
        self.assertIn("store_slug=slug", src)
        self.assertNotIn("CartRecoveryReason.store_id", src)
        self.assertIn("merchant_reason_counts_store_window", src)

    def test_silent_except_pass_removed_from_loader(self) -> None:
        src = inspect.getsource(load_bounded_evidence_bags_v1)
        self.assertNotIn("except Exception:\n        pass", src)
        self.assertIn("log.warning", src)

    def test_loader_passes_store_slug_to_aggregator(self) -> None:
        with mock.patch(
            "services.dashboard_kpi_time_v1.merchant_reason_counts_store_window",
            return_value=dict(R17),
        ) as mocked:
            bags = load_bounded_evidence_bags_v1("tenant-a")
        mocked.assert_called()
        self.assertEqual(mocked.call_args.kwargs.get("store_slug"), "tenant-a")
        self.assertTrue(bags)
        signals = bags[0].get("signals") or {}
        self.assertGreaterEqual(int(signals.get("shipping") or 0), 12)

    def test_tenant_isolation_argument(self) -> None:
        seen: list[str] = []

        def _fake(dash_store=None, days=7, store_slug=None, **_k):
            seen.append(str(store_slug or ""))
            if store_slug == "store-a":
                return {"shipping": 12}
            return {}

        with mock.patch(
            "services.dashboard_kpi_time_v1.merchant_reason_counts_store_window",
            side_effect=_fake,
        ):
            bags_a = load_bounded_evidence_bags_v1("store-a")
            bags_b = load_bounded_evidence_bags_v1("store-b")
        self.assertEqual(seen, ["store-a", "store-b"])
        self.assertTrue(any(int((b.get("signals") or {}).get("shipping") or 0) >= 12 for b in bags_a))
        self.assertFalse(
            any(int((b.get("signals") or {}).get("shipping") or 0) >= 12 for b in bags_b)
        )


class SummaryReasonCountsAndColTests(unittest.TestCase):
    def test_r17_col_shipping_friction(self) -> None:
        col = _col(R17)
        self.assertFalse(col.get("empty"))
        self.assertEqual(_primary_family(col), "shipping_friction")

    def test_r18_delivery_maps_to_shipping_friction(self) -> None:
        col = _col(R18)
        self.assertEqual(_primary_family(col), "shipping_friction")

    def test_r20_product_confidence(self) -> None:
        col = _col(R20)
        self.assertEqual(_primary_family(col), "product_confidence")

    def test_r21_price(self) -> None:
        col = _col(R21)
        self.assertEqual(_primary_family(col), "price_hesitation")

    def test_zero_reasons_insufficient(self) -> None:
        col = _col({})
        self.assertTrue(col.get("empty"))
        ogl = _ogl({})
        self.assertEqual(ogl.get("family"), FAMILY_WAIT_INSUFFICIENT)

    def test_low_sample_insufficient(self) -> None:
        col = _col({"shipping": 3})
        primary = col.get("primary") if isinstance(col.get("primary"), dict) else {}
        self.assertNotEqual(primary.get("truth_class"), TRUTH_PRODUCTION_READY)
        ogl = _ogl({"shipping": 3})
        self.assertEqual(ogl.get("family"), FAMILY_WAIT_INSUFFICIENT)

    def test_conflicting_share_stays_bounded(self) -> None:
        counts = {"shipping": 8, "price": 8, "thinking": 4}
        col = _col(counts)
        ogl = _ogl(counts)
        # 8/20 = 0.40 is the gate edge — do not invent a second ranker outcome.
        self.assertIn(_primary_family(col) or "empty", {"shipping_friction", "price_hesitation", ""})
        self.assertIn(
            ogl.get("family"),
            {"shipping_friction", "price_hesitation", FAMILY_WAIT_INSUFFICIENT},
        )

    def test_ogl_reads_merchant_reason_counts_week(self) -> None:
        ogl = _ogl(R17)
        self.assertEqual(ogl.get("family"), "shipping_friction")
        ev = str(ogl.get("evidence_summary_ar") or ogl.get("diagnosis") or "")
        self.assertIn("12", ev)
        self.assertIn("20", ev)

    def test_catalog_follows_col_ready_shipping(self) -> None:
        col = _col(R17)
        cat = compose_mission_catalog_v1(
            col_package=col,
            commitments_by_key={},
            store_slug="cf_live_reality_lab",
        )
        primary = cat.get("primary") if isinstance(cat.get("primary"), dict) else {}
        self.assertEqual(str(primary.get("family") or ""), "shipping_friction")

    def test_reality_families_are_merchant_distinct(self) -> None:
        r17 = _col(R17)
        r20 = _col(R20)
        r21 = _col(R21)
        wait = _col({})
        self.assertEqual(_primary_family(r17), "shipping_friction")
        self.assertEqual(_primary_family(r20), "product_confidence")
        self.assertEqual(_primary_family(r21), "price_hesitation")
        self.assertTrue(wait.get("empty"))
        self.assertEqual(_ogl(R17).get("family"), "shipping_friction")
        self.assertIn(str(_ogl(R20).get("family") or ""), {"product_confidence", "product_confidence_quality"})
        self.assertEqual(_ogl(R21).get("family"), "price_hesitation")
        self.assertEqual(_ogl({}).get("family"), FAMILY_WAIT_INSUFFICIENT)
        sees = {
            "shipping": str((_ogl(R17).get("home_surface") or {}).get("what_we_see_ar") or ""),
            "quality": str((_ogl(R20).get("home_surface") or {}).get("what_we_see_ar") or ""),
            "price": str((_ogl(R21).get("home_surface") or {}).get("what_we_see_ar") or ""),
            "wait": str((_ogl({}).get("home_surface") or {}).get("what_we_see_ar") or ""),
        }
        self.assertTrue(len({sees["shipping"], sees["quality"], sees["price"], sees["wait"]}) >= 3)

    def test_home_workspace_family_consistency(self) -> None:
        summary = {
            "store_slug": "cf_live_reality_lab",
            "merchant_reason_counts_week": dict(R17),
        }
        col = compose_commercial_opportunity_layer_v1(
            summary, store_slug="cf_live_reality_lab", environ=COL_ON
        )
        ogl = compose_operational_guidance_v1(
            summary, store_slug="cf_live_reality_lab"
        )
        self.assertEqual(_primary_family(col), "shipping_friction")
        self.assertEqual(ogl.get("family"), "shipping_friction")

    def test_frontend_does_not_rank_commercial_family(self) -> None:
        with open("static/merchant_ui_v2_home.js", encoding="utf-8") as fh:
            home = fh.read()
        with open("static/merchant_ui_v2_workspace.js", encoding="utf-8") as fh:
            workspace = fh.read()
        self.assertIn("commercial_opportunity_layer_v1", home)
        self.assertIn("mission_catalog_v1", home)
        self.assertIn("commercial_opportunity_layer_v1", workspace)
        self.assertNotIn("if (shipping > price)", home)
        self.assertNotIn("if (shipping > price)", workspace)

    def test_no_product_scoped_shipping_overclaim(self) -> None:
        ogl = _ogl(R17)
        blob = " ".join(
            [
                str(ogl.get("diagnosis") or ""),
                str(ogl.get("evidence_summary_ar") or ""),
                str((ogl.get("home_surface") or {}).get("what_we_see_ar") or ""),
            ]
        )
        self.assertNotIn("عنبر ليلي لديه 12", blob)
        self.assertFalse(
            product_scoped_shipping_claim_allowed(
                product_hesitation_n=4, store_shipping_n=12
            )
        )

    def test_stamp_reason_counts_on_summary_helper(self) -> None:
        from services.dashboard_kpi_time_v1 import (
            ensure_merchant_reason_counts_week,
            stamp_hesitation_evidence_from_reason_counts,
        )

        body: dict = {"store_slug": "x", "merchant_reason_counts_week": dict(R17)}
        with mock.patch(
            "services.dashboard_kpi_time_v1.merchant_reason_counts_store_window"
        ) as mocked:
            out = ensure_merchant_reason_counts_week(body, store_slug="x")
            mocked.assert_not_called()
        self.assertEqual(out.get("shipping"), 12)
        ev = body.get("hesitation_evidence_v1") or {}
        self.assertEqual(int(ev.get("hesitation_total") or 0), 20)
        stamped = stamp_hesitation_evidence_from_reason_counts({}, R17)
        self.assertEqual(stamped.get("shipping"), 12)


class ContactTruthTests(unittest.TestCase):
    def test_recoverability_gap_is_not_missing_contact(self) -> None:
        pub = compose_merchant_publication_v1(
            {
                "portfolio": [
                    {
                        "decision_type": "recoverability_gap",
                        "root_cause_key": "missing_contact",
                        "suppressed": False,
                    }
                ],
                "business_domains_v1": {"signals": {"no_phone_total": 0}},
            }
        )
        cc = pub.get("communication_condition") or {}
        self.assertFalse(bool(cc.get("constrained")))

    def test_reconcile_clears_constrained_when_counts_prove_zero(self) -> None:
        body = {
            "merchant_store_cart_counts": {"no_phone_total": 0},
            "merchant_publication_v1": {
                "communication_condition": {
                    "constrained": True,
                    "summary_ar": "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل.",
                }
            },
        }
        reconcile_publication_contact_truth_v1(body)
        cc = (body.get("merchant_publication_v1") or {}).get("communication_condition") or {}
        self.assertFalse(bool(cc.get("constrained")))

    def test_reconcile_does_not_invent_availability_when_counts_absent(self) -> None:
        body = {
            "merchant_publication_v1": {
                "communication_condition": {"constrained": True}
            }
        }
        reconcile_publication_contact_truth_v1(body)
        cc = (body.get("merchant_publication_v1") or {}).get("communication_condition") or {}
        self.assertTrue(bool(cc.get("constrained")))

    def test_leftover_arabic_does_not_override_proven_zero_phone(self) -> None:
        sections = apply_home_diagnosis_language_v1(
            [
                {
                    "id": "carts",
                    "summary_ar": "متابعة بعض السلال مقيدة لأن معلومات التواصل غير متاحة.",
                }
            ],
            summary={
                "merchant_store_cart_counts": {"no_phone_total": 0},
                "home_teaser_inputs_v1": {
                    "health": {"no_phone": 0},
                    "carts": {"no_phone": 0, "waiting": 0},
                    "communication": {"no_phone": 0},
                },
            },
        )
        carts = next(s for s in sections if s["id"] == "carts")
        self.assertNotIn("معلومات التواصل غير متاحة", str(carts.get("diagnosis_ar") or ""))

    def test_persisted_contact_diagnostic_skipped_when_counts_zero(self) -> None:
        sections = apply_home_diagnosis_language_v1(
            [{"id": "health", "summary_ar": "المتجر مستقر."}],
            summary={
                "merchant_store_cart_counts": {"no_phone_total": 0},
                "diagnostic_publication_v1": {
                    "diagnostic_family": "contact_followup_blocked",
                    "diagnosis_ar": "الأدلة تشير إلى أن متابعة العملاء مقيدة لأن معلومات التواصل غير متاحة.",
                    "recommendation_ar": "راجع التواصل.",
                },
            },
        )
        health = next(s for s in sections if s["id"] == "health")
        self.assertNotIn("معلومات التواصل غير متاحة", str(health.get("diagnosis_ar") or ""))


class CartsSnapshotSemanticsTests(unittest.TestCase):
    def test_hot_slice_cap_unchanged(self) -> None:
        self.assertEqual(HOT_SLICE_MAX_ROWS, 25)
        self.assertEqual(NORMAL_CARTS_PAGE_LIMIT, 50)

    def test_snapshot_rows_survive_hot_merge_when_present(self) -> None:
        snapshot = [
            {
                "recovery_key": f"cf_live_reality_lab:cart-{i}",
                "store_slug": "cf_live_reality_lab",
                "zid_cart_id": f"cart-{i}",
            }
            for i in range(38)
        ]
        hot = snapshot[:25]
        merged = merge_hot_slice_active_rows(snapshot, hot, page_limit=50)
        self.assertEqual(len(merged), 38)
        self.assertLessEqual(len(hot), HOT_SLICE_MAX_ROWS)

    def test_empty_snapshot_falls_back_to_hot_cap(self) -> None:
        hot = [
            {"recovery_key": f"rk-{i}", "zid_cart_id": f"c-{i}"}
            for i in range(25)
        ]
        merged = merge_hot_slice_active_rows([], hot, page_limit=50)
        self.assertEqual(len(merged), 25)


class ProductsContractTests(unittest.TestCase):
    def test_contract_ready_and_visit_label(self) -> None:
        self.assertEqual(PRODUCT_READ_MODEL_SCHEMA, "product_read_model_v1")
        self.assertIn("unique_visitors", KNOWN_UNKNOWNS)
        self.assertEqual(visit_field_label(lab_tenant=True), VISIT_FIELD_CLASS_LAB_ONLY)
        self.assertEqual(visit_field_label(lab_tenant=False), "NOT_STORED")
        self.assertNotEqual(visit_field_label(lab_tenant=False), VISIT_FIELD_CLASS_LAB_ONLY)


if __name__ == "__main__":
    unittest.main()
