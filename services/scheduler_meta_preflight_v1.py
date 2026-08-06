# -*- coding: utf-8 -*-
"""
Scheduler Meta Preflight V1 — read-only process-local provider config probe.

No Graph calls. No DB. No sends. Never returns secrets or full Meta IDs.
"""
from __future__ import annotations

import os
from typing import Any

from services.admin_whatsapp_meta_status_v1 import (
    PLACEHOLDER_TOKENS,
    read_whatsapp_meta_env,
)
from services.deploy_build_info_v1 import resolve_deploy_git_sha
from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.recovery_process_role_v1 import resolve_process_role
from services.whatsapp_provider import PROVIDER_META, resolve_whatsapp_provider

EXPECTED_META_RECOVERY_TEMPLATE = TEMPLATE_NAME  # cartflow_cart_reminder_ar_v2


def _env_configured(raw: str) -> bool:
    v = (raw or "").strip()
    if not v:
        return False
    if v.lower() in PLACEHOLDER_TOKENS:
        return False
    return True


def build_scheduler_meta_preflight() -> dict[str, Any]:
    """
    Build a safe preflight payload for the current process.

    Callers should gate HTTP access so only ``role==scheduler`` returns 200
    with readiness; this builder always returns the same field set.
    """
    role = resolve_process_role()
    provider = resolve_whatsapp_provider()
    template_env = (os.getenv("WHATSAPP_META_RECOVERY_TEMPLATE_NAME") or "").strip()
    env = read_whatsapp_meta_env()

    access_ok = _env_configured(env.get("access_token") or "")
    phone_ok = _env_configured(env.get("phone_number_id") or "")
    waba_ok = _env_configured(env.get("waba_id") or "")

    ready = bool(
        role == "scheduler"
        and provider == PROVIDER_META
        and template_env == EXPECTED_META_RECOVERY_TEMPLATE
        and access_ok
        and phone_ok
        and waba_ok
    )

    return {
        "role": role,
        "git_sha": resolve_deploy_git_sha(short=False),
        "whatsapp_provider": provider,
        "meta_template_name": template_env or None,
        "access_token_configured": access_ok,
        "phone_number_id_configured": phone_ok,
        "waba_id_configured": waba_ok,
        "template_expected_name": EXPECTED_META_RECOVERY_TEMPLATE,
        "ready_for_meta_recovery": ready,
    }


__all__ = [
    "EXPECTED_META_RECOVERY_TEMPLATE",
    "build_scheduler_meta_preflight",
]
