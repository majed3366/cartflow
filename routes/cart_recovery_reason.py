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
from services.recovery_session_phone import (
    record_recovery_customer_phone,
    recovery_key_for_reason_session,
)

from services.normal_recovery_phone_persist import apply_normal_recovery_phone_to_session
from services.recovery_reason_preserve import PHONE_CAPTURE_REASON_VALUES
from services.cf_test_phone_override import (
    cf_test_customer_phone_override_allowed,
    normalize_cf_test_customer_phone,
    phone_matches_cartflow_demo_test_customer_phone,
)

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

        phone_from_cf_test = False
        _PHONE_OMIT = object()
        reason_phone_update: Any = _PHONE_OMIT
        if "phone" in body or "customer_phone" in body:
            pr = body["phone"] if "phone" in body else body.get("customer_phone")
            if pr is None or not str(pr).strip():
                reason_phone_update = None
            else:
                reason_phone_update = str(pr).strip()[:100]

        body_phone_nonempty = isinstance(reason_phone_update, str) and bool(
            reason_phone_update.strip()
        )

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

        cn = ""
        if cf_test_customer_phone_override_allowed(ss):
            ct_raw = body.get("cf_test_phone")
            if ct_raw is not None and str(ct_raw).strip():
                cn = normalize_cf_test_customer_phone(ct_raw) or ""

        if cn and not body_phone_nonempty:
            persisted = ""
            if row is not None:
                persisted = (getattr(row, "customer_phone", None) or "").strip()[:100]
            if persisted and not phone_matches_cartflow_demo_test_customer_phone(persisted):
                reason_phone_update = persisted
                phone_from_cf_test = False
                log.info(
                    "outbound_phone_source=real_customer_phone "
                    "detail=persisted_cart_recovery_reason_over_cf_test "
                    "session_id=%s store=%s",
                    sid[:80],
                    ss[:64],
                )
            else:
                reason_phone_update = cn[:100]
                phone_from_cf_test = True
                cid_log = (
                    str(body.get("cart_id") or body.get("zid_cart_id") or "").strip() or "-"
                )[:255]
                log.info(
                    "outbound_phone_source=demo_test_phone "
                    "[TEST CUSTOMER PHONE APPLIED] session_id=%s cart_id=%s customer_phone=%s",
                    sid[:80],
                    cid_log,
                    cn[:32],
                )
        elif cn and body_phone_nonempty:
            log.info(
                "outbound_phone_source=real_customer_phone "
                "detail=body_phone_overrides_cf_test session_id=%s store=%s",
                sid[:80],
                ss[:64],
            )

        sub_cat: Optional[str] = None
        if row is not None:
            prev_lc = (row.reason or "").strip().lower()
            preserve_objection = (
                reason_tag in PHONE_CAPTURE_REASON_VALUES
                and prev_lc
                and prev_lc not in PHONE_CAPTURE_REASON_VALUES
            )
            if preserve_objection:
                row.updated_at = now
                row.source = "widget"
                if reason_phone_update is not _PHONE_OMIT:
                    row.customer_phone = reason_phone_update
                log.info(
                    "[PHONE CAPTURE] store=%s session=%s preserved_reason=%s",
                    ss[:64],
                    sid[:64],
                    (row.reason or "")[:64],
                )
            else:
                row.reason = reason_tag
                row.sub_category = sub_cat
                row.custom_text = custom_reason
                row.source = "widget"
                row.updated_at = now
                if reason_tag == "no_help":
                    row.user_rejected_help = True
                    row.rejection_timestamp = now
                if reason_phone_update is not _PHONE_OMIT:
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
                        reason_phone_update
                        if reason_phone_update is not _PHONE_OMIT
                        else None
                    ),
                    source="widget",
                    created_at=now,
                    updated_at=now,
                    user_rejected_help=reason_tag == "no_help",
                    rejection_timestamp=now if reason_tag == "no_help" else None,
                )
            )

        db.session.flush()
        cart_id_raw = body.get("cart_id") or body.get("zid_cart_id")
        cid_apply: Optional[str] = None
        if cart_id_raw is not None and str(cart_id_raw).strip():
            cid_apply = str(cart_id_raw).strip()[:255]
        row_after = (
            db.session.query(CartRecoveryReason)
            .filter(
                and_(
                    CartRecoveryReason.store_slug == ss,
                    CartRecoveryReason.session_id == sid,
                )
            )
            .first()
        )
        ph_sync = (getattr(row_after, "customer_phone", None) or "").strip() if row_after else ""
        if ph_sync:
            persist_rt = (
                (getattr(row_after, "reason", None) or "").strip()[:_MAX_REASON]
                or reason_tag
            )
            _persist_src = (
                "demo_test_phone"
                if phone_from_cf_test
                or phone_matches_cartflow_demo_test_customer_phone(ph_sync)
                else "real_customer_phone"
            )
            apply_normal_recovery_phone_to_session(
                db.session,
                store_slug=ss,
                session_id=sid,
                cart_id=cid_apply,
                phone=ph_sync,
                reason_tag=persist_rt,
                phone_record_source=_persist_src,
            )

        db.session.commit()
        rk = recovery_key_for_reason_session(ss, sid)
        if reason_phone_update is not _PHONE_OMIT:
            _rk_phone = (
                reason_phone_update if isinstance(reason_phone_update, str) else None
            )
            _rk_src: Optional[str] = None
            if isinstance(reason_phone_update, str) and reason_phone_update.strip():
                _rk_src = (
                    "demo_test_phone"
                    if phone_from_cf_test
                    or phone_matches_cartflow_demo_test_customer_phone(reason_phone_update)
                    else "real_customer_phone"
                )
            record_recovery_customer_phone(rk, _rk_phone, source=_rk_src)
            if reason_phone_update:
                print("[PHONE ATTACHED]")
                print("session_id=", sid)
                print("phone=", reason_phone_update)
        stored_reason_log = (
            (getattr(row_after, "reason", None) or "").strip()
            if row_after is not None
            else reason_tag
        )
        print(
            f"[REASON SAVED] store={ss} session={sid} reason={stored_reason_log} custom={custom_reason}"
        )
        try:
            from main import _schedule_normal_recovery_after_cart_recovery_reason_saved

            await _schedule_normal_recovery_after_cart_recovery_reason_saved(
                store_slug=ss,
                session_id=sid,
                body=body,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("post-reason normal recovery reschedule hook skipped: %s", exc)

        resp_ok: dict[str, Any] = {"ok": True, "saved": True}
        if reason_tag == "no_help":
            resp_ok["user_rejected_help"] = True
        return j(resp_ok)
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cart-recovery/reason widget: %s", e)
        return j({"ok": False, "saved": False, "error": "persist_failed"}, 500)
