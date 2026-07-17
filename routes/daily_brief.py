# -*- coding: utf-8 -*-
"""Merchant Daily Brief v1 — read-only governed decision consumer API.

INV-002 WP-4: identity from Platform Identity Authority (MQIC) — not
route-local legacy auth-slug resolution.
INV-002 RC-3: optional Reality Attach composition before bind.
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
    clear_mqic,
)
from services.identity_authority.reality_attach_composition_v1 import (
    merchant_request_identity_bind,
)
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

    Identity from Platform Identity Authority (MQIC) — not route-local resolve.
    RC-3: optional Reality Attach via Lab headers before bind.
    """
    try:
        with merchant_request_identity_bind(
            cookies=dict(request.cookies),
            headers=request.headers,
        ) as mqic:
            if mqic is None:
                return j({"ok": False, "error": "unauthorized"}, 401)

            query_slug = (store_slug or "").strip()[:255]
            if query_slug and query_slug != mqic.store_slug:
                return j({"ok": False, "error": "forbidden"}, 403)

            db.create_all()
            from services.dashboard_store_context import (  # noqa: PLC0415
                dashboard_canonical_store_row,
            )

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
        if code in ("store_slug_mismatch", "attach_membership_denied"):
            return j({"ok": False, "error": "forbidden"}, 403)
        return j({"ok": False, "error": "unauthorized"}, 401)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api dashboard/daily-brief: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
    finally:
        clear_mqic()
