# -*- coding: utf-8 -*-
"""Canonical store identity for recovery runtime — one zid per flow."""
from __future__ import annotations

from typing import Any, Optional


def canonical_store_slug_from_recovery_key(recovery_key: Optional[str]) -> Optional[str]:
    """First segment of ``{store_slug}:{session_id}`` recovery_key."""
    rk = (recovery_key or "").strip()
    if not rk or ":" not in rk:
        return None
    head = rk.split(":", 1)[0].strip()[:255]
    return head if head else None


def coerce_recovery_runtime_store_slug(
    recovery_key: str,
    store_slug_hint: Optional[str],
) -> str:
    """Prefer recovery_key merchant zid; log and ignore conflicting hints."""
    canon = canonical_store_slug_from_recovery_key(recovery_key)
    hint = (store_slug_hint or "").strip()[:255]
    if canon:
        if hint and hint.casefold() != canon.casefold():
            log_store_context_mismatch(
                recovery_key=recovery_key,
                canonical_store_slug=canon,
                hint_store_slug=hint,
            )
        return canon
    return hint


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
