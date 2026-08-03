# -*- coding: utf-8 -*-
"""Admin API — Meta WhatsApp message template operations."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from json_response import j
from services.cartflow_admin_http_auth import (
    admin_cookie_name,
    admin_password_configured,
    admin_session_cookie_valid,
)
from services.meta_recovery_template_contract_v1 import (
    TEMPLATE_NAME,
    local_contract_summary,
)

router = APIRouter(tags=["admin-meta-templates"])


def _admin_json_auth(request: Request) -> Optional[JSONResponse]:
    if not admin_password_configured():
        return JSONResponse(status_code=503, content={"ok": False, "error": "admin_not_configured"})
    cookie = request.cookies.get(admin_cookie_name())
    if not admin_session_cookie_valid(cookie):
        return JSONResponse(status_code=401, content={"ok": False, "error": "unauthorized"})
    return None


@router.get("/admin/api/whatsapp/meta-templates")
def api_admin_meta_templates_list(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.meta_template_operations_v1 import list_meta_templates  # noqa: PLC0415

    return j(list_meta_templates())


@router.get("/admin/api/whatsapp/meta-templates/recovery-contract")
def api_admin_meta_recovery_contract_status(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    from services.meta_template_operations_v1 import (  # noqa: PLC0415
        get_recovery_template_status,
    )

    return j(get_recovery_template_status())


@router.get("/admin/api/whatsapp/meta-templates/recovery-contract/local")
def api_admin_meta_recovery_contract_local(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    return j({"ok": True, "local_contract": local_contract_summary()})


@router.post("/admin/api/whatsapp/meta-templates/recovery-contract/create")
async def api_admin_meta_recovery_contract_create(request: Request) -> Any:
    denied = _admin_json_auth(request)
    if denied is not None:
        return denied
    try:
        body = await request.json()
    except (TypeError, ValueError):
        body = {}
    if not isinstance(body, dict):
        body = {}
    confirm = body.get("confirm") is True
    template_name = str(body.get("template_name") or "").strip() or TEMPLATE_NAME
    from services.meta_template_operations_v1 import create_recovery_template  # noqa: PLC0415

    return j(
        create_recovery_template(
            confirm=confirm,
            template_name=template_name,
        )
    )
