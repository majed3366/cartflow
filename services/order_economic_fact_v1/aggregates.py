# -*- coding: utf-8 -*-
"""Persisted-fact aggregates. No Zid GET. Same currency only."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from extensions import db
from models import OrderEconomicFact
from schema_order_economic_fact_v1 import ensure_order_economic_fact_schema
from services.order_economic_fact_v1.contract import SAFE_AGGREGATE_TERM, SAFE_AOV_TERM, TRUTH_VERSION
from integrations.zid_order_economic_v1 import parse_money


def _window_query(
    *,
    store_slug: str,
    currency: str,
    window_start: datetime,
    window_end: datetime,
    truth_version: str = TRUTH_VERSION,
):
    slug = (store_slug or "").strip()
    cur = (currency or "").strip().upper()
    if not slug or not cur or window_start is None or window_end is None:
        return None
    if window_end <= window_start:
        return None
    ensure_order_economic_fact_schema(db)
    return (
        db.session.query(OrderEconomicFact)
        .filter(
            OrderEconomicFact.store_slug == slug,
            OrderEconomicFact.currency == cur,
            OrderEconomicFact.truth_version == truth_version,
            OrderEconomicFact.payment_state == "paid",
            OrderEconomicFact.observed_at >= window_start,
            OrderEconomicFact.observed_at < window_end,
        )
    )


def store_paid_order_value(
    *,
    store_slug: str,
    currency: str,
    window_start: datetime,
    window_end: datetime,
) -> Optional[dict]:
    q = _window_query(
        store_slug=store_slug,
        currency=currency,
        window_start=window_start,
        window_end=window_end,
    )
    if q is None:
        return None
    total = Decimal("0")
    ids: set[str] = set()
    for row in q.all():
        amt = parse_money(row.paid_amount)
        if amt is None:
            continue
        ids.add(str(row.external_order_id))
        total += amt
    return {
        "term": SAFE_AGGREGATE_TERM,
        "currency": currency.strip().upper(),
        "paid_order_value": format(total.normalize(), "f"),
        "distinct_orders": len(ids),
        "net_revenue": False,
    }


def gross_paid_order_aov(
    *,
    store_slug: str,
    currency: str,
    window_start: datetime,
    window_end: datetime,
) -> Optional[dict]:
    rolled = store_paid_order_value(
        store_slug=store_slug,
        currency=currency,
        window_start=window_start,
        window_end=window_end,
    )
    if rolled is None:
        return None
    n = int(rolled["distinct_orders"])
    if n <= 0:
        return {
            "term": SAFE_AOV_TERM,
            "currency": rolled["currency"],
            "gross_paid_order_aov": None,
            "distinct_orders": 0,
            "net_aov": False,
        }
    total = parse_money(rolled["paid_order_value"]) or Decimal("0")
    aov = total / Decimal(n)
    return {
        "term": SAFE_AOV_TERM,
        "currency": rolled["currency"],
        "gross_paid_order_aov": format(aov.normalize(), "f"),
        "distinct_orders": n,
        "net_aov": False,
    }
