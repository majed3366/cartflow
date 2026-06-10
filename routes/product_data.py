# -*- coding: utf-8 -*-
"""Product Data Foundation v1 — read-only merchant health API."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from extensions import db
from json_response import j
from services.product_data.product_data_health_v1 import build_product_data_health_report
from services.product_data.product_foundation_governance_v1 import (
    build_product_foundation_governance_report,
)

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/product-data", tags=["product-data"])


@router.get("/health")
def api_product_data_health(
    request: Request,
    window_days: int = Query(7, ge=1, le=90),
    store_slug: Optional[str] = Query(None),
):
    """
    Product data readiness for authenticated merchants (read-only, no writes).
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
        report = build_product_data_health_report(
            db.session,
            slug,
            window_days=window_days,
        )
        return j(report.to_dict())
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api product-data/health: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)


@router.get("/governance/health")
def api_product_foundation_governance_health(
    request: Request,
    store_slug: Optional[str] = Query(None),
):
    """
    Product Foundation governance — read-only growth + query cost visibility.
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
        report = build_product_foundation_governance_report(db.session, slug)
        return j(report)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api product-data/governance/health: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
