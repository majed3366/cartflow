# -*- coding: utf-8 -*-
"""
Governed WhatsApp provider boundary for recovery outbound sends.

Selection: WHATSAPP_PROVIDER=twilio|meta (default: twilio).
No automatic cross-provider fallback.
Never logs access tokens or full phone numbers.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Mapping, Optional

from services.whatsapp_providers.contracts import (
    MODE_SESSION_TEXT,
    MODE_TEMPLATE,
    PROVIDER_META,
    PROVIDER_TWILIO,
    WhatsAppProviderRequest,
    empty_provider_result,
)
from services.whatsapp_providers.meta_cloud import send_via_meta
from services.whatsapp_providers.twilio_provider import send_via_twilio

logger = logging.getLogger(__name__)

_VALID_PROVIDERS = frozenset({PROVIDER_TWILIO, PROVIDER_META})

# First controlled-test Meta recovery template (Contract V1 — BODY + buttons).
META_RECOVERY_TEMPLATE_CARTFLOW_V1 = "cartflow_cart_reminder_ar_v1"
META_RECOVERY_TEMPLATE_CARTFLOW_V2 = "cartflow_cart_reminder_ar_v2"
META_RECOVERY_TEMPLATE_V1_BODY_PARAM_COUNT = 1
META_RECOVERY_TEMPLATE_V2_BODY_PARAM_COUNT = 1
# Templates that use store_display_name body {{1}} (+ v2 URL button token).
_META_RECOVERY_STORE_NAME_TEMPLATES = frozenset(
    {
        META_RECOVERY_TEMPLATE_CARTFLOW_V1,
        META_RECOVERY_TEMPLATE_CARTFLOW_V2,
    }
)
_META_RECOVERY_BUTTON_TEMPLATES = frozenset({META_RECOVERY_TEMPLATE_CARTFLOW_V2})
STORE_DISPLAY_NAME_MAX_LEN = 60
CHECKOUT_URL_MAX_LEN = 2000


def normalize_checkout_url(raw: Any) -> Optional[str]:
    """Accept http(s) checkout/restore URLs only."""
    if raw is None:
        return None
    if not isinstance(raw, str):
        return None
    u = raw.strip()
    if not u or len(u) > CHECKOUT_URL_MAX_LEN:
        return None
    lowered = u.lower()
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        return None
    if any(ch in u for ch in ("\n", "\r", "\t", " ")):
        return None
    return u


def resolve_store_name_from_context(context: Mapping[str, Any]) -> Optional[str]:
    """Runtime store_name (alias: store_display_name)."""
    for key in ("store_name", "store_display_name"):
        n = normalize_store_display_name(context.get(key))
        if n:
            return n
    return resolve_store_display_name_from_context(context)


def resolve_checkout_url_from_context(context: Mapping[str, Any]) -> Optional[str]:
    for key in ("checkout_url", "cart_url", "restore_url"):
        u = normalize_checkout_url(context.get(key))
        if u:
            return u
    return None


def resolve_whatsapp_provider(explicit: Optional[str] = None) -> str:
    """
    Resolve active WhatsApp provider.

    Default / missing / unknown → twilio (preserves current production behavior).
    """
    raw = (explicit if explicit is not None else os.getenv("WHATSAPP_PROVIDER") or "").strip().lower()
    if not raw:
        return PROVIDER_TWILIO
    if raw in _VALID_PROVIDERS:
        return raw
    logger.warning(
        "[WA PROVIDER] unknown WHATSAPP_PROVIDER=%s — falling back to twilio",
        raw[:32],
    )
    return PROVIDER_TWILIO


def _log_provider_diagnostic(
    *,
    provider: str,
    accepted: bool,
    recovery_key: Optional[str],
    store_slug: Optional[str],
    external_message_id: Optional[str],
    error_code: Optional[str],
    error_subcode: Optional[str],
    message_mode: Optional[str],
) -> None:
    rk = (recovery_key or "-")[:120]
    slug = (store_slug or "-")[:64]
    mid = (external_message_id or "-")[:80]
    code = (error_code or "-")[:64]
    sub = (error_subcode or "-")[:64]
    mode = (message_mode or "-")[:32]
    outcome = "accepted" if accepted else "failed"
    line = (
        f"[WA PROVIDER SEND] provider={provider} outcome={outcome} "
        f"recovery_key={rk} store_slug={slug} message_mode={mode} "
        f"external_message_id={mid} error_code={code} error_subcode={sub}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    logger.info("%s", line)


def _meta_template_defaults_from_env() -> tuple[Optional[str], str]:
    name = (os.getenv("WHATSAPP_META_RECOVERY_TEMPLATE_NAME") or "").strip() or None
    lang = (os.getenv("WHATSAPP_META_RECOVERY_TEMPLATE_LANGUAGE") or "").strip() or "ar"
    return name, lang


def normalize_store_display_name(raw: Any) -> Optional[str]:
    """
    Normalize merchant store label for Meta body {{1}}.

    Rejects empty, newlines, URL-like values, and overlong strings.
    Preserves Arabic characters.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raw = str(raw)
    text = raw.strip()
    if not text:
        return None
    if "\n" in text or "\r" in text:
        return None
    lowered = text.lower()
    if "http://" in lowered or "https://" in lowered or "www." in lowered:
        return None
    if len(text) > STORE_DISPLAY_NAME_MAX_LEN:
        return None
    return text


def _label_from_store_slug(store_slug: Optional[str]) -> Optional[str]:
    """Safe fallback label derived from store_slug (not a demo placeholder)."""
    slug = (store_slug or "").strip()
    if not slug:
        return None
    # Reject opaque / non-merchant runtime slugs
    if slug.lower() in ("demo", "default", "test", "unknown", "-"):
        return None
    # Prefer human-readable form; keep Unicode (Arabic) slugs intact
    label = slug.replace("_", " ").replace("-", " ").strip()
    return normalize_store_display_name(label)


def resolve_store_display_name_from_context(
    context: Mapping[str, Any],
) -> Optional[str]:
    """
    Provider-neutral store display name for template {{1}}.

    Canonical merchant label: ``merchant_store_display_name`` from Store.widget_display_name
    (see services/merchant_onboarding_store.py). Generic «متجرك» alone is not treated as
    a truthful store-specific value — slug fallback is preferred, then fail-safe.
    """
    # B. Explicit provider-neutral context field
    from_ctx = normalize_store_display_name(context.get("store_display_name"))
    if from_ctx:
        return from_ctx

    slug = str(context.get("store_slug") or "").strip()[:255] or None
    store = None
    if slug:
        try:
            from services.whatsapp_production_reality_v2 import (
                resolve_store_for_template_enforcement,
            )

            store = resolve_store_for_template_enforcement(slug)
        except Exception:  # noqa: BLE001
            store = None

    if store is not None:
        # Prefer real widget_display_name (canonical merchant store label)
        wn = normalize_store_display_name(getattr(store, "widget_display_name", None))
        if wn:
            return wn
        try:
            from services.merchant_onboarding_store import merchant_store_display_name

            resolved = (merchant_store_display_name(store, merchant_user=None) or "").strip()
            # «متجرك» is the function's generic placeholder — not store-specific truth
            if resolved and resolved != "متجرك":
                wn2 = normalize_store_display_name(resolved)
                if wn2:
                    return wn2
        except Exception:  # noqa: BLE001
            pass

    # C. Safe fallback from store_slug
    return _label_from_store_slug(slug)


def _normalize_explicit_template_parameters(
    raw_params: Any,
) -> Optional[list[str]]:
    """Return normalized non-empty param list, or None if input absent/invalid."""
    if not isinstance(raw_params, (list, tuple)):
        return None
    out: list[str] = []
    for p in raw_params:
        n = normalize_store_display_name(p)
        if n is None:
            return None
        out.append(n)
    if not out:
        return None
    return out


def resolve_meta_template_parameters(
    context: Mapping[str, Any],
    *,
    template_name: Optional[str],
) -> tuple[Optional[list[str]], Optional[str]]:
    """
    Resolve Meta template body parameters.

    Order:
      A. Explicit context['template_parameters'] (valid normalized list)
      B/C. Governed store_name (store_name → store_display_name → Store → slug)
      D. Fail with meta_store_display_name_missing

    Never uses the full recovery message.
    Returns (params, error_code).
    """
    name = (template_name or "").strip()
    explicit = _normalize_explicit_template_parameters(context.get("template_parameters"))
    if explicit is not None:
        if name in _META_RECOVERY_STORE_NAME_TEMPLATES:
            expected = (
                META_RECOVERY_TEMPLATE_V2_BODY_PARAM_COUNT
                if name == META_RECOVERY_TEMPLATE_CARTFLOW_V2
                else META_RECOVERY_TEMPLATE_V1_BODY_PARAM_COUNT
            )
            if len(explicit) != expected:
                return None, "meta_template_parameter_count_invalid"
        return explicit, None

    display = resolve_store_name_from_context(context)
    if not display:
        return None, "meta_store_display_name_missing"
    params = [display]
    if name in _META_RECOVERY_STORE_NAME_TEMPLATES:
        expected = (
            META_RECOVERY_TEMPLATE_V2_BODY_PARAM_COUNT
            if name == META_RECOVERY_TEMPLATE_CARTFLOW_V2
            else META_RECOVERY_TEMPLATE_V1_BODY_PARAM_COUNT
        )
        if len(params) != expected:
            return None, "meta_template_parameter_count_invalid"
    return params, None


def resolve_meta_template_button_url_param(
    context: Mapping[str, Any],
    *,
    template_name: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve URL-button dynamic suffix for recovery template V2.
    Requires checkout_url; mints opaque checkout redirect token (not raw URL).
    """
    name = (template_name or "").strip()
    if name and name not in _META_RECOVERY_BUTTON_TEMPLATES:
        return None, None
    explicit = str(context.get("template_button_url_param") or "").strip()
    if explicit:
        return explicit[:1800], None
    checkout = resolve_checkout_url_from_context(context)
    if not checkout:
        return None, "meta_checkout_url_missing"
    from services.meta_recovery_template_contract_v1 import TEMPLATE_NAME
    from services.recovery_checkout_redirect_v1 import mint_token_from_send_context

    token = mint_token_from_send_context(
        context,
        checkout_url=checkout,
        template_name=name or TEMPLATE_NAME,
    )
    if not token:
        return None, "meta_checkout_url_invalid"
    return token, None


def _proven_session_window_allows_freeform(
    *,
    to_phone: str,
    store_slug: Optional[str],
) -> bool:
    """
    Use existing platform conversation-window truth only.
    Returns True only when status is explicitly inside_24h.
    Unknown / outside → False (do not invent session truth).
    """
    try:
        from services.whatsapp_production_reality_v2 import (
            WINDOW_INSIDE,
            evaluate_conversation_window,
            resolve_store_for_template_enforcement,
        )

        key = "".join(c for c in (to_phone or "") if c.isdigit())
        if not key:
            return False
        store = resolve_store_for_template_enforcement((store_slug or "")[:255])
        window = evaluate_conversation_window(
            customer_phone_key=key,
            store=store,
        )
        return window.conversation_window_status == WINDOW_INSIDE
    except Exception:  # noqa: BLE001
        return False


def _apply_shared_preflight_guards(
    *,
    context: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    """Reuse Twilio-path guards for Meta so lifecycle safety stays consistent."""
    from services.whatsapp_send import _blocked_send_whatsapp_if_user_rejected_help

    store_slug = str(context.get("store_slug") or "")[:255] or None
    session_id = str(context.get("session_id") or "")[:512] or None
    reason_tag = context.get("reason_tag")

    try:
        from services.store_reality_simulator.safe_delivery_adapter_v1 import (
            guard_send_whatsapp,
        )

        sim_guard = guard_send_whatsapp(
            store_slug=store_slug,
            reason_tag=str(reason_tag) if reason_tag is not None else None,
        )
        if sim_guard is not None:
            return sim_guard
    except Exception:  # noqa: BLE001
        try:
            from services.store_reality_simulator.context_v1 import is_simulation_active

            if is_simulation_active():
                return {
                    "ok": False,
                    "error": "simulation_adapter_unavailable",
                    "provider": PROVIDER_META,
                    "accepted": False,
                    "raw_payload_stored": False,
                }
        except Exception:  # noqa: BLE001
            pass

    blocked = _blocked_send_whatsapp_if_user_rejected_help(store_slug, session_id)
    if blocked is not None:
        out = dict(blocked)
        out.setdefault("provider", PROVIDER_META)
        out["accepted"] = False
        out["raw_payload_stored"] = False
        return out

    try:
        from services.operational_control_v1 import operational_control_blocks_whatsapp_send_safe

        oc_blocked = operational_control_blocks_whatsapp_send_safe(
            store_slug=store_slug,
            reason_tag=str(reason_tag) if reason_tag is not None else None,
        )
        if oc_blocked is not None:
            out = dict(oc_blocked)
            out.setdefault("provider", PROVIDER_META)
            out["accepted"] = False
            out["raw_payload_stored"] = False
            return out
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "error": "operational_control_unavailable",
            "provider": PROVIDER_META,
            "accepted": False,
            "raw_payload_stored": False,
            "unavailable_reason": str(exc)[:200],
        }

    # Twilio's enforce_whatsapp_template_window_before_send is not applied here —
    # Meta selects template vs session_text from conversation-window truth below.
    return None


def _build_meta_request(
    to_phone: str,
    message: str,
    context: Mapping[str, Any],
) -> tuple[WhatsAppProviderRequest, Optional[str]]:
    """
    Meta recovery: template mode by default.

    session_text only when existing platform truth proves inside_24h window,
    or when context explicitly sets message_mode=session_text *and* window is proven.

    Returns (request, error_code). error_code is set when template params cannot
    be resolved — caller must not call Graph.
    """
    ctx_mode = str(context.get("message_mode") or "").strip().lower()
    allow_session = _proven_session_window_allows_freeform(
        to_phone=to_phone,
        store_slug=str(context.get("store_slug") or "") or None,
    )

    if ctx_mode == MODE_TEMPLATE:
        mode = MODE_TEMPLATE
    elif ctx_mode == MODE_SESSION_TEXT:
        # Honored only when platform truth proves inside_24h (enforced again before send)
        mode = MODE_SESSION_TEXT if allow_session else MODE_TEMPLATE
    elif allow_session:
        # Proven window + no explicit mode → session free-form allowed
        mode = MODE_SESSION_TEXT
    else:
        # Unknown/outside window → template only (never silent free-form)
        mode = MODE_TEMPLATE

    env_name, env_lang = _meta_template_defaults_from_env()
    template_name = (
        str(context.get("template_name") or "").strip()
        or env_name
    )
    template_language = (
        str(context.get("template_language") or "").strip()
        or env_lang
    )

    template_parameters: list[str] = []
    param_error: Optional[str] = None
    button_url_param: Optional[str] = None
    button_error: Optional[str] = None
    store_display_name = resolve_store_name_from_context(context)
    checkout_url = resolve_checkout_url_from_context(context)
    if mode == MODE_TEMPLATE:
        template_parameters, param_error = resolve_meta_template_parameters(
            context,
            template_name=template_name,
        )
        if template_parameters and not store_display_name:
            store_display_name = template_parameters[0]
        button_url_param, button_error = resolve_meta_template_button_url_param(
            context,
            template_name=template_name,
        )
        if param_error is None and button_error:
            param_error = button_error

    # body_text retained for session_text / Twilio-compat; NEVER copied into template params
    req = WhatsAppProviderRequest(
        to_phone=to_phone,
        provider=PROVIDER_META,
        message_mode=mode,
        body_text=(message or "").strip(),
        template_name=template_name,
        template_language=template_language,
        template_parameters=list(template_parameters or []),
        checkout_url=checkout_url,
        template_button_url_param=button_url_param,
        recovery_key=str(context.get("recovery_key") or "")[:120] or None,
        store_slug=str(context.get("store_slug") or "")[:255] or None,
        store_display_name=store_display_name,
        store_name=store_display_name,
        idempotency_key=str(context.get("idempotency_key") or "")[:256] or None,
        reason_tag=str(context.get("reason_tag") or "")[:64] or None,
        session_id=str(context.get("session_id") or "")[:512] or None,
        wa_trace_path=context.get("wa_trace_path"),
        wa_trace_last_activity=context.get("wa_trace_last_activity"),
        wa_trace_recovery_delay_minutes=context.get("wa_trace_recovery_delay_minutes"),
        wa_trace_delay_passed=context.get("wa_trace_delay_passed"),
    )
    return req, param_error if mode == MODE_TEMPLATE else None


def send_whatsapp_message(
    to_phone: str,
    message: str,
    context: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """
    Provider-neutral recovery send entry.

    Selects Twilio or Meta from WHATSAPP_PROVIDER (default twilio).
    Returns legacy-compatible dict (ok/sid/status/error) plus canonical fields.
    No automatic fallback between providers.
    """
    ctx: Mapping[str, Any] = context or {}
    try:
        from services.db_resource_safety_v1.release_before_wait_v1 import (
            release_before_external_wait,
        )

        release_before_external_wait(reason="whatsapp_send")
    except Exception:  # noqa: BLE001
        pass
    explicit = ctx.get("provider")
    provider = resolve_whatsapp_provider(
        str(explicit) if explicit is not None else None
    )

    if provider == PROVIDER_TWILIO:
        req = WhatsAppProviderRequest(
            to_phone=to_phone or "",
            provider=PROVIDER_TWILIO,
            message_mode=MODE_SESSION_TEXT,
            body_text=(message or "").strip(),
            recovery_key=str(ctx.get("recovery_key") or "")[:120] or None,
            store_slug=str(ctx.get("store_slug") or "")[:255] or None,
            idempotency_key=str(ctx.get("idempotency_key") or "")[:256] or None,
            reason_tag=str(ctx.get("reason_tag") or "")[:64] or None,
            session_id=str(ctx.get("session_id") or "")[:512] or None,
            wa_trace_path=ctx.get("wa_trace_path"),
            wa_trace_last_activity=ctx.get("wa_trace_last_activity"),
            wa_trace_recovery_delay_minutes=ctx.get("wa_trace_recovery_delay_minutes"),
            wa_trace_delay_passed=ctx.get("wa_trace_delay_passed"),
        )
        out = send_via_twilio(req)
        _log_provider_diagnostic(
            provider=PROVIDER_TWILIO,
            accepted=bool(out.get("ok") is True),
            recovery_key=req.recovery_key,
            store_slug=req.store_slug,
            external_message_id=str(out.get("sid") or out.get("external_message_id") or "")
            or None,
            error_code=str(out.get("error_code") or out.get("error") or "") or None,
            error_subcode=str(out.get("error_subcode") or "") or None,
            message_mode=req.message_mode,
        )
        return out

    # Meta path
    preflight = _apply_shared_preflight_guards(context=ctx)
    if preflight is not None:
        _log_provider_diagnostic(
            provider=PROVIDER_META,
            accepted=False,
            recovery_key=str(ctx.get("recovery_key") or "") or None,
            store_slug=str(ctx.get("store_slug") or "") or None,
            external_message_id=None,
            error_code=str(preflight.get("error") or "preflight_blocked"),
            error_subcode=None,
            message_mode=str(ctx.get("message_mode") or MODE_TEMPLATE),
        )
        return preflight

    req, param_error = _build_meta_request(to_phone or "", message or "", ctx)

    # Refuse silent free-form Meta send outside proven session window
    if req.message_mode == MODE_SESSION_TEXT:
        if not _proven_session_window_allows_freeform(
            to_phone=to_phone or "",
            store_slug=req.store_slug,
        ):
            blocked = empty_provider_result(
                PROVIDER_META,
                error_code="meta_session_text_not_allowed",
                error_message_safe="meta_session_text_not_allowed",
                message_mode=MODE_SESSION_TEXT,
            ).to_legacy_wa_dict()
            _log_provider_diagnostic(
                provider=PROVIDER_META,
                accepted=False,
                recovery_key=req.recovery_key,
                store_slug=req.store_slug,
                external_message_id=None,
                error_code="meta_session_text_not_allowed",
                error_subcode=None,
                message_mode=MODE_SESSION_TEXT,
            )
            return blocked

    if req.message_mode == MODE_TEMPLATE and not (req.template_name or "").strip():
        missing = empty_provider_result(
            PROVIDER_META,
            error_code="meta_template_name_missing",
            error_message_safe="meta_template_name_missing",
            message_mode=MODE_TEMPLATE,
        ).to_legacy_wa_dict()
        _log_provider_diagnostic(
            provider=PROVIDER_META,
            accepted=False,
            recovery_key=req.recovery_key,
            store_slug=req.store_slug,
            external_message_id=None,
            error_code="meta_template_name_missing",
            error_subcode=None,
            message_mode=MODE_TEMPLATE,
        )
        return missing

    if req.message_mode == MODE_TEMPLATE and param_error:
        rejected = empty_provider_result(
            PROVIDER_META,
            error_code=param_error,
            error_message_safe=param_error,
            message_mode=MODE_TEMPLATE,
        ).to_legacy_wa_dict()
        _log_provider_diagnostic(
            provider=PROVIDER_META,
            accepted=False,
            recovery_key=req.recovery_key,
            store_slug=req.store_slug,
            external_message_id=None,
            error_code=param_error,
            error_subcode=None,
            message_mode=MODE_TEMPLATE,
        )
        return rejected

    if req.message_mode == MODE_TEMPLATE and len(req.template_parameters or []) < 1:
        rejected = empty_provider_result(
            PROVIDER_META,
            error_code="meta_store_display_name_missing",
            error_message_safe="meta_store_display_name_missing",
            message_mode=MODE_TEMPLATE,
        ).to_legacy_wa_dict()
        _log_provider_diagnostic(
            provider=PROVIDER_META,
            accepted=False,
            recovery_key=req.recovery_key,
            store_slug=req.store_slug,
            external_message_id=None,
            error_code="meta_store_display_name_missing",
            error_subcode=None,
            message_mode=MODE_TEMPLATE,
        )
        return rejected

    out = send_via_meta(req)
    _log_provider_diagnostic(
        provider=PROVIDER_META,
        accepted=bool(out.get("ok") is True),
        recovery_key=req.recovery_key,
        store_slug=req.store_slug,
        external_message_id=str(out.get("sid") or out.get("external_message_id") or "")
        or None,
        error_code=str(out.get("error_code") or out.get("error") or "") or None,
        error_subcode=str(out.get("error_subcode") or "") or None,
        message_mode=req.message_mode,
    )
    # Safety: never echo token-like values into result
    for k in list(out.keys()):
        if "token" in k.lower() or "authorization" in k.lower():
            out.pop(k, None)
    return out


__all__ = [
    "resolve_whatsapp_provider",
    "send_whatsapp_message",
    "normalize_store_display_name",
    "normalize_checkout_url",
    "resolve_store_display_name_from_context",
    "resolve_store_name_from_context",
    "resolve_checkout_url_from_context",
    "resolve_meta_template_parameters",
    "resolve_meta_template_button_url_param",
    "META_RECOVERY_TEMPLATE_CARTFLOW_V1",
    "META_RECOVERY_TEMPLATE_CARTFLOW_V2",
    "PROVIDER_META",
    "PROVIDER_TWILIO",
    "MODE_TEMPLATE",
    "MODE_SESSION_TEXT",
]
