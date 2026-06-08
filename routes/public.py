# -*- coding: utf-8 -*-
"""Public marketing pages and legacy redirects."""
from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import RedirectResponse

router = APIRouter(tags=["public"])


@router.get("/")
def home(request: Request):
    """الصفحة العامة — واجهة تسويق CartFlow (عربي، RTL مع تخطيط مطابق للمرجع)."""
    from main import templates  # lazy — avoid circular import at module load

    return templates.TemplateResponse(
        request,
        "cartflow_landing.html",
        {"request": request},
    )


@router.get("/register")
def register_placeholder(request: Request):
    """إعادة توجيه — التسجيل الفعلي عند ‎/signup‎."""
    return RedirectResponse(url="/signup", status_code=302)
