# -*- coding: utf-8 -*-
"""
تهيئة Sentry اختيارية — أداء + أخطاء. لا تُفعّل بدون ‎SENTRY_DSN‎.
"""
from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger("cartflow")


def init_cartflow_sentry(app: Any) -> None:
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        log.warning("[SENTRY] sentry-sdk not installed; pip install sentry-sdk")
        return

    traces = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.15"))
    profiles = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0"))

    sentry_sdk.init(
        dsn=dsn,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        environment=(os.getenv("SENTRY_ENVIRONMENT") or "production").strip(),
        release=(os.getenv("CARTFLOW_RELEASE") or "").strip() or None,
        traces_sample_rate=max(0.0, min(1.0, traces)),
        profiles_sample_rate=max(0.0, min(1.0, profiles)),
        send_default_pii=False,
    )
    log.info(
        "[SENTRY] initialized env=%s traces_sample_rate=%s",
        os.getenv("SENTRY_ENVIRONMENT", "production"),
        traces,
    )


def capture_whatsapp_failure(detail: str, *, extra: dict[str, Any] | None = None) -> None:
    """استدعاء من مسارات الإرسال عند فشل Twilio/Meta — يسهّل تنبيهات Sentry."""
    dsn = (os.getenv("SENTRY_DSN") or "").strip()
    if not dsn:
        return
    try:
        import sentry_sdk
    except ImportError:
        return
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("subsystem", "whatsapp")
        scope.set_level("error")
        if extra:
            for k, v in extra.items():
                scope.set_extra(k, v)
        sentry_sdk.capture_message(f"whatsapp_failure: {detail[:500]}", level="error")
