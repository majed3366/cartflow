# -*- coding: utf-8 -*-
"""طبقة ‎Layer D‎ — سبب ترك السلة من الودجت (بدون اشتراطات ‎reason‎ القديمة لـ‎ /api/cartflow/reason)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Request
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import CartRecoveryReason
from schema_widget import ensure_store_widget_schema

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/cart-recovery", tags=["cart-recovery"])

_MAX_REASON = 64
_MAX_CUSTOM = 20000


@router.post("/reason")
async def post_widget_cart_recovery_reason(request: Request) -> Any:
    """
    يخزّن آخر سبب من ودجت الاسترجاع؛ ‎reason_tag‎ حر نسبياً (مثل ‎price_high‎).
    يحدّث الصفّ لنفس ‎(store_slug, session_id)‎ إن وُجد.
    """
    try:
        ensure_store_widget_schema(db)
        db.create_all()
    except (OSError, SQLAlchemyError):
        db.session.rollback()
    try:
        body: Any
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        if not isinstance(body, dict):
            return j({"ok": False, "saved": False, "error": "json_object_required"}, 400)

        ss = (str(body.get("store_slug", "") or "")).strip()[:255]
        sid = (str(body.get("session_id", "") or "")).strip()[:512]
        tag_raw = body.get("reason_tag")
        reason_tag = (
            str(tag_raw).strip().lower()[:_MAX_REASON] if tag_raw is not None else ""
        )

        cr = body.get("custom_reason")
        custom_reason: Optional[str]
        if cr is None or str(cr).strip() == "":
            custom_reason = None
        else:
            custom_reason = str(cr).strip()[:_MAX_CUSTOM]

        if reason_tag == "other" and not custom_reason:
            return j(
                {"ok": False, "saved": False, "error": "custom_reason_required"}, 400
            )

        if custom_reason is not None and reason_tag != "other":
            return j({"ok": False, "saved": False, "error": "custom_not_other"}, 400)

        if not ss or not sid or not reason_tag:
            return j(
                {
                    "ok": False,
                    "saved": False,
                    "error": "store_slug_session_reason_required",
                },
                400,
            )

        now = datetime.now(timezone.utc)

        reason_phone_update: Optional[str] = None
        if "phone" in body:
            pr = body.get("phone")
            if pr is None or not str(pr).strip():
                reason_phone_update = None
            else:
                reason_phone_update = str(pr).strip()[:100]

        row = (
            db.session.query(CartRecoveryReason)
            .filter(
                and_(
                    CartRecoveryReason.store_slug == ss,
                    CartRecoveryReason.session_id == sid,
                )
            )
            .first()
        )

        sub_cat: Optional[str] = None
        if row is not None:
            row.reason = reason_tag
            row.sub_category = sub_cat
            row.custom_text = custom_reason
            row.source = "widget"
            row.updated_at = now
            if "phone" in body:
                row.customer_phone = reason_phone_update
        else:
            db.session.add(
                CartRecoveryReason(
                    store_slug=ss,
                    session_id=sid,
                    reason=reason_tag,
                    sub_category=sub_cat,
                    custom_text=custom_reason,
                    customer_phone=(
                        reason_phone_update if "phone" in body else None
                    ),
                    source="widget",
                    created_at=now,
                    updated_at=now,
                )
            )

        db.session.commit()
        print(
            f"[REASON SAVED] store={ss} session={sid} reason={reason_tag} custom={custom_reason}"
        )
        return j({"ok": True, "saved": True})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cart-recovery/reason widget: %s", e)
        return j({"ok": False, "saved": False, "error": "persist_failed"}, 500)
