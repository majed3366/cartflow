# -*- coding: utf-8 -*-
"""PIB-3 — Recovery Journey Explainability acceptance tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.customer_lifecycle_states_v1 import (
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    STATE_NEEDS_INTERVENTION,
)
from services.knowledge_producer_metadata_v1 import (
    enrich_decision_knowledge_metadata_v1,
    enrich_kl_insight_knowledge_metadata_v1,
)
from services.merchant_daily_brief_composer_v2 import compose_merchant_daily_brief_v2
from services.merchant_decision_layer_v1 import (
    CLASS_NEEDS_ATTENTION,
    CLASS_OBSERVATION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1
from services.merchant_recovery_journey_home_v1 import (
    build_recovery_journey_for_attention_v1,
    is_recovery_journey_complete_v1,
)

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_dashboard_home_v1.js").read_text(encoding="utf-8")


def _obtain_contact(**overrides: object) -> dict:
    base = {
        "decision_id": "decision_obtain_contact",
        "decision_class": CLASS_OBSERVATION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["rk:contact"],
        "confidence": "insufficient",
        "commercial_goal": "recover_revenue",
        "merchant_action": "none",
        "priority": 100,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "السبب محفوظ — بانتظار رقم العميل لإكمال الإرسال.",
            "why_now_ar": "لا يمكن متابعة الاسترجاع بدون رقم تواصل",
            "if_omitted_ar": "تبقى السلة بدون إرسال استرجاع آلي",
        },
        "decision_timestamp": "2026-05-04T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:contact:1",
        "action_key": "obtain_contact",
    }
    base.update(overrides)
    enrich_decision_knowledge_metadata_v1(
        base, store_slug="demo", recovery_key="rk:contact"
    )
    return base


def _fix_channel(**overrides: object) -> dict:
    base = {
        "decision_id": "decision_fix_channel",
        "decision_class": CLASS_NEEDS_ATTENTION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["rk:fail"],
        "confidence": "high",
        "commercial_goal": "recover_revenue",
        "merchant_action": "execute",
        "priority": 400,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "فشل إرسال واتساب",
            "why_now_ar": "فشل إرسال رسالة الاسترجاع — يلزم إصلاح قناة واتساب",
            "if_omitted_ar": "تتوقف رسائل الاسترجاع على هذه السلة",
        },
        "decision_timestamp": "2026-05-04T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:fail:1",
        "action_key": "fix_channel",
    }
    base.update(overrides)
    enrich_decision_knowledge_metadata_v1(base, store_slug="demo", recovery_key="rk:fail")
    return base


def _compose_home(decisions: list[dict], insights: list[dict] | None = None):
    brief = compose_merchant_daily_brief_v2(
        decision_bundles=[{"decisions": decisions}],
        kl_insights=insights or [],
    )
    return compose_merchant_home_experience_v1(
        daily_brief=brief,
        kl_insights=insights or [],
        brief_date="2026-05-04",
        nav_metadata={"knowledge_cart_count": 5},
    )


class RecoveryJourneyMapperTests(unittest.TestCase):
    def test_obtain_contact_maps_to_canonical_intervention_stage(self) -> None:
        journey = build_recovery_journey_for_attention_v1(
            operational_decision_key="decision:obtain_contact",
            case_count=5,
        )
        assert journey is not None
        self.assertTrue(is_recovery_journey_complete_v1(journey))
        self.assertEqual(journey["recovery_stage_key"], STATE_NEEDS_INTERVENTION)
        self.assertIn(LABEL_WAITING_CONTACT_COMPLETION_AR, journey["recovery_stage_ar"])
        self.assertIn("واتساب", journey["recovery_blocker_ar"])
        self.assertTrue(journey["recovery_merchant_required"])

    def test_fix_channel_uses_whatsapp_channel(self) -> None:
        journey = build_recovery_journey_for_attention_v1(
            operational_decision_key="decision:fix_channel",
        )
        assert journey is not None
        self.assertEqual(journey["recovery_channel_ar"], "واتساب")
        self.assertIn("واتساب", journey["recovery_blocker_ar"])


class Pib3HomeRecoveryJourneyTests(unittest.TestCase):
    def test_attention_lead_exposes_full_journey_contract(self) -> None:
        decisions = [_obtain_contact(merge_key=f"cart:c:{i}") for i in range(5)]
        insights = [
            {
                "insight_key": "store_health_overview",
                "category": "traffic",
                "severity": "warning",
                "title_ar": "صحة بيانات المتجر",
                "message_ar": "معظم السلات بدون رقم عميل.",
                "evidence": {},
                "confidence": "low",
                "data_window": {"days": 7},
                "sample_size": 5,
                "source_tables": ["abandoned_carts"],
                "recommended_action_ar": "",
                "evidence_id": "store_activity",
            }
        ]
        enrich_kl_insight_knowledge_metadata_v1(
            insights[0], store_slug="demo", window_days=7
        )
        home = _compose_home(decisions, insights)
        lead = home["attention_today"]["items"][0]
        for key in (
            "recovery_stage_key",
            "recovery_stage_ar",
            "recovery_channel_ar",
            "recovery_stage_why_ar",
            "recovery_blocker_ar",
            "recovery_next_platform_ar",
            "recovery_next_merchant_ar",
            "recovery_completion_condition_ar",
        ):
            self.assertTrue(str(lead.get(key) or "").strip(), msg=f"missing {key}")
        self.assertTrue(lead.get("recovery_journey_complete"))
        self.assertEqual(lead.get("recovery_stage_key"), STATE_NEEDS_INTERVENTION)
        self.assertTrue(lead.get("recovery_merchant_required"))

    def test_waiting_state_is_explained_not_silent(self) -> None:
        home = _compose_home([_obtain_contact()])
        lead = home["attention_today"]["items"][0]
        self.assertTrue(lead.get("recovery_blocker_ar"))
        self.assertNotEqual(lead.get("recovery_blocker_ar"), "—")
        self.assertIn("رقم", lead["recovery_blocker_ar"])

    def test_merchant_intervention_justified(self) -> None:
        home = _compose_home([_obtain_contact()])
        lead = home["attention_today"]["items"][0]
        self.assertTrue(lead.get("recovery_merchant_required"))
        self.assertTrue(lead.get("recovery_next_merchant_ar"))
        self.assertNotIn("لا يلزم إجراء منك الآن", lead["recovery_next_merchant_ar"])

    def test_fix_channel_journey_on_home(self) -> None:
        home = _compose_home([_fix_channel()])
        lead = home["attention_today"]["items"][0]
        self.assertEqual(lead.get("operational_decision_key"), "decision:fix_channel")
        self.assertEqual(lead.get("recovery_channel_ar"), "واتساب")
        self.assertTrue(lead.get("recovery_journey_complete"))

    def test_ui_renders_journey_block(self) -> None:
        for token in (
            "renderRecoveryJourney",
            "ma-ecc-journey",
            "مسار الاسترجاع",
            "recovery_stage_ar",
            "recovery_blocker_ar",
            "recovery_next_platform_ar",
            "يكتمل عندما:",
        ):
            self.assertIn(token, _JS)

    def test_observability_flag(self) -> None:
        home = _compose_home([_obtain_contact()])
        self.assertTrue(
            home["observability"].get("pib3_recovery_journey_explainability")
        )


if __name__ == "__main__":
    unittest.main()
