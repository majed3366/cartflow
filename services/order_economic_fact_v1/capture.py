# -*- coding: utf-8 -*-
"""Bounded Manager GET after PLATFORM_PAID. Never called from dashboard render."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from extensions import db
from models import Store, StoreIdentityAlias
from services.cartflow_purchase_truth import (
    find_authoritative_platform_paid_row,
    is_authoritative_platform_paid_source,
)
from services.order_economic_fact_v1.contract import (
    CanonicalOrderEconomicFact,
    TRUTH_VERSION,
)
from services.order_economic_fact_v1.persist import persist_order_economic_fact
from services.store_identity_v1 import ALIAS_KIND_ZID_NUMERIC_ID

log = logging.getLogger("cartflow")

OrderViewFetcher = Callable[[Any, str], tuple[dict, int]]


def _store_for_slug(store_slug: str) -> Optional[Store]:
    slug = (store_slug or "").strip()
    if not slug:
        return None
    return db.session.query(Store).filter(Store.zid_store_id == slug).first()


def _expected_zid_numeric_id(store: Store) -> str:
    row = (
        db.session.query(StoreIdentityAlias)
        .filter(
            StoreIdentityAlias.store_id == store.id,
            StoreIdentityAlias.alias_kind == ALIAS_KIND_ZID_NUMERIC_ID,
        )
        .first()
    )
    return str(row.alias_value or "").strip() if row else ""


def capture_after_platform_paid(
    *,
    purchase_source: str,
    store_slug: str,
    external_order_id: str,
    fetch_order_view: Optional[OrderViewFetcher] = None,
) -> dict[str, Any]:
    """Persist one OrderEconomicFact or return unavailable. Purchase Truth is untouched."""
    slug = (store_slug or "").strip()
    oid = (external_order_id or "").strip()
    if not is_authoritative_platform_paid_source(purchase_source):
        return {"ok": False, "reason": "not_platform_paid"}
    if not slug or not oid:
        return {"ok": False, "reason": "missing_identity"}
    if find_authoritative_platform_paid_row(slug, oid) is None:
        return {"ok": False, "reason": "platform_paid_row_missing"}

    store = _store_for_slug(slug)
    if store is None:
        return {"ok": False, "reason": "store_not_found"}

    fetcher = fetch_order_view
    if fetcher is None:
        from integrations.zid_client import fetch_order_view as _live_fetch
        from integrations.zid_client import manager_headers_for_store

        headers, err = manager_headers_for_store(store)
        if err or not headers:
            return {"ok": False, "reason": "manager_auth_incomplete"}
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return {"ok": False, "reason": "test_fetcher_required"}
        fetcher = _live_fetch
    try:
        body, http = fetcher(store, oid)
    except Exception as exc:  # noqa: BLE001
        log.warning("order economic fact GET failed: %s", exc)
        reason = (
            "manager_timeout"
            if "timeout" in str(exc).lower() or exc.__class__.__name__.lower().find("timeout") >= 0
            else "manager_get_error"
        )
        return {"ok": False, "reason": reason, "http": None}

    if http == 401:
        return {"ok": False, "reason": "manager_unauthorized", "http": 401}
    if http == 404:
        return {"ok": False, "reason": "order_not_found", "http": 404}
    if http == 409:
        return {"ok": False, "reason": "manager_auth_incomplete", "http": 409}
    if http in (408, 504):
        return {"ok": False, "reason": "manager_timeout", "http": http}
    if http in (502,) or (
        isinstance(body, dict) and body.get("error") == "request_failed"
    ):
        return {"ok": False, "reason": "manager_timeout", "http": http}
    if http != 200 or not isinstance(body, dict):
        return {"ok": False, "reason": "manager_unusable", "http": http}

    from integrations.adapters.zid import ZidAdapter

    mapped = ZidAdapter().map_order_economic_fact(body)
    if not mapped:
        return {"ok": False, "reason": "monetary_conditions_failed", "http": http}

    if str(mapped.get("external_order_id") or "") != oid:
        return {"ok": False, "reason": "order_id_mismatch", "http": http}

    expected_nid = _expected_zid_numeric_id(store)
    got_nid = str(mapped.get("platform_store_id") or "").strip()
    if expected_nid and got_nid and expected_nid != got_nid:
        return {"ok": False, "reason": "cross_tenant_rejected", "http": http}

    fact = CanonicalOrderEconomicFact(
        store_slug=slug,
        external_order_id=oid,
        platform=str(mapped["platform"]),
        payment_state=str(mapped["payment_state"]),
        currency=str(mapped["currency"]),
        paid_amount=str(mapped["paid_amount"]),
        order_total=mapped.get("order_total"),
        transaction_amount=mapped.get("transaction_amount"),
        customer_shipping_charge=mapped.get("customer_shipping_charge"),
        order_subtotal=mapped.get("order_subtotal"),
        discount_amount=mapped.get("discount_amount"),
        tax_amount=mapped.get("tax_amount"),
        remaining_amount=mapped.get("remaining_amount"),
        observed_at=datetime.now(timezone.utc),
        source=str(mapped.get("source") or "zid_manager_order_view"),
        truth_version=TRUTH_VERSION,
    )
    row = persist_order_economic_fact(fact)
    return {
        "ok": True,
        "reason": "persisted",
        "http": http,
        "id": row.id,
        "paid_amount": row.paid_amount,
        "currency": row.currency,
    }
