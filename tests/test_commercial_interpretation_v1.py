# -*- coding: utf-8 -*-
"""Commercial Interpretation Layer V1 — acceptance tests."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from services.commercial_interpretation_v1 import (
    CTA_AFFECTED_CARTS_AR,
    DRILLDOWN_NOPHONE,
    EVIDENCE_SOURCE_NO_PHONE,
    INTERPRETATION_MISSING_CONTACT,
    apply_commercial_interpretation_to_home_v1,
    build_missing_contact_blocks_recovery_v1,
    clear_commercial_interpretation_last_valid_cache_v1,
    enrich_knowledge_report_commercial_interpretation_v1,
    evaluate_commercial_interpretations_v1,
    merchant_facing_text_is_clean,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

_REPO = Path(__file__).resolve().parents[1]


class TestMissingContactInterpretation(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_50_canonical_cases_generate_interpretation(self) -> None:
        interp, obs = build_missing_contact_blocks_recovery_v1(
            store_slug="demo",
            no_phone_total=50,
        )
        self.assertTrue(obs["generated"])
        assert interp is not None
        self.assertEqual(interp["interpretation_id"], INTERPRETATION_MISSING_CONTACT)
        self.assertEqual(interp["evidence_count"], 50)
        self.assertIn("50", interp["evidence_text"])
        self.assertEqual(
            interp["conclusion"],
            "أكبر عائق أمام الاسترجاع حاليًا هو نقص بيانات التواصل.",
        )
        self.assertEqual(interp["confidence_level"], "high")
        self.assertTrue(interp["is_primary_commercial_blocker"])
        self.assertEqual(interp["drilldown_target"], DRILLDOWN_NOPHONE)
        self.assertEqual(interp["evidence_source"], EVIDENCE_SOURCE_NO_PHONE)

    def test_evidence_count_equals_canonical_no_phone(self) -> None:
        for count in (1, 7, 50, 128):
            interp, _ = build_missing_contact_blocks_recovery_v1(
                store_slug="store-a",
                no_phone_total=count,
            )
            assert interp is not None
            self.assertEqual(interp["evidence_count"], count)

    def test_zero_cases_suppress(self) -> None:
        interp, obs = build_missing_contact_blocks_recovery_v1(
            store_slug="demo",
            no_phone_total=0,
        )
        self.assertIsNone(interp)
        self.assertTrue(obs["suppressed"])
        self.assertEqual(obs["suppression_reason"], "count_zero")

    def test_confidence_high_for_direct_canonical(self) -> None:
        interp, _ = build_missing_contact_blocks_recovery_v1(
            store_slug="demo",
            no_phone_total=50,
        )
        assert interp is not None
        self.assertEqual(interp["confidence_level"], "high")
        self.assertTrue(interp["confidence_reason"])

    def test_no_technical_field_names_in_merchant_copy(self) -> None:
        interp, _ = build_missing_contact_blocks_recovery_v1(
            store_slug="demo",
            no_phone_total=50,
        )
        assert interp is not None
        merchant_fields = [
            interp["conclusion"],
            interp["evidence_text"],
            interp["business_impact"],
            interp["cartflow_action"],
            interp["merchant_action"],
            interp["expected_result"],
            interp["home_headline_ar"],
            interp["home_impact_ar"],
            interp["home_cartflow_action_ar"],
            interp["home_merchant_action_ar"],
            interp["knowledge_progression"]["observation_ar"],
            interp["knowledge_progression"]["evidence_ar"],
            interp["knowledge_progression"]["explanation_ar"],
            interp["knowledge_progression"]["recommendation_ar"],
        ]
        for text in merchant_fields:
            self.assertTrue(merchant_facing_text_is_clean(text), text)

    def test_store_isolation_and_demo_never_leaks(self) -> None:
        pkg_a = evaluate_commercial_interpretations_v1(
            store_slug="merchant-a",
            no_phone_total=50,
        )
        pkg_b = evaluate_commercial_interpretations_v1(
            store_slug="merchant-b",
            no_phone_total=3,
        )
        self.assertEqual(pkg_a["store_slug"], "merchant-a")
        self.assertEqual(pkg_b["store_slug"], "merchant-b")
        self.assertEqual(pkg_a["primary"]["evidence_count"], 50)
        self.assertEqual(pkg_b["primary"]["evidence_count"], 3)
        self.assertNotEqual(
            pkg_a["primary"]["store_slug"],
            pkg_b["primary"]["store_slug"],
        )


class TestHomeConsumesGovernedOutput(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_home_consumes_governed_output_not_rebuild(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر اختبار",
            date_ar="الجمعة",
            brief_date="2026-07-17",
            daily_brief={"version": "v1", "achievements": [], "attention_items": []},
            kl_insights=[],
            nav_metadata={
                "active_carts": 60,
                "waiting_send": 10,
                "canonical_no_phone_total": 50,
                "knowledge_cart_count": 60,
            },
            store_slug="demo",
        )
        package = home.get("commercial_interpretation_v1")
        self.assertIsInstance(package, dict)
        primary = package.get("primary")
        assert isinstance(primary, dict)
        items = home["store_understanding"]["items"]
        self.assertGreaterEqual(len(items), 1)
        lead = items[0]
        self.assertEqual(
            lead.get("commercial_interpretation_id"),
            INTERPRETATION_MISSING_CONTACT,
        )
        self.assertEqual(lead.get("evidence_count"), 50)
        self.assertEqual(lead.get("evidence_label_ar"), primary.get("evidence_text"))
        # Knowledge explains (observation), Attention decides — no action on Knowledge.
        self.assertTrue(lead.get("observation_ar"))
        self.assertFalse(str(lead.get("action_ar") or "").strip())
        att = home["attention_today"]["items"][0]
        self.assertTrue(att.get("action_ar"))
        self.assertEqual(att.get("drilldown_href"), "#carts?tab=nophone")
        # Must not leave the empty-knowledge contradiction.
        blob = " ".join(
            str(items[0].get(k) or "")
            for k in (
                "observation_ar",
                "title_ar",
                "evidence_label_ar",
                "impact_ar",
                "action_ar",
            )
        )
        self.assertNotIn("لا ملاحظة جاهزة", blob)
        self.assertNotIn("لا توجد استنتاجات كافية", blob)

    def test_home_failure_does_not_break_composition(self) -> None:
        with patch(
            "services.commercial_interpretation_v1.evaluate_commercial_interpretations_v1",
            side_effect=RuntimeError("boom"),
        ):
            home = compose_merchant_home_experience_v1(
                merchant_name_ar="متجر",
                daily_brief={},
                kl_insights=[],
                nav_metadata={"canonical_no_phone_total": 50},
                store_slug="demo",
            )
        self.assertEqual(home.get("version"), "v1")
        self.assertIn("store_understanding", home)
        self.assertIn("attention_today", home)

    def test_zero_no_phone_keeps_empty_understanding_honest(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            daily_brief={},
            kl_insights=[],
            nav_metadata={"canonical_no_phone_total": 0, "active_carts": 5},
            store_slug="demo",
        )
        package = home.get("commercial_interpretation_v1")
        self.assertIsNone((package or {}).get("primary"))
        self.assertEqual(home["store_understanding"]["items"], [])

    def test_cta_drilldown_is_nophone(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر",
            daily_brief={},
            kl_insights=[],
            nav_metadata={"canonical_no_phone_total": 50},
            store_slug="demo",
        )
        # CTA lives on Attention (decision), not Knowledge (explain).
        att = home["attention_today"]["items"][0]
        self.assertEqual(att.get("drilldown_href"), DRILLDOWN_NOPHONE)
        self.assertEqual(att.get("cta_label_ar"), CTA_AFFECTED_CARTS_AR)


class TestKnowledgeConsumesSameInterpretation(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_knowledge_consumes_same_interpretation(self) -> None:
        payload = {
            "ok": True,
            "store_slug": "demo",
            "insights": [],
            "knowledge_layer_projection_v1": {
                "display_cards": [],
                "empty_reason": "insufficient_actionable_knowledge",
                "observability": {"display_card_count": 0},
            },
            "merchant_store_cart_counts": {"no_phone_total": 50, "active_total": 60},
        }
        enrich_knowledge_report_commercial_interpretation_v1(
            payload,
            store_slug="demo",
            no_phone_total=50,
        )
        package = payload["commercial_interpretation_v1"]
        self.assertEqual(package["primary"]["evidence_count"], 50)
        self.assertEqual(
            payload["insights"][0]["insight_key"],
            INTERPRETATION_MISSING_CONTACT,
        )
        cards = payload["knowledge_layer_projection_v1"]["display_cards"]
        self.assertEqual(cards[0]["insight_key"], INTERPRETATION_MISSING_CONTACT)
        self.assertIsNone(payload["knowledge_layer_projection_v1"]["empty_reason"])
        self.assertEqual(cards[0]["drilldown_href"], DRILLDOWN_NOPHONE)


class TestFailurePreservesLastValid(unittest.TestCase):
    def setUp(self) -> None:
        clear_commercial_interpretation_last_valid_cache_v1()

    def test_failure_preserves_last_valid_for_same_store(self) -> None:
        first = evaluate_commercial_interpretations_v1(
            store_slug="demo",
            no_phone_total=50,
        )
        self.assertTrue(first["ok"])
        self.assertEqual(first["primary"]["evidence_count"], 50)

        with patch(
            "services.commercial_interpretation_v1.build_missing_contact_blocks_recovery_v1",
            side_effect=RuntimeError("fail"),
        ):
            failed = evaluate_commercial_interpretations_v1(
                store_slug="demo",
                no_phone_total=50,
            )
        self.assertFalse(failed["ok"])
        self.assertTrue(failed["used_last_valid"])
        self.assertEqual(failed["primary"]["evidence_count"], 50)
        self.assertEqual(failed["primary"]["store_slug"], "demo")


class TestNoMainLogicAndNoAi(unittest.TestCase):
    def test_no_interpretation_logic_added_as_main_module_owner(self) -> None:
        main_text = (_REPO / "main.py").read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("build_missing_contact_blocks_recovery_v1", main_text)
        self.assertNotIn("Commercial Interpretation Layer", main_text)
        # Wiring of existing counter into nav is allowed; conclusion builders are not.
        self.assertNotIn("أكبر عائق أمام الاسترجاع", main_text)

    def test_package_marks_non_ai_non_probabilistic(self) -> None:
        pkg = evaluate_commercial_interpretations_v1(
            store_slug="demo",
            no_phone_total=12,
        )
        obs = pkg["observability"]
        self.assertFalse(obs["ai_used"])
        self.assertFalse(obs["probabilistic"])


class TestJsCtaAndParity(unittest.TestCase):
    def test_js_cta_opens_nophone_filtered_view(self) -> None:
        ecc = (_REPO / "static" / "merchant_dashboard_home_v1.js").read_text(
            encoding="utf-8", errors="replace"
        )
        pe = (_REPO / "static" / "merchant_home_experience.js").read_text(
            encoding="utf-8", errors="replace"
        )
        # CTA drilldown lives on Attention after Knowledge Redistribution V1.
        self.assertIn("goToCartTab", ecc)
        self.assertIn("nophone", ecc)
        self.assertIn("drilldownHref", ecc)
        self.assertIn("goDrilldownOnclick", ecc)
        self.assertIn("goToCartTab", pe)
        self.assertIn("nophone", pe)
        att_fn = ecc[
            ecc.find("function renderAttention") : ecc.find("function renderTimeline")
        ]
        self.assertIn("drilldownHref(item)", att_fn)
        self.assertIn("goDrilldownOnclick(item)", att_fn)

    def test_mobile_and_desktop_share_same_governed_fields(self) -> None:
        """Knowledge explains; Attention owns the governed CTA fields."""
        home = {
            "store_understanding": {"items": []},
            "attention_today": {"items": []},
            "observability": {},
        }
        apply_commercial_interpretation_to_home_v1(
            home,
            store_slug="demo",
            no_phone_total=50,
        )
        lead = home["store_understanding"]["items"][0]
        for key in (
            "observation_ar",
            "evidence_label_ar",
            "impact_ar",
            "confidence",
        ):
            self.assertTrue(lead.get(key), key)
        self.assertFalse(str(lead.get("action_ar") or "").strip())
        att = home["attention_today"]["items"][0]
        for key in (
            "headline_ar",
            "why_ar",
            "action_ar",
            "if_ignored_ar",
            "drilldown_href",
            "cta_label_ar",
        ):
            self.assertTrue(att.get(key), key)


class TestCountersDoNotRegress(unittest.TestCase):
    def test_interpretation_does_not_mutate_counter_payload(self) -> None:
        counters = {"no_phone_total": 50, "active_total": 60}
        payload = {"merchant_store_cart_counts": dict(counters)}
        evaluate_commercial_interpretations_v1(
            store_slug="demo",
            no_phone_total=50,
            payload=payload,
        )
        self.assertEqual(payload["merchant_store_cart_counts"], counters)


if __name__ == "__main__":
    unittest.main()
