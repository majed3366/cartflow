# -*- coding: utf-8 -*-
"""VIP سلة: عتبة على ‎Store‎ — عند ‎cart_total >= threshold‎ يفعّل ‎main‎ مسار المتابعة اليدوية (بدون استرجاع تلقائي للعميل)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def is_vip_cart(cart_total: Any, store: Any) -> bool:
    """
    إذا وُجدت عتبة صالحة على المتجر وقيمة السلة >= العتبة → ‎True‎.
    ‎NULL‎ أو غياب العمود أو قيم غير رقمية → ‎False‎ (الميزة معطّلة).
    """
    if store is None:
        return False
    raw_th = getattr(store, "vip_cart_threshold", None)
    if raw_th is None:
        return False
    try:
        threshold = int(raw_th)
    except (TypeError, ValueError):
        return False
    if threshold < 1:
        return False
    try:
        total = float(cart_total) if cart_total is not None else 0.0
    except (TypeError, ValueError):
        return False
    return total >= float(threshold)


def apply_vip_cart_threshold_from_body(row: Any, body: Dict[str, Any]) -> None:
    """تحديث جزئي: المفتاح الغائب لا يغيّر القيمة."""
    if "vip_cart_threshold" not in body:
        return
    raw = body.get("vip_cart_threshold")
    if raw is None:
        row.vip_cart_threshold = None
        return
    if isinstance(raw, str) and not raw.strip():
        row.vip_cart_threshold = None
        return
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return
    row.vip_cart_threshold = v if v >= 1 else None


def vip_cart_threshold_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    if row is None:
        return {"vip_cart_threshold": None}
    raw = getattr(row, "vip_cart_threshold", None)
    if raw is None:
        return {"vip_cart_threshold": None}
    try:
        return {"vip_cart_threshold": int(raw)}
    except (TypeError, ValueError):
        return {"vip_cart_threshold": None}
