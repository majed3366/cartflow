# -*- coding: utf-8 -*-
"""Signed short links for recovery clicks — optional when CARTFLOW_PUBLIC_BASE_URL is set."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
from typing import Optional, Tuple
from urllib.parse import quote

from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AbandonedCart
from services.behavioral_recovery.state_store import merge_behavioral_state, utc_now_iso

log = logging.getLogger("cartflow")

_LINK_SECRET_ENV = "CARTFLOW_LINK_SIGNING_SECRET"


def _link_signing_secret() -> bytes:
    raw = (
        os.getenv(_LINK_SECRET_ENV) or os.getenv("SECRET_KEY") or "cartflow-dev-link"
    ).encode("utf-8")
    return raw


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_decode(seg: str) -> Optional[bytes]:
    try:
        pad = "=" * (-len(seg) % 4)
        return base64.urlsafe_b64decode((seg + pad).encode("ascii"))
    except (TypeError, ValueError, OSError):
        return None


def sign_recovery_click_token(cart_id: str, session_id: str) -> str:
    cid = (cart_id or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    payload = json.dumps(
        {"c": cid, "s": sid},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    body_b64 = _b64url(payload)
    sig = hmac.new(
        _link_signing_secret(), body_b64.encode("ascii"), hashlib.sha256
    ).hexdigest()[:20]
    return f"{body_b64}.{sig}"


def verify_recovery_click_token(token: str) -> Optional[Tuple[str, str]]:
    t = (token or "").strip()
    if "." not in t:
        return None
    body_b64, sig = t.rsplit(".", 1)
    want = hmac.new(
        _link_signing_secret(), body_b64.encode("ascii"), hashlib.sha256
    ).hexdigest()[:20]
    if not hmac.compare_digest(want, sig):
        return None
    raw = _b64url_decode(body_b64)
    if raw is None:
        return None
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict):
        return None
    c = str(obj.get("c") or "").strip()[:255]
    s = str(obj.get("s") or "").strip()[:512]
    if not c and not s:
        return None
    return c, s


def public_app_base_url() -> str:
    return (
        (os.getenv("CARTFLOW_PUBLIC_BASE_URL") or os.getenv("PUBLIC_BASE_URL") or "")
        .strip()
        .rstrip("/")
    )


def build_recovery_tracking_url(cart_id: str, session_id: str) -> Optional[str]:
    base = public_app_base_url()
    if not base:
        return None
    tok = sign_recovery_click_token(cart_id, session_id)
    return f"{base}/api/recover/r?t={quote(tok, safe='')}"


def inject_tracking_url_into_message(
    message: str,
    *,
    cart_url: Optional[str],
    tracking_url: Optional[str],
) -> str:
    if not tracking_url:
        return message
    msg = (message or "").rstrip()
    cu = (cart_url or "").strip()
    if cu and cu in msg:
        return msg.replace(cu, tracking_url, 1)
    if tracking_url in msg:
        return msg
    return f"{msg}\n\n{tracking_url}"


def apply_outbound_tracking_to_message(
    message: str,
    *,
    cart_id: Optional[str],
    session_id: str,
) -> str:
    cid = (str(cart_id).strip()[:255] if cart_id else "") or ""
    sid = (session_id or "").strip()[:512]
    if not cid or not sid:
        return message
    track = build_recovery_tracking_url(cid, sid)
    if not track:
        return message
    cart_url: Optional[str] = None
    try:
        db.create_all()
        row = (
            db.session.query(AbandonedCart.cart_url)
            .filter(AbandonedCart.zid_cart_id == cid)
            .order_by(AbandonedCart.last_seen_at.desc())
            .first()
        )
        if row is not None and row[0]:
            cart_url = str(row[0]).strip() or None
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        db.session.rollback()
    return inject_tracking_url_into_message(
        message, cart_url=cart_url, tracking_url=track
    )


def handle_recovery_link_click(token: str) -> RedirectResponse:
    parsed = verify_recovery_click_token(token)
    if parsed is None:
        return RedirectResponse(url="https://zid.sa/", status_code=302)
    cid, sid = parsed
    target = "https://zid.sa/"
    try:
        db.create_all()
        q = db.session.query(AbandonedCart).filter(AbandonedCart.vip_mode.is_(False))
        ac = None
        if cid:
            ac = (
                q.filter(AbandonedCart.zid_cart_id == cid)
                .order_by(AbandonedCart.last_seen_at.desc())
                .first()
            )
        if ac is None and sid:
            ac = (
                q.filter(AbandonedCart.recovery_session_id == sid)
                .order_by(AbandonedCart.last_seen_at.desc())
                .first()
            )
        if ac is not None:
            cu = getattr(ac, "cart_url", None)
            if isinstance(cu, str) and cu.strip():
                target = cu.strip()[:2048]
            merge_behavioral_state(
                ac,
                recovery_link_clicked=True,
                last_clicked_at=utc_now_iso(),
                lifecycle_hint="clicked",
            )
            db.session.add(ac)
            db.session.commit()
        line = f"[RECOVERY LINK CLICKED] session_id={sid} cart_id={cid}"
        print(line, flush=True)
        log.info("%s", line)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("recovery link click: %s", e, exc_info=True)
    return RedirectResponse(url=target, status_code=302)
