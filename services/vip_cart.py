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


VIP_OFFER_TYPES = frozenset({"discount", "free_shipping", "gift_wrap", "gift"})


def apply_vip_offer_settings_from_body(row: Any, body: Dict[str, Any]) -> None:
    """تحديث جزئي لحقول العروض — لا يؤثر على الإرسال حتى يُستخدم لاحقاً."""
    touched = False
    if "vip_offer_enabled" in body:
        touched = True
        row.vip_offer_enabled = bool(body.get("vip_offer_enabled"))
    if "vip_offer_type" in body:
        touched = True
        vt = body.get("vip_offer_type")
        if vt is None or (isinstance(vt, str) and not vt.strip()):
            row.vip_offer_type = None
        else:
            s = str(vt).strip()[:32]
            row.vip_offer_type = s if s in VIP_OFFER_TYPES else None
    if "vip_offer_value" in body:
        touched = True
        vv = body.get("vip_offer_value")
        if vv is None or (isinstance(vv, str) and not vv.strip()):
            row.vip_offer_value = None
        else:
            row.vip_offer_value = str(vv).strip()[:500]
    if not touched:
        return
    otype = getattr(row, "vip_offer_type", None)
    if otype in ("free_shipping", "gift_wrap"):
        row.vip_offer_value = None
    elif otype == "discount" and getattr(row, "vip_offer_value", None):
        try:
            p = int(str(row.vip_offer_value).strip())
        except (TypeError, ValueError):
            row.vip_offer_value = None
        else:
            if p < 1 or p > 100:
                row.vip_offer_value = None
            else:
                row.vip_offer_value = str(p)


def vip_offer_fields_for_api(row: Optional[Any]) -> Dict[str, Any]:
    if row is None:
        return {
            "vip_offer_enabled": False,
            "vip_offer_type": None,
            "vip_offer_value": None,
        }
    en = getattr(row, "vip_offer_enabled", False)
    try:
        enabled = bool(en)
    except (TypeError, ValueError):
        enabled = False
    ot = getattr(row, "vip_offer_type", None)
    ov = getattr(row, "vip_offer_value", None)
    ot_out = ot.strip()[:32] if isinstance(ot, str) and ot.strip() else None
    ov_out = ov.strip()[:500] if isinstance(ov, str) and ov.strip() else None
    if ot_out not in VIP_OFFER_TYPES:
        ot_out = None
    return {
        "vip_offer_enabled": enabled,
        "vip_offer_type": ot_out,
        "vip_offer_value": ov_out,
    }


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
