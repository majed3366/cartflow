# -*- coding: utf-8 -*-
"""Business Findings Engine V1 — deterministic contract, families, ranking, safety."""
from __future__ import annotations

import unittest

from services.business_findings_contract_v1 import (
    REC_TEST,
    STATUS_INSUFFICIENT,
    TYPE_MISSING_CONTACT_BLOCKS,
    is_merchant_worthy,
)
from services.business_findings_engine_v1 import (
    dedupe_findings_v1,
    run_business_findings_engine_v1,
    score_finding_v1,
    select_home_candidates_v1,
)
from services.business_findings_evidence_v1 import (
    build_conflicting_evidence_bundle_v1,
    build_demo_rich_evidence_bundle_v1,
    build_insufficient_evidence_bundle_v1,
)


class TestBusinessFindingsEngineV1(unittest.TestCase):
    def test_demo_produces_multiple_distinct_families(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        self.assertTrue(pkg["ok"])
        self.assertFalse(pkg["ai_used"])
        findings = pkg["findings"]
        self.assertGreaterEqual(len(findings), 5)
        families = {f.get("family_key") for f in findings}
        self.assertGreaterEqual(len(families), 3)
        types = {f.get("finding_type") for f in findings}
        # Required product / recovery / hesitation / insufficient-or-traffic
        self.assertTrue(any("product" in (f or "") for f in families))
        self.assertTrue(
            any(
                t
                and (
                    "hesitation" in t
                    or "dominant_hesitation" in t
                )
                for t in types
            )
        )
        self.assertTrue(
            any(
                "channel" in (f or "") or "whatsapp" in (t or "")
                for f, t in ((x.get("family_key"), x.get("finding_type")) for x in findings)
            )
        )
        self.assertTrue(
            any(
                f.get("status") == STATUS_INSUFFICIENT
                or "insufficient" in str(f.get("finding_type") or "")
                or "traffic_versus" in str(f.get("finding_type") or "")
                for f in findings
            )
        )

    def test_deterministic_output(self) -> None:
        a = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        b = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        ids_a = [f["finding_id"] for f in a["findings"]]
        ids_b = [f["finding_id"] for f in b["findings"]]
        self.assertEqual(ids_a, ids_b)
        self.assertEqual(
            [f["title"] for f in a["findings"]],
            [f["title"] for f in b["findings"]],
        )

    def test_tenant_isolation_in_finding_ids(self) -> None:
        demo = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        other = run_business_findings_engine_v1(store_slug="demo2", demo_fixture=True)
        self.assertEqual(demo["store_slug"], "demo")
        self.assertEqual(other["store_slug"], "demo2")
        for f in demo["findings"]:
            self.assertEqual(f["store_slug"], "demo")
        for f in other["findings"]:
            self.assertEqual(f["store_slug"], "demo2")

    def test_missing_contact_deduped_once(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        contactish = [
            f
            for f in pkg["findings"]
            if f.get("finding_type") == TYPE_MISSING_CONTACT_BLOCKS
            or "بيانات التواصل" in str(f.get("title") or "")
        ]
        self.assertEqual(len(contactish), 1)

    def test_home_candidates_no_repeat_ids(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        home = pkg["home_candidates_v1"]
        # Opportunity / understanding must not duplicate primary or action.
        primary = (home.get("most_important_finding") or {}).get("finding_id")
        action = (home.get("highest_value_action") or {}).get("finding_id")
        opp = (home.get("strongest_opportunity") or {}).get("finding_id")
        und = (home.get("new_understanding") or {}).get("finding_id")
        if opp:
            self.assertNotEqual(opp, primary)
            self.assertNotEqual(opp, action)
        if und:
            self.assertNotEqual(und, primary)
            self.assertNotEqual(und, action)
        # act_now may legitimately occupy both important + action.
        if primary and action and primary == action:
            self.assertEqual(
                (home.get("highest_value_action") or {}).get("recommendation_type"),
                "act_now",
            )

    def test_whatsapp_test_is_test_not_confirmed_cause(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        tests = [
            f
            for f in pkg["findings"]
            if "whatsapp_message_timing_test" in str(f.get("finding_type") or "")
        ]
        self.assertTrue(tests)
        for f in tests:
            self.assertEqual(f.get("recommendation_type"), REC_TEST)
            self.assertFalse(f.get("is_confirmed_cause"))

    def test_insufficient_bundle_emits_honest_insufficient(self) -> None:
        ev = build_insufficient_evidence_bundle_v1()
        pkg = run_business_findings_engine_v1(store_slug="demo", evidence=ev)
        self.assertGreaterEqual(pkg["observability"]["insufficient_evidence_count"], 1)
        self.assertTrue(
            any(
                f.get("status") == STATUS_INSUFFICIENT
                or f.get("recommendation_type") == "insufficient_evidence"
                for f in pkg["findings"]
            )
        )

    def test_conflicting_bundle_can_flag_conflict_or_split(self) -> None:
        ev = build_conflicting_evidence_bundle_v1()
        pkg = run_business_findings_engine_v1(store_slug="demo", evidence=ev)
        self.assertTrue(pkg["findings"])
        # Either explicit conflicting finding or dual equal hesitation handling
        self.assertTrue(
            pkg["observability"]["conflicting_evidence_count"] >= 1
            or any("متعارض" in str(f.get("title") or "") for f in pkg["findings"])
            or any("موزّعة" in str(f.get("title") or "") for f in pkg["findings"])
        )

    def test_no_raw_event_as_finding(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        for f in pkg["findings"]:
            self.assertTrue(is_merchant_worthy(f), msg=f.get("title"))
            self.assertFalse(str(f.get("title") or "").startswith("تمت إضافة"))

    def test_evidence_linkage_present(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        for f in pkg["findings"]:
            self.assertTrue(str(f.get("evidence_summary") or "").strip())
            self.assertGreaterEqual(int(f.get("sample_size") or 0), 0)

    def test_ranking_prefers_act_now(self) -> None:
        high = {
            "sample_size": 40,
            "confidence_score": 0.9,
            "status": "confirmed",
            "recommendation_type": "act_now",
            "home_eligible": True,
            "family_key": "contact_blocker",
        }
        low = {
            "sample_size": 5,
            "confidence_score": 0.2,
            "status": "emerging",
            "recommendation_type": "monitor",
            "home_eligible": False,
            "family_key": "other",
        }
        self.assertGreater(score_finding_v1(high), score_finding_v1(low))

    def test_dedupe_collapses_contact_synonyms(self) -> None:
        items = [
            {
                "finding_id": "a",
                "finding_type": "other",
                "family_key": "x",
                "title": "43 سلة بلا رقم",
                "merchant_summary": "لا يمكن الإرسال",
                "rank_score": 10,
            },
            {
                "finding_id": "b",
                "finding_type": TYPE_MISSING_CONTACT_BLOCKS,
                "family_key": "contact_blocker",
                "title": "نقص بيانات التواصل يعيق الاسترجاع",
                "merchant_summary": "بيانات التواصل ناقصة",
                "rank_score": 50,
            },
        ]
        out, n = dedupe_findings_v1(items)
        self.assertEqual(n, 1)
        self.assertEqual(len([f for f in out if "تواصل" in f["title"] or "بلا رقم" in f["title"]]), 1)

    def test_knowledge_items_projected(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        self.assertEqual(len(pkg["knowledge_items_v1"]), len(pkg["findings"]))
        for item in pkg["knowledge_items_v1"]:
            self.assertTrue(item.get("finding_v1"))
            self.assertFalse(item.get("ai_used"))
            self.assertIn("knowledge_layer", item.get("eligible_surfaces") or [])

    def test_idempotent_finding_ids(self) -> None:
        ev = build_demo_rich_evidence_bundle_v1()
        a = run_business_findings_engine_v1(store_slug="demo", evidence=ev)
        b = run_business_findings_engine_v1(store_slug="demo", evidence=ev)
        self.assertEqual(
            [f["finding_id"] for f in a["findings"]],
            [f["finding_id"] for f in b["findings"]],
        )

    def test_home_selection_structure(self) -> None:
        pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
        home = select_home_candidates_v1(pkg["findings"])
        self.assertIn("most_important_finding", home)
        self.assertIn("strongest_opportunity", home)
        self.assertIn("highest_value_action", home)
        self.assertIn("new_understanding", home)


if __name__ == "__main__":
    unittest.main()
