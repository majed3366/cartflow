# -*- coding: utf-8 -*-
"""لوحة مشرف منفصلة — تنبيهات قابلة للتنفيذ. لا تمس مسارات الويدجت/الاسترجاع."""
from __future__ import annotations

import hmac
import logging
import os
from pathlib import Path
from typing import Any, Optional, Sequence

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import AdminAlert, Store

log = logging.getLogger("cartflow")

_ROOT = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(_ROOT / "templates"))

router = APIRouter(include_in_schema=False)

ADMIN_STATUSES = frozenset({"active", "monitoring", "resolved"})
ADMIN_SEVERITIES = frozenset({"critical", "high", "medium", "low"})

STATUS_SORT = {"active": 0, "monitoring": 1, "resolved": 2}
SEVERITY_SORT = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_DEFAULT_ALERTS: tuple[dict[str, Any], ...] = (
    {
        "alert_type": "whatsapp_error",
        "title": "WhatsApp sending issue",
        "status": "active",
        "severity": "critical",
        "cause": (
            "WhatsApp credentials may be missing, invalid, or failing "
            "(Twilio / environment)."
        ),
        "action_label": "Fix WhatsApp Settings",
        "action_route": "/admin/integrations/whatsapp",
        "store_slug": None,
    },
    {
        "alert_type": "widget_load_error",
        "title": "Widget loading issue",
        "status": "monitoring",
        "severity": "high",
        "cause": "Widget script may not be loading correctly on the store.",
        "action_label": "Inspect Store Setup",
        "action_route": "/admin/stores",
        "store_slug": None,
    },
    {
        "alert_type": "cart_event_error",
        "title": "Cart events issue",
        "status": "active",
        "severity": "high",
        "cause": "Cart events are not being received or processed correctly.",
        "action_label": "Review Cart Events",
        "action_route": "/admin/cart-events",
        "store_slug": None,
    },
    {
        "alert_type": "backend_error",
        "title": "Backend system error",
        "status": "monitoring",
        "severity": "medium",
        "cause": "A server-side error was detected.",
        "action_label": "Open Error Logs",
        "action_route": "/admin/errors",
        "store_slug": None,
    },
    {
        "alert_type": "store_inactive",
        "title": "Store inactive",
        "status": "active",
        "severity": "medium",
        "cause": "Store is disabled or not fully configured.",
        "action_label": "Manage Store",
        "action_route": "/admin/stores",
        "store_slug": None,
    },
)


def _admin_username() -> str:
    return (os.getenv("ADMIN_USERNAME") or os.getenv("ADMIN_EMAIL") or "admin").strip()


def _admin_password() -> str:
    return (os.getenv("ADMIN_PASSWORD") or "admin").strip()


def _session_admin_ok(request: Request) -> bool:
    return request.session.get("admin_authenticated") is True


def _require_admin(request: Request) -> Optional[RedirectResponse]:
    if not _session_admin_ok(request):
        return RedirectResponse(url="/admin/login", status_code=302)
    return None


def _credential_ok(username: str, password: str) -> bool:
    u = (username or "").strip()
    p = (password or "").strip()
    eu = _admin_username().encode("utf-8")
    ep = _admin_password().encode("utf-8")
    try:
        return hmac.compare_digest(u.encode("utf-8"), eu) and hmac.compare_digest(
            p.encode("utf-8"), ep
        )
    except Exception:  # noqa: BLE001
        return False


def _ensure_admin_alerts_table() -> None:
    db.create_all()


def ensure_default_admin_alerts() -> None:
    """يُنشئ التنبيهات الافتراضية إذا كان الجدول فارغاً."""
    _ensure_admin_alerts_table()
    try:
        n = db.session.query(func.count(AdminAlert.id)).scalar() or 0
        if int(n) > 0:
            return
        for row in _DEFAULT_ALERTS:
            db.session.add(
                AdminAlert(
                    alert_type=str(row["alert_type"])[:64],
                    title=str(row["title"])[:255],
                    status=str(row["status"])[:32],
                    severity=str(row["severity"])[:32],
                    cause=str(row["cause"]),
                    action_label=str(row["action_label"])[:255],
                    action_route=str(row["action_route"])[:512],
                    store_slug=(str(row["store_slug"])[:255] if row.get("store_slug") else None),
                )
            )
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        log.warning("ensure_default_admin_alerts: %s", e)


def _alert_row_to_card_dict(row: AdminAlert) -> dict[str, Any]:
    return {
        "id": row.id,
        "type": row.alert_type,
        "title": row.title,
        "status": row.status,
        "severity": row.severity,
        "cause": row.cause,
        "action_label": row.action_label,
        "action_route": row.action_route,
        "created_at": row.created_at,
        "store_slug": row.store_slug,
    }


def _sort_alerts(rows: Sequence[AdminAlert]) -> list[AdminAlert]:
    def key(r: AdminAlert) -> tuple[int, int, int]:
        st = STATUS_SORT.get((r.status or "").lower(), 9)
        sev = SEVERITY_SORT.get((r.severity or "").lower(), 9)
        cid = int(r.id or 0)
        return (st, sev, cid)

    return sorted(rows, key=key)


def _dedupe_filter_params(
    status: Optional[str], severity: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    st = (status or "").strip().lower() or None
    if st and st not in ADMIN_STATUSES:
        st = None
    sev = (severity or "").strip().lower() or None
    if sev and sev not in ADMIN_SEVERITIES:
        sev = None
    return st, sev


def _store_overview_counts() -> dict[str, int]:
    try:
        db.create_all()
        total = int(db.session.query(func.count(Store.id)).scalar() or 0)
        active = int(
            db.session.query(func.count(Store.id))
            .filter(Store.is_active.is_(True))
            .scalar()
            or 0
        )
    except SQLAlchemyError:
        db.session.rollback()
        return {"total_stores": 0, "active_stores": 0}
    return {"total_stores": total, "active_stores": active}


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> Any:
    if _session_admin_ok(request):
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": None},
    )


@router.post("/admin/login", response_class=HTMLResponse)
def admin_login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
) -> Any:
    if _credential_ok(username, password):
        request.session["admin_authenticated"] = True
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": "Invalid username or password."},
        status_code=401,
    )


@router.get("/admin/logout")
def admin_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=302)


@router.get("/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    status: Optional[str] = None,
    severity: Optional[str] = None,
) -> Any:
    redir = _require_admin(request)
    if redir:
        return redir
    ensure_default_admin_alerts()
    st_f, sev_f = _dedupe_filter_params(status, severity)
    try:
        q = db.session.query(AdminAlert)
        if st_f:
            q = q.filter(AdminAlert.status == st_f)
        if sev_f:
            q = q.filter(AdminAlert.severity == sev_f)
        rows = _sort_alerts(list(q.all()))
        cards = [_alert_row_to_card_dict(r) for r in rows]
        alerts_active = int(
            db.session.query(func.count(AdminAlert.id))
            .filter(AdminAlert.status == "active")
            .scalar()
            or 0
        )
        critical_open = int(
            db.session.query(func.count(AdminAlert.id))
            .filter(
                AdminAlert.severity == "critical",
                AdminAlert.status.in_(("active", "monitoring")),
            )
            .scalar()
            or 0
        )
    except SQLAlchemyError as e:
        db.session.rollback()
        log.warning("admin dashboard: %s", e)
        cards = []
        alerts_active = 0
        critical_open = 0
    overview = _store_overview_counts()
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "alerts": cards,
            "filter_status": st_f or "",
            "filter_severity": sev_f or "",
            "total_stores": overview["total_stores"],
            "active_stores": overview["active_stores"],
            "alerts_active": alerts_active,
            "critical_alerts": critical_open,
        },
    )


def _admin_placeholder(
    request: Request,
    *,
    page_title: str,
    body_html: str,
) -> Any:
    redir = _require_admin(request)
    if redir:
        return redir
    return templates.TemplateResponse(
        "admin/placeholder.html",
        {
            "request": request,
            "page_title": page_title,
            "body_html": body_html,
        },
    )


@router.get("/admin/integrations/whatsapp", response_class=HTMLResponse)
def admin_whatsapp_integration(request: Request) -> Any:
    return _admin_placeholder(
        request,
        page_title="WhatsApp / Twilio integration",
        body_html=(
            "<p>Connection status and configuration hints will appear here.</p>"
            "<p class=\"text-slate-600 text-sm\">Check environment variables for "
            "<code class=\"bg-slate-100 px-1 rounded\">TWILIO_*</code> and related "
            "credentials.</p>"
        ),
    )


@router.get("/admin/stores", response_class=HTMLResponse)
def admin_stores(request: Request) -> Any:
    return _admin_placeholder(
        request,
        page_title="Stores",
        body_html=(
            "<p>Manage stores, activate or deactivate accounts, and review status.</p>"
        ),
    )


@router.get("/admin/cart-events", response_class=HTMLResponse)
def admin_cart_events(request: Request) -> Any:
    return _admin_placeholder(
        request,
        page_title="Cart events",
        body_html=(
            "<p>Inspect incoming cart events and recent processing failures.</p>"
        ),
    )


@router.get("/admin/errors", response_class=HTMLResponse)
def admin_errors(request: Request) -> Any:
    return _admin_placeholder(
        request,
        page_title="System errors",
        body_html=(
            "<p>Grouped server-side errors and logs — placeholder view.</p>"
        ),
    )


@router.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request) -> Any:
    return _admin_placeholder(
        request,
        page_title="Admin settings",
        body_html="<p>General system and admin preferences — placeholder.</p>",
    )


@router.post("/admin/alerts/{alert_id}/status")
def admin_alert_set_status(
    request: Request,
    alert_id: int,
    status: str = Form(...),
) -> RedirectResponse:
    redir = _require_admin(request)
    if redir:
        return redir
    st = (status or "").strip().lower()
    if st not in ADMIN_STATUSES:
        return RedirectResponse(url="/admin", status_code=302)
    try:
        row = db.session.get(AdminAlert, int(alert_id))
        if row is not None:
            row.status = st
            db.session.commit()
    except (SQLAlchemyError, TypeError, ValueError):
        db.session.rollback()
    return RedirectResponse(url="/admin", status_code=302)
