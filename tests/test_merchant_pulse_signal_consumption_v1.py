# -*- coding: utf-8 -*-
"""Merchant Pulse consumes Commerce Signals for Recovery/Purchase what-happened only."""
from __future__ import annotations

import os
import unittest

from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_BLOCKED,
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_RECOVERY_PROGRESSED,
    build_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1
from services.merchant_decision_layer_v1 import CLASS_CRITICAL_ACTION
from services.merchant_pulse_v1 import (
    FORK_ENTER_WORK,
    FORK_LEAVE,
    STATUS_HEALTHY,
    STATUS_NO_ACTION,
    STATUS_REQUIRE_ACTION,
    build_merchant_pulse_v1_from_summary,
)
from services.merchant_pulse_v1_flag import ENV_MERCHANT_PULSE_V1

STORE = "demo-store"
RK = f"{STORE}:session-pulse-sig-1"


def _base_body(**extra: object) -> dict:
    body: dict = {
        "ok": True,
        "store_slug": STORE,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": "2026-07-10T00:00:00+00:00",
            "empty_calm": False,
            "while_away": {
                "items": [
                    {
                        "headline_ar": "أُرسلت متابعة لسلة واحدة",
                        "detail_ar": "تم القبول من المزود",
                        "aggregation_key": "ach:legacy",
                    }
                ],
                "empty_message_ar": "—",
            },
            "attention_today": {
                "items": [],
                "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
            },
        },
        "whatsapp_readiness_card": {
            "readiness_overall": "ready",
            "connection_state": "connected",
        },
        "store_connection": {"ok": True, "connected": True},
    }
    body.update(extra)
    return body


def _sig(
    signal_type: str,
    *,
    store_slug: str = STORE,
    recovery_key: str = RK,
) -> dict:
    return {
        "signal_type": signal_type,
        "subject": {
            "kind": "cart_recovery",
            "store_slug": store_slug,
            "recovery_key": recovery_key,
        },
        "observed_at": "2026-07-10T12:00:00+00:00",
        "source": "test",
        "evidence_refs": [{"ref_type": "test", "id": 1, "recovery_key": recovery_key}],
    }


class PulseSignalConsumptionTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        os.environ.pop(ENV_MERCHANT_PULSE_V1, None)

    def test_flag_off_preserves_legacy_what_happened(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        body = _base_body(
            commerce_signals_v1={
                "signals": [_sig(SIGNAL_PURCHASE_CONFIRMED)],
            }
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertIn("أُرسلت", pulse["cartflow_progress"]["message"])
        self.assertFalse(pulse["sources"].get("commerce_signals_used"))

    def test_purchase_confirmed_in_what_happened(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_PURCHASE_CONFIRMED)]},
            commerce_language_v1={"amounts_by_key": {RK: 449.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertTrue(pulse["sources"]["commerce_signals_used"])
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_NO_ACTION)
        self.assertIn("استرداد", pulse["executive_brief"]["message"])
        self.assertIn("449", pulse["executive_brief"]["message"])
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))
        # No duplicate legacy achievement text when Signals used for progress
        self.assertNotIn("أُرسلت", pulse["cartflow_progress"]["message"])

    def test_recovery_completed_changes_brief_and_progress_only(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_RECOVERY_COMPLETED)]},
            commerce_language_v1={"amounts_by_key": {RK: 100.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertEqual(pulse["executive_brief"]["status"], STATUS_HEALTHY)
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))
        self.assertIn("خلال غيابك تم استرداد", pulse["executive_brief"]["message"])
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_NO_ACTION)
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_NO_ACTION)
        self.assertEqual(
            pulse["decision_summary"]["message"],
            "لا توجد حالة تحتاج تدخلك الآن.",
        )
        self.assertEqual(
            pulse["merchant_decision"]["message"],
            "لا قرار مطلوب حاليًا.",
        )
        self.assertEqual(pulse["fork"], FORK_LEAVE)

    def test_recovery_blocked_does_not_create_merchant_action(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_RECOVERY_BLOCKED)]}
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertNotEqual(pulse["decision_summary"]["status"], STATUS_REQUIRE_ACTION)
        self.assertNotEqual(pulse["merchant_decision"]["status"], STATUS_REQUIRE_ACTION)
        self.assertIn("توقف", pulse["executive_brief"]["message"])
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))

    def test_decision_require_unchanged_when_signals_present(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_PURCHASE_CONFIRMED)]},
            commerce_language_v1={"amounts_by_key": {RK: 449.0}},
            merchant_home_experience_v1={
                "ok": True,
                "generated_at": "2026-07-10T00:00:00+00:00",
                "while_away": {"items": [], "empty_message_ar": "—"},
                "attention_today": {
                    "items": [
                        {
                            "headline_ar": "سلال بانتظار رقم العميل",
                            "action_ar": "احصل على رقم العميل",
                            "action_present": True,
                            "decision_class": CLASS_CRITICAL_ACTION,
                            "confidence": "high",
                        }
                    ],
                    "empty_message_ar": "—",
                },
            },
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertEqual(pulse["fork"], FORK_ENTER_WORK)
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_REQUIRE_ACTION)
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_REQUIRE_ACTION)
        # Require owns brief; Commerce Language owns progress (no duplicate)
        self.assertIn("رقم العميل", pulse["executive_brief"]["message"])
        self.assertIn("استرداد", pulse["cartflow_progress"]["message"])
        self.assertIn("449", pulse["cartflow_progress"]["message"])
        self.assertFalse(pulse["cartflow_progress"].get("hidden"))
        self.assertNotEqual(
            pulse["executive_brief"]["message"],
            pulse["cartflow_progress"]["message"],
        )

    def test_cross_store_signals_ignored(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={
                "signals": [
                    _sig(SIGNAL_PURCHASE_CONFIRMED, store_slug="other-store"),
                ]
            }
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertFalse(pulse["sources"].get("commerce_signals_used"))
        self.assertIn("أُرسلت", pulse["cartflow_progress"]["message"])

    def test_no_duplicate_facts_from_builder_signals(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        built = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=[
                {
                    "status": "scheduled",
                    "timestamp": "2026-07-10T10:00:00+00:00",
                    "source": "timeline",
                    "store_slug": STORE,
                    "recovery_key": RK,
                    "row_id": 1,
                },
                {
                    "status": "provider_sent",
                    "timestamp": "2026-07-10T10:05:00+00:00",
                    "source": "timeline",
                    "store_slug": STORE,
                    "recovery_key": RK,
                    "row_id": 2,
                },
            ],
            purchase={
                "purchase_detected": True,
                "purchase_time": "2026-07-10T11:00:00+00:00",
                "purchase_source": "order_paid",
                "store_slug": STORE,
                "recovery_key": RK,
                "id": 9,
            },
            force=True,
        )
        # Duplicate the list intentionally
        body = _base_body(
            commerce_signals_v1={"signals": built + built},
            commerce_language_v1={"amounts_by_key": {RK: 449.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertTrue(pulse["sources"]["commerce_signals_used"])
        # Commerce Language owns brief; progress hidden (no duplicate sentence)
        self.assertIn("خلال غيابك تم استرداد", pulse["executive_brief"]["message"])
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))
        self.assertNotEqual(
            pulse["executive_brief"]["message"],
            pulse["cartflow_progress"]["message"],
        )
        self.assertIn(SIGNAL_RECOVERY_COMPLETED, pulse["sources"]["commerce_signal_types"])
        self.assertIn(SIGNAL_RECOVERY_PROGRESSED, pulse["sources"]["commerce_signal_types"])


if __name__ == "__main__":
    unittest.main()
