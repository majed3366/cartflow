# -*- coding: utf-8 -*-
"""واجهات ‎CartFlow‎ للوحة (تحليلات الاسترجاع) وسبب ترك السلة (ودجت)."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Path, Query, Request
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import AbandonmentReasonLog, CartRecoveryLog, CartRecoveryReason, Store
from schema_widget import ensure_store_widget_schema
from services.cartflow_whatsapp_mock import (
    build_mock_whatsapp_message,
    get_merchant_whatsapp_e164_for_store,
)
from services.decision_engine import VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY
from services.recovery_decision import (
    get_primary_recovery_reason,
    resolve_auto_whatsapp_reason,
)
from services.store_template_control import (
    exit_intent_template_fields_for_api,
    template_control_fields_for_api,
)
from services.recovery_session_phone import (
    record_recovery_customer_phone,
    recovery_key_for_reason_session,
)
from services.cartflow_widget_recovery_gate import (
    cartflow_widget_recovery_gate_fields_for_api,
)
from services.cartflow_widget_trigger_settings import widget_trigger_config_for_api
from services.store_widget_customization import widget_customization_fields_for_api
from services.vip_cart import is_vip_cart, vip_cart_threshold_fields_for_api
from services.vip_abandoned_cart_phone import (
    apply_vip_phone_capture_to_abandoned_carts,
    resolve_store_row_for_cartflow_slug,
)
from services.normal_recovery_phone_persist import apply_normal_recovery_phone_to_session
from services.recovery_reason_preserve import (
    PHONE_CAPTURE_REASON_VALUES,
    effective_cart_recovery_reason_row_value,
)

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/cartflow", tags=["cartflow"])


REASON_CHOICES = frozenset(
    {
        "price",
        "quality",
        "warranty",
        "shipping",
        "thinking",
        "other",
        "human_support",
        "vip_phone_capture",
    }
)

VIP_PHONE_CAPTURE_MARKER = "vip_cart_phone_capture"

# فرع ‎السعر‎: يُلزم مع ‎reason=price‎
PRICE_SUB_CATEGORIES = frozenset(
    {
        "price_discount_request",
        "price_budget_issue",
        "price_cheaper_alternative",
    }
)


SENT_STATUSES = frozenset({"sent_real", "mock_sent"})


def _normalize_sa_mobile_cartflow_customer(raw: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    مدخلات عميل سعودية: ‎05XXXXXXXX‎ أو ‎9665XXXXXXXX‎ → ‎9665XXXXXXXX‎.
    يُعيد ‎(رقم مسطّح،‎ None)؛ أو ‎(None,‎ None)‎ إن فارغ؛ أو ‎(None,‎ 'invalid_customer_phone')‎ إن موجود لكن غير صالح.
    """
    if raw is None:
        return None, None
    s = str(raw).strip()
    if not s:
        return None, None
    d = "".join(c for c in s if c.isdigit())
    if len(d) == 10 and d.startswith("05"):
        d = "966" + d[1:]
    elif len(d) == 9 and d.startswith("5"):
        d = "966" + d
    if re.fullmatch(r"9665\d{8}", d):
        return d, None
    return None, "invalid_customer_phone"


def compute_recovery_analytics(store_slug: str) -> dict[str, Any]:
    """
    نفس تجميعات ‎GET /api/cartflow/analytics/{store_slug}‎ (بدون ‎ok / revenue‎).
    ‎store_slug‎ مُطبَّع كما في المسار.
    """
    ss = (store_slug or "").strip()[:255]
    if not ss:
        raise ValueError("empty store slug")
    db.create_all()
    base = db.session.query(CartRecoveryLog).filter(CartRecoveryLog.store_slug == ss)

    total_attempts = base.count()
    sent_real = base.filter(CartRecoveryLog.status == "sent_real").count()
    failed_final = base.filter(CartRecoveryLog.status == "failed_final").count()
    stopped_converted = base.filter(
        CartRecoveryLog.status == "stopped_converted"
    ).count()

    steps: dict[str, dict[str, int]] = {}
    for n, key in ((1, "step1"), (2, "step2"), (3, "step3")):
        sub = base.filter(CartRecoveryLog.step == n)
        sent = sub.filter(CartRecoveryLog.status.in_(SENT_STATUSES)).count()
        conv = sub.filter(CartRecoveryLog.status == "stopped_converted").count()
        steps[key] = {"sent": sent, "converted": conv}

    return {
        "store_slug": ss,
        "total_attempts": total_attempts,
        "sent_real": sent_real,
        "failed_final": failed_final,
        "stopped_converted": stopped_converted,
        "steps": steps,
    }


@router.get("/analytics/{store_slug}")
def get_recovery_analytics(
    store_slug: str = Path(..., min_length=1, max_length=255, description="معرّف المتجر"),
) -> Any:
    """
    مقاييس أداء الاسترجاع من ‎CartRecoveryLog‎ (لكل ‎status‎ / ‎step‎).
    """
    ss = (store_slug or "").strip()[:255]
    if not ss:
        return j({"ok": False, "error": "store_slug_required"}, 400)

    try:
        data = compute_recovery_analytics(ss)
        return j(
            {
                "ok": True,
                **data,
                "revenue_recovered": 0.0,
            }
        )
    except (ValueError, SQLAlchemyError) as e:
        db.session.rollback()
        log.warning("cartflow analytics: %s", e)
        if isinstance(e, ValueError):
            return j({"ok": False, "error": "store_slug_required"}, 400)
        return j({"ok": False, "error": "query_failed"}, 500)


def _ready_after_step1(store_slug: str, session_id: str) -> bool:
    ss = (store_slug or "").strip()[:255]
    sid = (session_id or "").strip()[:512]
    if not ss or not sid:
        return False
    base = (
        db.session.query(CartRecoveryLog)
        .filter(CartRecoveryLog.store_slug == ss, CartRecoveryLog.session_id == sid)
        .filter(
            CartRecoveryLog.step == 1,
            CartRecoveryLog.status.in_(SENT_STATUSES),
        )
    )
    return base.first() is not None


@router.get("/primary-recovery-reason")
def primary_recovery_reason(
    store_slug: str = Query(..., min_length=1, max_length=255),
) -> Any:
    """
    أكثر ‎reason‎ تكراراً لمتجر (لوحة ‎CartRecoveryReason‎) — للودجت قبل بناء نص واتساب.
    """
    try:
        db.create_all()
        ss = (store_slug or "").strip()[:255]
        if not ss:
            return j({"ok": False, "error": "store_slug_required"}, 400)
        pr = get_primary_recovery_reason(ss)
        if not pr or pr not in REASON_CHOICES:
            pr = "price"
        return j({"ok": True, "primary_reason": pr})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("primary-recovery-reason: %s", e)
        return j({"ok": True, "primary_reason": "price"})


@router.post("/generate-whatsapp-message")
async def post_generate_whatsapp_message(request: Request) -> Any:
    """
    نص ‎Mock‎ لمتابعة واتساب حسب ‎reason‎ / ‎sub_category‎ (لا إرسال ولا ‎DB‎).
    """
    try:
        body: Any
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        if not isinstance(body, dict):
            return j({"ok": False, "error": "json_object_required"}, 400)
        ss = (str(body.get("store_slug", "")) or "").strip()[:255]
        sid = (str(body.get("session_id", "")) or "").strip()[:512]
        reason_raw = (str(body.get("reason", "")) or "").strip().lower()[:32]
        is_auto = reason_raw == "auto"
        sub_raw = body.get("sub_category")
        sub_cat: Optional[str] = None
        if not is_auto and sub_raw is not None and (str(sub_raw) or "").strip():
            sub_cat = (str(sub_raw) or "").strip()[:64]
        p_name = body.get("product_name")
        p_price = body.get("product_price")
        c_url = body.get("cart_url")
        name_s = (str(p_name) if p_name is not None else "") or ""
        price_s = (str(p_price) if p_price is not None else "") or ""
        url_s = (str(c_url) if c_url is not None else "") or ""
        if not ss or not sid:
            return j({"ok": False, "error": "store_slug_session_required"}, 400)
        vip_row = resolve_store_row_for_cartflow_slug(ss)
        ct_try = body.get("cart_total")
        if vip_row is not None and ct_try is not None:
            try:
                ct_f = float(ct_try)
                if is_vip_cart(ct_f, vip_row):
                    return j(
                        {
                            "ok": True,
                            "message": VIP_CUSTOMER_WHATSAPP_NEUTRAL_BODY,
                            "reason": "vip_neutral_followup",
                            "sub_category": None,
                            "resolved_reason": "vip_neutral_followup",
                            "resolved_sub_category": None,
                            "primary_reason_log": "vip_neutral_followup",
                            "used_dashboard_primary": False,
                            "merchant_whatsapp_e164": get_merchant_whatsapp_e164_for_store(
                                ss
                            ),
                        }
                    )
            except (TypeError, ValueError):
                pass
        used_analytics = False
        if is_auto:
            reason, sub_cat, primary_log, used_analytics = resolve_auto_whatsapp_reason(
                ss
            )
        else:
            reason = reason_raw
            if not reason or reason not in REASON_CHOICES:
                return j({"ok": False, "error": "invalid_reason"}, 400)
            if reason == "price":
                if not sub_cat or sub_cat not in PRICE_SUB_CATEGORIES:
                    return j(
                        {"ok": False, "error": "sub_category_required_or_invalid"},
                        400,
                    )
            else:
                if sub_cat is not None:
                    return j({"ok": False, "error": "sub_category_not_applicable"}, 400)
            primary_log = reason
        try:
            msg = build_mock_whatsapp_message(
                reason=reason,
                sub_category=sub_cat,
                product_name=name_s.strip() or None,
                product_price=price_s.strip() or None,
                cart_url=url_s.strip() or None,
            )
        except ValueError as e:
            err = (str(e) or "").strip() or "invalid"
            return j({"ok": False, "error": err}, 400)
        return j(
            {
                "ok": True,
                "message": msg,
                "reason": reason,
                "sub_category": sub_cat,
                "resolved_reason": reason,
                "resolved_sub_category": sub_cat,
                "primary_reason_log": primary_log,
                "used_dashboard_primary": bool(is_auto and used_analytics),
                "merchant_whatsapp_e164": get_merchant_whatsapp_e164_for_store(ss),
            }
        )
    except (OSError, TypeError) as e:
        log.warning("generate whatsapp message: %s", e)
        return j({"ok": False, "error": "failed"}, 500)


@router.get("/ready")
def cartflow_ready(
    store_slug: str = Query(..., min_length=1, max_length=255),
    session_id: str = Query(..., min_length=1, max_length=512),
) -> Any:
    """
    ‎true‎ عند تسجيل ‎step1‎ استرجاع واتساب (مرسَل/وهمي) لنفس ‎store_slug + session_id‎.

    الجسم يتضمن حقول النمط والودجيت للعرض الأمامي، منها:
    ‎widget_name‎، ‎widget_primary_color‎، ‎widget_style‎ (مع باقي حقول القوالب).
    """
    try:
        ensure_store_widget_schema(db)
    except (OSError, SQLAlchemyError):
        db.session.rollback()
    try:
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        tpl = template_control_fields_for_api(row)
        tpl.update(exit_intent_template_fields_for_api(row))
        tpl.update(widget_customization_fields_for_api(row))
        tpl.update(vip_cart_threshold_fields_for_api(row))
        tpl.update(cartflow_widget_recovery_gate_fields_for_api(row))
        tpl.update(widget_trigger_config_for_api(row))
        return j(
            {
                "ok": True,
                "after_step1": _ready_after_step1(store_slug, session_id),
                **tpl,
            }
        )
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow ready: %s", e)
        return j({"ok": False, "error": "query_failed"}, 500)


@router.get("/public-config")
def cartflow_public_config(
    store_slug: str = Query(..., min_length=1, max_length=255),
    cart_total: Optional[float] = Query(None),
) -> Any:
    """
    لودجت السبب: رابط واتساب الدعم (أحدث ‎Store‎) — ‎store_slug‎ محجوز للمطابقة لاحقاً.
    اختياري: ‎cart_total‎ لتحديد ‎is_vip‎ حسب نفس قاعدة الخادم (‎is_vip_cart‎).
    """
    _ = (store_slug or "").strip()[:255]
    try:
        from main import _ensure_default_store_for_recovery  # type: ignore  # runtime; يتجنب دورة

        ensure_store_widget_schema(db)
        db.create_all()
        _ensure_default_store_for_recovery()
    except (OSError, SQLAlchemyError):
        db.session.rollback()
    try:
        row = db.session.query(Store).order_by(Store.id.desc()).first()
        wa: Optional[str] = None
        if row is not None:
            w = getattr(row, "whatsapp_support_url", None)
            if isinstance(w, str) and w.strip():
                wa = w.strip()[:2048]
        tpl = template_control_fields_for_api(row)
        tpl.update(exit_intent_template_fields_for_api(row))
        tpl.update(widget_customization_fields_for_api(row))
        tpl.update(vip_cart_threshold_fields_for_api(row))
        tpl.update(cartflow_widget_recovery_gate_fields_for_api(row))
        tpl.update(widget_trigger_config_for_api(row))
        ct_out: Optional[float] = None
        is_vip_pub = False
        vip_eval = False
        if cart_total is not None:
            vip_eval = True
            try:
                ct_out = float(cart_total)
                is_vip_pub = bool(is_vip_cart(ct_out, row))
            except (TypeError, ValueError):
                ct_out = None
                is_vip_pub = False
        return j(
            {
                "ok": True,
                "whatsapp_url": wa,
                "cart_total": ct_out,
                "is_vip": is_vip_pub,
                "vip_from_cart_total": vip_eval,
                **tpl,
            }
        )
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow public-config: %s", e)
        return j({"ok": False, "error": "query_failed", "whatsapp_url": None}, 500)


@router.post("/reason")
async def post_abandonment_reason(request: Request) -> Any:
    """
    يسجّل سبب التردد من الودجت. الأجسام: ‎store_slug, session_id, reason، ‎
    ‎custom_text‎ اختياري لـ ‎other‎؛ ‎customer_phone‎ (‎05‎ / ‎9665‎…) لـ ‎other‎ مع توسيع القديم (‎custom_text‎ وحده لا يزال مقبولاً).
    """
    try:
        ensure_store_widget_schema(db)
    except (OSError, SQLAlchemyError):
        db.session.rollback()
    try:
        body: Any
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = None
        if not isinstance(body, dict):
            return j({"ok": False, "error": "json_object_required"}, 400)
        ss = (str(body.get("store_slug", "")) or "").strip()[:255]
        sid = (str(body.get("session_id", "")) or "").strip()[:512]
        reason = (str(body.get("reason", "")) or "").strip().lower()[:32]
        sub_raw = body.get("sub_category")
        sub_cat: Optional[str] = None
        if sub_raw is not None and (str(sub_raw) or "").strip():
            sub_cat = (str(sub_raw) or "").strip()[:64]
        custom_raw = body.get("custom_text")
        if not ss or not sid or not reason:
            return j({"ok": False, "error": "store_slug_session_reason_required"}, 400)
        if reason not in REASON_CHOICES:
            return j({"ok": False, "error": "invalid_reason"}, 400)
        if reason == "price":
            if not sub_cat or sub_cat not in PRICE_SUB_CATEGORIES:
                return j(
                    {
                        "ok": False,
                        "error": "sub_category_required_or_invalid",
                    },
                    400,
                )
        else:
            if sub_cat is not None:
                return j({"ok": False, "error": "sub_category_not_applicable"}, 400)

        phone_norm: Optional[str] = None
        phone_raw = body.get("customer_phone")
        if reason == "vip_phone_capture":
            if phone_raw is None or not isinstance(phone_raw, str):
                return j({"ok": False, "error": "customer_phone_required"}, 400)
            if not phone_raw.strip():
                return j({"ok": False, "error": "customer_phone_required"}, 400)
            pn, err = _normalize_sa_mobile_cartflow_customer(phone_raw)
            if err or pn is None:
                return j({"ok": False, "error": "invalid_customer_phone"}, 400)
            phone_norm = pn
        elif phone_raw is not None:
            if not isinstance(phone_raw, str):
                return j({"ok": False, "error": "invalid_customer_phone_payload"}, 400)
            pn, err = _normalize_sa_mobile_cartflow_customer(phone_raw)
            if reason == "other":
                if err or pn is None:
                    if not phone_raw.strip():
                        phone_norm = None
                    else:
                        return j({"ok": False, "error": "invalid_customer_phone"}, 400)
                else:
                    phone_norm = pn
            else:
                if err or pn is None:
                    phone_norm = None
                else:
                    phone_norm = pn

        if phone_norm:
            cf_sid = sid[:512] if sid else "-"
            cf_r = (reason or "-")[:32]
            cf_p = phone_norm
            log.info(
                "[CF PHONE RECEIVED] session_id=%s reason=%s customer_phone=%s",
                cf_sid,
                cf_r,
                cf_p,
            )
            print(
                "[CF PHONE RECEIVED]\n"
                "session_id=" + cf_sid + "\n"
                "reason=" + cf_r + "\n"
                "customer_phone=" + cf_p,
                flush=True,
            )

        custom: Optional[str] = None
        if reason == "vip_phone_capture":
            cts = (str(custom_raw) if custom_raw is not None else "").strip()
            if cts != VIP_PHONE_CAPTURE_MARKER:
                return j({"ok": False, "error": "custom_text_invalid_vip_capture"}, 400)
            custom = VIP_PHONE_CAPTURE_MARKER
        elif reason in ("other", "human_support"):
            c = (
                (str(custom_raw) if custom_raw is not None else "")
                or ""
            ).strip()[:20000]
            if reason == "other" and not c and not phone_norm:
                return j({"ok": False, "error": "custom_text_required"}, 400)
            custom = c if c else None
        elif custom_raw is not None and (str(custom_raw) or "").strip():
            return j({"ok": False, "error": "custom_text_not_applicable"}, 400)
        sub_for_row: Optional[str] = sub_cat if reason == "price" else None
        row = AbandonmentReasonLog(
            store_slug=ss,
            session_id=sid,
            reason=reason,
            sub_category=sub_for_row,
            custom_text=custom,
        )
        db.session.add(row)
        now = datetime.now(timezone.utc)
        crr = (
            db.session.query(CartRecoveryReason)
            .filter(
                and_(
                    CartRecoveryReason.store_slug == ss,
                    CartRecoveryReason.session_id == sid,
                )
            )
            .first()
        )
        prev_crr_phone = (
            (getattr(crr, "customer_phone", None) or "").strip()[:100]
            if crr is not None
            else ""
        )
        if phone_norm:
            crr_phone: Optional[str] = phone_norm[:100]
        elif prev_crr_phone:
            crr_phone = prev_crr_phone
        else:
            crr_phone = None
        if crr is not None:
            prev_reason_lc = (crr.reason or "").strip().lower()
            if (
                reason in PHONE_CAPTURE_REASON_VALUES
                and prev_reason_lc
                and prev_reason_lc not in PHONE_CAPTURE_REASON_VALUES
            ):
                stored_reason = effective_cart_recovery_reason_row_value(
                    incoming_reason=reason,
                    existing_reason=crr.reason,
                )
                crr.reason = stored_reason[:32]
                crr.customer_phone = crr_phone
                crr.updated_at = now
                log.info(
                    "[PHONE CAPTURE] session_id=%s incoming=%s preserved_reason=%s",
                    (sid or "")[:64],
                    reason,
                    (crr.reason or "")[:64],
                )
            else:
                crr.reason = reason
                crr.sub_category = sub_for_row
                crr.custom_text = custom
                crr.customer_phone = crr_phone
                crr.updated_at = now
        else:
            db.session.add(
                CartRecoveryReason(
                    store_slug=ss,
                    session_id=sid,
                    reason=reason,
                    customer_phone=crr_phone,
                    sub_category=sub_for_row,
                    custom_text=custom,
                    source="legacy_api",
                    created_at=now,
                    updated_at=now,
                )
            )
        if reason == "vip_phone_capture" and phone_norm:
            apply_vip_phone_capture_to_abandoned_carts(
                store_slug=ss,
                recovery_session_id=sid,
                normalized_phone=phone_norm,
            )
        db.session.flush()
        cart_id_raw = body.get("cart_id") or body.get("zid_cart_id")
        cid_apply: Optional[str] = None
        if cart_id_raw is not None and str(cart_id_raw).strip():
            cid_apply = str(cart_id_raw).strip()[:255]
        crr_row = (
            db.session.query(CartRecoveryReason)
            .filter(
                and_(
                    CartRecoveryReason.store_slug == ss,
                    CartRecoveryReason.session_id == sid,
                )
            )
            .first()
        )
        ph_sync = (getattr(crr_row, "customer_phone", None) or "").strip() if crr_row else ""
        if ph_sync:
            persist_rt = (
                (getattr(crr_row, "reason", None) or "").strip()[:64] or reason
            )
            apply_normal_recovery_phone_to_session(
                db.session,
                store_slug=ss,
                session_id=sid,
                cart_id=cid_apply,
                phone=ph_sync,
                reason_tag=persist_rt,
            )
        db.session.commit()
        if phone_norm:
            cf_sid2 = sid[:512] if sid else "-"
            log.info(
                "[CF PHONE SAVED] session_id=%s customer_phone=%s",
                cf_sid2,
                phone_norm,
            )
            print(
                "[CF PHONE SAVED]\n"
                "session_id=" + cf_sid2 + "\n"
                "customer_phone=" + phone_norm,
                flush=True,
            )
        if phone_norm:
            record_recovery_customer_phone(
                recovery_key_for_reason_session(ss, sid),
                phone_norm,
                source="real_customer_phone",
            )
        if reason == "vip_phone_capture" and phone_norm:
            try:
                from services.vip_abandoned_cart_phone import (
                    resolve_store_row_for_cartflow_slug,
                    vip_cart_value_for_recovery_session,
                )
                from services.vip_merchant_alert import (
                    try_send_vip_phone_capture_merchant_alert,
                )

                sto = resolve_store_row_for_cartflow_slug(ss)
                cart_val = vip_cart_value_for_recovery_session(ss, sid)
                try_send_vip_phone_capture_merchant_alert(
                    sto,
                    cart_total=cart_val,
                    customer_phone=phone_norm,
                )
            except Exception as alert_err:  # noqa: BLE001
                log.warning(
                    "vip_phone_capture merchant whatsapp: %s",
                    alert_err,
                    exc_info=True,
                )
        return j({"ok": True})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow reason: %s", e)
        return j({"ok": False, "error": "persist_failed"}, 500)
