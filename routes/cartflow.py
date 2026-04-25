# -*- coding: utf-8 -*-
"""واجهات ‎CartFlow‎ للوحة (تحليلات الاسترجاع)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Path
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import CartRecoveryLog

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/cartflow", tags=["cartflow"])


SENT_STATUSES = frozenset({"sent_real", "mock_sent"})


@router.get("/analytics/{store_slug}")
def get_recovery_analytics(
    store_slug: str = Path(..., min_length=1, max_length=255, description="معرّف المتجر"),
) -> Any:
    """
    مقاييس أداء الاسترجاع من ‎CartRecoveryLog‎ (لكل ‎status‎ / ‎step‎).
    """
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return j({"ok": False, "error": "store_slug_required"}, 400)

    try:
        db.create_all()
        base = db.session.query(CartRecoveryLog).filter(
            CartRecoveryLog.store_slug == ss
        )

        total_attempts = base.count()
        sent_real = base.filter(CartRecoveryLog.status == "sent_real").count()
        failed_final = base.filter(CartRecoveryLog.status == "failed_final").count()
        stopped_converted = base.filter(
            CartRecoveryLog.status == "stopped_converted"
        ).count()

        steps: dict[str, dict[str, int]] = {}
        for n, key in ((1, "step1"), (2, "step2"), (3, "step3")):
            sub = base.filter(CartRecoveryLog.step == n)
            sent = sub.filter(CartRecoveryLog.status.in_(SENT_STATUSES)).count()
            conv = sub.filter(CartRecoveryLog.status == "stopped_converted").count()
            steps[key] = {"sent": sent, "converted": conv}

        return j(
            {
                "ok": True,
                "store_slug": ss,
                "total_attempts": total_attempts,
                "sent_real": sent_real,
                "failed_final": failed_final,
                "stopped_converted": stopped_converted,
                "revenue_recovered": 0.0,
                "steps": steps,
            }
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        log.warning("cartflow analytics: %s", e)
        return j({"ok": False, "error": "query_failed"}, 500)
