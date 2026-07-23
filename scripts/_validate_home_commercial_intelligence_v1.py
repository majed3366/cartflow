# -*- coding: utf-8 -*-
"""Validate Home Commercial Intelligence diversity (demo evidence fixture)."""
from __future__ import annotations

import json
from pathlib import Path

from services.business_findings_engine_v1 import run_business_findings_engine_v1
from services.commercial_interpretation_v1 import (
    clear_commercial_interpretation_last_valid_cache_v1,
)
from services.merchant_home_composition_v1 import compose_merchant_home_experience_v1

_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    clear_commercial_interpretation_last_valid_cache_v1()
    pkg = run_business_findings_engine_v1(store_slug="demo", demo_fixture=True)
    home = compose_merchant_home_experience_v1(
        merchant_name_ar="متجر التحقق",
        date_ar="الأحد",
        brief_date="2026-07-19",
        daily_brief={"version": "v1", "achievements": [], "attention_items": []},
        kl_insights=[],
        nav_metadata={
            "active_carts": 77,
            "canonical_no_phone_total": 43,
            "waiting_send": 5,
            "knowledge_cart_count": 77,
        },
        store_slug="demo",
        findings_package=pkg,
        commercial_intel_demo=False,
    )
    meta = home.get("home_commercial_intelligence_v1") or {}
    mapping = []
    for key, section in (
        ("business_health", home.get("business_health")),
        ("todays_priority", home.get("todays_priority") or home.get("attention_today")),
        ("business_understanding", home.get("store_understanding")),
        ("biggest_opportunity", home.get("biggest_opportunity")),
        ("learning_progress", home.get("learning_progress")),
    ):
        if not isinstance(section, dict):
            continue
        item = section.get("item")
        if item is None and section.get("items"):
            item = section["items"][0]
        item = item if isinstance(item, dict) else {}
        mapping.append(
            {
                "section": key,
                "admitted": (section.get("home_admission_v1") or {}).get("admitted"),
                "question_id": item.get("commercial_question_id")
                or (section.get("home_admission_v1") or {}).get("commercial_question_id"),
                "question_ar": item.get("commercial_question_ar")
                or section.get("section_question_ar"),
                "dimension": item.get("commercial_dimension"),
                "answer": item.get("commercial_answer_ar")
                or item.get("observation_ar")
                or item.get("headline_ar")
                or item.get("progress_ar")
                or section.get("summary_ar"),
                "evidence": item.get("evidence_ar") or item.get("evidence_label_ar"),
                "confidence": item.get("confidence") or section.get("confidence"),
                "meaning": item.get("merchant_meaning_ar")
                or item.get("business_meaning_ar"),
            }
        )

    out = {
        "ok": bool(meta.get("ok") and meta.get("diversity_ok")),
        "questions_answered_count": meta.get("questions_answered_count"),
        "dimensions_answered": meta.get("dimensions_answered"),
        "questions_answered": meta.get("questions_answered"),
        "success_metric": meta.get("success_metric"),
        "question_to_insight_mapping": mapping,
        "evidence_flow": [
            "EvidenceBundle(demo_rich)",
            "Business Findings Engine",
            "Commercial Question Registry",
            "Home Commercial Intelligence admission",
            "Semantic composition",
            "Adaptive Cognition section_order",
        ],
        "home_commercial_intelligence_v1": meta,
    }
    path = _ROOT / "HOME_COMMERCIAL_INTELLIGENCE_TRANSITION_V1_EVIDENCE.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS" if out["ok"] else "FAIL", path)
    print("questions", out["questions_answered_count"], "dims", out["dimensions_answered"])
    for row in mapping:
        if row.get("admitted") or row.get("question_id"):
            ans = (row.get("answer") or "")[:60]
            print(
                "-",
                row["section"],
                row.get("question_id"),
                row.get("dimension"),
                "->",
                ans.encode("ascii", "replace").decode("ascii"),
            )


if __name__ == "__main__":
    main()
