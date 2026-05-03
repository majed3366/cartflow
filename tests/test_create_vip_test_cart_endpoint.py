# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_create_vip_test_cart_returns_ok_shape(client):
    r = client.post("/dev/create-vip-test-cart")
    assert r.status_code == 200, r.text
    b = r.json()
    assert b.get("ok") is True
    assert b.get("vip") is True
    assert b.get("cart_id") == "vip-codegen-test-cart-1"


def test_create_vip_test_cart_idempotent_repost(client):
    r1 = client.post("/dev/create-vip-test-cart")
    r2 = client.post("/dev/create-vip-test-cart")
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json().get("cart_id") == r2.json().get("cart_id")
