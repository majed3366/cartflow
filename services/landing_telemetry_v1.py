# -*- coding: utf-8 -*-
"""Anonymous Landing Page behavioural telemetry (Reality Validation V1).

No PII. Allowed event names only. Persist for observation reports.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

log = logging.getLogger("cartflow.landing_telemetry")

ALLOWED_EVENTS = frozenset(
    {
        "landing_opened",
        "hero_visible",
        "hero_cta_clicked",
        "login_clicked",
        "signup_clicked",
        "problem_section_viewed",
        "widget_section_viewed",
        "whatsapp_section_viewed",
        "dashboard_section_viewed",
        "knowledge_section_viewed",
        "faq_section_viewed",
        "footer_reached",
        "scroll_25",
        "scroll_50",
        "scroll_75",
        "scroll_100",
        "page_exit",
    }
)

ALLOWED_DEVICES = frozenset({"mobile", "tablet", "desktop", "unknown"})

_schema_lock = threading.Lock()
_schema_ready = False


def reset_landing_telemetry_schema_guard_for_tests() -> None:
    global _schema_ready
    _schema_ready = False


def ensure_landing_telemetry_schema() -> None:
    """Idempotent DDL for landing_page_events_v1."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        from extensions import db
        import models  # noqa: F401

        try:
            models.LandingPageEventV1.__table__.create(bind=db.engine, checkfirst=True)
            _schema_ready = True
        except SQLAlchemyError as exc:
            log.warning("landing_telemetry schema ensure failed: %s", type(exc).__name__)
            try:
                db.session.rollback()
            except Exception:
                pass


def normalize_device(raw: Optional[str]) -> str:
    d = (raw or "").strip().lower()
    return d if d in ALLOWED_DEVICES else "unknown"


def normalize_session_key(raw: Optional[str]) -> str:
    s = (raw or "").strip()
    if not s or len(s) > 64:
        return ""
    # anonymous opaque id only
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
    if any(ch not in allowed for ch in s):
        return ""
    return s


def record_landing_event(
    *,
    event: str,
    section: Optional[str] = None,
    device: Optional[str] = None,
    session_key: Optional[str] = None,
) -> dict[str, Any]:
    ev = (event or "").strip()
    if ev not in ALLOWED_EVENTS:
        return {"ok": False, "error": "event_not_allowed"}

    ensure_landing_telemetry_schema()
    from extensions import db
    from models import LandingPageEventV1

    sec = (section or "").strip()[:64] or None
    row = LandingPageEventV1(
        event_name=ev,
        section=sec,
        device=normalize_device(device),
        session_key=normalize_session_key(session_key) or None,
        created_at=datetime.now(timezone.utc),
    )
    try:
        db.session.add(row)
        db.session.commit()
        return {"ok": True, "event": ev}
    except SQLAlchemyError as exc:
        db.session.rollback()
        log.warning("landing_telemetry write failed: %s", type(exc).__name__)
        return {"ok": False, "error": "persist_failed"}


def summarize_landing_telemetry(*, hours: int = 168) -> dict[str, Any]:
    """Aggregate anonymous counters for Reality Validation reports."""
    ensure_landing_telemetry_schema()
    from extensions import db
    from models import LandingPageEventV1
    from sqlalchemy import func

    h = max(1, min(int(hours or 168), 24 * 90))
    since = datetime.now(timezone.utc) - timedelta(hours=h)

    try:
        rows = (
            db.session.query(LandingPageEventV1.event_name, func.count(LandingPageEventV1.id))
            .filter(LandingPageEventV1.created_at >= since)
            .group_by(LandingPageEventV1.event_name)
            .all()
        )
        by_event = {name: int(cnt) for name, cnt in rows}

        sessions = (
            db.session.query(func.count(func.distinct(LandingPageEventV1.session_key)))
            .filter(
                LandingPageEventV1.created_at >= since,
                LandingPageEventV1.session_key.isnot(None),
            )
            .scalar()
        )
        device_rows = (
            db.session.query(LandingPageEventV1.device, func.count(LandingPageEventV1.id))
            .filter(
                LandingPageEventV1.created_at >= since,
                LandingPageEventV1.event_name == "landing_opened",
            )
            .group_by(LandingPageEventV1.device)
            .all()
        )
        by_device = {d or "unknown": int(c) for d, c in device_rows}

        opened = by_event.get("landing_opened", 0)
        scroll_depths = {
            "scroll_25": by_event.get("scroll_25", 0),
            "scroll_50": by_event.get("scroll_50", 0),
            "scroll_75": by_event.get("scroll_75", 0),
            "scroll_100": by_event.get("scroll_100", 0),
        }

        return {
            "ok": True,
            "window_hours": h,
            "since_utc": since.isoformat(),
            "visitors_approx_sessions": int(sessions or 0),
            "landing_opened": opened,
            "by_event": by_event,
            "device_distribution_opens": by_device,
            "scroll_depth_counts": scroll_depths,
            "knowledge_section_present_on_live": True,
            "notes": [
                "LP-09 Knowledge is present on Production Landing V1 (placeholder evidence until RV card Acceptance)",
                "No PII stored; session_key is opaque client-generated id",
            ],
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": type(exc).__name__}


__all__ = [
    "ALLOWED_EVENTS",
    "ensure_landing_telemetry_schema",
    "record_landing_event",
    "reset_landing_telemetry_schema_guard_for_tests",
    "summarize_landing_telemetry",
]
