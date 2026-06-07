# -*- coding: utf-8 -*-
"""Billing interval model and automatic subscription date calculation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Optional

BILLING_INTERVAL_TRIAL = "trial"
BILLING_INTERVAL_MONTHLY = "monthly"
BILLING_INTERVAL_ANNUAL = "annual"
BILLING_INTERVAL_MANUAL_CUSTOM = "manual_custom"

CANONICAL_BILLING_INTERVALS: frozenset[str] = frozenset(
    {
        BILLING_INTERVAL_TRIAL,
        BILLING_INTERVAL_MONTHLY,
        BILLING_INTERVAL_ANNUAL,
        BILLING_INTERVAL_MANUAL_CUSTOM,
    }
)

BILLING_INTERVAL_LABEL_AR: dict[str, str] = {
    BILLING_INTERVAL_TRIAL: "Trial — 14 days",
    BILLING_INTERVAL_MONTHLY: "Monthly — 30 days",
    BILLING_INTERVAL_ANNUAL: "Annual — 365 days",
    BILLING_INTERVAL_MANUAL_CUSTOM: "Custom",
}

TRIAL_DURATION_DAYS = 14
MONTHLY_DURATION_DAYS = 30
ANNUAL_DURATION_DAYS = 365


def normalize_billing_interval(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    if key in CANONICAL_BILLING_INTERVALS:
        return key
    return ""


def billing_interval_label_ar(interval: str | None) -> str:
    key = normalize_billing_interval(interval)
    if not key:
        return "—"
    return BILLING_INTERVAL_LABEL_AR.get(key, key)


def interval_duration_days(interval: str) -> Optional[int]:
    key = normalize_billing_interval(interval)
    if key == BILLING_INTERVAL_TRIAL:
        return TRIAL_DURATION_DAYS
    if key == BILLING_INTERVAL_MONTHLY:
        return MONTHLY_DURATION_DAYS
    if key == BILLING_INTERVAL_ANNUAL:
        return ANNUAL_DURATION_DAYS
    return None


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def calculate_expires_at_from_interval(
    *,
    billing_interval: str,
    started_at: datetime,
    expires_at: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Marketplace readiness: use explicit expires_at when provided,
    otherwise derive from billing_interval.
    """
    if expires_at is not None:
        return _aware(expires_at)
    days = interval_duration_days(billing_interval)
    if days is None:
        return None
    return _aware(started_at) + timedelta(days=days)


def apply_trial_dates(*, started_at: datetime) -> dict[str, datetime]:
    start = _aware(started_at)
    return {
        "trial_started_at": start,
        "trial_expires_at": start + timedelta(days=TRIAL_DURATION_DAYS),
    }


def apply_active_plan_dates(
    *,
    billing_interval: str,
    started_at: datetime,
    plan_expires_at: Optional[datetime] = None,
) -> dict[str, datetime]:
    start = _aware(started_at)
    exp = calculate_expires_at_from_interval(
        billing_interval=billing_interval,
        started_at=start,
        expires_at=plan_expires_at,
    )
    if exp is None:
        raise ValueError("invalid_billing_interval_for_plan_dates")
    return {"plan_started_at": start, "plan_expires_at": exp}


def preview_marketplace_subscription_dates(
    payload: Optional[Mapping[str, Any]],
    *,
    default_started_at: Optional[datetime] = None,
) -> dict[str, Any]:
    """Architecture-only helper for future Zid/Salla events — no integration."""
    data = payload or {}
    started = default_started_at or datetime.now(timezone.utc)
    if data.get("started_at"):
        try:
            started = _aware(datetime.fromisoformat(str(data["started_at"]).replace("Z", "+00:00")))
        except (TypeError, ValueError):
            pass
    interval = normalize_billing_interval(
        str(data.get("billing_interval") or data.get("interval") or "")
    )
    explicit_exp = data.get("expires_at")
    parsed_exp = None
    if explicit_exp:
        try:
            parsed_exp = _aware(datetime.fromisoformat(str(explicit_exp).replace("Z", "+00:00")))
        except (TypeError, ValueError):
            parsed_exp = None
    if interval == BILLING_INTERVAL_TRIAL:
        dates = apply_trial_dates(started_at=started)
        return {
            "billing_interval": interval,
            "trial_started_at": dates["trial_started_at"].isoformat(),
            "trial_expires_at": dates["trial_expires_at"].isoformat(),
            "implementation_status": "architecture_only",
        }
    if interval in (BILLING_INTERVAL_MONTHLY, BILLING_INTERVAL_ANNUAL):
        dates = apply_active_plan_dates(
            billing_interval=interval,
            started_at=started,
            plan_expires_at=parsed_exp,
        )
        return {
            "billing_interval": interval,
            "plan_started_at": dates["plan_started_at"].isoformat(),
            "plan_expires_at": dates["plan_expires_at"].isoformat(),
            "implementation_status": "architecture_only",
        }
    return {
        "billing_interval": interval or None,
        "implementation_status": "architecture_only",
        "message": "missing_or_custom_interval",
    }
