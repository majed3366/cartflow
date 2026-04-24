# -*- coding: utf-8 -*-
"""
رسائل الاسترجاع — لحن سعودي، عربي أولاً، واضحة، بلا ضغط.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional


def build_abandoned_cart_message(cart_context: Mapping[str, Any]) -> str:
    """يُبنى نص تذكير بسيط من بيانات السلة (نفس شكل ‎/dev/mock-cart‎ أو ‎Zid)."""
    ctx: dict[str, Any] = dict(cart_context)
    name = (ctx.get("customer_name") or "").strip()
    cart_url = (ctx.get("cart_url") or ctx.get("checkout_url") or "").strip()
    cart_value = ctx.get("cart_value")
    items = ctx.get("items") or []
    product_name: Optional[str] = None
    if isinstance(items, list) and items:
        first = items[0]
        if isinstance(first, dict):
            product_name = (first.get("name") or first.get("title") or first.get("product_name") or "").strip() or None

    greet = f"هلا {name} 👋" if name else "هلا 👋"
    if product_name and cart_url:
        return (
            f"{greet} لاحظنا إنك تركت «{product_name}» في السلة. "
            f"إذا حاب تكمل طلبك، تقدر ترجع لها من هنا: {cart_url}"
        )
    if cart_url:
        if cart_value is not None:
            try:
                v = float(cart_value)
                v_str = f"{v:g}" if v == int(v) else f"{v:.2f}"
            except (TypeError, ValueError):
                v_str = str(cart_value)
            return (
                f"{greet} لاحظنا إنك تركت سلتك بمبلغ تقريباً {v_str} ر.س. "
                f"إذا حاب تكمل، الرابط هنا: {cart_url}"
            )
        return (
            f"{greet} لاحظنا إنك تركت بعض المنتجات في السلة. "
            f"إذا حاب تكمل طلبك، تقدر ترجع لها من هنا: {cart_url}"
        )
    if product_name:
        return f"{greet} لاحظنا إن «{product_name}» باقي في السلة. ودّك تكمل الطلب؟"
    return f"{greet} ودّك تكمل طلبك؟ نحن جاهزين نساعدك إذا حاب."

