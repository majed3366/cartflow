# -*- coding: utf-8 -*-
"""Zid order-view → platform-neutral paid-order money. Raw paths stay here."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

_MONEY_STRIP = re.compile(r"[^\d.\-]")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _unwrap_order(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    for key in ("order", "data"):
        inner = raw.get(key)
        if isinstance(inner, dict) and (
            "payment_status" in inner or "order_total" in inner or "id" in inner
        ):
            return inner
    return raw


def parse_money(raw: Any) -> Optional[Decimal]:
    if raw is None or isinstance(raw, bool):
        return None
    try:
        s = _MONEY_STRIP.sub("", str(raw).replace(",", ""))
        if not s or s in {".", "-", "-."}:
            return None
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def money_text(raw: Any) -> Optional[str]:
    d = parse_money(raw)
    if d is None:
        return None
    return format(d.normalize(), "f")


def _invoice_by_code(order: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pay = _as_dict(order.get("payment"))
    rows = pay.get("invoice")
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        if code:
            out[code] = row
    return out


def _payment_status(order: dict[str, Any]) -> str:
    return str(order.get("payment_status") or "").strip().lower()


def _currency(order: dict[str, Any]) -> Optional[str]:
    cur = _as_dict(order.get("currency"))
    oc = _as_dict(cur.get("order_currency")).get("code")
    code = str(oc or order.get("currency_code") or "").strip().upper()
    alt = str(order.get("currency_code") or "").strip().upper()
    if oc and alt and str(oc).strip().upper() != alt:
        return None
    if not _CURRENCY.match(code):
        return None
    return code


def map_zid_order_view_to_economic_candidate(
    raw_payload: dict[str, Any],
) -> Optional[dict[str, Any]]:
    """Return canonical money fields or None. Never invent zeros for unknown tax/discount."""
    order = _unwrap_order(raw_payload)
    if not order:
        return None
    if _payment_status(order) != "paid":
        return None
    psum = _as_dict(order.get("payment_summary"))
    paid = parse_money(psum.get("paid_amount"))
    if paid is None or paid <= 0:
        return None
    currency = _currency(order)
    if not currency:
        return None
    inv = _invoice_by_code(order)
    tax_row = inv.get("vat") or inv.get("tax")
    disc_row = inv.get("coupon") or inv.get("discount")
    coup = order.get("coupon")
    coupon_discount = None
    if isinstance(coup, dict):
        coupon_discount = coup.get("discount")
    discount_raw = disc_row.get("value") if disc_row else coupon_discount
    oid = order.get("id") or order.get("order_id")
    if oid is None or isinstance(oid, (dict, list, bool)):
        return None
    external_id = str(oid).strip()
    if not external_id:
        return None
    store_id = order.get("store_id")
    return {
        "external_order_id": external_id,
        "platform": "zid",
        "payment_state": "paid",
        "currency": currency,
        "paid_amount": money_text(paid),
        "order_total": money_text(order.get("order_total")),
        "transaction_amount": money_text(order.get("transaction_amount")),
        "customer_shipping_charge": money_text((inv.get("shipping") or {}).get("value")),
        "order_subtotal": money_text((inv.get("sub_totals") or {}).get("value")),
        "discount_amount": money_text(discount_raw) if discount_raw is not None else None,
        "tax_amount": money_text((tax_row or {}).get("value")) if tax_row else None,
        "remaining_amount": money_text(psum.get("remaining_amount")),
        "platform_store_id": str(store_id).strip() if store_id not in (None, "", []) else None,
        "source": "zid_manager_order_view",
    }
