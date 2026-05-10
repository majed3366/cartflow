# -*- coding: utf-8 -*-
"""إعدادات عروض التاجر لمسار الاستمرار — قواعد فقط؛ لا إنشاء خصومات تلقائياً."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

DEFAULT_MERCHANT_OFFER_SETTINGS: Dict[str, Any] = {
    "offer_enabled": False,
    "enable_discount_offers": False,
    "discount_code": "",
    "discount_percent": None,
    "offer_trigger_reason": "price",
    "offer_min_cart_total": None,
    "offer_delay_minutes": 0,
    "offer_max_uses": None,
}


def _boolish(v: Any, default: bool) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("true", "1", "yes", "on"):
            return True
        if s in ("false", "0", "no", "off", ""):
            return False
    return default


def normalize_merchant_offer_settings(raw: Any) -> Dict[str, Any]:
    out = dict(DEFAULT_MERCHANT_OFFER_SETTINGS)
    if not isinstance(raw, dict):
        return out
    out["offer_enabled"] = _boolish(raw.get("offer_enabled"), bool(out["offer_enabled"]))
    out["enable_discount_offers"] = _boolish(
        raw.get("enable_discount_offers"), bool(out["enable_discount_offers"])
    )
    dc = raw.get("discount_code")
    if isinstance(dc, str):
        out["discount_code"] = dc.strip()[:64]
    elif dc is None:
        out["discount_code"] = ""
    dp = raw.get("discount_percent")
    if dp is None or dp == "":
        out["discount_percent"] = None
    else:
        try:
            p = int(dp)
            out["discount_percent"] = p if 1 <= p <= 35 else None
        except (TypeError, ValueError):
            out["discount_percent"] = None
    tr = raw.get("offer_trigger_reason")
    if isinstance(tr, str) and tr.strip():
        out["offer_trigger_reason"] = tr.strip().lower()[:32]
    else:
        out["offer_trigger_reason"] = "price"
    mct = raw.get("offer_min_cart_total")
    if mct is None or mct == "":
        out["offer_min_cart_total"] = None
    else:
        try:
            f = float(mct)
            out["offer_min_cart_total"] = f if f > 0 else None
        except (TypeError, ValueError):
            out["offer_min_cart_total"] = None
    od = raw.get("offer_delay_minutes")
    try:
        om = int(od) if od is not None else 0
        out["offer_delay_minutes"] = max(0, min(om, 10080))
    except (TypeError, ValueError):
        out["offer_delay_minutes"] = 0
    mx = raw.get("offer_max_uses")
    if mx is None or mx == "":
        out["offer_max_uses"] = None
    else:
        try:
            u = int(mx)
            out["offer_max_uses"] = u if u >= 1 else None
        except (TypeError, ValueError):
            out["offer_max_uses"] = None
    return out


def merchant_offer_settings_from_store_row(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "cf_merchant_offer_settings_json", None) if row is not None else None
    if not isinstance(raw, str) or not raw.strip():
        return dict(DEFAULT_MERCHANT_OFFER_SETTINGS)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return dict(DEFAULT_MERCHANT_OFFER_SETTINGS)
    return normalize_merchant_offer_settings(data)


def merge_merchant_offer_settings_from_body(row: Optional[Any], body: Dict[str, Any]) -> Dict[str, Any]:
    base = merchant_offer_settings_from_store_row(row)
    patch = body.get("merchant_offer_settings")
    if not isinstance(patch, dict):
        return base
    merged = dict(base)
    merged.update(patch)
    return normalize_merchant_offer_settings(merged)


def apply_merchant_offer_settings_from_body(row: Any, body: Dict[str, Any]) -> None:
    if not isinstance(body.get("merchant_offer_settings"), dict):
        return
    normalized = normalize_merchant_offer_settings(body["merchant_offer_settings"])
    row.cf_merchant_offer_settings_json = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":")
    )


def merchant_offer_settings_for_api(row: Optional[Any]) -> Dict[str, Any]:
    return {"merchant_offer_settings": merchant_offer_settings_from_store_row(row)}


def normalize_product_catalog(raw: Any) -> Dict[str, Any]:
    """{version: 1, products: [...]} — حدود آمنة؛ لا منتجات وهمية."""
    out: Dict[str, Any] = {"version": 1, "products": []}
    if not isinstance(raw, dict):
        return out
    ver = raw.get("version")
    try:
        v = int(ver) if ver is not None else 1
    except (TypeError, ValueError):
        v = 1
    out["version"] = 1 if v != 1 else 1
    prods = raw.get("products")
    if not isinstance(prods, list):
        return out
    cleaned: list[Dict[str, Any]] = []
    for p in prods[:500]:
        if not isinstance(p, dict):
            continue
        pid = p.get("id") or p.get("product_id") or p.get("sku")
        pid_s = str(pid).strip()[:128] if pid is not None else ""
        name = p.get("name") or p.get("title") or ""
        name_s = str(name).strip()[:300]
        if not name_s:
            continue
        price_v: Optional[float] = None
        for k in ("price", "sale_price", "unit_price", "amount"):
            if k in p and p[k] is not None:
                try:
                    price_v = float(p[k])
                    if price_v > 0:
                        break
                except (TypeError, ValueError):
                    continue
        if price_v is None or price_v <= 0:
            continue
        cat = p.get("category") or p.get("product_category")
        if isinstance(cat, dict):
            cat = cat.get("name") or cat.get("title")
        cat_s = str(cat).strip()[:120] if cat is not None else ""
        url = p.get("url") or p.get("product_url") or p.get("link")
        url_s = str(url).strip()[:2048] if url is not None else ""
        avail = p.get("available")
        if avail is None:
            avail = p.get("in_stock")
        available = True if avail is None else _boolish(avail, True)
        cleaned.append(
            {
                "id": pid_s or name_s[:64],
                "name": name_s,
                "price": round(price_v, 2),
                "category": cat_s,
                "url": url_s,
                "available": available,
            }
        )
    out["products"] = cleaned
    return out


def product_catalog_from_store_row(row: Optional[Any]) -> Dict[str, Any]:
    raw = getattr(row, "cf_product_catalog_json", None) if row is not None else None
    if not isinstance(raw, str) or not raw.strip():
        return normalize_product_catalog({})
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return normalize_product_catalog({})
    return normalize_product_catalog(data if isinstance(data, dict) else {})


def merge_product_catalog_from_body(row: Optional[Any], body: Dict[str, Any]) -> Dict[str, Any]:
    base = product_catalog_from_store_row(row)
    patch = body.get("product_catalog")
    if not isinstance(patch, dict):
        return base
    merged = dict(base)
    merged.update(patch)
    return normalize_product_catalog(merged)


def apply_product_catalog_from_body(row: Any, body: Dict[str, Any]) -> None:
    if not isinstance(body.get("product_catalog"), dict):
        return
    normalized = normalize_product_catalog(body["product_catalog"])
    row.cf_product_catalog_json = json.dumps(
        normalized, ensure_ascii=False, separators=(",", ":")
    )[:520000]


def product_catalog_for_api(row: Optional[Any]) -> Dict[str, Any]:
    return {"product_catalog": product_catalog_from_store_row(row)}


def offer_applications_count_for_api(row: Optional[Any]) -> Dict[str, Any]:
    if row is None:
        return {"offer_applications_count": 0}
    try:
        n = int(getattr(row, "cf_offer_applications_count", 0) or 0)
    except (TypeError, ValueError):
        n = 0
    return {"offer_applications_count": max(0, n)}
