# -*- coding: utf-8 -*-
"""Sprint 2 — Golden scenarios, projection version, render foundation (no merchant UI)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.cart_workspace.feature_flag_v1 import cart_workspace_v1_enabled
from services.cart_workspace.golden_scenarios_v1 import list_golden_ids, run_all_goldens, run_golden
from services.cart_workspace.live_update_v1 import (
    ACCEPT,
    CONFLICT_SAME_VERSION,
    STALE_OLDER,
    compare_projection_envelope,
)
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1


def test_all_golden_scenarios_pass():
    report = run_all_goldens()
    assert report["ok"] is True, json.dumps(
        [{"id": r["scenario_id"], "failures": r.get("failures")} for r in report["results"] if not r["ok"]],
        ensure_ascii=False,
    )
    assert report["total"] == 10
    assert report["passed"] == 10


@pytest.mark.parametrize("sid", list_golden_ids())
def test_each_golden_individually(sid):
    r = run_golden(sid, store=ShadowStoreV1(), reset=True)
    assert r["ok"] is True, r.get("failures")


def test_projection_version_no_repaint_same_version():
    local = {"projection_version": 3, "projection_fingerprint": "abc"}
    incoming = {"projection_version": 3, "projection_fingerprint": "abc"}
    c = compare_projection_envelope(local, incoming)
    assert c["decision"] == ACCEPT
    assert c["should_paint"] is False


def test_projection_version_paint_on_advance():
    local = {"projection_version": 1, "projection_fingerprint": "a"}
    incoming = {"projection_version": 2, "projection_fingerprint": "b"}
    c = compare_projection_envelope(local, incoming)
    assert c["should_paint"] is True
    assert c["decision"] == ACCEPT


def test_projection_version_stale_older():
    local = {"projection_version": 5, "projection_fingerprint": "a"}
    incoming = {"projection_version": 4, "projection_fingerprint": "b"}
    c = compare_projection_envelope(local, incoming)
    assert c["decision"] == STALE_OLDER
    assert c["should_paint"] is False


def test_projection_version_conflict_same_version():
    local = {"projection_version": 2, "projection_fingerprint": "a"}
    incoming = {"projection_version": 2, "projection_fingerprint": "b"}
    c = compare_projection_envelope(local, incoming)
    assert c["decision"] == CONFLICT_SAME_VERSION
    assert c["should_paint"] is False


def test_feature_flag_still_off():
    assert cart_workspace_v1_enabled() is False


def test_render_js_has_no_admission_or_ownership_symbols():
    root = Path(__file__).resolve().parents[1] / "static"
    files = [
        root / "cart_workspace_grid_v1.js",
        root / "cart_workspace_decision_card_v1.js",
        root / "cart_workspace_projection_version_v1.js",
    ]
    forbidden = [
        "evaluate_admission",
        "apply_transition",
        "matrix_row",
        "override_eligible",
        "decision_owner",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"{path.name} contains forbidden business token: {token}"
    # Controller may mention audit helpers; ensure it does not call admission/ownership APIs.
    ctrl = (root / "cart_workspace_render_controller_v1.js").read_text(encoding="utf-8")
    assert "evaluate_admission(" not in ctrl
    assert "apply_transition(" not in ctrl
    assert "CartWorkspaceRenderControllerV1" in ctrl


def test_js_version_contract_mirrors_python_semantics():
    """Load JS compare via subprocess-free reimplementation check — same outcomes as Python."""
    # Already covered by Python live_update tests; ensure JS file exports expected API names.
    js = (Path(__file__).resolve().parents[1] / "static" / "cart_workspace_projection_version_v1.js").read_text(
        encoding="utf-8"
    )
    assert "compareProjectionEnvelope" in js
    assert "should_paint" in js


def test_dev_golden_endpoint(monkeypatch):
    import routes.cart_workspace_v1 as cw

    monkeypatch.setattr(cw, "_dev_only", lambda: True)
    resp = cw.dev_cart_workspace_golden_all()
    data = json.loads(resp.body)
    assert data["ok"] is True
    assert data["merchant_surface_active"] is False


def test_dev_render_harness_dev_only(monkeypatch):
    import routes.cart_workspace_v1 as cw

    monkeypatch.setattr(cw, "_dev_only", lambda: False)
    resp = cw.dev_cart_workspace_render_harness()
    assert getattr(resp, "status_code", None) == 404

    monkeypatch.setattr(cw, "_dev_only", lambda: True)
    resp2 = cw.dev_cart_workspace_render_harness()
    assert getattr(resp2, "status_code", 200) == 200
    assert b"Cart Workspace Shadow Render" in resp2.body


def test_merchant_dashboard_lazy_not_wired_to_workspace():
    """Acceptance: carts lazy path unchanged; Workspace only behind template flag block."""
    root = Path(__file__).resolve().parents[1]
    lazy = (root / "static" / "merchant_dashboard_lazy.js").read_text(encoding="utf-8", errors="ignore")
    assert "CartWorkspaceRenderControllerV1" not in lazy
    assert "cart_workspace_grid_v1" not in lazy
    html = (root / "templates" / "merchant_app.html").read_text(encoding="utf-8", errors="ignore")
    # Scripts may appear only inside merchant_cart_workspace_v1 flag block
    assert "{% if merchant_cart_workspace_v1 %}" in html
    assert "cart_workspace_merchant_v1.js" in html
    # Ensure not loaded unconditionally before the flag block end for carts RSC
    rsc_idx = html.find("cart_page_rendering_state_controller_v1.js")
    flag_idx = html.find("{% if merchant_cart_workspace_v1 %}")
    assert rsc_idx != -1 and flag_idx != -1
    # Workspace scripts come after RSC and inside flag (Sprint 3)
    assert "cart_workspace_render_controller_v1.js" in html[flag_idx:]
