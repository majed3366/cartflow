# -*- coding: utf-8 -*-
"""Merchant password reset delivery via Resend (optional)."""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple
from urllib.parse import quote, urlparse

import requests

log = logging.getLogger("cartflow")


def _is_development_env() -> bool:
    return (os.getenv("ENV") or "").strip().lower() == "development"

_RESEND_API_URL = "https://api.resend.com/emails"
_RESET_SUBJECT = "استعادة كلمة المرور — CartFlow"


def log_resend_password_reset_startup() -> None:
    """Safe startup probe — warn only, never raise."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    if not api_key:
        log.warning(
            "[RESEND] RESEND_API_KEY not set — merchant password reset emails disabled"
        )
        return
    from_email = (os.getenv("RESEND_FROM_EMAIL") or "").strip()
    if not from_email:
        log.warning(
            "[RESEND] RESEND_FROM_EMAIL not set — password reset sends may fail at Resend"
        )
    else:
        log.info("[RESEND] password reset email delivery configured")


def public_reset_base_url() -> str:
    return (
        (os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "")
        .strip()
        .rstrip("/")
    )


def build_password_reset_link(raw_token: str, base_url: Optional[str] = None) -> str:
    path = f"/reset-password?token={quote(raw_token, safe='')}"
    base = (base_url if base_url is not None else public_reset_base_url()).strip().rstrip(
        "/"
    )
    if base:
        return f"{base}{path}"
    return path


def _reset_path_for_dev_display(reset_link: str) -> str:
    if reset_link.startswith("/"):
        return reset_link
    parsed = urlparse(reset_link)
    out = parsed.path or "/reset-password"
    if parsed.query:
        out = f"{out}?{parsed.query}"
    return out


def _password_reset_email_text(reset_link: str) -> str:
    return (
        "مرحبا،\n\n"
        "تم طلب استعادة كلمة المرور لحسابك.\n\n"
        "اضغط الرابط التالي:\n\n"
        f"{reset_link}\n\n"
        "إذا لم تطلب ذلك، تجاهل هذه الرسالة.\n"
    )


def _send_via_resend(*, to_email: str, reset_link: str) -> bool:
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    from_email = (os.getenv("RESEND_FROM_EMAIL") or "").strip()
    if not api_key or not from_email:
        return False
    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": _RESET_SUBJECT,
        "text": _password_reset_email_text(reset_link),
    }
    try:
        resp = requests.post(
            _RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
    except requests.RequestException as exc:
        log.warning(
            "[MERCHANT PASSWORD RESET] resend request failed exc_type=%s exc=%s",
            type(exc).__name__,
            exc,
        )
        return False
    if resp.status_code not in (200, 201):
        log.warning(
            "[MERCHANT PASSWORD RESET] resend HTTP %s body=%s",
            resp.status_code,
            (resp.text or "")[:500],
        )
        return False
    return True


def deliver_password_reset_email(
    *,
    to_email: str,
    reset_link: str,
) -> Tuple[bool, Optional[str]]:
    """
    Send reset email when Resend is configured.
    Returns (email_attempted_and_sent, dev_reset_path_or_none).
    Development without API key: log link and return path for UI hint.
    Never raises — caller keeps generic user-facing message.
    """
    dev_path = _reset_path_for_dev_display(reset_link)
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()

    if api_key:
        sent = _send_via_resend(to_email=to_email, reset_link=reset_link)
        if sent:
            log.info("[MERCHANT PASSWORD RESET] resend delivered to=%s", to_email)
            if _is_development_env():
                return True, dev_path
            return True, None
        log.warning(
            "[MERCHANT PASSWORD RESET] resend send failed to=%s (user message unchanged)",
            to_email,
        )

    if _is_development_env():
        log.info("[MERCHANT AUTH DEV] password reset link: %s", dev_path)
        return False, dev_path

    return False, None


__all__ = [
    "build_password_reset_link",
    "deliver_password_reset_email",
    "log_resend_password_reset_startup",
    "public_reset_base_url",
]
