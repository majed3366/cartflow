# -*- coding: utf-8 -*-
"""Merchant Daily Brief v1 — read-only governed decision consumer API.

INV-002 WP-4: identity from Platform Identity Authority (MQIC) — not
route-local legacy auth-slug resolution.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from extensions import db
from json_response import j
from services.identity_authority import (
    IdentityError,
    attach_daily_brief_identity_observability,
    bind_mqic_for_daily_brief,
    clear_mqic,
)
from services.merchant_daily_brief_v1 import build_merchant_daily_brief_api_payload

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _bind_daily_brief_mqic(request: Request):
    """Bind MQIC once for this Daily Brief request; 401 if unauthenticated."""
    clear_mqic()
    try:
        mqic = bind_mqic_for_daily_brief(cookies=dict(request.cookies))
    except IdentityError:
        clear_mqic()
        return None
    return mqic


@router.get("/daily-brief")
def api_dashboard_daily_brief(
    request: Request,
    store_slug: Optional[str] = Query(None),
):
    """
    Daily operational brief — consumes merchant_decisions_v1 only.

    Identity from Platform Identity Authority (MQIC) — not route-local resolve.
    """
    mqic = _bind_daily_brief_mqic(request)
    if mqic is None:
        return j({"ok": False, "error": "unauthorized"}, 401)

    try:
        query_slug = (store_slug or "").strip()[:255]
        if query_slug and query_slug != mqic.store_slug:
            return j({"ok": False, "error": "forbidden"}, 403)

        db.create_all()
        from services.dashboard_store_context import dashboard_canonical_store_row  # noqa: PLC0415

        slug = mqic.store_slug
        dash_store = dashboard_canonical_store_row(slug, allow_schema_warm=False)
        payload = build_merchant_daily_brief_api_payload(
            db.session,
            slug,
            dash_store,
            mqic=mqic,
        )
        attach_daily_brief_identity_observability(payload)
        return j(payload)
    except IdentityError as exc:
        log.warning("api dashboard/daily-brief identity: %s", exc)
        clear_mqic()
        code = getattr(exc, "code", "") or ""
        if code == "store_slug_mismatch":
            return j({"ok": False, "error": "forbidden"}, 403)
        return j({"ok": False, "error": "unauthorized"}, 401)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api dashboard/daily-brief: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
    finally:
        clear_mqic()
