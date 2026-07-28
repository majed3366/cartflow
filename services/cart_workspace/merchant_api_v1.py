# -*- coding: utf-8 -*-
"""
Cart Workspace merchant API v1 — flag-gated projection + commands.

Gate 0 (Performance Recovery): Home architectural parity —
paint cache → durable decision_workspace snapshot → enrich fallback.
No request-time ORV/facts/situations when snapshot/package reusable.
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

    from services.decision_workspace_v2.perf_timeline_v1 import (  # noqa: PLC0415
        workspace_perf_attach_to_payload,
        workspace_perf_begin,
        workspace_perf_end,
        workspace_perf_meta,
        workspace_perf_note,
        workspace_perf_stage,
        workspace_perf_wants_from_request,
    )

    want_perf = workspace_perf_wants_from_request(request)
    if want_perf:
        workspace_perf_begin(label="workspace_projection")

    paint_cache_hit = False
    durable_snapshot_hit = False
    serve_path = "unknown"
    degraded = False
    degrade_reason = None
    projection: dict[str, Any] = {}
    zone_assignment = None

    try:
        from services.decision_workspace_v2.paint_cache_v1 import (  # noqa: PLC0415
            workspace_paint_cache_get,
            workspace_paint_cache_set,
        )
        from services.decision_workspace_v2.snapshot_serve_v1 import (  # noqa: PLC0415
            read_decision_workspace_snapshot_v1,
        )

        with workspace_perf_stage("auth_ready"):
            pass

        with workspace_perf_stage("paint_cache_lookup"):
            cached = workspace_paint_cache_get(auth)
        if isinstance(cached, dict) and (
            cached.get("zone_b") is not None or cached.get("quiet")
        ):
            projection = cached
            paint_cache_hit = True
            serve_path = "paint_cache"
            workspace_perf_meta(paint_cache="hit", durable_snapshot="skipped")
            zone_assignment = {
                "zone_a": [],
                "zone_b": [
                    c.get("decision_id")
                    for c in list(projection.get("zone_b") or [])
                    if isinstance(c, dict)
                ],
            }
        else:
            workspace_perf_meta(paint_cache="miss")
            with workspace_perf_stage("durable_snapshot_read", cache="lookup"):
                snap_proj = read_decision_workspace_snapshot_v1(auth)
            if isinstance(snap_proj, dict) and (
                snap_proj.get("zone_b") is not None or snap_proj.get("quiet")
            ):
                projection = snap_proj
                durable_snapshot_hit = True
                serve_path = "durable_snapshot"
                meta = dict(projection.pop("_workspace_snapshot_v1", None) or {})
                workspace_perf_meta(
                    durable_snapshot="hit",
                    snapshot_stale=bool(meta.get("stale")),
                    snapshot_version=meta.get("version"),
                )
                workspace_perf_note("serve_durable_workspace_snapshot")
                zone_assignment = {
                    "zone_a": [],
                    "zone_b": [
                        c.get("decision_id")
                        for c in list(projection.get("zone_b") or [])
                        if isinstance(c, dict)
                    ],
                }
                try:
                    workspace_paint_cache_set(auth, projection)
                except Exception:  # noqa: BLE001
                    pass
            else:
                workspace_perf_meta(durable_snapshot="miss")
                serve_path = "enrich_fallback"
                with workspace_perf_stage("shadow_projection"):
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

                    with workspace_perf_stage("enrich_compose_budget"):
                        projection = enrich_projection_with_fde_v1(projection, auth)
                    snap["projection"] = projection
                    workspace_paint_cache_set(auth, projection)
                    # Persist so the next request is Home-parity snapshot-read.
                    try:
                        from models import Store  # noqa: PLC0415
                        from extensions import db  # noqa: PLC0415

                        row = (
                            db.session.query(Store.id)
                            .filter(Store.zid_store_id == auth)
                            .first()
                        )
                        if row is not None:
                            sid = int(row[0] if isinstance(row, tuple) else row.id)
                            with workspace_perf_stage("durable_snapshot_write"):
                                from services.dashboard_snapshot_change_v1 import (  # noqa: PLC0415
                                    write_dashboard_snapshot_guarded,
                                )
                                from services.decision_workspace_v2.snapshot_serve_v1 import (  # noqa: PLC0415
                                    SNAPSHOT_TYPE_DECISION_WORKSPACE,
                                )

                                write_dashboard_snapshot_guarded(
                                    store_id=sid,
                                    store_slug=auth,
                                    snapshot_type=SNAPSHOT_TYPE_DECISION_WORKSPACE,
                                    payload={
                                        "ok": True,
                                        "store_slug": auth,
                                        "invalidated": False,
                                        "projection": projection,
                                        "zone_assignment": zone_assignment,
                                        "gate_workspace_snapshot_v1": True,
                                        "source": "request_fallback",
                                    },
                                )
                    except Exception:  # noqa: BLE001
                        workspace_perf_note("durable_snapshot_write_skipped")
                except Exception as enrich_exc:  # noqa: BLE001
                    degraded = True
                    degrade_reason = f"enrich:{type(enrich_exc).__name__}"
    except Exception as exc:  # noqa: BLE001
        degraded = True
        degrade_reason = f"projection:{type(exc).__name__}:{exc}"[:240]
        projection = _empty_quiet_projection(auth)
        serve_path = "degraded_empty"

    with workspace_perf_stage("identity_stamp"):
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

    with workspace_perf_stage("serialization"):
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
            "workspace_paint_cache_hit": paint_cache_hit,
            "workspace_durable_snapshot_hit": durable_snapshot_hit,
            "workspace_serve_path": serve_path,
            "decision_workspace_refinement_v1": bool(
                (projection or {}).get("decision_workspace_refinement_v1")
            ),
        }

    if want_perf:
        workspace_perf_meta(
            paint_cache="hit" if paint_cache_hit else "miss",
            durable_snapshot="hit" if durable_snapshot_hit else "miss",
            serve_path=serve_path,
        )
        report = workspace_perf_end()
        workspace_perf_attach_to_payload(payload, report)

    return j(payload)


@router.post("/commands")
def api_cart_workspace_command(request: Request, body: CommandBody):
    if not cart_workspace_v1_enabled():
        return j({"ok": False, "error": "feature_flag_off"}, 404)
    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)

    try:
        from services.decision_workspace_v2.snapshot_serve_v1 import (  # noqa: PLC0415
            invalidate_decision_workspace_snapshot_v1,
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
        invalidate_decision_workspace_snapshot_v1(store_id=None, store_slug=auth)
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

    from services.decision_workspace_v2.snapshot_serve_v1 import (  # noqa: PLC0415
        invalidate_decision_workspace_snapshot_v1,
    )

    out = seed_merchant_comprehension_set(auth, SHADOW_STORE)
    invalidate_decision_workspace_snapshot_v1(store_id=None, store_slug=auth)
    return j(
        {
            "ok": True,
            "store_slug": auth,
            "projection": out["snapshot"]["projection"],
            "seeded": out["seeded"],
            "flag": cart_workspace_v1_flag_state(),
        }
    )
