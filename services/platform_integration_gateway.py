# -*- coding: utf-8 -*-
"""
Platform integration gateway v1 — route normalized platform events into CartFlow Core.

Additive only: does not change recovery, WhatsApp, lifecycle, purchase truth, widget, or dashboard.
Not wired to production webhooks until a platform adapter is implemented.
"""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any, Optional

from integrations.normalized_platform_event import (
    EVENT_CART_ABANDONED,
    EVENT_CART_CREATED,
    EVENT_CART_UPDATED,
    EVENT_CHECKOUT_STARTED,
    EVENT_CUSTOMER_UPDATED,
    EVENT_ORDER_CANCELLED,
    EVENT_ORDER_CREATED,
    EVENT_ORDER_PAID,
    NORMALIZED_EVENT_TYPES,
    PURCHASE_TRUTH_EVENT_TYPES,
    NormalizedPlatformEvent,
)

log = logging.getLogger("cartflow")

_LOCK = threading.RLock()
_seen_external_events: set[str] = set()
_MAX_SEEN = 5000

# Per event_type: required NormalizedPlatformEvent fields (no guessing).
_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    EVENT_CART_ABANDONED: ("platform", "store_slug", "event_type"),
    EVENT_CART_CREATED: ("platform", "store_slug", "event_type"),
    EVENT_CART_UPDATED: ("platform", "store_slug", "event_type"),
    EVENT_CHECKOUT_STARTED: ("platform", "store_slug", "event_type"),
    EVENT_ORDER_CREATED: ("platform", "store_slug", "event_type"),
    EVENT_ORDER_PAID: ("platform", "store_slug", "event_type"),
    EVENT_ORDER_CANCELLED: ("platform", "store_slug", "event_type"),
    EVENT_CUSTOMER_UPDATED: ("platform", "store_slug", "event_type"),
}

# Identity: at least one external id for cart/order paths (do not invent).
_IDENTITY_FIELDS = ("external_cart_id", "external_customer_id", "external_order_id")


def clear_platform_integration_state_for_tests() -> None:
    with _LOCK:
        _seen_external_events.clear()


def _log_platform_line(tag: str, **fields: Any) -> None:
    parts = [tag]
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


def validate_minimum_fields(event: NormalizedPlatformEvent) -> list[str]:
    """Return missing required field names; empty list means valid."""
    missing: list[str] = []
    ev = (event.event_type or "").strip().lower()
    if ev not in NORMALIZED_EVENT_TYPES:
        missing.append("event_type")
        return missing
    for f in _REQUIRED_FIELDS.get(ev, ("platform", "store_slug", "event_type")):
        if not str(getattr(event, f, "") or "").strip():
            missing.append(f)
    if not (event.store_slug or "").strip():
        if "store_slug" not in missing:
            missing.append("store_slug")
    if not (event.platform or "").strip():
        if "platform" not in missing:
            missing.append("platform")
    # Cart/order/customer events need at least one external identity (no guessing).
    if ev in (
        EVENT_CART_ABANDONED,
        EVENT_CART_CREATED,
        EVENT_CART_UPDATED,
        EVENT_CHECKOUT_STARTED,
        EVENT_ORDER_CREATED,
        EVENT_ORDER_PAID,
        EVENT_ORDER_CANCELLED,
        EVENT_CUSTOMER_UPDATED,
    ):
        if not any(str(getattr(event, f, "") or "").strip() for f in _IDENTITY_FIELDS):
            missing.append("external_identity")
    return missing


def build_idempotency_key(event: NormalizedPlatformEvent) -> str:
    plat = (event.platform or "").strip().lower()[:32]
    store = (event.store_slug or "").strip().lower()[:255]
    ev = (event.event_type or "").strip().lower()[:64]
    cart = (event.external_cart_id or "").strip()[:255]
    order = (event.external_order_id or "").strip()[:255]
    cust = (event.external_customer_id or "").strip()[:255]
    t = (event.event_time or "").strip()[:64]
    return f"{plat}|{store}|{ev}|{cart}|{order}|{cust}|{t}"


def _mark_seen(key: str) -> bool:
    """Return True if first time seen; False if duplicate."""
    with _LOCK:
        if key in _seen_external_events:
            return False
        _seen_external_events.add(key)
        if len(_seen_external_events) > _MAX_SEEN:
            # Drop arbitrary oldest half (set order undefined — acceptable for v1 in-process).
            drop = list(_seen_external_events)[: _MAX_SEEN // 2]
            for k in drop:
                _seen_external_events.discard(k)
        return True


def normalized_event_to_core_payload(event: NormalizedPlatformEvent) -> dict[str, Any]:
    """Build dict shape understood by existing cart-event / purchase-truth paths."""
    session_id = (event.external_cart_id or "").strip()
    if not session_id and (event.external_customer_id or "").strip():
        session_id = f"platform:{event.platform}:{event.external_customer_id}"[:512]
    cart_id = (event.external_cart_id or "").strip() or None
    payload: dict[str, Any] = {
        "event": event.event_type,
        "store": event.store_slug,
        "store_slug": event.store_slug,
        "session_id": session_id,
        "platform": event.platform,
        "source": event.source or "platform_integration",
        "_platform_integration_v1": True,
        "_platform_idempotency_key": build_idempotency_key(event),
    }
    if cart_id:
        payload["cart_id"] = cart_id
    if event.external_order_id:
        payload["order_id"] = event.external_order_id
        payload["external_order_id"] = event.external_order_id
    if event.customer_phone:
        payload["phone"] = event.customer_phone
    if event.customer_email:
        payload["email"] = event.customer_email
    if event.cart_total is not None:
        payload["cart_total"] = event.cart_total
    if event.currency:
        payload["currency"] = event.currency
    if event.items:
        payload["cart"] = event.items
    if event.checkout_url:
        payload["checkout_url"] = event.checkout_url
    if event.event_type in PURCHASE_TRUTH_EVENT_TYPES:
        if event.event_type == EVENT_ORDER_PAID:
            payload["order_paid"] = True
        if event.event_type == EVENT_ORDER_CREATED:
            payload["order_created"] = True
    return payload


def _session_and_cart_from_event(event: NormalizedPlatformEvent) -> tuple[str, str]:
    core = normalized_event_to_core_payload(event)
    sid = str(core.get("session_id") or "").strip()
    cid = str(core.get("cart_id") or "").strip()
    return sid, cid


def _route_purchase_truth(core_payload: dict[str, Any]) -> dict[str, Any]:
    from services.purchase_truth import ingest_purchase_truth_payload

    key = ingest_purchase_truth_payload(core_payload)
    return {
        "ok": True,
        "routed": True,
        "target": "purchase_truth",
        "recovery_key": key,
        "applied": key is not None,
    }


def _route_customer_phone(event: NormalizedPlatformEvent, core_payload: dict[str, Any]) -> dict[str, Any]:
    phone = (event.customer_phone or "").strip()
    if not phone:
        _log_platform_line("[PLATFORM EVENT SKIPPED]", reason="no_phone_on_customer_path")
        return {"ok": True, "skipped": True, "reason": "no_phone", "target": "customer_phone"}
    try:
        from main import _recovery_key_from_payload  # noqa: PLC0415

        rk = _recovery_key_from_payload(core_payload)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"recovery_key:{exc}"}
    if not rk:
        return {"ok": False, "error": "missing_recovery_key"}
    from services.recovery_session_phone import record_recovery_customer_phone

    record_recovery_customer_phone(rk, phone, source="platform_integration")
    return {"ok": True, "routed": True, "target": "customer_phone", "recovery_key": rk}


def _route_checkout_started_future(event: NormalizedPlatformEvent) -> dict[str, Any]:
    """Lifecycle truth hook reserved — no lifecycle mutation in v1."""
    _log_platform_line(
        "[PLATFORM EVENT ROUTED]",
        target="lifecycle_truth_future_hook",
        event_type=event.event_type,
        store_slug=event.store_slug,
        platform=event.platform,
    )
    return {
        "ok": True,
        "routed": True,
        "target": "lifecycle_truth_future_hook",
        "note": "observation_only_v1",
    }


def _route_cart_abandoned(event: NormalizedPlatformEvent, core_payload: dict[str, Any]) -> dict[str, Any]:
    from services.cartflow_duplicate_guard import should_process_cart_event_burst

    sid, cid = _session_and_cart_from_event(event)
    if not should_process_cart_event_burst(
        store_slug=event.store_slug,
        session_id=sid,
        cart_id=cid,
        event_norm=EVENT_CART_ABANDONED,
    ):
        _log_platform_line(
            "[PLATFORM EVENT SKIPPED]",
            reason="duplicate_cart_event_burst",
            store_slug=event.store_slug,
        )
        return {"ok": True, "skipped": True, "reason": "duplicate_cart_event_burst"}

    try:
        from main import (  # noqa: PLC0415
            BackgroundTasks,
            _is_user_converted,
            _recovery_key_from_payload,
            handle_cart_abandoned,
        )

        rk = _recovery_key_from_payload(core_payload)
        if rk and _is_user_converted(rk):
            _log_platform_line(
                "[PLATFORM EVENT ROUTED]",
                target="cart_abandoned",
                note="converted_skip",
                recovery_key=rk[:80],
            )
            return {"ok": True, "routed": True, "target": "cart_abandoned", "note": "converted_skip"}

        bg = BackgroundTasks()

        async def _run() -> dict[str, Any]:
            return await handle_cart_abandoned(bg, core_payload)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Caller already in async context — schedule is not available here; sync fallback.
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    out = pool.submit(asyncio.run, _run()).result(timeout=120)
            else:
                out = loop.run_until_complete(_run())
        except RuntimeError:
            out = asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        log.warning("platform cart_abandoned route failed: %s", exc, exc_info=True)
        return {"ok": False, "error": str(exc)[:512], "target": "cart_abandoned"}

    _log_platform_line(
        "[PLATFORM EVENT ROUTED]",
        target="cart_abandoned",
        store_slug=event.store_slug,
        platform=event.platform,
    )
    return {"ok": True, "routed": True, "target": "cart_abandoned", "core_result": out}


def _route_cart_sync_light(event: NormalizedPlatformEvent, core_payload: dict[str, Any]) -> dict[str, Any]:
    """cart_created / cart_updated — DB upsert only, no recovery dispatch."""
    try:
        from main import upsert_abandoned_cart_from_payload  # noqa: PLC0415

        ok, err, _row = upsert_abandoned_cart_from_payload(core_payload)
        _log_platform_line(
            "[PLATFORM EVENT ROUTED]",
            target="cart_sync",
            event_type=event.event_type,
            ok=ok,
        )
        return {
            "ok": bool(ok),
            "routed": True,
            "target": "cart_sync",
            "error": err,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:512], "target": "cart_sync"}


def receive_normalized_event(event: NormalizedPlatformEvent) -> dict[str, Any]:
    """
    Entry point for adapter output → CartFlow Core.

    Logs: RECEIVED → NORMALIZED → ROUTED or SKIPPED.
    """
    _log_platform_line(
        "[PLATFORM EVENT RECEIVED]",
        platform=event.platform,
        store_slug=event.store_slug,
        event_type=event.event_type,
    )

    missing = validate_minimum_fields(event)
    if missing:
        _log_platform_line(
            "[PLATFORM EVENT SKIPPED]",
            reason="missing_required_field",
            fields=",".join(missing),
        )
        return {
            "ok": False,
            "skipped": True,
            "reason": "missing_required_field",
            "missing_fields": missing,
        }

    _log_platform_line(
        "[PLATFORM EVENT NORMALIZED]",
        platform=event.platform,
        event_type=event.event_type,
        confidence=event.confidence,
        source=event.source,
    )

    phone_present = bool((event.customer_phone or "").strip())
    if not phone_present:
        _log_platform_line("phone_present=false", event_type=event.event_type)

    idem = build_idempotency_key(event)
    if not _mark_seen(idem):
        _log_platform_line(
            "[PLATFORM EVENT SKIPPED]",
            reason="duplicate_external_event",
            idempotency_key=idem[:120],
        )
        return {
            "ok": True,
            "skipped": True,
            "reason": "duplicate_external_event",
            "idempotency_key": idem,
        }

    core_payload = normalized_event_to_core_payload(event)
    ev = (event.event_type or "").strip().lower()

    if ev == EVENT_CART_ABANDONED:
        return _route_cart_abandoned(event, core_payload)

    if ev in PURCHASE_TRUTH_EVENT_TYPES or ev == "checkout_completed":
        result = _route_purchase_truth(core_payload)
        _log_platform_line(
            "[PLATFORM EVENT ROUTED]",
            target="purchase_truth",
            event_type=ev,
            applied=result.get("applied"),
        )
        return result

    if ev == EVENT_CHECKOUT_STARTED:
        return _route_checkout_started_future(event)

    if ev in (EVENT_CART_CREATED, EVENT_CART_UPDATED):
        return _route_cart_sync_light(event, core_payload)

    if ev == EVENT_CUSTOMER_UPDATED:
        return _route_customer_phone(event, core_payload)

    if ev == EVENT_ORDER_CANCELLED:
        _log_platform_line(
            "[PLATFORM EVENT ROUTED]",
            target="observation_only",
            event_type=ev,
        )
        return {"ok": True, "routed": True, "target": "observation_only", "event_type": ev}

    _log_platform_line("[PLATFORM EVENT SKIPPED]", reason="unsupported_route", event_type=ev)
    return {"ok": False, "skipped": True, "reason": "unsupported_route", "event_type": ev}


def receive_from_adapter(
    adapter: Any,
    raw_payload: dict[str, Any],
    *,
    headers: Optional[dict[str, Any]] = None,
    raw_body: Optional[bytes] = None,
) -> dict[str, Any]:
    """Optional helper: adapter.normalize_event → gateway (signature not enforced in v1)."""
    normalized = adapter.normalize_event(raw_payload)
    if normalized is None:
        _log_platform_line(
            "[PLATFORM EVENT SKIPPED]",
            reason="adapter_normalize_returned_none",
            platform=getattr(adapter, "platform_id", "?"),
        )
        return {"ok": False, "skipped": True, "reason": "adapter_not_implemented"}
    return receive_normalized_event(normalized)
