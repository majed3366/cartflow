# -*- coding: utf-8 -*-
"""Meta WhatsApp Cloud API webhook routes."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from services.meta_whatsapp_webhook_v1 import (
    process_webhook_payload,
    verify_subscription,
)

log = logging.getLogger("cartflow")

router = APIRouter(tags=["meta-whatsapp-webhook"])


@router.get("/webhooks/meta/whatsapp")
async def meta_whatsapp_webhook_verify(
    request: Request,
) -> Any:
    qp = request.query_params
    ok, err, challenge = verify_subscription(
        str(qp.get("hub.mode") or ""),
        str(qp.get("hub.verify_token") or ""),
        str(qp.get("hub.challenge") or ""),
    )
    if not ok:
        log.warning("[CF META WA WEBHOOK] verify_failed reason=%s", err)
        return JSONResponse(
            {"ok": False, "error": err},
            status_code=403,
        )
    return PlainTextResponse(challenge or "", status_code=200)


@router.post("/webhooks/meta/whatsapp")
async def meta_whatsapp_webhook_events(request: Request) -> PlainTextResponse:
    payload: dict[str, Any] = {}
    try:
        body = await request.json()
        if isinstance(body, dict):
            payload = body
    except Exception as exc:  # noqa: BLE001
        log.warning("[CF META WA WEBHOOK] json_parse_failed: %s", exc)
        payload = {}

    try:
        process_webhook_payload(payload)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[CF META WA WEBHOOK] process_failed: %s",
            exc,
            exc_info=True,
        )

    return PlainTextResponse("OK", status_code=200)
