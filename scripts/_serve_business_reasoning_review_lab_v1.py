# -*- coding: utf-8 -*-
"""Lightweight Product review host for Business Reasoning Review Lab V1.

Serves only /dev/business-reasoning-review (fixture by default).
Does not start the full production app or touch Home / Products / Knowledge.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.business_reasoning_review_lab_v1 import (  # noqa: E402
    build_reasoning_review_lab_payload_v1,
)

app = FastAPI(title="Business Reasoning Review Lab V1", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(ROOT / "templates"))


@app.get("/")
def root() -> dict:
    return {
        "ok": True,
        "review": "/dev/business-reasoning-review?source=fixture&store=demo",
    }


@app.get("/dev/business-reasoning-review", response_class=HTMLResponse)
def business_reasoning_review(
    request: Request,
    source: str = Query("fixture"),
    store: str = Query("demo"),
):
    payload = build_reasoning_review_lab_payload_v1(
        store_slug=(store or "demo").strip() or "demo",
        source=(source or "fixture").strip() or "fixture",
    )
    return templates.TemplateResponse(
        request,
        "business_reasoning_review_lab_v1.html",
        {"request": request, "payload": payload},
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8766"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
