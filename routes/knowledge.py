# -*- coding: utf-8 -*-
"""Knowledge Layer v1 — read-only merchant API."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from extensions import db
from json_response import j
from services.knowledge_health_v1 import build_knowledge_health
from services.knowledge_layer_v1 import build_knowledge_report

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/report")
def api_knowledge_report(
    request: Request,
    window_days: int = Query(7, ge=1, le=90),
    store_slug: Optional[str] = Query(None),
):
    """
    Evidence-based store insights for authenticated merchants (read-only).
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
        report = build_knowledge_report(db.session, slug, window_days=window_days)
        payload = report.to_dict()
        from services.merchant_claim_evidence_v1 import (  # noqa: PLC0415
            enrich_knowledge_report_claim_evidence_v1,
        )

        enrich_knowledge_report_claim_evidence_v1(payload)
        return j(payload)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api knowledge/report: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)


@router.get("/health")
def api_knowledge_health(
    request: Request,
    window_days: int = Query(7, ge=1, le=90),
    store_slug: Optional[str] = Query(None),
):
    """
    Read-only Knowledge Layer health for authenticated merchants.
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
        health = build_knowledge_health(db.session, slug, window_days=window_days)
        return j(health.to_dict())
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api knowledge/health: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
