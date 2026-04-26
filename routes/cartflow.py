# -*- coding: utf-8 -*-
"""واجهات ‎CartFlow‎ للوحة (تحليلات الاسترجاع) وسبب ترك السلة (ودجت)."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Path, Query, Request
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import AbandonmentReasonLog, CartRecoveryLog, Store
from schema_widget import ensure_store_widget_schema

log = logging.getLogger("cartflow")

router = APIRouter(prefix="/api/cartflow", tags=["cartflow"])


REASON_CHOICES = frozenset(
    {"price", "quality", "warranty", "shipping", "thinking", "other", "human_support"}
)


SENT_STATUSES = frozenset({"sent_real", "mock_sent"})


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


@router.get("/ready")
def cartflow_ready(
    store_slug: str = Query(..., min_length=1, max_length=255),
    session_id: str = Query(..., min_length=1, max_length=512),
) -> Any:
    """
    ‎true‎ عند تسجيل ‎step1‎ استرجاع واتساب (مرسَل/وهمي) لنفس ‎store_slug + session_id‎.
    """
    try:
        ensure_store_widget_schema(db)
    except (OSError, SQLAlchemyError):
        db.session.rollback()
    try:
        return j(
            {
                "ok": True,
                "after_step1": _ready_after_step1(store_slug, session_id),
            }
        )
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow ready: %s", e)
        return j({"ok": False, "error": "query_failed"}, 500)


@router.get("/public-config")
def cartflow_public_config(
    store_slug: str = Query(..., min_length=1, max_length=255),
) -> Any:
    """
    لودجت السبب: رابط واتساب الدعم (أحدث ‎Store‎) — ‎store_slug‎ محجوز للمطابقة لاحقاً.
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
        return j({"ok": True, "whatsapp_url": wa})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow public-config: %s", e)
        return j({"ok": False, "error": "query_failed", "whatsapp_url": None}, 500)


@router.post("/reason")
async def post_abandonment_reason(request: Request) -> Any:
    """
    يسجّل سبب التردد من الودجت. الأجسام: ‎store_slug, session_id, reason، ‎
    ‎custom_text‎ اختياري لـ ‎other‎.
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
        custom_raw = body.get("custom_text")
        if not ss or not sid or not reason:
            return j({"ok": False, "error": "store_slug_session_reason_required"}, 400)
        if reason not in REASON_CHOICES:
            return j({"ok": False, "error": "invalid_reason"}, 400)
        custom: Optional[str] = None
        if reason in ("other", "human_support"):
            c = (
                (str(custom_raw) if custom_raw is not None else "")
                or ""
            ).strip()[:20000]
            if reason == "other" and not c:
                return j({"ok": False, "error": "custom_text_required"}, 400)
            custom = c if c else None
        elif custom_raw is not None and (str(custom_raw) or "").strip():
            return j({"ok": False, "error": "custom_text_not_applicable"}, 400)
        row = AbandonmentReasonLog(
            store_slug=ss,
            session_id=sid,
            reason=reason,
            custom_text=custom,
        )
        db.session.add(row)
        db.session.commit()
        return j({"ok": True})
    except (SQLAlchemyError, OSError) as e:
        db.session.rollback()
        log.warning("cartflow reason: %s", e)
        return j({"ok": False, "error": "persist_failed"}, 500)
