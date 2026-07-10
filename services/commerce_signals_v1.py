# -*- coding: utf-8 -*-
"""
Commerce Signals V1 — immutable read-only projections.

Answers only: what happened?
Families in V1 runtime: Recovery, Purchase.
Never writes truth. Never decides, explains, or recommends.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from services.commerce_signals_v1_flag import commerce_signals_v1_enabled
from services.recovery_truth_timeline_v1 import (
    STATUS_BEFORE_SEND,
    STATUS_CONTINUATION_STARTED,
    STATUS_CUSTOMER_REPLY,
    STATUS_DELAY_STARTED,
    STATUS_PROVIDER_QUEUED,
    STATUS_PROVIDER_SENT,
    STATUS_SCHEDULED,
    STATUS_WEBHOOK_DELIVERED,
)

log = logging.getLogger("cartflow")

# Bound store-level summary attach — avoid unbounded per-key Truth reads.
_STORE_SIGNAL_KEY_LIMIT = 25

PROJECTION = "CommerceSignalsV1"

SIGNAL_RECOVERY_STARTED = "recovery_started"
SIGNAL_RECOVERY_PROGRESSED = "recovery_progressed"
SIGNAL_RECOVERY_COMPLETED = "recovery_completed"
SIGNAL_RECOVERY_BLOCKED = "recovery_blocked"
SIGNAL_PURCHASE_CONFIRMED = "purchase_confirmed"

_STARTED_STATUSES = frozenset({STATUS_SCHEDULED, STATUS_DELAY_STARTED})
_PROGRESSED_STATUSES = frozenset(
    {
        STATUS_BEFORE_SEND,
        STATUS_PROVIDER_QUEUED,
        STATUS_PROVIDER_SENT,
        STATUS_WEBHOOK_DELIVERED,
        STATUS_CUSTOMER_REPLY,
        STATUS_CONTINUATION_STARTED,
    }
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _norm(v: Any) -> str:
    return str(v or "").strip()


def _store_prefix(store_slug: str) -> str:
    return f"{_norm(store_slug)}:"


def _recovery_key_belongs_to_store(recovery_key: str, store_slug: str) -> bool:
    rk = _norm(recovery_key)
    ss = _norm(store_slug)
    if not rk or not ss:
        return False
    return rk.startswith(_store_prefix(ss))


def _evidence_key(refs: list[dict[str, Any]]) -> tuple[str, ...]:
    parts: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        parts.append(
            f"{_norm(ref.get('ref_type'))}:{_norm(ref.get('id'))}:"
            f"{_norm(ref.get('status'))}:{_norm(ref.get('recovery_key'))}"
        )
    return tuple(sorted(parts))


def _make_signal(
    *,
    signal_type: str,
    subject: dict[str, Any],
    observed_at: str,
    source: str,
    evidence_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "signal_type": signal_type,
        "subject": subject,
        "observed_at": observed_at or _utc_now_iso(),
        "source": source or "unknown",
        "evidence_refs": list(evidence_refs),
    }


def _subject(store_slug: str, recovery_key: str) -> dict[str, Any]:
    return {
        "kind": "cart_recovery",
        "store_slug": _norm(store_slug),
        "recovery_key": _norm(recovery_key),
    }


def build_commerce_signals_v1(
    *,
    store_slug: str,
    recovery_key: str,
    timeline_events: Optional[list[dict[str, Any]]] = None,
    purchase: Optional[dict[str, Any]] = None,
    blocked: Optional[dict[str, Any]] = None,
    force: bool = False,
) -> list[dict[str, Any]]:
    """
    Pure projection from existing truth inputs.

    Returns [] when flag off (unless force=True), store isolation fails,
    or inputs are empty/invalid.
    """
    if not force and not commerce_signals_v1_enabled():
        return []

    ss = _norm(store_slug)
    rk = _norm(recovery_key)
    if not ss or not rk:
        return []
    if not _recovery_key_belongs_to_store(rk, ss):
        return []

    subject = _subject(ss, rk)
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    def _emit(sig: dict[str, Any]) -> None:
        key = (sig["signal_type"], _evidence_key(sig["evidence_refs"]))
        if key in seen:
            return
        seen.add(key)
        out.append(sig)

    # --- Recovery timeline (store-isolated) ---
    started_event: Optional[dict[str, Any]] = None
    for raw in timeline_events or ():
        if not isinstance(raw, dict):
            continue
        ev_store = _norm(raw.get("store_slug"))
        if ev_store and ev_store != ss:
            continue
        ev_rk = _norm(raw.get("recovery_key"))
        if ev_rk and ev_rk != rk:
            continue
        status = _norm(raw.get("status")).lower()
        if not status:
            continue
        row_id = raw.get("row_id")
        refs = [
            {
                "ref_type": "recovery_truth_timeline_event",
                "id": row_id,
                "status": status,
                "recovery_key": rk,
            }
        ]
        observed = _norm(raw.get("timestamp")) or _utc_now_iso()
        source = _norm(raw.get("source")) or "recovery_truth_timeline"

        if status in _STARTED_STATUSES:
            if started_event is None:
                started_event = raw
                _emit(
                    _make_signal(
                        signal_type=SIGNAL_RECOVERY_STARTED,
                        subject=subject,
                        observed_at=observed,
                        source=source,
                        evidence_refs=refs,
                    )
                )
            continue

        if status in _PROGRESSED_STATUSES:
            _emit(
                _make_signal(
                    signal_type=SIGNAL_RECOVERY_PROGRESSED,
                    subject=subject,
                    observed_at=observed,
                    source=source,
                    evidence_refs=refs,
                )
            )

    # --- Purchase (store-isolated) ---
    purchase_ok = False
    if isinstance(purchase, dict) and purchase.get("purchase_detected") is True:
        p_store = _norm(purchase.get("store_slug"))
        p_rk = _norm(purchase.get("recovery_key"))
        if p_store and p_store != ss:
            purchase = None
        elif p_rk and p_rk != rk:
            purchase = None
        else:
            purchase_ok = True
            p_refs = [
                {
                    "ref_type": "purchase_truth_record",
                    "id": purchase.get("id") or purchase.get("purchase_truth_id"),
                    "recovery_key": rk,
                }
            ]
            _emit(
                _make_signal(
                    signal_type=SIGNAL_PURCHASE_CONFIRMED,
                    subject=subject,
                    observed_at=_norm(purchase.get("purchase_time")) or _utc_now_iso(),
                    source=_norm(purchase.get("purchase_source")) or "purchase_truth",
                    evidence_refs=p_refs,
                )
            )
            # Recovery completed = recovery had started and purchase confirmed.
            if started_event is not None:
                started_status = _norm(started_event.get("status")).lower()
                completed_refs = [
                    {
                        "ref_type": "purchase_truth_record",
                        "id": purchase.get("id") or purchase.get("purchase_truth_id"),
                        "recovery_key": rk,
                    },
                    {
                        "ref_type": "recovery_truth_timeline_event",
                        "id": started_event.get("row_id"),
                        "status": started_status,
                        "recovery_key": rk,
                    },
                ]
                _emit(
                    _make_signal(
                        signal_type=SIGNAL_RECOVERY_COMPLETED,
                        subject=subject,
                        observed_at=_norm(purchase.get("purchase_time")) or _utc_now_iso(),
                        source="purchase_truth+recovery_truth_timeline",
                        evidence_refs=completed_refs,
                    )
                )

    # --- Blocked (explicit verified block fact only) ---
    if isinstance(blocked, dict) and _norm(blocked.get("reason")):
        b_store = _norm(blocked.get("store_slug"))
        b_rk = _norm(blocked.get("recovery_key"))
        if (not b_store or b_store == ss) and (not b_rk or b_rk == rk):
            b_refs = [
                {
                    "ref_type": _norm(blocked.get("ref_type")) or "recovery_block",
                    "id": blocked.get("id"),
                    "status": _norm(blocked.get("reason")),
                    "recovery_key": rk,
                }
            ]
            _emit(
                _make_signal(
                    signal_type=SIGNAL_RECOVERY_BLOCKED,
                    subject=subject,
                    observed_at=_norm(blocked.get("observed_at")) or _utc_now_iso(),
                    source=_norm(blocked.get("source")) or "recovery_truth",
                    evidence_refs=b_refs,
                )
            )

    # Silence unused in pure path
    _ = purchase_ok
    return out


def load_commerce_signals_for_recovery_key(
    *,
    store_slug: str,
    recovery_key: str,
    force: bool = False,
) -> dict[str, Any]:
    """
    Read-only loader for debug/test projection.
    Does not write. Does not attach to merchant UI.
    """
    if not force and not commerce_signals_v1_enabled():
        return {
            "ok": True,
            "projection": PROJECTION,
            "enabled": False,
            "signals": [],
        }

    ss = _norm(store_slug)
    rk = _norm(recovery_key)
    if not ss or not rk:
        return {"ok": False, "error": "store_slug_and_recovery_key_required", "signals": []}
    if not _recovery_key_belongs_to_store(rk, ss):
        return {
            "ok": False,
            "error": "store_isolation_rejected",
            "store_slug": ss,
            "recovery_key": rk,
            "signals": [],
        }

    timeline: list[dict[str, Any]] = []
    purchase: Optional[dict[str, Any]] = None
    blocked: Optional[dict[str, Any]] = None

    try:
        from services.recovery_truth_timeline_v1 import (  # noqa: PLC0415
            get_recovery_truth_timeline,
        )

        timeline = get_recovery_truth_timeline(rk)
    except Exception:  # noqa: BLE001
        timeline = []

    try:
        from services.cartflow_purchase_truth import purchase_context  # noqa: PLC0415

        purchase = purchase_context(rk)
    except Exception:  # noqa: BLE001
        purchase = None

    try:
        from models import RecoverySchedule  # noqa: PLC0415
        from extensions import db  # noqa: PLC0415

        row = (
            db.session.query(RecoverySchedule)
            .filter(RecoverySchedule.recovery_key == rk)
            .order_by(RecoverySchedule.id.desc())
            .first()
        )
        if row is not None:
            err = _norm(getattr(row, "last_error", None)).lower()
            if err in (
                "schedule_blocked_missing_phone",
                "purchase_truth_stop",
                "skipped_missing_phone",
                "skipped_no_verified_phone",
            ):
                blocked = {
                    "reason": err,
                    "store_slug": ss,
                    "recovery_key": rk,
                    "observed_at": _utc_now_iso(),
                    "source": "recovery_schedule",
                    "ref_type": "recovery_schedule",
                    "id": getattr(row, "id", None),
                }
    except Exception:  # noqa: BLE001
        blocked = None

    signals = build_commerce_signals_v1(
        store_slug=ss,
        recovery_key=rk,
        timeline_events=timeline,
        purchase=purchase,
        blocked=blocked,
        force=force,
    )
    return {
        "ok": True,
        "projection": PROJECTION,
        "enabled": True,
        "store_slug": ss,
        "recovery_key": rk,
        "signals": signals,
        "signal_count": len(signals),
        "read_only": True,
    }


def _recent_store_recovery_keys(
    store_slug: str,
    *,
    limit: int = _STORE_SIGNAL_KEY_LIMIT,
) -> list[str]:
    """Bounded, store-isolated recovery_key set from existing Truth tables."""
    ss = _norm(store_slug)
    if not ss or limit <= 0:
        return []
    out: list[str] = []
    seen: set[str] = set()

    def _add(raw: Any) -> None:
        rk = _norm(raw)
        if not rk or rk in seen:
            return
        if not _recovery_key_belongs_to_store(rk, ss):
            return
        seen.add(rk)
        out.append(rk)

    try:
        from extensions import db  # noqa: PLC0415
        from models import (  # noqa: PLC0415
            PurchaseTruthRecord,
            RecoverySchedule,
            RecoveryTruthTimelineEvent,
        )
        from sqlalchemy import desc  # noqa: PLC0415

        for model, order_col in (
            (RecoveryTruthTimelineEvent, RecoveryTruthTimelineEvent.id),
            (PurchaseTruthRecord, PurchaseTruthRecord.id),
            (RecoverySchedule, RecoverySchedule.id),
        ):
            if len(out) >= limit:
                break
            rows = (
                db.session.query(model.recovery_key)
                .filter(model.store_slug == ss)
                .order_by(desc(order_col))
                .limit(limit)
                .all()
            )
            for row in rows:
                _add(row[0] if row is not None else None)
                if len(out) >= limit:
                    break
    except Exception:  # noqa: BLE001
        return out[:limit]
    return out[:limit]


def load_store_commerce_signals_v1(
    *,
    store_slug: str,
    force: bool = False,
    recovery_keys: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Store-scoped read-only Signals for summary attach.

    Reuses per-key Truth→Signal projection; dedupes by type+evidence.
    """
    if not force and not commerce_signals_v1_enabled():
        return {
            "ok": True,
            "projection": PROJECTION,
            "enabled": False,
            "signals": [],
        }

    ss = _norm(store_slug)
    if not ss:
        return {
            "ok": True,
            "projection": PROJECTION,
            "enabled": True,
            "store_slug": "",
            "signals": [],
            "signal_count": 0,
            "read_only": True,
        }

    keys = list(recovery_keys) if recovery_keys is not None else _recent_store_recovery_keys(ss)
    signals: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for raw_rk in keys:
        rk = _norm(raw_rk)
        if not rk or not _recovery_key_belongs_to_store(rk, ss):
            continue
        loaded = load_commerce_signals_for_recovery_key(
            store_slug=ss,
            recovery_key=rk,
            force=force,
        )
        for sig in loaded.get("signals") or []:
            if not isinstance(sig, dict):
                continue
            key = (str(sig.get("signal_type") or ""), _evidence_key(sig.get("evidence_refs") or []))
            if key in seen:
                continue
            seen.add(key)
            signals.append(sig)

    return {
        "ok": True,
        "projection": PROJECTION,
        "enabled": True,
        "store_slug": ss,
        "signals": signals,
        "signal_count": len(signals),
        "read_only": True,
    }


def attach_commerce_signals_v1_to_summary(
    body: dict[str, Any],
    *,
    store_slug: str = "",
    force: bool = False,
) -> dict[str, Any]:
    """Attach store-scoped CommerceSignalsV1 when flag enabled (before Pulse)."""
    if not isinstance(body, dict):
        body = dict(body or {})
    if not force and not commerce_signals_v1_enabled():
        body.pop("commerce_signals_v1", None)
        return body

    slug = _norm(store_slug)
    if not slug:
        snap = body.get("_snapshot")
        if isinstance(snap, Mapping):
            slug = _norm(snap.get("store_slug"))
    if not slug:
        slug = _norm(body.get("store_slug"))

    try:
        payload = load_store_commerce_signals_v1(store_slug=slug, force=force)
        body["commerce_signals_v1"] = {
            "projection": PROJECTION,
            "store_slug": slug,
            "signals": list(payload.get("signals") or []),
            "read_only": True,
        }
    except Exception as exc:  # noqa: BLE001
        log.warning("commerce_signals_v1 attach: %s", exc)
        body["commerce_signals_v1"] = {
            "projection": PROJECTION,
            "store_slug": slug,
            "signals": [],
            "read_only": True,
        }
    return body


__all__ = [
    "PROJECTION",
    "SIGNAL_PURCHASE_CONFIRMED",
    "SIGNAL_RECOVERY_BLOCKED",
    "SIGNAL_RECOVERY_COMPLETED",
    "SIGNAL_RECOVERY_PROGRESSED",
    "SIGNAL_RECOVERY_STARTED",
    "attach_commerce_signals_v1_to_summary",
    "build_commerce_signals_v1",
    "load_commerce_signals_for_recovery_key",
    "load_store_commerce_signals_v1",
]
