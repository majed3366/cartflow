# -*- coding: utf-8 -*-
"""
Product Intelligence Foundation v1 — product context + safe factual signals only.

Additive layer: does NOT change recovery, lifecycle, WhatsApp, continuation, attribution,
or widget flows. No recommendations, fake products, discounts, or hallucinated alternatives.

Existing ``cartflow_product_intelligence.py`` (continuation/cheaper matching) is unchanged.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

log = logging.getLogger("cartflow")

PRICE_CONFIDENCE_HIGH = "high"
PRICE_CONFIDENCE_MEDIUM = "medium"
PRICE_CONFIDENCE_LOW = "low"
PRICE_CONFIDENCE_NONE = "none"


@dataclass
class ProductContext:
    """Normalized product facts from cart / platform / widget — no invented fields."""

    product_name: str = ""
    product_id: str = ""
    category: str = ""
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    currency: str = ""
    tags: list[str] = field(default_factory=list)
    inventory: Optional[int] = None
    brand: str = ""
    warranty: str = ""
    shipping_info: str = ""
    variants: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""

    @property
    def has_product_identity(self) -> bool:
        return bool((self.product_id or "").strip() or (self.product_name or "").strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CustomerContext:
    """Lightweight session context for future PI decisions."""

    store_slug: str = ""
    session_id: str = ""
    reason_tag: str = ""
    phone_present: bool = False
    customer_replied: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProductIntelligenceInputs:
    """reason_tag + product + customer → future recommendation capability."""

    reason_tag: str = ""
    product: ProductContext = field(default_factory=ProductContext)
    customer: CustomerContext = field(default_factory=CustomerContext)
    # Optional merchant catalog rows for *factual* cheaper checks only (never invented).
    catalog_entries: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason_tag": self.reason_tag,
            "product": self.product.to_dict(),
            "customer": self.customer.to_dict(),
            "catalog_entry_count": len(self.catalog_entries),
        }


@dataclass
class ProductIntelligenceContext:
    """Safe boolean/numeric facts only — no recommendation text."""

    has_same_category: bool = False
    has_cheaper_option: bool = False
    has_shipping_reassurance: bool = False
    has_warranty_signal: bool = False
    price_confidence: str = PRICE_CONFIDENCE_NONE
    has_product_identity: bool = False
    reason_tag: str = ""
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def log_product_context(ctx: ProductContext, *, store_slug: str = "") -> None:
    price_s = "-" if ctx.price is None else str(ctx.price)
    block = (
        "[PRODUCT CONTEXT]\n"
        f"store_slug={(store_slug or '-')[:255]}\n"
        f"product_id={(ctx.product_id or '-')[:64]}\n"
        f"product_name={(ctx.product_name or '-')[:120]}\n"
        f"category={(ctx.category or '-')[:80]}\n"
        f"price={price_s}\n"
        f"currency={(ctx.currency or '-')[:8]}\n"
        f"source={(ctx.source or '-')[:32]}"
    )
    _emit_log(block)


def log_product_intelligence(
    intel: ProductIntelligenceContext,
    *,
    store_slug: str = "",
    session_id: str = "",
) -> None:
    block = (
        "[PRODUCT INTELLIGENCE]\n"
        f"store_slug={(store_slug or '-')[:255]}\n"
        f"session_id={(session_id or '-')[:80]}\n"
        f"reason_tag={(intel.reason_tag or '-')[:64]}\n"
        f"has_same_category={'true' if intel.has_same_category else 'false'}\n"
        f"has_cheaper_option={'true' if intel.has_cheaper_option else 'false'}\n"
        f"has_shipping_reassurance={'true' if intel.has_shipping_reassurance else 'false'}\n"
        f"has_warranty_signal={'true' if intel.has_warranty_signal else 'false'}\n"
        f"price_confidence={intel.price_confidence}"
    )
    if intel.evidence:
        block += f"\nevidence={','.join(intel.evidence)[:200]}"
    _emit_log(block)


def _emit_log(block: str) -> None:
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        f = float(value)
        return f if f >= 0 else None
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _norm_tags(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(t).strip()[:64] for t in raw if str(t).strip()][:20]
    if isinstance(raw, str) and raw.strip():
        return [t.strip()[:64] for t in raw.split(",") if t.strip()][:20]
    return []


def _norm_variants(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for v in raw[:20]:
        if isinstance(v, dict):
            slim = {str(k)[:64]: v[k] for k in list(v.keys())[:12]}
            out.append(slim)
    return out


def _line_item_to_product_context(
    it: dict[str, Any],
    *,
    source: str,
    currency: str = "",
) -> ProductContext:
    name = str(
        it.get("name")
        or it.get("title")
        or it.get("product_name")
        or (it.get("product") or {}).get("name")
        or ""
    ).strip()[:200]
    pid = str(
        it.get("id")
        or it.get("product_id")
        or it.get("variant_id")
        or it.get("sku")
        or (it.get("product") or {}).get("id")
        or ""
    ).strip()[:128]
    cat_raw = it.get("category") or it.get("product_category")
    if isinstance(cat_raw, dict):
        category = str(cat_raw.get("name") or cat_raw.get("title") or "").strip()[:120]
    else:
        category = str(cat_raw or "").strip()[:120]
    price = _safe_float(
        it.get("price")
        or it.get("unit_price")
        or it.get("sale_price")
        or it.get("amount")
    )
    compare_at = _safe_float(it.get("compare_at_price") or it.get("compare_at"))
    inv = _safe_int(it.get("inventory") or it.get("quantity") or it.get("stock"))
    brand = str(it.get("brand") or (it.get("product") or {}).get("brand") or "").strip()[
        :120
    ]
    warranty = str(it.get("warranty") or it.get("warranty_info") or "").strip()[:200]
    shipping = str(
        it.get("shipping_info")
        or it.get("shipping")
        or it.get("delivery_info")
        or ""
    ).strip()[:200]
    cur = str(it.get("currency") or currency or "").strip()[:8]
    return ProductContext(
        product_name=name,
        product_id=pid,
        category=category,
        price=price,
        compare_at_price=compare_at,
        currency=cur,
        tags=_norm_tags(it.get("tags")),
        inventory=inv,
        brand=brand,
        warranty=warranty,
        shipping_info=shipping,
        variants=_norm_variants(it.get("variants")),
        source=source,
    )


def _first_line_item(scope: dict[str, Any]) -> Optional[dict[str, Any]]:
    cart_raw = scope.get("cart")
    items: list[dict[str, Any]] = []
    if isinstance(cart_raw, list):
        items = [x for x in cart_raw if isinstance(x, dict)]
    elif isinstance(cart_raw, dict):
        for key in ("line_items", "items", "products", "order_items"):
            raw = cart_raw.get(key)
            if isinstance(raw, list) and raw:
                items = [x for x in raw if isinstance(x, dict)]
                break
    for key in ("line_items", "items", "products", "order_items"):
        raw = scope.get(key)
        if isinstance(raw, list) and raw:
            items = [x for x in raw if isinstance(x, dict)]
            break
    return items[0] if items else None


class ProductContextResolver:
    """Extract ``ProductContext`` from cart, platform payload, or widget state."""

    @staticmethod
    def resolve_from_cart(
        cart_payload: Optional[dict[str, Any]],
        *,
        currency: str = "",
    ) -> ProductContext:
        if not isinstance(cart_payload, dict):
            return ProductContext(source="cart_empty")
        data = cart_payload.get("data")
        scope = data if isinstance(data, dict) else cart_payload
        item = _first_line_item(scope)
        if item is None:
            return ProductContext(source="cart_no_line_items")
        return _line_item_to_product_context(item, source="cart", currency=currency)

    @staticmethod
    def resolve_from_platform_payload(
        payload: Optional[dict[str, Any]],
    ) -> ProductContext:
        if not isinstance(payload, dict):
            return ProductContext(source="platform_empty")
        items = payload.get("items")
        if isinstance(items, list) and items and isinstance(items[0], dict):
            return _line_item_to_product_context(
                items[0],
                source="platform",
                currency=str(payload.get("currency") or ""),
            )
        return ProductContextResolver.resolve_from_cart(payload)

    @staticmethod
    def resolve_from_widget_state(
        widget_state: Optional[dict[str, Any]],
    ) -> ProductContext:
        if not isinstance(widget_state, dict):
            return ProductContext(source="widget_empty")
        name = str(
            widget_state.get("product_name")
            or widget_state.get("name")
            or widget_state.get("title")
            or ""
        ).strip()
        pid = str(
            widget_state.get("product_id")
            or widget_state.get("id")
            or ""
        ).strip()
        category = str(
            widget_state.get("category")
            or widget_state.get("product_category")
            or ""
        ).strip()
        price = _safe_float(
            widget_state.get("price")
            or widget_state.get("product_price")
            or widget_state.get("cart_total")
        )
        return ProductContext(
            product_name=name[:200],
            product_id=pid[:128],
            category=category[:120],
            price=price,
            compare_at_price=_safe_float(widget_state.get("compare_at_price")),
            currency=str(widget_state.get("currency") or "")[:8],
            tags=_norm_tags(widget_state.get("tags")),
            inventory=_safe_int(widget_state.get("inventory")),
            brand=str(widget_state.get("brand") or "")[:120],
            warranty=str(widget_state.get("warranty") or "")[:200],
            shipping_info=str(widget_state.get("shipping_info") or "")[:200],
            variants=_norm_variants(widget_state.get("variants")),
            source="widget",
        )

    @staticmethod
    def resolve_from_abandoned_cart_raw(raw_payload: Optional[str]) -> ProductContext:
        if not isinstance(raw_payload, str) or not raw_payload.strip():
            return ProductContext(source="abandoned_cart_empty")
        try:
            data = json.loads(raw_payload)
        except (json.JSONDecodeError, TypeError, ValueError):
            return ProductContext(source="abandoned_cart_invalid_json")
        if not isinstance(data, dict):
            return ProductContext(source="abandoned_cart_not_object")
        return ProductContextResolver.resolve_from_cart(data)

    @classmethod
    def resolve(
        cls,
        *,
        cart: Optional[dict[str, Any]] = None,
        platform_payload: Optional[dict[str, Any]] = None,
        widget_state: Optional[dict[str, Any]] = None,
        abandoned_cart_raw: Optional[str] = None,
    ) -> ProductContext:
        """First non-empty source wins: cart → platform → widget → abandoned raw."""
        for fn, arg in (
            (cls.resolve_from_cart, cart),
            (cls.resolve_from_platform_payload, platform_payload),
            (cls.resolve_from_widget_state, widget_state),
        ):
            if isinstance(arg, dict) and arg:
                ctx = fn(arg)
                if ctx.has_product_identity:
                    return ctx
        if abandoned_cart_raw:
            ctx = cls.resolve_from_abandoned_cart_raw(abandoned_cart_raw)
            if ctx.has_product_identity:
                return ctx
        if isinstance(cart, dict) and cart:
            return cls.resolve_from_cart(cart)
        if isinstance(platform_payload, dict) and platform_payload:
            return cls.resolve_from_platform_payload(platform_payload)
        if isinstance(widget_state, dict) and widget_state:
            return cls.resolve_from_widget_state(widget_state)
        return ProductContext(source="unresolved")


def _price_confidence(product: ProductContext) -> str:
    if product.price is None or product.price <= 0:
        return PRICE_CONFIDENCE_NONE
    if (product.product_id or "").strip():
        return PRICE_CONFIDENCE_HIGH
    if (product.product_name or "").strip():
        return PRICE_CONFIDENCE_MEDIUM
    return PRICE_CONFIDENCE_LOW


def _factual_cheaper_in_catalog(
    product: ProductContext,
    catalog_entries: tuple[dict[str, Any], ...],
) -> bool:
    """
    True only when catalog lists a cheaper *available* item in the same category.

    Never invents SKUs or prices.
    """
    if product.price is None or product.price <= 0:
        return False
    cat = (product.category or "").strip().lower()
    if not cat:
        return False
    pid = (product.product_id or "").strip()
    for row in catalog_entries:
        if not isinstance(row, dict):
            continue
        row_cat = str(row.get("category") or row.get("normalized_category") or "").strip().lower()
        if row_cat != cat:
            continue
        row_price = _safe_float(row.get("price"))
        if row_price is None or row_price <= 0 or row_price >= product.price:
            continue
        row_id = str(row.get("product_id") or row.get("id") or "").strip()
        if pid and row_id and row_id == pid:
            continue
        avail = row.get("available")
        if avail is False:
            continue
        return True
    return False


def build_product_intelligence_context(
    inputs: ProductIntelligenceInputs,
) -> ProductIntelligenceContext:
    """
    Derive safe factual signals — no recommendation strings, no fake alternatives.
    """
    product = inputs.product
    reason = (inputs.reason_tag or inputs.customer.reason_tag or "").strip()[:64]
    evidence: list[str] = []

    if product.has_product_identity:
        evidence.append("product_identity_present")
    if (product.category or "").strip():
        evidence.append("category_present")
        has_same_category = True
    else:
        has_same_category = False
        evidence.append("category_missing")

    pc = _price_confidence(product)
    if pc == PRICE_CONFIDENCE_NONE:
        evidence.append("price_missing")
    else:
        evidence.append(f"price_confidence_{pc}")

    has_shipping = bool((product.shipping_info or "").strip())
    if has_shipping:
        evidence.append("shipping_info_present")

    has_warranty = bool((product.warranty or "").strip())
    if has_warranty:
        evidence.append("warranty_present")

    has_cheaper = False
    if inputs.catalog_entries:
        has_cheaper = _factual_cheaper_in_catalog(product, inputs.catalog_entries)
        evidence.append(
            "catalog_cheaper_option_found" if has_cheaper else "catalog_no_cheaper_option"
        )
    else:
        evidence.append("catalog_not_provided")

    return ProductIntelligenceContext(
        has_same_category=has_same_category,
        has_cheaper_option=has_cheaper,
        has_shipping_reassurance=has_shipping,
        has_warranty_signal=has_warranty,
        price_confidence=pc,
        has_product_identity=product.has_product_identity,
        reason_tag=reason,
        evidence=evidence,
    )


def observe_product_intelligence(
    inputs: ProductIntelligenceInputs,
    *,
    log: bool = True,
) -> ProductIntelligenceContext:
    """
    Build + optionally log PI context (observation only — not wired to recovery send).
    """
    intel = build_product_intelligence_context(inputs)
    if log:
        log_product_context(
            inputs.product,
            store_slug=inputs.customer.store_slug,
        )
        log_product_intelligence(
            intel,
            store_slug=inputs.customer.store_slug,
            session_id=inputs.customer.session_id,
        )
    return intel
