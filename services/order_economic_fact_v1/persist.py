# -*- coding: utf-8 -*-
"""Idempotent persist for OrderEconomicFact. One grain, no recovery_key count."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.exc import IntegrityError

from extensions import db
from models import OrderEconomicFact
from schema_order_economic_fact_v1 import ensure_order_economic_fact_schema
from services.order_economic_fact_v1.contract import CanonicalOrderEconomicFact, TRUTH_VERSION

log = logging.getLogger("cartflow")


def get_order_economic_fact(
    *,
    store_slug: str,
    external_order_id: str,
    truth_version: str = TRUTH_VERSION,
) -> Optional[OrderEconomicFact]:
    slug = (store_slug or "").strip()
    oid = (external_order_id or "").strip()
    ver = (truth_version or "").strip() or TRUTH_VERSION
    if not slug or not oid:
        return None
    ensure_order_economic_fact_schema(db)
    return (
        db.session.query(OrderEconomicFact)
        .filter(
            OrderEconomicFact.store_slug == slug,
            OrderEconomicFact.external_order_id == oid,
            OrderEconomicFact.truth_version == ver,
        )
        .first()
    )


def persist_order_economic_fact(fact: CanonicalOrderEconomicFact) -> OrderEconomicFact:
    ensure_order_economic_fact_schema(db)
    now = datetime.now(timezone.utc)
    row = get_order_economic_fact(
        store_slug=fact.store_slug,
        external_order_id=fact.external_order_id,
        truth_version=fact.truth_version,
    )
    if row is None:
        row = OrderEconomicFact(
            store_slug=fact.store_slug,
            external_order_id=fact.external_order_id,
            platform=fact.platform,
            payment_state=fact.payment_state,
            currency=fact.currency,
            paid_amount=fact.paid_amount,
            order_total=fact.order_total,
            transaction_amount=fact.transaction_amount,
            customer_shipping_charge=fact.customer_shipping_charge,
            order_subtotal=fact.order_subtotal,
            discount_amount=fact.discount_amount,
            tax_amount=fact.tax_amount,
            remaining_amount=fact.remaining_amount,
            observed_at=fact.observed_at,
            source=fact.source,
            truth_version=fact.truth_version,
            created_at=now,
            updated_at=now,
        )
        db.session.add(row)
    else:
        _apply_fact_fields(row, fact, now)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        row = get_order_economic_fact(
            store_slug=fact.store_slug,
            external_order_id=fact.external_order_id,
            truth_version=fact.truth_version,
        )
        if row is None:
            raise
        _apply_fact_fields(row, fact, datetime.now(timezone.utc))
        db.session.commit()
    return row


def _apply_fact_fields(row: OrderEconomicFact, fact: CanonicalOrderEconomicFact, now: datetime) -> None:
    row.payment_state = fact.payment_state
    row.currency = fact.currency
    row.paid_amount = fact.paid_amount
    row.order_total = fact.order_total
    row.transaction_amount = fact.transaction_amount
    row.customer_shipping_charge = fact.customer_shipping_charge
    row.order_subtotal = fact.order_subtotal
    row.discount_amount = fact.discount_amount
    row.tax_amount = fact.tax_amount
    row.remaining_amount = fact.remaining_amount
    row.observed_at = fact.observed_at
    row.source = fact.source
    row.updated_at = now
