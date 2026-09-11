# -*- coding: utf-8 -*-
"""Platform-neutral Order Economic Fact contract (oef_v1)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

TRUTH_VERSION = "oef_v1"
SOURCE_ZID_MANAGER_ORDER_VIEW = "zid_manager_order_view"
SAFE_MERCHANT_TERM = "قيمة الطلب المدفوع"
SAFE_AGGREGATE_TERM = "قيمة الطلبات المدفوعة"
SAFE_AOV_TERM = "متوسط قيمة الطلب المدفوع"


@dataclass(frozen=True)
class CanonicalOrderEconomicFact:
    store_slug: str
    external_order_id: str
    platform: str
    payment_state: str
    currency: str
    paid_amount: str
    observed_at: datetime
    source: str
    truth_version: str = TRUTH_VERSION
    order_total: Optional[str] = None
    transaction_amount: Optional[str] = None
    customer_shipping_charge: Optional[str] = None
    order_subtotal: Optional[str] = None
    discount_amount: Optional[str] = None
    tax_amount: Optional[str] = None
    remaining_amount: Optional[str] = None
