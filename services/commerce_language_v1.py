# -*- coding: utf-8 -*-
"""
Commerce Language V1 — merchant-facing translation only.

Owns how existing commerce facts are *said* to the merchant.
Does not mint Truth, Signals, Decisions, Recovery, or lifecycle state.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

from services.commerce_signals_v1 import (
    SIGNAL_PURCHASE_CONFIRMED,
    SIGNAL_RECOVERY_COMPLETED,
)

# Calm Leave copy when a recovered-purchase outcome is the Pulse story.
DECISION_SUMMARY_NO_INTERVENTION_AR = "لا توجد حالة تحتاج تدخلك الآن."
MERCHANT_DECISION_NO_DECISION_AR = "لا قرار مطلوب حاليًا."

_RECOVERED_PURCHASE_TYPES = frozenset(
    {
        SIGNAL_PURCHASE_CONFIRMED,
        SIGNAL_RECOVERY_COMPLETED,
    }
)


def _norm(value: Any) -> str:
    return str(value or "").strip()


def is_recovered_purchase_signal_type(signal_type: Any) -> bool:
    return _norm(signal_type) in _RECOVERED_PURCHASE_TYPES


def recovered_purchase_count_phrase_ar(count: int) -> str:
    """Arabic singular / dual / plural for recovered purchase count."""
    n = int(count or 0)
    if n <= 0:
        n = 1
    if n == 1:
        return "عملية شراء واحدة"
    if n == 2:
        return "عمليتي شراء"
    if 3 <= n <= 10:
        return f"{n} عمليات شراء"
    return f"{n} عملية شراء"


def format_recovered_value_ar(value: float) -> str:
    """Format a known recovered amount for Arabic merchant copy (no currency invent)."""
    amount = float(value)
    if amount == int(amount):
        return str(int(amount))
    text = f"{amount:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def recovered_purchase_outcome_ar(
    *,
    count: int,
    total_value: Optional[float] = None,
) -> str:
    """
    Merchant outcome for confirmed recovered purchase(s).

    Uses count + optional total recovered value only.
    Never invents an amount when total_value is missing/invalid.
    """
    phrase = recovered_purchase_count_phrase_ar(count)
    if total_value is None:
        return f"خلال غيابك تم استرداد {phrase}."
    try:
        amount = float(total_value)
    except (TypeError, ValueError):
        return f"خلال غيابك تم استرداد {phrase}."
    if amount <= 0 or amount != amount:  # NaN guard
        return f"خلال غيابك تم استرداد {phrase}."
    return (
        f"خلال غيابك تم استرداد {phrase} "
        f"بقيمة {format_recovered_value_ar(amount)} ريال."
    )


def collect_recovered_purchase_keys(signals: Sequence[Mapping[str, Any]]) -> list[str]:
    """Distinct recovery_key values with purchase_confirmed or recovery_completed."""
    out: list[str] = []
    seen: set[str] = set()
    for raw in signals or ():
        if not isinstance(raw, Mapping):
            continue
        if not is_recovered_purchase_signal_type(raw.get("signal_type")):
            continue
        subject = raw.get("subject")
        subject_map = dict(subject) if isinstance(subject, Mapping) else {}
        rk = _norm(subject_map.get("recovery_key"))
        if not rk or rk in seen:
            continue
        seen.add(rk)
        out.append(rk)
    return out


def _cart_ref_from_recovery_key(recovery_key: str) -> str:
    rk = _norm(recovery_key)
    if ":" in rk:
        return rk.split(":", 1)[1].strip()
    return rk


def load_recovered_cart_values_by_key(
    store_slug: str,
    recovery_keys: Sequence[str],
) -> dict[str, Optional[float]]:
    """
    Read existing recovered cart_value for recovery keys (AbandonedCart only).

    Fail-closed: missing rows / errors → None for that key (no invented amount).
    """
    ss = _norm(store_slug)
    keys = [_norm(k) for k in (recovery_keys or ()) if _norm(k)]
    out: dict[str, Optional[float]] = {k: None for k in keys}
    if not ss or not keys:
        return out
    try:
        from extensions import db  # noqa: PLC0415
        from models import AbandonedCart, Store  # noqa: PLC0415

        store = (
            db.session.query(Store)
            .filter(Store.zid_store_id == ss)
            .first()
        )
        if store is None:
            return out
        store_id = getattr(store, "id", None)
        if store_id is None:
            return out

        refs = {_cart_ref_from_recovery_key(k): k for k in keys}
        ref_list = [r for r in refs if r]
        if not ref_list:
            return out

        from sqlalchemy import or_  # noqa: PLC0415

        rows = (
            db.session.query(AbandonedCart)
            .filter(
                AbandonedCart.store_id == store_id,
                AbandonedCart.status == "recovered",
                or_(
                    AbandonedCart.zid_cart_id.in_(ref_list),
                    AbandonedCart.recovery_session_id.in_(ref_list),
                ),
            )
            .all()
        )
        for row in rows:
            cid = _norm(getattr(row, "zid_cart_id", None))
            sid = _norm(getattr(row, "recovery_session_id", None))
            matched_key = refs.get(cid) or refs.get(sid)
            if not matched_key:
                continue
            raw_val = getattr(row, "cart_value", None)
            if raw_val is None:
                continue
            try:
                amount = float(raw_val)
            except (TypeError, ValueError):
                continue
            if amount <= 0 or amount != amount:
                continue
            # Prefer first positive value; do not overwrite with a weaker second match.
            if out.get(matched_key) is None:
                out[matched_key] = amount
    except Exception:  # noqa: BLE001 — presentation must not break Pulse
        return out
    return out


def resolve_recovered_purchase_total(
    *,
    count: int,
    amounts_by_key: Optional[Mapping[str, Optional[float]]] = None,
    recovery_keys: Optional[Sequence[str]] = None,
    store_slug: str = "",
) -> tuple[int, Optional[float]]:
    """
    Resolve (count, total_value).

    total_value is set only when every recovered key has a known positive amount.
    Otherwise total_value is None (safe wording without invented amount).
    """
    n = int(count or 0)
    keys = [_norm(k) for k in (recovery_keys or ()) if _norm(k)]
    if n <= 0:
        n = len(keys) or 0
    if n <= 0:
        return 0, None

    amounts: dict[str, Optional[float]]
    if amounts_by_key is not None:
        amounts = {k: amounts_by_key.get(k) for k in keys} if keys else {}
        if not keys and amounts_by_key:
            # Tests may pass a flat map without keys list.
            amounts = { _norm(k): v for k, v in amounts_by_key.items() }
            keys = list(amounts.keys())
            n = max(n, len(keys))
    else:
        amounts = load_recovered_cart_values_by_key(store_slug, keys)

    if not keys:
        return n, None

    values: list[float] = []
    for key in keys:
        raw = amounts.get(key)
        if raw is None:
            return n, None
        try:
            amount = float(raw)
        except (TypeError, ValueError):
            return n, None
        if amount <= 0 or amount != amount:
            return n, None
        values.append(amount)
    if len(values) != len(keys):
        return n, None
    return n, float(sum(values))


__all__ = [
    "DECISION_SUMMARY_NO_INTERVENTION_AR",
    "MERCHANT_DECISION_NO_DECISION_AR",
    "collect_recovered_purchase_keys",
    "format_recovered_value_ar",
    "is_recovered_purchase_signal_type",
    "load_recovered_cart_values_by_key",
    "recovered_purchase_count_phrase_ar",
    "recovered_purchase_outcome_ar",
    "resolve_recovered_purchase_total",
]
