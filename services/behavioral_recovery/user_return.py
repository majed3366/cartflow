# -*- coding: utf-8 -*-
"""Persist return-to-site on the cart row (in addition to in-memory anti-spam flag)."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from services.recovery_conversation_state_machine import (
    build_return_to_site_behavioral_patch,
)
from services.behavioral_recovery.state_store import (
    abandoned_carts_for_session_or_cart,
    behavioral_dict_for_abandoned_cart,
    merge_behavioral_state,
    utc_now_iso,
)

log = logging.getLogger("cartflow")


def _return_page_flags_from_payload(payload: dict[str, Any]) -> tuple[bool, bool]:
    rp = payload.get("returned_product_page") is True
    rc = payload.get("returned_checkout_page") is True
    ctx = str(
        payload.get("recovery_return_context")
        or payload.get("return_page")
        or payload.get("return_context")
        or ""
    ).strip().lower()
    if ctx in ("product", "product_page", "pdp", "item"):
        rp = True
    if ctx in ("checkout", "checkout_page", "payment", "pay"):
        rc = True
    return rp, rc


def record_behavioral_user_return_from_payload(payload: dict[str, Any]) -> None:
    """Mark behavioral user_returned_to_site when widget reports return (normal carts)."""
    if not isinstance(payload, dict):
        return
    sid = ""
    raw_sid = payload.get("session_id")
    if isinstance(raw_sid, str) and raw_sid.strip():
        sid = raw_sid.strip()[:512]
    cid_raw = payload.get("cart_id")
    cid = str(cid_raw).strip()[:255] if cid_raw is not None else ""
    if not sid and not cid:
        return
    returned_product_page, returned_checkout_page = _return_page_flags_from_payload(
        payload
    )
    rts = payload.get("return_timestamp")
    if isinstance(rts, str) and rts.strip():
        return_ts_iso = rts.strip()[:64]
    else:
        return_ts_iso = utc_now_iso()
    try:
        db.create_all()
        touched = False
        for ac in abandoned_carts_for_session_or_cart(sid, cid or None):
            if bool(getattr(ac, "vip_mode", False)):
                continue
            prior = behavioral_dict_for_abandoned_cart(ac)
            extra = build_return_to_site_behavioral_patch(
                prior,
                returned_product_page=returned_product_page,
                returned_checkout_page=returned_checkout_page,
                return_timestamp_iso=return_ts_iso,
                fuse_adaptive=True,
            )
            merge_behavioral_state(
                ac,
                user_returned_to_site=True,
                user_returned_at=utc_now_iso(),
                lifecycle_hint="returned",
                **extra,
            )
            db.session.add(ac)
            touched = True
        if touched:
            db.session.commit()
            line = (
                "[RECOVERY STOPPED USER RETURNED] "
                f"session_id={sid} cart_id={cid}"
            )
            print(line, flush=True)
            log.info("%s", line)
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("behavioral user return: %s", e, exc_info=True)
