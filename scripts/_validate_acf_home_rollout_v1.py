# -*- coding: utf-8 -*-
"""Validate Adaptive Cognition Home sequencing (local engine + optional prod HTML)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.home_adaptive_cognition_home_bridge_v1 import (  # noqa: E402
    attach_adaptive_cognition_to_home_v1,
    clear_acf_home_request_context_v1,
    section_order_for_path_v1,
    set_acf_home_request_context_v1,
)
from services.home_cognitive_router_v1 import (  # noqa: E402
    clear_cognitive_sessions_v1,
    fixture_truth_snapshots_v1,
)

OUT = ROOT / "HOME_ADAPTIVE_COGNITION_HOME_ROLLOUT_EVIDENCE_V1.json"


def main() -> int:
    clear_cognitive_sessions_v1()
    clear_acf_home_request_context_v1()
    base_home = {
        "business_health": {"summary_ar": "ملخص", "attention_required": False},
        "attention_today": {"items": []},
        "todays_priority": {"items": []},
        "business_understanding": {"items": []},
        "biggest_revenue_risk": {"item": None},
        "biggest_opportunity": {},
        "learning_progress": {},
        "business_timeline": {},
        "greeting": {"merchant_name_ar": "متجر التحقق"},
    }
    results = {}
    for name in sorted(fixture_truth_snapshots_v1().keys()):
        if name == "vip_resolved":
            continue
        clear_cognitive_sessions_v1()
        clear_acf_home_request_context_v1()
        set_acf_home_request_context_v1(fixture=name, trigger="session_start")
        home = attach_adaptive_cognition_to_home_v1(dict(base_home))
        acf = home["adaptive_cognition_v1"]
        path = acf["selected_path"]
        order = acf["section_order"]
        expected = section_order_for_path_v1(path)
        results[name] = {
            "selected_path": path,
            "path_label": acf.get("path_label"),
            "section_order": order,
            "order_matches_path": order == expected,
            "first_focus": order[1] if len(order) > 1 else order[0],
            "content_preserved": home.get("greeting", {}).get("merchant_name_ar")
            == "متجر التحقق",
        }
    # stability
    clear_cognitive_sessions_v1()
    clear_acf_home_request_context_v1()
    set_acf_home_request_context_v1(fixture="vip", trigger="session_start")
    h1 = attach_adaptive_cognition_to_home_v1(dict(base_home))
    sid = h1["adaptive_cognition_v1"]["session_id"]
    clear_acf_home_request_context_v1()
    h2 = attach_adaptive_cognition_to_home_v1(
        dict(base_home), trigger="view_stable", session_id=sid, fixture="vip"
    )
    results["_stability"] = {
        "path1": h1["adaptive_cognition_v1"]["selected_path"],
        "path2": h2["adaptive_cognition_v1"]["selected_path"],
        "unchanged": h2["adaptive_cognition_v1"].get("path_unchanged"),
    }
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    ok = all(
        v.get("order_matches_path") and v.get("content_preserved")
        for k, v in results.items()
        if not k.startswith("_")
    )
    ok = ok and results["_stability"]["path1"] == results["_stability"]["path2"]
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
