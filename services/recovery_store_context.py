# -*- coding: utf-8 -*-
"""Canonical store identity for recovery runtime — one zid per flow."""
from __future__ import annotations

from typing import Any, Optional

from services.merchant_test_widget_store_v1 import is_public_widget_sandbox_slug


def canonical_store_slug_from_recovery_key(recovery_key: Optional[str]) -> Optional[str]:
    """First segment of ``{store_slug}:{session_id}`` recovery_key."""
    rk = (recovery_key or "").strip()
    if not rk or ":" not in rk:
        return None
    head = rk.split(":", 1)[0].strip()[:255]
    return head if head else None


def session_part_from_recovery_key(recovery_key: Optional[str]) -> str:
    rk = (recovery_key or "").strip()
    if not rk or ":" not in rk:
        return rk
    return rk.split(":", 1)[1].strip()[:512]


def reconcile_recovery_identity(
    *,
    recovery_key: str,
    store_slug: str = "",
    session_id: str = "",
    recovery_context: Optional[dict[str, Any]] = None,
) -> tuple[str, str, str]:
    """
    When durable store_slug (schedule row / context) is a merchant zid but
    recovery_key still uses demo/default, rebuild ``{merchant}:{session}``.
    """
    rk_in = (recovery_key or "").strip()[:512]
    slug_in = (store_slug or "").strip()[:255]
    sid_in = (session_id or "").strip()[:512]
    ctx = recovery_context if isinstance(recovery_context, dict) else {}
    ctx_slug = (str(ctx.get("store_slug") or "")).strip()[:255]
    ctx_sid = (str(ctx.get("session_id") or "")).strip()[:512]

    rk_slug = canonical_store_slug_from_recovery_key(rk_in) or ""
    rk_sid = session_part_from_recovery_key(rk_in) if rk_in else ""

    slug = slug_in or ctx_slug or rk_slug
    sid = sid_in or ctx_sid or rk_sid

    durable_slug = slug_in or ctx_slug
    auth_slug = ""
    try:
        from services.merchant_test_widget_store_v1 import (  # noqa: PLC0415
            merchant_authenticated_store_slug,
        )

        auth_slug = (merchant_authenticated_store_slug() or "").strip()[:255]
    except Exception:  # noqa: BLE001
        auth_slug = ""

    merchant_slug = ""
    if durable_slug and not is_public_widget_sandbox_slug(durable_slug):
        merchant_slug = durable_slug
    elif auth_slug and not is_public_widget_sandbox_slug(auth_slug):
        merchant_slug = auth_slug

    if (
        merchant_slug
        and rk_slug
        and is_public_widget_sandbox_slug(rk_slug)
        and sid
    ):
        slug = merchant_slug
        rk_out = f"{merchant_slug}:{sid}"[:512]
        return rk_out, slug, sid

    if rk_in and rk_slug and not is_public_widget_sandbox_slug(rk_slug):
        return rk_in, rk_slug, sid or rk_sid
    if rk_in:
        return rk_in, slug or rk_slug, sid or rk_sid
    if slug and sid:
        return f"{slug}:{sid}"[:512], slug, sid
    return rk_in, slug, sid


def coerce_recovery_runtime_store_slug(
    recovery_key: str,
    store_slug_hint: Optional[str],
) -> str:
    """
    Prefer authenticated merchant hint over sandbox recovery_key prefix.
    Otherwise keep sandbox canon (ignore stale non-sandbox dashboard hints).
    """
    canon = canonical_store_slug_from_recovery_key(recovery_key)
    hint = (store_slug_hint or "").strip()[:255]
    auth_slug = ""
    try:
        from services.merchant_test_widget_store_v1 import (  # noqa: PLC0415
            merchant_authenticated_store_slug,
        )

        auth_slug = (merchant_authenticated_store_slug() or "").strip()[:255]
    except Exception:  # noqa: BLE001
        auth_slug = ""

    if hint and not is_public_widget_sandbox_slug(hint):
        if not canon or is_public_widget_sandbox_slug(canon):
            if auth_slug and auth_slug.casefold() == hint.casefold():
                if canon and hint.casefold() != canon.casefold():
                    log_store_context_mismatch(
                        recovery_key=recovery_key,
                        canonical_store_slug=canon,
                        hint_store_slug=hint,
                    )
                return hint
            if canon and is_public_widget_sandbox_slug(canon):
                return canon
            return hint
    if canon:
        if hint and hint.casefold() != canon.casefold():
            log_store_context_mismatch(
                recovery_key=recovery_key,
                canonical_store_slug=canon,
                hint_store_slug=hint,
            )
        return canon
    return hint


def log_recovery_identity_source(
    *,
    dashboard_store: str,
    schedule_recovery_key: str,
    ctx_recovery_key: str,
    derived_store_slug: str,
    source_function: str,
) -> None:
    try:
        print("[RECOVERY IDENTITY SOURCE]", flush=True)
        print(f"dashboard_store={(dashboard_store or '-')[:255]}", flush=True)
        print(
            f"schedule_recovery_key={(schedule_recovery_key or '-')[:512]}",
            flush=True,
        )
        print(f"ctx_recovery_key={(ctx_recovery_key or '-')[:512]}", flush=True)
        print(f"derived_store_slug={(derived_store_slug or '-')[:255]}", flush=True)
        print(f"source_function={(source_function or '-')[:128]}", flush=True)
    except OSError:
        pass


def log_store_context_mismatch(
    *,
    recovery_key: str,
    canonical_store_slug: str,
    hint_store_slug: str,
) -> None:
    try:
        print("[STORE CONTEXT MISMATCH]", flush=True)
        print(f"recovery_key={recovery_key[:120]}", flush=True)
        print(f"canonical_store_slug={canonical_store_slug}", flush=True)
        print(f"hint_store_slug={hint_store_slug}", flush=True)
        print("action=use_canonical_only", flush=True)
    except OSError:
        pass


def _norm_slug_label(raw: Optional[str]) -> str:
    s = (raw or "").strip()
    return s if s else "-"


def log_store_context_check(
    *,
    recovery_key: str,
    canonical_store_slug: str,
    template_store_slug: str,
    delay_store_slug: str,
    phone_store_slug: str,
    selected_store_slug: str,
) -> bool:
    """Emit ``[STORE CONTEXT CHECK]``; return whether all active slugs match canonical."""
    rk_store = canonical_store_slug_from_recovery_key(recovery_key) or canonical_store_slug
    canon = (canonical_store_slug or "").strip()
    labels = {
        "template_store_slug": _norm_slug_label(template_store_slug),
        "delay_store_slug": _norm_slug_label(delay_store_slug),
        "phone_store_slug": _norm_slug_label(phone_store_slug),
        "selected_store_slug": _norm_slug_label(selected_store_slug),
    }

    def _active_slug(val: str) -> Optional[str]:
        if not val or val == "-":
            return None
        return val

    active = [s for s in (_active_slug(v) for v in labels.values()) if s]
    ok = True
    if canon:
        for s in active:
            if s.casefold() != canon.casefold():
                ok = False
                break
    if rk_store and canon and rk_store.casefold() != canon.casefold():
        ok = False

    try:
        sel = _norm_slug_label(selected_store_slug or canon)
        print("[STORE CONTEXT CHECK]", flush=True)
        print(f"recovery_key_store={_norm_slug_label(rk_store)}", flush=True)
        print(f"template_store_slug={labels['template_store_slug']}", flush=True)
        print(f"delay_store_slug={labels['delay_store_slug']}", flush=True)
        print(f"phone_store_slug={labels['phone_store_slug']}", flush=True)
        print(f"selected_store_slug={sel}", flush=True)
        print(f"ok={'true' if ok else 'false'}", flush=True)
        if not ok:
            print("[STORE CONTEXT MISMATCH]", flush=True)
            print(f"canonical_store_slug={_norm_slug_label(canon)}", flush=True)
            print("action=use_canonical_only", flush=True)
    except OSError:
        pass
    return ok


def recovery_runtime_slugs_aligned(
    canonical_store_slug: str,
    *slugs: Optional[str],
) -> bool:
    canon = (canonical_store_slug or "").strip()
    if not canon:
        return True
    for raw in slugs:
        s = (raw or "").strip()
        if not s or s == "-":
            continue
        if s.casefold() != canon.casefold():
            return False
    return True
