# -*- coding: utf-8 -*-
"""
Founder Evaluation Reality Coverage V1 — seed isolated evaluation tenants.

Creates MerchantUser + Store + CartRecoveryReason rows only for cf_fe_v1_* slugs.
Does not touch demo or other production merchants. No WhatsApp / Meta / Scheduler.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from extensions import db
from models import CartRecoveryReason, MerchantUser, Store
from services.founder_evaluation_reality_v1.constants_v1 import (
    ALL_EVAL_STORE_SLUGS,
    EMAIL_ACTIONABLE,
    EMAIL_INSUFFICIENT,
    EMAIL_MEASURING,
    EVAL_PASSWORD,
    NAME_ACTIONABLE,
    NAME_INSUFFICIENT,
    NAME_MEASURING,
    SEED_ACTIONABLE_REASONS,
    SEED_INSUFFICIENT_REASONS,
    SEED_MEASURING_REASONS,
    STORE_ACTIONABLE,
    STORE_INSUFFICIENT,
    STORE_MEASURING,
)
from services.merchant_auth_v1 import hash_password


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _purge_eval_slug(slug: str) -> None:
    from sqlalchemy.exc import OperationalError

    try:
        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == slug
        ).delete(synchronize_session=False)
    except OperationalError:
        db.session.rollback()
        db.create_all()
        db.session.query(CartRecoveryReason).filter(
            CartRecoveryReason.store_slug == slug
        ).delete(synchronize_session=False)
    store = (
        db.session.query(Store).filter(Store.zid_store_id == slug).first()
    )
    if store is not None:
        mid = getattr(store, "merchant_user_id", None)
        if mid:
            user = (
                db.session.query(MerchantUser)
                .filter(MerchantUser.id == int(mid))
                .first()
            )
            if user is not None and getattr(user, "primary_store_id", None) == store.id:
                user.primary_store_id = None
                db.session.flush()
        db.session.delete(store)
        db.session.flush()
        if mid:
            user = (
                db.session.query(MerchantUser)
                .filter(MerchantUser.id == int(mid))
                .first()
            )
            if user is not None:
                other = (
                    db.session.query(Store)
                    .filter(Store.merchant_user_id == user.id)
                    .count()
                )
                if other == 0:
                    db.session.delete(user)


def _ensure_merchant_store(
    *,
    email: str,
    store_name: str,
    zid: str,
) -> tuple[MerchantUser, Store]:
    user = (
        db.session.query(MerchantUser)
        .filter(MerchantUser.email == email.strip().lower())
        .first()
    )
    if user is None:
        user = MerchantUser(
            email=email.strip().lower(),
            password_hash=hash_password(EVAL_PASSWORD),
            merchant_name=store_name[:255],
        )
        db.session.add(user)
        db.session.flush()
    else:
        user.password_hash = hash_password(EVAL_PASSWORD)
        user.merchant_name = store_name[:255]

    store = (
        db.session.query(Store).filter(Store.zid_store_id == zid).first()
    )
    if store is None:
        store = Store(
            zid_store_id=zid,
            merchant_user_id=int(user.id),
            widget_display_name=store_name[:255],
            recovery_delay=2,
            recovery_delay_unit="minutes",
            recovery_attempts=1,
            is_active=True,
            integration_source="founder_evaluation_v1",
        )
        db.session.add(store)
        db.session.flush()
    else:
        store.merchant_user_id = int(user.id)
        store.widget_display_name = store_name[:255]
        store.integration_source = "founder_evaluation_v1"
        store.is_active = True
        db.session.flush()

    user.primary_store_id = int(store.id)
    db.session.flush()
    return user, store


def _seed_reasons(slug: str, counts: dict[str, int]) -> int:
    db.session.query(CartRecoveryReason).filter(
        CartRecoveryReason.store_slug == slug
    ).delete(synchronize_session=False)
    now = _utcnow()
    n = 0
    for reason, count in counts.items():
        for i in range(int(count)):
            # Stagger within last 6 days so rolling 7-day window includes all.
            ts = now - timedelta(hours=6 + i * 3)
            row = CartRecoveryReason(
                store_slug=slug,
                session_id=f"fe-eval-{slug}-{reason}-{i}",
                reason=reason,
                source="founder_evaluation_v1",
                created_at=ts,
                updated_at=ts,
            )
            db.session.add(row)
            n += 1
    db.session.flush()
    return n


def seed_founder_evaluation_tenants_v1(*, reset: bool = True) -> dict[str, Any]:
    """
    Idempotent seed of three isolated evaluation tenants.
    Returns proof dict for REPORT / capture.
    """
    if reset:
        for slug in sorted(ALL_EVAL_STORE_SLUGS):
            _purge_eval_slug(slug)
        db.session.flush()

    plans = (
        (EMAIL_ACTIONABLE, NAME_ACTIONABLE, STORE_ACTIONABLE, SEED_ACTIONABLE_REASONS),
        (EMAIL_MEASURING, NAME_MEASURING, STORE_MEASURING, SEED_MEASURING_REASONS),
        (
            EMAIL_INSUFFICIENT,
            NAME_INSUFFICIENT,
            STORE_INSUFFICIENT,
            SEED_INSUFFICIENT_REASONS,
        ),
    )
    out: dict[str, Any] = {"stores": {}, "production_slugs_touched": False}
    for email, name, zid, reasons in plans:
        user, store = _ensure_merchant_store(
            email=email, store_name=name, zid=zid
        )
        n = _seed_reasons(zid, reasons)
        out["stores"][zid] = {
            "email": email,
            "merchant_user_id": int(user.id),
            "store_id": int(store.id),
            "reason_rows": n,
            "reason_counts": dict(reasons),
        }
    db.session.commit()
    return out


__all__ = ["seed_founder_evaluation_tenants_v1"]
