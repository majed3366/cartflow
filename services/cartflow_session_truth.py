# -*- coding: utf-8 -*-
"""
Session truth hardening v1 — in-process session dicts are cache only.

Read paths must use ``has_conversion_truth`` / ``has_sent_truth`` so restart and
multi-worker gaps fall back to durable evidence (purchase_truth_records,
CartRecoveryLog). Write paths unchanged in v1.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from extensions import db
from models import CartRecoveryLog

log = logging.getLogger("cartflow")

_SENT_STATUSES = frozenset({"mock_sent", "sent_real"})
_CONVERSION_LOG_STATUSES = frozenset({"stopped_converted"})


def _emit_session_truth_log(tag: str, **fields: Any) -> None:
    parts = [f"[{tag}]"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        parts.append(f"{key}={str(val)[:200] if val is not None else '-'}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    try:
        log.info("%s", line)
    except Exception:  # noqa: BLE001
        pass


def parse_recovery_key(recovery_key: str) -> tuple[str, str]:
    """Return ``(store_slug, session_id)`` from ``slug:session``."""
    rk = (recovery_key or "").strip()
    if not rk:
        return "", ""
    if ":" not in rk:
        return rk, ""
    store_slug, session_id = rk.split(":", 1)
    return store_slug.strip(), session_id.strip()


def rehydrate_conversion_cache(recovery_key: str) -> None:
    rk = (recovery_key or "").strip()
    if not rk:
        return
    try:
        from main import _recovery_session_lock, _session_recovery_converted  # noqa: PLC0415

        with _recovery_session_lock:
            _session_recovery_converted[rk] = True
    except Exception as exc:  # noqa: BLE001
        log.warning("session truth rehydrate conversion cache failed: %s", exc)


def rehydrate_sent_cache(recovery_key: str) -> None:
    rk = (recovery_key or "").strip()
    if not rk:
        return
    try:
        from main import _recovery_session_lock, _session_recovery_sent  # noqa: PLC0415

        with _recovery_session_lock:
            _session_recovery_sent[rk] = True
    except Exception as exc:  # noqa: BLE001
        log.warning("session truth rehydrate sent cache failed: %s", exc)


def session_conversion_cache_hit(recovery_key: str) -> bool:
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    try:
        from main import _recovery_session_lock, _session_recovery_converted  # noqa: PLC0415

        with _recovery_session_lock:
            return bool(_session_recovery_converted.get(rk))
    except Exception:  # noqa: BLE001
        return False


def session_sent_cache_hit(recovery_key: str) -> bool:
    rk = (recovery_key or "").strip()
    if not rk:
        return False
    try:
        from main import _recovery_session_lock, _session_recovery_sent  # noqa: PLC0415

        with _recovery_session_lock:
            return bool(_session_recovery_sent.get(rk))
    except Exception:  # noqa: BLE001
        return False


def _durable_conversion_from_logs(
    *,
    recovery_key: str,
    session_id: str,
    cart_id: Optional[str] = None,
) -> bool:
    sid = (session_id or "").strip()[:512]
    if not sid:
        return False
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    try:
        from sqlalchemy import or_

        conds: list[Any] = [CartRecoveryLog.session_id == sid]
        if cid:
            conds.append(CartRecoveryLog.cart_id == cid)
        row = (
            db.session.query(CartRecoveryLog.id)
            .filter(
                CartRecoveryLog.status.in_(_CONVERSION_LOG_STATUSES),
                or_(*conds),
            )
            .first()
        )
        return row is not None
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "session truth conversion log lookup failed recovery_key=%s: %s",
            recovery_key,
            exc,
        )
        return False


def _durable_sent_from_logs(
    *,
    recovery_key: str,
    session_id: str,
    cart_id: Optional[str] = None,
    step: Optional[int] = None,
) -> bool:
    sid = (session_id or "").strip()[:512]
    if not sid:
        return False
    cid = (cart_id or "").strip()[:255] if cart_id else ""
    try:
        from sqlalchemy import or_

        conds: list[Any] = [CartRecoveryLog.session_id == sid]
        if cid:
            conds.append(CartRecoveryLog.cart_id == cid)
        q = db.session.query(CartRecoveryLog.id).filter(
            CartRecoveryLog.status.in_(_SENT_STATUSES),
            or_(*conds),
        )
        if step is not None:
            try:
                q = q.filter(CartRecoveryLog.step == int(step))
            except (TypeError, ValueError):
                pass
        return q.first() is not None
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "session truth sent log lookup failed recovery_key=%s: %s",
            recovery_key,
            exc,
        )
        return False


def has_conversion_truth(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: Optional[str] = None,
    rehydrate_cache: bool = True,
) -> bool:
    """
    True when durable evidence shows purchase/conversion for this recovery session.

    Order: session cache → purchase_truth_records → CartRecoveryLog stopped_converted.
    """
    rk = (recovery_key or "").strip()
    if not rk:
        return False

    if session_conversion_cache_hit(rk):
        _emit_session_truth_log(
            "SESSION TRUTH CACHE HIT",
            kind="conversion",
            recovery_key=rk,
        )
        return True

    _emit_session_truth_log(
        "SESSION TRUTH CACHE MISS",
        kind="conversion",
        recovery_key=rk,
    )

    try:
        from services.cartflow_purchase_truth import has_purchase

        if has_purchase(rk):
            _emit_session_truth_log(
                "SESSION TRUTH DB FALLBACK",
                kind="conversion",
                source="purchase_truth_records",
                recovery_key=rk,
            )
            if rehydrate_cache:
                rehydrate_conversion_cache(rk)
                _emit_session_truth_log(
                    "SESSION TRUTH REHYDRATED",
                    kind="conversion",
                    recovery_key=rk,
                )
            return True
    except Exception as exc:  # noqa: BLE001
        log.warning("session truth purchase_truth fallback failed: %s", exc)

    _slug, sid = parse_recovery_key(rk)
    sid_eff = (session_id or sid).strip()
    if _durable_conversion_from_logs(
        recovery_key=rk,
        session_id=sid_eff,
        cart_id=cart_id,
    ):
        _emit_session_truth_log(
            "SESSION TRUTH DB FALLBACK",
            kind="conversion",
            source="cart_recovery_log.stopped_converted",
            recovery_key=rk,
        )
        if rehydrate_cache:
            rehydrate_conversion_cache(rk)
            _emit_session_truth_log(
                "SESSION TRUTH REHYDRATED",
                kind="conversion",
                recovery_key=rk,
            )
        return True

    return False


def has_sent_truth(
    recovery_key: str,
    *,
    session_id: str = "",
    cart_id: Optional[str] = None,
    step: Optional[int] = None,
    rehydrate_cache: bool = True,
) -> bool:
    """
    True when durable evidence shows a recovery WhatsApp was sent for this session.

    Order: session cache → CartRecoveryLog mock_sent/sent_real.
    """
    rk = (recovery_key or "").strip()
    if not rk:
        return False

    if session_sent_cache_hit(rk):
        _emit_session_truth_log(
            "SESSION TRUTH CACHE HIT",
            kind="sent",
            recovery_key=rk,
        )
        return True

    _emit_session_truth_log(
        "SESSION TRUTH CACHE MISS",
        kind="sent",
        recovery_key=rk,
    )

    _slug, sid = parse_recovery_key(rk)
    sid_eff = (session_id or sid).strip()
    if _durable_sent_from_logs(
        recovery_key=rk,
        session_id=sid_eff,
        cart_id=cart_id,
        step=step,
    ):
        _emit_session_truth_log(
            "SESSION TRUTH DB FALLBACK",
            kind="sent",
            source="cart_recovery_log.sent",
            recovery_key=rk,
            step=step if step is not None else "-",
        )
        if rehydrate_cache:
            rehydrate_sent_cache(rk)
            _emit_session_truth_log(
                "SESSION TRUTH REHYDRATED",
                kind="sent",
                recovery_key=rk,
            )
        return True

    return False


__all__ = [
    "has_conversion_truth",
    "has_sent_truth",
    "parse_recovery_key",
    "rehydrate_conversion_cache",
    "rehydrate_sent_cache",
    "session_conversion_cache_hit",
    "session_sent_cache_hit",
]
