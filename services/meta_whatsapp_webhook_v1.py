# -*- coding: utf-8 -*-
"""Meta WhatsApp Cloud API webhook verification and event diagnostics (v1)."""
from __future__ import annotations

import json
import logging
import os
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

log = logging.getLogger("cartflow")

_MAX_RECENT = 50
_lock = threading.Lock()

_state: dict[str, Any] = {
    "last_webhook_received_at": None,
    "last_webhook_raw": None,
    "last_delivered": None,
    "last_read": None,
    "last_inbound": None,
    "recent_events": deque(maxlen=_MAX_RECENT),
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_meta_webhook_verify_token() -> str:
    return (
        (os.getenv("META_WEBHOOK_VERIFY_TOKEN") or "").strip()
        or (os.getenv("WHATSAPP_WEBHOOK_VERIFY_TOKEN") or "").strip()
        or (os.getenv("WHATSAPP_META_WEBHOOK_VERIFY_TOKEN") or "").strip()
    )


def verify_subscription(
    hub_mode: str,
    hub_verify_token: str,
    hub_challenge: str,
) -> tuple[bool, str, Optional[str]]:
    """
    Meta webhook subscription verification.
    Returns (ok, error_code, challenge_to_return).
    """
    mode = (hub_mode or "").strip()
    token = (hub_verify_token or "").strip()
    challenge = (hub_challenge or "").strip()
    expected = read_meta_webhook_verify_token()

    if mode != "subscribe":
        return False, "invalid_hub_mode", None
    if not expected:
        return False, "verify_token_not_configured", None
    if token != expected:
        return False, "verify_token_mismatch", None
    if not challenge:
        return False, "missing_hub_challenge", None
    return True, "", challenge


def _safe_json_preview(obj: Any, limit: int = 4000) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)[:limit]
    except (TypeError, ValueError):
        return str(obj)[:limit]


def _append_event(kind: str, summary: dict[str, Any]) -> None:
    entry = {
        "kind": kind,
        "received_at": _utc_now_iso(),
        **summary,
    }
    with _lock:
        _state["recent_events"].appendleft(entry)


def _parse_status_event(status: dict[str, Any]) -> Optional[str]:
    st = str(status.get("status") or "").strip().lower()
    if st in ("delivered", "read"):
        return st
    return None


def _parse_inbound_message(msg: dict[str, Any]) -> Optional[dict[str, Any]]:
    msg_type = str(msg.get("type") or "").strip().lower()
    from_id = str(msg.get("from") or "").strip()
    message_id = str(msg.get("id") or "").strip()
    if not from_id and not message_id:
        return None

    text_body = ""
    if msg_type == "text":
        text_obj = msg.get("text")
        if isinstance(text_obj, dict):
            text_body = str(text_obj.get("body") or "").strip()
    elif msg_type == "button":
        btn = msg.get("button")
        if isinstance(btn, dict):
            text_body = str(btn.get("text") or btn.get("payload") or "").strip()
    elif msg_type == "interactive":
        inter = msg.get("interactive")
        if isinstance(inter, dict):
            br = inter.get("button_reply")
            if isinstance(br, dict):
                text_body = str(br.get("title") or br.get("id") or "").strip()

    return {
        "from": from_id or None,
        "message_id": message_id or None,
        "type": msg_type or None,
        "text": text_body or None,
        "timestamp": msg.get("timestamp"),
        "received_at": _utc_now_iso(),
    }


def process_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parse Meta webhook JSON, log diagnostics, store last events.
    Does not trigger recovery or merchant flows.
    """
    received_at = _utc_now_iso()
    parsed_counts = {"delivered": 0, "read": 0, "inbound": 0, "other_status": 0}

    with _lock:
        _state["last_webhook_received_at"] = received_at
        _state["last_webhook_raw"] = payload

    entries = payload.get("entry") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        log.info("[CF META WA WEBHOOK] received payload without entry list")
        _append_event("raw", {"note": "no_entry_list"})
        return {
            "ok": True,
            "received_at": received_at,
            "parsed_counts": parsed_counts,
        }

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue

            statuses = value.get("statuses")
            if isinstance(statuses, list):
                for status in statuses:
                    if not isinstance(status, dict):
                        continue
                    kind = _parse_status_event(status)
                    wamid = str(status.get("id") or "").strip()
                    summary = {
                        "wamid": wamid or None,
                        "status": status.get("status"),
                        "recipient_id": status.get("recipient_id"),
                        "timestamp": status.get("timestamp"),
                    }
                    if kind == "delivered":
                        parsed_counts["delivered"] += 1
                        with _lock:
                            _state["last_delivered"] = {
                                **summary,
                                "received_at": received_at,
                            }
                        log.info(
                            "[CF META WA WEBHOOK] event=delivered wamid=%s recipient=%s",
                            wamid,
                            summary.get("recipient_id"),
                        )
                        _append_event("delivered", summary)
                    elif kind == "read":
                        parsed_counts["read"] += 1
                        with _lock:
                            _state["last_read"] = {
                                **summary,
                                "received_at": received_at,
                            }
                        log.info(
                            "[CF META WA WEBHOOK] event=read wamid=%s recipient=%s",
                            wamid,
                            summary.get("recipient_id"),
                        )
                        _append_event("read", summary)
                    else:
                        parsed_counts["other_status"] += 1
                        log.info(
                            "[CF META WA WEBHOOK] event=status status=%s wamid=%s",
                            status.get("status"),
                            wamid,
                        )
                        _append_event("status_other", summary)

            messages = value.get("messages")
            if isinstance(messages, list):
                for msg in messages:
                    if not isinstance(msg, dict):
                        continue
                    inbound = _parse_inbound_message(msg)
                    if not inbound:
                        continue
                    parsed_counts["inbound"] += 1
                    with _lock:
                        _state["last_inbound"] = inbound
                    log.info(
                        "[CF META WA WEBHOOK] event=inbound_message from=%s wamid=%s text=%s",
                        inbound.get("from"),
                        inbound.get("message_id"),
                        _safe_json_preview(inbound.get("text"), 120),
                    )
                    _append_event("inbound_message", inbound)

    return {
        "ok": True,
        "received_at": received_at,
        "parsed_counts": parsed_counts,
    }


def get_webhook_diagnostics() -> dict[str, Any]:
    with _lock:
        recent = list(_state["recent_events"])
        return {
            "last_webhook_received_at": _state.get("last_webhook_received_at"),
            "last_delivered": _state.get("last_delivered"),
            "last_read": _state.get("last_read"),
            "last_inbound": _state.get("last_inbound"),
            "last_webhook_raw": _state.get("last_webhook_raw"),
            "recent_events": recent[:20],
            "verify_token_configured": bool(read_meta_webhook_verify_token()),
        }


def clear_webhook_state_for_tests() -> None:
    with _lock:
        _state["last_webhook_received_at"] = None
        _state["last_webhook_raw"] = None
        _state["last_delivered"] = None
        _state["last_read"] = None
        _state["last_inbound"] = None
        _state["recent_events"].clear()
