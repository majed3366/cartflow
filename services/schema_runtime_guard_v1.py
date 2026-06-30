# -*- coding: utf-8 -*-
"""
Reliability Foundation V1 — Phase 0: disable runtime schema mutation on merchant HTTP paths.
"""
from __future__ import annotations

from services.recovery_process_role_v1 import is_api_process_role
from services.recovery_scheduler_guardrails import is_production_like_runtime


def request_schema_middleware_enabled() -> bool:
    """
    True only when legacy dev/staging may run ensure/bootstrap on HTTP requests.

    Production-like and API-role processes never run schema work per request.
    """
    if is_production_like_runtime():
        return False
    if is_api_process_role():
        return False
    return True


__all__ = ["request_schema_middleware_enabled"]
