# -*- coding: utf-8 -*-
from __future__ import annotations

from unittest.mock import patch

import pytest
from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import AbandonedCart, CartRecoveryLog, Store


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.mark.parametrize("method", ("get", "post"))
def test_create_vip_test_cart_returns_ok_shape(client, method):
    fn = getattr(client, method)
    r = fn("/dev/create-vip-test-cart")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b.get("ok") is True
    assert b.get("vip") is True
    assert b.get("cart_id") == "vip-codegen-test-cart-1"
    lg = (
        db.session.query(CartRecoveryLog)
        .filter(
            CartRecoveryLog.cart_id == "vip-codegen-test-cart-1",
            CartRecoveryLog.status == "vip_manual_handling",
        )
        .order_by(CartRecoveryLog.created_at.desc())
        .first()
    )
    assert lg is not None
    ac = db.session.query(AbandonedCart).filter_by(zid_cart_id="vip-codegen-test-cart-1").one()
    st_row = db.session.get(Store, ac.store_id)
    assert st_row is not None
    assert ac.store_id == st_row.id
    assert (st_row.store_whatsapp_number or "").strip() == "+966579706669"


@pytest.mark.parametrize("method", ("get", "post"))
def test_create_vip_test_cart_idempotent_repost(client, method):
    fn = getattr(client, method)
    r1 = fn("/dev/create-vip-test-cart")
    r2 = fn("/dev/create-vip-test-cart")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json().get("cart_id") == r2.json().get("cart_id")


@patch("services.whatsapp_send.send_whatsapp")
def test_create_vip_test_cart_merchant_manual_send_ok(mock_sw, client):
    mock_sw.return_value = {"ok": True, "sid": "SM_vip_dev_test"}
    r0 = client.get("/dev/create-vip-test-cart")
    assert r0.status_code == 200
    ac = db.session.query(AbandonedCart).filter_by(zid_cart_id="vip-codegen-test-cart-1").one()
    assert (db.session.get(Store, ac.store_id).store_whatsapp_number or "").strip() == "+966579706669"
    r = client.post(f"/api/dashboard/vip-cart/{ac.id}/merchant-alert", json={})
    assert r.status_code == 200, r.text
    assert r.json().get("ok") is True
    assert r.json().get("message") == "تم إرسال تنبيه التاجر"
