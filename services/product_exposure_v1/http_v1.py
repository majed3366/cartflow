# -*- coding: utf-8 -*-
"""FastAPI adapter for POST /api/storefront/product-viewed."""
from __future__ import annotations

from fastapi import Request

from json_response import j
from services.product_exposure_v1.ingest_v1 import IngestHttpError, ingest_product_viewed


async def handle_product_viewed(request: Request):
    raw = await request.body()
    origin = (request.headers.get("origin") or request.headers.get("Origin") or "").strip()
    try:
        body = ingest_product_viewed(raw_body=raw, origin=origin or None)
    except IngestHttpError as exc:
        return j({"ok": False, "error": exc.error}, exc.status)
    public = {
        "ok": True,
        "persisted": body["persisted"],
        "reason": body["reason"],
    }
    return j(public, 200)
