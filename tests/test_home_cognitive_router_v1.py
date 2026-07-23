# -*- coding: utf-8 -*-
from __future__ import annotations

from services.home_cognitive_router_v1 import (
    PATH_A_HEALTHY,
    PATH_B_ATTENTION,
    PATH_C_VIP,
    PATH_D_OPS,
    PATH_E_INSUFFICIENT,
    PATH_F_PENDING,
    TRIGGER_FULL_PAGE_REFRESH,
    TRIGGER_MANUAL_REFRESH,
    TRIGGER_RETURN_FROM_SURFACE,
    TRIGGER_SIGNIFICANT_STATE_TRANSITION,
    clear_cognitive_sessions_v1,
    evaluate_cognitive_route_v1,
    fixture_truth_snapshots_v1,
    reevaluate_cognition_session_v1,
    start_cognition_session_v1,
    view_tick_cognition_session_v1,
)


def setup_function() -> None:
    clear_cognitive_sessions_v1()


def test_path_selection_by_fixture() -> None:
    fx = fixture_truth_snapshots_v1()
    assert evaluate_cognitive_route_v1(fx["healthy"])["selected_path"] == PATH_A_HEALTHY
    assert evaluate_cognitive_route_v1(fx["vip"])["selected_path"] == PATH_C_VIP
    assert evaluate_cognitive_route_v1(fx["attention"])["selected_path"] == PATH_B_ATTENTION
    assert evaluate_cognitive_route_v1(fx["operational"])["selected_path"] == PATH_D_OPS
    assert evaluate_cognitive_route_v1(fx["insufficient"])["selected_path"] == PATH_E_INSUFFICIENT
    assert evaluate_cognitive_route_v1(fx["pending"])["selected_path"] == PATH_F_PENDING


def test_router_does_not_mutate_truth() -> None:
    fx = fixture_truth_snapshots_v1()["vip"]
    before = dict(fx)
    evaluate_cognitive_route_v1(fx)
    assert fx == before


def test_ownership_declared_on_decision() -> None:
    d = evaluate_cognitive_route_v1(fixture_truth_snapshots_v1()["healthy"])
    assert "sequencing" in d["ownership"]["router_owns"]
    assert "business_truth" in d["ownership"]["router_never_owns"]


def test_session_path_stable_on_view_ticks() -> None:
    fx = fixture_truth_snapshots_v1()["vip"]
    started = start_cognition_session_v1(fx)
    sid = started["session_id"]
    path = started["selected_path"]
    t1 = view_tick_cognition_session_v1(sid)
    t2 = view_tick_cognition_session_v1(sid)
    assert t1["path_unchanged"] is True
    assert t1["reevaluated"] is False
    assert t1["selected_path"] == path
    assert t2["selected_path"] == path
    assert t2["view_ticks_while_locked"] == 2


def test_ungoverned_trigger_rejected() -> None:
    fx = fixture_truth_snapshots_v1()["vip"]
    started = start_cognition_session_v1(fx)
    out = reevaluate_cognition_session_v1(
        started["session_id"], trigger="periodic_poll"
    )
    assert out["ok"] is False
    assert out["error"] == "ungoverned_trigger"
    # path still locked as VIP
    assert started["selected_path"] == PATH_C_VIP


def test_governed_reeval_on_significant_transition() -> None:
    fx = fixture_truth_snapshots_v1()
    started = start_cognition_session_v1(fx["vip"])
    assert started["selected_path"] == PATH_C_VIP
    out = reevaluate_cognition_session_v1(
        started["session_id"],
        trigger=TRIGGER_SIGNIFICANT_STATE_TRANSITION,
        truth=fx["vip_resolved"],
    )
    assert out["ok"] is True
    assert out["reevaluated"] is True
    assert out["previous_path"] == PATH_C_VIP
    assert out["selected_path"] == PATH_A_HEALTHY
    assert out["path_changed"] is True


def test_return_from_surface_segment() -> None:
    fx = fixture_truth_snapshots_v1()
    started = start_cognition_session_v1(fx["attention"])
    out = reevaluate_cognition_session_v1(
        started["session_id"],
        trigger=TRIGGER_RETURN_FROM_SURFACE,
        truth=fx["healthy"],
        segment="RETURN",
    )
    assert out["ok"] is True
    assert "R-RETURN-CONTINUE" in out["decision"]["rationale_codes"]
    assert "ContextRestore" in out["decision"]["active_nodes"]


def test_manual_and_full_refresh_allowed() -> None:
    fx = fixture_truth_snapshots_v1()
    started = start_cognition_session_v1(fx["operational"])
    sid = started["session_id"]
    a = reevaluate_cognition_session_v1(
        sid, trigger=TRIGGER_MANUAL_REFRESH, truth=fx["operational"]
    )
    b = reevaluate_cognition_session_v1(
        sid, trigger=TRIGGER_FULL_PAGE_REFRESH, truth=fx["healthy"]
    )
    assert a["ok"] and b["ok"]
    assert b["selected_path"] == PATH_A_HEALTHY
