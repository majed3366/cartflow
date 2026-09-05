# -*- coding: utf-8 -*-
"""Thin merchant routes for Commercial Decision Commitment V1."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from json_response import j

router = APIRouter(
    prefix="/api/commercial-decision-commitment/v1",
    tags=["commercial-decision-commitment-v1"],
)


def _auth_slug(request: Request) -> Optional[str]:
    from services.merchant_auth_v1 import resolve_authenticated_store_slug  # noqa: PLC0415

    slug = resolve_authenticated_store_slug(dict(request.cookies))
    return (slug or "").strip()[:191] or None


def _col_package_for_store(store_slug: str) -> dict[str, Any]:
    """Resolve current COL package for accept (evidence check)."""
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


class AcceptBody(BaseModel):
    model_config = {"extra": "forbid"}

    opportunity_key: str = Field(..., min_length=3, max_length=255)
    action_summary: str = Field("", max_length=512)
    proposed_metric_key: Optional[str] = Field(None, max_length=128)


class StartMeasurementBody(BaseModel):
    model_config = {"extra": "forbid"}

    commitment_id: str = Field(..., min_length=8, max_length=36)
    authority: str = Field(..., min_length=3, max_length=64)
    measurement_start_ref: str = Field("", max_length=191)
    metric_key: str = Field(..., min_length=1, max_length=128)
    metric_value: Optional[float] = None
    truth_class_at_start: str = Field("", max_length=64)
    recheck_condition: str = Field("", max_length=2000)


class CloseBody(BaseModel):
    model_config = {"extra": "forbid"}

    commitment_id: str = Field(..., min_length=8, max_length=36)
    close_reason: str = Field(..., min_length=3, max_length=64)
    close_note: str = Field("", max_length=200)


@router.post("/accept")
def api_accept_commitment(request: Request, body: AcceptBody) -> Any:
    from services.commercial_decision_commitment_v1 import (  # noqa: PLC0415
        CommitmentError,
        accept_commitment,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    col = _col_package_for_store(auth)
    try:
        result = accept_commitment(
            store_slug=auth,
            opportunity_key=body.opportunity_key,
            col_package=col,
            action_summary=body.action_summary,
            proposed_metric_key=body.proposed_metric_key,
        )
        return j(result)
    except CommitmentError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


@router.post("/start-measurement")
def api_start_measurement(request: Request, body: StartMeasurementBody) -> Any:
    from services.commercial_decision_commitment_v1 import (  # noqa: PLC0415
        CommitmentError,
        start_measurement,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    try:
        result = start_measurement(
            store_slug=auth,
            commitment_id=body.commitment_id,
            authority=body.authority,
            measurement_start_ref=body.measurement_start_ref,
            metric_key=body.metric_key,
            metric_value=body.metric_value,
            truth_class_at_start=body.truth_class_at_start,
            recheck_condition=body.recheck_condition,
        )
        return j(result)
    except CommitmentError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


@router.post("/close")
def api_close_commitment(request: Request, body: CloseBody) -> Any:
    from services.commercial_decision_commitment_v1 import (  # noqa: PLC0415
        CommitmentError,
        close_commitment,
    )

    auth = _auth_slug(request)
    if not auth:
        return j({"ok": False, "error": "unauthorized"}, 401)
    try:
        result = close_commitment(
            store_slug=auth,
            commitment_id=body.commitment_id,
            close_reason=body.close_reason,
            actor="merchant",
            close_note=body.close_note,
        )
        return j(result)
    except CommitmentError as exc:
        return j({"ok": False, "error": exc.code}, exc.http_status)


__all__ = ["router"]
