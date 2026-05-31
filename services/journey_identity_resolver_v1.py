# -*- coding: utf-8 -*-
"""
Journey identity shadow resolver — Phase 0 observation only.

Computes BID / JID / recommended RK without changing production recovery_key behavior.
Enable logs: CARTFLOW_JOURNEY_IDENTITY_MODE=shadow (default off).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Literal, Mapping, Optional, Union

log = logging.getLogger("cartflow")

_MODE_ENV = "CARTFLOW_JOURNEY_IDENTITY_MODE"

_SYNTHETIC_CART_PREFIXES = ("cf_w_", "fp:")
_PLACEHOLDER_CART_IDS = frozenset(
    {
        "",
        "-",
        "default",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "undefined",
    }
)


def journey_identity_mode() -> Literal["off", "shadow"]:
    raw = (os.getenv(_MODE_ENV) or "").strip().lower()
    if raw == "shadow":
        return "shadow"
    if raw and raw not in ("off", "0", "false", "no"):
        log.warning(
            "[JOURNEY IDENTITY] invalid_%s=%r defaulting_to=off",
            _MODE_ENV,
            raw[:80],
        )
    return "off"


def journey_identity_shadow_logging_enabled() -> bool:
    return journey_identity_mode() == "shadow"


def is_synthetic_cart_id(cart_id: Optional[str]) -> bool:
    cid = (str(cart_id).strip() if cart_id is not None else "")[:255]
    if not cid:
        return True
    if cid.casefold() in _PLACEHOLDER_CART_IDS:
        return True
    for prefix in _SYNTHETIC_CART_PREFIXES:
        if cid.startswith(prefix):
            return True
    return False


def has_stable_cart_id(cart_id: Optional[str]) -> bool:
    return not is_synthetic_cart_id(cart_id)


def _norm_session_id(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()[:512]
    s = str(raw).strip()
    return s[:512] if s else ""


def _norm_cart_id(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw.strip()[:255]
    s = str(raw).strip()
    return s[:255] if s else ""


def _payload_dict(
    payload_or_fields: Union[Mapping[str, Any], dict[str, Any], None],
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> dict[str, Any]:
    if isinstance(payload_or_fields, Mapping):
        out = dict(payload_or_fields)
    else:
        out = {}
    if store_slug:
        out.setdefault("store", store_slug)
        out.setdefault("store_slug", store_slug)
    if session_id:
        out.setdefault("session_id", session_id)
    if cart_id:
        out.setdefault("cart_id", cart_id)
    return out


def _build_rk(store_slug: str, part: str) -> str:
    ss = (store_slug or "").strip()[:255]
    seg = (part or "").strip()[:512]
    if not ss or not seg:
        return ""
    return f"{ss}:{seg}"[:800]


@dataclass(frozen=True)
class JourneyIdentityShadowResult:
    store_slug: str
    session_id: str
    cart_id: str
    bid_rk: str
    jid_rk: str
    current_rk: str
    recommended_rk: str
    identity_mode: Literal["shadow"]
    has_stable_cart_id: bool
    is_synthetic_cart_id: bool
    mismatch: bool
    mismatch_reason: str

    def to_log_dict(self, *, source: str) -> dict[str, str]:
        return {
            "source": (source or "unknown")[:64],
            "store_slug": (self.store_slug or "-")[:255],
            "has_session_id": "true" if self.session_id else "false",
            "has_cart_id": "true" if self.cart_id else "false",
            "bid_rk": (self.bid_rk or "-")[:512],
            "jid_rk": (self.jid_rk or "-")[:512],
            "current_rk": (self.current_rk or "-")[:512],
            "recommended_rk": (self.recommended_rk or "-")[:512],
            "mismatch": "true" if self.mismatch else "false",
            "mismatch_reason": (self.mismatch_reason or "-")[:220],
        }


def resolve_journey_identity_shadow(
    payload_or_fields: Union[Mapping[str, Any], dict[str, Any], None] = None,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> JourneyIdentityShadowResult:
    """
    Read-only journey identity snapshot for shadow observability.

    ``current_rk`` uses production ``_recovery_key_from_payload`` (session-first).
    ``recommended_rk`` follows the future contract: JID when stable cart_id exists,
    otherwise BID.
    """
    payload = _payload_dict(
        payload_or_fields,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )

    try:
        from main import (  # noqa: PLC0415 — lazy: match production slug + rk
            _cart_id_str_from_payload,
            _normalize_store_slug,
            _recovery_key_from_payload,
        )
    except Exception:  # noqa: BLE001
        slug = (store_slug or "").strip()[:255]
        sid = _norm_session_id(payload.get("session_id"))
        cid = _norm_cart_id(payload.get("cart_id"))
        stable = has_stable_cart_id(cid)
        synthetic = is_synthetic_cart_id(cid)
        bid = _build_rk(slug, sid) if sid else ""
        jid = _build_rk(slug, cid) if stable else ""
        recommended = jid or bid or ""
        return JourneyIdentityShadowResult(
            store_slug=slug,
            session_id=sid,
            cart_id=cid,
            bid_rk=bid,
            jid_rk=jid,
            current_rk=recommended,
            recommended_rk=recommended,
            identity_mode="shadow",
            has_stable_cart_id=stable,
            is_synthetic_cart_id=synthetic,
            mismatch=False,
            mismatch_reason="",
        )

    slug = _normalize_store_slug(payload)
    sid = _norm_session_id(payload.get("session_id"))
    cid_raw = _cart_id_str_from_payload(payload)
    cid = _norm_cart_id(cid_raw)
    stable = has_stable_cart_id(cid)
    synthetic = is_synthetic_cart_id(cid)

    bid_rk = _build_rk(slug, sid) if sid else ""
    jid_rk = _build_rk(slug, cid) if stable else ""

    if jid_rk:
        recommended_rk = jid_rk
    elif bid_rk:
        recommended_rk = bid_rk
    else:
        recommended_rk = _recovery_key_from_payload(payload)

    current_rk = _recovery_key_from_payload(payload)

    mismatch = bool(current_rk and recommended_rk and current_rk != recommended_rk)
    mismatch_reason = ""
    if mismatch:
        if sid and stable and bid_rk and jid_rk and current_rk == bid_rk:
            mismatch_reason = "stable_cart_id_present_but_current_rk_uses_session"
        elif stable and not jid_rk:
            mismatch_reason = "stable_cart_id_expected_jid_missing"
        else:
            mismatch_reason = "current_rk_differs_from_recommended_rk"

    return JourneyIdentityShadowResult(
        store_slug=slug,
        session_id=sid,
        cart_id=cid,
        bid_rk=bid_rk,
        jid_rk=jid_rk,
        current_rk=current_rk,
        recommended_rk=recommended_rk,
        identity_mode="shadow",
        has_stable_cart_id=stable,
        is_synthetic_cart_id=synthetic,
        mismatch=mismatch,
        mismatch_reason=mismatch_reason,
    )


def emit_journey_identity_shadow_log(
    result: JourneyIdentityShadowResult,
    *,
    source: str,
) -> None:
    """Structured log — safe fields only; never raises."""
    fields = result.to_log_dict(source=source)
    lines = ["[JOURNEY IDENTITY SHADOW]"] + [
        f"{k}={v}" for k, v in fields.items()
    ]
    block = "\n".join(lines)
    try:
        print(block, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", block.replace("\n", " | "))
    except Exception:  # noqa: BLE001
        pass


def maybe_log_journey_identity_shadow(
    payload_or_fields: Union[Mapping[str, Any], dict[str, Any], None] = None,
    *,
    source: str,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> Optional[JourneyIdentityShadowResult]:
    """
    Resolve and log when CARTFLOW_JOURNEY_IDENTITY_MODE=shadow.
    No-op when off. Never changes runtime behavior.
    """
    if not journey_identity_shadow_logging_enabled():
        return None
    try:
        result = resolve_journey_identity_shadow(
            payload_or_fields,
            store_slug=store_slug,
            session_id=session_id,
            cart_id=cart_id,
        )
        emit_journey_identity_shadow_log(result, source=source)
        return result
    except Exception as exc:  # noqa: BLE001
        try:
            log.warning(
                "[JOURNEY IDENTITY SHADOW] resolve_failed source=%s err=%s",
                (source or "-")[:64],
                str(exc)[:200],
            )
        except Exception:  # noqa: BLE001
            pass
        return None


__all__ = [
    "JourneyIdentityShadowResult",
    "emit_journey_identity_shadow_log",
    "has_stable_cart_id",
    "is_synthetic_cart_id",
    "journey_identity_mode",
    "journey_identity_shadow_logging_enabled",
    "maybe_log_journey_identity_shadow",
    "resolve_journey_identity_shadow",
]
