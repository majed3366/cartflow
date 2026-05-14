# -*- coding: utf-8 -*-
"""مسار تجربة المتجر التجريبي فقط (‎slug=demo‎): ‎?reset_demo=1‎ يولّد هويات جديدة وينظّف ‎storage‎ المحلي."""
from __future__ import annotations

import logging
from typing import Any

from services.demo_pi_fresh_session import (
    merge_demo_pi_fresh_query_into_context,
    new_demo_tracking_identity_pair,
)

log = logging.getLogger("cartflow")

_DEMO_PRIMARY_SLUG = "demo"


def merge_demo_reset_query_into_context(request: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """
    إن وُجد ‎reset_demo=1|true|yes‎ والمتجر ‎demo‎ (وليس ‎demo2‎): يضبط سياق القالب لتشغيل
    مسح ‎storage‎ في المتصفح وضبط ‎session_id‎ و‎cart_event_id‎ جديدين.
    لا يمس قواعد الاسترجاع ولا المتاجر الإنتاجية.
    """
    slug = str(ctx.get("demo_store_slug") or "").strip()
    if slug != _DEMO_PRIMARY_SLUG:
        return ctx
    try:
        qp = getattr(request, "query_params", None)
    except Exception:  # noqa: BLE001
        qp = None
    if qp is None:
        return ctx
    flag = str(qp.get("reset_demo") or "").strip().lower()
    if flag not in ("1", "true", "yes"):
        return ctx

    sid, cid = new_demo_tracking_identity_pair()
    ctx["demo_reset_applied"] = True
    ctx["demo_reset_session_id"] = sid
    ctx["demo_reset_cart_event_id"] = cid
    try:
        log.info(
            "[CF DEMO SESSION RESET] store_slug=demo session_id=%s cart_event_id=%s",
            (sid or "")[:80],
            (cid or "")[:80],
        )
    except Exception:  # noqa: BLE001
        pass
    return ctx


def merge_demo_primary_store_demo_queries(request: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """سلسلة ‎/demo/store*‎ (المتجر الافتراضي ‎demo‎ فقط): ‎reset_demo‎ ثم ‎fresh‎ إن وُجد."""
    ctx = merge_demo_reset_query_into_context(request, ctx)
    return merge_demo_pi_fresh_query_into_context(request, ctx)
