# -*- coding: utf-8 -*-
"""Bounded PLATFORM_PAID backfill design. Default execute=False. No USER_CLAIM."""
from __future__ import annotations

from typing import Any, Callable, Optional

from extensions import db
from models import PurchaseTruthRecord
from services.cartflow_purchase_truth import _PLATFORM_PAID_SOURCES
from services.order_economic_fact_v1.capture import capture_after_platform_paid
from services.order_economic_fact_v1.persist import get_order_economic_fact


def eligible_platform_paid_order_ids(store_slug: str, *, limit: int = 20) -> list[str]:
    slug = (store_slug or "").strip()
    if not slug:
        return []
    cap = max(1, min(int(limit), 50))
    rows = (
        db.session.query(PurchaseTruthRecord.order_id)
        .filter(
            PurchaseTruthRecord.store_slug == slug,
            PurchaseTruthRecord.purchase_detected.is_(True),
            PurchaseTruthRecord.purchase_source.in_(tuple(_PLATFORM_PAID_SOURCES)),
            PurchaseTruthRecord.order_id.isnot(None),
            PurchaseTruthRecord.order_id != "",
        )
        .distinct()
        .limit(cap)
        .all()
    )
    return [str(r[0]).strip() for r in rows if r and r[0]]


def backfill_order_economic_facts(
    *,
    store_slug: str,
    limit: int = 20,
    execute: bool = False,
    fetch_order_view: Optional[Callable] = None,
) -> dict[str, Any]:
    """Dry-run by default. Does not run bulk history. USER_CLAIM / PRE_PURCHASE excluded."""
    ids = eligible_platform_paid_order_ids(store_slug, limit=limit)
    missing = [oid for oid in ids if get_order_economic_fact(store_slug=store_slug, external_order_id=oid) is None]
    plan = {
        "execute": bool(execute),
        "eligible": ids,
        "missing": missing,
        "ran": [],
    }
    if not execute:
        return plan
    ran = []
    for oid in missing:
        ran.append(
            capture_after_platform_paid(
                purchase_source="zid_webhook:platform_paid",
                store_slug=store_slug,
                external_order_id=oid,
                fetch_order_view=fetch_order_view,
            )
        )
    plan["ran"] = ran
    return plan
