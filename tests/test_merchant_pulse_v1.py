# -*- coding: utf-8 -*-
"""Merchant Pulse V1 projection tests — Healthy / Require / No Action / Unknown / Loading."""
from __future__ import annotations

import os
import unittest

from services.merchant_home_experience_activation_v1 import finalize_dashboard_summary_payload
from services.merchant_pulse_v1 import (
    FORK_ENTER_WORK,
    FORK_LEAVE,
    PULSE_PROJECTION,
    STATUS_HEALTHY,
    STATUS_LOADING,
    STATUS_NO_ACTION,
    STATUS_REQUIRE_ACTION,
    STATUS_UNKNOWN,
    attach_merchant_pulse_v1_to_summary,
    build_merchant_pulse_v1_from_summary,
)
from services.merchant_pulse_v1_flag import ENV_MERCHANT_PULSE_V1


def _slot_keys(block: dict) -> None:
    for key in ("status", "message", "confidence", "last_updated"):
        assert key in block, f"missing {key}"


class MerchantPulseV1ProjectionTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_MERCHANT_PULSE_V1, None)

    def test_loading_state(self) -> None:
        pulse = build_merchant_pulse_v1_from_summary({}, loading=True, store_slug="demo")
        self.assertEqual(pulse["status"], STATUS_LOADING)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        for key in (
            "executive_brief",
            "decision_summary",
            "cartflow_progress",
            "merchant_decision",
        ):
            _slot_keys(pulse[key])
            self.assertEqual(pulse[key]["status"], STATUS_LOADING)

    def test_healthy_leave(self) -> None:
        body = {
            "ok": True,
            "merchant_home_experience_v1": {
                "ok": True,
                "generated_at": "2026-07-10T00:00:00+00:00",
                "empty_calm": False,
                "while_away": {
                    "items": [
                        {
                            "headline_ar": "أُرسلت متابعة لسلة واحدة",
                            "detail_ar": "تم القبول من المزود",
                            "source_knowledge_id": "k1",
                            "aggregation_key": "ach:1",
                        }
                    ],
                    "empty_message_ar": "—",
                },
                "attention_today": {
                    "items": [],
                    "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
                },
            },
            "merchant_daily_brief_v1": {
                "version": "v2",
                "achievements": [
                    {
                        "headline_ar": "أُرسلت متابعة لسلة واحدة",
                        "why_ar": "تم القبول من المزود",
                        "aggregation_key": "ach:1",
                    }
                ],
                "attention_items": [],
            },
            "whatsapp_readiness_card": {
                "readiness_overall": "ready",
                "connection_state": "connected",
            },
            "store_connection": {"ok": True, "connected": True},
        }
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug="demo")
        self.assertEqual(pulse["projection"], PULSE_PROJECTION)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertIn(pulse["status"], (STATUS_HEALTHY, STATUS_NO_ACTION))
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_NO_ACTION)
        self.assertEqual(pulse["cartflow_progress"]["status"], STATUS_HEALTHY)
        self.assertIn("أُرسلت", pulse["cartflow_progress"]["message"])
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_NO_ACTION)
        for key in (
            "executive_brief",
            "decision_summary",
            "cartflow_progress",
            "merchant_decision",
        ):
            _slot_keys(pulse[key])

    def test_require_action_enter_work(self) -> None:
        body = {
            "ok": True,
            "merchant_home_experience_v1": {
                "ok": True,
                "generated_at": "2026-07-10T00:00:00+00:00",
                "while_away": {"items": []},
                "attention_today": {
                    "items": [
                        {
                            "headline_ar": "سلال بانتظار رقم العميل",
                            "why_ar": "لا يمكن المتابعة بدون تواصل",
                            "action_ar": "احصل على رقم العميل",
                            "action_present": True,
                            "decision_class": "critical_action",
                            "confidence": "high",
                            "aggregation_key": "dec:1",
                            "source_knowledge_id": "d1",
                        }
                    ]
                },
            },
            "merchant_daily_brief_v1": {"attention_items": [], "achievements": []},
            "whatsapp_readiness_card": {
                "readiness_overall": "ready",
                "connection_state": "connected",
            },
            "store_connection": {"ok": True},
        }
        pulse = build_merchant_pulse_v1_from_summary(body, store_slug="demo")
        self.assertEqual(pulse["fork"], FORK_ENTER_WORK)
        self.assertEqual(pulse["status"], STATUS_REQUIRE_ACTION)
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_REQUIRE_ACTION)
        self.assertEqual(pulse["executive_brief"]["status"], STATUS_REQUIRE_ACTION)
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_REQUIRE_ACTION)
        self.assertEqual(pulse["merchant_decision"]["work_entry"], "carts")
        self.assertIn("رقم", pulse["merchant_decision"]["message"])

    def test_no_action_recommend_does_not_enter_work(self) -> None:
        body = {
            "ok": True,
            "merchant_home_experience_v1": {
                "ok": True,
                "generated_at": "2026-07-10T00:00:00+00:00",
                "while_away": {"items": []},
                "attention_today": {
                    "items": [
                        {
                            "headline_ar": "يمكنك مراجعة سلال عالية القيمة",
                            "action_ar": "راجع عند التفرغ",
                            "action_present": True,
                            "decision_class": "suggested_action",
                            "confidence": "medium",
                        }
                    ],
                    "empty_message_ar": "لا أمور تتطلب انتباهك الآن.",
                },
            },
            "whatsapp_readiness_card": {
                "readiness_overall": "ready",
                "connection_state": "connected",
            },
            "store_connection": {"ok": True},
        }
        pulse = build_merchant_pulse_v1_from_summary(body)
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_NO_ACTION)
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_NO_ACTION)

    def test_unknown_when_empty_summary(self) -> None:
        pulse = build_merchant_pulse_v1_from_summary({"ok": True}, store_slug="x")
        self.assertEqual(pulse["fork"], FORK_LEAVE)
        self.assertEqual(pulse["status"], STATUS_UNKNOWN)
        self.assertEqual(pulse["decision_summary"]["status"], STATUS_UNKNOWN)
        self.assertEqual(pulse["merchant_decision"]["status"], STATUS_UNKNOWN)

    def test_flag_off_strips_pulse(self) -> None:
        os.environ[ENV_MERCHANT_PULSE_V1] = "0"
        body = {"ok": True, "merchant_pulse_v1": {"stale": True}}
        out = attach_merchant_pulse_v1_to_summary(body, store_slug="demo")
        self.assertNotIn("merchant_pulse_v1", out)

    def test_flag_on_attaches_via_finalize(self) -> None:
        os.environ[ENV_MERCHANT_PULSE_V1] = "1"
        body = {
            "ok": True,
            "merchant_daily_brief_v1": {
                "version": "v2",
                "achievements": [
                    {
                        "headline_ar": "اكتملت متابعة",
                        "aggregation_key": "a1",
                    }
                ],
                "attention_items": [],
            },
            "whatsapp_readiness_card": {
                "readiness_overall": "ready",
                "connection_state": "connected",
            },
            "store_connection": {"ok": True},
        }
        out = finalize_dashboard_summary_payload(
            body,
            summary_source="live",
            store_slug="demo",
        )
        pulse = out.get("merchant_pulse_v1") or {}
        self.assertTrue(pulse.get("ok"))
        self.assertEqual(pulse.get("projection"), PULSE_PROJECTION)
        self.assertEqual(pulse.get("fork"), FORK_LEAVE)
        for key in (
            "executive_brief",
            "decision_summary",
            "cartflow_progress",
            "merchant_decision",
        ):
            _slot_keys(pulse[key])

    def test_flag_off_finalize_omits_pulse(self) -> None:
        os.environ[ENV_MERCHANT_PULSE_V1] = "0"
        out = finalize_dashboard_summary_payload(
            {"ok": True, "merchant_daily_brief_v1": {}},
            summary_source="live",
            store_slug="demo",
        )
        self.assertNotIn("merchant_pulse_v1", out)


if __name__ == "__main__":
    unittest.main()
