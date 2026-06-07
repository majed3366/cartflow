# -*- coding: utf-8 -*-
"""Admin-only merchant subscription control — pilot / early launch (no billing)."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

from extensions import db
from models import MerchantSubscriptionAuditLog, MerchantUser, Store
from sqlalchemy import or_
from schema_merchant_subscription import ensure_merchant_subscription_schema
from services.cartflow_plans_v1 import CANONICAL_PLAN_IDS, PLAN_LABEL_AR, PlanId, normalize_plan_id
from services.merchant_onboarding_store import merchant_store_display_name
from services.merchant_subscription_v1 import (
    PLAN_SOURCE_MANUAL,
    PLAN_STATUS_ACTIVE,
    PLAN_STATUS_CANCELLED,
    PLAN_STATUS_EXPIRED,
    PLAN_STATUS_TRIALING,
    _format_dt_ar,
    normalize_plan_status,
    read_subscription_fields,
)

log = logging.getLogger("cartflow.admin_subscription_control")

DEFAULT_TRIAL_DAYS = 14
DEFAULT_EXTEND_TRIAL_DAYS = 7

ADMIN_ACTIONS = frozenset(
    {
        "change_plan",
        "start_trial",
        "extend_trial",
        "mark_active",
        "mark_expired",
        "cancel",
        "reactivate",
        "set_plan_expiration",
        "clear_expiration",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_date_only(raw: Any) -> Optional[datetime]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, datetime):
        return _aware(raw)
    s = str(raw).strip()
    if not s:
        return None
    try:
        if "T" in s:
            return _aware(datetime.fromisoformat(s.replace("Z", "+00:00")))
        return datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _snapshot_user(user: MerchantUser) -> dict[str, Any]:
    fields = read_subscription_fields(user)
    fields["trial_started_at"] = _aware(getattr(user, "trial_started_at", None))
    fields["trial_expires_at"] = _aware(getattr(user, "trial_expires_at", None))
    return fields


def _primary_store_for_user(user: MerchantUser) -> Optional[Store]:
    sid = getattr(user, "primary_store_id", None)
    if sid:
        row = db.session.get(Store, int(sid))
        if row is not None:
            return row
    return (
        db.session.query(Store)
        .filter(Store.merchant_user_id == int(user.id))
        .order_by(Store.id.asc())
        .first()
    )


def append_subscription_audit_log(
    *,
    merchant_user: MerchantUser,
    action: str,
    admin_source: str,
    reason: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> MerchantSubscriptionAuditLog:
    store = _primary_store_for_user(merchant_user)
    row = MerchantSubscriptionAuditLog(
        merchant_user_id=int(merchant_user.id),
        store_id=int(store.id) if store is not None else None,
        admin_source=(admin_source or "admin_session")[:128],
        action=(action or "unknown")[:64],
        old_plan=before.get("current_plan"),
        new_plan=after.get("current_plan"),
        old_status=before.get("plan_status"),
        new_status=after.get("plan_status"),
        old_plan_expires_at=before.get("plan_expires_at"),
        new_plan_expires_at=after.get("plan_expires_at"),
        old_trial_expires_at=before.get("trial_expires_at"),
        new_trial_expires_at=after.get("trial_expires_at"),
        reason=(reason or "").strip() or None,
    )
    db.session.add(row)
    return row


@dataclass
class AdminSubscriptionRow:
    merchant_user_id: int
    merchant_email: str
    merchant_name: str
    store_id: Optional[int]
    store_name: str
    store_slug: str
    current_plan: str
    current_plan_label: str
    plan_status: str
    plan_status_label: str
    plan_source: str
    plan_started_at_ar: str
    plan_expires_at_ar: str
    trial_started_at_ar: str
    trial_expires_at_ar: str
    updated_at_ar: str

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "merchant_user_id": self.merchant_user_id,
            "merchant_email": self.merchant_email,
            "merchant_name": self.merchant_name,
            "store_id": self.store_id,
            "store_name": self.store_name,
            "store_slug": self.store_slug,
            "current_plan": self.current_plan,
            "current_plan_label": self.current_plan_label,
            "plan_status": self.plan_status,
            "plan_status_label": self.plan_status_label,
            "plan_source": self.plan_source,
            "plan_started_at_ar": self.plan_started_at_ar,
            "plan_expires_at_ar": self.plan_expires_at_ar,
            "trial_started_at_ar": self.trial_started_at_ar,
            "trial_expires_at_ar": self.trial_expires_at_ar,
            "updated_at_ar": self.updated_at_ar,
        }


def build_admin_subscription_row(user: MerchantUser) -> AdminSubscriptionRow:
    store = _primary_store_for_user(user)
    plan_id = normalize_plan_id(getattr(user, "current_plan", None))
    status = normalize_plan_status(getattr(user, "plan_status", None))
    from services.merchant_subscription_v1 import (  # noqa: PLC0415
        PLAN_SOURCE_LABEL_AR,
        PLAN_STATUS_LABEL_AR,
        normalize_plan_source,
    )

    updated = _aware(getattr(user, "updated_at", None))
    return AdminSubscriptionRow(
        merchant_user_id=int(user.id),
        merchant_email=(getattr(user, "email", None) or "").strip(),
        merchant_name=(getattr(user, "merchant_name", None) or "").strip(),
        store_id=int(store.id) if store is not None else None,
        store_name=merchant_store_display_name(store, merchant_user=user),
        store_slug=(getattr(store, "zid_store_id", None) or "").strip() if store else "",
        current_plan=plan_id,
        current_plan_label=PLAN_LABEL_AR.get(plan_id, plan_id),
        plan_status=status,
        plan_status_label=PLAN_STATUS_LABEL_AR.get(status, status),
        plan_source=normalize_plan_source(getattr(user, "plan_source", None)),
        plan_started_at_ar=_format_dt_ar(_aware(getattr(user, "plan_started_at", None))),
        plan_expires_at_ar=_format_dt_ar(_aware(getattr(user, "plan_expires_at", None))),
        trial_started_at_ar=_format_dt_ar(_aware(getattr(user, "trial_started_at", None))),
        trial_expires_at_ar=_format_dt_ar(_aware(getattr(user, "trial_expires_at", None))),
        updated_at_ar=_format_dt_ar(updated),
    )


def list_admin_subscription_rows(
    *,
    query: Optional[str] = None,
    limit: int = 50,
) -> list[AdminSubscriptionRow]:
    ensure_merchant_subscription_schema(db)
    q = db.session.query(MerchantUser).order_by(MerchantUser.id.desc())
    needle = (query or "").strip().lower()
    if needle:
        like = f"%{needle}%"
        q = q.filter(
            or_(
                MerchantUser.email.ilike(like),
                MerchantUser.merchant_name.ilike(like),
            )
        )
    rows = q.limit(max(1, min(int(limit), 200))).all()
    return [build_admin_subscription_row(u) for u in rows]


@dataclass
class AdminSubscriptionActionResult:
    ok: bool
    message: str
    merchant_user_id: int
    subscription: Optional[dict[str, Any]] = None
    audit_log_id: Optional[int] = None

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "message": self.message,
            "merchant_user_id": self.merchant_user_id,
            "subscription": self.subscription,
            "audit_log_id": self.audit_log_id,
        }


def apply_admin_subscription_action(
    merchant_user_id: int,
    *,
    action: str,
    admin_source: str = "admin_session",
    reason: str = "",
    plan: Optional[str] = None,
    trial_days: Optional[int] = None,
    extend_days: Optional[int] = None,
    plan_expires_at: Any = None,
    trial_expires_at: Any = None,
) -> AdminSubscriptionActionResult:
    ensure_merchant_subscription_schema(db)
    act = (action or "").strip().lower()
    if act not in ADMIN_ACTIONS:
        return AdminSubscriptionActionResult(
            ok=False,
            message="unknown_action",
            merchant_user_id=merchant_user_id,
        )
    if not (reason or "").strip():
        return AdminSubscriptionActionResult(
            ok=False,
            message="reason_required",
            merchant_user_id=merchant_user_id,
        )

    user = db.session.get(MerchantUser, int(merchant_user_id))
    if user is None:
        return AdminSubscriptionActionResult(
            ok=False,
            message="merchant_not_found",
            merchant_user_id=merchant_user_id,
        )

    before = _snapshot_user(user)
    now = _utcnow()

    if act == "change_plan":
        plan_id = normalize_plan_id(plan)
        if plan_id not in CANONICAL_PLAN_IDS:
            return AdminSubscriptionActionResult(
                ok=False,
                message="invalid_plan",
                merchant_user_id=merchant_user_id,
            )
        user.current_plan = plan_id
        if not user.plan_started_at:
            user.plan_started_at = now

    elif act == "start_trial":
        plan_id = normalize_plan_id(plan or user.current_plan)
        if plan_id not in CANONICAL_PLAN_IDS:
            return AdminSubscriptionActionResult(
                ok=False,
                message="invalid_plan",
                merchant_user_id=merchant_user_id,
            )
        days = int(trial_days if trial_days is not None else DEFAULT_TRIAL_DAYS)
        days = max(1, min(days, 365))
        user.current_plan = plan_id
        user.plan_status = PLAN_STATUS_TRIALING
        user.plan_source = PLAN_SOURCE_MANUAL
        user.trial_started_at = now
        user.trial_expires_at = now + timedelta(days=days)
        if not user.plan_started_at:
            user.plan_started_at = now

    elif act == "extend_trial":
        days = int(extend_days if extend_days is not None else DEFAULT_EXTEND_TRIAL_DAYS)
        days = max(1, min(days, 365))
        base = _aware(user.trial_expires_at) or now
        if base < now:
            base = now
        user.trial_expires_at = base + timedelta(days=days)
        if normalize_plan_status(user.plan_status) != PLAN_STATUS_TRIALING:
            user.plan_status = PLAN_STATUS_TRIALING

    elif act == "mark_active":
        user.plan_status = PLAN_STATUS_ACTIVE

    elif act == "mark_expired":
        user.plan_status = PLAN_STATUS_EXPIRED

    elif act == "cancel":
        user.plan_status = PLAN_STATUS_CANCELLED

    elif act == "reactivate":
        user.plan_status = PLAN_STATUS_ACTIVE

    elif act == "set_plan_expiration":
        exp = _parse_date_only(plan_expires_at)
        if exp is None:
            return AdminSubscriptionActionResult(
                ok=False,
                message="invalid_plan_expires_at",
                merchant_user_id=merchant_user_id,
            )
        user.plan_expires_at = exp

    elif act == "clear_expiration":
        user.plan_expires_at = None
        user.trial_expires_at = None

    user.updated_at = now
    after = _snapshot_user(user)
    audit = append_subscription_audit_log(
        merchant_user=user,
        action=act,
        admin_source=admin_source,
        reason=reason,
        before=before,
        after=after,
    )
    db.session.commit()
    db.session.refresh(user)
    db.session.refresh(audit)

    from services.merchant_subscription_v1 import build_merchant_subscription_status  # noqa: PLC0415

    status = build_merchant_subscription_status(merchant_user=user)
    log.info(
        "[ADMIN SUBSCRIPTION] action=%s merchant_user_id=%s plan=%s status=%s audit_id=%s",
        act,
        merchant_user_id,
        status.current_plan,
        status.plan_status,
        audit.id,
    )
    return AdminSubscriptionActionResult(
        ok=True,
        message="applied",
        merchant_user_id=merchant_user_id,
        subscription=status.to_api_dict(),
        audit_log_id=int(audit.id),
    )


def list_subscription_audit_logs(
    merchant_user_id: int,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    ensure_merchant_subscription_schema(db)
    rows = (
        db.session.query(MerchantSubscriptionAuditLog)
        .filter(MerchantSubscriptionAuditLog.merchant_user_id == int(merchant_user_id))
        .order_by(MerchantSubscriptionAuditLog.id.desc())
        .limit(max(1, min(int(limit), 100)))
        .all()
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        out.append(
            {
                "id": int(row.id),
                "admin_source": row.admin_source,
                "action": row.action,
                "old_plan": row.old_plan,
                "new_plan": row.new_plan,
                "old_status": row.old_status,
                "new_status": row.new_status,
                "old_plan_expires_at": (
                    row.old_plan_expires_at.isoformat()
                    if row.old_plan_expires_at
                    else None
                ),
                "new_plan_expires_at": (
                    row.new_plan_expires_at.isoformat()
                    if row.new_plan_expires_at
                    else None
                ),
                "old_trial_expires_at": (
                    row.old_trial_expires_at.isoformat()
                    if row.old_trial_expires_at
                    else None
                ),
                "new_trial_expires_at": (
                    row.new_trial_expires_at.isoformat()
                    if row.new_trial_expires_at
                    else None
                ),
                "reason": row.reason,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out
