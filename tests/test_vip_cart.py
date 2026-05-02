# -*- coding: utf-8 -*-
from __future__ import annotations

from types import SimpleNamespace

from services.vip_cart import (
    apply_vip_cart_threshold_from_body,
    is_vip_cart,
    vip_cart_threshold_fields_for_api,
)


def test_is_vip_cart_disabled_when_no_threshold() -> None:
    store = SimpleNamespace(vip_cart_threshold=None)
    assert is_vip_cart(9999.0, store) is False


def test_is_vip_cart_true_when_meets_threshold() -> None:
    store = SimpleNamespace(vip_cart_threshold=500)
    assert is_vip_cart(500.0, store) is True
    assert is_vip_cart(600, store) is True


def test_is_vip_cart_false_below_threshold() -> None:
    store = SimpleNamespace(vip_cart_threshold=500)
    assert is_vip_cart(499.99, store) is False


def test_apply_vip_cart_threshold_clears() -> None:
    row = SimpleNamespace(vip_cart_threshold=100)
    apply_vip_cart_threshold_from_body(row, {"vip_cart_threshold": None})
    assert row.vip_cart_threshold is None


def test_apply_vip_cart_threshold_empty_string() -> None:
    row = SimpleNamespace(vip_cart_threshold=100)
    apply_vip_cart_threshold_from_body(row, {"vip_cart_threshold": "  "})
    assert row.vip_cart_threshold is None


def test_apply_vip_cart_threshold_sets_int() -> None:
    row = SimpleNamespace(vip_cart_threshold=None)
    apply_vip_cart_threshold_from_body(row, {"vip_cart_threshold": 750})
    assert row.vip_cart_threshold == 750


def test_apply_vip_cart_threshold_zero_disables() -> None:
    row = SimpleNamespace(vip_cart_threshold=100)
    apply_vip_cart_threshold_from_body(row, {"vip_cart_threshold": 0})
    assert row.vip_cart_threshold is None


def test_vip_cart_threshold_fields_for_api() -> None:
    assert vip_cart_threshold_fields_for_api(None) == {"vip_cart_threshold": None}
    assert vip_cart_threshold_fields_for_api(SimpleNamespace(vip_cart_threshold=300)) == {
        "vip_cart_threshold": 300,
    }
