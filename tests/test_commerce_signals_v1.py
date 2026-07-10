# -*- coding: utf-8 -*-
"""Commerce Signals V1 — Recovery + Purchase projection tests."""
from __future__ import annotations

import os
import unittest

from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_BLOCKED,
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_RECOVERY_PROGRESSED,
    SIGNAL_RECOVERY_STARTED,
    build_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import (
    ENV_COMMERCE_SIGNALS_V1,
    commerce_signals_v1_enabled,
)

STORE = "demo-store"
RK = f"{STORE}:session-signals-1"


def _contract_keys(sig: dict) -> None:
    for key in ("signal_type", "subject", "observed_at", "source", "evidence_refs"):
        assert key in sig, f"missing {key}"
    assert set(sig.keys()) == {
        "signal_type",
        "subject",
        "observed_at",
        "source",
        "evidence_refs",
    }


def _timeline_started() -> list[dict]:
    return [
        {
            "status": "scheduled",
            "timestamp": "2026-07-10T10:00:00+00:00",
            "source": "recovery_truth_timeline",
            "store_slug": STORE,
            "recovery_key": RK,
            "row_id": 101,
        }
    ]


def _timeline_progressed() -> list[dict]:
    return _timeline_started() + [
        {
            "status": "provider_sent",
            "timestamp": "2026-07-10T10:05:00+00:00",
            "source": "recovery_truth_timeline",
            "store_slug": STORE,
            "recovery_key": RK,
            "row_id": 102,
        }
    ]


def _purchase() -> dict:
    return {
        "purchase_detected": True,
        "purchase_time": "2026-07-10T11:00:00+00:00",
        "purchase_source": "order_paid",
        "store_slug": STORE,
        "recovery_key": RK,
        "id": 55,
    }


class CommerceSignalsFlagTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)

    def test_flag_default_off(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        self.assertFalse(commerce_signals_v1_enabled())

    def test_flag_off_produces_no_signals(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline_progressed(),
            purchase=_purchase(),
        )
        self.assertEqual(signals, [])


class CommerceSignalsProjectionTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)

    def setUp(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"

    def test_recovery_completed_produces_one_valid_signal(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline_started(),
            purchase=_purchase(),
        )
        completed = [s for s in signals if s["signal_type"] == SIGNAL_RECOVERY_COMPLETED]
        self.assertEqual(len(completed), 1)
        _contract_keys(completed[0])
        self.assertEqual(completed[0]["subject"]["recovery_key"], RK)
        self.assertTrue(completed[0]["evidence_refs"])

    def test_blocked_recovery_produces_one_valid_signal(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            blocked={
                "reason": "schedule_blocked_missing_phone",
                "store_slug": STORE,
                "recovery_key": RK,
                "observed_at": "2026-07-10T09:00:00+00:00",
                "source": "recovery_schedule",
                "ref_type": "recovery_schedule",
                "id": 9,
            },
        )
        blocked = [s for s in signals if s["signal_type"] == SIGNAL_RECOVERY_BLOCKED]
        self.assertEqual(len(blocked), 1)
        _contract_keys(blocked[0])
        self.assertEqual(blocked[0]["signal_type"], SIGNAL_RECOVERY_BLOCKED)

    def test_confirmed_purchase_produces_one_valid_signal(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
        )
        purchases = [s for s in signals if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED]
        self.assertEqual(len(purchases), 1)
        _contract_keys(purchases[0])
        # No recovery_completed without recovery_started
        self.assertFalse(
            any(s["signal_type"] == SIGNAL_RECOVERY_COMPLETED for s in signals)
        )

    def test_duplicate_evidence_does_not_duplicate_signals(self) -> None:
        dup_timeline = _timeline_progressed() + _timeline_progressed()
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=dup_timeline,
            purchase=_purchase(),
        )
        by_type: dict[str, int] = {}
        for s in signals:
            by_type[s["signal_type"]] = by_type.get(s["signal_type"], 0) + 1
            _contract_keys(s)
        self.assertEqual(by_type.get(SIGNAL_RECOVERY_STARTED), 1)
        self.assertEqual(by_type.get(SIGNAL_RECOVERY_PROGRESSED), 1)
        self.assertEqual(by_type.get(SIGNAL_PURCHASE_CONFIRMED), 1)
        self.assertEqual(by_type.get(SIGNAL_RECOVERY_COMPLETED), 1)

        # Same purchase twice in one build path via force re-entry of identical refs
        again = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline_started(),
            purchase=_purchase(),
        )
        purchases = [s for s in again if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED]
        self.assertEqual(len(purchases), 1)

    def test_cross_store_evidence_is_rejected(self) -> None:
        # Wrong recovery_key prefix for requested store
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key="other-store:session-x",
            timeline_events=_timeline_started(),
            purchase=_purchase(),
        )
        self.assertEqual(signals, [])

        # Timeline + purchase stamped for another store while rk matches
        foreign_timeline = [
            {
                "status": "scheduled",
                "timestamp": "2026-07-10T10:00:00+00:00",
                "source": "recovery_truth_timeline",
                "store_slug": "other-store",
                "recovery_key": RK,
                "row_id": 201,
            }
        ]
        foreign_purchase = dict(_purchase())
        foreign_purchase["store_slug"] = "other-store"
        signals2 = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=foreign_timeline,
            purchase=foreign_purchase,
            blocked={
                "reason": "schedule_blocked_missing_phone",
                "store_slug": "other-store",
                "recovery_key": RK,
                "id": 1,
            },
        )
        self.assertEqual(signals2, [])

    def test_started_and_progressed_emit(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline_progressed(),
        )
        types = {s["signal_type"] for s in signals}
        self.assertIn(SIGNAL_RECOVERY_STARTED, types)
        self.assertIn(SIGNAL_RECOVERY_PROGRESSED, types)
        for s in signals:
            _contract_keys(s)


if __name__ == "__main__":
    unittest.main()
