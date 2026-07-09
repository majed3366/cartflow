# -*- coding: utf-8 -*-
"""Durable merchant cart archive / reopen (dashboard lifecycle only)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from sqlalchemy.exc import SQLAlchemyError

from extensions import db
from models import MerchantCartLifecycleArchive

SOURCE_MANUAL = "manual"
SOURCE_AUTO_EXHAUSTED = "auto_exhausted"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def bulk_merchant_archived(recovery_keys: Any) -> dict[str, bool]:
    """Single query for dashboard batch."""
    keys: list[str] = []
    seen: set[str] = set()
    for raw in recovery_keys or ():
        rk = (str(raw) or "").strip()[:512]
        if rk and rk not in seen:
            seen.add(rk)
            keys.append(rk)
    if not keys:
        return {}
    try:
        from schema_merchant_cart_lifecycle_archive import (  # noqa: PLC0415
            ensure_merchant_cart_lifecycle_archive_schema,
        )

        ensure_merchant_cart_lifecycle_archive_schema(db)
        rows = (
            db.session.query(MerchantCartLifecycleArchive.recovery_key)
            .filter(
                MerchantCartLifecycleArchive.recovery_key.in_(keys),
                MerchantCartLifecycleArchive.is_archived.is_(True),
            )
            .all()
        )
        return {
            str((row[0] if row else "") or "").strip()[:512]: True
            for row in rows
            if (row[0] if row else "")
        }
    except SQLAlchemyError:
        db.session.rollback()
        return {}


def bulk_merchant_reopened_keys(recovery_keys: Any) -> set[str]:
    """Keys with a durable archive row cleared (is_archived=False) — reopen truth."""
    keys: list[str] = []
    seen: set[str] = set()
    for raw in recovery_keys or ():
        rk = (str(raw) or "").strip()[:512]
        if rk and rk not in seen:
            seen.add(rk)
            keys.append(rk)
    if not keys:
        return set()
    try:
        from schema_merchant_cart_lifecycle_archive import (  # noqa: PLC0415
            ensure_merchant_cart_lifecycle_archive_schema,
        )

        ensure_merchant_cart_lifecycle_archive_schema(db)
        rows = (
            db.session.query(MerchantCartLifecycleArchive.recovery_key)
            .filter(
                MerchantCartLifecycleArchive.recovery_key.in_(keys),
                MerchantCartLifecycleArchive.is_archived.is_(False),
            )
            .all()
        )
        out: set[str] = set()
        for row in rows:
            rk = str((row[0] if row else "") or "").strip()[:512]
            if rk:
                out.add(rk)
        return out
    except SQLAlchemyError:
        db.session.rollback()
        return set()


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


def _dedupe_recovery_keys(keys: Any) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in keys or ():
        rk = (str(raw) or "").strip()[:512]
        if not rk or rk in seen:
            continue
        seen.add(rk)
        out.append(rk)
    return out


def archive_recovery_keys(
    *,
    recovery_keys: Any,
    store_slug: str,
    abandoned_cart_id: Optional[int] = None,
    source: str = SOURCE_MANUAL,
    session_id: str = "",
    cart_id: str = "",
) -> dict[str, Any]:
    """Persist archive for cart-specific recovery keys (session-only aliases excluded)."""
    from services.cart_action_identity_v1 import filter_mutation_recovery_keys  # noqa: PLC0415

    keys = filter_mutation_recovery_keys(
        _dedupe_recovery_keys(recovery_keys),
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    if not keys:
        return {"ok": False, "error": "recovery_key_required"}
    last: dict[str, Any] = {"ok": False, "error": "archive_failed"}
    archived_any = False
    for rk in keys:
        last = archive_recovery_key(
            recovery_key=rk,
            store_slug=store_slug,
            abandoned_cart_id=abandoned_cart_id,
            source=source,
        )
        if last.get("ok"):
            archived_any = True
    if archived_any:
        return {
            "ok": True,
            "archived": True,
            "recovery_key": keys[0],
            "recovery_keys": keys,
        }
    return last


def reopen_recovery_keys(
    recovery_keys: Any,
    *,
    store_slug: str = "",
    session_id: str = "",
    cart_id: str = "",
) -> dict[str, Any]:
    from services.cart_action_identity_v1 import filter_mutation_recovery_keys  # noqa: PLC0415

    keys = filter_mutation_recovery_keys(
        _dedupe_recovery_keys(recovery_keys),
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )
    if not keys:
        return {"ok": False, "error": "recovery_key_required"}
    cleared_any = False
    last: dict[str, Any] = {"ok": False, "error": "reopen_failed"}
    for rk in keys:
        last = reopen_recovery_key(rk)
        if last.get("ok"):
            cleared_any = True
            if last.get("cleared_persisted"):
                cleared_any = True
    if cleared_any:
        return {
            "ok": True,
            "archived": False,
            "recovery_key": keys[0],
            "recovery_keys": keys,
            "cleared_persisted": True,
        }
    return last


def dashboard_cart_lifecycle_archive_from_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """Archive one cart from dashboard POST body — cart-specific keys only."""
    from services.cart_action_identity_v1 import (  # noqa: PLC0415
        mutation_recovery_keys_for_dashboard_body,
        resolve_abandoned_cart_for_dashboard_action,
    )

    rk = (str(body.get("recovery_key") or "")).strip()[:512]
    if not rk:
        return {"ok": False, "error": "recovery_key_required"}
    ac_row, store_slug, ac_id_i = resolve_abandoned_cart_for_dashboard_action(body)
    keys = mutation_recovery_keys_for_dashboard_body(body)
    if not keys:
        return {"ok": False, "error": "recovery_key_required"}
    session_id = (
        (getattr(ac_row, "recovery_session_id", None) or "") if ac_row is not None else ""
    ).strip()
    cart_id = (
        (getattr(ac_row, "zid_cart_id", None) or "") if ac_row is not None else ""
    ).strip()[:255]
    if not session_id:
        session_id = (str(body.get("session_id") or "")).strip()[:512]
    if not cart_id:
        cart_id = (str(body.get("cart_id") or "")).strip()[:255]
    return archive_recovery_keys(
        recovery_keys=keys,
        store_slug=store_slug,
        abandoned_cart_id=ac_id_i,
        session_id=session_id,
        cart_id=cart_id,
    )


def dashboard_cart_lifecycle_reopen_from_body(body: Mapping[str, Any]) -> dict[str, Any]:
    """Reopen one cart from dashboard POST body — cart-specific keys only."""
    from services.cart_action_identity_v1 import (  # noqa: PLC0415
        mutation_recovery_keys_for_dashboard_body,
        resolve_abandoned_cart_for_dashboard_action,
    )

    rk = (str(body.get("recovery_key") or "")).strip()[:512]
    if not rk:
        return {"ok": False, "error": "recovery_key_required"}
    ac_row, store_slug, _ac_id_i = resolve_abandoned_cart_for_dashboard_action(body)
    keys = mutation_recovery_keys_for_dashboard_body(body)
    if not keys:
        return {"ok": False, "error": "recovery_key_required"}
    session_id = (
        (getattr(ac_row, "recovery_session_id", None) or "") if ac_row is not None else ""
    ).strip()
    cart_id = (
        (getattr(ac_row, "zid_cart_id", None) or "") if ac_row is not None else ""
    ).strip()[:255]
    if not session_id:
        session_id = (str(body.get("session_id") or "")).strip()[:512]
    if not cart_id:
        cart_id = (str(body.get("cart_id") or "")).strip()[:255]
    return reopen_recovery_keys(
        keys,
        store_slug=store_slug,
        session_id=session_id,
        cart_id=cart_id,
    )


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
            return {
                "ok": True,
                "recovery_key": rk,
                "archived": False,
                "cleared_persisted": False,
            }
        row.is_archived = False
        row.reopened_at = _utc_now()
        db.session.commit()
        return {
            "ok": True,
            "recovery_key": rk,
            "archived": False,
            "cleared_persisted": True,
        }
    except SQLAlchemyError as exc:
        db.session.rollback()
        return {"ok": False, "error": str(exc)[:240]}


def _row_recovery_key(row: Mapping[str, Any]) -> str:
    if not isinstance(row, Mapping):
        return ""
    rk = (str(row.get("recovery_key") or "")).strip()[:512]
    if rk:
        return rk
    store = (
        str(row.get("store_slug") or row.get("merchant_store_slug") or "")
    ).strip()[:255]
    cid = (str(row.get("zid_cart_id") or row.get("cart_id") or "")).strip()[:255]
    sid = (
        str(row.get("recovery_session_id") or row.get("session_id") or "")
    ).strip()[:512]
    if store and cid:
        return f"{store}:{cid}"[:512]
    if store and sid:
        return f"{store}:{sid}"[:512]
    return ""


def _mark_row_merchant_archived_visual(row: dict[str, Any]) -> None:
    row["customer_lifecycle_is_archived_visual"] = True
    row["customer_lifecycle_state"] = "archived"
    row["customer_lifecycle_label_ar"] = "مؤرشفة"
    row["customer_lifecycle_dashboard_action"] = "reopen"
    row["customer_lifecycle_status_row_class"] = "s-archived"
    row["merchant_status_row_class"] = "s-archived"
    row["merchant_status_label_ar"] = "مؤرشفة"
    row["merchant_next_action_urgent"] = False
    row["merchant_cart_bucket"] = "archived"
    row["merchant_cart_primary_bucket"] = "archived"
    row["merchant_cart_visible_tabs"] = ["all"]
    proj = row.get("cart_detail_projection_v1")
    if isinstance(proj, dict) and str(proj.get("version") or "") == "v1":
        proj["lifecycle_ui"] = {
            "recovery_key": _row_recovery_key(row),
            "archive_visible": False,
            "reopen_visible": True,
        }


def _clear_row_merchant_archived_visual(row: dict[str, Any]) -> None:
    row["customer_lifecycle_is_archived_visual"] = False
    if str(row.get("customer_lifecycle_dashboard_action") or "").strip() == "reopen":
        row["customer_lifecycle_dashboard_action"] = "archive"
    proj = row.get("cart_detail_projection_v1")
    if isinstance(proj, dict) and str(proj.get("version") or "") == "v1":
        act = str(row.get("customer_lifecycle_dashboard_action") or "").strip()
        proj["lifecycle_ui"] = {
            "recovery_key": _row_recovery_key(row),
            "archive_visible": act == "archive",
            "reopen_visible": act == "reopen",
        }


def apply_merchant_archive_truth_to_normal_carts_payload(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Overlay durable merchant archive flags onto snapshot/hot-merged normal-carts.

    Snapshot rows can lag archive/reopen writes by a builder tick. Hot-slice merge
    also re-appends stale active snapshot rows when hot correctly excludes them.
    This pass enforces DB ``merchant_cart_lifecycle_archives`` truth on every read.
    """
    if not isinstance(payload, dict):
        return payload

    active = [
        r for r in list(payload.get("merchant_carts_page_rows") or []) if isinstance(r, dict)
    ]
    archived = [
        r
        for r in list(payload.get("merchant_archived_carts_page_rows") or [])
        if isinstance(r, dict)
    ]
    keys: list[str] = []
    seen: set[str] = set()
    for row in active + archived:
        rk = _row_recovery_key(row)
        if rk and rk not in seen:
            seen.add(rk)
            keys.append(rk)
    if not keys:
        return payload

    archived_map = bulk_merchant_archived(keys)
    reopened_keys = bulk_merchant_reopened_keys(keys)

    keep_active: list[dict[str, Any]] = []
    moved_to_archived: list[dict[str, Any]] = []
    for row in active:
        rk = _row_recovery_key(row)
        if rk and archived_map.get(rk):
            _mark_row_merchant_archived_visual(row)
            moved_to_archived.append(row)
        else:
            keep_active.append(row)

    keep_archived: list[dict[str, Any]] = []
    restored_active: list[dict[str, Any]] = []
    archived_seen: set[str] = set()
    active_keys = {_row_recovery_key(r) for r in keep_active if _row_recovery_key(r)}
    for row in archived + moved_to_archived:
        rk = _row_recovery_key(row)
        if rk and rk in archived_seen:
            continue
        if rk:
            archived_seen.add(rk)
        if rk and archived_map.get(rk):
            _mark_row_merchant_archived_visual(row)
            keep_archived.append(row)
            continue
        # Durable reopen: archive row exists with is_archived=False.
        if rk and rk in reopened_keys:
            from services.customer_lifecycle_states_v1 import (  # noqa: PLC0415
                lifecycle_payload_for_reopen,
            )

            life = lifecycle_payload_for_reopen(rk)
            if isinstance(life, dict) and life:
                row.update(life)
            else:
                _clear_row_merchant_archived_visual(row)
            restored_active.append(row)
            continue
        # Hot/active already has this key — drop stale archived duplicate.
        if rk and rk in active_keys:
            continue
        keep_archived.append(row)

    # Prefer restored rows over any stale active duplicate of the same key.
    restored_keys = {_row_recovery_key(r) for r in restored_active if _row_recovery_key(r)}
    if restored_keys:
        keep_active = [
            r for r in keep_active if _row_recovery_key(r) not in restored_keys
        ]
        keep_active = restored_active + keep_active

    payload["merchant_carts_page_rows"] = keep_active
    payload["merchant_archived_carts_page_rows"] = keep_archived
    payload["merchant_archived_cart_count"] = len(keep_archived)
    payload["merchant_archive_truth_overlay"] = True
    if keep_active:
        payload["merchant_table_rows"] = list(keep_active[:8])
    return payload


__all__ = [
    "SOURCE_AUTO_EXHAUSTED",
    "SOURCE_MANUAL",
    "apply_merchant_archive_truth_to_normal_carts_payload",
    "archive_recovery_key",
    "archive_recovery_keys",
    "bulk_merchant_archived",
    "bulk_merchant_reopened_keys",
    "dashboard_cart_lifecycle_archive_from_body",
    "dashboard_cart_lifecycle_reopen_from_body",
    "is_merchant_archived",
    "reopen_recovery_key",
    "reopen_recovery_keys",
]
