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


if __name__ == "__main__":
    unittest.main()
