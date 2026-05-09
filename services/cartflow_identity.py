# -*- coding: utf-8 -*-
"""
Canonical identity helpers for store_slug, session_id, cart_id.

Single place for structured mismatch logs and behavioral merge guards.
Does not change recovery scheduling or WhatsApp sending.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Tuple

log = logging.getLogger("cartflow")


def log_cartflow_identity_warning(
    *,
    store_slug: str,
    resolved_store_id: str,
    expected_store_id: str,
    session_id: str,
    cart_id: str,
    reason: str,
) -> None:
    """Structured operational log for identity drift (grep: [CARTFLOW IDENTITY WARNING])."""
    ss = (store_slug or "").strip()[:255] or "-"
    rsid = (resolved_store_id or "").strip()[:64] or "-"
    esid = (expected_store_id or "").strip()[:64] or "-"
    sid = (session_id or "").strip()[:512] or "-"
    cid = (cart_id or "").strip()[:255] or "-"
    rsn = (reason or "").strip()[:500] or "-"
    line = (
        "[CARTFLOW IDENTITY WARNING]\n"
        f"store_slug={ss}\n"
        f"resolved_store_id={rsid}\n"
        f"expected_store_id={esid}\n"
        f"session_id={sid}\n"
        f"cart_id={cid}\n"
        f"reason={rsn}"
    )
    try:
        print(line, flush=True)
    except OSError:
        pass
    log.warning("%s", line.replace("\n", " | "))


@dataclass(frozen=True)
class IdentitySnapshot:
    store_slug: str
    session_id: str
    cart_id: str
    recovery_key: str
    store_pk: Optional[int]
    store_zid: Optional[str]


def identity_snapshot_from_payload(payload: dict[str, Any]) -> IdentitySnapshot:
    """Align with main._recovery_key_from_payload / store session cart extractors."""
    from main import (  # noqa: PLC0415 — lazy: avoid circular import at module load
        _cart_id_str_from_payload,
        _load_store_row_for_recovery,
        _normalize_store_slug,
        _recovery_key_from_payload,
        _session_part_from_payload,
    )

    if not isinstance(payload, dict):
        payload = {}
    store_slug = _normalize_store_slug(payload)
    session_id = _session_part_from_payload(payload)
    cart_id = (_cart_id_str_from_payload(payload) or "").strip()[:255]
    recovery_key = _recovery_key_from_payload(payload)
    row = _load_store_row_for_recovery(store_slug)
    store_pk: Optional[int] = None
    store_zid: Optional[str] = None
    if row is not None:
        try:
            if getattr(row, "id", None) is not None:
                store_pk = int(row.id)
        except (TypeError, ValueError):
            store_pk = None
        z = getattr(row, "zid_store_id", None)
        store_zid = str(z).strip()[:255] if isinstance(z, str) and z.strip() else None
    return IdentitySnapshot(
        store_slug=store_slug[:255],
        session_id=session_id[:512],
        cart_id=cart_id,
        recovery_key=recovery_key[:800],
        store_pk=store_pk,
        store_zid=store_zid,
    )


def resolve_store_pk_for_event_slug(slug: str) -> Optional[int]:
    """Same Store row as cart abandon upsert (widget slugs → dashboard latest)."""
    s = (slug or "").strip()
    if not s or s in ("default", "—"):
        return None
    try:
        from main import _load_store_row_for_recovery  # noqa: PLC0415

        from extensions import db  # noqa: PLC0415

        db.create_all()
        row = _load_store_row_for_recovery(s)
        if row is None or getattr(row, "id", None) is None:
            return None
        return int(row.id)
    except (TypeError, ValueError, ImportError, AttributeError):
        try:
            from extensions import db  # noqa: PLC0415

            db.session.rollback()
        except (ImportError, AttributeError):
            pass
        return None


def inferred_expected_store_pk_from_candidates(
    candidates: list[Any],
) -> tuple[Optional[int], str]:
    """
    When payload does not resolve a store PK, infer from abandoned rows if unambiguous.
    Returns (pk_or_none, provenance_tag).
    """
    ids: set[int] = set()
    for ac in candidates:
        if bool(getattr(ac, "vip_mode", False)):
            continue
        raw = getattr(ac, "store_id", None)
        if raw is None:
            continue
        try:
            ids.add(int(raw))
        except (TypeError, ValueError):
            continue
    if len(ids) == 1:
        return next(iter(ids)), "inferred_single_store_from_cart_rows"
    if len(ids) > 1:
        return None, "ambiguous_multi_store_cart_rows"
    return None, "no_store_id_on_cart_rows"


def should_merge_behavioral_for_store(
    ac: Any,
    *,
    expected_store_pk: Optional[int],
    inferred_only: bool,
) -> Tuple[bool, str]:
    """
    If expected_store_pk is set, refuse merge when row.store_id contradicts it.
    Rows with NULL store_id still merge (legacy / backfill).
    """
    if expected_store_pk is None:
        return True, ""
    ac_st = getattr(ac, "store_id", None)
    if ac_st is None:
        return True, ""
    try:
        if int(ac_st) != int(expected_store_pk):
            if inferred_only:
                return False, "store_mismatch_inferred_scope"
            return False, "store_mismatch_payload_scope"
    except (TypeError, ValueError):
        return False, "store_id_uncomparable"
    return True, ""


def detect_abandoned_cart_identity_anomaly(
    session_id: str,
    cart_id: Optional[str],
) -> Tuple[bool, str]:
    """
    True when non-VIP scope for this session/cart is inconsistent (merchant trust risk).

    - More than one abandoned row for the exact (session_id, cart_id) pair.
    - Or multiple non-VIP rows reachable via session/cart with differing store_id.
    """
    from sqlalchemy.exc import SQLAlchemyError  # noqa: PLC0415

    from extensions import db  # noqa: PLC0415
    from models import AbandonedCart  # noqa: PLC0415
    from services.behavioral_recovery.state_store import (  # noqa: PLC0415
        abandoned_carts_for_session_or_cart,
    )

    sid = (session_id or "").strip()[:512]
    cid = (str(cart_id).strip()[:255] if cart_id else "") or ""
    if not sid and not cid:
        return False, ""

    if cid and sid:
        try:
            db.create_all()
            n_pair = (
                db.session.query(AbandonedCart)
                .filter(
                    AbandonedCart.recovery_session_id == sid,
                    AbandonedCart.zid_cart_id == cid,
                    AbandonedCart.vip_mode.is_(False),
                )
                .count()
            )
            if int(n_pair or 0) > 1:
                return True, "duplicate_abandoned_row_same_session_cart"
        except (SQLAlchemyError, OSError, TypeError, ValueError):
            db.session.rollback()

    try:
        non_vip = [
            ac
            for ac in abandoned_carts_for_session_or_cart(sid, cid or None)
            if not bool(getattr(ac, "vip_mode", False))
        ]
    except (SQLAlchemyError, OSError, TypeError, ValueError):
        return False, ""

    store_ids: set[int] = set()
    for ac in non_vip:
        raw = getattr(ac, "store_id", None)
        if raw is None:
            continue
        try:
            store_ids.add(int(raw))
        except (TypeError, ValueError):
            continue
    if len(store_ids) > 1:
        return True, "duplicate_cart_identity_multi_store"
    return False, ""


MERCHANT_IDENTITY_TRUST_AR = "تعذر ربط بيانات السلة"

IDENTITY_TRUST_FAILED_KEY = "identity_trust_failed"
IDENTITY_TRUST_MESSAGE_KEY = "identity_trust_message_ar"
