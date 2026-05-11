# -*- coding: utf-8 -*-
"""
سياق منتج من السلة — للإرشاد التفاعلي فقط (لا إرسال ولا جدولة).
جاهز لاحقاً لربط المخزون والبدائل الذكية.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Final, Optional

from models import AbandonedCart


@dataclass(frozen=True, slots=True)
class RecoveryProductContext:
    current_product_name: Optional[str]
    current_product_price: Optional[float]
    current_product_category: Optional[str]
    inferred_category: Optional[str]
    cheaper_alternative_name: Optional[str]
    cheaper_alternative_price: Optional[float]
    line_item_count: int


_CATEGORY_KEYWORDS: Final[tuple[tuple[str, frozenset[str]], ...]] = (
    (
        "إلكترونيات",
        frozenset(
            {
                "هاتف",
                "جوال",
                "لابتوب",
                "كمبيوتر",
                "سماعة",
                "شاحن",
                "ايباد",
                "آيباد",
                "ساعة",
                "ذكية",
                "كاميرا",
                "الكترون",
                "إلكترون",
                "phone",
                "laptop",
                "usb",
            }
        ),
    ),
    (
        "الموضة والأزياء",
        frozenset(
            {
                "قميص",
                "فستان",
                "حذاء",
                "جاكيت",
                "عباية",
                "شنطة",
                "ساعة يد",
                "نظارة",
                "هودي",
                "hoodie",
            }
        ),
    ),
    (
        "العناية والتجميل",
        frozenset(
            {
                "عطر",
                "مكياج",
                "كريم",
                "شامبو",
                "عناية",
                "تجميل",
            }
        ),
    ),
    (
        "المنزل والمعيشة",
        frozenset(
            {
                "كنب",
                "سرير",
                "مفرش",
                "ديكور",
                "مطبخ",
                "ابجورة",
                "إبجورة",
            }
        ),
    ),
)


def infer_category_from_product_name(product_name: str) -> str:
    n = (product_name or "").strip().lower()
    if not n:
        return ""
    for label, keys in _CATEGORY_KEYWORDS:
        for k in keys:
            if k in n:
                return label
    return ""


def _unwrap_data_level(payload: dict[str, Any]) -> dict[str, Any]:
    d = payload.get("data")
    if isinstance(d, dict):
        return d
    return payload


def _first_line_items_list(scope: dict[str, Any]) -> list[dict[str, Any]]:
    cart_raw = scope.get("cart")
    if isinstance(cart_raw, list) and cart_raw:
        return [x for x in cart_raw if isinstance(x, dict)]
    cart = cart_raw if isinstance(cart_raw, dict) else {}
    for key in ("line_items", "items", "products", "order_items"):
        for src in (scope, cart):
            raw = src.get(key)
            if isinstance(raw, list) and raw:
                return [x for x in raw if isinstance(x, dict)]
    return []


def _item_display_name(it: dict[str, Any]) -> str:
    n = it.get("name") or it.get("title") or it.get("product_name") or ""
    s = str(n).strip()
    return s[:120] if s else ""


def _item_unit_price(it: dict[str, Any]) -> Optional[float]:
    for k in (
        "unit_price",
        "price",
        "sale_price",
        "amount",
        "line_price",
        "total",
        "subtotal",
    ):
        v = it.get(k)
        if v is None:
            continue
        try:
            f = float(v)
            if f > 0:
                return f
        except (TypeError, ValueError):
            continue
    return None


def _item_category(it: dict[str, Any]) -> str:
    c = it.get("category") or it.get("product_category")
    if isinstance(c, dict):
        c = c.get("name") or c.get("title")
    if c is not None:
        s = str(c).strip()
        return s[:120] if s else ""
    prod = it.get("product")
    if isinstance(prod, dict):
        pc = prod.get("category")
        if isinstance(pc, dict):
            s2 = str(pc.get("name") or pc.get("title") or "").strip()
            return s2[:120] if s2 else ""
        s3 = str(pc or "").strip()
        return s3[:120] if s3 else ""
    return ""


def recovery_product_context_from_payload(payload: Optional[dict[str, Any]]) -> RecoveryProductContext:
    if not isinstance(payload, dict):
        return RecoveryProductContext(
            current_product_name=None,
            current_product_price=None,
            current_product_category=None,
            inferred_category=None,
            cheaper_alternative_name=None,
            cheaper_alternative_price=None,
            line_item_count=0,
        )
    data = _unwrap_data_level(payload)
    items = _first_line_items_list(data)
    if not items:
        return RecoveryProductContext(
            current_product_name=None,
            current_product_price=None,
            current_product_category=None,
            inferred_category=None,
            cheaper_alternative_name=None,
            cheaper_alternative_price=None,
            line_item_count=0,
        )
    primary = items[0]
    pname = _item_display_name(primary) or None
    pprice = _item_unit_price(primary)
    pcat = _item_category(primary) or None
    inferred = infer_category_from_product_name(pname or "") or None
    alt_name: Optional[str] = None
    alt_price: Optional[float] = None
    if len(items) >= 2 and pprice is not None:
        for other in items[1:]:
            oname = _item_display_name(other)
            oprice = _item_unit_price(other)
            if (
                oname
                and oprice is not None
                and oprice > 0
                and oprice < pprice * 0.999
            ):
                alt_name, alt_price = oname, oprice
                break
    return RecoveryProductContext(
        current_product_name=pname,
        current_product_price=pprice,
        current_product_category=pcat,
        inferred_category=inferred,
        cheaper_alternative_name=alt_name,
        cheaper_alternative_price=alt_price,
        line_item_count=len(items),
    )


def recovery_product_context_from_abandoned_cart(ac: Optional[AbandonedCart]) -> RecoveryProductContext:
    if ac is None:
        return recovery_product_context_from_payload(None)
    rp = getattr(ac, "raw_payload", None)
    if not isinstance(rp, str) or not rp.strip():
        return recovery_product_context_from_payload(None)
    try:
        data = json.loads(rp)
    except (json.JSONDecodeError, TypeError, ValueError):
        return recovery_product_context_from_payload(None)
    if not isinstance(data, dict):
        return recovery_product_context_from_payload(None)
    return recovery_product_context_from_payload(data)


def line_items_from_abandoned_cart(ac: Optional[AbandonedCart]) -> list[dict[str, Any]]:
    """عناصر السطر من ‎raw_payload‎ — لإعادة الاستخدام في طبقة ذكاء المنتج."""
    if ac is None:
        return []
    rp = getattr(ac, "raw_payload", None)
    if not isinstance(rp, str) or not rp.strip():
        return []
    try:
        data = json.loads(rp)
    except (json.JSONDecodeError, TypeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    scope = _unwrap_data_level(data)
    return _first_line_items_list(scope)


def resolved_category_label(ctx: RecoveryProductContext) -> Optional[str]:
    if ctx.current_product_category and ctx.current_product_category.strip():
        return ctx.current_product_category.strip()
    if ctx.inferred_category and ctx.inferred_category.strip():
        return ctx.inferred_category.strip()
    return None
