# -*- coding: utf-8 -*-
"""Purchase Truth Semantic Correction V1 — Zid paid contract + provenance."""
from __future__ import annotations

import uuid

import pytest

from extensions import db
from models import PurchaseTruthRecord
from schema_purchase_truth import reset_purchase_truth_schema_guard_for_tests
from services.cartflow_purchase_truth import (
    PROVENANCE_OTHER,
    PROVENANCE_PLATFORM_PAID,
    PROVENANCE_PRE_PURCHASE,
    PROVENANCE_USER_CLAIM,
    classify_purchase_provenance,
    count_authoritative_platform_paid,
    extract_purchase_evidence,
    find_authoritative_platform_paid_row,
    has_purchase,
    record_purchase,
    reset_purchase_truth_foundation_for_tests,
    stop_if_purchased,
)
from services.purchase_truth import (
    ingest_purchase_truth,
    ingest_purchase_truth_from_reply_claim,
    ingest_purchase_truth_payload,
)
from services.zid_webhook_purchase_v2 import (
    SOURCE_ZID_PLATFORM_PAID,
    SOURCE_ZID_PLATFORM_PAID_BRIDGE,
    ZID_PLATFORM_PAID_EVENT,
    build_zid_purchase_truth_payload,
    extract_zid_order_id,
    zid_payload_indicates_platform_paid,
    zid_payload_indicates_purchase,
)


def _reset() -> None:
    reset_purchase_truth_foundation_for_tests()
    reset_purchase_truth_schema_guard_for_tests()
    try:
        db.session.query(PurchaseTruthRecord).delete()
        db.session.commit()
    except Exception:  # noqa: BLE001
        db.session.rollback()


@pytest.fixture(autouse=True)
def _isolate() -> None:
    _reset()
    db.create_all()
    yield
    _reset()


def _paid(**overrides: object) -> dict:
    body: dict = {
        "event": ZID_PLATFORM_PAID_EVENT,
        "payment_status": "paid",
        "id": "ORD-CANON-1",
        "store_slug": "demo",
        "session_id": "s-paid",
    }
    body.update(overrides)
    return body


def _row(rk: str) -> PurchaseTruthRecord | None:
    return (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == rk)
        .first()
    )


def test_payment_status_update_paid_is_authoritative() -> None:
    payload = _paid()
    assert zid_payload_indicates_platform_paid(payload) is True
    assert zid_payload_indicates_purchase(payload) is True
    built = build_zid_purchase_truth_payload(payload)
    assert built is not None
    assert built["purchase_source"] == SOURCE_ZID_PLATFORM_PAID
    assert built["order_id"] == "ORD-CANON-1"
    rk = ingest_purchase_truth_payload(built)
    assert rk == "demo:s-paid"
    row = _row(rk)
    assert row is not None
    assert row.purchase_source == SOURCE_ZID_PLATFORM_PAID
    assert classify_purchase_provenance(row.purchase_source) == PROVENANCE_PLATFORM_PAID
    assert row.order_id == "ORD-CANON-1"
    assert count_authoritative_platform_paid(row.store_slug, "ORD-CANON-1") == 1
    assert has_purchase(rk) is True
    assert stop_if_purchased(rk, session_id="s-paid") is True


def test_nested_data_id_is_canonical_order_identity() -> None:
    payload = {
        "event": ZID_PLATFORM_PAID_EVENT,
        "store_slug": "demo",
        "session_id": "s-nested",
        "data": {"id": 98765, "payment_status": "paid"},
    }
    assert extract_zid_order_id(payload) == "98765"
    built = build_zid_purchase_truth_payload(payload)
    assert built is not None
    assert built["order_id"] == "98765"
    rk = ingest_purchase_truth_payload(built)
    assert rk == "demo:s-nested"
    row = _row(rk)
    assert row is not None
    assert row.order_id == "98765"


def test_payment_status_pending_is_not_authoritative() -> None:
    payload = _paid(payment_status="pending")
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None
    assert ingest_purchase_truth_payload(payload) is None
    assert count_authoritative_platform_paid("demo", "ORD-CANON-1") == 0


def test_payment_status_refunded_is_not_authoritative() -> None:
    payload = _paid(payment_status="refunded")
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None


def test_payment_status_voided_is_not_authoritative() -> None:
    payload = _paid(payment_status="voided")
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None


def test_order_created_is_pre_purchase_not_platform_paid() -> None:
    payload = {
        "store_slug": "demo",
        "session_id": "s-created",
        "order_created": True,
        "order_id": "ORD-CREATED-1",
    }
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    rk = ingest_purchase_truth_payload(payload)
    assert rk == "demo:s-created"
    row = _row(rk)
    assert row is not None
    assert classify_purchase_provenance(row.purchase_source) == PROVENANCE_PRE_PURCHASE
    assert find_authoritative_platform_paid_row("demo", "ORD-CREATED-1") is None
    assert has_purchase(rk) is True
    assert stop_if_purchased(rk, session_id="s-created") is True


def test_whatsapp_claim_is_user_claim_only() -> None:
    rk = "demo:s-wa-claim"
    written = ingest_purchase_truth_from_reply_claim(
        recovery_key=rk,
        store_slug="demo",
        session_id="s-wa-claim",
        reply_preview="تم الطلب",
        confidence="medium",
    )
    assert written is True
    row = _row(rk)
    assert row is not None
    assert row.purchase_source == "reply_purchase_claim"
    assert classify_purchase_provenance(row.purchase_source) == PROVENANCE_USER_CLAIM
    assert count_authoritative_platform_paid("demo", "") == 0
    assert has_purchase(rk) is True
    assert stop_if_purchased(rk, session_id="s-wa-claim") is True


def test_synthetic_order_paid_is_not_zid_platform_paid() -> None:
    payload = {
        "event": "order.paid",
        "store_slug": "demo",
        "session_id": "s-synth",
        "order_id": "ORD-SYNTH",
    }
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None


def test_event_substring_order_and_paid_is_not_authoritative() -> None:
    payload = {
        "event": "customer_said_order_was_paid",
        "store_slug": "demo",
        "session_id": "s-sub",
        "order_id": "ORD-SUB",
    }
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None


def test_missing_payment_status_fails_closed() -> None:
    payload = {
        "event": ZID_PLATFORM_PAID_EVENT,
        "store_slug": "demo",
        "session_id": "s-nopay",
        "id": "ORD-NOPAY",
    }
    assert zid_payload_indicates_platform_paid(payload) is False
    assert build_zid_purchase_truth_payload(payload) is None
    assert extract_purchase_evidence(payload) is None


def test_missing_order_id_fails_closed_for_platform_paid() -> None:
    payload = {
        "event": ZID_PLATFORM_PAID_EVENT,
        "payment_status": "paid",
        "store_slug": "demo",
        "session_id": "s-noid",
    }
    assert zid_payload_indicates_platform_paid(payload) is True
    assert extract_zid_order_id(payload) == ""
    assert build_zid_purchase_truth_payload(payload) is None
    written = ingest_purchase_truth(
        recovery_key="demo:s-noid",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="demo",
        session_id="s-noid",
        order_id=None,
    )
    assert written is False
    assert has_purchase("demo:s-noid") is False


def test_cross_tenant_platform_paid_is_rejected() -> None:
    written = ingest_purchase_truth(
        recovery_key="store-a:s-x",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="store-b",
        session_id="s-x",
        order_id="ORD-X",
    )
    assert written is False
    assert has_purchase("store-a:s-x") is False
    assert count_authoritative_platform_paid("store-b", "ORD-X") == 0
    assert count_authoritative_platform_paid("store-a", "ORD-X") == 0


def test_duplicate_paid_webhook_is_idempotent() -> None:
    built = build_zid_purchase_truth_payload(_paid())
    assert built is not None
    rk1 = ingest_purchase_truth_payload(built)
    rk2 = ingest_purchase_truth_payload(built)
    assert rk1 == rk2 == "demo:s-paid"
    rows = (
        db.session.query(PurchaseTruthRecord)
        .filter(PurchaseTruthRecord.recovery_key == "demo:s-paid")
        .all()
    )
    assert len(rows) == 1
    assert rows[0].purchase_source == SOURCE_ZID_PLATFORM_PAID
    assert count_authoritative_platform_paid(rows[0].store_slug, "ORD-CANON-1") == 1


def test_second_recovery_key_for_same_order_is_bridge_not_second_paid() -> None:
    first = ingest_purchase_truth(
        recovery_key="demo:s-primary",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="demo",
        session_id="s-primary",
        order_id="ORD-DUP-1",
    )
    second = ingest_purchase_truth(
        recovery_key="demo:s-bridge",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="demo",
        session_id="s-bridge",
        order_id="ORD-DUP-1",
    )
    assert first is True
    assert second is True
    primary = _row("demo:s-primary")
    bridged = _row("demo:s-bridge")
    assert primary is not None and primary.purchase_source == SOURCE_ZID_PLATFORM_PAID
    assert bridged is not None and bridged.purchase_source == SOURCE_ZID_PLATFORM_PAID_BRIDGE
    assert classify_purchase_provenance(bridged.purchase_source) == PROVENANCE_OTHER
    assert count_authoritative_platform_paid(primary.store_slug, "ORD-DUP-1") == 1
    assert has_purchase("demo:s-primary") is True
    assert has_purchase("demo:s-bridge") is True
    assert stop_if_purchased("demo:s-bridge", session_id="s-bridge") is True


def test_platform_paid_not_overwritten_by_weaker_source() -> None:
    ingest_purchase_truth(
        recovery_key="demo:s-keep",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="demo",
        session_id="s-keep",
        order_id="ORD-KEEP",
    )
    ingest_purchase_truth_from_reply_claim(
        recovery_key="demo:s-keep",
        store_slug="demo",
        session_id="s-keep",
        reply_preview="تم الطلب",
    )
    row = _row("demo:s-keep")
    assert row is not None
    assert row.purchase_source == SOURCE_ZID_PLATFORM_PAID
    assert row.order_id == "ORD-KEEP"


def test_conversion_flag_remains_other_non_authoritative() -> None:
    rk = ingest_purchase_truth_payload(
        {
            "store_slug": "demo",
            "session_id": "s-flag",
            "purchase_completed": True,
        }
    )
    assert rk == "demo:s-flag"
    row = _row(rk)
    assert row is not None
    assert classify_purchase_provenance(row.purchase_source) == PROVENANCE_OTHER
    assert has_purchase(rk) is True


def test_record_purchase_rejects_platform_paid_without_tenant_match() -> None:
    ok = record_purchase(
        recovery_key=f"other:{uuid.uuid4().hex[:8]}",
        purchase_source=SOURCE_ZID_PLATFORM_PAID,
        store_slug="demo",
        session_id="s-rej",
        order_id="ORD-REJ",
    )
    assert ok is False
