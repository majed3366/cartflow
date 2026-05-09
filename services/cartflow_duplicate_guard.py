# -*- coding: utf-8 -*-
"""
Centralized duplicate prevention bookkeeping for CartFlow (in-process, deterministic).

Does not change WhatsApp payloads, decision engine, VIP paths, or provider integration.
Logs use the canonical prefix ‎[CARTFLOW DUPLICATE]‎ for operational correlation.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import Any

log = logging.getLogger("cartflow")

PREFIX_DUPLICATE = "[CARTFLOW DUPLICATE]"

# Duplicate-specific anomaly symbols (distinct from core runtime_health symbols where useful)
ANOMALY_DUPLICATE_ACTIVE_RECOVERY = "duplicate_active_recovery"
ANOMALY_DUPLICATE_BEHAVIORAL_MERGE = "duplicate_behavioral_merge"
ANOMALY_DUPLICATE_DASHBOARD_PAYLOAD = "duplicate_dashboard_payload_state"

_LOCK = threading.Lock()

# Monotonic timestamps for TTL windows
_inflight_send: dict[str, float] = {}
_cart_event_last: dict[str, float] = {}
_behavioral_return_last: dict[str, float] = {}

# Simple rolling window for “blocked recently” (seconds ago, monotonic)
_blocked_send_ts: deque[float] = deque(maxlen=200)

_DASH_PAYLOAD_THROTTLE: dict[str, float] = {}

_counters: dict[str, int] = {
    "recovery_schedule_duplicate": 0,
    "send_duplicate_blocked": 0,
    "send_inflight_blocked": 0,
    "behavioral_merge_idempotent_skip": 0,
    "cart_event_spam_suppressed": 0,
    "lifecycle_conflict_logged": 0,
    "sequential_slot_duplicate": 0,
    "dashboard_payload_conflict": 0,
}


def _emit_duplicate_line(dup_type: str, **fields: Any) -> None:
    dt = (dup_type or "").strip()[:80] or "unknown"
    parts = [PREFIX_DUPLICATE, f"type={dt}"]
    for k in sorted(fields.keys()):
        key = str(k).strip()[:48]
        if not key:
            continue
        val = fields[k]
        sval = "-" if val is None else str(val).strip().replace("\n", " ")[:256]
        parts.append(f"{key}={sval}")
    line = " ".join(parts)
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.info("%s", line)


def canonical_recovery_schedule_signature(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
) -> str:
    ss = (store_slug or "").strip()[:128] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    cid = (cart_id or "").strip()[:255] or "-"
    return f"sched:{ss}|{sid}|{cid}"


def canonical_recovery_send_signature(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    attempt_index: int,
) -> str:
    ss = (store_slug or "").strip()[:128] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    cid = (cart_id or "").strip()[:255] or "-"
    try:
        step = int(attempt_index)
    except (TypeError, ValueError):
        step = 0
    return f"send:{ss}|{sid}|{cid}|step={step}"


def behavioral_return_merge_signature(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    return_ts_iso: str,
    returned_product_page: bool,
    returned_checkout_page: bool,
    context_tail: str,
) -> str:
    ss = (store_slug or "").strip()[:128] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    cid = (cart_id or "").strip()[:255] or "-"
    rts = (return_ts_iso or "").strip()[:64] or "-"
    ctx = (context_tail or "").strip()[:64] or "-"
    return (
        f"beh_ret:{ss}|{sid}|{cid}|ts={rts}|rp={int(bool(returned_product_page))}"
        f"|rc={int(bool(returned_checkout_page))}|ctx={ctx}"
    )


def note_recovery_schedule_duplicate(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    recovery_key: str,
) -> None:
    with _LOCK:
        _counters["recovery_schedule_duplicate"] = (
            int(_counters.get("recovery_schedule_duplicate", 0)) + 1
        )
    sig = canonical_recovery_schedule_signature(
        store_slug=store_slug, session_id=session_id, cart_id=cart_id or ""
    )
    _emit_duplicate_line(
        "recovery_schedule_duplicate",
        recovery_signature=sig,
        recovery_key=(recovery_key or "").strip()[:800] or "-",
    )
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_DUPLICATE_ACTIVE_RECOVERY,
            source="duplicate_guard",
            detail="recovery_schedule_duplicate",
        )
    except Exception:
        pass


def note_send_duplicate_blocked(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    attempt_index: int,
    reason: str,
    recovery_key: str = "",
) -> None:
    with _LOCK:
        _counters["send_duplicate_blocked"] = (
            int(_counters.get("send_duplicate_blocked", 0)) + 1
        )
        _blocked_send_ts.append(time.monotonic())
    sig = canonical_recovery_send_signature(
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id or "",
        attempt_index=attempt_index,
    )
    _emit_duplicate_line(
        "send_duplicate_blocked",
        recovery_signature=sig,
        reason=(reason or "").strip()[:120] or "-",
        attempt_index=str(int(attempt_index)),
        recovery_key=(recovery_key or "").strip()[:800] or "-",
    )
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            ANOMALY_DUPLICATE_SEND_ATTEMPT,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_DUPLICATE_SEND_ATTEMPT,
            source="duplicate_guard",
            detail=(reason or "").strip()[:120] or "send_duplicate_blocked",
        )
    except Exception:
        pass


def note_sequential_recovery_slot_duplicate(
    *,
    recovery_key: str,
    slot_kind: str,
    slot_detail: str,
) -> None:
    with _LOCK:
        _counters["sequential_slot_duplicate"] = (
            int(_counters.get("sequential_slot_duplicate", 0)) + 1
        )
    _emit_duplicate_line(
        "recovery_slot_duplicate",
        recovery_key=(recovery_key or "").strip()[:800] or "-",
        slot_kind=(slot_kind or "").strip()[:40] or "-",
        slot_detail=(slot_detail or "").strip()[:120] or "-",
    )


def try_begin_outbound_whatsapp_inflight(
    recovery_key: str,
    step_num: int,
    *,
    ttl_seconds: float = 6.0,
) -> bool:
    """
    Returns True if this coroutine may proceed to provider send; False if overlapping
    in-flight send for the same recovery key + step (retry / double-task window).
    """
    rk = (recovery_key or "").strip()[:800]
    try:
        st = int(step_num)
    except (TypeError, ValueError):
        st = 0
    sk = f"{rk}:step:{st}"
    now = time.monotonic()
    ttl = max(0.5, float(ttl_seconds))
    with _LOCK:
        exp = _inflight_send.get(sk)
        if exp is not None and exp > now:
            _counters["send_inflight_blocked"] = (
                int(_counters.get("send_inflight_blocked", 0)) + 1
            )
            _blocked_send_ts.append(now)
            _emit_duplicate_line(
                "send_duplicate_blocked",
                subtype="inflight_overlap",
                recovery_key=rk or "-",
                attempt_index=str(st),
            )
            try:
                from services.cartflow_runtime_health import (  # noqa: PLC0415
                    ANOMALY_DUPLICATE_SEND_ATTEMPT,
                    record_runtime_anomaly,
                )

                record_runtime_anomaly(
                    ANOMALY_DUPLICATE_SEND_ATTEMPT,
                    source="duplicate_guard",
                    detail="inflight_send_overlap",
                )
            except Exception:
                pass
            return False
        _inflight_send[sk] = now + ttl
        # opportunistic prune of expired keys
        dead = [k for k, t in _inflight_send.items() if t <= now]
        for k in dead[:50]:
            _inflight_send.pop(k, None)
    return True


def release_outbound_whatsapp_inflight(recovery_key: str, step_num: int) -> None:
    rk = (recovery_key or "").strip()[:800]
    try:
        st = int(step_num)
    except (TypeError, ValueError):
        st = 0
    sk = f"{rk}:step:{st}"
    with _LOCK:
        _inflight_send.pop(sk, None)


def should_process_cart_event_burst(
    *,
    store_slug: str,
    session_id: str,
    cart_id: str,
    event_norm: str,
    min_interval_seconds: float = 0.85,
) -> bool:
    """
    Returns False when the same store/session/cart/event fires faster than min_interval
    (browser refresh / double-submit spam) — caller should no-op after logging.
    """
    ss = (store_slug or "").strip()[:128] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    cid = (cart_id or "").strip()[:255] or "-"
    ev = (event_norm or "").strip()[:64] or "-"
    key = f"{ss}|{sid}|{cid}|{ev}"
    now = time.monotonic()
    gap = max(0.1, float(min_interval_seconds))
    with _LOCK:
        last = _cart_event_last.get(key)
        if last is not None and (now - last) < gap:
            _counters["cart_event_spam_suppressed"] = (
                int(_counters.get("cart_event_spam_suppressed", 0)) + 1
            )
            _emit_duplicate_line(
                "cart_event_duplicate_suppressed",
                store_slug=ss,
                session_id=sid[:64] + ("…" if len(sid) > 64 else ""),
                cart_id=cid[:48] + ("…" if len(cid) > 48 else ""),
                event=ev,
            )
            return False
        _cart_event_last[key] = now
        old = [k for k, t in _cart_event_last.items() if now - t > 120.0]
        for k in old[:80]:
            _cart_event_last.pop(k, None)
    return True


def try_consume_behavioral_return_merge(
    *,
    signature: str,
    ttl_seconds: float = 45.0,
) -> bool:
    """
    Returns True if merge should proceed; False if the same signature was applied
    recently (idempotent skip — no DB writes).
    """
    sig = (signature or "").strip()[:900]
    if not sig:
        return True
    now = time.monotonic()
    ttl = max(1.0, float(ttl_seconds))
    with _LOCK:
        last_t = _behavioral_return_last.get(sig)
        if last_t is not None and (now - last_t) < ttl:
            _counters["behavioral_merge_idempotent_skip"] = (
                int(_counters.get("behavioral_merge_idempotent_skip", 0)) + 1
            )
            _emit_duplicate_line(
                "duplicate_behavioral_merge",
                behavioral_signature=sig[:200],
            )
            try:
                from services.cartflow_runtime_health import (  # noqa: PLC0415
                    record_runtime_anomaly,
                )

                record_runtime_anomaly(
                    ANOMALY_DUPLICATE_BEHAVIORAL_MERGE,
                    source="duplicate_guard",
                    detail="behavioral_return_idempotent",
                )
            except Exception:
                pass
            return False
        _behavioral_return_last[sig] = now
        stale = [k for k, t in _behavioral_return_last.items() if now - t > ttl * 4]
        for k in stale[:80]:
            _behavioral_return_last.pop(k, None)
    return True


def log_lifecycle_conflict_pattern(
    pattern: str,
    *,
    recovery_key: str = "",
    session_id: str = "",
    cart_id: str = "",
    step: int | str = "",
    detail: str = "",
) -> None:
    """Diagnostics only — does not mutate recovery state."""
    pat = (pattern or "").strip()[:80] or "unknown"
    with _LOCK:
        _counters["lifecycle_conflict_logged"] = (
            int(_counters.get("lifecycle_conflict_logged", 0)) + 1
        )
    _emit_duplicate_line(
        "lifecycle_conflict",
        pattern=pat,
        recovery_key=(recovery_key or "").strip()[:800] or "-",
        session_id=(session_id or "").strip()[:64] or "-",
        cart_id=(cart_id or "").strip()[:48] or "-",
        step=str(step),
        detail=(detail or "").strip()[:160] or "-",
    )


def note_dashboard_payload_state_conflict(
    *,
    reason_code: str,
    session_id: str = "",
    cart_id: str = "",
    throttle_seconds: float = 90.0,
) -> None:
    rc = (reason_code or "").strip()[:120] or "-"
    sid = (session_id or "").strip()[:128] or "-"
    cid = (cart_id or "").strip()[:128] or "-"
    key = f"{sid}|{cid}|{rc}"
    now = time.monotonic()
    th = max(5.0, float(throttle_seconds))
    with _LOCK:
        last = _DASH_PAYLOAD_THROTTLE.get(key)
        if last is not None and (now - last) < th:
            return
        _DASH_PAYLOAD_THROTTLE[key] = now
        stale = [k for k, t in _DASH_PAYLOAD_THROTTLE.items() if now - t > th * 24]
        for k in stale[:48]:
            _DASH_PAYLOAD_THROTTLE.pop(k, None)
        _counters["dashboard_payload_conflict"] = (
            int(_counters.get("dashboard_payload_conflict", 0)) + 1
        )
    _emit_duplicate_line(
        "duplicate_dashboard_payload_state",
        reason_code=(reason_code or "").strip()[:120] or "-",
        session_id=(session_id or "").strip()[:64] or "-",
        cart_id=(cart_id or "").strip()[:48] or "-",
    )
    try:
        from services.cartflow_runtime_health import (  # noqa: PLC0415
            ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_DASHBOARD_PAYLOAD_CONFLICT,
            source="duplicate_guard",
            detail=(reason_code or "").strip()[:120] or "payload_state",
        )
    except Exception:
        pass


def duplicate_send_blocked_recently(*, within_seconds: float = 300.0) -> bool:
    """True if a duplicate send was blocked in the recent monotonic window."""
    now = time.monotonic()
    win = max(1.0, float(within_seconds))
    with _LOCK:
        for ts in reversed(_blocked_send_ts):
            if now - ts <= win:
                return True
    return False


def get_duplicate_guard_diagnostics_readonly() -> dict[str, Any]:
    with _LOCK:
        counters = dict(_counters)
        inflight_n = len(_inflight_send)
    blocked_recent = duplicate_send_blocked_recently(within_seconds=300.0)
    return {
        "counters": counters,
        "inflight_send_keys": inflight_n,
        "duplicate_send_blocked_recently": bool(blocked_recent),
        "duplicate_prevention_runtime_ok": bool(inflight_n < 50000),
    }


def reset_duplicate_guard_for_tests() -> None:
    with _LOCK:
        _inflight_send.clear()
        _cart_event_last.clear()
        _behavioral_return_last.clear()
        _blocked_send_ts.clear()
        _DASH_PAYLOAD_THROTTLE.clear()
        for k in list(_counters.keys()):
            _counters[k] = 0
