# -*- coding: utf-8 -*-
"""Governed product/customer behaviour profiles — planner probabilities only."""
from __future__ import annotations

from typing import Any

from services.demo_sandbox_catalog import SANDBOX_PRODUCTS

# Planner-facing product roles (map to demo catalog keys)
PRODUCT_ROLES: dict[str, dict[str, Any]] = {
    "low_price_volume": {"keys": ["charger", "watch_band"], "role": "low_price_volume"},
    "high_price_consideration": {"keys": ["hp_pro", "watch_pro"], "role": "high_price"},
    "shipping_hesitation": {"keys": ["perfume", "perfume_velvet"], "role": "shipping"},
    "high_atc_low_conv": {"keys": ["hoodie", "hoodie_essentials"], "role": "low_conv"},
    "wa_recovery": {"keys": ["earbuds", "hp_air"], "role": "wa"},
    "comparison": {"keys": ["hp_pro", "earbuds", "hp_air"], "role": "compare"},
    "vip": {"keys": ["hp_pro", "watch_pro"], "role": "vip"},
}

CUSTOMER_ARCHETYPES: tuple[str, ...] = (
    "fast_buyer",
    "price_sensitive",
    "shipping_sensitive",
    "comparison_shopper",
    "needs_reassurance",
    "high_value_vip",
    "repeated_visitor",
    "widget_engager",
    "whatsapp_responder",
    "recovery_resistant",
    "organic_buyer",
    "anonymous_no_phone",
)

# Platform reason tags only
REASON_WEIGHTS_BASELINE: dict[str, float] = {
    "price": 0.28,
    "shipping": 0.18,
    "thinking": 0.22,
    "quality": 0.12,
    "delivery": 0.08,
    "warranty": 0.05,
    "other": 0.07,
}

REASON_WEIGHTS_SHIPPING: dict[str, float] = {
    "shipping": 0.62,
    "price": 0.12,
    "thinking": 0.12,
    "delivery": 0.08,
    "quality": 0.03,
    "warranty": 0.01,
    "other": 0.02,
}


def catalog_product(key: str) -> dict[str, Any]:
    p = SANDBOX_PRODUCTS.get(key) or {}
    return {
        "key": key,
        "id": p.get("id") or f"demo_{key}",
        "name": p.get("name") or key,
        "price": float(p.get("price") or 0),
        "category": p.get("category") or "",
        "sku": p.get("sku") or "",
    }


def pick_product_key(role: str, rng: Any) -> str:
    meta = PRODUCT_ROLES.get(role) or PRODUCT_ROLES["low_price_volume"]
    keys = [k for k in meta["keys"] if k in SANDBOX_PRODUCTS]
    if not keys:
        keys = list(SANDBOX_PRODUCTS.keys())[:3]
    return rng.choice(keys)


def weighted_choice(weights: dict[str, float], rng: Any) -> str:
    items = list(weights.items())
    total = sum(max(0.0, float(w)) for _, w in items) or 1.0
    r = rng.random() * total
    acc = 0.0
    for key, w in items:
        acc += max(0.0, float(w))
        if r <= acc:
            return key
    return items[-1][0]
