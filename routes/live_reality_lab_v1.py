# -*- coding: utf-8 -*-
"""
Live Reality Lab V1 — authenticated lab-only control routes.

Never trust client store_slug. Auth session must resolve to cf_live_reality_lab.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from json_response import j

router = APIRouter(
    prefix="/api/live-reality-lab/v1",
    tags=["live-reality-lab-v1"],
)


def _auth_slug(request: Request) -> Optional[str]:
    from services.merchant_auth_v1 import resolve_authenticated_store_slug  # noqa: PLC0415

    slug = resolve_authenticated_store_slug(dict(request.cookies))
    return (slug or "").strip()[:191] or None


def _assert_query_slug(request: Request, auth: str) -> Optional[Any]:
    """Query store_slug is assertion-only. It never selects the tenant."""
    claimed = (request.query_params.get("store_slug") or "").strip()
    if claimed and claimed != auth:
        return j({"ok": False, "error": "live_reality_lab_tenant_mismatch"}, 403)
    return None


class ScenarioBody(BaseModel):
    model_config = {"extra": "forbid"}

    scenario_id: str = Field(..., min_length=2, max_length=64)


@router.post("/ensure")
def api_lab_ensure(request: Request) -> Any:
    """Idempotent lab tenant bootstrap — lab merchant session OR missing store bootstrap.

    Bootstrap without session is intentionally denied: ops must create via
    ensure_live_reality_lab_tenant_v1() from authorized tooling, then login.
    """
    from services.live_reality_lab_v1 import (  # noqa: PLC0415
        LAB_STORE_SLUG,
        ensure_live_reality_lab_tenant_v1,
        is_live_reality_lab_tenant,
    )
    from extensions import db  # noqa: PLC0415
    from models import Store  # noqa: PLC0415

    auth = _auth_slug(request)
    store = (
        db.session.query(Store).filter(Store.zid_store_id == LAB_STORE_SLUG).first()
    )
    if store is None:
        # First-time ensure: require no auth spoof — only empty DB ops path.
        # Still refuse if caller authenticated as another merchant.
        if auth and auth != LAB_STORE_SLUG:
            return j({"ok": False, "error": "live_reality_lab_unauthorized_tenant"}, 403)
        out = ensure_live_reality_lab_tenant_v1()
        return j(out)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    if auth != LAB_STORE_SLUG or not is_live_reality_lab_tenant(store=store):
        return j({"ok": False, "error": "live_reality_lab_unauthorized_tenant"}, 403)
    out = ensure_live_reality_lab_tenant_v1()
    return j(out)


@router.get("/scenarios")
def api_lab_scenarios(request: Request) -> Any:
    from services.live_reality_lab_v1 import LAB_STORE_SLUG  # noqa: PLC0415
    from services.live_reality_lab_v1.dataset_v1 import (  # noqa: PLC0415
        all_scenario_manifests,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    if auth != LAB_STORE_SLUG:
        return j({"ok": False, "error": "live_reality_lab_unauthorized_tenant"}, 403)
    manifests = all_scenario_manifests()
    return j(
        {
            "ok": True,
            "store_slug": LAB_STORE_SLUG,
            "scenarios": sorted(manifests.keys()),
            "manifests": manifests,
        }
    )


@router.post("/reset")
def api_lab_reset(request: Request) -> Any:
    from services.live_reality_lab_v1 import reset_lab_tenant_data_v1  # noqa: PLC0415

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    mismatch = _assert_query_slug(request, auth)
    if mismatch is not None:
        return mismatch
    try:
        return j(reset_lab_tenant_data_v1(authenticated_store_slug=auth))
    except ValueError as exc:
        return j({"ok": False, "error": str(exc)}, 403)


@router.post("/apply")
def api_lab_apply(request: Request, body: ScenarioBody) -> Any:
    from services.live_reality_lab_v1 import apply_lab_scenario_v1  # noqa: PLC0415

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    mismatch = _assert_query_slug(request, auth)
    if mismatch is not None:
        return mismatch
    # Ignore any client-supplied store identity — auth slug only.
    try:
        return j(
            apply_lab_scenario_v1(
                authenticated_store_slug=auth,
                scenario_id=body.scenario_id,
            )
        )
    except ValueError as exc:
        code = str(exc)
        status = 400 if "unknown_scenario" in code else 403
        return j({"ok": False, "error": code}, status)


@router.post("/verify")
def api_lab_verify(request: Request, body: ScenarioBody) -> Any:
    from services.live_reality_lab_v1 import verify_lab_scenario_v1  # noqa: PLC0415

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    mismatch = _assert_query_slug(request, auth)
    if mismatch is not None:
        return mismatch
    try:
        out = verify_lab_scenario_v1(
            authenticated_store_slug=auth,
            scenario_id=body.scenario_id,
        )
        return j(out, 200 if out.get("ok") else 409)
    except ValueError as exc:
        code = str(exc)
        status = 400 if "unknown_scenario" in code else 403
        return j({"ok": False, "error": code}, status)
