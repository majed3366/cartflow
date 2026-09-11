# -*- coding: utf-8 -*-
from services import zid_webhook_purchase_v2 as zid_paid


def test_observed_root_paid_delivery_builds_canonical_purchase(monkeypatch):
    monkeypatch.setattr(
        zid_paid,
        "_canonical_store_slug_from_identifier",
        lambda raw: "cartflow-42b491" if str(raw) == "3121837" else "",
    )

    payload = {
        "id": 900001,
        "store_id": 3121837,
        "payment_status": "paid",
    }

    out = zid_paid.build_zid_purchase_truth_payload(payload)

    assert out is not None
    assert out["store_slug"] == "cartflow-42b491"
    assert out["store"] == "cartflow-42b491"
    assert out["order_id"] == "900001"
    assert out["session_id"] == "zid-order:900001"
    assert out["event"] == zid_paid.ZID_PLATFORM_PAID_EVENT
    assert out["payment_status"] == "paid"
    assert out["_zid_platform_paid"] is True


def test_observed_root_delivery_stays_fail_closed():
    assert zid_paid.zid_payload_indicates_platform_paid(
        {"id": 1, "store_id": 3121837, "payment_status": "pending"}
    ) is False
    assert zid_paid.zid_payload_indicates_platform_paid(
        {"id": 1, "payment_status": "paid"}
    ) is False
    assert zid_paid.zid_payload_indicates_platform_paid(
        {"store_id": 3121837, "payment_status": "paid"}
    ) is False
    assert zid_paid.zid_payload_indicates_platform_paid(
        {
            "event": "order.created",
            "id": 1,
            "store_id": 3121837,
            "payment_status": "paid",
        }
    ) is False
    assert zid_paid.zid_payload_indicates_platform_paid(
        {
            "order": {"id": 1, "store_id": 3121837, "payment_status": "paid"},
        }
    ) is False


def test_wrapped_documented_paid_event_remains_supported(monkeypatch):
    monkeypatch.setattr(
        zid_paid,
        "_canonical_store_slug_from_identifier",
        lambda raw: "cartflow-42b491" if str(raw) == "3121837" else "",
    )

    payload = {
        "event": "order.payment_status.update",
        "data": {
            "order": {
                "id": "wrapped-1",
                "store_id": 3121837,
                "payment_status": "paid",
            }
        },
    }

    out = zid_paid.build_zid_purchase_truth_payload(payload)

    assert out is not None
    assert out["store_slug"] == "cartflow-42b491"
    assert out["order_id"] == "wrapped-1"
