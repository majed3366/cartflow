# -*- coding: utf-8 -*-
"""
Read-only live activation state inspection for GET /api/dashboard/summary.

No stage resolution changes — logging and slim response shape only.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Mapping, Optional

log = logging.getLogger("cartflow")


def _truthy_query(val: str | None) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def wants_activation_inspect(request: Any) -> bool:
    qp = getattr(request, "query_params", None)
    if qp is None:
        return False
    return _truthy_query(qp.get("activation_inspect"))


def infer_ui_blocker_inferred(
    act: Mapping[str, Any],
    dbg: Mapping[str, Any],
) -> str:
    """Server-side inference (DOM / hash timing not available here)."""
    if not act:
        return "missing_merchant_activation"
    display = str(act.get("activation_display") or "")
    if display == "hidden":
        reasons = dbg.get("production_signal_reasons") or act.get(
            "production_signal_reasons"
        )
        if reasons:
            return "server_activation_display_hidden"
        return "server_activation_display_hidden_no_production_reasons"
    if display == "compact":
        return "server_should_render_compact"
    if display == "prominent":
        return "server_should_render_prominent"
    return "server_unknown_activation_display"


def activation_inspect_response(body: Mapping[str, Any]) -> dict[str, Any]:
    act = body.get("merchant_activation") if isinstance(body, Mapping) else {}
    if not isinstance(act, dict):
        act = {}
    dbg = body.get("merchant_activation_visibility_debug")
    if dbg is None:
        dbg = act.get("activation_visibility_debug")
    if not isinstance(dbg, dict):
        dbg = {}
    return {
        "merchant_activation": {
            "home_stage": act.get("home_stage"),
            "activation_display": act.get("activation_display"),
            "hide_setup_card": act.get("hide_setup_card"),
            "production_signal_reasons": act.get("production_signal_reasons")
            if act.get("production_signal_reasons") is not None
            else dbg.get("production_signal_reasons"),
            "milestones": act.get("milestones"),
        },
        "merchant_activation_visibility_debug": dbg,
    }


def log_activation_state_from_summary(body: Mapping[str, Any]) -> None:
    snap = activation_inspect_response(body)
    act = snap["merchant_activation"]
    dbg = snap.get("merchant_activation_visibility_debug") or {}
    blocker = infer_ui_blocker_inferred(act, dbg if isinstance(dbg, dict) else {})
    milestones = act.get("milestones")
    try:
        milestones_s = json.dumps(milestones, ensure_ascii=False, default=str)
    except TypeError:
        milestones_s = repr(milestones)
    reasons = act.get("production_signal_reasons")
    try:
        reasons_s = json.dumps(reasons, ensure_ascii=False)
    except TypeError:
        reasons_s = repr(reasons)
    log.info(
        "[ACTIVATION STATE]\n"
        "home_stage=%s\n"
        "activation_display=%s\n"
        "hide_setup_card=%s\n"
        "production_signal_reasons=%s\n"
        "milestones=%s\n"
        "ui_blocker_inferred=%s",
        act.get("home_stage"),
        act.get("activation_display"),
        act.get("hide_setup_card"),
        reasons_s,
        milestones_s,
        blocker,
    )


__all__ = [
    "activation_inspect_response",
    "infer_ui_blocker_inferred",
    "log_activation_state_from_summary",
    "wants_activation_inspect",
]
