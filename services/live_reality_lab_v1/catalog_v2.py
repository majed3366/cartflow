# -*- coding: utf-8 -*-
"""
Live Reality Dataset V2 — نور العناية product catalog.

Production-shaped ProductCatalogEntry inputs. One deliberate missing-name fixture.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.live_reality_lab_v1.contract_v1 import MISSING_NAME_PRODUCT_ID
from services.product_data.product_catalog_types_v1 import CatalogProductInput

LAB_CATEGORY = "عناية شخصية"

# (product_id, arabic_name, price_sar, cart_slots)
NAMED_PRODUCTS: Tuple[Tuple[str, str, float, int], ...] = (
    ("nf-oud-royal", "عود ملكي مركز", 189.0, 5),
    ("nf-musk-tahara", "مسك الطهارة", 79.0, 4),
    ("nf-rose-damascus", "ورد دمشقي مركز", 129.0, 4),
    ("nf-amber-night", "عنبر ليلي", 149.0, 4),
    ("nf-hair-serum", "سيروم تغذية الشعر", 95.0, 4),
    ("nf-body-butter", "زبدة الجسم بالشيا", 68.0, 3),
    ("nf-face-cleanser", "غسول الوجه بالعسل", 55.0, 3),
    ("nf-hand-cream", "كريم اليدين بالورد", 42.0, 3),
    ("nf-oud-spray", "معطر عود للمنزل", 85.0, 3),
    ("nf-gift-set", "طقم العناية الفاخر", 249.0, 4),
)

MISSING_NAME_PRICE = 39.0
MISSING_NAME_CART_SLOTS = 1

GENERIC_FORBIDDEN = (
    "منتج",
    "Product",
    "item",
    "sku",
)


def named_product_count() -> int:
    return len(NAMED_PRODUCTS)


def catalog_inputs_v2() -> List[CatalogProductInput]:
    rows: List[CatalogProductInput] = []
    for pid, name, price, _slots in NAMED_PRODUCTS:
        rows.append(
            CatalogProductInput(
                product_id=pid,
                variant_id=f"{pid}-default",
                sku=pid.upper().replace("-", "_"),
                name=name,
                category=LAB_CATEGORY,
                price=price,
                currency="SAR",
            )
        )
    rows.append(
        CatalogProductInput(
            product_id=MISSING_NAME_PRODUCT_ID,
            variant_id=f"{MISSING_NAME_PRODUCT_ID}-default",
            sku="NF_MISSING_NAME",
            name="",
            category=LAB_CATEGORY,
            price=MISSING_NAME_PRICE,
            currency="SAR",
        )
    )
    return rows


def product_by_id() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for pid, name, price, slots in NAMED_PRODUCTS:
        out[pid] = {
            "product_id": pid,
            "name": name,
            "price": price,
            "slots": slots,
            "missing_name": False,
        }
    out[MISSING_NAME_PRODUCT_ID] = {
        "product_id": MISSING_NAME_PRODUCT_ID,
        "name": "",
        "price": MISSING_NAME_PRICE,
        "slots": MISSING_NAME_CART_SLOTS,
        "missing_name": True,
    }
    return out


def cart_product_sequence() -> List[str]:
    seq: List[str] = []
    for pid, _name, _price, slots in NAMED_PRODUCTS:
        seq.extend([pid] * int(slots))
    seq.extend([MISSING_NAME_PRODUCT_ID] * MISSING_NAME_CART_SLOTS)
    return seq


def line_for_product(product_id: str, *, quantity: int = 1) -> Dict[str, Any]:
    meta = product_by_id()[product_id]
    line: Dict[str, Any] = {
        "product_id": product_id,
        "variant_id": f"{product_id}-default",
        "sku": str(product_id).upper().replace("-", "_"),
        "unit_price": float(meta["price"]),
        "quantity": int(quantity),
        "currency": "SAR",
    }
    name = str(meta.get("name") or "")
    if name:
        line["name"] = name
    return line


def assert_no_generic_named_products() -> None:
    for _pid, name, _price, _slots in NAMED_PRODUCTS:
        n = name.strip()
        if not n or n in GENERIC_FORBIDDEN:
            raise ValueError("live_reality_lab_generic_product_name")


def product_name(product_id: str) -> Optional[str]:
    meta = product_by_id().get(product_id) or {}
    name = str(meta.get("name") or "").strip()
    return name or None


__all__ = [
    "LAB_CATEGORY",
    "MISSING_NAME_CART_SLOTS",
    "MISSING_NAME_PRICE",
    "NAMED_PRODUCTS",
    "assert_no_generic_named_products",
    "cart_product_sequence",
    "catalog_inputs_v2",
    "line_for_product",
    "named_product_count",
    "product_by_id",
    "product_name",
]
