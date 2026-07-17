# -*- coding: utf-8 -*-
"""
Lab / walkthrough session membership alignment — INV-002 RC-3 Fix (B3).

Links the Lab simulation store (`demo`) to the merchant principal so Phase 3
membership can include it for Reality Attach — without making `demo` the
onboarding primary (onboarding resolve rejects system slugs).

Does not resolve identity for surfaces. Does not bypass Identity Authority.
Normal signup primary path is preserved when Reality Attach is inactive.
"""
from __future__ import annotations

from typing import Any

from services.identity_authority.exceptions import IdentityError
from services.store_reality_simulator.contracts_v1 import DEMO_STORE_SLUG


def align_merchant_session_to_simulation_store(
    *,
    merchant_user_id: int,
    store_slug: str = DEMO_STORE_SLUG,
) -> dict[str, Any]:
    """
    Authorize Lab membership for the simulation store.

    Sets ``Store.merchant_user_id`` on the demo row to the merchant so
    ``load_session_membership`` can include demo in ``membership_store_ids``.
    Does **not** change ``MerchantUser.primary_store_id`` (signup primary remains).

    Fail closed if merchant/store missing or slug is not the Lab sim tenant.
    """
    from extensions import db
    from models import MerchantUser, Store

    mid = int(merchant_user_id)
    slug = (store_slug or "").strip()
    if not slug:
        raise IdentityError("lab_bind_slug_required", "store_slug_required")
    if slug != DEMO_STORE_SLUG:
        raise IdentityError(
            "lab_bind_slug_forbidden",
            f"lab_bind_only_allows_{DEMO_STORE_SLUG}",
        )

    user = db.session.query(MerchantUser).filter_by(id=mid).first()
    if user is None:
        raise IdentityError("lab_bind_merchant_missing", f"merchant_not_found:{mid}")

    store = (
        db.session.query(Store).filter(Store.zid_store_id == DEMO_STORE_SLUG).first()
    )
    if store is None:
        raise IdentityError("lab_bind_store_missing", f"store_not_found:{DEMO_STORE_SLUG}")

    store_pk = int(store.id)
    prior_owner = getattr(store, "merchant_user_id", None)
    primary_id = getattr(user, "primary_store_id", None)

    store.merchant_user_id = mid
    db.session.add(store)
    db.session.commit()
    db.session.refresh(store)
    db.session.refresh(user)

    if int(store.merchant_user_id or 0) != mid:
        raise IdentityError(
            "lab_bind_owner_mismatch", "store_merchant_user_id_not_persisted"
        )
    # Primary must remain the signup store (not demo) for onboarding resolve.
    if primary_id is not None and int(primary_id) == store_pk:
        raise IdentityError(
            "lab_bind_primary_is_demo",
            "primary_must_remain_signup_store_not_demo",
        )

    return {
        "ok": True,
        "merchant_user_id": mid,
        "store_slug": DEMO_STORE_SLUG,
        "canonical_store_id": str(store_pk),
        "simulation_store_id": store_pk,
        "primary_store_id": int(primary_id) if primary_id else None,
        "prior_demo_owner_id": int(prior_owner) if prior_owner else None,
        "source": "lab_session_bind_v1",
        "membership_mode": "demo_owned_alongside_primary",
    }


def ensure_demo_store_for_lab() -> Any:
    """Ensure the Lab demo Store row exists (idempotent)."""
    from extensions import db
    from models import Store

    demo = db.session.query(Store).filter(Store.zid_store_id == DEMO_STORE_SLUG).first()
    if demo is not None:
        return demo
    demo = Store(
        zid_store_id=DEMO_STORE_SLUG,
        is_active=True,
        whatsapp_recovery_enabled=False,
    )
    db.session.add(demo)
    db.session.commit()
    db.session.refresh(demo)
    return demo


__all__ = [
    "align_merchant_session_to_simulation_store",
    "ensure_demo_store_for_lab",
]
