# -*- coding: utf-8 -*-
"""تجربة Product Intelligence: جلسة نظيفة (حذف سجلات تجريبية + معرفات جديدة + سبب ‎price_high‎)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import quote

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import (
    AbandonedCart,
    AbandonmentReasonLog,
    CartRecoveryLog,
    CartRecoveryReason,
    MessageLog,
    MerchantFollowupAction,
    RecoveryEvent,
    Store,
)
from schema_widget import ensure_store_widget_schema
from services.cf_test_phone_override import (
    cf_test_customer_phone_override_allowed,
    normalize_cf_test_customer_phone,
)
from services.normal_recovery_phone_persist import apply_normal_recovery_phone_to_session
from services.recovery_session_phone import (
    record_recovery_customer_phone,
    recovery_key_for_reason_session,
)

log = logging.getLogger("cartflow")

_DEMO_SLUGS = frozenset({"demo", "demo2"})


def _new_demo_session_id() -> str:
    return "s_" + str(uuid.uuid4())


def _new_demo_cart_id() -> str:
    return "cf_cart_" + str(uuid.uuid4())


def _pn_match(db_val: Optional[str], target_norm: str) -> bool:
    if not target_norm:
        return False
    if db_val is None or not str(db_val).strip():
        return False
    return normalize_cf_test_customer_phone(db_val) == target_norm


def purge_demo_recovery_rows_for_test_phone(
    store_slug: str, cf_test_phone: str
) -> dict[str, int]:
    """حذف صفوف الاسترجاع المرتبطة برقم الاختبار فقط (متجر ‎demo|demo2‎)."""
    ss = (store_slug or "").strip()[:255]
    pn = normalize_cf_test_customer_phone(cf_test_phone)
    counts: dict[str, int] = {}
    if ss not in _DEMO_SLUGS or not pn:
        return counts

    try:
        st = (
            db.session.query(Store)
            .filter(Store.zid_store_id == ss)
            .first()
        )
        store_id: Optional[int] = int(st.id) if st is not None else None

        session_ids: set[str] = set()
        cart_ids: set[str] = set()

        for r in (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.store_slug == ss)
            .all()
        ):
            if _pn_match(getattr(r, "customer_phone", None), pn):
                sid = (getattr(r, "session_id", None) or "").strip()[:512]
                if sid:
                    session_ids.add(sid)

        for row in (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == ss)
            .all()
        ):
            if _pn_match(getattr(row, "phone", None), pn):
                s = (getattr(row, "session_id", None) or "").strip()[:512]
                c = (getattr(row, "cart_id", None) or "").strip()[:255]
                if s:
                    session_ids.add(s)
                if c:
                    cart_ids.add(c)

        abandoned_ids: set[int] = set()
        if store_id is not None:
            ac_rows = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.store_id == store_id)
                .all()
            )
            for ac in ac_rows:
                if _pn_match(getattr(ac, "customer_phone", None), pn):
                    abandoned_ids.add(int(ac.id))
                    continue
                rs = (getattr(ac, "recovery_session_id", None) or "").strip()[:512]
                zi = (getattr(ac, "zid_cart_id", None) or "").strip()[:255]
                if rs and rs in session_ids:
                    abandoned_ids.add(int(ac.id))
                elif zi and zi in cart_ids:
                    abandoned_ids.add(int(ac.id))

        if abandoned_ids:
            n = (
                db.session.query(MessageLog)
                .filter(MessageLog.abandoned_cart_id.in_(abandoned_ids))
                .delete(synchronize_session=False)
            )
            counts["message_logs"] = int(n or 0)
            n = (
                db.session.query(RecoveryEvent)
                .filter(RecoveryEvent.abandoned_cart_id.in_(abandoned_ids))
                .delete(synchronize_session=False)
            )
            counts["recovery_events"] = int(n or 0)
            n = (
                db.session.query(MerchantFollowupAction)
                .filter(MerchantFollowupAction.abandoned_cart_id.in_(abandoned_ids))
                .delete(synchronize_session=False)
            )
            counts["merchant_followup_actions"] = int(n or 0)
            n = (
                db.session.query(AbandonedCart)
                .filter(AbandonedCart.id.in_(abandoned_ids))
                .delete(synchronize_session=False)
            )
            counts["abandoned_carts"] = int(n or 0)

        n_logs = 0
        for row in (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == ss)
            .all()
        ):
            if _pn_match(getattr(row, "phone", None), pn):
                db.session.delete(row)
                n_logs += 1
        counts["cart_recovery_logs"] = n_logs

        n_reason = 0
        for row in (
            db.session.query(CartRecoveryReason)
            .filter(CartRecoveryReason.store_slug == ss)
            .all()
        ):
            if _pn_match(getattr(row, "customer_phone", None), pn):
                db.session.delete(row)
                n_reason += 1
        counts["cart_recovery_reasons"] = n_reason

        if session_ids:
            n = (
                db.session.query(AbandonmentReasonLog)
                .filter(AbandonmentReasonLog.store_slug == ss)
                .filter(AbandonmentReasonLog.session_id.in_(session_ids))
                .delete(synchronize_session=False)
            )
            counts["abandonment_reason_logs"] = int(n or 0)

        db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("purge_demo_recovery_rows_for_test_phone: %s", e)
        raise
    return counts


def apply_demo_pi_fresh_start(
    *,
    store_slug: str,
    cf_test_phone: str,
    purge_database: bool = True,
) -> dict[str, Any]:
    """
    جلسة جديدة لاختبار ذكاء المنتج: معرفات جديدة + ‎CartRecoveryReason‎ بـ‎price_high‎ ورقم الاختبار.
    يُسمح فقط لمتاجر ‎demo|demo2‎ مع مسار ‎cf_test_phone‎ المفعّل لذلك المتجر.
    """
    ss = (store_slug or "").strip()[:255]
    phone_raw = (cf_test_phone or "").strip()
    if ss not in _DEMO_SLUGS:
        return {"ok": False, "error": "invalid_store"}
    if not phone_raw:
        return {"ok": False, "error": "cf_test_phone_required"}
    if not cf_test_customer_phone_override_allowed(ss):
        return {"ok": False, "error": "cf_test_override_not_allowed"}
    pn = normalize_cf_test_customer_phone(phone_raw)
    if not pn:
        return {"ok": False, "error": "invalid_cf_test_phone"}

    purge_counts: dict[str, int] = {}
    try:
        ensure_store_widget_schema(db)
        db.create_all()
    except (OSError, SQLAlchemyError):
        db.session.rollback()

    if purge_database:
        try:
            purge_counts = purge_demo_recovery_rows_for_test_phone(ss, phone_raw)
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            return {"ok": False, "error": "purge_failed"}

    sid = _new_demo_session_id()
    cid = _new_demo_cart_id()
    now = datetime.now(timezone.utc)
    ph100 = pn[:100]

    try:
        existing = (
            db.session.query(CartRecoveryReason)
            .filter(
                CartRecoveryReason.store_slug == ss,
                CartRecoveryReason.session_id == sid,
            )
            .first()
        )
        if existing is not None:
            db.session.delete(existing)
            db.session.flush()

        db.session.add(
            CartRecoveryReason(
                store_slug=ss,
                session_id=sid,
                reason="price_high",
                sub_category=None,
                custom_text=None,
                customer_phone=ph100,
                source="widget",
                created_at=now,
                updated_at=now,
                user_rejected_help=False,
                rejection_timestamp=None,
            )
        )
        db.session.flush()
        apply_normal_recovery_phone_to_session(
            db.session,
            store_slug=ss,
            session_id=sid,
            cart_id=cid,
            phone=ph100,
            reason_tag="price_high",
            phone_record_source="demo_test_phone",
        )
        rk = recovery_key_for_reason_session(ss, sid)
        record_recovery_customer_phone(rk, ph100, source="demo_test_phone")
        db.session.commit()
    except (SQLAlchemyError, OSError, TypeError, ValueError) as e:
        db.session.rollback()
        log.warning("apply_demo_pi_fresh_start: %s", e)
        return {"ok": False, "error": "persist_failed"}

    dash = (
        f"/dashboard/normal-carts?nr_session={quote(sid, safe='')}"
        f"&nr_cart={quote(cid, safe='')}&nr_lifecycle=active"
    )
    return {
        "ok": True,
        "store_slug": ss,
        "session_id": sid,
        "cart_id": cid,
        "purge_counts": purge_counts,
        "normal_dashboard_url": dash,
    }


def merge_demo_pi_fresh_query_into_context(request: Any, ctx: dict[str, Any]) -> dict[str, Any]:
    """عند ‎?fresh=1‎ و‎cf_test_phone‎: يُنفّذ إعادة التعيين على الخادم ويُمرّر المعرفات للقالب."""
    try:
        qp = getattr(request, "query_params", None)
    except Exception:  # noqa: BLE001
        qp = None
    if qp is None:
        return ctx
    fresh = str(qp.get("fresh") or "").strip().lower()
    if fresh not in ("1", "true", "yes"):
        return ctx
    slug = str(ctx.get("demo_store_slug") or "demo").strip()
    phone = str(qp.get("cf_test_phone") or "").strip()
    res = apply_demo_pi_fresh_start(
        store_slug=slug,
        cf_test_phone=phone,
        purge_database=True,
    )
    if res.get("ok"):
        ctx["demo_pi_fresh_applied"] = True
        ctx["demo_pi_fresh_session_id"] = res["session_id"]
        ctx["demo_pi_fresh_cart_id"] = res["cart_id"]
        ctx["demo_pi_fresh_normal_dashboard_url"] = res.get("normal_dashboard_url", "")
        ctx["demo_pi_fresh_purge_counts"] = res.get("purge_counts", {})
    else:
        ctx["demo_pi_fresh_error"] = res.get("error", "failed")
    return ctx
