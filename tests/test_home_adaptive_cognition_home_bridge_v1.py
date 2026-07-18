# -*- coding: utf-8 -*-
from __future__ import annotations

from services.home_adaptive_cognition_home_bridge_v1 import (
    attach_adaptive_cognition_to_home_v1,
    build_truth_snapshot_from_home_v1,
    clear_acf_home_request_context_v1,
    section_order_for_path_v1,
    set_acf_home_request_context_v1,
)
from services.home_cognitive_router_v1 import (
    PATH_A_HEALTHY,
    PATH_C_VIP,
    PATH_D_OPS,
    clear_cognitive_sessions_v1,
)


def setup_function() -> None:
    clear_cognitive_sessions_v1()
    clear_acf_home_request_context_v1()


def test_vip_attention_maps_to_path_c() -> None:
    home = {
        "business_health": {
            "summary_ar": "وضع المتجر",
            "attention_required": True,
        },
        "attention_today": {
            "items": [
                {
                    "title_ar": "عميل VIP يحتاج تواصل",
                    "decision_class": "critical_action",
                    "is_vip": True,
                    "action_href": "/dashboard#messages",
                }
            ]
        },
        "store_understanding": {"items": []},
    }
    truth = build_truth_snapshot_from_home_v1(home)
    assert truth["vip_primary"] is True
    out = attach_adaptive_cognition_to_home_v1(dict(home))
    acf = out["adaptive_cognition_v1"]
    assert acf["selected_path"] == PATH_C_VIP
    assert acf["section_order"][0] == "business_health"
    assert acf["section_order"][1] == "todays_priority"
    # Empty understanding is not admitted — must not force-render a hollow section.
    assert "business_understanding" not in acf["section_order"]


def test_ops_item_maps_to_path_d() -> None:
    home = {
        "business_health": {"summary_ar": "محدود", "attention_required": True},
        "attention_today": {
            "items": [
                {
                    "title_ar": "مشكلة تكامل المتجر",
                    "operational_decision_key": "decision:fix_integration",
                    "action_href": "/dashboard#settings",
                }
            ]
        },
    }
    out = attach_adaptive_cognition_to_home_v1(dict(home))
    assert out["adaptive_cognition_v1"]["selected_path"] == PATH_D_OPS


def test_fixture_override_forces_sequence_not_content() -> None:
    home = {
        "business_health": {"summary_ar": "صحة", "attention_required": False},
        "attention_today": {"items": []},
        "greeting": {"merchant_name_ar": "متجر الاختبار"},
    }
    set_acf_home_request_context_v1(fixture="vip", trigger="session_start")
    out = attach_adaptive_cognition_to_home_v1(dict(home))
    assert out["adaptive_cognition_v1"]["selected_path"] == PATH_C_VIP
    assert out["greeting"]["merchant_name_ar"] == "متجر الاختبار"
    assert out["adaptive_cognition_v1"]["fixture_override"] == "vip"


def test_view_stable_keeps_locked_path() -> None:
    home = {
        "business_health": {"summary_ar": "ok", "attention_required": False},
        "attention_today": {"items": []},
    }
    first = attach_adaptive_cognition_to_home_v1(
        dict(home), trigger="session_start"
    )
    sid = first["adaptive_cognition_v1"]["session_id"]
    path = first["adaptive_cognition_v1"]["selected_path"]
    assert path == PATH_A_HEALTHY
    second = attach_adaptive_cognition_to_home_v1(
        dict(home), trigger="view_stable", session_id=sid
    )
    assert second["adaptive_cognition_v1"]["selected_path"] == path
    assert second["adaptive_cognition_v1"]["path_unchanged"] is True


def test_section_order_covers_all_keys() -> None:
    for path in ("A", "B", "C", "D", "E", "F"):
        order = section_order_for_path_v1(path)
        assert len(order) == len(set(order))
        assert "business_health" in order
        assert "todays_priority" in order
