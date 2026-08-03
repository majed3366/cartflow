# -*- coding: utf-8 -*-
"""Twilio WhatsApp provider — wraps existing send_whatsapp without behavior change."""
from __future__ import annotations

from typing import Any

from services.whatsapp_providers.contracts import (
    PROVIDER_TWILIO,
    WhatsAppProviderRequest,
    WhatsAppProviderResult,
    empty_provider_result,
)


def send_via_twilio(req: WhatsAppProviderRequest) -> dict[str, Any]:
    """
    Delegate to ``services.whatsapp_send.send_whatsapp``.

    Returns a legacy-compatible dict (ok/sid/status/error) plus canonical fields.
    """
    from services.whatsapp_send import WA_TRACE_DELAY_UNSPECIFIED, send_whatsapp

    delay_passed = req.wa_trace_delay_passed
    if delay_passed is None:
        delay_passed = WA_TRACE_DELAY_UNSPECIFIED

    legacy = send_whatsapp(
        req.to_phone,
        req.body_text,
        reason_tag=req.reason_tag,
        recovery_key=req.recovery_key,
        wa_trace_path=req.wa_trace_path,
        wa_trace_session_id=req.session_id,
        wa_trace_store_slug=req.store_slug,
        wa_trace_last_activity=req.wa_trace_last_activity,
        wa_trace_recovery_delay_minutes=req.wa_trace_recovery_delay_minutes,
        wa_trace_delay_passed=delay_passed,
    )
    if not isinstance(legacy, dict):
        result = empty_provider_result(
            PROVIDER_TWILIO,
            error_code="invalid_provider_response",
            error_message_safe="invalid_provider_response",
            message_mode=req.message_mode,
        )
        return result.to_legacy_wa_dict()

    ok = legacy.get("ok") is True
    sid = str(legacy.get("sid") or "").strip() or None
    err = str(legacy.get("error") or "").strip() or None
    status = legacy.get("status")
    status_str = str(status) if status is not None else None

    canonical = WhatsAppProviderResult(
        provider=str(legacy.get("provider") or PROVIDER_TWILIO),
        accepted=ok,
        external_message_id=sid,
        provider_status=status_str,
        error_code=None if ok else (err or "twilio_send_failed"),
        error_subcode=None,
        error_message_safe=None if ok else (err or "twilio_send_failed"),
        retryable=bool(err == "provider_timeout") if not ok else False,
        raw_payload_stored=False,
        message_mode=req.message_mode,
    )
    out = dict(legacy)
    out.update(
        {
            "provider": canonical.provider,
            "accepted": canonical.accepted,
            "external_message_id": canonical.external_message_id,
            "provider_status": canonical.provider_status,
            "error_code": canonical.error_code,
            "error_subcode": canonical.error_subcode,
            "error_message_safe": canonical.error_message_safe,
            "retryable": canonical.retryable,
            "raw_payload_stored": False,
            "message_mode": req.message_mode,
        }
    )
    if not ok and "error" not in out:
        out["error"] = canonical.error_message_safe
    return out
