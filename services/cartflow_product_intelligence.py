# -*- coding: utf-8 -*-
"""
طبقة ذكاء المنتج v1 — قواعد فقط، بلا ذكاء اصطناعي، بلا منتجات أو أسعار وهمية.

معزولة عن الجدولة ومسار واتساب الرئيسي؛ تُستهلك من مسار الاستمرار فقط.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from models import AbandonedCart, Store

from services.cartflow_merchant_offer_settings import merchant_offer_settings_from_store_row
from services.cartflow_merchant_offer_settings import product_catalog_from_store_row
from services.recovery_product_context import (
    infer_category_from_product_name,
    line_items_from_abandoned_cart,
    recovery_product_context_from_abandoned_cart,
    resolved_category_label,
    _item_category,
    _item_display_name,
    _item_unit_price,
)

log = logging.getLogger("cartflow")

FALLBACK_CHEAPER_MESSAGE_AR = (
    "أفهمك 👍\n"
    "نقدر نساعدك بخيار أنسب حسب ميزانيتك."
)


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    product_id: str
    name: str
    price: float
    category: str
    url: str
    available: bool


@dataclass(frozen=True, slots=True)
class ProductIntelligenceSnapshot:
    current_product_id: Optional[str]
    current_product_name: Optional[str]
    current_product_price: Optional[float]
    current_product_category: Optional[str]
    current_product_url: Optional[str]
    current_checkout_url: str
    cart_total: Optional[float]
    alternative: Optional[CatalogEntry]
    cart_products: tuple[CatalogEntry, ...]


def _norm_bucket(label: str) -> str:
    return (label or "").strip().lower()


def _line_item_id(it: dict[str, Any]) -> str:
    for k in ("id", "product_id", "variant_id", "sku"):
        v = it.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()[:128]
    prod = it.get("product")
    if isinstance(prod, dict):
        for k in ("id", "sku"):
            v = prod.get(k)
            if v is not None and str(v).strip():
                return str(v).strip()[:128]
    return ""


def _line_item_url(it: dict[str, Any]) -> str:
    u = it.get("url") or it.get("product_url") or it.get("link")
    if not u and isinstance(it.get("product"), dict):
        u = it["product"].get("url") or it["product"].get("permalink")
    if u is None:
        return ""
    return str(u).strip()[:2048]


def _entry_from_line_item(it: dict[str, Any]) -> Optional[CatalogEntry]:
    name = _item_display_name(it)
    price = _item_unit_price(it)
    if not name or price is None or price <= 0:
        return None
    cat = _item_category(it) or infer_category_from_product_name(name)
    return CatalogEntry(
        product_id=_line_item_id(it) or name[:64],
        name=name[:300],
        price=float(price),
        category=(cat or "")[:120],
        url=_line_item_url(it),
        available=True,
    )


def _entries_from_catalog_dict(catalog: dict[str, Any]) -> list[CatalogEntry]:
    out: list[CatalogEntry] = []
    prods = catalog.get("products") if isinstance(catalog.get("products"), list) else []
    for p in prods:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()[:128]
        name = str(p.get("name") or "").strip()[:300]
        try:
            price = float(p.get("price"))
        except (TypeError, ValueError):
            continue
        if not name or price <= 0:
            continue
        if p.get("available") is False:
            continue
        cat = str(p.get("category") or "").strip()[:120]
        url = str(p.get("url") or "").strip()[:2048]
        out.append(
            CatalogEntry(
                product_id=pid or name[:64],
                name=name,
                price=round(price, 2),
                category=cat,
                url=url,
                available=True,
            )
        )
    return out


def _primary_category_bucket(
    primary_name: Optional[str],
    primary_explicit_cat: Optional[str],
    recovery_ctx_category: Optional[str],
) -> str:
    for c in (recovery_ctx_category, primary_explicit_cat):
        b = _norm_bucket(c or "")
        if b:
            return b
    inf = infer_category_from_product_name(primary_name or "")
    return _norm_bucket(inf)


def _candidate_category_bucket(name: str, explicit_cat: str) -> str:
    b = _norm_bucket(explicit_cat)
    if b:
        return b
    return _norm_bucket(infer_category_from_product_name(name))


def select_cheaper_alternative(
    *,
    primary: CatalogEntry,
    cart_entries: list[CatalogEntry],
    catalog_entries: list[CatalogEntry],
    recovery_category_label: Optional[str],
) -> Optional[CatalogEntry]:
    """
    نفس الفئة (عند توفر إشارة فئة)، سعر أقل فقط، متاح فقط — بدون اختراع.
    """
    if primary.price <= 0:
        return None
    bucket = _primary_category_bucket(
        primary.name,
        primary.category,
        recovery_category_label,
    )
    if not bucket:
        log.info(
            "[PRODUCT MATCH] skip: no category signal primary_id=%s",
            primary.product_id[:32] if primary.product_id else "",
        )
        return None

    candidates: list[CatalogEntry] = []
    seen_ids: set[str] = set()
    for e in cart_entries + catalog_entries:
        if e.product_id == primary.product_id and e.name == primary.name:
            continue
        key = f"{e.product_id}|{e.name}"
        if key in seen_ids:
            continue
        seen_ids.add(key)
        if not e.available:
            continue
        cb = _candidate_category_bucket(e.name, e.category)
        if cb != bucket:
            continue
        if e.price >= primary.price * 0.999:
            continue
        candidates.append(e)

    log.info(
        "[PRODUCT MATCH] bucket=%s primary_price=%s candidates=%s",
        bucket[:48],
        primary.price,
        len(candidates),
    )
    if not candidates:
        return None
    best = max(candidates, key=lambda x: x.price)
    log.info(
        "[ALTERNATIVE SELECTED] id=%s price=%s (primary=%s)",
        best.product_id[:48],
        best.price,
        primary.price,
    )
    return best


def _cart_total_from_abandoned(ac: AbandonedCart, entries: list[CatalogEntry]) -> Optional[float]:
    raw = getattr(ac, "cart_value", None)
    if raw is not None:
        try:
            v = float(raw)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if not entries:
        return None
    s = sum(e.price for e in entries)
    return s if s > 0 else None


def build_product_intelligence_snapshot(
    ac: AbandonedCart,
    store: Optional[Store],
) -> ProductIntelligenceSnapshot:
    from services.behavioral_recovery.link_tracking import build_recovery_tracking_url

    line_dicts = line_items_from_abandoned_cart(ac)
    cart_entries: list[CatalogEntry] = []
    for d in line_dicts:
        e = _entry_from_line_item(d)
        if e:
            cart_entries.append(e)

    primary: Optional[CatalogEntry] = cart_entries[0] if cart_entries else None
    recovery_ctx = recovery_product_context_from_abandoned_cart(ac)
    rc_cat = resolved_category_label(recovery_ctx)

    catalog: dict[str, Any] = (
        product_catalog_from_store_row(store) if store is not None else {"products": []}
    )
    catalog_entries = _entries_from_catalog_dict(catalog)

    alt: Optional[CatalogEntry] = None
    if primary is not None:
        alt = select_cheaper_alternative(
            primary=primary,
            cart_entries=cart_entries[1:],
            catalog_entries=catalog_entries,
            recovery_category_label=rc_cat,
        )
        if alt is None and recovery_ctx.cheaper_alternative_name:
            pprice = primary.price
            oprice = recovery_ctx.cheaper_alternative_price
            oname = (recovery_ctx.cheaper_alternative_name or "").strip()
            if (
                oname
                and oprice is not None
                and oprice > 0
                and oprice < pprice * 0.999
                and line_dicts
                and len(line_dicts) >= 2
            ):
                for d in line_dicts[1:]:
                    e2 = _entry_from_line_item(d)
                    if (
                        e2
                        and e2.name == oname
                        and abs(e2.price - float(oprice)) < 0.02
                    ):
                        alt = e2
                        log.info(
                            "[ALTERNATIVE SELECTED] source=cart_line id=%s",
                            e2.product_id[:48],
                        )
                        break

    zid = (getattr(ac, "zid_cart_id", None) or "").strip()
    sid = (getattr(ac, "recovery_session_id", None) or "").strip()
    checkout = (
        build_recovery_tracking_url(zid, sid) or (getattr(ac, "cart_url", None) or "").strip()
    )

    cart_total = _cart_total_from_abandoned(ac, cart_entries)

    snap = ProductIntelligenceSnapshot(
        current_product_id=primary.product_id if primary else None,
        current_product_name=primary.name if primary else None,
        current_product_price=primary.price if primary else None,
        current_product_category=primary.category if primary else None,
        current_product_url=primary.url if primary and primary.url else None,
        current_checkout_url=checkout,
        cart_total=cart_total,
        alternative=alt,
        cart_products=tuple(cart_entries),
    )

    log.info(
        "[PRODUCT CONTEXT] product_id=%s name=%s price=%s category=%s "
        "cart_lines=%s alt=%s cart_total=%s",
        (snap.current_product_id or "")[:64],
        (snap.current_product_name or "")[:80],
        snap.current_product_price,
        (snap.current_product_category or "")[:64],
        len(cart_entries),
        bool(alt),
        cart_total,
    )
    return snap


def _reason_matches_trigger(reason_tag: str, trigger: str) -> bool:
    rt = (reason_tag or "").strip().lower()
    tr = (trigger or "").strip().lower()
    if not tr:
        return False
    if tr == "price":
        return rt == "price" or rt.startswith("price_")
    if tr == "shipping":
        return rt in ("shipping", "delivery") or rt.startswith("ship")
    if tr == "quality":
        return rt == "quality" or rt.startswith("quality_")
    return tr in rt or rt == tr


def _continuation_intent_for_offer(contextual_intent: str) -> str:
    return (contextual_intent or "").strip().lower()


def decide_merchant_offer_line(
    store: Optional[Store],
    *,
    reason_tag: str,
    contextual_intent: str,
    action: str,
    cart_total: Optional[float],
    first_seen_at: Optional[datetime],
    has_real_alternative: bool,
) -> tuple[str, bool]:
    """
    يرجع (سطر عربي للعرض، هل يُسمح باحتساب استخدام).
    """
    if store is None:
        log.info("[OFFER DECISION] skip: no store")
        return "", False
    settings = merchant_offer_settings_from_store_row(store)
    if not settings.get("offer_enabled") or not settings.get("enable_discount_offers"):
        log.info("[OFFER DECISION] skip: offers disabled")
        return "", False
    code = str(settings.get("discount_code") or "").strip()
    if not code:
        log.info("[OFFER DECISION] skip: empty discount_code")
        return "", False

    if not _reason_matches_trigger(reason_tag, str(settings.get("offer_trigger_reason") or "")):
        log.info(
            "[OFFER DECISION] skip: reason mismatch tag=%s trigger=%s",
            reason_tag,
            settings.get("offer_trigger_reason"),
        )
        return "", False

    min_tot = settings.get("offer_min_cart_total")
    if min_tot is not None:
        try:
            need = float(min_tot)
            ct = float(cart_total) if cart_total is not None else 0.0
            if ct < need:
                log.info(
                    "[OFFER DECISION] skip: cart_total %s < min %s",
                    cart_total,
                    need,
                )
                return "", False
        except (TypeError, ValueError):
            return "", False

    delay_m = int(settings.get("offer_delay_minutes") or 0)
    if delay_m > 0 and first_seen_at is not None:
        now = datetime.now(timezone.utc)
        fs = first_seen_at
        if fs.tzinfo is None:
            fs = fs.replace(tzinfo=timezone.utc)
        age_min = (now - fs).total_seconds() / 60.0
        if age_min < delay_m:
            log.info(
                "[OFFER DECISION] skip: delay not elapsed (%.1f < %s)",
                age_min,
                delay_m,
            )
            return "", False

    max_uses = settings.get("offer_max_uses")
    if max_uses is not None:
        try:
            cap = int(max_uses)
            used = int(getattr(store, "cf_offer_applications_count", 0) or 0)
            if used >= cap:
                log.info("[OFFER DECISION] skip: max_uses reached %s/%s", used, cap)
                return "", False
        except (TypeError, ValueError):
            pass

    ci = _continuation_intent_for_offer(contextual_intent)
    allow_intents = frozenset(
        {
            "wants_cheaper_alternative",
            "yes_to_cheaper_alternative",
            "asks_price_detail",
            "ready_for_checkout",
            "confirmation_generic",
            "asks_shipping_detail",
            "asks_delivery_detail",
        }
    )
    allow_actions = frozenset(
        {
            "send_cheaper_alternative",
            "explain_price",
            "send_checkout_link",
            "resend_checkout_link",
            "explain_shipping",
            "explain_delivery",
        }
    )
    if ci not in allow_intents and (action or "") not in allow_actions:
        log.info("[OFFER DECISION] skip: intent/action not targeted")
        return "", False

    if ci in ("ready_for_checkout", "confirmation_generic") and has_real_alternative:
        log.info("[OFFER DECISION] skip: checkout path with alternative context")
        return "", False

    parts = [f"كود الخصم: {code}"]
    pct = settings.get("discount_percent")
    if pct is not None:
        try:
            p = int(pct)
            if 1 <= p <= 35:
                parts.append(f"({p}٪)")
        except (TypeError, ValueError):
            pass
    line = " — ".join(parts)
    log.info(
        "[OFFER DECISION] allow reason=%s intent=%s action=%s line=%s",
        reason_tag,
        contextual_intent,
        action,
        line[:120],
    )
    return f"\n\n{line}", True


def build_intelligence_continuation_vars(
    ac: AbandonedCart,
    store: Optional[Store],
    *,
    reason_tag: str,
    contextual_intent: str,
    action: str,
) -> dict[str, str]:
    snap = build_product_intelligence_snapshot(ac, store)
    ship = os.getenv("CARTFLOW_SHIPPING_ESTIMATE_AR") or (
        "حسب المدينة — غالباً ٣–٧ أيام عمل"
    )
    ship = str(ship).strip()

    checkout = snap.current_checkout_url or "رابط المتجر"
    alt = snap.alternative
    has_real = bool(alt and alt.name.strip())

    offer_line, offer_apply = decide_merchant_offer_line(
        store,
        reason_tag=reason_tag,
        contextual_intent=contextual_intent,
        action=action,
        cart_total=snap.cart_total,
        first_seen_at=getattr(ac, "first_seen_at", None),
        has_real_alternative=has_real,
    )
    if offer_apply:
        log.info("[OFFER APPLIED] preview=%s", offer_line.strip()[:100])

    vars_map: dict[str, str] = {
        "checkout_url": checkout,
        "alternative_product_name": alt.name if alt else "",
        "alternative_checkout_url": (alt.url if alt and alt.url else checkout),
        "shipping_estimate": ship,
        "cheaper_reply_mode": "real" if has_real else "fallback",
        "has_price_context": "1"
        if snap.current_product_price is not None
        else "0",
        "current_product_price_display": ""
        if snap.current_product_price is None
        else f"{snap.current_product_price:.2f}",
        "merchant_offer_line": offer_line,
        "merchant_offer_applied": "1" if offer_apply else "0",
    }
    return vars_map


def record_merchant_offer_use(store: Optional[Store]) -> None:
    if store is None:
        return
    try:
        n = int(getattr(store, "cf_offer_applications_count", 0) or 0)
        store.cf_offer_applications_count = n + 1
        log.info("[OFFER APPLIED] cf_offer_applications_count=%s", n + 1)
    except (TypeError, ValueError):
        pass


def resolve_store_for_abandoned_cart(ac: Optional[AbandonedCart]) -> Optional[Store]:
    if ac is None:
        return None
    raw = getattr(ac, "store_id", None)
    if raw is None:
        return None
    try:
        from unittest.mock import MagicMock as _MagicMock
    except ImportError:
        _MagicMock = ()  # type: ignore[assignment]
    if isinstance(raw, _MagicMock):
        return None
    try:
        from extensions import db

        return db.session.get(Store, int(raw))
    except (TypeError, ValueError, RuntimeError):
        return None
