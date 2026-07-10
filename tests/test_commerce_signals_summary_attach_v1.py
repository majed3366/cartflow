# -*- coding: utf-8 -*-
"""Commerce Signals V1 — summary attach before Pulse."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from services.commerce_signals_v1 import (
    PROJECTION,
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_PROGRESSED,
    attach_commerce_signals_v1_to_summary,
    build_commerce_signals_v1,
    load_store_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1
from services.merchant_home_experience_activation_v1 import (
    finalize_dashboard_summary_payload,
)
from services.merchant_pulse_v1_flag import ENV_MERCHANT_PULSE_V1
from services.recovery_truth_timeline_v1 import STATUS_PROVIDER_SENT, STATUS_SCHEDULED

STORE = "demo-store"
OTHER = "other-store"
RK = f"{STORE}:session-attach-1"
RK_OTHER = f"{OTHER}:session-attach-x"


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


def _base_summary(**extra: object) -> dict:
    body: dict = {
        "ok": True,
        "store_slug": STORE,
        "merchant_home_experience_v1": {
            "ok": True,
            "generated_at": "2026-07-10T00:00:00+00:00",
            "empty_calm": True,
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


class SummaryAttachFlagTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        os.environ.pop(ENV_MERCHANT_PULSE_V1, None)

    def test_flag_off_omits_key(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        body = _base_summary(commerce_signals_v1={"signals": [_sig(SIGNAL_PURCHASE_CONFIRMED)]})
        out = attach_commerce_signals_v1_to_summary(body, store_slug=STORE)
        self.assertNotIn("commerce_signals_v1", out)

    def test_flag_on_attaches_empty_valid_payload(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        with mock.patch(
            "services.commerce_signals_v1.load_store_commerce_signals_v1",
            return_value={
                "ok": True,
                "projection": PROJECTION,
                "store_slug": STORE,
                "signals": [],
                "read_only": True,
            },
        ):
            out = attach_commerce_signals_v1_to_summary(_base_summary(), store_slug=STORE)
        payload = out.get("commerce_signals_v1")
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload.get("projection"), PROJECTION)
        self.assertEqual(payload.get("store_slug"), STORE)
        self.assertEqual(payload.get("signals"), [])
        self.assertTrue(payload.get("read_only"))


class SummaryAttachFinalizeTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        os.environ.pop(ENV_MERCHANT_PULSE_V1, None)

    def test_flag_on_finalize_attaches_and_pulse_uses_signals(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        os.environ[ENV_MERCHANT_PULSE_V1] = "1"
        signals = [_sig(SIGNAL_PURCHASE_CONFIRMED)]
        with mock.patch(
            "services.commerce_signals_v1.load_store_commerce_signals_v1",
            return_value={
                "ok": True,
                "projection": PROJECTION,
                "store_slug": STORE,
                "signals": signals,
                "read_only": True,
            },
        ):
            out = finalize_dashboard_summary_payload(
                _base_summary(),
                summary_source="live",
                store_slug=STORE,
            )
        self.assertIn("commerce_signals_v1", out)
        self.assertEqual(out["commerce_signals_v1"]["signals"], signals)
        pulse = out.get("merchant_pulse_v1") or {}
        self.assertTrue(pulse.get("sources", {}).get("commerce_signals_used"))
        self.assertIn("شراء", pulse.get("executive_brief", {}).get("message", ""))

    def test_flag_off_finalize_omits_signals_keeps_legacy_pulse(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        os.environ[ENV_MERCHANT_PULSE_V1] = "1"
        out = finalize_dashboard_summary_payload(
            _base_summary(
                merchant_daily_brief_v1={
                    "achievements": [
                        {
                            "headline_ar": "أُرسلت متابعة لسلة",
                            "aggregation_key": "ach:1",
                        }
                    ],
                    "attention_items": [],
                },
                merchant_home_experience_v1={
                    "ok": True,
                    "generated_at": "2026-07-10T00:00:00+00:00",
                    "empty_calm": False,
                    "while_away": {
                        "items": [
                            {
                                "headline_ar": "أُرسلت متابعة لسلة",
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
            ),
            summary_source="live",
            store_slug=STORE,
        )
        self.assertNotIn("commerce_signals_v1", out)
        pulse = out.get("merchant_pulse_v1") or {}
        self.assertFalse(pulse.get("sources", {}).get("commerce_signals_used"))
        self.assertIn("أُرسلت", pulse.get("cartflow_progress", {}).get("message", ""))

    def test_empty_signals_do_not_break_pulse(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        os.environ[ENV_MERCHANT_PULSE_V1] = "1"
        with mock.patch(
            "services.commerce_signals_v1.load_store_commerce_signals_v1",
            return_value={
                "ok": True,
                "projection": PROJECTION,
                "store_slug": STORE,
                "signals": [],
                "read_only": True,
            },
        ):
            out = finalize_dashboard_summary_payload(
                _base_summary(),
                summary_source="live",
                store_slug=STORE,
            )
        self.assertEqual(out["commerce_signals_v1"]["signals"], [])
        pulse = out.get("merchant_pulse_v1") or {}
        self.assertTrue(pulse.get("ok"))
        self.assertFalse(pulse.get("sources", {}).get("commerce_signals_used"))

    def test_cross_store_signals_not_consumed_by_pulse(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        os.environ[ENV_MERCHANT_PULSE_V1] = "1"
        foreign = [_sig(SIGNAL_PURCHASE_CONFIRMED, store_slug=OTHER, recovery_key=RK_OTHER)]
        with mock.patch(
            "services.commerce_signals_v1.load_store_commerce_signals_v1",
            return_value={
                "ok": True,
                "projection": PROJECTION,
                "store_slug": STORE,
                "signals": foreign,
                "read_only": True,
            },
        ):
            out = finalize_dashboard_summary_payload(
                _base_summary(),
                summary_source="live",
                store_slug=STORE,
            )
        pulse = out.get("merchant_pulse_v1") or {}
        self.assertFalse(pulse.get("sources", {}).get("commerce_signals_used"))


class StoreLoadIsolationTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)

    def test_load_store_skips_foreign_recovery_keys(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        foreign_built = build_commerce_signals_v1(
            store_slug=OTHER,
            recovery_key=RK_OTHER,
            timeline_events=[
                {
                    "status": STATUS_SCHEDULED,
                    "timestamp": "2026-07-10T10:00:00+00:00",
                    "source": "recovery_truth_timeline",
                    "store_slug": OTHER,
                    "recovery_key": RK_OTHER,
                    "row_id": 1,
                },
                {
                    "status": STATUS_PROVIDER_SENT,
                    "timestamp": "2026-07-10T10:05:00+00:00",
                    "source": "recovery_truth_timeline",
                    "store_slug": OTHER,
                    "recovery_key": RK_OTHER,
                    "row_id": 2,
                },
            ],
            force=True,
        )
        self.assertTrue(foreign_built)

        with mock.patch(
            "services.commerce_signals_v1._recent_store_recovery_keys",
            return_value=[RK_OTHER],
        ), mock.patch(
            "services.commerce_signals_v1.load_commerce_signals_for_recovery_key",
            return_value={
                "ok": False,
                "error": "store_isolation_rejected",
                "signals": foreign_built,
            },
        ):
            # recovery_keys override still filters by store prefix before load
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK_OTHER],
            )
        self.assertEqual(payload.get("signals"), [])

    def test_load_store_dedupes_identical_facts(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"
        built = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=[
                {
                    "status": STATUS_SCHEDULED,
                    "timestamp": "2026-07-10T10:00:00+00:00",
                    "source": "recovery_truth_timeline",
                    "store_slug": STORE,
                    "recovery_key": RK,
                    "row_id": 11,
                },
                {
                    "status": STATUS_PROVIDER_SENT,
                    "timestamp": "2026-07-10T10:05:00+00:00",
                    "source": "recovery_truth_timeline",
                    "store_slug": STORE,
                    "recovery_key": RK,
                    "row_id": 12,
                },
            ],
            force=True,
        )
        self.assertTrue(
            any(s["signal_type"] == SIGNAL_RECOVERY_PROGRESSED for s in built)
        )
        with mock.patch(
            "services.commerce_signals_v1.load_commerce_signals_for_recovery_key",
            return_value={
                "ok": True,
                "signals": list(built) + list(built),
            },
        ):
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK],
            )
        types = [s["signal_type"] for s in payload["signals"]]
        self.assertEqual(len(types), len(set(types)))


if __name__ == "__main__":
    unittest.main()
