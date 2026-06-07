# -*- coding: utf-8 -*-
"""Merchant subscription experience — visibility, health, benefits (no billing)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.cartflow_plans_v1 import (
    PLAN_GROWTH,
    PLAN_PRO,
    PLAN_RANK,
    PLAN_STARTER,
    PlanId,
    normalize_plan_id,
)
from services.merchant_billing_interval_v1 import BILLING_INTERVAL_TRIAL, normalize_billing_interval
from services.merchant_subscription_v1 import (
    PLAN_STATUS_ACTIVE,
    PLAN_STATUS_CANCELLED,
    PLAN_STATUS_EXPIRED,
    PLAN_STATUS_TRIALING,
    PLAN_SOURCE_LABEL_AR,
    PLAN_STATUS_LABEL_AR,
    normalize_plan_source,
    normalize_plan_status,
    subscription_expires_at_for_display,
)

PLAN_SIGNATURE_BENEFITS_AR: Mapping[str, tuple[str, ...]] = {
    PLAN_STARTER: (
        "الودجيت",
        "استرجاع واتساب",
        "لوحة التحكم",
        "تحليلات أساسية",
    ),
    PLAN_GROWTH: (
        "كشف VIP",
        "تنبيهات VIP",
        "رسائل متعددة",
        "تحليلات متقدمة",
    ),
    PLAN_PRO: (
        "تحكم استرجاع متقدم",
        "رؤى تشغيلية",
        "طبقات ذكاء قادمة",
    ),
}

UPGRADE_DISCOVERY_LABELS_AR: Mapping[str, str] = {
    PLAN_GROWTH: "متاح في Growth",
    PLAN_PRO: "متاح في Pro",
}


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def days_remaining_until(
    expires_at: Optional[datetime],
    *,
    now: Optional[datetime] = None,
) -> Optional[int]:
    if expires_at is None:
        return None
    ref = _aware(now or datetime.now(timezone.utc))
    end = _aware(expires_at)
    return (end.date() - ref.astimezone(timezone.utc).date()).days


def days_remaining_label_ar(days: Optional[int]) -> str:
    if days is None:
        return "—"
    if days < 0:
        return "منتهٍ"
    if days == 0:
        return "ينتهي اليوم"
    if days == 1:
        return "يوم واحد متبقٍ"
    return f"{days} يوماً متبقية"


def subscription_health_message_ar(
    *,
    plan_status: str,
    billing_interval: str,
    days_remaining: Optional[int],
    is_trialing: bool,
) -> tuple[str, str]:
    """Return (message_ar, tone) where tone is ok|warning|danger|neutral."""
    status = normalize_plan_status(plan_status)
    if status == PLAN_STATUS_CANCELLED:
        return "تم إلغاء الاشتراك", "danger"
    if status == PLAN_STATUS_EXPIRED:
        return "انتهى الاشتراك", "danger"
    if days_remaining is not None and days_remaining < 0:
        if is_trialing or normalize_billing_interval(billing_interval) == BILLING_INTERVAL_TRIAL:
            return "انتهت التجربة", "danger"
        return "انتهى الاشتراك", "danger"

    if is_trialing or status == PLAN_STATUS_TRIALING:
        if days_remaining is None:
            return "تجربة نشطة", "ok"
        if days_remaining == 0:
            return "تنتهي التجربة اليوم", "warning"
        if days_remaining == 1:
            return "تنتهي التجربة خلال يوم واحد", "warning"
        return f"تنتهي التجربة خلال {days_remaining} يوماً", "ok" if days_remaining > 7 else "warning"

    if status == PLAN_STATUS_ACTIVE and days_remaining is not None:
        if days_remaining == 0:
            return "ينتهي الاشتراك اليوم", "warning"
        if days_remaining == 1:
            return "ينتهي الاشتراك خلال يوم واحد", "warning"
        return f"ينتهي الاشتراك خلال {days_remaining} يوماً", "ok" if days_remaining > 7 else "warning"

    if status == PLAN_STATUS_ACTIVE:
        return "اشتراكك نشط", "neutral"

    return PLAN_STATUS_LABEL_AR.get(status, status), "neutral"


def current_plan_benefits_ar(plan_id: PlanId) -> list[str]:
    pid = normalize_plan_id(plan_id)
    benefits: list[str] = list(PLAN_SIGNATURE_BENEFITS_AR[PLAN_STARTER])
    if PLAN_RANK[pid] >= PLAN_RANK[PLAN_GROWTH]:
        benefits.extend(PLAN_SIGNATURE_BENEFITS_AR[PLAN_GROWTH])
    if pid == PLAN_PRO:
        benefits.extend(PLAN_SIGNATURE_BENEFITS_AR[PLAN_PRO])
    return benefits


def upgrade_discovery_ar(plan_id: PlanId) -> dict[str, list[str]]:
    pid = normalize_plan_id(plan_id)
    out: dict[str, list[str]] = {}
    if PLAN_RANK[pid] < PLAN_RANK[PLAN_GROWTH]:
        out[PLAN_GROWTH] = list(PLAN_SIGNATURE_BENEFITS_AR[PLAN_GROWTH])
    if PLAN_RANK[pid] < PLAN_RANK[PLAN_PRO]:
        out[PLAN_PRO] = list(PLAN_SIGNATURE_BENEFITS_AR[PLAN_PRO])
    return out


def upgrade_discovery_sections_ar(plan_id: PlanId) -> list[dict[str, Any]]:
    discovery = upgrade_discovery_ar(plan_id)
    sections: list[dict[str, Any]] = []
    for tier in (PLAN_GROWTH, PLAN_PRO):
        items = discovery.get(tier)
        if not items:
            continue
        sections.append(
            {
                "tier": tier,
                "title_ar": UPGRADE_DISCOVERY_LABELS_AR[tier],
                "items_ar": items,
            }
        )
    return sections


def status_badge_class(plan_status: str, *, is_trialing: bool = False) -> str:
    status = normalize_plan_status(plan_status)
    if is_trialing or status == PLAN_STATUS_TRIALING:
        return "is-trial"
    if status == PLAN_STATUS_EXPIRED:
        return "is-expired"
    if status == PLAN_STATUS_CANCELLED:
        return "is-cancelled"
    if status == PLAN_STATUS_ACTIVE:
        return "is-active"
    return "is-neutral"


def source_badge_class(plan_source: str) -> str:
    src = normalize_plan_source(plan_source)
    if src.endswith("_marketplace"):
        return "is-marketplace"
    if src == "future_direct_billing":
        return "is-cartflow"
    return "is-manual"


def build_subscription_experience_payload(
    *,
    current_plan: str,
    plan_status: str,
    plan_source: str,
    billing_interval: str,
    plan_expires_at: Optional[datetime],
    trial_expires_at: Optional[datetime],
    is_trialing: bool,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    interval = normalize_billing_interval(billing_interval)
    status = normalize_plan_status(plan_status)
    display_expires = subscription_expires_at_for_display(
        billing_interval=interval,
        plan_status=status,
        plan_expires_at=plan_expires_at,
        trial_expires_at=trial_expires_at,
    )
    days = days_remaining_until(display_expires, now=now)
    health_ar, health_tone = subscription_health_message_ar(
        plan_status=status,
        billing_interval=interval,
        days_remaining=days,
        is_trialing=is_trialing,
    )
    pid = normalize_plan_id(current_plan)
    src = normalize_plan_source(plan_source)
    return {
        "days_remaining": days,
        "days_remaining_label_ar": days_remaining_label_ar(days),
        "subscription_health_ar": health_ar,
        "subscription_health_tone": health_tone,
        "plan_badge_class": pid,
        "status_badge_class": status_badge_class(status, is_trialing=is_trialing),
        "status_badge_label_ar": (
            "Trial" if is_trialing or status == PLAN_STATUS_TRIALING else PLAN_STATUS_LABEL_AR.get(status, status)
        ),
        "source_badge_class": source_badge_class(src),
        "source_badge_label_ar": PLAN_SOURCE_LABEL_AR.get(src, src),
        "current_benefits_ar": current_plan_benefits_ar(pid),
        "upgrade_discovery": upgrade_discovery_ar(pid),
        "upgrade_discovery_sections_ar": upgrade_discovery_sections_ar(pid),
    }


def build_admin_subscription_visibility(
    *,
    plan_status: str,
    billing_interval: str,
    plan_expires_at: Optional[datetime],
    trial_expires_at: Optional[datetime],
    is_trialing: bool = False,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    interval = normalize_billing_interval(billing_interval)
    status = normalize_plan_status(plan_status)
    display_expires = subscription_expires_at_for_display(
        billing_interval=interval,
        plan_status=status,
        plan_expires_at=plan_expires_at,
        trial_expires_at=trial_expires_at,
    )
    days = days_remaining_until(display_expires, now=now)
    health_ar, health_tone = subscription_health_message_ar(
        plan_status=status,
        billing_interval=interval,
        days_remaining=days,
        is_trialing=is_trialing or status == PLAN_STATUS_TRIALING,
    )
    return {
        "days_remaining": days,
        "days_remaining_label_ar": days_remaining_label_ar(days),
        "subscription_health_ar": health_ar,
        "subscription_health_tone": health_tone,
    }
