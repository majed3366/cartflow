# -*- coding: utf-8 -*-
"""Order Economic Fact V1 — fail-closed paid-order money."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest

from extensions import db
from integrations.adapters.zid import ZidAdapter
from integrations.zid_order_economic_v1 import map_zid_order_view_to_economic_candidate
from models import OrderEconomicFact, PurchaseTruthRecord, Store, StoreIdentityAlias
from schema_order_economic_fact_v1 import reset_order_economic_fact_schema_guard_for_tests
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import reset_purchase_truth_foundation_for_tests
from services.order_economic_fact_v1.aggregates import gross_paid_order_aov, store_paid_order_value
from services.order_economic_fact_v1.backfill import backfill_order_economic_facts
from services.order_economic_fact_v1.capture import capture_after_platform_paid
from services.order_economic_fact_v1.contract import (
    SAFE_AGGREGATE_TERM,
    SAFE_AOV_TERM,
    SAFE_MERCHANT_TERM,
    TRUTH_VERSION,
    CanonicalOrderEconomicFact,
)
from services.order_economic_fact_v1.persist import get_order_economic_fact, persist_order_economic_fact
from services.purchase_truth import ingest_purchase_truth
from services.store_identity_v1 import ALIAS_KIND_ZID_NUMERIC_ID, PLATFORM_ZID
from services.zid_webhook_purchase_v2 import SOURCE_ZID_PLATFORM_PAID


PAID_ORDER_ID = "74389634"
ZID_NUMERIC = "3121837"


def paid_view_74389634(**overrides: object) -> dict:
    body: dict = {
        "id": 74389634,
        "store_id": 3121837,
        "payment_status": "paid",
        "order_total": 21,
        "transaction_amount": 21,
        "currency_code": "SAR",
        "currency": {"order_currency": {"code": "SAR"}},
        "coupon": None,
        "payment_summary": {"paid_amount": 21, "remaining_amount": 0, "total": 21},
        "payment": {
            "invoice": [
                {"code": "sub_totals", "value": 1},
                {"code": "shipping", "value": 20},
                {"code": "total", "value": 21},
            ],
            "method": {"code": "zid_bank_transfer"},
        },
        "products": [{"tax_amount": 0, "total": 1}],
    }
    body.update(overrides)
    return body


def pending_view_68459818() -> dict:
    return {
        "id": 68459818,
        "store_id": 3121837,
        "payment_status": "pending",
        "order_total": 11523,
        "transaction_amount": 11523,
        "currency": {"order_currency": {"code": "SAR"}},
        "payment_summary": {"paid_amount": 0, "remaining_amount": 11523},
        "payment": {
            "invoice": [
                {"code": "sub_totals_before_vat", "value": 10020},
                {"code": "shipping", "value": 20},
                {"code": "vat", "value": 1503},
            ]
        },
    }


def _reset() -> None:
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    reset_order_economic_fact_schema_guard_for_tests()
    try:
        db.session.query(OrderEconomicFact).delete()
        db.session.query(PurchaseTruthRecord).delete()
        lab_stores = (
            db.session.query(Store).filter(Store.zid_store_id.like("oef-%")).all()
        )
        lab_ids = [s.id for s in lab_stores]
        if lab_ids:
            db.session.query(StoreIdentityAlias).filter(
                StoreIdentityAlias.store_id.in_(lab_ids)
            ).delete(synchronize_session=False)
            db.session.query(Store).filter(Store.id.in_(lab_ids)).delete(
                synchronize_session=False
            )
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


def _slug() -> str:
    return f"oef-{uuid.uuid4().hex[:10]}"


def _store(slug: str, *, numeric: str) -> Store:
    row = Store(
        zid_store_id=slug,
        access_token="mgr-token",
        zid_authorization_token="auth-token",
        is_active=True,
    )
    db.session.add(row)
    db.session.commit()
    db.session.add(
        StoreIdentityAlias(
            store_id=row.id,
            alias_kind=ALIAS_KIND_ZID_NUMERIC_ID,
            alias_value=numeric,
            platform=PLATFORM_ZID,
        )
    )
    db.session.commit()
    return row


def _lab(*, numeric: str | None = None) -> tuple[str, str, dict]:
    slug = _slug()
    nid = numeric or str(3_000_000 + uuid.uuid4().int % 900_000)
    _store(slug, numeric=nid)
    body = paid_view_74389634(store_id=int(nid))
    return slug, nid, body


def _ingest_platform_paid(slug: str, order_id: str, session_id: str = "s1") -> bool:
    return ingest_purchase_truth(
        recovery_key=f"{slug}:{session_id}",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        session_id=session_id,
        order_id=order_id,
        evidence_detail="oef-test",
        apply_lifecycle=False,
    )


def _fetch(body: dict, http: int = 200):
    def _fn(_store: object, _oid: str) -> tuple[dict, int]:
        return body, http

    return _fn


def test_extract_order_stays_empty() -> None:
    assert ZidAdapter().extract_order({}) == {}


def test_paid_paid_amount_positive() -> None:
    mapped = map_zid_order_view_to_economic_candidate(paid_view_74389634())
    assert mapped is not None
    assert mapped["paid_amount"] == "21"
    assert mapped["currency"] == "SAR"
    assert mapped["payment_state"] == "paid"
    assert mapped["order_subtotal"] == "1"
    assert mapped["customer_shipping_charge"] == "20"
    assert mapped["remaining_amount"] == "0"
    assert mapped["order_total"] == "21"
    assert mapped["transaction_amount"] == "21"
    assert mapped["discount_amount"] is None
    assert mapped["tax_amount"] is None
    assert "refund_amount" not in mapped
    assert "cart_value" not in mapped


def test_paid_remaining_zero_still_creates_fact() -> None:
    slug, _nid, body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    out = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    assert out["ok"] is True
    row = get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID)
    assert row is not None
    assert row.remaining_amount == "0"
    assert row.paid_amount == "21"


def test_pending_order_total_positive_rejected() -> None:
    assert map_zid_order_view_to_economic_candidate(pending_view_68459818()) is None


def test_paid_paid_amount_missing_rejected() -> None:
    body = paid_view_74389634()
    body["payment_summary"] = {"remaining_amount": 0}
    assert map_zid_order_view_to_economic_candidate(body) is None


def test_paid_paid_amount_zero_rejected() -> None:
    body = paid_view_74389634(payment_summary={"paid_amount": 0, "remaining_amount": 0})
    assert map_zid_order_view_to_economic_candidate(body) is None


def test_missing_currency_rejected() -> None:
    body = paid_view_74389634()
    body.pop("currency")
    body.pop("currency_code")
    assert map_zid_order_view_to_economic_candidate(body) is None


def test_currency_mismatch_rejected() -> None:
    body = paid_view_74389634(currency_code="USD")
    assert map_zid_order_view_to_economic_candidate(body) is None


def test_shipping_absent_nullable() -> None:
    body = paid_view_74389634()
    body["payment"]["invoice"] = [{"code": "sub_totals", "value": 1}, {"code": "total", "value": 21}]
    mapped = map_zid_order_view_to_economic_candidate(body)
    assert mapped is not None
    assert mapped["customer_shipping_charge"] is None
    assert mapped["order_subtotal"] == "1"


def test_discount_null_stays_null() -> None:
    mapped = map_zid_order_view_to_economic_candidate(paid_view_74389634(coupon=None))
    assert mapped is not None
    assert mapped["discount_amount"] is None


def test_tax_absent_stays_null_not_line_zero() -> None:
    mapped = map_zid_order_view_to_economic_candidate(paid_view_74389634())
    assert mapped is not None
    assert mapped["tax_amount"] is None


def test_sub_totals_before_vat_is_not_subtotal() -> None:
    body = paid_view_74389634()
    body["payment"]["invoice"] = [
        {"code": "sub_totals_before_vat", "value": 10020},
        {"code": "shipping", "value": 20},
    ]
    mapped = map_zid_order_view_to_economic_candidate(body)
    assert mapped is not None
    assert mapped["order_subtotal"] is None
    assert mapped["customer_shipping_charge"] == "20"


def test_refund_unknown_no_zero_column() -> None:
    assert not hasattr(OrderEconomicFact, "refund_amount")
    mapped = map_zid_order_view_to_economic_candidate(paid_view_74389634())
    assert mapped is not None
    assert "refund_amount" not in mapped


def test_user_claim_excluded(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    def spy(**kwargs: object) -> dict:
        calls.append(dict(kwargs))
        return {"ok": False, "reason": "spy"}

    monkeypatch.setattr(
        "services.order_economic_fact_v1.capture.capture_after_platform_paid",
        spy,
    )
    slug = _slug()
    ok = ingest_purchase_truth(
        recovery_key=f"{slug}:claim",
        purchase_source="reply_purchase_claim",
        store_slug=slug,
        session_id="claim",
        order_id="ORD-CLAIM",
        apply_lifecycle=False,
    )
    assert ok is True
    assert calls == []
    assert get_order_economic_fact(store_slug=slug, external_order_id="ORD-CLAIM") is None


def test_pre_purchase_excluded() -> None:
    slug, _nid, body = _lab()
    ok = ingest_purchase_truth(
        recovery_key=f"{slug}:created",
        purchase_source="order_created",
        store_slug=slug,
        session_id="created",
        order_id="ORD-CREATED",
        apply_lifecycle=False,
    )
    assert ok is True
    out = capture_after_platform_paid(
        purchase_source="order_created",
        store_slug=slug,
        external_order_id="ORD-CREATED",
        fetch_order_view=_fetch({**body, "id": "ORD-CREATED"}),
    )
    assert out["reason"] == "not_platform_paid"
    assert get_order_economic_fact(store_slug=slug, external_order_id="ORD-CREATED") is None


def test_duplicate_paid_webhook_one_fact() -> None:
    slug, _nid, body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID, "s-a")
    first = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    second = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    assert first["ok"] and second["ok"]
    n = (
        db.session.query(OrderEconomicFact)
        .filter(
            OrderEconomicFact.store_slug == slug,
            OrderEconomicFact.external_order_id == PAID_ORDER_ID,
        )
        .count()
    )
    assert n == 1


def test_bridge_recovery_key_does_not_duplicate_money() -> None:
    slug, _nid, body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID, "rk-1")
    capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    bridged = ingest_purchase_truth(
        recovery_key=f"{slug}:rk-2",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        session_id="rk-2",
        order_id=PAID_ORDER_ID,
        apply_lifecycle=False,
    )
    assert bridged is True
    row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == f"{slug}:rk-2")
        .first()
    )
    assert row is not None
    assert row.purchase_source == "zid_webhook:platform_paid_bridge"
    n = (
        db.session.query(OrderEconomicFact)
        .filter(OrderEconomicFact.store_slug == slug, OrderEconomicFact.external_order_id == PAID_ORDER_ID)
        .count()
    )
    assert n == 1


def test_same_order_replay_one_grain() -> None:
    slug, _nid, body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(body),
    )
    assert (
        db.session.query(OrderEconomicFact)
        .filter(OrderEconomicFact.store_slug == slug)
        .count()
        == 1
    )


def test_cross_tenant_order_id_rejected() -> None:
    slug = _slug()
    foreign = str(8_000_000 + uuid.uuid4().int % 900_000)
    _store(slug, numeric=foreign)
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    out = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch(paid_view_74389634()),
    )
    assert out["ok"] is False
    assert out["reason"] == "cross_tenant_rejected"
    assert get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID) is None
    assert (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.store_slug == slug, PurchaseTruthRecord.order_id == PAID_ORDER_ID)
        .count()
        == 1
    )


def test_manager_get_401_leaves_purchase_truth() -> None:
    slug, _nid, _body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    out = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch({"error": "unauthenticated"}, 401),
    )
    assert out == {"ok": False, "reason": "manager_unauthorized", "http": 401}
    assert get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID) is None
    assert (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.store_slug == slug, PurchaseTruthRecord.order_id == PAID_ORDER_ID)
        .first()
        is not None
    )


def test_manager_get_timeout_leaves_purchase_truth() -> None:
    slug, _nid, _body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)

    def boom(_store: object, _oid: str) -> tuple[dict, int]:
        raise TimeoutError("manager timeout")

    out = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=boom,
    )
    assert out["ok"] is False
    assert out["reason"] == "manager_timeout"
    assert get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID) is None


def test_order_detail_404_leaves_purchase_truth() -> None:
    slug, _nid, _body = _lab()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID)
    out = capture_after_platform_paid(
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        external_order_id=PAID_ORDER_ID,
        fetch_order_view=_fetch({"error": "not_found"}, 404),
    )
    assert out["reason"] == "order_not_found"
    assert get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID) is None


def test_ingest_without_store_keeps_purchase_truth() -> None:
    slug = _slug()
    assert _ingest_platform_paid(slug, PAID_ORDER_ID) is True
    assert get_order_economic_fact(store_slug=slug, external_order_id=PAID_ORDER_ID) is None
    row = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == f"{slug}:s1")
        .first()
    )
    assert row is not None
    assert row.purchase_source == SOURCE_ZID_PLATFORM_PAID


def test_canonical_dedupe_is_store_and_order_not_recovery_key() -> None:
    slug = _slug()
    now = datetime.now(timezone.utc)
    persist_order_economic_fact(
        CanonicalOrderEconomicFact(
            store_slug=slug,
            external_order_id=PAID_ORDER_ID,
            platform="zid",
            payment_state="paid",
            currency="SAR",
            paid_amount="21",
            observed_at=now,
            source="zid_manager_order_view",
        )
    )
    persist_order_economic_fact(
        CanonicalOrderEconomicFact(
            store_slug=slug,
            external_order_id=PAID_ORDER_ID,
            platform="zid",
            payment_state="paid",
            currency="SAR",
            paid_amount="21",
            observed_at=now,
            source="zid_manager_order_view",
        )
    )
    assert (
        db.session.query(OrderEconomicFact)
        .filter(OrderEconomicFact.store_slug == slug, OrderEconomicFact.external_order_id == PAID_ORDER_ID)
        .count()
        == 1
    )


def test_aov_and_store_value_same_currency_explicit_window() -> None:
    slug = _slug()
    now = datetime.now(timezone.utc)
    persist_order_economic_fact(
        CanonicalOrderEconomicFact(
            store_slug=slug,
            external_order_id="1",
            platform="zid",
            payment_state="paid",
            currency="SAR",
            paid_amount="21",
            observed_at=now,
            source="zid_manager_order_view",
        )
    )
    persist_order_economic_fact(
        CanonicalOrderEconomicFact(
            store_slug=slug,
            external_order_id="2",
            platform="zid",
            payment_state="paid",
            currency="SAR",
            paid_amount="10",
            observed_at=now,
            source="zid_manager_order_view",
        )
    )
    persist_order_economic_fact(
        CanonicalOrderEconomicFact(
            store_slug=slug,
            external_order_id="3",
            platform="zid",
            payment_state="paid",
            currency="USD",
            paid_amount="99",
            observed_at=now,
            source="zid_manager_order_view",
        )
    )
    start = now - timedelta(hours=1)
    end = now + timedelta(hours=1)
    rolled = store_paid_order_value(
        store_slug=slug, currency="SAR", window_start=start, window_end=end
    )
    aov = gross_paid_order_aov(
        store_slug=slug, currency="SAR", window_start=start, window_end=end
    )
    assert rolled is not None
    assert rolled["term"] == SAFE_AGGREGATE_TERM
    assert rolled["paid_order_value"] == "31"
    assert rolled["distinct_orders"] == 2
    assert rolled["net_revenue"] is False
    assert aov is not None
    assert aov["term"] == SAFE_AOV_TERM
    assert aov["gross_paid_order_aov"] == "15.5"
    assert aov["net_aov"] is False
    assert SAFE_MERCHANT_TERM == "قيمة الطلب المدفوع"
    assert "صافي" not in SAFE_MERCHANT_TERM
    assert "ربح" not in SAFE_AGGREGATE_TERM


def test_aov_requires_explicit_window() -> None:
    slug = _slug()
    now = datetime.now(timezone.utc)
    assert (
        gross_paid_order_aov(
            store_slug=slug,
            currency="SAR",
            window_start=now,
            window_end=now,
        )
        is None
    )


def test_backfill_dry_run_excludes_user_claim_and_does_not_execute() -> None:
    slug = _slug()
    ingest_purchase_truth(
        recovery_key=f"{slug}:paid",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug=slug,
        session_id="paid",
        order_id="ORD-BF-1",
        apply_lifecycle=False,
    )
    ingest_purchase_truth(
        recovery_key=f"{slug}:claim",
        purchase_source="reply_purchase_claim",
        store_slug=slug,
        session_id="claim",
        order_id="ORD-CLAIM-BF",
        apply_lifecycle=False,
    )
    plan = backfill_order_economic_facts(store_slug=slug, execute=False)
    assert plan["execute"] is False
    assert "ORD-BF-1" in plan["eligible"]
    assert "ORD-CLAIM-BF" not in plan["eligible"]
    assert plan["ran"] == []


def test_safe_terms_forbid_net_revenue() -> None:
    assert SAFE_MERCHANT_TERM == "قيمة الطلب المدفوع"
    assert SAFE_AGGREGATE_TERM == "قيمة الطلبات المدفوعة"
    for term in (SAFE_MERCHANT_TERM, SAFE_AGGREGATE_TERM, SAFE_AOV_TERM):
        assert "صافي الإيراد" not in term
        assert "الربح" not in term
        assert "صافي ما يحتفظ به المتجر" not in term


def test_model_has_no_refund_and_truth_version_grain() -> None:
    cols = {c.name for c in OrderEconomicFact.__table__.columns}
    assert "refund_amount" not in cols
    assert "paid_amount" in cols
    assert "truth_version" in cols
    assert TRUTH_VERSION == "oef_v1"
