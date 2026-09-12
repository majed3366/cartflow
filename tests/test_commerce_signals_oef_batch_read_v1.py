# -*- coding: utf-8 -*-
"""OEF batch read correction — Commerce Signals DSE proofs A–L."""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from services.commerce_signals_v1 import (
    REF_TYPE_ORDER_ECONOMIC_FACT,
    SIGNAL_PURCHASE_CONFIRMED,
    build_commerce_signals_v1,
    load_commerce_signals_for_recovery_key,
    load_store_commerce_signals_v1,
)
from services.commerce_signals_v1_flag import ENV_COMMERCE_SIGNALS_V1
from services.order_economic_fact_v1.persist import (
    MAX_BATCH_ORDER_IDS,
    _bounded_external_order_ids,
    get_order_economic_fact,
    get_order_economic_facts,
)

STORE = "cartflow-42b491"
OTHER = "other-store"
ORDER_ID = "74436306"
OTHER_ORDER_ID = "74389634"
PT_ID = 1168
OEF_ID = 1
RK = f"{STORE}:session-oef-bridge-1"
PAID_AMOUNT = "21"
CURRENCY = "SAR"
CART_VALUE = "999"

EXPECTED_OEF_REF = {
    "ref_type": REF_TYPE_ORDER_ECONOMIC_FACT,
    "id": OEF_ID,
    "recovery_key": RK,
    "paid_amount": PAID_AMOUNT,
    "currency": CURRENCY,
    "status": "paid",
}


def _purchase(*, recovery_key: str = RK, order_id: str = ORDER_ID, pt_id: int = PT_ID) -> dict:
    return {
        "purchase_detected": True,
        "purchase_time": "2026-09-12T00:00:00+00:00",
        "purchase_source": "zid_webhook:platform_paid",
        "store_slug": STORE,
        "recovery_key": recovery_key,
        "id": pt_id,
        "order_id": order_id,
        "cart_value": CART_VALUE,
    }


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


def _purchase_signal(signals: list) -> dict:
    purchases = [s for s in signals if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED]
    assert len(purchases) == 1, purchases
    return purchases[0]


def _oef_refs(sig: dict) -> list[dict]:
    return [
        ref
        for ref in sig.get("evidence_refs") or []
        if isinstance(ref, dict) and ref.get("ref_type") == REF_TYPE_ORDER_ECONOMIC_FACT
    ]


def _empty_query(*_a, **_k):
    q = mock.MagicMock()
    q.filter.return_value.all.return_value = []
    q.filter.return_value.first.return_value = None
    return q


class OefBatchPersistTests(unittest.TestCase):
    def test_empty_or_invalid_input_makes_zero_queries(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.db.session.query"
        ) as query:
            self.assertEqual(
                get_order_economic_facts(store_slug="", external_order_ids=[ORDER_ID]),
                {},
            )
            self.assertEqual(
                get_order_economic_facts(store_slug=STORE, external_order_ids=[]),
                {},
            )
            self.assertEqual(
                get_order_economic_facts(store_slug=STORE, external_order_ids=["", "  "]),
                {},
            )
            self.assertIsNone(
                get_order_economic_fact(store_slug=STORE, external_order_id="")
            )
            query.assert_not_called()

    def test_d_duplicate_order_ids_are_deduplicated(self) -> None:
        self.assertEqual(
            _bounded_external_order_ids([ORDER_ID, ORDER_ID, f" {ORDER_ID} ", OTHER_ORDER_ID]),
            [ORDER_ID, OTHER_ORDER_ID],
        )

    def test_batch_caps_at_25(self) -> None:
        ids = [str(i) for i in range(40)]
        bounded = _bounded_external_order_ids(ids)
        self.assertEqual(len(bounded), MAX_BATCH_ORDER_IDS)
        self.assertEqual(bounded, ids[:MAX_BATCH_ORDER_IDS])

    def test_reads_do_not_call_schema_ensure(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.db.session.query",
            side_effect=_empty_query,
        ), mock.patch(
            "services.order_economic_fact_v1.persist.ensure_order_economic_fact_schema"
        ) as ensure:
            self.assertEqual(
                get_order_economic_facts(
                    store_slug=STORE,
                    external_order_ids=[ORDER_ID, OTHER_ORDER_ID],
                ),
                {},
            )
            self.assertIsNone(
                get_order_economic_fact(store_slug=STORE, external_order_id=ORDER_ID)
            )
            ensure.assert_not_called()


class OefBatchSignalsTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ[ENV_COMMERCE_SIGNALS_V1] = "1"

    def tearDown(self) -> None:
        os.environ.pop(ENV_COMMERCE_SIGNALS_V1, None)

    def _load_store(self, *, purchases_by_key: dict[str, dict], facts: dict, keys: list[str]):
        def _purchase_ctx(recovery_key: str):
            return purchases_by_key.get(recovery_key)

        with mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_facts",
            return_value=facts,
        ) as batch, mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_fact",
        ) as single, mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            side_effect=_purchase_ctx,
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=keys,
            )
        return payload, batch, single

    def test_a_store_load_multiple_purchases_one_oef_select(self) -> None:
        rk2 = f"{STORE}:session-oef-bridge-2"
        oid2 = "74436307"
        purchases = {
            RK: _purchase(),
            rk2: _purchase(recovery_key=rk2, order_id=oid2, pt_id=1169),
        }
        facts = {
            ORDER_ID: _oef(),
            oid2: _oef(id=2, external_order_id=oid2, paid_amount="21"),
        }
        payload, batch, single = self._load_store(
            purchases_by_key=purchases,
            facts=facts,
            keys=[RK, rk2],
        )
        self.assertEqual(batch.call_count, 1)
        single.assert_not_called()
        called_ids = list(batch.call_args.kwargs["external_order_ids"])
        self.assertEqual(called_ids, [ORDER_ID, oid2])
        purchases_out = [
            s for s in payload["signals"] if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED
        ]
        self.assertEqual(len(purchases_out), 2)

    def test_b_twenty_five_eligible_keys_still_one_oef_select(self) -> None:
        keys = []
        purchases = {}
        facts = {}
        for i in range(25):
            rk = f"{STORE}:session-oef-bridge-{i}"
            oid = f"74436{i:03d}"
            keys.append(rk)
            purchases[rk] = _purchase(recovery_key=rk, order_id=oid, pt_id=2000 + i)
            facts[oid] = _oef(id=i + 1, external_order_id=oid)
        payload, batch, single = self._load_store(
            purchases_by_key=purchases,
            facts=facts,
            keys=keys,
        )
        self.assertEqual(batch.call_count, 1)
        single.assert_not_called()
        self.assertEqual(len(batch.call_args.kwargs["external_order_ids"]), 25)
        self.assertEqual(
            sum(1 for s in payload["signals"] if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED),
            25,
        )

    def test_c_no_eligible_order_id_zero_oef_selects(self) -> None:
        purchase = _purchase()
        purchase.pop("order_id")
        with mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_facts",
        ) as batch, mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            return_value=purchase,
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK],
            )
        batch.assert_not_called()
        confirmed = _purchase_signal(payload["signals"])
        self.assertEqual(_oef_refs(confirmed), [])

    def test_d_store_load_deduplicates_duplicate_order_ids(self) -> None:
        rk2 = f"{STORE}:session-oef-bridge-dup"
        purchases = {
            RK: _purchase(),
            rk2: _purchase(recovery_key=rk2, order_id=ORDER_ID, pt_id=1170),
        }
        payload, batch, single = self._load_store(
            purchases_by_key=purchases,
            facts={ORDER_ID: _oef()},
            keys=[RK, rk2],
        )
        self.assertEqual(batch.call_count, 1)
        single.assert_not_called()
        self.assertEqual(list(batch.call_args.kwargs["external_order_ids"]), [ORDER_ID])
        self.assertEqual(
            sum(1 for s in payload["signals"] if s["signal_type"] == SIGNAL_PURCHASE_CONFIRMED),
            2,
        )

    def test_e_single_key_load_plus_one_max(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_facts",
            return_value={ORDER_ID: _oef()},
        ) as batch, mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_fact",
        ) as single, mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            return_value=_purchase(),
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            payload = load_commerce_signals_for_recovery_key(
                store_slug=STORE,
                recovery_key=RK,
                force=True,
            )
        self.assertEqual(batch.call_count, 1)
        single.assert_not_called()
        self.assertEqual(list(batch.call_args.kwargs["external_order_ids"]), [ORDER_ID])
        self.assertEqual(_oef_refs(_purchase_signal(payload["signals"]))[0]["paid_amount"], PAID_AMOUNT)

    def test_f_cross_store_oef_never_attaches(self) -> None:
        foreign = _oef(store_slug=OTHER, external_order_id=ORDER_ID, id=99)
        payload, batch, _single = self._load_store(
            purchases_by_key={RK: _purchase()},
            facts={ORDER_ID: foreign},
            keys=[RK],
        )
        self.assertEqual(batch.call_count, 1)
        confirmed = _purchase_signal(payload["signals"])
        self.assertEqual(_oef_refs(confirmed), [])
        self.assertNotIn(PAID_AMOUNT, str(confirmed))

    def test_g_missing_oef_preserves_purchase_confirmed(self) -> None:
        payload, batch, _single = self._load_store(
            purchases_by_key={RK: _purchase()},
            facts={},
            keys=[RK],
        )
        self.assertEqual(batch.call_count, 1)
        confirmed = _purchase_signal(payload["signals"])
        self.assertEqual(confirmed["signal_type"], SIGNAL_PURCHASE_CONFIRMED)
        self.assertEqual(_oef_refs(confirmed), [])
        self.assertNotIn("paid_amount", str(confirmed))
        self.assertNotIn(CART_VALUE, str(confirmed))

    def test_h_21_sar_order_74436306_evidence_shape_identical(self) -> None:
        signals = build_commerce_signals_v1(
            store_slug=STORE,
            recovery_key=RK,
            purchase=_purchase(),
            order_economic_fact=_oef(),
            force=True,
        )
        confirmed = _purchase_signal(signals)
        self.assertEqual(set(confirmed.keys()), {
            "signal_type",
            "subject",
            "observed_at",
            "source",
            "evidence_refs",
        })
        self.assertEqual(_oef_refs(confirmed), [EXPECTED_OEF_REF])
        self.assertNotIn(CART_VALUE, str(confirmed))

    def test_i_j_merchant_reads_do_not_invoke_create_all_or_inspect(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.db.session.query",
            side_effect=_empty_query,
        ), mock.patch(
            "services.order_economic_fact_v1.persist.ensure_order_economic_fact_schema",
        ) as ensure_persist, mock.patch(
            "schema_order_economic_fact_v1.ensure_order_economic_fact_schema",
        ) as ensure_schema, mock.patch(
            "extensions.db.create_all",
        ) as create_all, mock.patch(
            "schema_order_economic_fact_v1.inspect",
        ) as inspect_schema, mock.patch(
            "services.cartflow_purchase_truth.purchase_context",
            return_value=_purchase(),
        ), mock.patch(
            "services.recovery_truth_timeline_v1.get_recovery_truth_timeline",
            return_value=[],
        ):
            store_payload = load_store_commerce_signals_v1(
                store_slug=STORE,
                force=True,
                recovery_keys=[RK],
            )
            key_payload = load_commerce_signals_for_recovery_key(
                store_slug=STORE,
                recovery_key=RK,
                force=True,
            )
        ensure_persist.assert_not_called()
        ensure_schema.assert_not_called()
        create_all.assert_not_called()
        inspect_schema.assert_not_called()
        self.assertEqual(_oef_refs(_purchase_signal(store_payload["signals"])), [])
        self.assertEqual(_oef_refs(_purchase_signal(key_payload["signals"])), [])

    def test_build_does_not_query_oef(self) -> None:
        with mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_facts",
        ) as batch, mock.patch(
            "services.order_economic_fact_v1.persist.get_order_economic_fact",
        ) as single:
            signals = build_commerce_signals_v1(
                store_slug=STORE,
                recovery_key=RK,
                purchase=_purchase(),
                force=True,
            )
        batch.assert_not_called()
        single.assert_not_called()
        self.assertEqual(_oef_refs(_purchase_signal(signals)), [])


if __name__ == "__main__":
    unittest.main()
