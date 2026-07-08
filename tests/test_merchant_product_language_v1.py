# -*- coding: utf-8 -*-
"""Merchant Product Language V1 — foundation certification tests."""
from __future__ import annotations

import re
import unittest

from services.merchant_product_language_v1 import (
    AUTHORITY,
    LANGUAGE_VERSION,
    VALID_PAGE_KEYS,
    compose_merchant_product_language_v1,
    compose_page_narrative_v1,
    get_page_intent_v1,
    list_page_intents_v1,
    validate_page_narrative_v1,
)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_FORBIDDEN = re.compile(
    r"\b(lifecycle_state|group_key|reason_tag|snapshot|bucket|decision_key)\b",
    re.I,
)


class MerchantProductLanguageV1Tests(unittest.TestCase):
    def test_page_intent_registry_covers_all_pages(self) -> None:
        intents = list_page_intents_v1()
        self.assertEqual(len(intents), 7)
        keys = {item["page_key"] for item in intents}
        self.assertEqual(keys, set(VALID_PAGE_KEYS))

    def test_each_page_has_primary_question(self) -> None:
        for key in VALID_PAGE_KEYS:
            intent = get_page_intent_v1(key)
            self.assertEqual(intent["page_key"], key)
            self.assertTrue(_ARABIC_RE.search(intent["primary_question_ar"]))

    def test_compose_carts_narrative_attention(self) -> None:
        narrative = compose_page_narrative_v1(
            "carts",
            {
                "monitored_count": 47,
                "attention_count": 2,
                "automatic_count": 45,
                "cartflow_action_key": "monitoring_replies",
            },
        )
        self.assertEqual(narrative["version"], LANGUAGE_VERSION)
        self.assertEqual(narrative["authority"], AUTHORITY)
        sections = narrative["sections"]
        self.assertIn("سلتان تستحقان انتباهك", sections["headline"]["text_ar"])
        evidence_text = " ".join(sections["evidence"]["lines_ar"])
        self.assertIn("47", evidence_text)
        self.assertIn("2", evidence_text)
        self.assertIn("45", evidence_text)
        self.assertIn("يراقب ردود العملاء", sections["cartflow_action"]["text_ar"])
        self.assertEqual(validate_page_narrative_v1(narrative), [])

    def test_compose_carts_narrative_no_attention(self) -> None:
        narrative = compose_page_narrative_v1(
            "carts",
            {"monitored_count": 10, "attention_count": 0, "automatic_count": 10},
        )
        self.assertIn("لا يلزم إجراء", narrative["sections"]["headline"]["text_ar"])
        self.assertEqual(validate_page_narrative_v1(narrative), [])

    def test_compose_whatsapp_ready_vs_not_ready(self) -> None:
        ready = compose_page_narrative_v1("whatsapp", {"channel_ready": True})
        not_ready = compose_page_narrative_v1("whatsapp", {"channel_ready": False})
        self.assertIn("طبيعي", ready["sections"]["headline"]["text_ar"])
        self.assertIn("إعداد", not_ready["sections"]["headline"]["text_ar"])
        self.assertEqual(validate_page_narrative_v1(ready), [])
        self.assertEqual(validate_page_narrative_v1(not_ready), [])

    def test_details_section_not_composed(self) -> None:
        narrative = compose_page_narrative_v1("home", {"attention_count": 0})
        self.assertNotIn("details", narrative["sections"])
        self.assertTrue(narrative["observability"]["details_deferred"])

    def test_batch_compose_multiple_pages(self) -> None:
        payload = compose_merchant_product_language_v1(
            {
                "home": {"attention_count": 1},
                "plans": {"plan_label_ar": "الخطة الأساسية"},
            }
        )
        self.assertEqual(payload["version"], LANGUAGE_VERSION)
        self.assertIn("home", payload["narratives"])
        self.assertIn("plans", payload["narratives"])
        self.assertEqual(len(payload["page_intents"]), 7)

    def test_validate_rejects_forbidden_tokens(self) -> None:
        bad = compose_page_narrative_v1("carts", {"attention_count": 0})
        bad["sections"]["headline"]["text_ar"] = "group_key visible"
        violations = validate_page_narrative_v1(bad)
        self.assertTrue(any("forbidden" in v for v in violations))

    def test_source_refs_present_on_headline(self) -> None:
        narrative = compose_page_narrative_v1("carts", {"attention_count": 3})
        refs = narrative["sections"]["headline"]["source_refs"]
        self.assertIn("attention_count", refs)

    def test_unknown_page_raises(self) -> None:
        with self.assertRaises(ValueError):
            compose_page_narrative_v1("unknown_page", {})


if __name__ == "__main__":
    unittest.main()
