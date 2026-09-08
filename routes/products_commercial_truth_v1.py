# -*- coding: utf-8 -*-
"""Merchant Products V1 — bounded commercial truth read. No snapshot table."""
from __future__ import annotations

from fastapi import APIRouter

from json_response import j
from services.products_commercial_truth_v1 import compose_products_commercial_truth_v1

router = APIRouter(tags=["products-commercial-truth-v1"])


@router.get("/api/dashboard/products")
def api_dashboard_products():
    import main as _main  # noqa: PLC0415

    store = _main._dashboard_recovery_store_row()
    if store is None:
        return j({"ok": False, "error": "unauthorized"}, status_code=401)
    slug = str(getattr(store, "zid_store_id", "") or "").strip()
    pkg = compose_products_commercial_truth_v1(store_slug=slug, store=store)
    return j(pkg)
