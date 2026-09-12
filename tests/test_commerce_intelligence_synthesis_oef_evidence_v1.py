# -*- coding: utf-8 -*-
"""CISYN OEF evidence preservation V1 — lineage only, no Knowledge/Guidance."""
from __future__ import annotations

import inspect
import json
from datetime import datetime, timedelta

import pytest

from extensions import db
from models import CommerceIntelligenceSynthesis, Store
from schema_commerce_intelligence_synthesis_v1 import (
    reset_commerce_intelligence_synthesis_schema_guard_for_tests,
)
from schema_store_identity import ensure_store_identity_schema
from services.product_data import commerce_intelligence_synthesis_foundation_v1 as cisyn
from services.product_data.commerce_intelligence_synthesis_flag_v1 import (
    ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1,
)
from services.product_data.commerce_intelligence_synthesis_foundation_v1 import (
    REF_TYPE_ORDER_ECONOMIC_FACT,
    SIGNAL_PURCHASE_CONFIRMED,
    _collect_oef_evidence_from_purchase_signals,
    generate_commerce_intelligence_syntheses_v1,
)
from services.product_data.commerce_intelligence_synthesis_rule_registry_v1 import (
    synthesis_rule_by_key_v1,
)
from services.store_identity_v1 import (
    ALIAS_KIND_CARTFLOW_ZID,
    register_store_identity_alias,
)
from tests.test_recovery_isolation import _reset_recovery_memory

STORE = "cartflow-42b491"
RECOVERY_KEY = "cartflow-42b491:74436306"
OEF_ID = 1
PAID_AMOUNT = "21"
CURRENCY = "SAR"
AS_OF = datetime(2026, 9, 12, 2, 0, 0)


def _reset_tables() -> None:
    for model in (CommerceIntelligenceSynthesis, Store):
        try:
            db.session.query(model).delete()
            db.session.commit()
        except Exception:  # noqa: BLE001
            db.session.rollback()
    reset_commerce_intelligence_synthesis_schema_guard_for_tests()


@pytest.fixture(autouse=True)
def _isolate_db(monkeypatch: pytest.MonkeyPatch) -> None:
    _reset_recovery_memory()
    monkeypatch.setenv(ENV_COMMERCE_INTELLIGENCE_SYNTHESIS_V1, "1")
    _reset_tables()
    db.create_all()
    ensure_store_identity_schema(db)
    yield
    _reset_tables()


def _seed_store(slug: str = STORE) -> str:
    store = Store(zid_store_id=slug, vip_cart_threshold=1000)
    db.session.add(store)
    db.session.commit()
    register_store_identity_alias(
        store_id=int(store.id),
        alias_kind=ALIAS_KIND_CARTFLOW_ZID,
        alias_value=slug,
        platform="cartflow",
    )
    return slug


def _oef_ref(**overrides: object) -> dict:
    ref = {
        "ref_type": REF_TYPE_ORDER_ECONOMIC_FACT,
        "id": OEF_ID,
        "recovery_key": RECOVERY_KEY,
        "paid_amount": PAID_AMOUNT,
        "currency": CURRENCY,
    }
    ref.update(overrides)
    return ref


def _purchase(*, refs: list | None = None, **extra: object) -> dict:
    payload = {
        "signal_type": SIGNAL_PURCHASE_CONFIRMED,
        "subject": {
            "kind": "cart_recovery",
            "store_slug": STORE,
            "recovery_key": RECOVERY_KEY,
        },
        "observed_at": "2026-09-11T23:13:35+00:00",
        "source": "zid_webhook:platform_paid",
        "evidence_refs": list(refs if refs is not None else [_oef_ref()]),
    }
    payload.update(extra)
    return payload


def _recovery(i: int = 0) -> dict:
    return {
        "signal_type": "recovery_started",
        "subject": {
            "kind": "cart_recovery",
            "store_slug": STORE,
            "recovery_key": f"{STORE}:rk{i}",
        },
        "observed_at": "2026-09-11T23:00:00+00:00",
        "source": "recovery_truth_timeline",
        "evidence_refs": [
            {
                "ref_type": "recovery_truth_timeline_event",
                "id": i,
                "status": "scheduled",
                "recovery_key": f"{STORE}:rk{i}",
            }
        ],
    }


def _base_sources(slug: str, signals: list) -> dict:
    return {
        "ok": True,
        "store_slug": slug,
        "time_window_key": "d7",
        "window_start": (AS_OF - timedelta(days=7)).isoformat(sep=" "),
        "window_end": AS_OF.isoformat(sep=" "),
        "as_of": AS_OF.isoformat(sep=" "),
        "knowledge_window": "d7",
        "sources": {
            "knowledge": {
                "ok": True,
                "contract_key": "generate_knowledge_v1",
                "statements": [],
                "statement_count": 0,
                "canonical_fingerprint": "kf",
            },
            "product_hesitation": {
                "ok": True,
                "contract_key": "product_hesitation_mapping_read_v1",
                "store_mapping_count": 0,
                "shipping_hesitation_rows": [],
                "shipping_hesitation_count": 0,
            },
            "product_purchase": {
                "ok": True,
                "contract_key": "product_purchase_mapping_read_v1",
                "store_purchase_mapping_count": 0,
            },
            "commerce_signals": {
                "ok": True,
                "contract_key": "load_store_commerce_signals_v1",
                "signals": signals,
                "signal_count": len(signals),
                "enabled": True,
            },
        },
        "rejected_inputs": [],
        "unsupported_input_reasons": {},
        "available_source_domains": ["knowledge", "commerce_signals"],
        "missing_source_domains": ["product_hesitation", "product_purchase"],
        "errors": [],
    }


def _generate(monkeypatch: pytest.MonkeyPatch, signals: list) -> dict:
    slug = _seed_store()
    monkeypatch.setattr(
        cisyn,
        "load_synthesis_sources_v1",
        lambda *a, **k: _base_sources(slug, signals),
    )
    return generate_commerce_intelligence_syntheses_v1(
        slug, time_window_key="d7", as_of=AS_OF
    )


def _row(report: dict, rule_key: str) -> dict:
    matches = [
        s for s in report["syntheses"] if s["synthesis_rule_key"] == rule_key
    ]
    assert matches
    return matches[0]


def _money_blob(row: dict) -> str:
    return json.dumps(
        {
            "known": row.get("known_facts") or [],
            "unknown": row.get("unknown_facts") or [],
            "summary": row.get("synthesis_summary_key") or "",
            "prohibited": row.get("prohibited_claims") or [],
        },
        ensure_ascii=False,
    )


def test_helper_preserves_canonical_oef_shape() -> None:
    refs = _collect_oef_evidence_from_purchase_signals([_purchase()])
    assert refs == [
        {
            "ref_type": REF_TYPE_ORDER_ECONOMIC_FACT,
            "id": OEF_ID,
            "paid_amount": PAID_AMOUNT,
            "currency": CURRENCY,
            "recovery_key": RECOVERY_KEY,
        }
    ]


def test_helper_fail_closed_invalid_and_non_oef() -> None:
    signals = [
        _purchase(refs=[_oef_ref(paid_amount="not-a-number")]),
        _purchase(refs=[_oef_ref(paid_amount="0")]),
        _purchase(refs=[_oef_ref(paid_amount="-5")]),
        _purchase(refs=[_oef_ref(currency="")]),
        _purchase(refs=[_oef_ref(id="")]),
        _purchase(
            refs=[
                {
                    "ref_type": "purchase_truth_record",
                    "id": 1168,
                    "paid_amount": "99",
                    "currency": "SAR",
                    "cart_value": 999,
                }
            ]
        ),
        _purchase(refs=[{"ref_type": "abandoned_cart", "cart_value": 50}]),
        {"signal_type": "recovery_completed", "evidence_refs": [_oef_ref()]},
    ]
    assert _collect_oef_evidence_from_purchase_signals(signals) == []


def test_valid_oef_preserved_on_both_signal_evaluators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _generate(
        monkeypatch,
        [_recovery(0), _recovery(1), _recovery(2), _purchase()],
    )
    influence = _row(report, "recovery_influence_boundary")
    whatsapp = _row(report, "whatsapp_return_without_purchase")
    for row in (influence, whatsapp):
        contrib = row["source_contributions"][REF_TYPE_ORDER_ECONOMIC_FACT]
        assert contrib["supporting_records"] == 1
        assert contrib["role"] == "verified_paid_order_money"
        assert contrib["refs"][0]["id"] == OEF_ID
        assert contrib["refs"][0]["paid_amount"] == PAID_AMOUNT
        assert contrib["refs"][0]["currency"] == CURRENCY
        assert contrib["refs"][0]["ref_type"] == REF_TYPE_ORDER_ECONOMIC_FACT
        assert "oef:1" in row["source_record_ids"]


def test_known_facts_and_copy_have_no_oef_money(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _generate(monkeypatch, [_purchase()])
    influence = _row(report, "recovery_influence_boundary")
    blob = _money_blob(influence)
    assert "paid_amount" not in blob
    assert PAID_AMOUNT not in blob
    assert CURRENCY not in blob
    assert "order_economic_fact" not in blob
    assert "ريال" not in blob
    assert "recommend" not in blob.lower()
    assert any(
        str(item).startswith("purchase_confirmed_signals=1")
        for item in influence["known_facts"]
    )


def test_missing_oef_keeps_count_behavior(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bare = _purchase(refs=[{"ref_type": "purchase_truth_record", "id": 1168}])
    report = _generate(monkeypatch, [bare])
    influence = _row(report, "recovery_influence_boundary")
    assert influence["source_contributions"].get("purchase_truth", {}).get(
        "supporting_records"
    ) == 1
    assert REF_TYPE_ORDER_ECONOMIC_FACT not in influence["source_contributions"]
    assert not any(
        str(i).startswith("oef:") for i in influence["source_record_ids"]
    )
    assert any(
        str(item).startswith("purchase_confirmed_signals=1")
        for item in influence["known_facts"]
    )


@pytest.mark.parametrize(
    "bad_ref",
    [
        _oef_ref(paid_amount="abc"),
        _oef_ref(paid_amount="0"),
        _oef_ref(paid_amount="-1"),
        _oef_ref(currency=""),
        _oef_ref(currency="   "),
        _oef_ref(id=None),
    ],
)
def test_invalid_oef_fail_closed(
    monkeypatch: pytest.MonkeyPatch, bad_ref: dict
) -> None:
    if bad_ref.get("id") is None:
        bad_ref = dict(bad_ref)
        bad_ref.pop("id", None)
    report = _generate(monkeypatch, [_purchase(refs=[bad_ref])])
    influence = _row(report, "recovery_influence_boundary")
    assert REF_TYPE_ORDER_ECONOMIC_FACT not in influence["source_contributions"]
    assert any(
        str(item).startswith("purchase_confirmed_signals=1")
        for item in influence["known_facts"]
    )


def test_cart_value_is_not_monetary_truth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _generate(
        monkeypatch,
        [
            _purchase(
                refs=[
                    {
                        "ref_type": "purchase_truth_record",
                        "id": 1168,
                        "cart_value": 999,
                        "paid_amount": "999",
                        "currency": "SAR",
                    }
                ]
            )
        ],
    )
    influence = _row(report, "recovery_influence_boundary")
    assert REF_TYPE_ORDER_ECONOMIC_FACT not in influence["source_contributions"]
    blob = json.dumps(influence["source_contributions"])
    assert "999" not in blob
    assert "cart_value" not in blob


def test_direct_evaluators_do_not_query_or_change_counts() -> None:
    rule_inf = synthesis_rule_by_key_v1("recovery_influence_boundary")
    rule_wa = synthesis_rule_by_key_v1("whatsapp_return_without_purchase")
    assert rule_inf and rule_wa
    sources = _base_sources(
        STORE,
        [_recovery(0), _recovery(1), _recovery(2), _purchase()],
    )
    window_start = AS_OF - timedelta(days=7)
    influence = cisyn._eval_recovery_influence(
        rule_inf,
        store_slug=STORE,
        sources=sources,
        available={"commerce_signals"},
        window_start=window_start,
        window_end=AS_OF,
        time_window_key="d7",
    )[0]
    whatsapp = cisyn._eval_whatsapp_return(
        rule_wa,
        store_slug=STORE,
        sources=sources,
        available={"commerce_signals"},
        window_start=window_start,
        window_end=AS_OF,
        time_window_key="d7",
    )[0]
    assert influence["sample_size"] == 1
    assert influence["source_contributions"]["purchase_truth"][
        "supporting_records"
    ] == 1
    assert whatsapp["source_contributions"]["commerce_signals_purchase"][
        "supporting_records"
    ] == 1
    src = inspect.getsource(cisyn)
    assert "get_order_economic_fact" not in src
    assert "AbandonedCart" not in src
    assert "cart_value" not in src


def test_foundation_does_not_import_oef_persist() -> None:
    src = inspect.getsource(cisyn)
    assert "order_economic_fact_v1.persist" not in src
    assert "load_recovered_cart_values_by_key" not in src
