# -*- coding: utf-8 -*-
"""Sprint 3 — Merchant Experience (flag-gated) tests."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from services.cart_workspace.commands_v1 import CommandError, execute_command
from services.cart_workspace.feature_flag_v1 import FLAG_CART_WORKSPACE_V1, cart_workspace_v1_enabled
from services.cart_workspace.merchant_seed_v1 import seed_merchant_comprehension_set
from services.cart_workspace.admission_v1 import candidate_from_dict
from services.cart_workspace.shadow_pipeline_v1 import evaluate_candidate
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1


def test_flag_default_off(monkeypatch):
    monkeypatch.delenv(FLAG_CART_WORKSPACE_V1, raising=False)
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    assert cart_workspace_v1_enabled() is False


def test_flag_on_when_railway_deploy_and_unset(monkeypatch):
    monkeypatch.delenv(FLAG_CART_WORKSPACE_V1, raising=False)
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abc1234")
    assert cart_workspace_v1_enabled() is True


def test_flag_explicit_off_rolls_back_on_railway(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", "abc1234")
    monkeypatch.setenv(FLAG_CART_WORKSPACE_V1, "false")
    assert cart_workspace_v1_enabled() is False


def test_primary_dashboard_path_follows_flag(monkeypatch):
    from services.cart_workspace.feature_flag_v1 import (
        cart_workspace_primary_dashboard_path,
    )

    monkeypatch.delenv(FLAG_CART_WORKSPACE_V1, raising=False)
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    assert cart_workspace_primary_dashboard_path() == "/dashboard#carts"
    monkeypatch.setenv(FLAG_CART_WORKSPACE_V1, "true")
    assert cart_workspace_primary_dashboard_path() == "/dashboard#workspace"


def test_merchant_api_404_when_flag_off(monkeypatch):
    monkeypatch.delenv(FLAG_CART_WORKSPACE_V1, raising=False)
    monkeypatch.delenv("RAILWAY_GIT_COMMIT_SHA", raising=False)
    from services.cart_workspace import merchant_api_v1 as api

    req = MagicMock()
    req.cookies = {}
    resp = api.api_cart_workspace_projection(req)
    assert resp.status_code == 404
    body = json.loads(resp.body)
    assert body["error"] == "feature_flag_off"


def test_merchant_projection_and_command_when_flag_on(monkeypatch):
    monkeypatch.setenv(FLAG_CART_WORKSPACE_V1, "true")
    store = ShadowStoreV1()
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "shop-a",
                "recovery_key": "rk-cmd",
                "signal_class": "discount_request",
                "proof_class": "approve_deny",
                "evidence_ids": ["e1"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_discount",
            }
        ),
        store=store,
    )
    open_cards = store.open_decisions("shop-a")
    assert len(open_cards) == 1
    did = open_cards[0].decision_id

    result = execute_command(
        store=store,
        store_slug="shop-a",
        decision_id=did,
        command_type="approve_discount",
        actor_merchant_user_id="shop-a",
        command_id="cmd-1",
    )
    assert result["ok"] is True
    assert result["calm_recovery"] is True
    assert store.open_decisions("shop-a") == []

    # idempotent replay
    result2 = execute_command(
        store=store,
        store_slug="shop-a",
        decision_id=did,
        command_type="approve_discount",
        actor_merchant_user_id="shop-a",
        command_id="cmd-1-again",
    )
    assert result2["idempotent"] is True


def test_command_rejects_cross_store():
    store = ShadowStoreV1()
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "shop-a",
                "recovery_key": "rk",
                "signal_class": "discount_request",
                "proof_class": "x",
                "evidence_ids": ["e"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_discount",
            }
        ),
        store=store,
    )
    did = store.open_decisions("shop-a")[0].decision_id
    with pytest.raises(CommandError):
        execute_command(
            store=store,
            store_slug="other-shop",
            decision_id=did,
            command_type="approve_discount",
            actor_merchant_user_id="x",
        )


def test_seed_comprehension_set_zones():
    store = ShadowStoreV1()
    out = seed_merchant_comprehension_set("demo-mx", store)
    assert out["ok"] is True
    proj = out["snapshot"]["projection"]
    assert len(proj["zone_a"]) == 1
    assert len(proj["zone_b"]) == 1
    assert proj["zone_d"]["completed_count"] >= 1
    assert proj["mission_question"]
    assert proj["zone_labels"]["B"] == "ما يحتاج قرارك"


def test_projection_arabic_labels_on_cards():
    store = ShadowStoreV1()
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk",
                "signal_class": "discount_request",
                "proof_class": "x",
                "evidence_ids": ["e"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_discount",
            }
        ),
        store=store,
    )
    from services.cart_workspace.projection_v1 import build_workspace_projection

    proj = build_workspace_projection("demo", store)
    card = proj.zone_b[0]
    assert card["action_label_ar"]
    assert "CartFlow" in card["explanation"]["cartflow_did"]
    assert "بعد" in card["explanation"]["expected_after"] or "CartFlow" in card["explanation"]["expected_after"]


def test_merchant_template_gated_and_scripts():
    html = Path("templates/merchant_app.html").read_text(encoding="utf-8")
    assert "merchant_cart_workspace_v1" in html
    assert "page-workspace" in html
    assert "cart_workspace_merchant_v1.js" in html
    assert "CARTFLOW_CART_WORKSPACE_V1" in html
    assert "data-cw-console" in html
    assert "cw-merchant-seed" not in html
    js = Path("static/merchant_app.js").read_text(encoding="utf-8")
    assert "CARTFLOW_CART_WORKSPACE_V1" in js
    assert 'pageKey === "workspace"' in js
    lazy = Path("static/merchant_dashboard_lazy.js").read_text(encoding="utf-8", errors="ignore")
    assert "CartWorkspaceRenderControllerV1" not in lazy


def test_decision_first_card_presenter_contract():
    """Visual Rebuild: control-console tiles; eng terms only inside details."""
    card_js = Path("static/cart_workspace_decision_card_v1.js").read_text(encoding="utf-8")
    assert "presentCard" in card_js
    assert "عرض التفاصيل" in card_js
    assert "عرض خصم" in card_js
    assert "بدء المتابعة اليدوية" in card_js
    assert "cw-tile__title" in card_js
    assert "cw-tile__line" in card_js
    assert "cw-tile__details" in card_js
    grid_js = Path("static/cart_workspace_grid_v1.js").read_text(encoding="utf-8")
    assert "تتابعه أنت الآن" in grid_js
    assert "cw-counter" in grid_js
    assert "cw-console" in grid_js
    assert "mission_question" not in grid_js
    merchant_js = Path("static/cart_workspace_merchant_v1.js").read_text(encoding="utf-8")
    assert "getFollowingVip" in merchant_js
    assert "الإصدار" not in merchant_js
    assert "تجهيز أمثلة" not in merchant_js
    css = Path("static/cart_workspace_merchant_v1.css").read_text(encoding="utf-8")
    assert 'body[data-ma-page="workspace"] #ma-page-hero-global' in css
    assert "cw-console" in css or "cw-counter" in css


def test_render_still_paint_only():
    for name in (
        "cart_workspace_grid_v1.js",
        "cart_workspace_decision_card_v1.js",
        "cart_workspace_projection_version_v1.js",
    ):
        text = Path("static", name).read_text(encoding="utf-8")
        assert "evaluate_admission" not in text
        assert "apply_transition" not in text
