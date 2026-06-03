# -*- coding: utf-8 -*-
"""Strict canonical Store lookup for recovery — provision widget slugs without cross-store reads."""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from extensions import db
from models import Store

_log = logging.getLogger("cartflow")

WIDGET_RECOVERY_ZIDS = frozenset({"demo", "demo2", "default"})
CARTFLOW_DEFAULT_RECOVERY_STORE_ZID = "cartflow-default-recovery"

_RECOVERY_MIRROR_ATTRS = (
    "reason_templates_json",
    "recovery_delay",
    "recovery_delay_unit",
    "recovery_attempts",
    "recovery_delay_minutes",
    "second_attempt_delay_minutes",
    "vip_cart_threshold",
    "vip_enabled",
    "vip_notify_enabled",
    "vip_note",
    "whatsapp_recovery_enabled",
    "whatsapp_provider_mode",
    "store_whatsapp_number",
)


def is_widget_recovery_zid(zid: str) -> bool:
    return (zid or "").strip().casefold() in WIDGET_RECOVERY_ZIDS


def log_recovery_store_lookup(
    *,
    canonical_store: str,
    matched_store_id: Optional[int],
    matched_zid: Optional[str],
    found: bool,
    action: str = "",
) -> None:
    try:
        print("[STORE LOOKUP]", flush=True)
        print(f"canonical_store={canonical_store or '-'}", flush=True)
        print(
            f"matched_store_id={matched_store_id if matched_store_id is not None else '-'}",
            flush=True,
        )
        print(f"matched_zid={(matched_zid or '-')[:128]}", flush=True)
        print(f"found={'true' if found else 'false'}", flush=True)
        if action:
            print(f"action={action}", flush=True)
    except OSError:
        pass


def log_recovery_template_lookup(
    *,
    reason: str,
    template_found: bool,
    message_count: Optional[int],
    delay: Optional[float],
    unit: Optional[str],
    source: str,
    canon: Optional[str] = None,
) -> None:
    try:
        print("[TEMPLATE LOOKUP]", flush=True)
        print(f"reason={(reason or '-')[:64]}", flush=True)
        print(f"canon={(canon or '-')[:64]}", flush=True)
        print(f"template_found={'true' if template_found else 'false'}", flush=True)
        mc = message_count if message_count is not None else "-"
        print(f"message_count={mc}", flush=True)
        dv = delay if delay is not None else "-"
        print(f"delay={dv}", flush=True)
        print(f"unit={(unit or '-')[:16]}", flush=True)
        print(f"source={(source or '-')[:64]}", flush=True)
    except OSError:
        pass


def _query_store_by_zid(zid: str) -> Optional[Store]:
    """Resolve via canonical store identity layer (aliases + cartflow_zid)."""
    from services.store_identity_v1 import (
        canonical_store_slug_on_row,
        resolve_store_row_by_identifier,
    )

    ss = (zid or "").strip()
    if not ss:
        return None
    try:
        row, via = resolve_store_row_by_identifier(ss)
        if row is not None:
            log_recovery_store_lookup(
                canonical_store=ss,
                matched_store_id=getattr(row, "id", None),
                matched_zid=canonical_store_slug_on_row(row),
                found=True,
                action=via,
            )
        return row
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        return None


def ensure_recovery_store_row_for_zid(
    zid: str,
    *,
    allow_schema_warm: bool = True,
) -> Optional[Store]:
    """
    Ensure a Store row exists for canonical widget/recovery zid.
    Provisions sandbox widget slugs (demo/demo2/default) only — no latest-store fallback.
    """
    ss = (zid or "").strip()[:255]
    if not ss:
        return None

    if allow_schema_warm:
        try:
            from main import _ensure_cartflow_api_db_warmed  # noqa: PLC0415

            _ensure_cartflow_api_db_warmed()
        except Exception as exc:  # noqa: BLE001
            _log.warning("recovery store warm skipped: %s", exc)

    row = _query_store_by_zid(ss)
    if row is not None:
        return row

    if not is_widget_recovery_zid(ss):
        log_recovery_store_lookup(
            canonical_store=ss,
            matched_store_id=None,
            matched_zid=None,
            found=False,
            action="missing_non_widget_zid",
        )
        return None

    new_row = Store(
        zid_store_id=ss,
        recovery_delay=1,
        recovery_delay_unit="minutes",
        recovery_attempts=1,
    )
    try:
        db.session.add(new_row)
        db.session.commit()
        from services.store_identity_v1 import ensure_cartflow_zid_alias_for_store

        ensure_cartflow_zid_alias_for_store(new_row)
        log_recovery_store_lookup(
            canonical_store=ss,
            matched_store_id=getattr(new_row, "id", None),
            matched_zid=ss,
            found=True,
            action="provision_widget_row_new",
        )
        return new_row
    except IntegrityError:
        db.session.rollback()
        row = _query_store_by_zid(ss)
        if row is not None:
            log_recovery_store_lookup(
                canonical_store=ss,
                matched_store_id=getattr(row, "id", None),
                matched_zid=getattr(row, "zid_store_id", None),
                found=True,
                action="provision_race_retry",
            )
        return row
    except (SQLAlchemyError, OSError):
        db.session.rollback()
        log_recovery_store_lookup(
            canonical_store=ss,
            matched_store_id=None,
            matched_zid=None,
            found=False,
            action="provision_failed",
        )
        return None


def resolve_recovery_store_row_canonical(
    zid: str,
    *,
    allow_schema_warm: bool = True,
) -> Optional[Store]:
    """Identity-aware lookup, then safe provision for widget recovery slugs only."""
    ss = (zid or "").strip()[:255]
    if not ss:
        log_recovery_store_lookup(
            canonical_store="-",
            matched_store_id=None,
            matched_zid=None,
            found=False,
            action="empty_zid",
        )
        return None

    row = _query_store_by_zid(ss)
    if row is not None:
        return row

    return ensure_recovery_store_row_for_zid(ss, allow_schema_warm=allow_schema_warm)


def ensure_widget_recovery_store_rows_on_warm() -> int:
    """Called from API warm — guarantee demo/demo2 rows exist for storefront recovery."""
    n = 0
    for zid in ("demo", "demo2"):
        if ensure_recovery_store_row_for_zid(zid, allow_schema_warm=False) is not None:
            n += 1
    return n
