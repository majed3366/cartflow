# -*- coding: utf-8 -*-
"""
Home Cognitive Router V1 — Adaptive Cognition sequencing engine.

Owns ONLY: sequencing, timing, routing destination selection, optional node skipping.
Never creates, modifies, filters, or interprets business truth.
"""
from __future__ import annotations

import secrets
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, MutableMapping, Optional

# --- Path codes (Adaptive Cognitive Flow V2) ---
PATH_A_HEALTHY = "A"
PATH_B_ATTENTION = "B"
PATH_C_VIP = "C"
PATH_D_OPS = "D"
PATH_E_INSUFFICIENT = "E"
PATH_F_PENDING = "F"

PATH_LABELS = {
    PATH_A_HEALTHY: "Healthy",
    PATH_B_ATTENTION: "Attention",
    PATH_C_VIP: "VIP",
    PATH_D_OPS: "Operational",
    PATH_E_INSUFFICIENT: "Insufficient",
    PATH_F_PENDING: "Pending",
}

# Governed re-evaluation triggers only
TRIGGER_FULL_PAGE_REFRESH = "full_page_refresh"
TRIGGER_RETURN_FROM_SURFACE = "return_from_surface"
TRIGGER_MANUAL_REFRESH = "manual_refresh"
TRIGGER_SIGNIFICANT_STATE_TRANSITION = "significant_business_state_transition"
TRIGGER_SESSION_START = "session_start"

GOVERNED_TRIGGERS = frozenset(
    {
        TRIGGER_FULL_PAGE_REFRESH,
        TRIGGER_RETURN_FROM_SURFACE,
        TRIGGER_MANUAL_REFRESH,
        TRIGGER_SIGNIFICANT_STATE_TRANSITION,
        TRIGGER_SESSION_START,
    }
)

# Non-triggers (explicitly rejected)
REJECTED_TRIGGERS = frozenset(
    {
        "periodic_poll",
        "background_timer",
        "ui_hover",
        "scroll",
        "live_reshuffle",
    }
)


def _b(v: Any) -> bool:
    return bool(v)


@dataclass
class CognitionSessionV1:
    """Locked cognition session — path stable until a governed trigger."""

    session_id: str
    selected_path: str
    path_label: str
    locked_at_unix: float
    last_eval_trigger: str
    decision: dict[str, Any]
    truth_snapshot: dict[str, Any]
    reeval_count: int = 0
    view_ticks_while_locked: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)


# Process-local session store for validation lab / pre-Home wiring.
# Home merchant surface must use the same lock contract when wired later.
_SESSIONS: MutableMapping[str, CognitionSessionV1] = {}


def clear_cognitive_sessions_v1() -> None:
    """Test helper."""
    _SESSIONS.clear()


def fixture_truth_snapshots_v1() -> dict[str, dict[str, Any]]:
    """
    Governed-shaped truth snapshots for validation only.
    These are fixture inputs — the router does not invent business meaning.
    """
    return {
        "healthy": {
            "arrival": "A",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": False,
            "urgent_attention": False,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": True,
            "understanding_pending": False,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": None,
            "fixture_id": "healthy",
        },
        "vip": {
            "arrival": "B",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": True,
            "urgent_attention": True,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": True,
            "understanding_pending": False,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": "Communication",
            "fixture_id": "vip",
        },
        "attention": {
            "arrival": "B",
            "executive_summary_available": True,
            "store_change_eligible": True,
            "vip_primary": False,
            "urgent_attention": True,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": True,
            "understanding_pending": False,
            "reasoning_product_accepted": True,
            "bu_merchant_worthy": True,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": "Decision Workspace",
            "fixture_id": "attention",
        },
        "operational": {
            "arrival": "E",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": False,
            "urgent_attention": False,
            "ops_merchant_impacting": True,
            "ops_blocks_act": True,
            "data_sufficient": True,
            "understanding_pending": False,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": "Settings",
            "fixture_id": "operational",
        },
        "insufficient": {
            "arrival": "F",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": False,
            "urgent_attention": False,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": False,
            "understanding_pending": False,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": None,
            "fixture_id": "insufficient",
        },
        "pending": {
            "arrival": "C",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": False,
            "urgent_attention": False,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": True,
            "understanding_pending": True,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": None,
            "fixture_id": "pending",
        },
        "vip_resolved": {
            "arrival": "A",
            "executive_summary_available": True,
            "store_change_eligible": False,
            "vip_primary": False,
            "urgent_attention": False,
            "ops_merchant_impacting": False,
            "ops_blocks_act": False,
            "data_sufficient": True,
            "understanding_pending": False,
            "reasoning_product_accepted": False,
            "bu_merchant_worthy": False,
            "direction_approved": False,
            "direction_available": False,
            "primary_route": None,
            "fixture_id": "vip_resolved",
            "significant_transition": "vip_resolved",
        },
    }


def evaluate_cognitive_route_v1(
    truth: Mapping[str, Any],
    *,
    segment: str = "ENTRY",
) -> dict[str, Any]:
    """
    Deterministic path selection from governed truth snapshot.

    Does not alter `truth`. Does not invent business conclusions.
    """
    t = dict(truth)
    rationale: list[str] = []
    skipped: list[str] = []
    deferred: list[str] = []
    active: list[str] = ["Arrival"]
    route: Optional[str] = None
    interim_closure: Optional[str] = None
    path = PATH_A_HEALTHY

    ops = _b(t.get("ops_merchant_impacting"))
    vip = _b(t.get("vip_primary"))
    urgent = _b(t.get("urgent_attention"))
    arrival = str(t.get("arrival") or "").strip().upper()
    data_ok = _b(t.get("data_sufficient"))
    pending = _b(t.get("understanding_pending"))
    reasoning_ok = _b(t.get("reasoning_product_accepted")) and _b(
        t.get("bu_merchant_worthy")
    )
    direction_ok = _b(t.get("direction_approved")) and _b(t.get("direction_available"))
    ops_blocks = _b(t.get("ops_blocks_act"))

    if segment == "RETURN":
        rationale.append("R-RETURN-CONTINUE")
        # Post-return: continue deferred briefing; do not rediscover Arrival drama.
        active = ["ContextRestore"]
        if reasoning_ok:
            active.append("Understanding")
        else:
            skipped.append("Understanding")
            rationale.append("R-SKIP-HOLLOW-BU")
        if ops:
            active.append("Confidence")
        else:
            skipped.append("Confidence")
        if direction_ok:
            active.append("Direction")
        else:
            skipped.append("Direction")
            rationale.append("R-SKIP-HOLLOW-DIR")
        active.append("Closure")
        # Path identity on return follows residual urgency
        if ops:
            path = PATH_D_OPS
            rationale.append("R-SAFE-OPS")
        elif vip:
            path = PATH_C_VIP
            rationale.append("R-VIP")
        elif urgent:
            path = PATH_B_ATTENTION
            rationale.append("R-ACTION")
        else:
            path = PATH_A_HEALTHY
            rationale.append("R-HEALTHY")
        return _decision(
            path, active, skipped, deferred, None, "A", rationale, segment, t
        )

    # ENTRY precedence
    if ops:
        path = PATH_D_OPS
        rationale.append("R-SAFE-OPS")
        active += ["Confidence", "Closure", "Route"]
        skipped += ["Understanding", "Direction"]
        deferred += ["Understanding", "Direction"]
        interim_closure = "B"
        route = "Settings"
        rationale.append("R-DEFER-POST-RETURN")
    elif vip:
        path = PATH_C_VIP
        rationale.append("R-VIP")
        active += ["VIP Focus", "Closure", "Route"]
        skipped += ["Understanding", "Orientation", "Direction"]
        deferred += ["Confidence", "Direction"]
        interim_closure = "B"
        route = str(t.get("primary_route") or "Communication")
        if ops_blocks:
            active.insert(1, "Confidence")
            rationale.append("R-INLINE-TRUST")
        rationale.append("R-DEFER-POST-RETURN")
        rationale.append("R-SKIP-HOLLOW-BU")
    elif urgent:
        path = PATH_B_ATTENTION
        rationale.append("R-ACTION")
        active += ["Focus", "Closure", "Route"]
        skipped += ["Orientation", "Understanding", "Direction"]
        deferred += ["Understanding", "Confidence", "Direction"]
        interim_closure = "B"
        route = str(t.get("primary_route") or "Decision Workspace")
        rationale.append("R-DEFER-POST-RETURN")
    elif arrival in {"D", "F"} or not data_ok:
        path = PATH_E_INSUFFICIENT
        rationale.append("R-INSUFFICIENT")
        active += ["Orientation", "Closure"]
        skipped += ["Understanding", "Focus", "Confidence", "Direction"]
        interim_closure = "C"
        rationale.append("R-SKIP-HOLLOW-BU")
        rationale.append("R-SKIP-HOLLOW-DIR")
    elif arrival == "C" or pending:
        path = PATH_F_PENDING
        rationale.append("R-PENDING")
        active += ["Orientation", "Pending Understanding", "Closure"]
        skipped += ["Understanding", "Focus", "Direction"]
        interim_closure = "C"
        rationale.append("R-SKIP-HOLLOW-BU")
    else:
        path = PATH_A_HEALTHY
        rationale.append("R-HEALTHY")
        active += ["Orientation"]
        if reasoning_ok:
            active.append("Understanding")
        else:
            skipped.append("Understanding")
            rationale.append("R-SKIP-HOLLOW-BU")
        skipped.append("Focus")
        # Confidence silent when healthy
        skipped.append("Confidence")
        if direction_ok:
            active.append("Direction")
        else:
            skipped.append("Direction")
            rationale.append("R-SKIP-HOLLOW-DIR")
        active.append("Closure")
        interim_closure = "A"

    return _decision(
        path, active, skipped, deferred, route, interim_closure, rationale, segment, t
    )


def _decision(
    path: str,
    active: list[str],
    skipped: list[str],
    deferred: list[str],
    route: Optional[str],
    interim_closure: Optional[str],
    rationale: list[str],
    segment: str,
    truth: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "selected_path": path,
        "path_label": PATH_LABELS.get(path, path),
        "active_nodes": list(active),
        "skipped_nodes": list(skipped),
        "deferred_nodes": list(deferred),
        "interim_closure": interim_closure,
        "route_destination": route,
        "rationale_codes": list(rationale),
        "segment": segment,
        "ownership": {
            "router_owns": [
                "sequencing",
                "timing",
                "routing",
                "optional_node_skipping",
                "session_path_lock",
            ],
            "router_never_owns": [
                "business_truth",
                "knowledge_creation",
                "knowledge_modification",
                "truth_filtering",
                "business_interpretation",
                "decision_ownership",
            ],
            "truth_owners": [
                "Knowledge Platform",
                "Business Reasoning (when accepted)",
                "Merchant Alert Platform",
                "Operational Health",
            ],
        },
        # Echo fixture id only — not an interpretation
        "truth_fixture_id": truth.get("fixture_id"),
    }


def start_cognition_session_v1(
    truth: Mapping[str, Any],
    *,
    trigger: str = TRIGGER_SESSION_START,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a locked cognition session from governed truth."""
    if trigger not in GOVERNED_TRIGGERS:
        return {
            "ok": False,
            "error": "ungoverned_trigger",
            "trigger": trigger,
            "rejected": trigger in REJECTED_TRIGGERS,
        }
    decision = evaluate_cognitive_route_v1(truth, segment="ENTRY")
    sid = (session_id or "").strip() or secrets.token_urlsafe(16)
    now = time.time()
    sess = CognitionSessionV1(
        session_id=sid,
        selected_path=str(decision["selected_path"]),
        path_label=str(decision["path_label"]),
        locked_at_unix=now,
        last_eval_trigger=trigger,
        decision=decision,
        truth_snapshot=deepcopy(dict(truth)),
        reeval_count=0,
        view_ticks_while_locked=0,
        history=[
            {
                "event": "path_locked",
                "trigger": trigger,
                "path": decision["selected_path"],
                "at_unix": now,
            }
        ],
    )
    _SESSIONS[sid] = sess
    return _session_public(sess, event="session_started")


def view_tick_cognition_session_v1(session_id: str) -> dict[str, Any]:
    """
    Merchant continues reading — MUST NOT re-route.
    Proves path stability (no live cognitive reshuffling).
    """
    sess = _SESSIONS.get((session_id or "").strip())
    if not sess:
        return {"ok": False, "error": "session_not_found"}
    sess.view_ticks_while_locked += 1
    sess.history.append(
        {
            "event": "view_tick_stable",
            "path": sess.selected_path,
            "ticks": sess.view_ticks_while_locked,
            "at_unix": time.time(),
            "reevaluated": False,
        }
    )
    out = _session_public(sess, event="view_tick")
    out["path_unchanged"] = True
    out["reevaluated"] = False
    return out


def reevaluate_cognition_session_v1(
    session_id: str,
    *,
    trigger: str,
    truth: Optional[Mapping[str, Any]] = None,
    segment: str = "ENTRY",
) -> dict[str, Any]:
    """Re-evaluate only on governed triggers."""
    if trigger in REJECTED_TRIGGERS or trigger not in GOVERNED_TRIGGERS:
        return {
            "ok": False,
            "error": "ungoverned_trigger",
            "trigger": trigger,
            "message": "Periodic/background/UI reshuffle is forbidden.",
        }
    if trigger == TRIGGER_SESSION_START:
        return {
            "ok": False,
            "error": "invalid_reeval_trigger",
            "trigger": trigger,
        }
    sess = _SESSIONS.get((session_id or "").strip())
    if not sess:
        return {"ok": False, "error": "session_not_found"}

    snap = deepcopy(dict(truth)) if truth is not None else deepcopy(sess.truth_snapshot)
    if trigger == TRIGGER_RETURN_FROM_SURFACE:
        segment = "RETURN"

    prev_path = sess.selected_path
    decision = evaluate_cognitive_route_v1(snap, segment=segment)
    now = time.time()
    sess.selected_path = str(decision["selected_path"])
    sess.path_label = str(decision["path_label"])
    sess.locked_at_unix = now
    sess.last_eval_trigger = trigger
    sess.decision = decision
    sess.truth_snapshot = snap
    sess.reeval_count += 1
    sess.view_ticks_while_locked = 0
    sess.history.append(
        {
            "event": "governed_reevaluation",
            "trigger": trigger,
            "previous_path": prev_path,
            "new_path": sess.selected_path,
            "path_changed": prev_path != sess.selected_path,
            "at_unix": now,
        }
    )
    out = _session_public(sess, event="reevaluated")
    out["previous_path"] = prev_path
    out["path_changed"] = prev_path != sess.selected_path
    out["reevaluated"] = True
    return out


def get_cognition_session_v1(session_id: str) -> dict[str, Any]:
    sess = _SESSIONS.get((session_id or "").strip())
    if not sess:
        return {"ok": False, "error": "session_not_found"}
    return _session_public(sess, event="inspect")


def _session_public(sess: CognitionSessionV1, *, event: str) -> dict[str, Any]:
    return {
        "ok": True,
        "event": event,
        "session_id": sess.session_id,
        "selected_path": sess.selected_path,
        "path_label": sess.path_label,
        "locked": True,
        "locked_at_unix": sess.locked_at_unix,
        "last_eval_trigger": sess.last_eval_trigger,
        "reeval_count": sess.reeval_count,
        "view_ticks_while_locked": sess.view_ticks_while_locked,
        "decision": sess.decision,
        "history": list(sess.history),
        "stability_rule": (
            "Path remains locked until a governed re-evaluation trigger. "
            "No periodic background rerouting. No live cognitive reshuffling."
        ),
    }
