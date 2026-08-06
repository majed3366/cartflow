# -*- coding: utf-8 -*-
"""
Scheduler Meta Preflight V1 — read-only process-local provider config probe.

Also emits ``[SCHEDULER META RUNTIME]`` startup lines on the Scheduler process.

No Graph calls. No DB. No sends. Never returns/logs secrets or full Meta IDs.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from services.admin_whatsapp_meta_status_v1 import (
    PLACEHOLDER_TOKENS,
    read_whatsapp_meta_env,
)
from services.deploy_build_info_v1 import resolve_deploy_git_sha
from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.recovery_process_role_v1 import resolve_process_role
from services.whatsapp_provider import PROVIDER_META, resolve_whatsapp_provider

EXPECTED_META_RECOVERY_TEMPLATE = TEMPLATE_NAME  # cartflow_cart_reminder_ar_v2

log = logging.getLogger("cartflow")


def _env_configured(raw: str) -> bool:
    v = (raw or "").strip()
    if not v:
        return False
    if v.lower() in PLACEHOLDER_TOKENS:
        return False
    return True


def _bool_word(value: bool) -> str:
    return "true" if value else "false"


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


def format_scheduler_meta_runtime_log_lines(
    payload: Optional[dict[str, Any]] = None,
) -> list[str]:
    """
    Sanitized startup log lines for ``[SCHEDULER META RUNTIME]``.

    Never includes access tokens, Authorization headers, or full Meta IDs.
    """
    data = payload if isinstance(payload, dict) else build_scheduler_meta_preflight()
    template_name = data.get("meta_template_name")
    template_s = template_name if isinstance(template_name, str) and template_name else ""
    return [
        "[SCHEDULER META RUNTIME]",
        f"role={data.get('role')}",
        f"whatsapp_provider={data.get('whatsapp_provider')}",
        f"meta_template_name={template_s}",
        f"access_token_configured={_bool_word(bool(data.get('access_token_configured')))}",
        f"phone_number_id_configured={_bool_word(bool(data.get('phone_number_id_configured')))}",
        f"waba_id_configured={_bool_word(bool(data.get('waba_id_configured')))}",
        f"ready_for_meta_recovery={_bool_word(bool(data.get('ready_for_meta_recovery')))}",
    ]


def log_scheduler_meta_runtime(*, role: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Emit ``[SCHEDULER META RUNTIME]`` on Scheduler processes only.

    Safe no-op for api/unset/unknown roles. Never logs secrets.
    """
    resolved_role = (role or resolve_process_role() or "").strip().lower()
    if resolved_role != "scheduler":
        return None

    payload = build_scheduler_meta_preflight()
    # Role gate already enforced; keep payload role explicit for log truth.
    payload["role"] = "scheduler"
    template_env = str(payload.get("meta_template_name") or "")
    payload["ready_for_meta_recovery"] = bool(
        payload.get("whatsapp_provider") == PROVIDER_META
        and template_env == EXPECTED_META_RECOVERY_TEMPLATE
        and payload.get("access_token_configured")
        and payload.get("phone_number_id_configured")
        and payload.get("waba_id_configured")
    )

    for line in format_scheduler_meta_runtime_log_lines(payload):
        try:
            print(line, flush=True)
        except OSError:
            pass
        log.info("%s", line)
    return payload


__all__ = [
    "EXPECTED_META_RECOVERY_TEMPLATE",
    "build_scheduler_meta_preflight",
    "format_scheduler_meta_runtime_log_lines",
    "log_scheduler_meta_runtime",
]
