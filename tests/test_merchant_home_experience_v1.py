# -*- coding: utf-8 -*-
"""Merchant Home Experience v1 — composition consumer certification tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.knowledge_producer_metadata_v1 import (
    enrich_decision_knowledge_metadata_v1,
    enrich_kl_insight_knowledge_metadata_v1,
)
from services.knowledge_routing_v1 import SURFACE_MERCHANT_HOME, route_merchant_home_knowledge_v1
from services.merchant_daily_brief_composer_v2 import compose_merchant_daily_brief_v2
from services.merchant_home_composition_v1 import (
    COMPOSITION_VERSION,
    HOME_MAX_ATTENTION_DISPLAY,
    compose_merchant_home_experience_v1,
)
from services.merchant_decision_layer_v1 import (
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_home_experience.js").read_text(encoding="utf-8")


def _published_decision(**overrides: object) -> dict:
    base = {
        "decision_id": "decision_contact_customer",
        "decision_class": CLASS_NEEDS_ATTENTION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["rk:1"],
        "confidence": "medium",
        "commercial_goal": "recover_revenue",
        "merchant_action": "execute",
        "priority": 300,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "العميل لم يكمل الشراء",
            "why_now_ar": "مرّ وقت كافٍ",
            "if_omitted_ar": "—",
        },
        "decision_timestamp": "2026-07-05T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:1",
        "action_key": "contact_customer",
    }
    base.update(overrides)
    proof_source = str((base.get("proof_sources") or ["rk:1"])[0])
    enrich_decision_knowledge_metadata_v1(
        base,
        store_slug="demo",
        recovery_key=proof_source,
    )
    return base


def _sample_kl_insight(**overrides: object) -> dict:
    base = {
        "insight_key": "hesitation_top_reason",
        "category": "hesitation",
        "severity": "info",
        "title_ar": "سبب التردد الأبرز",
        "message_ar": "السبب الأكثر تسجيلاً هو «price».",
        "evidence": {
            "top_reason": "price",
            "top_count": 42,
            "hesitation_total": 75,
            "distribution": {"price": 42, "shipping": 20},
        },
        "confidence": "medium",
        "data_window": {"days": 7},
        "sample_size": 75,
        "source_tables": ["cart_recovery_reasons"],
        "recommended_action_ar": "راجع التسعير.",
        "evidence_id": "hesitation_reason",
        "evidence_label_ar": "سبب التردد",
    }
    base.update(overrides)
    enrich_kl_insight_knowledge_metadata_v1(base, store_slug="demo", window_days=7)
    return base


class MerchantHomeExperienceV1Tests(unittest.TestCase):
    def test_js_has_no_knowledge_ownership(self) -> None:
        forbidden = (
            "INSIGHT_PRIORITY",
            "pickTopInsights",
            "merchantDecisionExecutable",
            "OIA_BUILDERS",
            "/api/knowledge/report",
        )
        for token in forbidden:
            self.assertNotIn(token, _JS, msg=f"JS still owns knowledge: {token}")

    def test_js_consumes_home_composition(self) -> None:
        self.assertIn("merchant_home_experience_v1", _JS)
        self.assertIn("maApplyHomeExperience", _JS)

    def test_composition_has_five_sections(self) -> None:
        decision = _published_decision()
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"decisions": [decision]}],
            kl_insights=[_sample_kl_insight()],
        )
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر تجريبي",
            date_ar="الأحد 5 يوليو",
            daily_brief=brief,
            kl_insights=[_sample_kl_insight()],
        )
        self.assertEqual(home["version"], COMPOSITION_VERSION)
        self.assertIn("greeting", home)
        self.assertIn("while_away", home)
        self.assertIn("attention_today", home)
        self.assertIn("store_understanding", home)
        self.assertIn("quick_nav", home)

    def test_attention_capped_at_home_max(self) -> None:
        decisions = [
            _published_decision(
                decision_id=f"decision_contact_customer_{i}",
                merge_key=f"cart:{i}",
                action_key="contact_customer",
            )
            for i in range(6)
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"decisions": decisions}],
        )
        home = compose_merchant_home_experience_v1(daily_brief=brief)
        items = home["attention_today"]["items"]
        self.assertLessEqual(len(items), HOME_MAX_ATTENTION_DISPLAY)

    def test_dedupe_across_sections(self) -> None:
        decision = _published_decision(
            decision_class=CLASS_OBSERVATION,
            action_key="monitor",
            decision_id="decision_monitor_return",
        )
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"decisions": [decision]}],
        )
        home = compose_merchant_home_experience_v1(daily_brief=brief)
        away_keys = {
            i.get("aggregation_key") or i.get("source_knowledge_id")
            for i in home["while_away"]["items"]
        }
        attention_keys = {
            i.get("aggregation_key") or i.get("source_knowledge_id")
            for i in home["attention_today"]["items"]
        }
        overlap = away_keys & attention_keys
        self.assertFalse(overlap, msg=f"duplicate keys across sections: {overlap}")

    def test_greeting_fields(self) -> None:
        home = compose_merchant_home_experience_v1(
            merchant_name_ar="متجر أ",
            date_ar="اليوم",
            daily_brief=compose_merchant_daily_brief_v2(decision_bundles=[]),
        )
        greeting = home["greeting"]
        self.assertTrue(greeting["greeting_ar"])
        self.assertEqual(greeting["merchant_name_ar"], "متجر أ")
        self.assertEqual(greeting["date_ar"], "اليوم")

    def test_routing_surface_merchant_home(self) -> None:
        insight = _sample_kl_insight()
        feed = route_merchant_home_knowledge_v1(kl_insights=[insight])
        self.assertEqual(feed["surface"], SURFACE_MERCHANT_HOME)

    def test_quick_nav_has_core_links(self) -> None:
        home = compose_merchant_home_experience_v1(
            daily_brief=compose_merchant_daily_brief_v2(decision_bundles=[]),
            nav_metadata={"active_carts": 3, "waiting_send": 2},
        )
        nav_ids = {i["id"] for i in home["quick_nav"]["items"]}
        self.assertIn("knowledge", nav_ids)
        self.assertIn("active_carts", nav_ids)
        self.assertIn("completed", nav_ids)
        self.assertIn("settings", nav_ids)

    def test_experience_tier_architecture_placeholder(self) -> None:
        home = compose_merchant_home_experience_v1(
            daily_brief=compose_merchant_daily_brief_v2(decision_bundles=[]),
            experience_tier="starter",
        )
        self.assertEqual(home["experience_tier"], "starter")
        self.assertIn("starter", home["tier_capabilities"])
        self.assertIn("growth", home["tier_capabilities"])
        self.assertIn("pro", home["tier_capabilities"])

    def test_identical_input_identical_composition(self) -> None:
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"decisions": [_published_decision()]}],
            kl_insights=[_sample_kl_insight()],
        )
        a = compose_merchant_home_experience_v1(daily_brief=brief, kl_insights=[_sample_kl_insight()])
        b = compose_merchant_home_experience_v1(daily_brief=brief, kl_insights=[_sample_kl_insight()])
        self.assertEqual(
            a["attention_today"]["items"],
            b["attention_today"]["items"],
        )


if __name__ == "__main__":
    unittest.main()
