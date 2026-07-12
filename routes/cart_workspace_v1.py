# -*- coding: utf-8 -*-
"""Cart Workspace routes — shadow/dev only. No merchant UI. Flag default OFF."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

from json_response import j
from services.cart_workspace.feature_flag_v1 import cart_workspace_v1_enabled, cart_workspace_v1_flag_state
from services.cart_workspace.golden_scenarios_v1 import list_golden_ids, run_all_goldens, run_golden
from services.cart_workspace.shadow_pipeline_v1 import run_scenario, shadow_snapshot
from services.cart_workspace.shadow_store_v1 import SHADOW_STORE

from services.cart_workspace.merchant_api_v1 import router as merchant_api_router

router = APIRouter(tags=["cart-workspace-shadow"])
# Merchant surface APIs (flag-gated) — same module surface for Cart Workspace
router.include_router(merchant_api_router)

_TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "cart_workspace_shadow_render_dev.html"


def _dev_only() -> bool:
    try:
        import main as _main  # noqa: PLC0415

        return bool(_main._is_development_mode())
    except Exception:
        return False


def _opt_str(value: Optional[str]) -> Optional[str]:
    """FastAPI Query defaults are objects when the view is called outside the framework."""
    return value if isinstance(value, str) and value.strip() else None


def _opt_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    return default


@router.get("/dev/cart-workspace-projection")
def dev_cart_workspace_projection(
    store_slug: str = Query("demo"),
    scenario: Optional[str] = Query(
        None,
        description="Legacy shadow scenario id (quiet|r03_admit|…)",
    ),
    golden: Optional[str] = Query(
        None,
        description="Golden scenario id GS-01…GS-10",
    ),
    reset: bool = Query(False),
    scenario_reset: bool = Query(True),
):
    """Shadow Mode operational truth dump. Dev only. No merchant activation."""
    if not _dev_only():
        return PlainTextResponse("Not found", status_code=404)

    scenario = _opt_str(scenario)
    golden = _opt_str(golden)
    store_slug = store_slug if isinstance(store_slug, str) else "demo"
    reset_b = _opt_bool(reset, False)
    scenario_reset_b = _opt_bool(scenario_reset, True)

    if golden:
        payload = run_golden(golden, store=SHADOW_STORE, reset=bool(reset_b or scenario_reset_b))
        payload["flag"] = cart_workspace_v1_flag_state()
        payload["merchant_surface_active"] = False
        payload["merchant_flag_enabled"] = cart_workspace_v1_enabled()
        if payload.get("snapshot") and payload["snapshot"].get("projection"):
            payload["projection"] = payload["snapshot"]["projection"]
        return j(payload)

    if scenario:
        do_reset = reset_b or scenario_reset_b
        payload = run_scenario(scenario, store=SHADOW_STORE, reset=do_reset)
        payload["flag"] = cart_workspace_v1_flag_state()
        payload["merchant_surface_active"] = False
        return j(payload)

    if reset_b:
        SHADOW_STORE.reset()

    snap = shadow_snapshot(store_slug, store=SHADOW_STORE)
    snap["note"] = "Shadow projection only; merchant surface gated by CARTFLOW_CART_WORKSPACE_V1"
    snap["flag"] = cart_workspace_v1_flag_state()
    snap["merchant_surface_active"] = False
    snap["golden_ids"] = list_golden_ids()
    return j(snap)


@router.get("/dev/cart-workspace-golden")
def dev_cart_workspace_golden_all():
    """Run all GS-01…GS-10. Dev only."""
    if not _dev_only():
        return PlainTextResponse("Not found", status_code=404)
    report = run_all_goldens()
    report["flag"] = cart_workspace_v1_flag_state()
    report["merchant_surface_active"] = False
    return j(report)


@router.get("/dev/cart-workspace-render", response_class=HTMLResponse)
def dev_cart_workspace_render_harness():
    """
    Dev-only paint harness for Sprint 2 Rendering Foundation.
    Does not replace merchant carts page. Not linked from merchant nav.
    """
    if not _dev_only():
        return PlainTextResponse("Not found", status_code=404)
    if not _TEMPLATE.is_file():
        return PlainTextResponse("template missing", status_code=500)
    html = _TEMPLATE.read_text(encoding="utf-8")
    return HTMLResponse(html)
