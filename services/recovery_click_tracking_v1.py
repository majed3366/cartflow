# -*- coding: utf-8 -*-
"""
Recovery checkout click tracking V1 — governed evidence only.

Records checkout_button_clicked RecoveryEvent.
Never marks recovered/purchased/completed.
Never blocks redirect (caller must fail-open).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from services.recovery_checkout_redirect_v1 import CheckoutRedirectClaims

log = logging.getLogger(__name__)

EVENT_TYPE_CHECKOUT_BUTTON_CLICKED = "checkout_button_clicked"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()[:24]


def _mask_destination(url: str) -> str:
    """Safe log fragment — host only."""
    try:
        from urllib.parse import urlparse

        host = (urlparse(url).netloc or "")[:80]
        return host or "—"
    except Exception:
        return "—"


def build_checkout_click_payload(
    *,
    claims: CheckoutRedirectClaims,
    redirect_token: str,
    user_agent: str = "",
    ip_address: str = "",
    referer: str = "",
    clicked_at: Optional[str] = None,
    is_duplicate: bool = False,
) -> dict[str, Any]:
    """Canonical evidence payload (destination kept for internal evidence only)."""
    return {
        "event": EVENT_TYPE_CHECKOUT_BUTTON_CLICKED,
        "recovery_key": (claims.recovery_key or "")[:120] or None,
        "template_name": (claims.template_name or "")[:128] or None,
        "clicked_at": clicked_at or _utc_now_iso(),
        "destination_url": claims.destination_url,
        "redirect_token_fingerprint": _token_fingerprint(redirect_token),
        "message_id": (claims.message_id or "")[:128] or None,
        "store_slug": (claims.store_slug or "")[:255] or None,
        "customer_phone": (claims.customer_phone or "")[:40] or None,
        "user_agent": (user_agent or "")[:500] or None,
        "ip_address": (ip_address or "")[:64] or None,
        "referer": (referer or "")[:500] or None,
        "provider": (claims.provider or "")[:32] or None,
        "provider_message_id": (claims.provider_message_id or "")[:128] or None,
        "legacy_token": bool(claims.legacy),
        "is_duplicate_click": bool(is_duplicate),
        # Explicit non-claims — evidence only
        "purchase_inferred": False,
        "recovered_inferred": False,
        "completed_inferred": False,
    }


def record_checkout_button_click(
    *,
    claims: CheckoutRedirectClaims,
    redirect_token: str,
    user_agent: str = "",
    ip_address: str = "",
    referer: str = "",
    allow_duplicate: bool = True,
) -> dict[str, Any]:
    """
    Persist checkout_button_clicked evidence.

    Returns safe summary (never includes destination_url).
    On any failure returns ok=False — caller must still redirect.
    """
    fp = _token_fingerprint(redirect_token)
    try:
        from extensions import db
        from models import RecoveryEvent

        db.create_all()

        is_duplicate = False
        if not allow_duplicate and claims.recovery_key:
            # Best-effort: if an identical fingerprint already exists for this recovery, mark duplicate
            prior = (
                db.session.query(RecoveryEvent)
                .filter(RecoveryEvent.event_type == EVENT_TYPE_CHECKOUT_BUTTON_CLICKED)
                .order_by(RecoveryEvent.id.desc())
                .limit(25)
                .all()
            )
            for row in prior:
                try:
                    body = json.loads(row.payload or "{}")
                except (TypeError, ValueError):
                    continue
                if not isinstance(body, dict):
                    continue
                if body.get("redirect_token_fingerprint") == fp:
                    is_duplicate = True
                    break

        payload = build_checkout_click_payload(
            claims=claims,
            redirect_token=redirect_token,
            user_agent=user_agent,
            ip_address=ip_address,
            referer=referer,
            is_duplicate=is_duplicate,
        )
        row = RecoveryEvent(
            event_type=EVENT_TYPE_CHECKOUT_BUTTON_CLICKED,
            payload=json.dumps(payload, ensure_ascii=False)[:65000],
        )
        db.session.add(row)
        db.session.commit()
        event_id = int(row.id) if row.id is not None else None
        line = (
            f"[CHECKOUT CLICK] event={EVENT_TYPE_CHECKOUT_BUTTON_CLICKED} "
            f"recovery_key={(claims.recovery_key or '-')[:64]} "
            f"store_slug={(claims.store_slug or '-')[:64]} "
            f"token_fp={fp} dest_host={_mask_destination(claims.destination_url)} "
            f"duplicate={is_duplicate} event_id={event_id or '-'}"
        )
        try:
            print(line, flush=True)
        except OSError:
            pass
        log.info("%s", line)
        return {
            "ok": True,
            "event_type": EVENT_TYPE_CHECKOUT_BUTTON_CLICKED,
            "event_id": event_id,
            "recovery_key": claims.recovery_key or None,
            "is_duplicate_click": is_duplicate,
            "purchase_inferred": False,
            "redirect_token_fingerprint": fp,
        }
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[CHECKOUT CLICK] persist_failed err=%s recovery_key=%s",
            type(exc).__name__,
            (claims.recovery_key or "-")[:64],
        )
        try:
            from extensions import db as _db

            _db.session.rollback()
        except Exception:
            pass
        return {
            "ok": False,
            "error": "click_persist_failed",
            "event_type": EVENT_TYPE_CHECKOUT_BUTTON_CLICKED,
            "purchase_inferred": False,
            "redirect_token_fingerprint": fp,
        }


__all__ = [
    "EVENT_TYPE_CHECKOUT_BUTTON_CLICKED",
    "build_checkout_click_payload",
    "record_checkout_button_click",
]
