# -*- coding: utf-8 -*-
"""
لوحة تجريبية ‎(demo)‎: قراءة تسلسل الرسائل وسجلات ‎CartRecoveryLog‎ (لا تُشغّل الاسترجاع).
وصول ‎/demo/*‎ — لا يلامس الودجت العام.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from json_response import j
from models import CartRecoveryLog

log = logging.getLogger("cartflow")

# يطابق ‎main._RECOVERY_SEQUENCE_STEPS‎ (عرض ونسخ فقط)
DEMO_RECOVERY_STEPS: tuple[tuple[int, str], ...] = (
    (1, "يبدو أنك نسيت سلتك 🛒"),
    (2, "المنتج اللي اخترته عليه طلب عالي"),
    (3, "ممكن يخلص قريب 👀"),
)

DEMO_STORE_SLUGS = frozenset({"demo", "demo2"})

# عرض فقط: نصوص وهمية لما قد يُرسل عبر واتساب (بدون إرسال فعلي).
WHATSAPP_DEMO_PREVIEW_BY_PRICE_SUB: dict[str, str] = {
    "price_discount_request": (
        "عندك كود خصم خاص 🎁 استخدمه الآن وكمّل طلبك 👇"
    ),
    "price_budget_issue": (
        "لو السعر أعلى من ميزانيتك، هذا خيار قريب منه بسعر أقل 👇"
    ),
    "price_cheaper_alternative": "هذا منتج مشابه بسعر أفضل 👇",
}
WHATSAPP_DEMO_PREVIEW_BY_REASON: dict[str, str] = {
    "quality": "هذا المنتج موضح بجودة عالية، تحب أشرح لك أكثر؟",
    "shipping": "الشحن سريع ويوصلك خلال أيام قليلة 👍",
    "warranty": "نراسلك بملخص الضمان والتفاصيل المهمة لهذا المنتج 👇",
    "thinking": "خذ راحتك — نراسلك بلطف عندما تكون جاهزاً لإكمال طلبك 👇",
}

router = APIRouter()


def _iso(dt: Any) -> Optional[str]:
    if dt is None:
        return None
    if getattr(dt, "tzinfo", None) is None:
        from datetime import timezone

        return dt.replace(tzinfo=timezone.utc).isoformat()  # type: ignore[union-attr]
    return dt.isoformat()  # type: ignore[union-attr]


def _whatsapp_preview_message(reason: str, sub_category: Optional[str]) -> Optional[str]:
    r = (reason or "").strip().lower()[:32]
    if r == "price":
        s = (sub_category or "").strip().lower()[:64]
        if not s:
            return None
        return WHATSAPP_DEMO_PREVIEW_BY_PRICE_SUB.get(s)
    return WHATSAPP_DEMO_PREVIEW_BY_REASON.get(r)


@router.get("/cartflow/whatsapp-preview", tags=["demo"])
def get_demo_whatsapp_preview(
    reason: str = Query(..., min_length=1, max_length=32),
    sub_category: str = Query(default=""),
) -> Any:
    """
    معاينة نص (لا إرسال): يُطابق ‎reason‎ و‎sub_category‎ عند ‎price‎.
    """
    s = (sub_category or "").strip() or None
    msg = _whatsapp_preview_message(reason, s)
    if msg is None:
        return j(
            {"ok": False, "error": "unknown_reason_or_sub", "message": None},
            400,
        )
    return j({"ok": True, "message": msg, "reason": reason.strip().lower()[:32]})


@router.get("/cartflow/sequence", tags=["demo"])
def get_demo_cartflow_sequence() -> Any:
    """نصوص الخطوات الثلاث (للعرض في صفحات ‎/demo*‎)."""
    return j(
        {
            "ok": True,
            "steps": [
                {"step": n, "message": t} for n, t in DEMO_RECOVERY_STEPS
            ],
        }
    )


@router.get("/cartflow/logs", tags=["demo"])
def get_demo_cartflow_logs(
    store_slug: str = Query(..., description="demo or demo2"),
    session_id: str = Query(
        default="", description="مُرشّح اختياري; فارغ = كل سجلات المتجر"
    ),
) -> Any:
    """
    آخر ‎10‎ سجلات ‎CartRecoveryLog‎ — فقط ‎store_slug=demo|demo2‎.
    """
    ss = (store_slug or "").strip()[:255]
    if not ss or ss not in DEMO_STORE_SLUGS:
        return j({"ok": False, "error": "invalid_store_for_demo"}, 400)
    sid = (session_id or "").strip() or None
    if sid and len(sid) > 512:
        return j({"ok": False, "error": "session_too_long"}, 400)
    try:
        db.create_all()
        q = (
            db.session.query(CartRecoveryLog)
            .filter(CartRecoveryLog.store_slug == ss)
        )
        if sid:
            q = q.filter(CartRecoveryLog.session_id == sid)
        rows = (
            q.order_by(CartRecoveryLog.created_at.desc())
            .limit(10)
            .all()
        )
        return j(
            {
                "ok": True,
                "store_slug": ss,
                "session_id_filter": sid,
                "logs": [
                    {
                        "id": r.id,
                        "session_id": r.session_id,
                        "message": (r.message or "")[:2000],
                        "status": r.status,
                        "step": r.step,
                        "created_at": _iso(r.created_at),
                        "sent_at": _iso(r.sent_at),
                    }
                    for r in rows
                ],
            }
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        log.warning("demo cartflow logs: %s", e)
        return j({"ok": False, "error": "query_failed"}, 500)
