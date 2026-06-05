# -*- coding: utf-8 -*-
"""
Provider send timeout protection v1 — hard ceiling on outbound provider calls.

Applied at the Twilio messages.create boundary so workers never block indefinitely.
"""
from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

from twilio.http.http_client import TwilioHttpClient
from twilio.rest import Client

log = logging.getLogger(__name__)

DEFAULT_PROVIDER_SEND_TIMEOUT_SECONDS = 30.0
_MIN_TIMEOUT_SECONDS = 1.0
_MAX_TIMEOUT_SECONDS = 300.0
_MAX_EVENTS = 80

_provider_events_lock = __import__("threading").RLock()
_recent_provider_events: list[dict[str, Any]] = []

T = TypeVar("T")


def provider_send_timeout_seconds() -> float:
    """Configurable provider HTTP/send ceiling (seconds)."""
    raw = (
        os.getenv("PROVIDER_SEND_TIMEOUT_SECONDS")
        or os.getenv("TWILIO_PROVIDER_SEND_TIMEOUT_SECONDS")
        or ""
    ).strip()
    if not raw:
        return DEFAULT_PROVIDER_SEND_TIMEOUT_SECONDS
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_PROVIDER_SEND_TIMEOUT_SECONDS
    return max(_MIN_TIMEOUT_SECONDS, min(_MAX_TIMEOUT_SECONDS, val))


def build_twilio_client(account_sid: str, auth_token: str) -> Client:
    """Twilio client with HTTP-layer timeout aligned to provider_send_timeout_seconds."""
    timeout = provider_send_timeout_seconds()
    http_client = TwilioHttpClient(timeout=timeout)
    return Client(account_sid, auth_token, http_client=http_client)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _append_provider_event(entry: dict[str, Any]) -> None:
    with _provider_events_lock:
        _recent_provider_events.append(entry)
        while len(_recent_provider_events) > _MAX_EVENTS:
            _recent_provider_events.pop(0)


def log_provider_timeout(
    *,
    provider: str,
    recovery_key: Optional[str] = None,
    timeout_seconds: float,
) -> None:
    rk = (recovery_key or "-")[:120]
    prov = (provider or "unknown")[:32]
    ts = round(float(timeout_seconds), 1)
    try:
        print("[PROVIDER TIMEOUT]", flush=True)
        print(f"provider={prov}", flush=True)
        print(f"recovery_key={rk}", flush=True)
        print(f"timeout_seconds={ts}", flush=True)
    except OSError:
        pass
    log.warning(
        "[PROVIDER TIMEOUT] provider=%s recovery_key=%s timeout_seconds=%s",
        prov,
        rk,
        ts,
    )
    _append_provider_event(
        {
            "kind": "timeout",
            "provider": prov,
            "recovery_key": rk,
            "timeout_seconds": ts,
            "at_utc": _utc_now_iso(),
        }
    )


def log_provider_failure(
    *,
    provider: str,
    reason: str,
    recovery_key: Optional[str] = None,
) -> None:
    rk = (recovery_key or "-")[:120]
    prov = (provider or "unknown")[:32]
    rsn = (reason or "unknown")[:256]
    try:
        print("[PROVIDER FAILURE]", flush=True)
        print(f"provider={prov}", flush=True)
        print(f"reason={rsn}", flush=True)
    except OSError:
        pass
    log.warning(
        "[PROVIDER FAILURE] provider=%s reason=%s recovery_key=%s",
        prov,
        rsn,
        rk,
    )
    _append_provider_event(
        {
            "kind": "failure",
            "provider": prov,
            "reason": rsn,
            "recovery_key": rk,
            "at_utc": _utc_now_iso(),
        }
    )


def drain_recent_provider_send_events(limit: int = 50) -> list[dict[str, Any]]:
    """Read-only ring buffer for admin diagnostics (newest last)."""
    with _provider_events_lock:
        cap = max(1, min(int(limit), _MAX_EVENTS))
        return list(_recent_provider_events)[-cap:]


def clear_provider_send_events_for_tests() -> None:
    with _provider_events_lock:
        _recent_provider_events.clear()


def _is_timeout_exception(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    if isinstance(exc, (FuturesTimeout, TimeoutError)):
        return True
    msg = str(exc).lower()
    if "timeout" in name or "timed out" in msg or "timeout" in msg:
        return True
    try:
        import requests

        if isinstance(exc, requests.exceptions.Timeout):
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        import urllib3

        if isinstance(exc, urllib3.exceptions.TimeoutError):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def execute_provider_call_with_timeout(
    fn: Callable[[], T],
    *,
    provider: str,
    recovery_key: Optional[str] = None,
    timeout_seconds: Optional[float] = None,
) -> dict[str, Any]:
    """
    Run a blocking provider call with a hard timeout.

    Returns ``{ok: True, result: ...}`` or ``{ok: False, error: ..., ...}``.
    """
    timeout = (
        float(timeout_seconds)
        if timeout_seconds is not None
        else provider_send_timeout_seconds()
    )
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="provider-send")
    future = executor.submit(fn)
    try:
        result = future.result(timeout=timeout)
        return {"ok": True, "result": result}
    except FuturesTimeout:
        log_provider_timeout(
            provider=provider,
            recovery_key=recovery_key,
            timeout_seconds=timeout,
        )
        log_provider_failure(
            provider=provider,
            reason="provider_timeout",
            recovery_key=recovery_key,
        )
        _record_provider_timeout_anomaly(provider=provider)
        return {
            "ok": False,
            "error": "provider_timeout",
            "provider": (provider or "unknown")[:32],
            "timeout_seconds": round(timeout, 1),
            "failure_class": "provider_unavailable",
        }
    except Exception as exc:  # noqa: BLE001
        if _is_timeout_exception(exc):
            log_provider_timeout(
                provider=provider,
                recovery_key=recovery_key,
                timeout_seconds=timeout,
            )
            log_provider_failure(
                provider=provider,
                reason="provider_timeout",
                recovery_key=recovery_key,
            )
            _record_provider_timeout_anomaly(provider=provider)
            return {
                "ok": False,
                "error": "provider_timeout",
                "provider": (provider or "unknown")[:32],
                "timeout_seconds": round(timeout, 1),
                "failure_class": "provider_unavailable",
            }
        log_provider_failure(
            provider=provider,
            reason=str(exc)[:256],
            recovery_key=recovery_key,
        )
        _record_provider_failure_anomaly(provider=provider, detail=str(exc)[:200])
        return {
            "ok": False,
            "error": str(exc),
            "provider": (provider or "unknown")[:32],
        }
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def twilio_messages_create(
    client: Client,
    *,
    recovery_key: Optional[str] = None,
    **create_kwargs: Any,
) -> dict[str, Any]:
    """Twilio messages.create with timeout protection at the provider boundary."""

    def _call() -> Any:
        return client.messages.create(**create_kwargs)

    out = execute_provider_call_with_timeout(
        _call,
        provider="twilio",
        recovery_key=recovery_key,
    )
    if out.get("ok") is True:
        return {"ok": True, "msg": out.get("result")}
    return out


def _record_provider_timeout_anomaly(*, provider: str) -> None:
    try:
        from services.cartflow_runtime_health import (
            ANOMALY_PROVIDER_SEND_FAILURE,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_PROVIDER_SEND_FAILURE,
            source=(provider or "twilio")[:80],
            detail="provider_timeout",
        )
    except Exception:  # noqa: BLE001
        pass


def _record_provider_failure_anomaly(*, provider: str, detail: str) -> None:
    try:
        from services.cartflow_runtime_health import (
            ANOMALY_PROVIDER_SEND_FAILURE,
            record_runtime_anomaly,
        )

        record_runtime_anomaly(
            ANOMALY_PROVIDER_SEND_FAILURE,
            source=(provider or "twilio")[:80],
            detail=(detail or "provider_failure")[:200],
        )
    except Exception:  # noqa: BLE001
        pass


__all__ = [
    "DEFAULT_PROVIDER_SEND_TIMEOUT_SECONDS",
    "build_twilio_client",
    "clear_provider_send_events_for_tests",
    "drain_recent_provider_send_events",
    "execute_provider_call_with_timeout",
    "log_provider_failure",
    "log_provider_timeout",
    "provider_send_timeout_seconds",
    "twilio_messages_create",
]
