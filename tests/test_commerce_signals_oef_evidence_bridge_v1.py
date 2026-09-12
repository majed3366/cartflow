# -*- coding: utf-8 -*-
"""OEF → Commerce Signals evidence bridge V1."""
from __future__ import annotations

import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from services.commerce_signals_v1 import (
    REF_TYPE_ORDER_ECONOMIC_FACT,
    REF_TYPE_PURCHASE_TRUTH,
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_BLOCKED,
    SIGNAL_RECOVERY_COMPLETED,
    SIGNAL_RECOVERY_PROGRESSED,
    SIGNAL_RECOVERY_STARTED,
    build_commerce_signals_v1,
    load_store_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1

# Proven live production reference (cartflow-42b491 / order 74436306).
STORE = "cartflow-42b491"
OTHER = "other-store"
ORDER_ID = "74436306"
OTHER_ORDER_ID = "74389634"
PT_ID = 1168
OEF_ID = 1
RK = f"{STORE}:session-oef-bridge-1"
RK_OTHER = f"{OTHER}:session-oef-bridge-x"
PAID_AMOUNT = "21"
CURRENCY = "SAR"
CART_VALUE = "999"


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


def _purchase(**overrides: object) -> dict:
    body: dict = {
        "purchase_detected": True,
        "purchase_time": "2026-09-12T00:00:00+00:00",
        "purchase_source": "zid_webhook:platform_paid",
        "store_slug": STORE,
        "recovery_key": RK,
        "id": PT_ID,
        "order_id": ORDER_ID,
        "cart_value": CART_VALUE,
    }
    body.update(overrides)
    return body


def _oef(**overrides: object) -> SimpleNamespace:
    body = {
        "id": OEF_ID,
        "store_slug": STORE,
        "external_order_id": ORDER_ID,
        "paid_amount": PAID_AMOUNT,
        "currency": CURRENCY,
        "payment_state": "paid",
    }
    body.update(overrides)
    return SimpleNamespace(**body)


def _timeline() -> list[dict]:
    return [
        {
            "status": "scheduled",
            "timestamp": "2026-09-12T00:00:00+00:00",
            "source": "recovery_truth_timeline",
            "store_slug": STORE,
            "recovery_key": RK,
            "row_id": 201,
        },
        {
            "status": "provider_sent",
            "timestamp": "2026-09-12T00:05:00+00:00",
            "source": "recovery_truth_timeline",
            "store_slug": STORE,
            "recovery_key": RK,
            "row_id": 202,
        },
    ]


def _blocked() -> dict:
    return {
        "reason": "schedule_blocked_missing_phone",
        "store_slug": STORE,
        "recovery_key": RK,
        "observed_at": "2026-09-12T00:00:00+00:00",
        "source": "recovery_schedule",
        "ref_type": "recovery_schedule",
        "id": 9,
    }


def _purchase_signal(signals: list[dict]) -> dict:
    purchases = [s for s in signals if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED]
    assert len(purchases) == 1, purchases
    return purchases[0]


def _oef_refs(sig: dict) -> list[dict]:
    return [
        ref
        for ref in sig.get("evidence_refs") or []
        if isinstance(ref, dict) and ref.get("ref_type") == REF_TYPE_ORDER_ECONOMIC_FACT
    ]


def _money_tokens(payload: object) -> str:
    return json.dumps(payload, default=str)


class OefSignalBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)

    def test_a_purchase_truth_plus_matching_oef_attaches_21_sar(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
            order_economic_fact=_oef(),
            force=True,
        )
        confirmed = _purchase_signal(signals)
        _contract_keys(confirmed)
        oef_refs = _oef_refs(confirmed)
        self.assertEqual(len(oef_refs), 1)
        self.assertEqual(oef_refs[0]["paid_amount"], PAID_AMOUNT)
        self.assertEqual(oef_refs[0]["currency"], CURRENCY)
        self.assertEqual(oef_refs[0]["id"], OEF_ID)
        blob = _money_tokens(confirmed)
        self.assertIn(PAID_AMOUNT, blob)
        self.assertIn(CURRENCY, blob)
        self.assertNotIn(CART_VALUE, blob)

    def test_b_purchase_truth_without_oef_stays_unquantified(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
            order_economic_fact=None,
            force=True,
        )
        confirmed = _purchase_signal(signals)
        _contract_keys(confirmed)
        self.assertEqual(_oef_refs(confirmed), [])
        blob = _money_tokens(confirmed)
        self.assertNotIn(PAID_AMOUNT, blob)
        self.assertNotIn(CURRENCY, blob)
        self.assertNotIn(CART_VALUE, blob)
        self.assertNotIn("paid_amount", blob)
        self.assertNotIn("recommend", blob.lower())
        pt_refs = [
            ref
            for ref in confirmed["evidence_refs"]
            if ref.get("ref_type") == REF_TYPE_PURCHASE_TRUTH
        ]
        self.assertEqual(len(pt_refs), 1)
        self.assertEqual(pt_refs[0]["id"], PT_ID)

    def test_c_foreign_store_or_order_oef_never_attaches(self) -> None:
        foreign_store = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
            order_economic_fact=_oef(store_slug=OTHER),
            force=True,
        )
        foreign_order = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
            order_economic_fact=_oef(external_order_id=OTHER_ORDER_ID),
            force=True,
        )
        for signals in (foreign_store, foreign_order):
            confirmed = _purchase_signal(signals)
            self.assertEqual(_oef_refs(confirmed), [])
            blob = _money_tokens(confirmed)
            self.assertNotIn(PAID_AMOUNT, blob)
            self.assertNotIn("paid_amount", blob)

    def test_d_non_purchase_signals_unchanged(self) -> None:
        without = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline(),
            blocked=_blocked(),
            order_economic_fact=_oef(),
            force=True,
        )
        with_purchase = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            timeline_events=_timeline(),
            purchase=_purchase(),
            blocked=_blocked(),
            order_economic_fact=_oef(),
            force=True,
        )
        non_purchase_types = (
            SIGNAL_RECOVERY_STARTED,
            SIGNAL_RECOVERY_PROGRESSED,
            SIGNAL_RECOVERY_BLOCKED,
        )
        for signal_type in non_purchase_types:
            left = [s for s in without if s["signal_type"] == signal_type]
            right = [s for s in with_purchase if s["signal_type"] == signal_type]
            self.assertEqual(len(left), 1)
            self.assertEqual(left, right)
            self.assertEqual(_oef_refs(left[0]), [])
        completed = [
            s for s in with_purchase if s["signal_type"] == SIGNAL_RECOVERY_COMPLETED
        ]
        self.assertEqual(len(completed), 1)
        self.assertEqual(_oef_refs(completed[0]), [])

    def test_e_purchase_confirmed_backward_compatible_without_order_id(self) -> None:
        legacy = _purchase()
        legacy.pop("order_id")
        reader = mock.Mock(return_value=_oef())
        with mock.patch(
            "services.commerce_signals_v1._read_order_economic_fact",
            reader,
        ):
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=legacy,
                force=True,
            )
        confirmed = _purchase_signal(signals)
        _contract_keys(confirmed)
        self.assertEqual(
            confirmed["evidence_refs"],
            [
                {
                    "ref_type": REF_TYPE_PURCHASE_TRUTH,
                    "id": PT_ID,
                    "recovery_key": RK,
                }
            ],
        )
        reader.assert_not_called()

    def test_blank_or_non_positive_paid_amount_not_attached(self) -> None:
        for paid in ("", "0", "-1", None):
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=_purchase(),
                order_economic_fact=_oef(paid_amount=paid),
                force=True,
            )
            confirmed = _purchase_signal(signals)
            self.assertEqual(_oef_refs(confirmed), [])

    def test_persist_lookup_path_is_get_order_economic_fact(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_fact",
            return_value=_oef(),
        ) as lookup:
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=_purchase(),
                force=True,
            )
        lookup.assert_called_once_with(
            store_slug=STORE,
            external_order_id=ORDER_ID,
        )
        confirmed = _purchase_signal(signals)
        self.assertEqual(_oef_refs(confirmed)[0]["paid_amount"], PAID_AMOUNT)
        self.assertEqual(_oef_refs(confirmed)[0]["currency"], CURRENCY)

    def test_lookup_uses_store_slug_and_order_id(self) -> None:
        reader = mock.Mock(return_value=_oef())
        with mock.patch(
            "services.commerce_signals_v1._read_order_economic_fact",
            reader,
        ):
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=_purchase(),
                force=True,
            )
        reader.assert_called_once_with(STORE, ORDER_ID)
        confirmed = _purchase_signal(signals)
        self.assertEqual(_oef_refs(confirmed)[0]["paid_amount"], PAID_AMOUNT)

    def test_lookup_exception_does_not_block_purchase_confirmed(self) -> None:
        with mock.patch(
            "services.commerce_signals_v1._read_order_economic_fact",
            side_effect=RuntimeError("oef unavailable"),
        ):
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=_purchase(),
                force=True,
            )
        confirmed = _purchase_signal(signals)
        self.assertEqual(_oef_refs(confirmed), [])

    def test_load_store_attaches_matching_oef_only(self) -> None:
        purchase = _purchase()
        matching = _oef()
        foreign = _oef(store_slug=OTHER, external_order_id=OTHER_ORDER_ID, id=99)

        def _read(store_slug: str, order_id: str):
            if store_slug == STORE and order_id == ORDER_ID:
                return matching
            return foreign

        with mock.patch(
            "services.commerce_signals_v1._read_order_economic_fact",
            side_effect=_read,
        ), mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            return_value=purchase,
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK, RK_OTHER],
            )
        confirmed = _purchase_signal(payload["signals"])
        oef_refs = _oef_refs(confirmed)
        self.assertEqual(len(oef_refs), 1)
        self.assertEqual(oef_refs[0]["paid_amount"], PAID_AMOUNT)
        self.assertEqual(oef_refs[0]["currency"], CURRENCY)

    def test_load_store_missing_oef_keeps_purchase_confirmed(self) -> None:
        with mock.patch(
            "services.commerce_signals_v1._read_order_economic_fact",
            return_value=None,
        ), mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            return_value=_purchase(),
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK],
            )
        confirmed = _purchase_signal(payload["signals"])
        self.assertEqual(_oef_refs(confirmed), [])
        self.assertNotIn("paid_amount", _money_tokens(confirmed))


if __name__ == "__main__":
    unittest.main()
