# -*- coding: utf-8 -*-
"""Twilio / future Meta WhatsApp delivery status callbacks (additive)."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

log = logging.getLogger("cartflow")

router = APIRouter()


def _form_to_dict(form: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        for key in form.keys():
            val = form.get(key)
            if val is not None:
                out[str(key)] = val if isinstance(val, str) else str(val)
    except Exception:  # noqa: BLE001
        pass
    return out


@router.post("/webhook/whatsapp/status")
async def whatsapp_status_webhook(request: Request) -> PlainTextResponse:
    """
    Provider status callbacks (Twilio MessageStatus).
    Normalizes to DeliveryTruth only — does not run recovery or lifecycle.
    """
    payload: dict[str, Any]
    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            body = await request.json()
            payload = body if isinstance(body, dict) else {}
        else:
            form = await request.form()
            payload = _form_to_dict(form)
    except Exception as exc:  # noqa: BLE001
        log.warning("whatsapp status webhook parse failed: %s", exc)
        payload = {}

    try:
        from services.whatsapp_delivery_truth_v1 import ingest_twilio_status_callback

        ingest_twilio_status_callback(payload)
    except Exception as exc:  # noqa: BLE001
        log.warning("whatsapp status webhook ingest failed: %s", exc, exc_info=True)

    return PlainTextResponse("OK")
