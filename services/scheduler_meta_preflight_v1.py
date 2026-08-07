# -*- coding: utf-8 -*-
"""
Scheduler Meta Preflight V1 — read-only process-local provider config probe.

Emits one searchable ``[SCHEDULER META RUNTIME] …`` startup line on Scheduler.

No Graph calls. No DB. No sends. Never returns/logs secrets or full Meta IDs.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

from services.admin_whatsapp_meta_status_v1 import (
    PLACEHOLDER_TOKENS,
    read_whatsapp_meta_env,
)
from services.deploy_build_info_v1 import resolve_deploy_git_sha
from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
from services.recovery_process_role_v1 import resolve_process_role
from services.whatsapp_provider import (
    PROVIDER_META,
    _meta_template_defaults_from_env,
    resolve_whatsapp_provider,
)

EXPECTED_META_RECOVERY_TEMPLATE = TEMPLATE_NAME  # cartflow_cart_reminder_ar_v2

log = logging.getLogger("cartflow")

_SAFE_ERROR_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def _env_configured(raw: str) -> bool:
    v = (raw or "").strip()
    if not v:
        return False
    if v.lower() in PLACEHOLDER_TOKENS:
        return False
    return True


def _bool_word(value: bool) -> str:
    return "true" if value else "false"


def _safe_error_code(exc: BaseException) -> str:
    name = type(exc).__name__ or "error"
    return _SAFE_ERROR_RE.sub("_", name)[:64] or "error"


def _emit_line(line: str) -> None:
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def build_scheduler_meta_preflight() -> dict[str, Any]:
    """
    Build a safe preflight payload for the current process.

    Uses the same provider/template/credential resolvers as Meta recovery send.
    """
    role = resolve_process_role()
    provider = resolve_whatsapp_provider()
    template_env, _lang = _meta_template_defaults_from_env()
    template_name = (template_env or "").strip() or None
    env = read_whatsapp_meta_env()

    access_ok = _env_configured(env.get("access_token") or "")
    phone_ok = _env_configured(env.get("phone_number_id") or "")
    waba_ok = _env_configured(env.get("waba_id") or "")

    ready = bool(
        role == "scheduler"
        and provider == PROVIDER_META
        and template_name == EXPECTED_META_RECOVERY_TEMPLATE
        and access_ok
        and phone_ok
        and waba_ok
    )

    return {
        "role": role,
        "git_sha": resolve_deploy_git_sha(short=False),
        "whatsapp_provider": provider,
        "meta_template_name": template_name,
        "access_token_configured": access_ok,
        "phone_number_id_configured": phone_ok,
        "waba_id_configured": waba_ok,
        "template_expected_name": EXPECTED_META_RECOVERY_TEMPLATE,
        "ready_for_meta_recovery": ready,
    }


def format_scheduler_meta_runtime_log_line(
    payload: Optional[dict[str, Any]] = None,
) -> str:
    """
    One sanitized Railway-searchable startup line.

    Never includes access tokens, Authorization headers, or full Meta IDs.
    """
    data = payload if isinstance(payload, dict) else build_scheduler_meta_preflight()
    template_name = data.get("meta_template_name")
    template_s = template_name if isinstance(template_name, str) and template_name else ""
    return (
        "[SCHEDULER META RUNTIME] "
        f"role={data.get('role')} "
        f"whatsapp_provider={data.get('whatsapp_provider')} "
        f"meta_template_name={template_s} "
        f"access_token_configured={_bool_word(bool(data.get('access_token_configured')))} "
        f"phone_number_id_configured={_bool_word(bool(data.get('phone_number_id_configured')))} "
        f"waba_id_configured={_bool_word(bool(data.get('waba_id_configured')))} "
        f"ready_for_meta_recovery={_bool_word(bool(data.get('ready_for_meta_recovery')))}"
    )


def format_scheduler_meta_runtime_error_line(error_code: str) -> str:
    code = _SAFE_ERROR_RE.sub("_", (error_code or "error").strip())[:64] or "error"
    return f"[SCHEDULER META RUNTIME ERROR] error={code}"


def format_scheduler_meta_runtime_log_lines(
    payload: Optional[dict[str, Any]] = None,
) -> list[str]:
    """Backward-compatible wrapper — returns a single-element list. """
    return [format_scheduler_meta_runtime_log_line(payload)]


def log_scheduler_meta_runtime(*, role: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Emit one ``[SCHEDULER META RUNTIME]`` line on Scheduler processes only.

    On resolution failure emits ``[SCHEDULER META RUNTIME ERROR]`` (no secrets)
    and does not raise. API/unset roles are a no-op.
    """
    resolved_role = (role or resolve_process_role() or "").strip().lower()
    if resolved_role != "scheduler":
        return None

    try:
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
        _emit_line(format_scheduler_meta_runtime_log_line(payload))
        return payload
    except Exception as exc:  # noqa: BLE001 — must not crash Scheduler startup
        _emit_line(format_scheduler_meta_runtime_error_line(_safe_error_code(exc)))
        return None


__all__ = [
    "EXPECTED_META_RECOVERY_TEMPLATE",
    "build_scheduler_meta_preflight",
    "format_scheduler_meta_runtime_error_line",
    "format_scheduler_meta_runtime_log_line",
    "format_scheduler_meta_runtime_log_lines",
    "log_scheduler_meta_runtime",
]
