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

_EMPTY_ACTIVATION = {
    "home_stage": None,
    "activation_display": None,
    "hide_setup_card": None,
    "production_signal_reasons": [],
    "milestones": [],
}


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


def resolve_activation_inspect_context(
    dash_store: Any,
    *,
    cookies: Optional[dict[str, str]] = None,
) -> tuple[Optional[int], str]:
    merchant_id: Optional[int] = None
    store_slug = ""
    try:
        from services.merchant_onboarding_store import (  # noqa: PLC0415
            resolve_merchant_onboarding_store,
        )

        _, resolution = resolve_merchant_onboarding_store(cookies=cookies or {})
        merchant_id = resolution.merchant_id
    except Exception:  # noqa: BLE001
        merchant_id = None
    if dash_store is not None:
        store_slug = (getattr(dash_store, "zid_store_id", None) or "").strip()
    return merchant_id, store_slug


def log_activation_inspect_error(
    exc: BaseException,
    *,
    merchant_id: Optional[int] = None,
    store_slug: str = "",
) -> None:
    log.error(
        "[ACTIVATION INSPECT ERROR]\n"
        "error=%s: %s\n"
        "merchant_id=%s\n"
        "store_slug=%s",
        type(exc).__name__,
        str(exc)[:800],
        merchant_id if merchant_id is not None else "—",
        store_slug or "—",
        exc_info=True,
    )


def build_activation_inspect_body(
    dash_store: Any,
    *,
    cookies: Optional[dict[str, str]] = None,
    month_abandoned: int = 0,
    month_recovered: int = 0,
    month_revenue: float = 0.0,
) -> dict[str, Any]:
    """Activation-only summary body (no KPI / reason queries)."""
    from services.merchant_activation_v1 import (  # noqa: PLC0415
        build_merchant_activation_api_payload,
    )

    act = build_merchant_activation_api_payload(
        dash_store,
        cookies=cookies,
        month_abandoned=int(month_abandoned),
        month_recovered=int(month_recovered),
        month_revenue=float(month_revenue or 0.0),
    )
    dbg = None
    if isinstance(act, dict):
        dbg = act.get("activation_visibility_debug")
    return {
        "merchant_activation": act if isinstance(act, dict) else {},
        "merchant_activation_visibility_debug": dbg,
    }


def activation_inspect_error_payload(
    exc: BaseException,
    *,
    merchant_id: Optional[int] = None,
    store_slug: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": "activation_inspect_failed",
        "activation_inspect_error": {
            "type": type(exc).__name__,
            "message": str(exc)[:800],
            "merchant_id": merchant_id,
            "store_slug": store_slug or None,
        },
        "merchant_activation": dict(_EMPTY_ACTIVATION),
        "merchant_activation_visibility_debug": None,
    }


def activation_inspect_http_response(
    exc: BaseException,
    dash_store: Any,
    *,
    cookies: Optional[dict[str, str]] = None,
) -> Any:
    """Return JSONResponse-like dict for FastAPI j() helper."""
    merchant_id, store_slug = resolve_activation_inspect_context(
        dash_store, cookies=cookies
    )
    log_activation_inspect_error(
        exc, merchant_id=merchant_id, store_slug=store_slug
    )
    return activation_inspect_error_payload(
        exc, merchant_id=merchant_id, store_slug=store_slug
    )


__all__ = [
    "activation_inspect_error_payload",
    "activation_inspect_http_response",
    "activation_inspect_response",
    "build_activation_inspect_body",
    "infer_ui_blocker_inferred",
    "log_activation_inspect_error",
    "log_activation_state_from_summary",
    "resolve_activation_inspect_context",
    "wants_activation_inspect",
]
