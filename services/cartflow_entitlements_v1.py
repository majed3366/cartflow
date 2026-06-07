# -*- coding: utf-8 -*-
"""Central feature gates — marketplace-first plan entitlements."""
from __future__ import annotations

import os
from typing import Any, Optional

from services.cartflow_plans_v1 import (
    DEFAULT_PLAN_ID,
    PLAN_GROWTH,
    PLAN_PRO,
    PLAN_STARTER,
    PlanId,
    features_for_plan,
    normalize_plan_id,
    plan_includes_plan,
)


def plan_entitlements_enforcement_enabled() -> bool:
    """
    When disabled (default), all features are allowed — preserves pre-billing behavior.
    Enable via CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE=1 when marketplace billing goes live.
    """
    raw = (os.environ.get("CARTFLOW_PLAN_ENTITLEMENTS_ENFORCE") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def resolve_plan_id_from_merchant(merchant_user: Any | None) -> PlanId:
    if merchant_user is None:
        return DEFAULT_PLAN_ID
    return normalize_plan_id(getattr(merchant_user, "current_plan", None))


def resolve_plan_id_from_store(store: Any | None) -> PlanId:
    if store is None:
        return DEFAULT_PLAN_ID
    merchant_user = getattr(store, "merchant_user", None)
    if merchant_user is not None:
        return resolve_plan_id_from_merchant(merchant_user)
    merchant_user_id = getattr(store, "merchant_user_id", None)
    if merchant_user_id is None:
        return DEFAULT_PLAN_ID
    try:
        from extensions import db  # noqa: PLC0415
        from models import MerchantUser  # noqa: PLC0415

        row = db.session.get(MerchantUser, int(merchant_user_id))
        return resolve_plan_id_from_merchant(row)
    except (ImportError, TypeError, ValueError, AttributeError):
        return DEFAULT_PLAN_ID


def _subject_has_merchant_link(subject: Any | None) -> bool:
    if subject is None:
        return False
    if getattr(subject, "current_plan", None) is not None:
        return True
    if getattr(subject, "merchant_user_id", None) is not None:
        return True
    if getattr(subject, "email", None) is not None:
        return True
    return False


def has_feature(subject: Any | None, feature: str) -> bool:
    """
    Return True if ``subject`` (MerchantUser or Store) may use ``feature``.
    Defaults permissive when enforcement is off or subject has no merchant linkage.
    """
    key = (feature or "").strip().lower()
    if not key:
        return False
    if not plan_entitlements_enforcement_enabled():
        return True
    if not _subject_has_merchant_link(subject):
        return True
    merchant_user = subject
    if getattr(subject, "email", None) is None and getattr(subject, "current_plan", None) is None:
        from extensions import db  # noqa: PLC0415
        from models import MerchantUser  # noqa: PLC0415

        merchant_user_id = getattr(subject, "merchant_user_id", None)
        if merchant_user_id is not None:
            merchant_user = db.session.get(MerchantUser, int(merchant_user_id))
    from services.merchant_subscription_v1 import subscription_entitlements_blocked  # noqa: PLC0415

    if subscription_entitlements_blocked(merchant_user):
        return False
    plan_id = (
        resolve_plan_id_from_merchant(subject)
        if getattr(subject, "email", None) is not None
        or getattr(subject, "current_plan", None) is not None
        else resolve_plan_id_from_store(subject)
    )
    return key in features_for_plan(plan_id)


def is_starter(subject: Any | None) -> bool:
    if not plan_entitlements_enforcement_enabled():
        return False
    plan_id = _resolve_plan_for_subject(subject)
    return plan_id == PLAN_STARTER


def is_growth(subject: Any | None) -> bool:
    if not plan_entitlements_enforcement_enabled():
        return False
    plan_id = _resolve_plan_for_subject(subject)
    return plan_id == PLAN_GROWTH


def is_pro(subject: Any | None) -> bool:
    if not plan_entitlements_enforcement_enabled():
        return False
    plan_id = _resolve_plan_for_subject(subject)
    return plan_id == PLAN_PRO


def is_at_least_growth(subject: Any | None) -> bool:
    if not plan_entitlements_enforcement_enabled():
        return True
    plan_id = _resolve_plan_for_subject(subject)
    return plan_includes_plan(current=plan_id, required=PLAN_GROWTH)


def is_at_least_pro(subject: Any | None) -> bool:
    if not plan_entitlements_enforcement_enabled():
        return True
    plan_id = _resolve_plan_for_subject(subject)
    return plan_includes_plan(current=plan_id, required=PLAN_PRO)


def _resolve_plan_for_subject(subject: Any | None) -> PlanId:
    if subject is None:
        return DEFAULT_PLAN_ID
    if getattr(subject, "email", None) is not None or getattr(
        subject, "current_plan", None
    ) is not None:
        return resolve_plan_id_from_merchant(subject)
    return resolve_plan_id_from_store(subject)


def entitlements_snapshot(subject: Any | None) -> dict[str, bool]:
    """All known features → allowed flag (for diagnostics / future admin)."""
    from services.cartflow_plans_v1 import ALL_KNOWN_FEATURES  # noqa: PLC0415

    return {feat: has_feature(subject, feat) for feat in sorted(ALL_KNOWN_FEATURES)}
