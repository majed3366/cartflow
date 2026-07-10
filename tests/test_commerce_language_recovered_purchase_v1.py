# -*- coding: utf-8 -*-
"""Commerce Language V1 — recovered purchase outcome wording."""
from __future__ import annotations

import os
import unittest

from services.commerce_language_v1 import (
    DECISION_SUMMARY_NO_INTERVENTION_AR,
    MERCHANT_DECISION_NO_DECISION_AR,
    format_recovered_value_ar,
    recovered_purchase_count_phrase_ar,
    recovered_purchase_outcome_ar,
    resolve_recovered_purchase_total,
)
from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_COMPLETED,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1
from services.merchant_pulse_v1 import (
    FORK_LEAVE,
    STATUS_NO_ACTION,
    build_merchant_pulse_v1_from_summary,
)
from services.merchant_pulse_v1_flag import ENV_MERCHANT_PULSE_V1

STORE = "demo-store"
RK1 = f"{STORE}:cf_cart_one"
RK2 = f"{STORE}:cf_cart_two"


def _base_body(**extra: object) -> dict:
    body: dict = {
        "ok": True,
        "store_slug": STORE,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": "2026-07-10T00:00:00+00:00",
            "empty_calm": False,
            "while_away": {"items": [], "empty_message_ar": "—"},
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


def _sig(signal_type: str, recovery_key: str = RK1) -> dict:
    return {
        "signal_type": signal_type,
        "subject": {
            "kind": "cart_recovery",
            "store_slug": STORE,
            "recovery_key": recovery_key,
        },
        "observed_at": "2026-07-10T12:00:00+00:00",
        "source": "test",
        "evidence_refs": [{"ref_type": "test", "id": 1, "recovery_key": recovery_key}],
    }


class CommerceLanguageRecoveredPurchaseTests(unittest.TestCase):
    def test_singular_with_value(self) -> None:
        msg = recovered_purchase_outcome_ar(count=1, total_value=449.0)
        self.assertEqual(
            msg,
            "خلال غيابك تم استرداد عملية شراء واحدة بقيمة 449 ريال.",
        )
        self.assertNotIn("449.0", msg)

    def test_plural_with_total_value(self) -> None:
        msg = recovered_purchase_outcome_ar(count=3, total_value=1200.5)
        self.assertIn("3 عمليات شراء", msg)
        self.assertIn("بقيمة 1200.5 ريال", msg)
        self.assertTrue(msg.startswith("خلال غيابك تم استرداد"))

    def test_dual_form(self) -> None:
        self.assertEqual(recovered_purchase_count_phrase_ar(2), "عمليتي شراء")
        msg = recovered_purchase_outcome_ar(count=2, total_value=100)
        self.assertIn("عمليتي شراء", msg)

    def test_missing_value_safe_wording(self) -> None:
        msg = recovered_purchase_outcome_ar(count=1, total_value=None)
        self.assertEqual(msg, "خلال غيابك تم استرداد عملية شراء واحدة.")
        self.assertNotIn("بقيمة", msg)
        self.assertNotIn("ريال", msg)

    def test_zero_or_negative_value_omitted(self) -> None:
        self.assertNotIn("بقيمة", recovered_purchase_outcome_ar(count=1, total_value=0))
        self.assertNotIn("بقيمة", recovered_purchase_outcome_ar(count=1, total_value=-5))

    def test_format_whole_and_fraction(self) -> None:
        self.assertEqual(format_recovered_value_ar(449.0), "449")
        self.assertEqual(format_recovered_value_ar(449.5), "449.5")

    def test_resolve_total_requires_all_amounts(self) -> None:
        n, total = resolve_recovered_purchase_total(
            count=2,
            recovery_keys=[RK1, RK2],
            amounts_by_key={RK1: 100.0, RK2: None},
        )
        self.assertEqual(n, 2)
        self.assertIsNone(total)
        n2, total2 = resolve_recovered_purchase_total(
            count=2,
            recovery_keys=[RK1, RK2],
            amounts_by_key={RK1: 100.0, RK2: 349.0},
        )
        self.assertEqual(n2, 2)
        self.assertEqual(total2, 449.0)


class PulseRecoveredPurchaseLanguageTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        os.environ.pop(ENV_MERCHANT_PULSE_V1, None)

    def test_one_recovered_purchase_with_value(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={
                "signals": [_sig(SIGNAL_RECOVERY_COMPLETED)],
            },
            commerce_language_v1={"amounts_by_key": {RK1: 449.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertEqual(
            pulse["executive_brief"]["message"],
            "خلال غيابك تم استرداد عملية شراء واحدة بقيمة 449 ريال.",
        )
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))
        self.assertEqual(
            pulse["decision_summary"]["message"],
            DECISION_SUMMARY_NO_INTERVENTION_AR,
        )
        self.assertEqual(
            pulse["merchant_decision"]["message"],
            MERCHANT_DECISION_NO_DECISION_AR,
        )
        self.assertNotEqual(
            pulse["executive_brief"]["message"],
            pulse["cartflow_progress"]["message"],
        )
        # No hard-coded technical recovery path wording
        self.assertNotIn("اكتمل مسار", pulse["executive_brief"]["message"])

    def test_multiple_recovered_purchases_total_value(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={
                "signals": [
                    _sig(SIGNAL_PURCHASE_CONFIRMED, RK1),
                    _sig(SIGNAL_RECOVERY_COMPLETED, RK2),
                ]
            },
            commerce_language_v1={"amounts_by_key": {RK1: 200.0, RK2: 249.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertIn("عمليتي شراء", pulse["executive_brief"]["message"])
        self.assertIn("بقيمة 449 ريال", pulse["executive_brief"]["message"])
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))

    def test_missing_value_no_invented_amount(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_PURCHASE_CONFIRMED)]},
            commerce_language_v1={"amounts_by_key": {RK1: None}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        msg = pulse["executive_brief"]["message"]
        self.assertEqual(msg, "خلال غيابك تم استرداد عملية شراء واحدة.")
        self.assertNotIn("449", msg)
        self.assertNotIn("بقيمة", msg)

    def test_no_duplicate_sentence_across_slots(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            commerce_signals_v1={"signals": [_sig(SIGNAL_RECOVERY_COMPLETED)]},
            commerce_language_v1={"amounts_by_key": {RK1: 449.0}},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        messages = [
            pulse["executive_brief"]["message"],
            pulse["decision_summary"]["message"],
            pulse["cartflow_progress"]["message"],
            pulse["merchant_decision"]["message"],
        ]
        visible = [
            m
            for m, slot in zip(
                messages,
                (
                    pulse["executive_brief"],
                    pulse["decision_summary"],
                    pulse["cartflow_progress"],
                    pulse["merchant_decision"],
                ),
            )
            if not slot.get("hidden")
        ]
        self.assertEqual(len(visible), len(set(visible)))
        self.assertTrue(pulse["cartflow_progress"].get("hidden"))

    def test_no_recovered_purchase_keeps_fallback_progress(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        body = _base_body(
            merchant_home_experience_v1={
                "ok": True,
                "generated_at": "2026-07-10T00:00:00+00:00",
                "while_away": {
                    "items": [
                        {
                            "headline_ar": "أُرسلت متابعة لسلة واحدة",
                            "detail_ar": "تم القبول من المزود",
                        }
                    ],
                    "empty_message_ar": "—",
                },
                "attention_today": {
                    "items": [],
                    "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
                },
            },
            commerce_signals_v1={"signals": []},
        )
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug=STORE)
        self.assertIn("أُرسلت", pulse["cartflow_progress"]["message"])
        self.assertFalse(pulse["cartflow_progress"].get("hidden"))
        self.assertNotIn("خلال غيابك تم استرداد", pulse["executive_brief"]["message"])
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_NO_ACTION)


if __name__ == "__main__":
    unittest.main()
