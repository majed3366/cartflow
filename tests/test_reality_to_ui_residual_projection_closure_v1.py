# -*- coding: utf-8 -*-
"""Reality-to-UI Residual Projection Closure V1 — contact + carts snapshot."""
from __future__ import annotations

import unittest

from services.dashboard_hot_slice_v1 import HOT_SLICE_MAX_ROWS, NORMAL_CARTS_PAGE_LIMIT
from services.decision_composition_engine_v1.merchant_publication_v1 import (
    compose_merchant_publication_v1,
    reconcile_publication_contact_truth_v1,
    stamp_contact_truth_v1,
)
from services.home_executive_summary_v1.compose_v1 import build_home_executive_summary_v1
from services.home_executive_summary_v1.diagnosis_language_v1 import (
    apply_home_diagnosis_language_v1,
)


FALSE_CONTACT_AR = "معلومات التواصل غير متاحة"
STALE_PUB = {
    "ok": True,
    "communication_condition": {
        "constrained": True,
        "normal_forbidden": True,
        "summary_ar": "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل.",
    },
}


class ContactReconciliationTests(unittest.TestCase):
    def test_no_phone_zero_clears_stale_publication_via_stamp(self) -> None:
        body = {
            "merchant_store_cart_counts": {"no_phone_total": 0},
            "merchant_publication_v1": dict(STALE_PUB),
        }
        stamp_contact_truth_v1(body)
        del body["merchant_store_cart_counts"]
        reconcile_publication_contact_truth_v1(body)
        cc = (body.get("merchant_publication_v1") or {}).get("communication_condition") or {}
        self.assertFalse(bool(cc.get("constrained")))
        self.assertNotIn("نقص معلومات التواصل", str(cc.get("summary_ar") or ""))

    def test_no_phone_positive_keeps_operational_contact(self) -> None:
        pub = compose_merchant_publication_v1(
            {
                "portfolio": [],
                "business_domains_v1": {"signals": {"no_phone_total": 4, "available": True}},
            },
            summary={"merchant_store_cart_counts": {"no_phone_total": 4}},
        )
        cc = pub.get("communication_condition") or {}
        self.assertTrue(bool(cc.get("constrained")))
        self.assertIn("نقص معلومات التواصل", str(cc.get("summary_ar") or ""))

    def test_unknown_counts_do_not_invent_availability(self) -> None:
        body = {"merchant_publication_v1": dict(STALE_PUB)}
        reconcile_publication_contact_truth_v1(body)
        cc = (body.get("merchant_publication_v1") or {}).get("communication_condition") or {}
        self.assertTrue(bool(cc.get("constrained")))

    def test_stale_publication_loses_to_current_zero(self) -> None:
        body = {
            "contact_truth_v1": {
                "no_phone_total": 0,
                "source": "merchant_store_cart_counts",
                "key_present": True,
            },
            "merchant_publication_v1": dict(STALE_PUB),
            "home_teaser_inputs_v1": {
                "health": {
                    "no_phone": 0,
                    "domain_summary_ar": "المتجر يحتاج تدخلاً عاجلاً — متابعة العملاء مقيدة بسبب نقص معلومات التواصل.",
                },
                "communication": {
                    "no_phone": 0,
                    "constrained": True,
                    "domain_summary_ar": "متابعة بعض العملاء مقيدة بسبب نقص معلومات التواصل.",
                },
                "carts": {"no_phone": 0, "waiting": 0},
            },
            "home_executive_summary_v1": {
                "sections": [
                    {
                        "id": "health",
                        "diagnosis_ar": f"تشير الأدلة إلى أن متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                        "summary_ar": f"تشير الأدلة إلى أن متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                    },
                    {
                        "id": "communication",
                        "diagnosis_ar": f"تشير الأدلة إلى أن متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                        "summary_ar": f"تشير الأدلة إلى أن متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                    },
                ]
            },
            "diagnostic_publication_v1": {
                "diagnostic_family": "checkout_abandonment_after_shipping",
                "diagnosis_ar": "الشحن يتكرر عند إتمام الشراء.",
                "recommendation_ar": "افصل تكلفة الشحن عن المدة.",
            },
        }
        reconcile_publication_contact_truth_v1(body)
        health = next(
            s
            for s in (body["home_executive_summary_v1"]["sections"])
            if s["id"] == "health"
        )
        comm = next(
            s
            for s in (body["home_executive_summary_v1"]["sections"])
            if s["id"] == "communication"
        )
        self.assertNotIn(FALSE_CONTACT_AR, str(health.get("diagnosis_ar") or ""))
        self.assertNotIn(FALSE_CONTACT_AR, str(comm.get("diagnosis_ar") or ""))
        self.assertFalse(
            bool(
                (body.get("merchant_publication_v1") or {})
                .get("communication_condition", {})
                .get("constrained")
            )
        )

    def test_mixed_contact_uses_authoritative_count(self) -> None:
        pub = compose_merchant_publication_v1(
            {
                "portfolio": [],
                "business_domains_v1": {"signals": {"no_phone_total": 12, "waiting_total": 3}},
            },
            summary={"merchant_store_cart_counts": {"no_phone_total": 0, "waiting_total": 3}},
        )
        cc = pub.get("communication_condition") or {}
        self.assertFalse(bool(cc.get("constrained")))

    def test_hes_compose_does_not_paint_false_contact_when_stamp_zero(self) -> None:
        hes = build_home_executive_summary_v1(
            {
                "contact_truth_v1": {"no_phone_total": 0, "key_present": True},
                "merchant_publication_v1": dict(STALE_PUB),
                "home_teaser_inputs_v1": {
                    "health": {"no_phone": 0, "abandoned_carts": 0, "active_carts": 4},
                    "communication": {"no_phone": 0, "constrained": True, "waiting": 0},
                    "carts": {"no_phone": 0, "waiting": 0},
                    "decisions": {},
                },
            }
        )
        painted = " ".join(
            str(s.get("summary_ar") or s.get("diagnosis_ar") or "")
            for s in (hes.get("sections") or [])
            if isinstance(s, dict)
        )
        self.assertNotIn("نقص معلومات التواصل", painted)
        self.assertNotIn(FALSE_CONTACT_AR, painted)

    def test_persisted_checkout_family_does_not_keep_contact_leftover(self) -> None:
        sections = apply_home_diagnosis_language_v1(
            [
                {
                    "id": "health",
                    "summary_ar": f"متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                    "diagnosis_ar": f"متابعة العملاء مقيدة لأن {FALSE_CONTACT_AR}.",
                }
            ],
            summary={
                "contact_truth_v1": {"no_phone_total": 0, "key_present": True},
                "diagnostic_publication_v1": {
                    "diagnostic_family": "checkout_abandonment_after_shipping",
                    "diagnosis_ar": "الشحن يتكرر عند إتمام الشراء.",
                    "recommendation_ar": "افصل تكلفة الشحن عن المدة.",
                },
            },
        )
        health = next(s for s in sections if s["id"] == "health")
        self.assertNotIn(FALSE_CONTACT_AR, str(health.get("diagnosis_ar") or ""))


class CartsSnapshotLawTests(unittest.TestCase):
    def test_hot_slice_cap_unchanged(self) -> None:
        self.assertEqual(HOT_SLICE_MAX_ROWS, 25)
        self.assertEqual(NORMAL_CARTS_PAGE_LIMIT, 50)

    def test_lab_reset_deletes_lab_snapshots_only(self) -> None:
        from pathlib import Path

        src = Path("services/live_reality_lab_v1/apply_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("DashboardSnapshot.store_slug == LAB_STORE_SLUG", src)
        self.assertIn("dashboard_snapshots", src)

    def test_thirty_eight_production_shaped_rows_fit_default_cap(self) -> None:
        import json

        from services.dashboard_snapshot_normal_carts_slim_v1 import (
            slim_normal_carts_payload_for_snapshot,
        )
        from services.dashboard_snapshot_v1 import (
            SNAPSHOT_TYPE_NORMAL_CARTS,
            encode_snapshot_payload_json,
            snapshot_payload_json_cap,
        )

        fat = {
            "recovery_key": "cf_live_reality_lab:lrl_v2_00",
            "zid_cart_id": "lrl_v2_00",
            "merchant_cart_bucket": "attention",
            "cart_detail_projection_v1": {"lines": ["detail"] * 40, "note": "نص " * 80},
            "merchant_intelligence_v1": {"blob": "i" * 800},
            "merchant_proof_surface_v1": {"proof": "p" * 400},
            "merchant_explanation_v1": {"what_happened_ar": "شرح " * 40},
            "merchant_product_name": "عود ملكي مركز",
            "merchant_cart_value": 189.0,
            "merchant_time_relative_ar": "منذ 1 دقيقة",
        }
        rows = []
        for i in range(38):
            row = dict(fat)
            row["recovery_key"] = f"cf_live_reality_lab:lrl_v2_{i:02d}"
            row["zid_cart_id"] = f"lrl_v2_{i:02d}"
            rows.append(row)
        payload = {
            "merchant_carts_page_rows": rows,
            "merchant_archived_carts_page_rows": [],
            "merchant_cart_filter_counts": {"all": 38, "attention": 38, "nophone": 0},
        }
        slim = slim_normal_carts_payload_for_snapshot(payload)
        raw = json.dumps(slim, ensure_ascii=False, default=str)
        cap = snapshot_payload_json_cap(SNAPSHOT_TYPE_NORMAL_CARTS)
        self.assertGreaterEqual(cap, 1_200_000)
        self.assertLessEqual(len(raw.encode("utf-8")), cap)
        encoded = encode_snapshot_payload_json(slim, snapshot_type=SNAPSHOT_TYPE_NORMAL_CARTS)
        self.assertEqual(encoded, raw)

    def test_lab_reset_cart_delete_is_store_scoped_not_prefix(self) -> None:
        from pathlib import Path

        src = Path("services/live_reality_lab_v1/apply_v1.py").read_text(
            encoding="utf-8"
        )
        reset_fn = src.split("def reset_lab_tenant_data_v1", 1)[1].split(
            "def _reset_lab_extended_truth", 1
        )[0]
        self.assertIn("AbandonedCart.store_id == int(store.id)", reset_fn)
        self.assertNotIn("LAB_CART_ID_PREFIX_ANY", reset_fn)


if __name__ == "__main__":
    unittest.main()
