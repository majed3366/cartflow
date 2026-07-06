# -*- coding: utf-8 -*-
"""Product Excellence Visual Rebuild V1 — isolated preview routes (static HTML only)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from starlette.responses import FileResponse

router = APIRouter(tags=["product-excellence-preview"])

_ROOT = Path(__file__).resolve().parents[1]
_PREVIEW_DIR = (_ROOT / "scripts" / "_product_excellence_visual_rebuild_v1").resolve()

_PAGE_FILES: dict[str, str] = {
    "index": "index.html",
    "home": "home_prototype.html",
    "carts": "carts_prototype.html",
    "cart-detail": "cart_detail_prototype.html",
    "compare/home-before": "before_home.html",
    "compare/carts-before": "before_carts.html",
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


@router.get("/preview/product-excellence")
@router.get("/preview/product-excellence/")
def product_excellence_preview_hub() -> FileResponse:
    """Comparison hub — visual approval gate only."""
    return FileResponse(
        _preview_file("index"),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": "product-excellence-v1"},
    )


@router.get("/preview/product-excellence/home")
def product_excellence_preview_home() -> FileResponse:
    return FileResponse(
        _preview_file("home"),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": "product-excellence-v1"},
    )


@router.get("/preview/product-excellence/carts")
def product_excellence_preview_carts() -> FileResponse:
    return FileResponse(
        _preview_file("carts"),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": "product-excellence-v1"},
    )


@router.get("/preview/product-excellence/cart-detail")
def product_excellence_preview_cart_detail() -> FileResponse:
    return FileResponse(
        _preview_file("cart-detail"),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": "product-excellence-v1"},
    )


@router.get("/preview/product-excellence/compare/{compare_name}")
def product_excellence_preview_compare(compare_name: str) -> FileResponse:
    key = f"compare/{compare_name}"
    return FileResponse(
        _preview_file(key),
        media_type="text/html; charset=utf-8",
        headers={"X-CartFlow-Preview": "product-excellence-v1"},
    )


@router.get("/preview/product-excellence/assets/{asset_path:path}")
def product_excellence_preview_asset(asset_path: str) -> FileResponse:
    path = _preview_asset(asset_path)
    media = "text/css; charset=utf-8" if path.suffix == ".css" else None
    return FileResponse(path, media_type=media)
