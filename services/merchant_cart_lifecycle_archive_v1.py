# -*- coding: utf-8 -*-
"""Durable merchant cart archive / reopen (dashboard lifecycle only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import MerchantCartLifecycleArchive

SOURCE_MANUAL = "manual"
SOURCE_AUTO_EXHAUSTED = "auto_exhausted"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def is_merchant_archived(recovery_key: str) -> bool:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return False
    try:
        from schema_merchant_cart_lifecycle_archive import (  # noqa: PLC0415
            ensure_merchant_cart_lifecycle_archive_schema,
        )

        ensure_merchant_cart_lifecycle_archive_schema(db)
        row = (
            db.session.query(MerchantCartLifecycleArchive.is_archived)
            .filter(MerchantCartLifecycleArchive.recovery_key == rk)
            .first()
        )
        return bool(row and row[0])
    except SQLAlchemyError:
        db.session.rollback()
        return False


def archive_recovery_key(
    *,
    recovery_key: str,
    store_slug: str,
    abandoned_cart_id: Optional[int] = None,
    source: str = SOURCE_MANUAL,
) -> dict[str, Any]:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return {"ok": False, "error": "recovery_key_required"}
    slug = (store_slug or "").strip()[:255] or "unknown"
    try:
        from schema_merchant_cart_lifecycle_archive import (  # noqa: PLC0415
            ensure_merchant_cart_lifecycle_archive_schema,
        )

        ensure_merchant_cart_lifecycle_archive_schema(db)
        row = (
            db.session.query(MerchantCartLifecycleArchive)
            .filter(MerchantCartLifecycleArchive.recovery_key == rk)
            .first()
        )
        now = _utc_now()
        if row is None:
            row = MerchantCartLifecycleArchive(
                recovery_key=rk,
                store_slug=slug,
                abandoned_cart_id=int(abandoned_cart_id)
                if abandoned_cart_id is not None
                else None,
                is_archived=True,
                archive_source=(source or SOURCE_MANUAL)[:64],
                archived_at=now,
            )
            db.session.add(row)
        else:
            row.is_archived = True
            row.archive_source = (source or row.archive_source or SOURCE_MANUAL)[:64]
            row.archived_at = now
            row.reopened_at = None
            row.store_slug = slug
            if abandoned_cart_id is not None:
                row.abandoned_cart_id = int(abandoned_cart_id)
        db.session.commit()
        return {"ok": True, "recovery_key": rk, "archived": True}
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": str(exc)[:240]}


def reopen_recovery_key(recovery_key: str) -> dict[str, Any]:
    rk = (recovery_key or "").strip()[:512]
    if not rk:
        return {"ok": False, "error": "recovery_key_required"}
    try:
        from schema_merchant_cart_lifecycle_archive import (  # noqa: PLC0415
            ensure_merchant_cart_lifecycle_archive_schema,
        )

        ensure_merchant_cart_lifecycle_archive_schema(db)
        row = (
            db.session.query(MerchantCartLifecycleArchive)
            .filter(MerchantCartLifecycleArchive.recovery_key == rk)
            .first()
        )
        if row is None:
            return {"ok": False, "error": "not_archived"}
        row.is_archived = False
        row.reopened_at = _utc_now()
        db.session.commit()
        return {"ok": True, "recovery_key": rk, "archived": False}
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": str(exc)[:240]}


__all__ = [
    "SOURCE_AUTO_EXHAUSTED",
    "SOURCE_MANUAL",
    "archive_recovery_key",
    "is_merchant_archived",
    "reopen_recovery_key",
]
