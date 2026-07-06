# -*- coding: utf-8 -*-
"""Product Excellence Visual Rebuild V2 — isolated preview routes (static HTML only)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

router = APIRouter(tags=["product-excellence-preview-v2"])

_ROOT = Path(__file__).resolve().parents[1]
_PREVIEW_DIR = (_ROOT / "scripts" / "_product_excellence_visual_rebuild_v2").resolve()

_PREVIEW_HEADER = "product-excellence-v2"

_PAGE_FILES: dict[str, str] = {
    "home": "home_v2.html",
    "carts": "carts_v2.html",
    "cart-detail": "cart_detail_v2.html",
}


def _preview_file(name: str) -> Path:
    rel = _PAGE_FILES.get(name)
    if not rel:
        raise HTTPException(status_code=404, detail="Not found")
    path = (_PREVIEW_DIR / rel).resolve()
    if not str(path).startswith(str(_PREVIEW_DIR)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return path


def _preview_asset(asset_path: str) -> Path:
    path = (_PREVIEW_DIR / asset_path).resolve()
    if not str(path).startswith(str(_PREVIEW_DIR)) or not path.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    return path


def _html_response(name: str) -> FileResponse:
    return FileResponse(
        _preview_file(name),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": _PREVIEW_HEADER},
    )


@router.get("/preview/product-excellence-v2/home")
def product_excellence_v2_preview_home() -> FileResponse:
    return _html_response("home")


@router.get("/preview/product-excellence-v2/carts")
def product_excellence_v2_preview_carts() -> FileResponse:
    return _html_response("carts")


@router.get("/preview/product-excellence-v2/cart-detail")
def product_excellence_v2_preview_cart_detail() -> FileResponse:
    return _html_response("cart-detail")


@router.get("/preview/product-excellence-v2/assets/{asset_path:path}")
def product_excellence_v2_preview_asset(asset_path: str) -> FileResponse:
    path = _preview_asset(asset_path)
    media = "text/css; charset=utf-8" if path.suffix == ".css" else None
    return FileResponse(path, media_type=media)
