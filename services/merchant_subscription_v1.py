# -*- coding: utf-8 -*-
"""Merchant subscription state — marketplace-first, no billing engine."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from extensions import db
from models import MerchantUser
from schema_merchant_subscription import ensure_merchant_subscription_schema
from services.cartflow_plans_v1 import (
    CANONICAL_PLAN_IDS,
    DEFAULT_PLAN_ID,
    PLAN_LABEL_AR,
    PlanId,
    normalize_plan_id,
)
from services.cartflow_entitlements_v1 import (
    entitlements_snapshot,
    plan_entitlements_enforcement_enabled,
)
from services.merchant_billing_interval_v1 import (
    BILLING_INTERVAL_ANNUAL,
    BILLING_INTERVAL_MANUAL_CUSTOM,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVAL_TRIAL,
    billing_interval_label_ar,
    normalize_billing_interval,
)

log = logging.getLogger("cartflow.merchant_subscription")

PLAN_STATUS_ACTIVE = "active"
PLAN_STATUS_TRIALING = "trialing"
PLAN_STATUS_EXPIRED = "expired"
PLAN_STATUS_SUSPENDED = "suspended"
PLAN_STATUS_CANCELLED = "cancelled"
# Legacy alias
PLAN_STATUS_TRIAL = PLAN_STATUS_TRIALING

CANONICAL_PLAN_STATUSES: frozenset[str] = frozenset(
    {
        PLAN_STATUS_ACTIVE,
        PLAN_STATUS_TRIALING,
        PLAN_STATUS_EXPIRED,
        PLAN_STATUS_CANCELLED,
    }
)

PLAN_SOURCE_MANUAL = "manual"
PLAN_SOURCE_ZID_MARKETPLACE = "zid_marketplace"
PLAN_SOURCE_SALLA_MARKETPLACE = "salla_marketplace"
PLAN_SOURCE_FUTURE_DIRECT_BILLING = "future_direct_billing"

CANONICAL_PLAN_SOURCES: tuple[str, ...] = (
    PLAN_SOURCE_MANUAL,
    PLAN_SOURCE_ZID_MARKETPLACE,
    PLAN_SOURCE_SALLA_MARKETPLACE,
    PLAN_SOURCE_FUTURE_DIRECT_BILLING,
)

PLAN_SOURCE_LABEL_AR: Mapping[str, str] = {
    PLAN_SOURCE_MANUAL: "Manual",
    PLAN_SOURCE_ZID_MARKETPLACE: "Zid",
    PLAN_SOURCE_SALLA_MARKETPLACE: "Salla",
    PLAN_SOURCE_FUTURE_DIRECT_BILLING: "CartFlow",
}

PLAN_STATUS_LABEL_AR: Mapping[str, str] = {
    PLAN_STATUS_ACTIVE: "نشطة",
    PLAN_STATUS_TRIALING: "Trial",
    PLAN_STATUS_EXPIRED: "منتهية",
    PLAN_STATUS_SUSPENDED: "موقوفة",
    PLAN_STATUS_CANCELLED: "ملغاة",
}

# Future marketplace webhook / app events — architecture only (no handlers wired).
MARKETPLACE_PLAN_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "zid_plan_activated",
        "zid_plan_changed",
        "salla_plan_activated",
        "salla_plan_changed",
    }
)


def normalize_plan_source(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if key in CANONICAL_PLAN_SOURCES:
        return key
    return PLAN_SOURCE_MANUAL


def normalize_plan_status(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if key == "trial":
        key = PLAN_STATUS_TRIALING
    if key in CANONICAL_PLAN_STATUSES:
        return key
    if key == PLAN_STATUS_SUSPENDED:
        return PLAN_STATUS_EXPIRED
    return PLAN_STATUS_ACTIVE


def subscription_entitlements_blocked(merchant_user: Any | None) -> bool:
    """True when enforcement should deny features (expired/cancelled/past trial end)."""
    from services.cartflow_entitlements_v1 import plan_entitlements_enforcement_enabled  # noqa: PLC0415

    if not plan_entitlements_enforcement_enabled() or merchant_user is None:
        return False
    status = normalize_plan_status(getattr(merchant_user, "plan_status", None))
    if status in (PLAN_STATUS_EXPIRED, PLAN_STATUS_CANCELLED):
        return True
    if status == PLAN_STATUS_TRIALING:
        exp = _coerce_dt(getattr(merchant_user, "trial_expires_at", None))
        if exp is not None:
            d = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > d.astimezone(timezone.utc):
                return True
    if status == PLAN_STATUS_ACTIVE:
        exp = _coerce_dt(getattr(merchant_user, "plan_expires_at", None))
        if exp is not None:
            d = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > d.astimezone(timezone.utc):
                return True
    return False


def _format_dt_ar(dt: Optional[datetime]) -> str:
    if dt is None:
        return "—"
    d = dt
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _coerce_dt(raw: Any) -> Optional[datetime]:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    return None


def read_subscription_fields(merchant_user: Any | None) -> dict[str, Any]:
    if merchant_user is None:
        return {
            "current_plan": DEFAULT_PLAN_ID,
            "plan_status": PLAN_STATUS_ACTIVE,
            "plan_source": PLAN_SOURCE_MANUAL,
            "billing_interval": "",
            "plan_started_at": None,
            "plan_expires_at": None,
            "trial_started_at": None,
            "trial_expires_at": None,
        }
    return {
        "current_plan": normalize_plan_id(getattr(merchant_user, "current_plan", None)),
        "plan_status": normalize_plan_status(getattr(merchant_user, "plan_status", None)),
        "plan_source": normalize_plan_source(getattr(merchant_user, "plan_source", None)),
        "billing_interval": normalize_billing_interval(
            getattr(merchant_user, "billing_interval", None)
        ),
        "plan_started_at": _coerce_dt(getattr(merchant_user, "plan_started_at", None)),
        "plan_expires_at": _coerce_dt(getattr(merchant_user, "plan_expires_at", None)),
        "trial_started_at": _coerce_dt(getattr(merchant_user, "trial_started_at", None)),
        "trial_expires_at": _coerce_dt(getattr(merchant_user, "trial_expires_at", None)),
    }


def subscription_expires_at_for_display(
    *,
    billing_interval: str,
    plan_status: str,
    plan_expires_at: Optional[datetime],
    trial_expires_at: Optional[datetime],
) -> Optional[datetime]:
    interval = normalize_billing_interval(billing_interval)
    status = normalize_plan_status(plan_status)
    if interval == BILLING_INTERVAL_TRIAL or status == PLAN_STATUS_TRIALING:
        return trial_expires_at
    if interval in (BILLING_INTERVAL_MONTHLY, BILLING_INTERVAL_ANNUAL):
        return plan_expires_at
    if interval == BILLING_INTERVAL_MANUAL_CUSTOM:
        return plan_expires_at or trial_expires_at
    if status == PLAN_STATUS_TRIALING:
        return trial_expires_at
    return plan_expires_at


def apply_subscription_fields_to_merchant(
    merchant_user: MerchantUser,
    *,
    current_plan: Optional[PlanId] = None,
    plan_status: Optional[str] = None,
    plan_source: Optional[str] = None,
    plan_started_at: Optional[datetime] = None,
    plan_expires_at: Optional[datetime] = None,
) -> None:
    if current_plan is not None:
        merchant_user.current_plan = normalize_plan_id(current_plan)
    if plan_status is not None:
        merchant_user.plan_status = normalize_plan_status(plan_status)
    if plan_source is not None:
        merchant_user.plan_source = normalize_plan_source(plan_source)
    if plan_started_at is not None:
        merchant_user.plan_started_at = plan_started_at
    if plan_expires_at is not None:
        merchant_user.plan_expires_at = plan_expires_at


@dataclass
class MerchantSubscriptionStatus:
    current_plan: PlanId
    current_plan_label_ar: str
    plan_status: str
    plan_status_label_ar: str
    plan_source: str
    plan_source_label_ar: str
    billing_interval: str
    billing_interval_label_ar: str
    plan_started_at: Optional[datetime]
    plan_started_at_ar: str
    plan_expires_at: Optional[datetime]
    plan_expires_at_ar: str
    trial_started_at: Optional[datetime]
    trial_started_at_ar: str
    trial_expires_at: Optional[datetime]
    trial_expires_at_ar: str
    subscription_expires_at: Optional[datetime]
    subscription_expires_at_ar: str
    is_trialing: bool
    subscription_updated_at: Optional[datetime]
    subscription_updated_at_ar: str
    entitlements_enforcement_enabled: bool
    entitlements_blocked: bool
    entitlements: dict[str, bool]

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "current_plan": self.current_plan,
            "current_plan_label_ar": self.current_plan_label_ar,
            "plan_status": self.plan_status,
            "plan_status_label_ar": self.plan_status_label_ar,
            "plan_source": self.plan_source,
            "plan_source_label_ar": self.plan_source_label_ar,
            "billing_interval": self.billing_interval or None,
            "billing_interval_label_ar": self.billing_interval_label_ar,
            "plan_started_at": (
                self.plan_started_at.isoformat() if self.plan_started_at else None
            ),
            "plan_started_at_ar": self.plan_started_at_ar,
            "plan_expires_at": (
                self.plan_expires_at.isoformat() if self.plan_expires_at else None
            ),
            "plan_expires_at_ar": self.plan_expires_at_ar,
            "trial_started_at": (
                self.trial_started_at.isoformat() if self.trial_started_at else None
            ),
            "trial_started_at_ar": self.trial_started_at_ar,
            "trial_expires_at": (
                self.trial_expires_at.isoformat() if self.trial_expires_at else None
            ),
            "trial_expires_at_ar": self.trial_expires_at_ar,
            "subscription_expires_at": (
                self.subscription_expires_at.isoformat()
                if self.subscription_expires_at
                else None
            ),
            "subscription_expires_at_ar": self.subscription_expires_at_ar,
            "is_trialing": self.is_trialing,
            "subscription_updated_at": (
                self.subscription_updated_at.isoformat()
                if self.subscription_updated_at
                else None
            ),
            "subscription_updated_at_ar": self.subscription_updated_at_ar,
            "entitlements_enforcement_enabled": self.entitlements_enforcement_enabled,
            "entitlements_blocked": self.entitlements_blocked,
            "entitlements": dict(self.entitlements),
            "read_only": True,
            "billing_actions_available": False,
        }


def build_merchant_subscription_status(
    *,
    cookies: Optional[Mapping[str, str]] = None,
    merchant_user: Any | None = None,
) -> MerchantSubscriptionStatus:
    ensure_merchant_subscription_schema(db)
    user = merchant_user
    if user is None and cookies is not None:
        from services.merchant_auth_v1 import (  # noqa: PLC0415
            get_merchant_user_by_id,
            merchant_id_from_request_cookies,
        )

        mid = merchant_id_from_request_cookies(dict(cookies))
        if mid:
            user = get_merchant_user_by_id(int(mid))
    fields = read_subscription_fields(user)
    plan_id = fields["current_plan"]
    source = fields["plan_source"]
    status = fields["plan_status"]
    interval = fields["billing_interval"]
    started = fields["plan_started_at"]
    expires = fields["plan_expires_at"]
    trial_started = fields["trial_started_at"]
    trial_expires = fields["trial_expires_at"]
    display_expires = subscription_expires_at_for_display(
        billing_interval=interval,
        plan_status=status,
        plan_expires_at=expires,
        trial_expires_at=trial_expires,
    )
    updated = _coerce_dt(getattr(user, "updated_at", None)) if user is not None else None
    is_trialing = status == PLAN_STATUS_TRIALING
    blocked = subscription_entitlements_blocked(user)
    return MerchantSubscriptionStatus(
        current_plan=plan_id,
        current_plan_label_ar=PLAN_LABEL_AR.get(plan_id, plan_id),
        plan_status=status,
        plan_status_label_ar=PLAN_STATUS_LABEL_AR.get(status, status),
        plan_source=source,
        plan_source_label_ar=PLAN_SOURCE_LABEL_AR.get(source, source),
        billing_interval=interval,
        billing_interval_label_ar=billing_interval_label_ar(interval),
        plan_started_at=started,
        plan_started_at_ar=_format_dt_ar(started),
        plan_expires_at=expires,
        plan_expires_at_ar=_format_dt_ar(expires),
        trial_started_at=trial_started,
        trial_started_at_ar=_format_dt_ar(trial_started),
        trial_expires_at=trial_expires,
        trial_expires_at_ar=_format_dt_ar(trial_expires),
        subscription_expires_at=display_expires,
        subscription_expires_at_ar=_format_dt_ar(display_expires),
        is_trialing=is_trialing,
        subscription_updated_at=updated,
        subscription_updated_at_ar=_format_dt_ar(updated),
        entitlements_enforcement_enabled=plan_entitlements_enforcement_enabled(),
        entitlements_blocked=blocked,
        entitlements=entitlements_snapshot(user),
    )


@dataclass
class MarketplacePlanEventResult:
    ok: bool
    event_type: str
    accepted: bool
    message: str
    implementation_status: str = "architecture_only"

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "event_type": self.event_type,
            "accepted": self.accepted,
            "message": self.message,
            "implementation_status": self.implementation_status,
        }


def validate_marketplace_plan_event_type(event_type: str) -> bool:
    return (event_type or "").strip().lower() in MARKETPLACE_PLAN_EVENT_TYPES


def preview_marketplace_plan_event(
    event_type: str,
    payload: Optional[Mapping[str, Any]] = None,
) -> MarketplacePlanEventResult:
    """
    Architecture stub for future Zid/Salla marketplace plan webhooks.
    Validates event type and logs intent — does not mutate subscription state yet.
    """
    key = (event_type or "").strip().lower()
    if not validate_marketplace_plan_event_type(key):
        return MarketplacePlanEventResult(
            ok=False,
            event_type=key,
            accepted=False,
            message="unknown_marketplace_plan_event_type",
        )
    plan_hint = (payload or {}).get("plan") or (payload or {}).get("current_plan")
    log.info(
        "[MARKETPLACE PLAN EVENT PREVIEW] event=%s plan_hint=%s payload_keys=%s",
        key,
        plan_hint,
        sorted((payload or {}).keys()),
    )
    return MarketplacePlanEventResult(
        ok=True,
        event_type=key,
        accepted=True,
        message="architecture_ready_no_integration",
    )


def marketplace_plan_event_source_for_type(event_type: str) -> str:
    key = (event_type or "").strip().lower()
    if key.startswith("zid_"):
        return PLAN_SOURCE_ZID_MARKETPLACE
    if key.startswith("salla_"):
        return PLAN_SOURCE_SALLA_MARKETPLACE
    return PLAN_SOURCE_MANUAL


def plan_id_from_marketplace_payload(payload: Optional[Mapping[str, Any]]) -> PlanId:
    raw = None
    if payload:
        raw = payload.get("plan") or payload.get("current_plan") or payload.get("plan_id")
    normalized = normalize_plan_id(str(raw) if raw is not None else None)
    if normalized not in CANONICAL_PLAN_IDS:
        return DEFAULT_PLAN_ID
    return normalized
