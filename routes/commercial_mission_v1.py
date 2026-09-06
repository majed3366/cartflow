# -*- coding: utf-8 -*-
"""Merchant routes for Commercial Mission (generic families over CDC)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from json_response import j

router = APIRouter(
    prefix="/api/commercial-mission/v1",
    tags=["commercial-mission-v1"],
)


def _auth_slug(request: Request) -> Optional[str]:
    from services.merchant_auth_v1 import resolve_authenticated_store_slug  # noqa: PLC0415

    slug = resolve_authenticated_store_slug(dict(request.cookies))
    return (slug or "").strip()[:191] or None


def _col_package_for_store(store_slug: str) -> dict[str, Any]:
    from extensions import db  # noqa: PLC0415
    from models import Store  # noqa: PLC0415
    from services.commercial_opportunity_layer_v1.compose_v1 import (  # noqa: PLC0415
        compose_commercial_opportunity_layer_v1,
    )
    from services.dashboard_kpi_time_v1 import (  # noqa: PLC0415
        merchant_reason_counts_store_window,
    )

    store = (
        db.session.query(Store)
        .filter(Store.zid_store_id == store_slug)
        .first()
    )
    try:
        counts = merchant_reason_counts_store_window(store, days=7) if store else {}
    except Exception:  # noqa: BLE001
        counts = {}
    summary = {
        "store_slug": store_slug,
        "merchant_reason_counts_week": dict(counts or {}),
    }
    return compose_commercial_opportunity_layer_v1(summary, store_slug=store_slug)


class CommitmentIdBody(BaseModel):
    model_config = {"extra": "forbid"}

    commitment_id: str = Field(..., min_length=8, max_length=36)


@router.post("/accept")
def api_mission_accept(request: Request) -> Any:
    from services.commercial_mission_v1 import (  # noqa: PLC0415
        MissionError,
        accept_mission,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    col = _col_package_for_store(auth)
    try:
        return j(accept_mission(store_slug=auth, col_package=col))
    except MissionError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


@router.post("/confirm-execution")
def api_mission_confirm_execution(request: Request, body: CommitmentIdBody) -> Any:
    from services.commercial_mission_v1 import (  # noqa: PLC0415
        MissionError,
        confirm_mission_execution,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    col = _col_package_for_store(auth)
    try:
        return j(
            confirm_mission_execution(
                store_slug=auth,
                commitment_id=body.commitment_id,
                col_package=col,
            )
        )
    except MissionError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


@router.post("/recheck")
def api_mission_recheck(request: Request, body: CommitmentIdBody) -> Any:
    from services.commercial_mission_v1 import (  # noqa: PLC0415
        MissionError,
        recheck_mission,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    col = _col_package_for_store(auth)
    try:
        return j(
            recheck_mission(
                store_slug=auth,
                commitment_id=body.commitment_id,
                col_package=col,
            )
        )
    except MissionError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


@router.post("/abandon")
def api_mission_abandon(request: Request, body: CommitmentIdBody) -> Any:
    from services.commercial_mission_v1 import (  # noqa: PLC0415
        MissionError,
        abandon_mission,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    try:
        return j(
            abandon_mission(store_slug=auth, commitment_id=body.commitment_id)
        )
    except MissionError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


__all__ = ["router"]
