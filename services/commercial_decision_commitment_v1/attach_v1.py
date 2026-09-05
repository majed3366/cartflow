# -*- coding: utf-8 -*-
"""Attach commercial commitment truth to dashboard summary (after COL)."""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Optional

from services.commercial_decision_commitment_v1.contract_v1 import (
    LAYER_VERSION,
    PHASE_TO_CONSOLE_MODE,
)
from services.commercial_decision_commitment_v1.service_v1 import (
    _row_public,
    derive_commitment_state,
    list_open_commitments,
)


def _nest_on_opp(opp: MutableMapping[str, Any], public: Mapping[str, Any]) -> None:
    opp["commitment"] = dict(public)
    # Server-derived console mode for Decision Console (not UI invent)
    mode = public.get("console_mode")
    if mode:
        opp["commitment_console_mode"] = mode


def attach_commitment_truth(
    summary: dict[str, Any],
    *,
    store_slug: Optional[str] = None,
) -> dict[str, Any]:
    """
    Shared Home/Workspace attach — +1 query list_open by store_slug.

    Does not mutate COL truth_class. Nests commitment read model onto matching
    opportunity objects when present. Backward compatible when zero rows.
    """
    if not isinstance(summary, dict):
        return summary
    slug = str(store_slug or summary.get("store_slug") or "").strip()[:191]
    empty = {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "by_opportunity_key": {},
        "open_count": 0,
        "query_delta": 0,
    }
    if not slug:
        summary["commercial_decision_commitment_v1"] = empty
        return summary

    try:
        rows = list_open_commitments(slug)
    except Exception:  # noqa: BLE001 — never break dashboard
        summary["commercial_decision_commitment_v1"] = {
            **empty,
            "ok": False,
            "error": "attach_failed",
        }
        return summary

    by_key: dict[str, Any] = {}
    for row in rows:
        pub = _row_public(row)
        by_key[row.opportunity_key] = pub

    payload = {
        "ok": True,
        "layer_version": LAYER_VERSION,
        "by_opportunity_key": by_key,
        "open_count": len(by_key),
        "query_delta": 1,
    }
    summary["commercial_decision_commitment_v1"] = payload

    col = summary.get("commercial_opportunity_layer_v1")
    if isinstance(col, dict):
        primary = col.get("primary")
        if isinstance(primary, dict):
            oid = str(primary.get("opportunity_id") or "")
            if oid in by_key:
                _nest_on_opp(primary, by_key[oid])
        secs = col.get("secondaries")
        if isinstance(secs, list):
            for s in secs:
                if isinstance(s, dict):
                    oid = str(s.get("opportunity_id") or "")
                    if oid in by_key:
                        _nest_on_opp(s, by_key[oid])

    return summary


def console_mode_for_opportunity(
    *,
    truth_class: str,
    commitment_phase: Optional[str],
) -> str:
    """Server helper: commitment phase wins; else COL-derived READY/INSUFFICIENT."""
    if commitment_phase:
        mode = PHASE_TO_CONSOLE_MODE.get(commitment_phase)
        if mode:
            return mode
    tc = str(truth_class or "")
    if tc == "PRODUCTION_PARTIAL":
        return "measuring"
    if tc == "PRODUCTION_TRUTH_READY":
        return "actionable"
    return "insufficient"


__all__ = [
    "attach_commitment_truth",
    "console_mode_for_opportunity",
    "derive_commitment_state",
]
