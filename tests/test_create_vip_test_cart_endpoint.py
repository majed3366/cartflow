# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from extensions import db
from fastapi.testclient import TestClient

from main import app
from models import CartRecoveryLog


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


@pytest.mark.parametrize("method", ("get", "post"))
def test_create_vip_test_cart_idempotent_repost(client, method):
    fn = getattr(client, method)
    r1 = fn("/dev/create-vip-test-cart")
    r2 = fn("/dev/create-vip-test-cart")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json().get("cart_id") == r2.json().get("cart_id")
