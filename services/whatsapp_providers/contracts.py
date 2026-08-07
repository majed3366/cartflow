# -*- coding: utf-8 -*-
"""Provider-neutral WhatsApp send contracts (recovery boundary)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional

PROVIDER_TWILIO = "twilio"
PROVIDER_META = "meta"

MODE_TEMPLATE = "template"
MODE_SESSION_TEXT = "session_text"


@dataclass
class WhatsAppProviderRequest:
    """Neutral outbound request — no Meta/Twilio payload leakage into recovery logic."""

    to_phone: str
    provider: str
    message_mode: str
    body_text: str = ""
    template_name: Optional[str] = None
    template_language: Optional[str] = None
    template_parameters: list[str] = field(default_factory=list)
    # URL button dynamic suffix (Meta {{1}} on checkout URL button)
    checkout_url: Optional[str] = None
    template_button_url_param: Optional[str] = None
    recovery_key: Optional[str] = None
    store_slug: Optional[str] = None
    store_display_name: Optional[str] = None
    store_name: Optional[str] = None
    idempotency_key: Optional[str] = None
    reason_tag: Optional[str] = None
    session_id: Optional[str] = None
    # Trace / gate fields (Twilio path compatibility)
    wa_trace_path: Optional[str] = None
    wa_trace_last_activity: Optional[Any] = None
    wa_trace_recovery_delay_minutes: Optional[Any] = None
    wa_trace_delay_passed: Any = None


@dataclass
class WhatsAppProviderResult:
    """Canonical provider result. Never includes access tokens."""

    provider: str
    accepted: bool
    external_message_id: Optional[str] = None
    provider_status: Optional[str] = None
    error_code: Optional[str] = None
    error_subcode: Optional[str] = None
    error_message_safe: Optional[str] = None
    error_trace_id: Optional[str] = None
    retryable: bool = False
    raw_payload_stored: bool = False
    message_mode: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_legacy_wa_dict(self) -> dict[str, Any]:
        """
        Shape expected by recovery lifecycle (ok / sid / status / error).

        ``accepted`` maps to provider acceptance only — not delivery confirmation.
        """
        out: dict[str, Any] = {
            "ok": bool(self.accepted),
            "sid": self.external_message_id,
            "status": self.provider_status,
            "provider": self.provider,
            "accepted": bool(self.accepted),
            "external_message_id": self.external_message_id,
            "provider_status": self.provider_status,
            "error_code": self.error_code,
            "error_subcode": self.error_subcode,
            "error_message_safe": self.error_message_safe,
            "error_trace_id": self.error_trace_id,
            "retryable": bool(self.retryable),
            "raw_payload_stored": False,
            "message_mode": self.message_mode,
        }
        if not self.accepted:
            out["error"] = self.error_message_safe or self.error_code or "provider_send_failed"
        return out


def empty_provider_result(
    provider: str,
    *,
    error_code: str,
    error_message_safe: str,
    retryable: bool = False,
    message_mode: Optional[str] = None,
    error_subcode: Optional[str] = None,
    error_trace_id: Optional[str] = None,
    provider_status: Optional[str] = None,
) -> WhatsAppProviderResult:
    return WhatsAppProviderResult(
        provider=provider,
        accepted=False,
        provider_status=provider_status or "rejected",
        error_code=error_code,
        error_subcode=error_subcode,
        error_message_safe=error_message_safe,
        error_trace_id=error_trace_id,
        retryable=retryable,
        raw_payload_stored=False,
        message_mode=message_mode,
    )
