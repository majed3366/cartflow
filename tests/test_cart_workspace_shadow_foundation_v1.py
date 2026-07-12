# -*- coding: utf-8 -*-
"""Cart Workspace Sprint 1 — Shadow Foundation tests (no merchant UI)."""
from __future__ import annotations

import os

import pytest

from services.cart_workspace.admission_v1 import (
    AdmissionCandidate,
    candidate_from_dict,
    evaluate_admission,
)
from services.cart_workspace.decision_identity_v1 import (
    allocate_decision_id,
    build_evidence_fingerprint,
    find_open_duplicate,
)
from services.cart_workspace.feature_flag_v1 import (
    FLAG_CART_WORKSPACE_V1,
    cart_workspace_v1_enabled,
)
from services.cart_workspace.ownership_v1 import (
    OwnershipError,
    apply_transition,
    default_ownership,
)
from services.cart_workspace.projection_v1 import build_workspace_projection
from services.cart_workspace.shadow_pipeline_v1 import (
    evaluate_candidate,
    run_scenario,
    shadow_snapshot,
)
from services.cart_workspace.shadow_store_v1 import ShadowStoreV1


# ---------------------------------------------------------------------------
# Feature flag isolation
# ---------------------------------------------------------------------------


def test_feature_flag_default_off(monkeypatch):
    monkeypatch.delenv(FLAG_CART_WORKSPACE_V1, raising=False)
    assert cart_workspace_v1_enabled() is False


def test_feature_flag_explicit_on(monkeypatch):
    monkeypatch.setenv(FLAG_CART_WORKSPACE_V1, "true")
    assert cart_workspace_v1_enabled() is True
    monkeypatch.setenv(FLAG_CART_WORKSPACE_V1, "0")
    assert cart_workspace_v1_enabled() is False


# ---------------------------------------------------------------------------
# Decision identity
# ---------------------------------------------------------------------------


def test_evidence_fingerprint_stable_and_order_independent():
    a = build_evidence_fingerprint(
        store_slug="Demo",
        recovery_key="rk1",
        proof_class="automation_exhausted",
        evidence_ids=["b", "a"],
        matrix_path="normal",
    )
    b = build_evidence_fingerprint(
        store_slug="demo",
        recovery_key="rk1",
        proof_class="automation_exhausted",
        evidence_ids=["a", "b"],
        matrix_path="normal",
    )
    assert a == b
    assert len(a) == 64


def test_decision_id_unique():
    assert allocate_decision_id() != allocate_decision_id()


def test_find_open_duplicate():
    fp = "abc"
    rows = [
        {
            "status": "open",
            "store_slug": "demo",
            "recovery_key": "rk",
            "evidence_fingerprint": fp,
            "decision_id": "d1",
        }
    ]
    assert find_open_duplicate(rows, store_slug="demo", recovery_key="rk", evidence_fingerprint=fp)["decision_id"] == "d1"
    assert find_open_duplicate(rows, store_slug="demo", recovery_key="rk", evidence_fingerprint="other") is None


# ---------------------------------------------------------------------------
# Ownership transitions
# ---------------------------------------------------------------------------


def test_ownership_t1_and_t3_roundtrip():
    st = default_ownership("demo", "rk")
    st2, audit, changed = apply_transition(st, transition_code="T1", evidence_refs=["e1"])
    assert changed is True
    assert st2.decision_owner == "merchant"
    assert audit.transition_code == "T1"
    st3, _, changed2 = apply_transition(st2, transition_code="T3", evidence_refs=["e1"])
    assert changed2 is True
    assert st3.decision_owner == "cartflow"


def test_ownership_t8_idempotent_no_oscillation():
    st = default_ownership("demo", "rk")
    st, _, c1 = apply_transition(st, transition_code="T8")
    assert c1 is True
    assert st.override_mode == "active"
    st2, _, c2 = apply_transition(st, transition_code="T8")
    assert c2 is False
    assert st2.override_mode == "active"


def test_ownership_deferred_t4_blocked():
    st = default_ownership("demo", "rk")
    st, _, _ = apply_transition(st, transition_code="T1")
    with pytest.raises(OwnershipError, match="product_deferred"):
        apply_transition(st, transition_code="T4")


def test_ownership_t10_completion():
    st = default_ownership("demo", "rk")
    st, _, _ = apply_transition(st, transition_code="T10")
    assert st.journey_phase == "completed"
    assert st.decision_owner == "cartflow"


# ---------------------------------------------------------------------------
# Admission matrix (representative R01–R20)
# ---------------------------------------------------------------------------


def _own(**kwargs):
    st = default_ownership(kwargs.get("store_slug", "demo"), kwargs.get("recovery_key", "rk"))
    for k, v in kwargs.items():
        if hasattr(st, k):
            setattr(st, k, v)
    return st


def test_admission_r01_insufficient_proof():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="hesitation",
        proof_class="weak",
        proof_sufficient=False,
        automation_capable=True,
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R01"


def test_admission_r03_admit():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="hesitation",
        proof_class="automation_exhausted",
        evidence_ids=["e1"],
        proof_sufficient=True,
        automation_capable=False,
        human_gain_exceeds_cost=True,
        expected_action="approve_next_step",
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "admit"
    assert r.matrix_row_id == "R03"
    assert r.expected_merchant_action == "approve_next_step"


def test_admission_r07_override():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="vip_detect",
        proof_class="override_eligible",
        evidence_ids=["vip1"],
        proof_sufficient=True,
        override_eligible=True,
        expected_action="override_decision_action",
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "admit"
    assert r.matrix_row_id == "R07"
    assert r.override_path is True


def test_admission_r08_override_dup():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="vip_detect",
        proof_class="override_eligible",
        proof_sufficient=True,
        override_eligible=True,
        is_duplicate_vip_while_active=True,
    )
    r = evaluate_admission(c, _own(override_mode="active", decision_owner="merchant"))
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R08"


def test_admission_r11_completed():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="purchase_completed",
        proof_class="terminal",
        journey_completed=True,
        proof_sufficient=True,
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R11"


def test_admission_r12_provider_retry():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="provider_failure",
        proof_class="retry_allowed",
        proof_sufficient=True,
        automation_capable=True,
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R12"


def test_admission_r17_refresh_duplicate():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="refresh",
        proof_class="automation_exhausted",
        is_refresh_same_fingerprint=True,
        proof_sufficient=True,
        automation_capable=False,
        human_gain_exceeds_cost=True,
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R17"


def test_admission_r18_knowledge():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="knowledge_claim",
        proof_class="claim",
        is_knowledge_only=True,
        proof_sufficient=True,
        automation_capable=True,
    )
    r = evaluate_admission(c, _own())
    assert r.outcome == "do_not_admit"
    assert r.matrix_row_id == "R18"


def test_admission_deterministic_same_inputs():
    c = AdmissionCandidate(
        store_slug="demo",
        recovery_key="rk",
        signal_class="discount_request",
        proof_class="approve_deny",
        evidence_ids=["d1"],
        proof_sufficient=True,
        automation_capable=False,
        human_gain_exceeds_cost=True,
        expected_action="approve_or_deny_discount",
    )
    r1 = evaluate_admission(c, _own())
    r2 = evaluate_admission(c, _own())
    assert r1.outcome == r2.outcome == "admit"
    assert r1.matrix_row_id == r2.matrix_row_id == "R06"
    assert r1.evidence_fingerprint == r2.evidence_fingerprint


# ---------------------------------------------------------------------------
# Projection + pipeline
# ---------------------------------------------------------------------------


def test_projection_quiet_when_no_decisions():
    store = ShadowStoreV1()
    proj = build_workspace_projection("demo", store)
    assert proj.quiet is True
    assert proj.zone_a == []
    assert proj.zone_b == []
    assert proj.workspace_phase == "WL-1"
    assert "CartFlow" in proj.zone_c["summary"] or "قرار" in proj.zone_c["summary"]


def test_pipeline_admit_creates_one_card_zone_b():
    store = ShadowStoreV1()
    out = evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk-a",
                "signal_class": "hesitation",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["e1"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_next_step",
            }
        ),
        store=store,
    )
    assert out["admission"]["outcome"] == "admit"
    assert out["decision"] is not None
    assert out["projection"]["quiet"] is False
    assert len(out["projection"]["zone_b"]) == 1
    assert out["projection"]["zone_a"] == []
    assert out["ownership"]["decision_owner"] == "merchant"


def test_pipeline_override_zone_a():
    store = ShadowStoreV1()
    out = evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk-vip",
                "signal_class": "vip_detect",
                "proof_class": "override_eligible",
                "evidence_ids": ["v1"],
                "proof_sufficient": True,
                "override_eligible": True,
                "expected_action": "override_decision_action",
            }
        ),
        store=store,
    )
    assert out["admission"]["matrix_row_id"] == "R07"
    assert len(out["projection"]["zone_a"]) == 1
    assert out["projection"]["zone_b"] == []
    assert out["ownership"]["override_mode"] == "active"


def test_duplicate_events_idempotent_no_second_card():
    store = ShadowStoreV1()
    payload = {
        "store_slug": "demo",
        "recovery_key": "rk-dup",
        "signal_class": "hesitation",
        "proof_class": "automation_exhausted",
        "evidence_ids": ["same"],
        "proof_sufficient": True,
        "automation_capable": False,
        "human_gain_exceeds_cost": True,
        "expected_action": "approve_next_step",
    }
    evaluate_candidate(candidate_from_dict(payload), store=store)
    out2 = evaluate_candidate(
        candidate_from_dict({**payload, "signal_class": "refresh", "is_refresh_same_fingerprint": True}),
        store=store,
    )
    assert out2["admission"]["outcome"] == "do_not_admit"
    assert len(store.open_decisions("demo")) == 1


def test_projection_determinism_same_open_set_stable_order():
    store = ShadowStoreV1()
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk-1",
                "signal_class": "hesitation",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["e1"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "a1",
            }
        ),
        store=store,
    )
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk-2",
                "signal_class": "discount_request",
                "proof_class": "approve_deny",
                "evidence_ids": ["e2"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_or_deny_discount",
            }
        ),
        store=store,
    )
    p1 = build_workspace_projection("demo", store)
    # Rebuild without new admits — version bumps but entity order/ids stable
    ids1 = [c["decision_id"] for c in p1.zone_b]
    p2 = build_workspace_projection("demo", store)
    ids2 = [c["decision_id"] for c in p2.zone_b]
    assert ids1 == ids2
    assert len(ids1) == 2


def test_restart_clears_in_memory_shadow_store():
    store = ShadowStoreV1()
    evaluate_candidate(
        candidate_from_dict(
            {
                "store_slug": "demo",
                "recovery_key": "rk",
                "signal_class": "hesitation",
                "proof_class": "automation_exhausted",
                "evidence_ids": ["e"],
                "proof_sufficient": True,
                "automation_capable": False,
                "human_gain_exceeds_cost": True,
                "expected_action": "approve_next_step",
            }
        ),
        store=store,
    )
    assert store.open_decisions("demo")
    store.reset()
    assert store.open_decisions("demo") == []
    proj = build_workspace_projection("demo", store)
    assert proj.quiet is True


def test_scenario_duplicate_fingerprint():
    store = ShadowStoreV1()
    snap = run_scenario("duplicate_fingerprint", store=store, reset=True)
    assert snap["ok"] is True
    assert len(snap["open_decision_ids"]) == 1
    assert snap["scenario_steps"][1]["admission"]["outcome"] == "do_not_admit"


def test_scenario_r11_completed_rollup():
    store = ShadowStoreV1()
    snap = run_scenario("r11_completed", store=store, reset=True)
    assert snap["projection"]["zone_d"]["completed_count"] >= 1
    assert snap["projection"]["quiet"] is True


def test_shadow_snapshot_marks_merchant_inactive():
    store = ShadowStoreV1()
    snap = shadow_snapshot("demo", store=store)
    assert snap["merchant_surface_active"] is False
    assert snap["feature_flag"]["enabled"] is False or snap["mode"] == "shadow"


# ---------------------------------------------------------------------------
# HTTP endpoint (dev-only)
# ---------------------------------------------------------------------------


def test_dev_endpoint_404_outside_development(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    # Import after env — main may already be loaded; patch _is_development_mode
    import routes.cart_workspace_v1 as cw

    monkeypatch.setattr(cw, "_dev_only", lambda: False)
    resp = cw.dev_cart_workspace_projection(store_slug="demo", scenario=None, reset=True, scenario_reset=True)
    assert getattr(resp, "status_code", None) == 404


def test_dev_endpoint_scenario_ok(monkeypatch):
    import routes.cart_workspace_v1 as cw

    monkeypatch.setattr(cw, "_dev_only", lambda: True)
    from services.cart_workspace.shadow_store_v1 import SHADOW_STORE

    SHADOW_STORE.reset()
    resp = cw.dev_cart_workspace_projection(
        store_slug="demo", scenario="quiet", reset=False, scenario_reset=True
    )
    body = resp.body
    import json

    data = json.loads(body)
    assert data["ok"] is True
    assert data["merchant_surface_active"] is False
    assert data["projection"]["quiet"] is True
