# -*- coding: utf-8 -*-
"""PIB-2 — Attention Decision Surface acceptance tests."""
from __future__ import annotations

import unittest
from pathlib import Path

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

_ROOT = Path(__file__).resolve().parent.parent
_JS = (_ROOT / "static" / "merchant_dashboard_home_v1.js").read_text(encoding="utf-8")


def _obtain_contact_observation(**overrides: object) -> dict:
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


def _contact_customer(**overrides: object) -> dict:
    base = {
        "decision_id": "decision_contact_customer",
        "decision_class": CLASS_NEEDS_ATTENTION,
        "evidence_ids": ["customer_journey"],
        "proof_sources": ["rk:2"],
        "confidence": "medium",
        "commercial_goal": "recover_revenue",
        "merchant_action": "execute",
        "priority": 300,
        "expiration": {"ttl_hours": 72},
        "suppression_state": "none",
        "verification_status": VERIFY_PASSED,
        "decision_explanation": {
            "rationale_ar": "العميل لم يكمل الشراء",
            "why_now_ar": "السلة تحتاج تدخلاً بعد توفر بيانات التواصل",
            "if_omitted_ar": "قد تفوت فرصة استرجاع يدوية",
        },
        "decision_timestamp": "2026-05-04T12:00:00+00:00",
        "lifecycle_state": LIFECYCLE_PUBLISHED,
        "owner": "merchant_decision_layer_v1",
        "verification_method": "test",
        "merge_key": "cart:2",
        "action_key": "contact_customer",
    }
    base.update(overrides)
    enrich_decision_knowledge_metadata_v1(base, store_slug="demo", recovery_key="rk:2")
    return base


def _kl_insight(
    *,
    insight_key: str,
    title_ar: str,
    message_ar: str,
    confidence: str,
    severity: str = "info",
    evidence: dict | None = None,
) -> dict:
    base = {
        "insight_key": insight_key,
        "category": "traffic",
        "severity": severity,
        "title_ar": title_ar,
        "message_ar": message_ar,
        "evidence": evidence or {},
        "confidence": confidence,
        "data_window": {"days": 7},
        "sample_size": 5,
        "source_tables": ["abandoned_carts"],
        "recommended_action_ar": "",
        "evidence_id": "store_activity",
        "evidence_label_ar": "نشاط المتجر",
    }
    enrich_kl_insight_knowledge_metadata_v1(base, store_slug="demo", window_days=7)
    return base


def _mv1_home():
    decisions = [_obtain_contact_observation(merge_key=f"cart:contact:{i}") for i in range(5)]
    insights = [
        _kl_insight(
            insight_key="store_health_overview",
            title_ar="صحة بيانات المتجر",
            message_ar="معظم السلات بدون رقم عميل.",
            confidence="low",
            severity="warning",
            evidence={"signals": ["معظم السلات بدون رقم عميل"]},
        ),
        _kl_insight(
            insight_key="traffic_cart_demand_trend",
            title_ar="اتجاه الطلب (سلات مهجورة)",
            message_ar="سلات الفترة الحالية: 5؛ الفترة السابقة: 0 (اتجاه: up).",
            confidence="high",
            evidence={"current_carts": 5, "previous_carts": 0, "direction": "up"},
        ),
    ]
    brief = compose_merchant_daily_brief_v2(
        decision_bundles=[{"decisions": decisions}],
        kl_insights=insights,
    )
    return compose_merchant_home_experience_v1(
        merchant_name_ar="متجرك",
        date_ar="",
        brief_date="2026-05-04",
        daily_brief=brief,
        kl_insights=insights,
        nav_metadata={"knowledge_cart_count": 5, "active_carts": 0},
    )


class Pib2AttentionDecisionSurfaceTests(unittest.TestCase):
    def test_attention_item_has_full_decision_contract(self) -> None:
        home = _mv1_home()
        items = home["attention_today"]["items"]
        self.assertGreaterEqual(len(items), 1)
        lead = items[0]
        for key in (
            "action_ar",
            "why_ar",
            "evidence_ar",
            "operational_state_ar",
            "expected_outcome_ar",
        ):
            self.assertTrue(_norm(lead.get(key)), msg=f"missing {key}: {lead}")
            self.assertNotEqual(lead.get(key), "—")
            self.assertNotIn("ملخص Knowledge Layer", str(lead.get(key)))

    def test_merchant_can_answer_if_ignored(self) -> None:
        lead = _mv1_home()["attention_today"]["items"][0]
        self.assertTrue(lead.get("if_ignored_ar"))
        self.assertIn("استرجاع", lead["if_ignored_ar"])

    def test_one_operational_decision_for_phone_gap(self) -> None:
        items = _mv1_home()["attention_today"]["items"]
        keys = [i.get("operational_decision_key") for i in items]
        self.assertEqual(keys.count("decision:obtain_contact"), 1)
        self.assertEqual(len(keys), len(set(keys)))

    def test_blocked_work_precedes_immediate_action(self) -> None:
        decisions = [
            _contact_customer(merge_key="cart:a"),
            _obtain_contact_observation(merge_key="cart:b"),
        ]
        brief = compose_merchant_daily_brief_v2(
            decision_bundles=[{"decisions": decisions}],
        )
        home = compose_merchant_home_experience_v1(daily_brief=brief)
        items = home["attention_today"]["items"]
        self.assertGreaterEqual(len(items), 1)
        self.assertEqual(items[0].get("operational_decision_key"), "decision:obtain_contact")
        self.assertEqual(items[0].get("priority_class"), 0)
        if len(items) > 1:
            self.assertGreaterEqual(int(items[1].get("priority_class") or 0), 0)
            self.assertLessEqual(
                int(items[0].get("priority_class") or 0),
                int(items[1].get("priority_class") or 0),
            )

    def test_queue_positions_are_ordered(self) -> None:
        items = _mv1_home()["attention_today"]["items"]
        positions = [i.get("queue_position") for i in items]
        self.assertEqual(positions, list(range(1, len(items) + 1)))

    def test_attention_is_decision_surface_not_list_copy(self) -> None:
        home = _mv1_home()
        att = home["attention_today"]
        self.assertTrue(att.get("decision_surface"))
        # Natural merchant language (Knowledge Redistribution V1) — not engineering queue copy.
        self.assertIn("قرار", att.get("lead_ar") or "")
        self.assertNotIn("طابور", att.get("lead_ar") or "")

    def test_ui_renders_decision_contract_fields(self) -> None:
        # Attention answers: why now, why important, if ignored, action.
        for token in (
            "expected_outcome_ar",
            "if_ignored_ar",
            "operational_decision_key",
            "لماذا الآن:",
            "لماذا مهم:",
            "إذا تجاهلت:",
        ):
            self.assertIn(token, _JS)

    def test_observability_flag(self) -> None:
        home = _mv1_home()
        self.assertTrue(home["observability"].get("pib2_attention_decision_surface"))


def _norm(value: object) -> str:
    return str(value or "").strip()


if __name__ == "__main__":
    unittest.main()
