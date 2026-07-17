# -*- coding: utf-8 -*-
"""PIB-1 — Home Truth Alignment acceptance tests (MV-1 evidence shape)."""
from __future__ import annotations

import unittest

from services.knowledge_producer_metadata_v1 import (
    enrich_decision_knowledge_metadata_v1,
    enrich_kl_insight_knowledge_metadata_v1,
)
from services.merchant_daily_brief_composer_v2 import compose_merchant_daily_brief_v2
from services.merchant_decision_layer_v1 import (
    CLASS_OBSERVATION,
    LIFECYCLE_PUBLISHED,
    VERIFY_PASSED,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

_PLACEHOLDER_WHY = "ملخص Knowledge Layer للفترة المحددة"


def _obtain_contact_observation(**overrides: object) -> dict:
    """MV-1 shape: obtain_contact capped to observation → Brief achievement."""
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
            "if_omitted_ar": "يستمر الحظر",
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
        base,
        store_slug="demo",
        recovery_key="rk:contact",
    )
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
        "category": "traffic" if "traffic" in insight_key or "store" in insight_key else "hesitation",
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


def _mv1_kl_insights() -> list[dict]:
    return [
        _kl_insight(
            insight_key="traffic_visitor_unavailable",
            title_ar="بيانات الزوار غير متوفرة",
            message_ar="CartFlow لا يرى عدد زوار المتجر حالياً.",
            confidence="insufficient",
        ),
        _kl_insight(
            insight_key="hesitation_insufficient_sample",
            title_ar="بيانات التردد محدودة",
            message_ar="عدد أسباب التردد المسجّلة (0) أقل من الحد الأدنى.",
            confidence="insufficient",
        ),
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


class Pib1HomeTruthAlignmentTests(unittest.TestCase):
    def _compose_mv1_home(self):
        decisions = [_obtain_contact_observation(merge_key=f"cart:contact:{i}") for i in range(5)]
        insights = _mv1_kl_insights()
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
            nav_metadata={"knowledge_cart_count": 5, "active_carts": 0, "waiting_send": 0},
        )

    def test_c01_attention_includes_contact_wait(self) -> None:
        home = self._compose_mv1_home()
        attention = home["attention_today"]
        self.assertGreaterEqual(attention["count"], 1)
        blob = " ".join(
            f"{i.get('headline_ar')} {i.get('why_ar')} {i.get('action_ar')}"
            for i in attention["items"]
        )
        self.assertTrue(
            "رقم" in blob or "obtain_contact" in blob or "تواصل" in blob,
            msg=f"contact wait missing from attention: {attention['items']}",
        )

    def test_c07_attention_has_next_step(self) -> None:
        home = self._compose_mv1_home()
        lead = home["attention_today"]["items"][0]
        self.assertEqual(lead.get("fact_key"), "fact:obtain_contact")
        self.assertTrue(lead.get("action_present"))
        self.assertTrue(lead.get("action_ar"))
        self.assertIn("رقم", lead["action_ar"])

    def test_c02_understanding_inherits_knowledge(self) -> None:
        home = self._compose_mv1_home()
        items = home["store_understanding"]["items"]
        self.assertGreaterEqual(len(items), 1)
        blob = " ".join(
            f"{i.get('title_ar')} {i.get('observation_ar')}" for i in items
        )
        self.assertTrue(
            "5" in blob or "بدون رقم" in blob or "اتجاه" in blob or "up" in blob.lower(),
            msg=f"understanding missing Knowledge numbers: {items}",
        )

    def test_no_empty_understanding_when_knowledge_has_evidence(self) -> None:
        home = self._compose_mv1_home()
        self.assertGreaterEqual(len(home["store_understanding"]["items"]), 1)

    def test_c03_one_fact_one_card_no_title_twins_in_while_away(self) -> None:
        home = self._compose_mv1_home()
        titles = [i.get("headline_ar") for i in home["while_away"]["items"]]
        self.assertEqual(len(titles), len(set(titles)), msg=f"duplicate titles: {titles}")

    def test_c04_no_placeholder_detail(self) -> None:
        home = self._compose_mv1_home()
        for section in ("while_away", "attention_today", "store_understanding"):
            for item in home[section]["items"]:
                details = [
                    item.get("detail_ar"),
                    item.get("why_ar"),
                    item.get("observation_ar"),
                ]
                for detail in details:
                    if detail is None or detail == "":
                        continue
                    self.assertNotEqual(detail, _PLACEHOLDER_WHY)
                    self.assertNotEqual(detail, "—")

    def test_c05_badge_equals_knowledge_cart_count(self) -> None:
        home = self._compose_mv1_home()
        badge = next(
            i for i in home["quick_nav"]["items"] if i["id"] == "active_carts"
        )
        self.assertEqual(badge["badge_count"], 5)

    def test_c06_greeting_date_matches_brief_date(self) -> None:
        home = self._compose_mv1_home()
        self.assertEqual(home["brief_date"], "2026-05-04")
        self.assertEqual(home["greeting"]["date_ar"], "2026-05-04")

    def test_c10_limits_not_while_away_wins(self) -> None:
        home = self._compose_mv1_home()
        away_blob = " ".join(
            f"{i.get('headline_ar')} {i.get('aggregation_key')}"
            for i in home["while_away"]["items"]
        )
        self.assertNotIn("insufficient", away_blob.lower())
        self.assertNotIn("unavailable", away_blob.lower())

    def test_contact_wait_not_in_while_away(self) -> None:
        home = self._compose_mv1_home()
        away_blob = " ".join(
            f"{i.get('headline_ar')} {i.get('aggregation_key')}"
            for i in home["while_away"]["items"]
        )
        self.assertNotIn("obtain_contact", away_blob.lower())
        self.assertNotIn("بانتظار رقم", away_blob)

    def test_cross_section_fact_keys_do_not_overlap(self) -> None:
        home = self._compose_mv1_home()
        keys = []
        for section in ("while_away", "attention_today", "store_understanding"):
            for item in home[section]["items"]:
                keys.append(item.get("fact_key") or item.get("aggregation_key"))
        self.assertEqual(len(keys), len(set(keys)), msg=f"overlapping facts: {keys}")


if __name__ == "__main__":
    unittest.main()
