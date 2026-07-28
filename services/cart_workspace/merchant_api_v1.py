# -*- coding: utf-8 -*-
"""
Cart Workspace merchant API v1 — flag-gated projection + commands.
Paint consumers only; no Admit on GET.
Refinement V1: short paint cache + optional workspace_perf timeline.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from json_response import j
from services.cart_workspace.commands_v1 import CommandError, execute_command
from services.cart_workspace.feature_flag_v1 import (
    cart_workspace_v1_enabled,
    cart_workspace_v1_flag_state,
)
from services.cart_workspace.merchant_seed_v1 import seed_merchant_comprehension_set
from services.cart_workspace.projection_v1 import build_workspace_projection
from services.cart_workspace.shadow_pipeline_v1 import shadow_snapshot
from services.cart_workspace.shadow_store_v1 import SHADOW_STORE
from services.cart_workspace.silent_success_flag_v1 import cart_workspace_silent_success_enabled

router = APIRouter(prefix="/api/cart-workspace/v1", tags=["cart-workspace-merchant"])


def _auth_slug(request: Request) -> Optional[str]:
    from services.merchant_auth_v1 import (  # noqa: PLC0415
        resolve_authenticated_store_slug,
    )

    slug = resolve_authenticated_store_slug(dict(request.cookies))
    return (slug or "").strip()[:255] or None


def _workspace_perf_wants(request: Request) -> bool:
    try:
        qp = getattr(request, "query_params", None)
        if qp is not None and str(qp.get("workspace_perf") or "").strip() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


class CommandBody(BaseModel):
    decision_id: str = Field(..., min_length=1)
    command_type: str = Field(..., min_length=1)
    command_id: Optional[str] = None
    payload: Optional[dict[str, Any]] = None


def _empty_quiet_projection(store_slug: str) -> dict[str, Any]:
    return {
        "store_slug": store_slug,
        "zone_a": [],
        "zone_b": [],
        "quiet": True,
        "mission_question": "ما القرار الذي يجب أن أتخذه الآن، ولماذا؟",
        "degraded_load": True,
        "gate_2_single_decision_owner": True,
    }


@router.get("/projection")
def api_cart_workspace_projection(request: Request):
    if not cart_workspace_v1_enabled():
        return j(
            {
                "ok": False,
                "error": "feature_flag_off",
                "flag": cart_workspace_v1_flag_state(),
            },
            404,
        )
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    want_perf = _workspace_perf_wants(request)
    t0 = time.perf_counter()
    stages: list[dict[str, Any]] = []
    cache_hit = False

    def _stage(name: str, started: float) -> None:
        if not want_perf:
            return
        stages.append(
            {
                "stage": name,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )

    degraded = False
    degrade_reason = None
    projection: dict[str, Any] = {}
    zone_assignment = None

    try:
        from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
            workspace_paint_cache_get,
            workspace_paint_cache_set,
        )

        t_cache = time.perf_counter()
        cached = workspace_paint_cache_get(auth)
        _stage("paint_cache_lookup", t_cache)
        if isinstance(cached, dict) and (
            cached.get("zone_b") is not None or cached.get("quiet")
        ):
            projection = cached
            cache_hit = True
            zone_assignment = {
                "zone_a": [],
                "zone_b": [
                    c.get("decision_id")
                    for c in list(projection.get("zone_b") or [])
                    if isinstance(c, dict)
                ],
            }
        else:
            t_shadow = time.perf_counter()
            if cart_workspace_silent_success_enabled() and not SHADOW_STORE.open_decisions(
                auth
            ):
                seed_merchant_comprehension_set(auth, SHADOW_STORE)

            snap = shadow_snapshot(auth, store=SHADOW_STORE)
            if not snap.get("projection"):
                proj = build_workspace_projection(auth, SHADOW_STORE)
                snap["projection"] = proj.to_dict()
            projection = dict(snap.get("projection") or {})
            zone_assignment = snap.get("zone_assignment")
            _stage("shadow_projection", t_shadow)

            try:
                from services.cart_workspace.business_findings_enrichment_v1 import (  # noqa: PLC0415
                    enrich_projection_with_fde_v1,
                )

                t_enrich = time.perf_counter()
                projection = enrich_projection_with_fde_v1(projection, auth)
                _stage("enrich_compose_budget", t_enrich)
                snap["projection"] = projection
                workspace_paint_cache_set(auth, projection)
            except Exception as enrich_exc:  # noqa: BLE001
                degraded = True
                degrade_reason = f"enrich:{type(enrich_exc).__name__}"
    except Exception as exc:  # noqa: BLE001
        degraded = True
        degrade_reason = f"projection:{type(exc).__name__}:{exc}"[:240]
        projection = _empty_quiet_projection(auth)

    t_id = time.perf_counter()
    try:
        from services.reality_validation_context_v1 import (  # noqa: PLC0415
            stamp_reality_validation_identity_from_summary_v1,
        )

        holder = {"commerce_situations_v1": projection.get("commerce_situations_v1")}
        stamp_reality_validation_identity_from_summary_v1(
            holder, store_slug=auth, cookies=dict(request.cookies)
        )
        projection["reality_validation_identity_v1"] = holder.get(
            "reality_validation_identity_v1"
        )
    except Exception:  # noqa: BLE001
        pass
    _stage("identity_stamp", t_id)

    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    payload: dict[str, Any] = {
        "ok": True,
        "store_slug": auth,
        "projection": projection,
        "zone_assignment": zone_assignment,
        "projection_version": projection.get("projection_version"),
        "flag": cart_workspace_v1_flag_state(),
        "merchant_surface_active": True,
        "silent_success_mode": cart_workspace_silent_success_enabled(),
        "degraded": degraded,
        "degrade_reason": degrade_reason,
        "reality_validation_identity_v1": projection.get(
            "reality_validation_identity_v1"
        ),
        "gate_2_single_decision_owner": True,
        "gate_2a_decision_workspace_completion": True,
        "gate_2b_decision_composition_engine": bool(
            (projection or {}).get("gate_2b_decision_composition_engine")
        ),
        "gate_2c_decision_portfolio": bool(
            (projection or {}).get("gate_2c_decision_portfolio")
        ),
        "workspace_paint_cache_hit": cache_hit,
        "decision_workspace_refinement_v1": bool(
            (projection or {}).get("decision_workspace_refinement_v1")
        ),
    }
    if want_perf:
        payload["_workspace_perf_timeline_v1"] = {
            "total_ms": total_ms,
            "cache_hit": cache_hit,
            "stages": stages,
        }
    return j(payload)


@router.post("/commands")
def api_cart_workspace_command(request: Request, body: CommandBody):
    if not cart_workspace_v1_enabled():
        return j({"ok": False, "error": "feature_flag_off"}, 404)
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    try:
        from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
            workspace_paint_cache_clear,
        )

        result = execute_command(
            store=SHADOW_STORE,
            store_slug=auth,
            decision_id=body.decision_id,
            command_type=body.command_type,
            actor_merchant_user_id=auth,
            command_id=body.command_id,
            payload=body.payload,
        )
        workspace_paint_cache_clear(auth)
        return j(result)
    except CommandError as e:
        return j({"ok": False, "error": e.code, "message": str(e)}, 400)


@router.post("/demo-seed")
def api_cart_workspace_demo_seed(request: Request):
    if not cart_workspace_v1_enabled():
        return j({"ok": False, "error": "feature_flag_off"}, 404)
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
        workspace_paint_cache_clear,
    )

    out = seed_merchant_comprehension_set(auth, SHADOW_STORE)
    workspace_paint_cache_clear(auth)
    return j(
        {
            "ok": True,
            "store_slug": auth,
            "projection": out["snapshot"]["projection"],
            "seeded": out["seeded"],
            "flag": cart_workspace_v1_flag_state(),
        }
    )
