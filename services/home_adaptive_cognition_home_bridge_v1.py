# -*- coding: utf-8 -*-
"""
Merchant Home consumer of Adaptive Cognition Engine V2.

Owns sequencing attachment only. Never invents or mutates business truth content.
"""
from __future__ import annotations

import contextvars
import logging
from typing import Any, Mapping, MutableMapping, Optional

from services.home_cognitive_router_v1 import (
    GOVERNED_TRIGGERS,
    REJECTED_TRIGGERS,
    TRIGGER_FULL_PAGE_REFRESH,
    TRIGGER_MANUAL_REFRESH,
    TRIGGER_RETURN_FROM_SURFACE,
    TRIGGER_SESSION_START,
    TRIGGER_SIGNIFICANT_STATE_TRANSITION,
    evaluate_cognitive_route_v1,
    fixture_truth_snapshots_v1,
    get_cognition_session_v1,
    reevaluate_cognition_session_v1,
    start_cognition_session_v1,
)

log = logging.getLogger("cartflow.home_acf_bridge")

# Request-scoped cognition controls (set by summary API).
_acf_request_ctx: contextvars.ContextVar[Optional[dict[str, Any]]] = contextvars.ContextVar(
    "acf_home_request_v1", default=None
)

# Existing Home section keys (presentation components — not redesigned).
SECTION_BUSINESS_HEALTH = "business_health"
SECTION_REVENUE_RISK = "biggest_revenue_risk"
SECTION_OPPORTUNITY = "biggest_opportunity"
SECTION_PRIORITY = "todays_priority"
SECTION_UNDERSTANDING = "business_understanding"
SECTION_LEARNING = "learning_progress"
SECTION_TIMELINE = "business_timeline"

ALL_SECTIONS = (
    SECTION_BUSINESS_HEALTH,
    SECTION_REVENUE_RISK,
    SECTION_OPPORTUNITY,
    SECTION_PRIORITY,
    SECTION_UNDERSTANDING,
    SECTION_LEARNING,
    SECTION_TIMELINE,
)

# Path → presentation order (existing components only).
SECTION_ORDER_BY_PATH: dict[str, list[str]] = {
    # Healthy: Orientation → Understanding → Confidence/Direction (learning/timeline) → soft rest
    "A": [
        SECTION_BUSINESS_HEALTH,
        SECTION_UNDERSTANDING,
        SECTION_LEARNING,
        SECTION_TIMELINE,
        SECTION_OPPORTUNITY,
        SECTION_REVENUE_RISK,
        SECTION_PRIORITY,
    ],
    # Urgent attention: Focus early
    "B": [
        SECTION_BUSINESS_HEALTH,
        SECTION_PRIORITY,
        SECTION_REVENUE_RISK,
        SECTION_UNDERSTANDING,
        SECTION_OPPORTUNITY,
        SECTION_LEARNING,
        SECTION_TIMELINE,
    ],
    # VIP: Focus immediately; Understanding deferred
    "C": [
        SECTION_BUSINESS_HEALTH,
        SECTION_PRIORITY,
        SECTION_REVENUE_RISK,
        SECTION_LEARNING,
        SECTION_TIMELINE,
        SECTION_UNDERSTANDING,
        SECTION_OPPORTUNITY,
    ],
    # Operational: platform trust / priority before business interpretation
    "D": [
        SECTION_BUSINESS_HEALTH,
        SECTION_PRIORITY,
        SECTION_LEARNING,
        SECTION_UNDERSTANDING,
        SECTION_TIMELINE,
        SECTION_REVENUE_RISK,
        SECTION_OPPORTUNITY,
    ],
    # Insufficient: Orientation → Closure (minimal)
    "E": [
        SECTION_BUSINESS_HEALTH,
        SECTION_TIMELINE,
        SECTION_LEARNING,
        SECTION_UNDERSTANDING,
        SECTION_PRIORITY,
        SECTION_REVENUE_RISK,
        SECTION_OPPORTUNITY,
    ],
    # Pending understanding: honest pending via understanding section early
    "F": [
        SECTION_BUSINESS_HEALTH,
        SECTION_UNDERSTANDING,
        SECTION_LEARNING,
        SECTION_TIMELINE,
        SECTION_PRIORITY,
        SECTION_REVENUE_RISK,
        SECTION_OPPORTUNITY,
    ],
}

_VIEW_STABLE = "view_stable"
_ALLOWED_HOME_TRIGGERS = GOVERNED_TRIGGERS | {_VIEW_STABLE, ""}


def set_acf_home_request_context_v1(
    *,
    trigger: str = "",
    session_id: str = "",
    fixture: str = "",
) -> None:
    _acf_request_ctx.set(
        {
            "trigger": (trigger or "").strip(),
            "session_id": (session_id or "").strip(),
            "fixture": (fixture or "").strip().lower(),
        }
    )


def clear_acf_home_request_context_v1() -> None:
    _acf_request_ctx.set(None)


def get_acf_home_request_context_v1() -> dict[str, str]:
    raw = _acf_request_ctx.get()
    if not isinstance(raw, dict):
        return {"trigger": "", "session_id": "", "fixture": ""}
    return {
        "trigger": str(raw.get("trigger") or "").strip(),
        "session_id": str(raw.get("session_id") or "").strip(),
        "fixture": str(raw.get("fixture") or "").strip().lower(),
    }


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _attention_items(home: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    att = home.get("attention_today") or home.get("todays_priority") or {}
    if not isinstance(att, Mapping):
        return []
    items = list(att.get("items") or [])
    out: list[Mapping[str, Any]] = []
    for it in items:
        if isinstance(it, Mapping):
            out.append(it)
    primary = att.get("item")
    if isinstance(primary, Mapping):
        out.insert(0, primary)
    return out


def _item_text_blob(item: Mapping[str, Any]) -> str:
    parts = [
        item.get("title_ar"),
        item.get("headline_ar"),
        item.get("summary_ar"),
        item.get("decision_class"),
        item.get("operational_decision_key"),
        item.get("action_href"),
        item.get("drilldown_href"),
        item.get("kind"),
        item.get("topic"),
    ]
    return " ".join(_norm(p).lower() for p in parts if p is not None)


def _is_vip_item(item: Mapping[str, Any]) -> bool:
    blob = _item_text_blob(item)
    if "vip" in blob or "في آي بي" in blob or "vip" in _norm(item.get("lane")).lower():
        return True
    if "manual" in blob and ("intervention" in blob or "تواصل" in blob):
        return True
    cls = _norm(item.get("decision_class")).lower()
    if cls in ("critical_action",) and ("vip" in blob or "merchant_alert" in blob):
        return True
    return bool(item.get("vip") or item.get("is_vip") or item.get("vip_alert"))


def _is_ops_item(item: Mapping[str, Any]) -> bool:
    blob = _item_text_blob(item)
    op = _norm(item.get("operational_decision_key")).lower()
    href = _norm(item.get("action_href") or item.get("drilldown_href")).lower()
    if "settings" in href or "#settings" in href or "whatsapp" in href:
        return True
    if op.startswith("decision:fix_") or "channel" in op or "integration" in op:
        return True
    if any(
        k in blob
        for k in (
            "integration",
            "تكامل",
            "قناة",
            "واتساب غير",
            "communication unavailable",
            "paused",
            "متوقف",
            "إعداد",
        )
    ):
        return True
    return False


def build_truth_snapshot_from_home_v1(
    home: Mapping[str, Any],
    *,
    summary: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Derive router inputs from governed Home payload already composed.
    Does not invent business conclusions — only flags for sequencing.
    """
    summary = summary if isinstance(summary, Mapping) else {}
    health = home.get("business_health") if isinstance(home.get("business_health"), Mapping) else {}
    understanding = (
        home.get("business_understanding")
        if isinstance(home.get("business_understanding"), Mapping)
        else home.get("store_understanding")
        if isinstance(home.get("store_understanding"), Mapping)
        else {}
    )
    u_items = [
        it
        for it in list((understanding or {}).get("items") or [])
        if isinstance(it, Mapping)
    ]
    att_items = _attention_items(home)
    vip = any(_is_vip_item(it) for it in att_items)
    ops = any(_is_ops_item(it) for it in att_items)
    attention_required = bool(health.get("attention_required")) or bool(att_items)
    urgent = bool(attention_required or vip) and not ops
    if vip:
        urgent = True

    bu_worthy = bool(u_items) and any(
        _norm(it.get("confidence")).lower()
        in ("high", "confirmed", "medium", "emerging")
        for it in u_items
    )
    # Reasoning → Home still gated; treat merchant-worthy BU as present only when items exist.
    reasoning_accepted = bu_worthy
    data_ok = bool(
        _norm(health.get("summary_ar"))
        or _norm(health.get("status_ar"))
        or att_items
        or u_items
        or summary.get("ok")
    )
    status_l = _norm(health.get("status_ar")).lower()
    # Pending only when status explicitly signals forming — empty BU alone is Path A + hollow skip.
    pending = (not bu_worthy) and (not attention_required) and (not ops) and data_ok and any(
        token in status_l
        for token in ("قيد التقييم", "قيد التشكيل", "نتعلم", "pending", "forming")
    )

    if ops:
        arrival = "E"
    elif vip or (attention_required and att_items):
        arrival = "B"
    elif not data_ok:
        arrival = "F"
    elif pending:
        arrival = "C"
    else:
        arrival = "A"

    primary_route = None
    if vip:
        primary_route = "Communication"
    elif ops:
        primary_route = "Settings"
    elif att_items:
        href = _norm(att_items[0].get("action_href") or att_items[0].get("drilldown_href"))
        if "cart" in href.lower():
            primary_route = "Carts"
        else:
            primary_route = "Decision Workspace"

    return {
        "arrival": arrival,
        "executive_summary_available": bool(_norm(health.get("summary_ar")) or data_ok),
        "store_change_eligible": bool(
            isinstance(home.get("business_timeline") or home.get("while_away"), Mapping)
        ),
        "vip_primary": vip,
        "urgent_attention": bool(urgent and not ops),
        "ops_merchant_impacting": ops,
        "ops_blocks_act": ops,
        "data_sufficient": data_ok,
        "understanding_pending": pending,
        "reasoning_product_accepted": reasoning_accepted,
        "bu_merchant_worthy": bu_worthy,
        "direction_approved": bool(_norm(health.get("direction_ar"))),
        "direction_available": bool(_norm(health.get("direction_ar"))),
        "primary_route": primary_route,
        "fixture_id": "home_live",
        "truth_source": "merchant_home_experience_v1",
    }


def section_order_for_path_v1(path: str) -> list[str]:
    order = list(SECTION_ORDER_BY_PATH.get(path) or SECTION_ORDER_BY_PATH["A"])
    # Guarantee every section appears exactly once
    seen = set(order)
    for key in ALL_SECTIONS:
        if key not in seen:
            order.append(key)
    return order


def resolve_home_cognition_session_v1(
    truth: Mapping[str, Any],
    *,
    trigger: str = "",
    session_id: str = "",
) -> dict[str, Any]:
    """
    Session lock for Home:
    - view_stable / empty trigger + session → keep locked path (no live reshuffle)
    - governed trigger → re-evaluate
    - otherwise → start session
    """
    trig = (trigger or "").strip()
    sid = (session_id or "").strip()

    if trig in REJECTED_TRIGGERS:
        if sid:
            existing = get_cognition_session_v1(sid)
            if existing.get("ok"):
                out = dict(existing)
                out["reevaluated"] = False
                out["rejected_trigger"] = trig
                return out
        return {
            "ok": False,
            "error": "ungoverned_trigger",
            "trigger": trig,
            "message": "Periodic/background/UI reshuffle is forbidden.",
        }

    if sid and trig in ("", _VIEW_STABLE):
        existing = get_cognition_session_v1(sid)
        if existing.get("ok"):
            out = dict(existing)
            out["reevaluated"] = False
            out["path_unchanged"] = True
            return out
        # Worker miss / expired — deterministic restart (same truth → same path)
        return start_cognition_session_v1(truth, trigger=TRIGGER_SESSION_START)

    if sid and trig in GOVERNED_TRIGGERS and trig != TRIGGER_SESSION_START:
        out = reevaluate_cognition_session_v1(sid, trigger=trig, truth=truth)
        if out.get("ok"):
            return out
        # Session missing — start fresh under governed trigger
        return start_cognition_session_v1(
            truth,
            trigger=TRIGGER_SESSION_START
            if trig
            in (
                TRIGGER_FULL_PAGE_REFRESH,
                TRIGGER_MANUAL_REFRESH,
                TRIGGER_SIGNIFICANT_STATE_TRANSITION,
                TRIGGER_RETURN_FROM_SURFACE,
            )
            else TRIGGER_SESSION_START,
        )

    start_trigger = trig if trig in GOVERNED_TRIGGERS else TRIGGER_SESSION_START
    if start_trigger == TRIGGER_SESSION_START or start_trigger not in (
        TRIGGER_FULL_PAGE_REFRESH,
        TRIGGER_MANUAL_REFRESH,
        TRIGGER_RETURN_FROM_SURFACE,
        TRIGGER_SIGNIFICANT_STATE_TRANSITION,
        TRIGGER_SESSION_START,
    ):
        start_trigger = TRIGGER_SESSION_START
    return start_cognition_session_v1(truth, trigger=start_trigger)


def attach_adaptive_cognition_to_home_v1(
    home: MutableMapping[str, Any],
    *,
    summary: Optional[Mapping[str, Any]] = None,
    trigger: str = "",
    session_id: str = "",
    fixture: str = "",
) -> MutableMapping[str, Any]:
    """
    Attach adaptive_cognition_v1 sequencing metadata onto Home payload.
    Does not alter section content payloads.
    """
    if not isinstance(home, MutableMapping):
        return home

    ctx = get_acf_home_request_context_v1()
    trigger = (trigger or ctx.get("trigger") or "").strip()
    session_id = (session_id or ctx.get("session_id") or "").strip()
    fixture = (fixture or ctx.get("fixture") or "").strip().lower()

    live_truth = build_truth_snapshot_from_home_v1(home, summary=summary)
    fixtures = fixture_truth_snapshots_v1()
    if fixture and fixture in fixtures:
        # Product validation: force path sequencing; content stays live.
        router_truth = dict(fixtures[fixture])
        router_truth["truth_source"] = "fixture_override_for_sequence"
        router_truth["live_fixture_id"] = live_truth.get("fixture_id")
    else:
        router_truth = live_truth

    session = resolve_home_cognition_session_v1(
        router_truth, trigger=trigger, session_id=session_id
    )
    def _eligible_order(selected_path: str) -> list[str]:
        try:
            from services.home_semantic_composition_v1 import (  # noqa: PLC0415
                apply_path_eligibility_v1,
                filter_section_order_by_admission_v1,
            )

            # Semantic composition already ran in finalize; path eligibility only.
            if not isinstance(home.get("home_semantic_composition_v1"), Mapping):
                from services.home_semantic_composition_v1 import (  # noqa: PLC0415
                    apply_home_semantic_composition_v1,
                )

                apply_home_semantic_composition_v1(home)
            apply_path_eligibility_v1(home, path=selected_path)
            return filter_section_order_by_admission_v1(
                section_order_for_path_v1(selected_path),
                home,
                path=selected_path,
            )
        except Exception:  # noqa: BLE001
            return section_order_for_path_v1(selected_path)

    if not session.get("ok"):
        # Fallback: deterministic evaluate without session (never blank Home)
        decision = evaluate_cognitive_route_v1(router_truth, segment="ENTRY")
        path = str(decision.get("selected_path") or "A")
        order = _eligible_order(path)
        home["adaptive_cognition_v1"] = {
            "ok": True,
            "engine": "home_cognitive_router_v1",
            "consumer": "merchant_home",
            "selected_path": path,
            "path_label": decision.get("path_label"),
            "section_order": order,
            "admitted_sections": list(
                (home.get("home_semantic_composition_v1") or {}).get("admitted_sections")
                or order
            ),
            "suppressed_sections": list(
                (home.get("home_semantic_composition_v1") or {}).get("suppressed") or []
            ),
            "active_nodes": decision.get("active_nodes"),
            "skipped_nodes": decision.get("skipped_nodes"),
            "deferred_nodes": decision.get("deferred_nodes"),
            "rationale_codes": decision.get("rationale_codes"),
            "ownership": decision.get("ownership"),
            "session_id": None,
            "locked": False,
            "fallback": "evaluate_without_session",
            "stability_rule": (
                "Path remains locked until a governed re-evaluation trigger."
            ),
            "eligibility_rule": (
                "section_order includes only semantically admitted sections for this path"
            ),
        }
        return home

    path = str(session.get("selected_path") or "A")
    decision = session.get("decision") if isinstance(session.get("decision"), Mapping) else {}
    order = _eligible_order(path)
    home["adaptive_cognition_v1"] = {
        "ok": True,
        "engine": "home_cognitive_router_v1",
        "consumer": "merchant_home",
        "selected_path": path,
        "path_label": session.get("path_label"),
        "section_order": order,
        "admitted_sections": list(
            (home.get("home_semantic_composition_v1") or {}).get("admitted_sections")
            or order
        ),
        "suppressed_sections": list(
            (home.get("home_semantic_composition_v1") or {}).get("suppressed") or []
        ),
        "active_nodes": decision.get("active_nodes"),
        "skipped_nodes": decision.get("skipped_nodes"),
        "deferred_nodes": decision.get("deferred_nodes"),
        "rationale_codes": decision.get("rationale_codes"),
        "route_destination": decision.get("route_destination"),
        "interim_closure": decision.get("interim_closure"),
        "ownership": decision.get("ownership"),
        "session_id": session.get("session_id"),
        "locked": True,
        "locked_at_unix": session.get("locked_at_unix"),
        "last_eval_trigger": session.get("last_eval_trigger"),
        "reeval_count": session.get("reeval_count"),
        "reevaluated": bool(session.get("reevaluated")),
        "path_unchanged": bool(session.get("path_unchanged")),
        "stability_rule": session.get("stability_rule"),
        "fixture_override": fixture or None,
        "truth_source": router_truth.get("truth_source"),
        "eligibility_rule": (
            "section_order includes only semantically admitted sections for this path"
        ),
    }
    return home


def attach_adaptive_cognition_to_summary_v1(
    body: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Attach ACF onto summary.merchant_home_experience_v1 when present."""
    if not isinstance(body, MutableMapping):
        return body
    home = body.get("merchant_home_experience_v1")
    if not isinstance(home, dict):
        return body
    try:
        attach_adaptive_cognition_to_home_v1(home, summary=body)
    except Exception as exc:  # noqa: BLE001
        log.warning("adaptive cognition home attach failed: %s", exc)
    return body


__all__ = [
    "ALL_SECTIONS",
    "SECTION_ORDER_BY_PATH",
    "attach_adaptive_cognition_to_home_v1",
    "attach_adaptive_cognition_to_summary_v1",
    "build_truth_snapshot_from_home_v1",
    "clear_acf_home_request_context_v1",
    "get_acf_home_request_context_v1",
    "resolve_home_cognition_session_v1",
    "section_order_for_path_v1",
    "set_acf_home_request_context_v1",
]
