# -*- coding: utf-8 -*-
"""Merchant Daily Brief v1 — read-only governed decision consumer API."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from extensions import db
from json_response import j
from services.merchant_daily_brief_v1 import build_merchant_daily_brief_api_payload

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/daily-brief")
def api_dashboard_daily_brief(
    request: Request,
    store_slug: Optional[str] = Query(None),
):
    """
    Daily operational brief — consumes merchant_decisions_v1 only.
    """
    from services.merchant_test_widget_store_v1 import (  # noqa: PLC0415
        merchant_authenticated_store_slug,
    )

    auth_slug = merchant_authenticated_store_slug(cookies=dict(request.cookies))
    if not auth_slug:
        return j({"ok": False, "error": "unauthorized"}, 401)

    slug = (store_slug or auth_slug or "").strip()[:255]
    if slug != auth_slug:
        return j({"ok": False, "error": "forbidden"}, 403)

    try:
        db.create_all()
        from services.dashboard_store_context import dashboard_canonical_store_row  # noqa: PLC0415

        dash_store = dashboard_canonical_store_row(slug, allow_schema_warm=False)
        payload = build_merchant_daily_brief_api_payload(
            db.session,
            slug,
            dash_store,
        )
        return j(payload)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api dashboard/daily-brief: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
