# -*- coding: utf-8 -*-
"""Knowledge Layer v1 — read-only merchant API (INV-002 WP-2: MQIC consumer)."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Query, Request

from extensions import db
from json_response import j
from services.identity_authority import (
    IdentityError,
    attach_knowledge_identity_observability,
    clear_mqic,
)
from services.identity_authority.reality_attach_composition_v1 import (
    merchant_request_identity_bind,
)
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
            report = build_knowledge_report(
                db.session,
                mqic.store_slug,
                window_days=window_days,
                mqic=mqic,
            )
            payload = report.to_dict()
            from services.merchant_claim_evidence_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_claim_evidence_v1,
            )

            enrich_knowledge_report_claim_evidence_v1(payload)
            from services.knowledge_producer_metadata_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_producer_metadata_v1,
            )

            enrich_knowledge_report_producer_metadata_v1(payload)
            from services.merchant_decision_layer_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_merchant_decisions_v1,
            )

            enrich_knowledge_report_merchant_decisions_v1(payload)
            from services.knowledge_layer_projection_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_kl_routing_and_projection_v1,
            )

            enrich_knowledge_report_kl_routing_and_projection_v1(payload)
            from services.commercial_interpretation_v1 import (  # noqa: PLC0415
                enrich_knowledge_report_commercial_interpretation_v1,
            )

            enrich_knowledge_report_commercial_interpretation_v1(
                payload,
                store_slug=mqic.store_slug,
            )
            attach_knowledge_identity_observability(payload)
            return j(payload)
    except IdentityError as exc:
        log.warning("api knowledge/report identity: %s", exc)
        clear_mqic()
        code = getattr(exc, "code", "") or ""
        if code in ("store_slug_mismatch", "attach_membership_denied"):
            return j({"ok": False, "error": "forbidden"}, 403)
        return j({"ok": False, "error": "unauthorized"}, 401)
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

    Identity from Platform Identity Authority (MQIC).
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
            health = build_knowledge_health(
                db.session,
                mqic.store_slug,
                window_days=window_days,
                mqic=mqic,
            )
            payload = health.to_dict()
            if isinstance(payload, dict):
                attach_knowledge_identity_observability(payload)
            return j(payload)
    except IdentityError as exc:
        log.warning("api knowledge/health identity: %s", exc)
        clear_mqic()
        return j({"ok": False, "error": "forbidden"}, 403)
    except (OSError, TypeError, ValueError) as exc:
        log.warning("api knowledge/health: %s", exc)
        return j({"ok": False, "error": "failed"}, 500)
