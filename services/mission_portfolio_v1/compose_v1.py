# -*- coding: utf-8 -*-
"""Mission Portfolio V1 — compose governance read model over catalog + CDC."""
from __future__ import annotations

from typing import Any, Mapping, Optional

from services.mission_portfolio_v1.conflict_v1 import evaluate_conflict_v1
from services.mission_portfolio_v1.contract_v1 import (
    LAYER_SCHEMA,
    LAYER_VERSION,
    MAX_ACTIVE_MISSIONS,
    MAX_SECONDARY_READY,
    REASON_CATALOG_SUPPRESSED,
    REASON_CLOSED_FREED,
    REASON_INSUFFICIENT,
    REASON_SAFE_SECONDARY,
    SLOT_PHASES,
)


def _phase(card: Mapping[str, Any] | None) -> Optional[str]:
    if not isinstance(card, Mapping):
        return None
    p = card.get("cdc_phase")
    if p:
        s = str(p).strip()
        if s and s != "None":
            return s
    c = card.get("commitment")
    if isinstance(c, Mapping):
        ph = c.get("phase")
        if ph:
            s = str(ph).strip()
            if s and s != "None":
                return s
        if c.get("closed_at"):
            return "CLOSED"
    return None


def _is_closed(card: Mapping[str, Any] | None) -> bool:
    if not isinstance(card, Mapping):
        return False
    c = card.get("commitment")
    if isinstance(c, Mapping) and c.get("closed_at"):
        return True
    return _phase(card) == "CLOSED"


def _owns_slot(card: Mapping[str, Any] | None) -> bool:
    if _is_closed(card):
        return False
    return _phase(card) in SLOT_PHASES


def _slim_card(card: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not isinstance(card, Mapping):
        return None
    return {
        "opportunity_id": card.get("opportunity_id"),
        "family": card.get("family"),
        "title_ar": card.get("title_ar"),
        "cdc_phase": _phase(card),
        "truth_class": card.get("truth_class"),
        "mission_ready": card.get("mission_ready"),
        "action_ar": card.get("action_ar"),
        "why_ar": card.get("why_ar"),
    }


def empty_portfolio_package_v1(*, reason: str = "empty") -> dict[str, Any]:
    return {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "schema": LAYER_SCHEMA,
        "empty": True,
        "empty_reason": reason,
        "question_ar": "ما الذي يجب أن أعمل عليه الآن، وما الذي يجب أن أؤجله؟",
        "active_mission": None,
        "next_mission": None,
        "deferred": [],
        "suppressed": [],
        "safe_secondaries": [],
        "capacity": {
            "max_active": MAX_ACTIVE_MISSIONS,
            "active_count": 0,
            "available_slots": MAX_ACTIVE_MISSIONS,
            "max_secondary_ready": MAX_SECONDARY_READY,
        },
        "reasons": [
            {
                "code": REASON_INSUFFICIENT
                if reason in ("insufficient", "empty", "catalog_empty")
                else reason,
                "opportunity_id": None,
                "family": None,
                "detail": reason,
            }
        ],
        "query_delta": 0,
    }


def compose_mission_portfolio_v1(
    *,
    catalog_package: Mapping[str, Any] | None,
    store_slug: str = "",
) -> dict[str, Any]:
    """
    In-memory portfolio over mission_catalog_v1 cards.

    Does not rerank commercial importance. query_delta: 0.
    """
    cat = catalog_package if isinstance(catalog_package, Mapping) else {}
    if not cat or cat.get("ok") is False:
        return empty_portfolio_package_v1(reason="catalog_missing")

    primary = cat.get("primary") if isinstance(cat.get("primary"), Mapping) else None
    secondaries = [
        s for s in (cat.get("secondaries") or []) if isinstance(s, Mapping)
    ]
    catalog_suppressed = [
        s for s in (cat.get("suppressed") or []) if isinstance(s, Mapping)
    ]

    if not primary and not secondaries:
        pkg = empty_portfolio_package_v1(reason="insufficient")
        pkg["store_slug"] = store_slug
        # Carry catalog suppressions as portfolio suppressed mirror
        pkg["suppressed"] = [
            {
                "opportunity_id": s.get("opportunity_id"),
                "family": s.get("family"),
                "conflict_type": None,
                "reason_code": REASON_CATALOG_SUPPRESSED,
                "catalog_code": s.get("code"),
            }
            for s in catalog_suppressed
        ]
        return pkg

    # Active slot: catalog primary if it owns CDC slot; else first secondary that owns
    active: Optional[Mapping[str, Any]] = None
    if _owns_slot(primary):
        active = primary
    else:
        for s in secondaries:
            if _owns_slot(s):
                active = s
                break

    # Closed primary with no other slot owner → capacity freed (next = primary if READY)
    if primary and _is_closed(primary) and active is None:
        # Treat as no active; primary may still be stale closed card — prefer non-closed
        pass

    reasons: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    safe_secondaries: list[dict[str, Any]] = []
    suppressed: list[dict[str, Any]] = []

    for s in catalog_suppressed:
        suppressed.append(
            {
                "opportunity_id": s.get("opportunity_id"),
                "family": s.get("family"),
                "conflict_type": None,
                "reason_code": REASON_CATALOG_SUPPRESSED,
                "catalog_code": s.get("code"),
            }
        )
        reasons.append(
            {
                "code": REASON_CATALOG_SUPPRESSED,
                "opportunity_id": s.get("opportunity_id"),
                "family": s.get("family"),
                "detail": s.get("code"),
            }
        )

    active_count = 1 if active is not None else 0
    available = max(0, MAX_ACTIVE_MISSIONS - active_count)

    if active is not None:
        next_mission = active
        reasons.append(
            {
                "code": "continuity_active_slot",
                "opportunity_id": active.get("opportunity_id"),
                "family": active.get("family"),
                "detail": _phase(active),
            }
        )
        # Evaluate every other catalog surface card
        pool: list[Mapping[str, Any]] = []
        if primary is not None and primary is not active:
            pool.append(primary)
        for s in secondaries:
            if s is active:
                continue
            if str(s.get("opportunity_id") or "") == str(
                active.get("opportunity_id") or ""
            ):
                continue
            pool.append(s)

        for cand in pool:
            ev = evaluate_conflict_v1(active=active, candidate=cand)
            entry = {
                "opportunity_id": cand.get("opportunity_id"),
                "family": cand.get("family"),
                "title_ar": cand.get("title_ar"),
                "conflict_type": ev["conflict_type"],
                "reason_code": ev["reason_code"],
            }
            if not ev["may_execute"]:
                deferred.append(entry)
                reasons.append(
                    {
                        "code": ev["reason_code"],
                        "opportunity_id": cand.get("opportunity_id"),
                        "family": cand.get("family"),
                        "detail": ev["conflict_type"],
                    }
                )
            elif ev["may_surface_secondary"] and len(safe_secondaries) < MAX_SECONDARY_READY:
                safe_secondaries.append(
                    {
                        **_slim_card(cand),
                        "reason_code": REASON_SAFE_SECONDARY,
                    }
                )
                reasons.append(
                    {
                        "code": REASON_SAFE_SECONDARY,
                        "opportunity_id": cand.get("opportunity_id"),
                        "family": cand.get("family"),
                        "detail": "visible_no_slot",
                    }
                )
            else:
                deferred.append(entry)
    else:
        # No slot owner — catalog primary is next (READY compete)
        next_mission = primary
        if primary and _is_closed(primary):
            # Capacity released; if primary closed, try first secondary as next
            next_mission = secondaries[0] if secondaries else None
            reasons.append(
                {
                    "code": REASON_CLOSED_FREED,
                    "opportunity_id": primary.get("opportunity_id"),
                    "family": primary.get("family"),
                    "detail": "closed",
                }
            )
        for s in secondaries:
            if next_mission is not None and str(s.get("opportunity_id") or "") == str(
                next_mission.get("opportunity_id") or ""
            ):
                continue
            ev = evaluate_conflict_v1(active=None, candidate=s)
            if ev["may_surface_secondary"] and len(safe_secondaries) < MAX_SECONDARY_READY:
                safe_secondaries.append(
                    {
                        **(_slim_card(s) or {}),
                        "reason_code": REASON_SAFE_SECONDARY,
                    }
                )
                reasons.append(
                    {
                        "code": REASON_SAFE_SECONDARY,
                        "opportunity_id": s.get("opportunity_id"),
                        "family": s.get("family"),
                        "detail": "visible_no_slot",
                    }
                )

    is_empty = next_mission is None and active is None
    return {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "schema": LAYER_SCHEMA,
        "empty": is_empty,
        "store_slug": store_slug,
        "question_ar": "ما الذي يجب أن أعمل عليه الآن، وما الذي يجب أن أؤجله؟",
        "active_mission": _slim_card(active),
        "next_mission": _slim_card(next_mission),
        "deferred": deferred,
        "suppressed": suppressed,
        "safe_secondaries": safe_secondaries[:MAX_SECONDARY_READY],
        "capacity": {
            "max_active": MAX_ACTIVE_MISSIONS,
            "active_count": active_count,
            "available_slots": available,
            "max_secondary_ready": MAX_SECONDARY_READY,
        },
        "reasons": reasons,
        "slot_phases": sorted(SLOT_PHASES),
        "ready_consumes_capacity": False,
        "query_delta": 0,
    }


def portfolio_allows_accept_v1(portfolio: Mapping[str, Any] | None) -> dict[str, Any]:
    """
    Read-model gate helper (does not change mission accept authority).

    Returns whether capacity would allow a new accept.
    """
    if not isinstance(portfolio, Mapping) or not portfolio.get("ok"):
        return {"allowed": False, "reason_code": "portfolio_unavailable"}
    cap = portfolio.get("capacity") if isinstance(portfolio.get("capacity"), Mapping) else {}
    avail = int(cap.get("available_slots") or 0)
    if avail < 1:
        return {
            "allowed": False,
            "reason_code": "active_mission_occupies_capacity",
            "available_slots": avail,
        }
    return {"allowed": True, "reason_code": None, "available_slots": avail}


__all__ = [
    "compose_mission_portfolio_v1",
    "empty_portfolio_package_v1",
    "portfolio_allows_accept_v1",
]
