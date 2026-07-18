# -*- coding: utf-8 -*-
"""
Adaptive Cognition Lab V1 — production validation surface.

Not Home. Not Wireframe. Not merchant nav.
Exposes Cognitive Router path selection + session stability for Product review.
"""
from __future__ import annotations

from typing import Any, Optional

from services.home_cognitive_router_v1 import (
    TRIGGER_FULL_PAGE_REFRESH,
    TRIGGER_MANUAL_REFRESH,
    TRIGGER_RETURN_FROM_SURFACE,
    TRIGGER_SESSION_START,
    TRIGGER_SIGNIFICANT_STATE_TRANSITION,
    fixture_truth_snapshots_v1,
    get_cognition_session_v1,
    reevaluate_cognition_session_v1,
    start_cognition_session_v1,
    view_tick_cognition_session_v1,
)


def build_adaptive_cognition_lab_payload_v1(
    *,
    fixture: str = "vip",
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    fixtures = fixture_truth_snapshots_v1()
    key = (fixture or "vip").strip().lower()
    if key not in fixtures:
        key = "vip"
    truth = fixtures[key]

    if session_id:
        existing = get_cognition_session_v1(session_id)
        if existing.get("ok"):
            return {
                "lab": "adaptive_cognition_v2",
                "not_home": True,
                "fixture_id": key,
                "fixtures": sorted(fixtures.keys()),
                "truth_snapshot": truth,
                "session": existing,
                "triggers": _trigger_catalog(),
                "ownership_principle": _ownership_principle(),
            }

    session = start_cognition_session_v1(truth, trigger=TRIGGER_SESSION_START)
    return {
        "lab": "adaptive_cognition_v2",
        "not_home": True,
        "fixture_id": key,
        "fixtures": sorted(fixtures.keys()),
        "truth_snapshot": truth,
        "session": session,
        "triggers": _trigger_catalog(),
        "ownership_principle": _ownership_principle(),
    }


def lab_view_tick_v1(session_id: str) -> dict[str, Any]:
    return view_tick_cognition_session_v1(session_id)


def lab_reeval_v1(
    session_id: str,
    *,
    trigger: str,
    fixture: Optional[str] = None,
) -> dict[str, Any]:
    fixtures = fixture_truth_snapshots_v1()
    truth = None
    if fixture:
        key = fixture.strip().lower()
        if key in fixtures:
            truth = fixtures[key]
    # Significant transition demo: VIP → resolved healthy
    if trigger == TRIGGER_SIGNIFICANT_STATE_TRANSITION and not truth:
        truth = fixtures["vip_resolved"]
    segment = "RETURN" if trigger == TRIGGER_RETURN_FROM_SURFACE else "ENTRY"
    return reevaluate_cognition_session_v1(
        session_id, trigger=trigger, truth=truth, segment=segment
    )


def _trigger_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": TRIGGER_FULL_PAGE_REFRESH,
            "label": "Full page refresh",
            "allowed": "yes",
        },
        {
            "id": TRIGGER_MANUAL_REFRESH,
            "label": "Manual refresh",
            "allowed": "yes",
        },
        {
            "id": TRIGGER_RETURN_FROM_SURFACE,
            "label": "Return from another surface",
            "allowed": "yes",
        },
        {
            "id": TRIGGER_SIGNIFICANT_STATE_TRANSITION,
            "label": "Significant governed state transition",
            "allowed": "yes",
        },
        {
            "id": "periodic_poll",
            "label": "Periodic background poll (FORBIDDEN)",
            "allowed": "no",
        },
    ]


def _ownership_principle() -> str:
    return (
        "The Adaptive Cognitive Engine never creates, modifies, filters or interprets "
        "business truth. It consumes governed truth and determines only the cognition "
        "sequence presented to the merchant."
    )
