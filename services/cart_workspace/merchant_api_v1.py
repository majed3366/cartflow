# -*- coding: utf-8 -*-
"""
Cart Workspace merchant API v1 — flag-gated projection + commands.
Paint consumers only; no Admit on GET.
"""
from __future__ import annotations

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
    """
    Same merchant store identity as Home / Living Store review.

    Do not use ``merchant_authenticated_store_slug`` here: it rejects demo via
    ``is_widget_recovery_zid`` (widget sandbox guard). That made Decision
    Workspace return 401 while Home read ``store_slug=demo`` — Reality
    Validation FIRST divergence after Living Store bind.
    """
    from services.merchant_auth_v1 import (  # noqa: PLC0415
        resolve_authenticated_store_slug,
    )

    slug = resolve_authenticated_store_slug(dict(request.cookies))
    return (slug or "").strip()[:255] or None


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
        "mission_question": "ماذا يجب أن أقرر الآن، ولماذا؟",
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

    degraded = False
    degrade_reason = None
    projection: dict[str, Any] = {}
    zone_assignment = None
    try:
        # Silent Success: auto-seed once if merchant has no open Decisions.
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
        try:
            from services.cart_workspace.business_findings_enrichment_v1 import (  # noqa: PLC0415
                enrich_projection_with_fde_v1,
            )

            projection = enrich_projection_with_fde_v1(projection, auth)
            snap["projection"] = projection
        except Exception as enrich_exc:  # noqa: BLE001
            degraded = True
            degrade_reason = f"enrich:{type(enrich_exc).__name__}"
    except Exception as exc:  # noqa: BLE001
        # Reality Validation: Workspace must never hard-fail the merchant surface.
        degraded = True
        degrade_reason = f"projection:{type(exc).__name__}:{exc}"[:240]
        projection = _empty_quiet_projection(auth)

    # Stamp identity for CEO Reality Validation (same dataset proof).
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

    return j(
        {
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
        }
    )


@router.post("/commands")
def api_cart_workspace_command(request: Request, body: CommandBody):
    if not cart_workspace_v1_enabled():
        return j({"ok": False, "error": "feature_flag_off"}, 404)
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    try:
        result = execute_command(
            store=SHADOW_STORE,
            store_slug=auth,
            decision_id=body.decision_id,
            command_type=body.command_type,
            actor_merchant_user_id=auth,
            command_id=body.command_id,
            payload=body.payload,
        )
        return j(result)
    except CommandError as e:
        return j({"ok": False, "error": e.code, "message": str(e)}, 400)


@router.post("/demo-seed")
def api_cart_workspace_demo_seed(request: Request):
    """
    Internal comprehension seed — only when flag ON.
    Does not invent Product rules; runs governed Admit path for curated candidacy.
    """
    if not cart_workspace_v1_enabled():
        return j({"ok": False, "error": "feature_flag_off"}, 404)
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    # Reset only this merchant's open set by using fresh evaluate into store;
    # full store reset would affect other slugs in same process — filter by closing none,
    # seed adds new recovery_keys unique per slug.
    out = seed_merchant_comprehension_set(auth, SHADOW_STORE)
    return j(
        {
            "ok": True,
            "store_slug": auth,
            "projection": out["snapshot"]["projection"],
            "seeded": out["seeded"],
            "flag": cart_workspace_v1_flag_state(),
        }
    )
