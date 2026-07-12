# -*- coding: utf-8 -*-
"""Silent Success facilitator readiness — no fake participant answers."""
from __future__ import annotations

import os

from services.cart_workspace.feature_flag_v1 import FLAG_CART_WORKSPACE_V1
from services.cart_workspace.merchant_seed_v1 import seed_merchant_comprehension_set
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1
from services.cart_workspace.silent_success_flag_v1 import (
    FLAG_SILENT_SUCCESS,
    cart_workspace_silent_success_enabled,
)


def test_silent_success_flag_default_off(monkeypatch):
    monkeypatch.delenv(FLAG_SILENT_SUCCESS, raising=False)
    assert cart_workspace_silent_success_enabled() is False


def test_silent_success_seed_is_merchant_clean():
    store = ShadowStoreV1()
    out = seed_merchant_comprehension_set("silent-p1", store)
    proj = out["snapshot"]["projection"]
    assert len(proj["zone_a"]) == 1
    assert len(proj["zone_b"]) == 1
    card_html_fields = proj["zone_a"][0]
    assert card_html_fields.get("action_label_ar")
    assert card_html_fields.get("explanation", {}).get("why_here")
    assert "mission_question" in proj


def test_template_hides_seed_in_silent_mode():
    html = open("templates/merchant_app.html", encoding="utf-8").read()
    assert "merchant_cart_workspace_silent_success" in html
    assert "data-cw-silent-success" in html
    assert "data-cw-console" in html
    assert "cw-merchant-seed" not in html
    assert "تجهيز أمثلة للفهم" not in html
    assert "ma-page-hero--workspace" not in html
    ws = html.split('id="page-workspace"', 1)[1].split('id="page-carts"', 1)[0]
    assert "ma-page-hero" not in ws
