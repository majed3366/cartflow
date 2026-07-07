# -*- coding: utf-8 -*-
"""Merchant Value Composition v1 — certification tests."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from services.merchant_cart_fact_v1 import attach_merchant_cart_fact_v1
from services.merchant_decision_layer_v1 import attach_merchant_decisions_v1
from services.merchant_explanation_v1 import attach_merchant_explanation_v1
from services.merchant_intelligence_v1 import (
    GROUP_COMPLETED,
    GROUP_NEEDS_MERCHANT,
    GROUP_RETURNED,
    GROUP_WAITING_REPLY,
    attach_merchant_intelligence_v1,
    build_store_merchant_intelligence_v1,
    ensure_normal_carts_merchant_intelligence_store_v1,
)
from services.merchant_proof_surface_v1 import attach_merchant_proof_surface_v1
from services.merchant_value_composition_v1 import (
    AUTHORITY,
    STORY_NEEDS_MERCHANT,
    STORY_PRICE_HESITATION,
    STORY_RECOVERED_PURCHASE,
    STORY_RETURNED_WITHOUT_PURCHASE,
    STORY_WAITING_REPLY,
    VALUE_VERSION,
    build_merchant_value_stories_v1,
    ensure_normal_carts_merchant_value_stories_v1,
    validate_merchant_value_story_v1,
)

_ROOT = Path(__file__).resolve().parent.parent
_MI_CARTS_JS = (_ROOT / "static" / "merchant_intelligence_carts_v1.js").read_text(
    encoding="utf-8"
)
_LAZY_JS = (_ROOT / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8")

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_ENGLISH_KEY_RE = re.compile(
    r"\b(needs_merchant|waiting_reply|reason_tag|group_key|lifecycle_state|required_action)\b",
    re.I,
)
_ROI_RE = re.compile(r"(استعدنا|حققنا لك|revenue|ROI)", re.I)


def _base_row(**overrides: object) -> dict:
    row = {
        "recovery_key": "store:cart:1",
        "store_slug": "demo",
        "has_phone": True,
        "merchant_cart_primary_bucket": "sent",
        "merchant_cart_bucket": "sent",
        "customer_lifecycle_state": "waiting_customer_reply",
        "customer_lifecycle_merchant_needed_ar": "لا",
        "merchant_intervention_executable": True,
        "cart_value": 1240.0,
        "reason_tag": "",
    }
    row.update(overrides)
    return row


def _attach_row(row: dict, *, action_key: str = "contact_customer") -> None:
    attach_merchant_proof_surface_v1(
        row,
        recovery_key=str(row.get("recovery_key") or ""),
        customer_lifecycle_state=str(row.get("customer_lifecycle_state") or ""),
        customer_lifecycle_what_happened_ar="تحتاج تدخل",
        log_statuses=[],
    )
    row["merchant_decision_key"] = action_key
    attach_merchant_decisions_v1(row)
    attach_merchant_explanation_v1(row)
    attach_merchant_intelligence_v1(row)


class MerchantValueCompositionV1Tests(unittest.TestCase):
    def test_stories_produced_from_mi_groups(self) -> None:
        rows = [
            _base_row(
                recovery_key="a",
                customer_lifecycle_merchant_needed_ar="نعم",
            ),
            _base_row(
                recovery_key="b",
                customer_lifecycle_merchant_needed_ar="نعم",
            ),
        ]
        for r in rows:
            _attach_row(r)
        store = build_store_merchant_intelligence_v1(rows)
        bundle = build_merchant_value_stories_v1(rows, store)
        self.assertEqual(bundle.get("version"), VALUE_VERSION)
        self.assertEqual(bundle.get("authority"), AUTHORITY)
        stories = bundle.get("stories") or []
        types = {s.get("story_type") for s in stories}
        self.assertIn(STORY_NEEDS_MERCHANT, types)
        story = next(s for s in stories if s.get("story_type") == STORY_NEEDS_MERCHANT)
        self.assertTrue(story.get("source_group_ids"))
        self.assertGreaterEqual(len(story.get("affected_cart_keys") or []), 1)

    def test_price_hesitation_story_from_pattern_group(self) -> None:
        rows = [
            _base_row(recovery_key=f"p{i}", reason_tag="price")
            for i in range(3)
        ]
        for r in rows:
            _attach_row(r)
        store = build_store_merchant_intelligence_v1(rows)
        bundle = build_merchant_value_stories_v1(rows, store)
        types = {s.get("story_type") for s in bundle.get("stories") or []}
        self.assertIn(STORY_PRICE_HESITATION, types)
        story = next(
            s for s in bundle["stories"] if s.get("story_type") == STORY_PRICE_HESITATION
        )
        self.assertIn("السعر", story.get("headline_ar") or "")
        self.assertTrue(story.get("evidence_ids"))

    def test_no_story_without_evidence_or_carts(self) -> None:
        store = {"groups": [], "recommendations": [], "memory": []}
        bundle = build_merchant_value_stories_v1([], store)
        self.assertEqual(bundle.get("stories"), [])

    def test_arabic_only_merchant_fields(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        story = build_merchant_value_stories_v1([row], store)["stories"][0]
        for field in (
            "title_ar",
            "headline_ar",
            "merchant_meaning_ar",
            "cartflow_action_ar",
            "recommendation_ar",
        ):
            val = str(story.get(field) or "")
            self.assertTrue(_ARABIC_RE.search(val), msg=f"missing Arabic in {field}")
            self.assertIsNone(_ENGLISH_KEY_RE.search(val), msg=f"internal key in {field}")

    def test_roi_claims_blocked_without_attribution(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_row(row)
        row["merchant_explanation_v1"]["system_did_ar"] = "استعدنا 500 ريال من هذه السلة"
        store = build_store_merchant_intelligence_v1([row])
        story = build_merchant_value_stories_v1([row], store)["stories"][0]
        action = str(story.get("cartflow_action_ar") or "")
        self.assertIsNone(_ROI_RE.search(action))

    def test_returned_without_purchase_story_safe(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket="return_to_site",
            customer_lifecycle_state="return_to_site",
        )
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        bundle = build_merchant_value_stories_v1([row], store)
        story = next(
            (s for s in bundle.get("stories") or [] if s.get("story_type") == STORY_RETURNED_WITHOUT_PURCHASE),
            None,
        )
        self.assertIsNotNone(story)
        assert story is not None
        self.assertIsNone(_ROI_RE.search(str(story.get("headline_ar") or "")))
        self.assertFalse(story.get("action_required"))

    def test_recovered_purchase_requires_purchase_evidence(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket="recovered",
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="purchased",
        )
        _attach_row(row)
        attach_merchant_cart_fact_v1(
            row,
            purchase_truth=True,
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="purchased",
        )
        store = build_store_merchant_intelligence_v1([row])
        bundle = build_merchant_value_stories_v1([row], store)
        story = next(
            (s for s in bundle.get("stories") or [] if s.get("story_type") == STORY_RECOVERED_PURCHASE),
            None,
        )
        self.assertIsNotNone(story)
        assert story is not None
        self.assertIn("الشراء", story.get("headline_ar") or "")

    def test_recovered_story_absent_without_purchase_evidence(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket="recovered",
            customer_lifecycle_state="completed",
            customer_lifecycle_completed_variant="purchased",
        )
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        bundle = build_merchant_value_stories_v1([row], store)
        types = {s.get("story_type") for s in bundle.get("stories") or []}
        self.assertNotIn(STORY_RECOVERED_PURCHASE, types)

    def test_waiting_reply_story(self) -> None:
        row = _base_row(
            merchant_cart_primary_bucket="sent",
            customer_lifecycle_merchant_needed_ar="لا",
        )
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        bundle = build_merchant_value_stories_v1([row], store)
        types = {s.get("story_type") for s in bundle.get("stories") or []}
        self.assertIn(STORY_WAITING_REPLY, types)

    def test_ensure_normal_carts_transport(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_row(row)
        body = {"merchant_carts_page_rows": [row]}
        ensure_normal_carts_merchant_value_stories_v1(body)
        bundle = body.get("merchant_value_stories_v1")
        self.assertIsInstance(bundle, dict)
        assert bundle is not None
        self.assertTrue(bundle.get("stories"))
        self.assertIn("merchant_intelligence_store_v1", body)

    def test_validate_story_contract(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        story = build_merchant_value_stories_v1([row], store)["stories"][0]
        self.assertEqual(validate_merchant_value_story_v1(story), [])

    def test_carts_js_consumes_value_stories(self) -> None:
        self.assertIn("merchant_value_stories_v1", _MI_CARTS_JS)
        self.assertIn("renderStories", _MI_CARTS_JS)
        self.assertIn("hasValueStories", _MI_CARTS_JS)
        self.assertIn("story.headline_ar", _MI_CARTS_JS)
        block = _LAZY_JS[
            _LAZY_JS.index("function renderMiCartsV1Workspace")
            : _LAZY_JS.index("function renderPeV2CartsQueue")
        ]
        self.assertIn("hasValueStories", block)
        self.assertIn("renderStories", block)
        self.assertIn("merchant_value_stories_v1", block)

    def test_diagnostics_internal_not_in_merchant_fields(self) -> None:
        row = _base_row(customer_lifecycle_merchant_needed_ar="نعم")
        _attach_row(row)
        store = build_store_merchant_intelligence_v1([row])
        story = build_merchant_value_stories_v1([row], store)["stories"][0]
        for field in ("title_ar", "headline_ar", "merchant_meaning_ar", "cartflow_action_ar"):
            val = str(story.get(field) or "").lower()
            self.assertNotIn("diagnostics", val)
            self.assertNotIn("composition_reason", val)


if __name__ == "__main__":
    unittest.main()
