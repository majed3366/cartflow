# -*- coding: utf-8 -*-
"""Generate Home semantic deduplication evidence for contact scenario + ACF paths."""
from __future__ import annotations

import json
from pathlib import Path

from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.home_adaptive_cognition_home_bridge_v1 import (
    attach_adaptive_cognition_to_home_v1,
    clear_acf_home_request_context_v1,
)
from services.home_cognitive_router_v1 import clear_cognitive_sessions_v1
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

_ROOT = Path(__file__).resolve().parents[1]


def contact_home() -> dict:
    return compose_merchant_home_experience_v1(
        merchant_name_ar="متجر اختبار",
        date_ar="السبت",
        brief_date="2026-07-18",
        daily_brief={"version": "v1", "achievements": [], "attention_items": []},
        kl_insights=[],
        nav_metadata={
            "active_carts": 77,
            "waiting_send": 5,
            "canonical_no_phone_total": 43,
            "knowledge_cart_count": 77,
        },
        store_slug="demo",
    )


def card_trace(home: dict, key: str) -> dict:
    alias = {
        "todays_priority": ("todays_priority", "attention_today"),
        "business_understanding": ("business_understanding", "store_understanding"),
        "business_timeline": ("business_timeline", "while_away"),
    }
    keys = alias.get(key, (key,))
    section = None
    for k in keys:
        if isinstance(home.get(k), dict):
            section = home[k]
            break
    if not isinstance(section, dict):
        return {"section": key, "admitted": False, "reason": "missing"}
    adm = section.get("home_admission_v1") or {}
    item = section.get("item")
    if item is None and section.get("items"):
        item = section["items"][0]
    ident = (item or {}).get("semantic_identity_v1") or section.get(
        "semantic_identity_v1"
    ) or {}
    return {
        "section": key,
        "admitted": bool(adm.get("admitted")),
        "admission_reason": adm.get("reason"),
        "cognitive_role": adm.get("cognitive_role") or ident.get("cognitive_role"),
        "merchant_problem": ident.get("merchant_problem"),
        "truth_id": ident.get("truth_id"),
        "headline": (item or {}).get("headline_ar")
        or (item or {}).get("observation_ar")
        or (item or {}).get("progress_ar")
        or section.get("summary_ar"),
    }


def main() -> None:
    clear_commercial_interpretation_last_valid_cache_v1()
    clear_cognitive_sessions_v1()
    clear_acf_home_request_context_v1()

    out: dict = {"contact_scenario": {}, "paths": {}}
    home = contact_home()
    meta = home.get("home_semantic_composition_v1") or {}
    out["contact_scenario"] = {
        "admitted_sections": meta.get("admitted_sections"),
        "suppressed": meta.get("suppressed"),
        "claimed_roles": meta.get("claimed_roles"),
        "cards": [
            card_trace(home, k)
            for k in (
                "business_health",
                "todays_priority",
                "biggest_revenue_risk",
                "biggest_opportunity",
                "business_understanding",
                "learning_progress",
                "business_timeline",
            )
        ],
    }
    for fixture in (
        "healthy",
        "vip",
        "operational",
        "attention",
        "pending",
        "insufficient",
    ):
        clear_cognitive_sessions_v1()
        clear_acf_home_request_context_v1()
        h = contact_home()
        attach_adaptive_cognition_to_home_v1(
            h, trigger="session_start", fixture=fixture
        )
        acf = h.get("adaptive_cognition_v1") or {}
        out["paths"][fixture] = {
            "selected_path": acf.get("selected_path"),
            "section_order": acf.get("section_order"),
            "suppressed": (h.get("home_semantic_composition_v1") or {}).get(
                "suppressed"
            ),
            "cards": [card_trace(h, k) for k in (acf.get("section_order") or [])],
        }

    path = _ROOT / "HOME_SEMANTIC_DEDUPLICATION_V1_EVIDENCE.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS wrote", path)
    print("admitted", out["contact_scenario"]["admitted_sections"])
    print("suppressed_count", len(out["contact_scenario"]["suppressed"] or []))
    for fx, row in out["paths"].items():
        print(fx, row["selected_path"], "->", row["section_order"])


if __name__ == "__main__":
    main()
