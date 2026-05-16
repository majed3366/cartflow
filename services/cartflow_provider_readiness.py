# -*- coding: utf-8 -*-
"""
Read-only WhatsApp provider readiness and diagnostics (Twilio-first; Meta placeholder).

Does not send messages, retry, or alter recovery/send code paths.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Any, Optional

log = logging.getLogger("cartflow")

PREFIX_PROVIDER = "[CARTFLOW PROVIDER]"

FAILURE_PROVIDER_NOT_CONFIGURED = "provider_not_configured"
FAILURE_SANDBOX_RECIPIENT = "sandbox_recipient_not_joined"
FAILURE_TEMPLATE_NOT_APPROVED = "template_not_approved"
FAILURE_PROVIDER_AUTH = "provider_auth_failed"
FAILURE_RATE_LIMITED = "provider_rate_limited"
FAILURE_UNAVAILABLE = "provider_unavailable"
FAILURE_REJECTED = "provider_rejected_message"
FAILURE_UNKNOWN = "unknown_provider_failure"
FAILURE_INTERNAL_SKIP = "internal_recovery_skip"

_MERCH: dict[str, tuple[str, str]] = {
    FAILURE_PROVIDER_NOT_CONFIGURED: (
        "واتساب غير مفعّل",
        "رسائل الاسترجاع لن تُرسل حتى يتم إعداد واتساب.",
    ),
    FAILURE_SANDBOX_RECIPIENT: (
        "رقم الاختبار غير مفعّل في Sandbox",
        "أضف الرقم إلى Twilio Sandbox قبل الاختبار.",
    ),
    FAILURE_TEMPLATE_NOT_APPROVED: (
        "قالب واتساب غير معتمد",
        "راجع حالة قالب واتساب قبل الإرسال.",
    ),
    FAILURE_PROVIDER_AUTH: (
        "تعذر الاتصال بمزود واتساب",
        "راجع إعدادات الربط أو مفاتيح الوصول.",
    ),
    FAILURE_RATE_LIMITED: (
        "الحدّ المسموح من المزود",
        "أعد المحاولة لاحقاً أو راجع حدود الإرسال لدى مزود واتساب.",
    ),
    FAILURE_UNAVAILABLE: (
        "مزود واتساب غير متاح مؤقتاً",
        "أعد المحاولة لاحقاً إذا استمرّت المشكلة.",
    ),
    FAILURE_REJECTED: (
        "المزود لم يقبل الرسالة",
        "راجع الرقم أو صيغة المحتوى وفق سياسات واتساب.",
    ),
    FAILURE_INTERNAL_SKIP: (
        "تم تخطي الإرسال داخلياً",
        "قد يكون الإرسال متوقفاً وفق شروط الاسترجاع (ليس بالضرورة خطأ مزود).",
    ),
    FAILURE_UNKNOWN: (
        "تعذر إرسال واتساب",
        "راجع إعدادات واتساب أو حالة المزود.",
    ),
}

_LOG_LOCK = threading.Lock()
_last_readiness_emit_at: dict[str, float] = {}
_EMIT_COOLDOWN_S = 120.0


def readiness_diag_log_enabled() -> bool:
    try:
        from services.cartflow_observability_mode import (
            observability_provider_readiness_diag_enabled,
        )

        return observability_provider_readiness_diag_enabled()
    except Exception:  # noqa: BLE001
        return False


def structured_health_style_enabled() -> bool:
    try:
        from services.cartflow_observability_mode import (
            observability_structured_health_dashboard_log_enabled,
        )

        return observability_structured_health_dashboard_log_enabled()
    except Exception:  # noqa: BLE001
        return False


def _emit_provider_line(
    *,
    provider: str,
    ready: bool,
    failure_type: str = "",
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> None:
    if not (readiness_diag_log_enabled() or structured_health_style_enabled()):
        return
    fp = f"{provider}|{int(bool(ready))}|{(failure_type or '').strip()[:40]}"
    now = time.monotonic()
    with _LOG_LOCK:
        last = _last_readiness_emit_at.get(fp)
        if last is not None and (now - last) < _EMIT_COOLDOWN_S:
            return
        _last_readiness_emit_at[fp] = now
        if len(_last_readiness_emit_at) > 200:
            _last_readiness_emit_at.clear()
    parts = [
        PREFIX_PROVIDER,
        "msg=readiness",
        f"provider={_safe(provider)}",
        f"ready={str(bool(ready)).lower()}",
        f"failure_type={_safe(failure_type or '-')}",
        f"store_slug={_safe(store_slug or '-')}",
        f"session_id={_safe((session_id or '')[:64])}",
        f"cart_id={_safe((cart_id or '')[:64])}",
    ]
    line = " ".join(parts)
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def _safe(s: str) -> str:
    return (s or "").strip().replace("\n", " ")[:200] or "-"


def _twilio_missing_env() -> list[str]:
    missing: list[str] = []
    if not (os.getenv("TWILIO_ACCOUNT_SID") or "").strip():
        missing.append("TWILIO_ACCOUNT_SID")
    if not (os.getenv("TWILIO_AUTH_TOKEN") or "").strip():
        missing.append("TWILIO_AUTH_TOKEN")
    if not (os.getenv("TWILIO_WHATSAPP_FROM") or "").strip():
        missing.append("TWILIO_WHATSAPP_FROM")
    return missing


def get_twilio_readiness() -> dict[str, Any]:
    missing = _twilio_missing_env()
    configured = len(missing) == 0
    try:
        from services.whatsapp_send import (  # noqa: PLC0415
            is_production_mode,
            recovery_uses_real_whatsapp,
        )

        prod = bool(is_production_mode())
        real_wa = bool(recovery_uses_real_whatsapp())
    except Exception:
        prod = False
        real_wa = False
    mode = "production" if prod else "sandbox"
    ready_env = bool(configured)
    ready = bool(real_wa and configured)
    fc = FAILURE_PROVIDER_NOT_CONFIGURED if not configured else "ok"
    if fc == "ok":
        label_ar = "واتساب مهيأ للإرسال"
        action_ar = "يمكن إرسال رسائل الاسترجاع عند توفر باقي الشروط."
    else:
        label_ar, action_ar = merchant_copy_for_failure_class(fc)
    return {
        "provider": "twilio",
        "configured": configured,
        "ready": ready,
        "ready_env_credentials": ready_env,
        "missing_env": missing,
        "mode": mode,
        "production_mode": prod,
        "recovery_uses_real_whatsapp": real_wa,
        "failure_class": fc,
        "last_failure_type": fc if fc != "ok" else None,
        "merchant_label_ar": label_ar,
        "merchant_action_ar": action_ar,
    }


def get_meta_readiness() -> dict[str, Any]:
    """Placeholder: no Meta Graph send path in this repo yet."""
    has_app = bool((os.getenv("META_WHATSAPP_TOKEN") or "").strip()) or bool(
        (os.getenv("WHATSAPP_CLOUD_API_TOKEN") or "").strip()
    )
    configured = has_app
    if configured:
        fc = "ok"
        label_ar = "مهيأ جزئياً (Meta)"
        action_ar = "مسار الإرسال عبر Meta غير مفعّل في هذا الإصدار؛ راجع Twilio."
    else:
        fc = FAILURE_UNKNOWN
        label_ar, action_ar = merchant_copy_for_failure_class(FAILURE_UNKNOWN)
    return {
        "provider": "meta",
        "configured": configured,
        "ready": False,
        "missing_env": []
        if configured
        else ["META_WHATSAPP_TOKEN_or_WHATSAPP_CLOUD_API_TOKEN"],
        "mode": "unknown",
        "failure_class": fc,
        "last_failure_type": None,
        "merchant_label_ar": label_ar,
        "merchant_action_ar": action_ar,
        "note": "meta_path_not_active",
    }


def get_whatsapp_provider_readiness() -> dict[str, Any]:
    tw = get_twilio_readiness()
    meta = get_meta_readiness()
    if tw.get("configured"):
        primary = "twilio"
    elif meta.get("configured"):
        primary = "meta"
    else:
        primary = "unknown"

    if primary == "twilio":
        fc_top = str(tw.get("failure_class") or "ok")
        mer_l = str(tw.get("merchant_label_ar") or "")
        mer_a = str(tw.get("merchant_action_ar") or "")
        configured = bool(tw.get("configured"))
        ready = bool(tw.get("ready"))
        missing = list(tw.get("missing_env") or [])
        mode = str(tw.get("mode") or "unknown")
        last_ft = tw.get("last_failure_type")
    elif primary == "meta":
        fc_top = str(meta.get("failure_class") or "ok")
        mer_l = str(meta.get("merchant_label_ar") or "")
        mer_a = str(meta.get("merchant_action_ar") or "")
        configured = bool(meta.get("configured"))
        ready = bool(meta.get("ready"))
        missing = list(meta.get("missing_env") or [])
        mode = str(meta.get("mode") or "unknown")
        last_ft = meta.get("last_failure_type")
    else:
        fc_top = FAILURE_PROVIDER_NOT_CONFIGURED
        mer_l, mer_a = merchant_copy_for_failure_class(FAILURE_PROVIDER_NOT_CONFIGURED)
        configured = False
        ready = False
        missing = list(tw.get("missing_env") or [])
        mode = "unknown"
        last_ft = fc_top

    return {
        "provider": primary,
        "configured": configured,
        "ready": ready,
        "missing_env": missing,
        "mode": mode,
        "last_failure_type": last_ft,
        "failure_class": fc_top,
        "merchant_label_ar": mer_l,
        "merchant_action_ar": mer_a,
        "twilio": tw,
        "meta": meta,
    }


def log_provider_readiness_snapshot(
    readiness: dict[str, Any],
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> None:
    """Throttled structured line; enable via CARTFLOW_PROVIDER_READINESS_LOG or HEALTH log flag."""
    if not isinstance(readiness, dict):
        return
    _emit_provider_line(
        provider=str(readiness.get("provider") or "unknown"),
        ready=bool(readiness.get("ready")),
        failure_type=str(readiness.get("failure_class") or ""),
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )


def merchant_copy_for_failure_class(failure_class: Optional[str]) -> tuple[str, str]:
    fc = (failure_class or "").strip() or FAILURE_UNKNOWN
    pair = _MERCH.get(fc)
    if pair:
        return pair
    return _MERCH[FAILURE_UNKNOWN]


def classify_provider_failure(
    error: Any = None,
    status: Any = None,
) -> str:
    """
    Map Twilio/Meta-style signals to a stable failure class (no PII).
    Accepts exception message string or status code/string.
    """
    chunks: list[str] = []
    if error is not None:
        chunks.append(str(error).lower())
    if status is not None:
        chunks.append(str(status).lower())
    blob = " ".join(chunks)

    if not blob.strip():
        return FAILURE_UNKNOWN

    if "twilio_not_configured" in blob or (
        "not configured" in blob and "twilio" in blob
    ):
        return FAILURE_PROVIDER_NOT_CONFIGURED
    if "twilio_invalid_from" in blob:
        return FAILURE_PROVIDER_AUTH

    code_m = re.search(r"\b(?:error|code|status)[^\d]{0,6}(\d{5})\b", blob)
    code = code_m.group(1) if code_m else ""
    if code in ("20404", "20003", "401", "403"):
        return FAILURE_PROVIDER_AUTH
    if code in ("20429",):
        return FAILURE_RATE_LIMITED
    if code in ("21610", "21211", "60200"):
        return FAILURE_REJECTED
    if code in ("63016", "63017", "63018") or (
        "sandbox" in blob
        and (
            "join" in blob
            or "not a participant" in blob
            or "not verified" in blob
        )
    ):
        return FAILURE_SANDBOX_RECIPIENT
    if "template" in blob or "not approved" in blob or code in ("63013", "63014"):
        return FAILURE_TEMPLATE_NOT_APPROVED
    if (
        "503" in blob
        or "502" in blob
        or "500" in blob
        or "timeout" in blob
        or "unavailable" in blob
        or "connection" in blob
    ):
        return FAILURE_UNAVAILABLE
    if (
        "authenticate" in blob
        or "authentication" in blob
        or (
            "invalid" in blob
            and (
                "credential" in blob
                or "token" in blob
                or "sid" in blob
            )
        )
    ):
        return FAILURE_PROVIDER_AUTH
    if "rate" in blob and "limit" in blob:
        return FAILURE_RATE_LIMITED
    if "rejected" in blob or "undeliverable" in blob:
        return FAILURE_REJECTED

    return FAILURE_UNKNOWN


def enrich_whatsapp_failed_blocker(
    bundle: Optional[dict[str, Any]],
    *,
    readiness: Optional[dict[str, Any]] = None,
    persisted_error_hint: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Add provider-readiness hints alongside the existing whatsapp_failed blocker.
    Does not replace core merchant labels (preserves recovery_blocker_display copy).
    """
    if not isinstance(bundle, dict):
        return bundle
    if str(bundle.get("key") or "") != "whatsapp_failed":
        return bundle
    r = readiness if isinstance(readiness, dict) else get_whatsapp_provider_readiness()
    out = dict(bundle)
    if not r.get("configured"):
        fc = FAILURE_PROVIDER_NOT_CONFIGURED
        hint_ar, action_ar = merchant_copy_for_failure_class(fc)
        out["provider_issue_hint_ar"] = f"{hint_ar} — {action_ar}"
        return out
    if persisted_error_hint:
        fc = classify_provider_failure(persisted_error_hint, None)
        hint_ar, action_ar = merchant_copy_for_failure_class(fc)
        out["provider_issue_hint_ar"] = f"{hint_ar} — {action_ar}"
        return out
    return bundle


def reset_provider_readiness_log_throttle_for_tests() -> None:
    with _LOG_LOCK:
        _last_readiness_emit_at.clear()
