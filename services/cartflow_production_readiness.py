# -*- coding: utf-8 -*-
"""
Read-only production readiness report for CartFlow operators.

Does not alter recovery, WhatsApp sends, VIP flows, widget/merchant UX, or queues.
Output contains only booleans and missing env *names* — never secret values.
"""
from __future__ import annotations

import json
import os
from typing import Any

# Keep aligned with main._DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT
_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT: frozenset[str] = frozenset(
    {
        "/dev/whatsapp-decision-test",
        "/dev/cartflow-delay-test",
        "/dev/vip-flow-verify",
        "/dev/create-vip-test-cart",
    }
)

# Keep aligned with routes.ops._INIT_DB_KEY
_OPS_INIT_DB_KEY = "dev-init"

_DEFAULT_SECRET_FALLBACK = "dev-only-change-in-production"

# Presence-only env reporting (no values).
_CRITICAL_ENV_KEYS: tuple[str, ...] = (
    "SECRET_KEY",
    "DATABASE_URL",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_WHATSAPP_FROM",
    "ENV",
    "PRODUCTION_MODE",
)

_OPTIONAL_KNOWN_ENV_KEYS: tuple[str, ...] = (
    "CARTFLOW_PUBLIC_BASE_URL",
    "PUBLIC_BASE_URL",
    "OAUTH_REDIRECT_URI",
    "ZID_CLIENT_ID",
    "ZID_CLIENT_SECRET",
    "ZID_WEBHOOK_SECRET",
)


def _strip_env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def _env_present(name: str) -> bool:
    return bool(_strip_env(name))


def is_development_mode() -> bool:
    """Same rule as main._is_development_mode (ENV=development only)."""
    return _strip_env("ENV").lower() == "development"


def _secret_key_is_default() -> bool:
    v = _strip_env("SECRET_KEY")
    if not v:
        return True
    return v == _DEFAULT_SECRET_FALLBACK


def _database_url_missing_using_fallback() -> bool:
    return not _env_present("DATABASE_URL")


def _unsafe_debug_paths() -> list[dict[str, Any]]:
    """
    HTTP paths that are not under /dev and therefore not covered by no_dev_in_production.
    Values are documentation-only; adjust if routes change.
    """
    return [
        {
            "path": "/debug/db",
            "description": "returns database_url_prefix (first 20 chars) and sqlite flag",
            "authenticated": False,
        }
    ]


def _collect_env_report() -> dict[str, Any]:
    required_status = {k: _env_present(k) for k in _CRITICAL_ENV_KEYS}
    optional_status = {k: _env_present(k) for k in _OPTIONAL_KNOWN_ENV_KEYS}
    # ENV empty means non-development runtime (see main no_dev_in_production); not an error.
    missing_required = [
        k for k, ok in required_status.items() if not ok and k not in ("ENV", "PRODUCTION_MODE")
    ]
    return {
        "required": {k: {"configured": bool(v)} for k, v in required_status.items()},
        "optional_public_urls_and_oauth": {
            k: {"configured": bool(v)} for k, v in optional_status.items()
        },
        "missing_required_keys": missing_required,
        "note_env_and_production_mode": (
            "ENV and PRODUCTION_MODE may be unset; empty ENV is treated as non-development."
        ),
    }


def _operational_signals() -> dict[str, Any]:
    """Compose existing read-only diagnostics without changing product behavior."""
    flat: dict[str, bool] = {}
    try:
        from services.cartflow_observability_runtime import (  # noqa: PLC0415
            runtime_health_snapshot_readonly,
        )

        raw = runtime_health_snapshot_readonly()
        flat = {str(k): bool(v) for k, v in raw.items()}
    except Exception:
        flat = {}

    provider: dict[str, Any] = {}
    try:
        from services.cartflow_provider_readiness import (  # noqa: PLC0415
            get_whatsapp_provider_readiness,
        )

        provider = get_whatsapp_provider_readiness()
    except Exception:
        provider = {}

    dup: dict[str, Any] = {}
    try:
        from services.cartflow_duplicate_guard import (  # noqa: PLC0415
            get_duplicate_guard_diagnostics_readonly,
        )

        dup = get_duplicate_guard_diagnostics_readonly()
    except Exception:
        dup = {}

    lifecycle: dict[str, Any] = {}
    try:
        from services.cartflow_lifecycle_guard import (  # noqa: PLC0415
            get_lifecycle_diagnostics_readonly,
        )

        lifecycle = get_lifecycle_diagnostics_readonly()
    except Exception:
        lifecycle = {}

    session: dict[str, Any] = {}
    try:
        from services.cartflow_session_consistency import (  # noqa: PLC0415
            get_session_consistency_diagnostics_readonly,
        )

        session = get_session_consistency_diagnostics_readonly()
    except Exception:
        session = {}

    onboarding: dict[str, Any] = {}
    try:
        from services.cartflow_onboarding_readiness import (  # noqa: PLC0415
            build_onboarding_health_section,
        )

        onboarding = build_onboarding_health_section()
    except Exception:
        onboarding = {}

    admin_summary: dict[str, Any] = {
        "available": False,
        "platform_admin_category": None,
        "error_class": None,
    }
    try:
        from services.cartflow_admin_operational_summary import (  # noqa: PLC0415
            build_admin_operational_summary_readonly,
        )

        summar = build_admin_operational_summary_readonly()
        admin_summary["available"] = isinstance(summar, dict) and bool(
            summar.get("platform_admin_category")
        )
        admin_summary["platform_admin_category"] = (
            summar.get("platform_admin_category") if isinstance(summar, dict) else None
        )
    except Exception as exc:
        admin_summary["error_class"] = type(exc).__name__

    prov_ready = bool(provider.get("ready")) if isinstance(provider, dict) else False
    prov_configured = bool(provider.get("configured")) if isinstance(provider, dict) else False
    failure_class = (
        str(provider.get("failure_class") or "") if isinstance(provider, dict) else ""
    )

    return {
        "runtime_health_flags": flat,
        "provider_readiness": {
            "configured": prov_configured,
            "ready": prov_ready,
            "failure_class": failure_class or None,
            "production_mode_expects_real_send": False,
        },
        "onboarding_health_section_keys": sorted(onboarding.keys())
        if isinstance(onboarding, dict)
        else [],
        "onboarding_ready_flag": bool(onboarding.get("onboarding_ready"))
        if isinstance(onboarding, dict)
        else None,
        "duplicate_guard": {
            "duplicate_prevention_runtime_ok": bool(
                dup.get("duplicate_prevention_runtime_ok", True)
            )
            if isinstance(dup, dict)
            else None,
            "duplicate_send_blocked_recently": bool(dup.get("duplicate_send_blocked_recently"))
            if isinstance(dup, dict)
            else None,
        },
        "lifecycle": {
            "lifecycle_runtime_ok": bool(lifecycle.get("lifecycle_runtime_ok", True))
            if isinstance(lifecycle, dict)
            else None,
        },
        "session_consistency": {
            "session_runtime_consistent": bool(
                session.get("session_runtime_consistent", True)
            )
            if isinstance(session, dict)
            else None,
        },
        "admin_operational_summary": admin_summary,
        "identity_safeguards": {
            "identity_resolution_ok": flat.get("identity_resolution_ok"),
        },
    }


def build_cartflow_production_readiness_report() -> dict[str, Any]:
    from services.whatsapp_send import (  # noqa: PLC0415
        is_production_mode,
        recovery_uses_real_whatsapp,
    )

    prod_mode = is_production_mode()
    dev_mode = is_development_mode()
    env_report = _collect_env_report()

    op = _operational_signals()
    if isinstance(op.get("provider_readiness"), dict):
        op["provider_readiness"]["production_mode_expects_real_send"] = bool(
            recovery_uses_real_whatsapp()
        )

    blocking: list[str] = []
    warnings: list[str] = []

    if prod_mode and _secret_key_is_default():
        blocking.append(
            "SECRET_KEY missing or still set to dev default — set a strong secret before production traffic."
        )
    elif not prod_mode and _secret_key_is_default():
        warnings.append(
            "SECRET_KEY is missing or using dev default — acceptable for local dev only."
        )

    if prod_mode and _database_url_missing_using_fallback():
        blocking.append(
            "DATABASE_URL is not set; application may use ephemeral SQLite — unsafe for production."
        )
    elif _database_url_missing_using_fallback():
        warnings.append(
            "DATABASE_URL is not set; using bundled SQLite fallback — data may not persist as expected."
        )

    if prod_mode:
        twilio_missing_names = [
            k
            for k in (
                "TWILIO_ACCOUNT_SID",
                "TWILIO_AUTH_TOKEN",
                "TWILIO_WHATSAPP_FROM",
            )
            if not _env_present(k)
        ]
        if twilio_missing_names:
            warnings.append(
                "Twilio env incomplete (missing: "
                + ", ".join(sorted(set(twilio_missing_names)))
                + ") — real WhatsApp will not send until configured."
            )
        pr = op.get("provider_readiness") if isinstance(op.get("provider_readiness"), dict) else {}
        if bool(recovery_uses_real_whatsapp()) and not bool(pr.get("ready")):
            blocking.append(
                "PRODUCTION_MODE expects real WhatsApp but provider readiness is not OK — fix Twilio/sandbox/template before launch."
            )
        elif bool(recovery_uses_real_whatsapp()) and bool(pr.get("ready")):
            pass
        elif prod_mode and not bool(pr.get("configured")):
            warnings.append(
                "PRODUCTION_MODE is on but Twilio env is incomplete — sends stay mocked until credentials are set."
            )

    unsafe_debug = _unsafe_debug_paths()
    safety_gates = {
        "development_mode": dev_mode,
        "production_mode_flag": prod_mode,
        "dev_paths_blocked_when_not_development": not dev_mode,
        "dev_paths_allowlisted_when_not_development": sorted(_DEV_ROUTES_ALLOWED_WHEN_NOT_DEVELOPMENT),
        "note_allowlisted_routes_have_no_session_auth": (
            "Several /dev paths remain reachable when ENV≠development; treat as manual tooling only."
            if not dev_mode
            else None
        ),
        "debug_endpoints_outside_dev_prefix": unsafe_debug,
        "admin_init_db_uses_shared_key": {
            "requires_query_key_named": "key",
            "documented_default_key_literal": _OPS_INIT_DB_KEY,
            "warning": (
                "admin/init-db uses a fixed default key in source — rotate or protect this route via edge auth."
            ),
        },
        "secrets_in_readiness_output": False,
        "readiness_never_includes_secret_values": True,
    }

    if prod_mode:
        blocking.append(
            "Public debug route /debug/db is reachable without /dev gating — restrict or remove before launch."
        )
        warnings.append(
            "GET /admin/init-db accepts a built-in shared key — protect at the network layer or change the key in source."
        )

    dup_ok = op.get("duplicate_guard", {})
    if isinstance(dup_ok, dict) and dup_ok.get("duplicate_prevention_runtime_ok") is False:
        warnings.append("Duplicate guard reports runtime not OK — review duplicate diagnostics.")
    lc = op.get("lifecycle", {})
    if isinstance(lc, dict) and lc.get("lifecycle_runtime_ok") is False:
        warnings.append("Lifecycle consistency reports issues — review lifecycle diagnostics.")
    sess = op.get("session_consistency", {})
    if isinstance(sess, dict) and sess.get("session_runtime_consistent") is False:
        warnings.append("Session consistency check failed — review session diagnostics.")

    trace = _strip_env("WA_RECOVERY_SEND_TRACE").lower()
    if prod_mode and trace in ("1", "true", "yes", "on"):
        warnings.append(
            "WA_RECOVERY_SEND_TRACE is enabled — ensure logs never include message bodies or tokens in production."
        )

    if prod_mode and not bool(
        op.get("admin_operational_summary", {}).get("available")
    ):
        warnings.append(
            "Admin operational summary could not be built — DB unavailable or unexpected error."
        )

    blocking = list(dict.fromkeys(blocking))
    warnings = list(dict.fromkeys(warnings))

    production_ready = len(blocking) == 0

    safe_to_demo = bool(dev_mode or not prod_mode)
    if prod_mode:
        safe_to_demo = production_ready and bool(
            op.get("provider_readiness", {}).get("ready")
            if isinstance(op.get("provider_readiness"), dict)
            else False
        )

    safe_to_onboard_merchant = bool(production_ready)
    if prod_mode:
        ob_ok = op.get("onboarding_ready_flag")
        pr_ready = False
        pr = op.get("provider_readiness")
        if isinstance(pr, dict):
            pr_ready = bool(pr.get("ready"))
        safe_to_onboard_merchant = (
            production_ready
            and (ob_ok is not False)
            and (pr_ready or not bool(recovery_uses_real_whatsapp()))
        )

    rec_ar: list[str] = []
    if blocking:
        rec_ar.append("معالجة عناصر القائمة «blocking_issues» أولاً قبل استقبال أي متاجر إنتاج.")
    elif warnings:
        rec_ar.append("راجع التحذيرات ثم ثبّت المتغيرات الحرجة (SECRET_KEY و DATABASE_URL ومزود واتساب).")
    else:
        rec_ar.append("الوضع جيد نسبياً — راقب اللوحة التشغيلية والسجلات بعد الإطلاق.")

    payload: dict[str, Any] = {
        "generated_from": "cartflow_production_readiness_v1",
        "production_ready": production_ready,
        "blocking_issues": blocking,
        "warnings": warnings,
        "safe_to_demo": safe_to_demo,
        "safe_to_onboard_merchant": safe_to_onboard_merchant,
        "recommended_next_action_ar": rec_ar,
        "environment": env_report,
        "safety_gates": safety_gates,
        "operational": op,
    }

    # Self-check: never emit obvious secret material from this payload path.
    ser = json.dumps(payload, default=str)
    for token in (
        _strip_env("TWILIO_AUTH_TOKEN"),
        _strip_env("SECRET_KEY"),
        _strip_env("ZID_CLIENT_SECRET"),
    ):
        if len(token) >= 8 and token in ser:
            payload["safety_gates"]["secrets_in_readiness_output"] = True
            payload["production_ready"] = False
            payload["blocking_issues"].append(
                "Readiness self-check suspected a secret in serialized output — report this as a bug."
            )

    return payload


__all__ = [
    "build_cartflow_production_readiness_report",
    "is_development_mode",
]
