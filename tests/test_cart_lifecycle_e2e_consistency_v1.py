# -*- coding: utf-8 -*-
"""Cart Lifecycle End-to-End Consistency — root-cause regression tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from services.customer_lifecycle_states_v1 import (
    LABEL_WAITING_CONTACT_COMPLETION_AR,
    LABEL_SCHEDULE_NOT_MATERIALIZED_AR,
    PROVIDER_CONFIRMED_SENT_LOG,
    SENT_LOG,
    STATE_NEEDS_INTERVENTION,
    STATE_WAITING_CUSTOMER_REPLY,
    STATE_WAITING_FIRST_SEND,
    UI_FILTER_SENT,
    UI_FILTER_WAITING,
    classify_customer_lifecycle_state_v1,
    lifecycle_state_to_filter_bucket,
    merchant_filter_bucket_for_lifecycle,
)
from services.merchant_intelligence_v1 import (
    GROUP_AWAITING_SEND,
    GROUP_WAITING_REPLY,
    assign_cart_intelligence_group,
)
from services.merchant_value_composition_v1 import (
    STORY_AWAITING_SEND,
    build_merchant_value_stories_v1,
)

_ROOT = Path(__file__).resolve().parents[1]
_FLOWS = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_flows.js").read_text(
    encoding="utf-8"
)
_UI = (_ROOT / "static/cartflow_widget_runtime/cartflow_widget_ui.js").read_text(
    encoding="utf-8"
)
_CARTFLOW = (_ROOT / "routes/cartflow.py").read_text(encoding="utf-8")


class CartLifecycleE2EConsistencyTests(unittest.TestCase):
    def test_reason_persist_before_advance(self) -> None:
        self.assertIn("persistThenAdvance", _FLOWS)
        self.assertIn("reason_save_in_flight", _FLOWS)
        idx = _FLOWS.index("function openReasonPath")
        block = _FLOWS[idx : idx + 5000]
        self.assertLess(
            block.index("Cf.Api.postReason(payloadCopy)"),
            block.index("showContinuation(rk, subCat)"),
        )
        self.assertIn("failReasonPersist", block)

    def test_double_click_guarded(self) -> None:
        self.assertIn('data-cf-reason-key', _UI)
        self.assertIn('if (b.getAttribute("disabled") === "true") return', _UI)
        self.assertIn("setReasonButtonsDisabled", _FLOWS)
        self.assertIn('why: "in_flight"', _FLOWS)

    def test_invalid_phone_rejected(self) -> None:
        self.assertIn(
            "Provided but invalid — never silently drop customer phone input.",
            _CARTFLOW,
        )

    def test_phone_clears_waiting_contact_despite_historic_block_log(self) -> None:
        lc = classify_customer_lifecycle_state_v1(
            recovery_key="demo:e2e-phone-clear",
            has_phone=True,
            log_statuses=frozenset({"schedule_blocked_missing_phone"}),
            coarse="pending",
            phase_key="pending_send",
            schedule_prefetched=True,
            effective_delay_seconds_prefetched=None,
        )
        self.assertNotEqual(lc.label_ar, LABEL_WAITING_CONTACT_COMPLETION_AR)

    def test_no_phone_keeps_waiting_contact(self) -> None:
        lc = classify_customer_lifecycle_state_v1(
            recovery_key="demo:e2e-no-phone",
            has_phone=False,
            log_statuses=frozenset({"schedule_blocked_missing_phone"}),
            coarse="pending",
            phase_key="pending_send",
            schedule_prefetched=True,
            effective_delay_seconds_prefetched=None,
        )
        self.assertEqual(lc.state_key, STATE_NEEDS_INTERVENTION)
        self.assertEqual(lc.label_ar, LABEL_WAITING_CONTACT_COMPLETION_AR)

    def test_mock_sent_not_merchant_sent_filter(self) -> None:
        self.assertIn("mock_sent", SENT_LOG)
        self.assertEqual(PROVIDER_CONFIRMED_SENT_LOG, frozenset({"sent_real"}))
        self.assertEqual(
            merchant_filter_bucket_for_lifecycle(
                STATE_WAITING_CUSTOMER_REPLY,
                log_statuses=frozenset({"mock_sent"}),
            ),
            UI_FILTER_WAITING,
        )
        self.assertEqual(
            merchant_filter_bucket_for_lifecycle(
                STATE_WAITING_CUSTOMER_REPLY,
                log_statuses=frozenset({"sent_real"}),
            ),
            UI_FILTER_SENT,
        )

    def test_waiting_first_send_filter_is_waiting(self) -> None:
        self.assertEqual(
            lifecycle_state_to_filter_bucket(STATE_WAITING_FIRST_SEND),
            UI_FILTER_WAITING,
        )

    def test_waiting_first_send_mi_group(self) -> None:
        row = {
            "recovery_key": "demo:cf_cart_wait",
            "customer_lifecycle_state": STATE_WAITING_FIRST_SEND,
            "merchant_cart_primary_bucket": "waiting",
            "merchant_has_customer_phone": True,
            "customer_lifecycle_merchant_needed_ar": "لا",
        }
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_AWAITING_SEND)

    def test_awaiting_send_story_has_row_keys(self) -> None:
        row = {
            "recovery_key": "demo:cf_cart_story",
            "customer_lifecycle_state": STATE_WAITING_FIRST_SEND,
            "merchant_cart_primary_bucket": "waiting",
            "merchant_has_customer_phone": True,
            "customer_lifecycle_merchant_needed_ar": "لا",
            "customer_lifecycle_system_did_ar": "جدولنا المتابعة.",
        }
        store = {
            "groups": [
                {
                    "group_id": GROUP_AWAITING_SEND,
                    "affected_carts": 1,
                    "affected_cart_keys": ["demo:cf_cart_story"],
                    "confidence": "medium",
                    "priority": 0,
                    "creation_reason": "awaiting_first_provider_send",
                    "eligible_surfaces": ["carts"],
                }
            ],
            "recommendations": [],
            "memory": [],
        }
        stories = build_merchant_value_stories_v1([row], store)
        types = [s.get("story_type") for s in (stories.get("stories") or [])]
        self.assertIn(STORY_AWAITING_SEND, types)
        story = next(
            s for s in stories["stories"] if s["story_type"] == STORY_AWAITING_SEND
        )
        self.assertIn("demo:cf_cart_story", story.get("affected_cart_keys") or [])
        # Must not claim a provider message was received.
        self.assertNotIn("تلقى", story.get("headline_ar") or "")

    def test_real_sent_still_waiting_reply_group(self) -> None:
        row = {
            "recovery_key": "demo:cf_cart_sent",
            "customer_lifecycle_state": STATE_WAITING_CUSTOMER_REPLY,
            "merchant_cart_primary_bucket": "sent",
            "merchant_has_customer_phone": True,
            "customer_lifecycle_merchant_needed_ar": "لا",
        }
        assignment = assign_cart_intelligence_group(row)
        self.assertEqual((assignment or {}).get("group_id"), GROUP_WAITING_REPLY)

    def test_phone_save_awaits_before_close(self) -> None:
        idx = _FLOWS.index("function handleThanksAfterReason")
        block = _FLOWS[idx : idx + 2800]
        self.assertIn("Cf.Phone.postReasonMerged", block)
        self.assertIn("تعذّر حفظ رقم الجوال", block)
        self.assertIn("gracefulCloseWidget()", block)

    def test_schedule_not_materialized_label_when_phone_present(self) -> None:
        lc = classify_customer_lifecycle_state_v1(
            recovery_key="demo:e2e-sched",
            has_phone=True,
            log_statuses=frozenset(),
            coarse="pending",
            phase_key="pending_send",
            schedule_prefetched=True,
            effective_delay_seconds_prefetched=None,
        )
        self.assertEqual(lc.state_key, STATE_NEEDS_INTERVENTION)
        self.assertEqual(lc.label_ar, LABEL_SCHEDULE_NOT_MATERIALIZED_AR)


if __name__ == "__main__":
    unittest.main()
